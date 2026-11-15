"""Shared plumbing for Week 5: paths, the eval set, the Week 4 collections, and question embeddings.

Week 5 searches the collections Week 4 built (week4/chroma_db), with the same embedding model.
Nothing here changes them.
"""

import json
import sys
import time
from pathlib import Path

WEEK5 = Path(__file__).resolve().parent.parent
REPO = WEEK5.parent
WEEK4_RAG = REPO / "week4" / "rag"
sys.path.insert(0, str(WEEK4_RAG))       # so `import ingest` finds the Week 4 pipeline

import ingest  # noqa: E402  (Week 4: EMBED_MODEL, CHROMA_PATH, get_embeddings, clean_text, ...)

EVAL_SET = WEEK5 / "eval_set.jsonl"
RESULTS = WEEK5 / "results"
CACHE = Path(__file__).resolve().parent / "cache"
QUERY_CACHE = CACHE / "query_vectors.json"
FALLBACK_CACHE = WEEK4_RAG / "build" / "fallback_vectors.json"   # shared with week4/rag/compare.py

COLLECTIONS = list(ingest.STRATEGIES)       # the six Week 4 collections
EMBED_MODEL = ingest.EMBED_MODEL
HELD_OUT_FROM = 31                          # qid 31-35 are my own questions: held out, never tuned on


def load_eval_set():
    return [json.loads(line) for line in EVAL_SET.read_text(encoding="utf-8").splitlines() if line.strip()]


def gold_of(question):
    """{"01/Policy": 2, ...} for one eval question."""
    return {f"{g['article']}/{g['section']}": g["grade"] for g in question["gold"]}


# Question embeddings, cached (gotcha 5: embed each question once, reuse all week)
_query_cache = None


def _load_query_cache():
    global _query_cache
    if _query_cache is None:
        data = json.loads(QUERY_CACHE.read_text(encoding="utf-8")) if QUERY_CACHE.exists() else {}
        _query_cache = data if data.get("model") == EMBED_MODEL else {"model": EMBED_MODEL, "vectors": {}, "ms": {}}
    return _query_cache


def embed_query(text):
    """Query-mode embedding of a question. Calls the API only the first time a text is seen."""
    cache = _load_query_cache()
    if text not in cache["vectors"]:
        start = time.perf_counter()
        cache["vectors"][text] = ingest.get_embeddings().embed_query(text)
        cache["ms"][text] = (time.perf_counter() - start) * 1000
        CACHE.mkdir(exist_ok=True)
        QUERY_CACHE.write_text(json.dumps(cache), encoding="utf-8")
    return cache["vectors"][text]


def embedding_ms():
    """How long each question took to embed when it was first cached (the cost the cache hides)."""
    return list(_load_query_cache()["ms"].values())


# The Week 4 collections
_client = None
_collections = {}
_memory_copies = {}


def get_collection(name):
    global _client
    import chromadb
    if _client is None:
        _client = chromadb.PersistentClient(path=str(ingest.CHROMA_PATH))
    if name not in _collections:
        col = _client.get_collection(name)
        model = col.metadata.get("embedding_model")
        if model != EMBED_MODEL:
            raise SystemExit(f"{name} was built with {model}, but questions use {EMBED_MODEL}.")
        _collections[name] = col
    return _collections[name]


def query(name, vector, n):
    """Top-n chunks of one collection for a query vector: [{"id", "text", "metadata", "distance"}].

    Same Windows workaround as week4/rag/compare.py: if Chroma cannot open the saved index
    ("Nothing found on disk"), the chunks are read, embedded again in passage mode (cached by
    chunk hash, shared with Week 4), and searched in an in-memory Chroma copy instead.
    """
    import chromadb.errors
    include = ["documents", "metadatas", "distances"]
    if name in _memory_copies:
        result = _memory_copies[name].query(query_embeddings=[vector], n_results=n, include=include)
    else:
        col = get_collection(name)
        try:
            result = col.query(query_embeddings=[vector], n_results=n, include=include)
        except chromadb.errors.InternalError as error:
            if "Nothing found on disk" not in str(error):
                raise
            _memory_copies[name] = in_memory_copy(name, col)
            result = _memory_copies[name].query(query_embeddings=[vector], n_results=n, include=include)
    return [
        {"id": i, "text": doc, "metadata": meta, "distance": dist}
        for i, doc, meta, dist in zip(result["ids"][0], result["documents"][0],
                                      result["metadatas"][0], result["distances"][0])
    ]


def in_memory_copy(name, col):
    import chromadb
    print(f"  ({name}: Chroma could not open its saved index, so it is searched from an in-memory copy)")
    records = col.get(include=["documents", "metadatas"])
    cache = json.loads(FALLBACK_CACHE.read_text(encoding="utf-8")) if FALLBACK_CACHE.exists() else {}
    missing = [i for i in records["ids"] if i not in cache]
    if missing:
        texts = dict(zip(records["ids"], records["documents"]))
        cache.update(zip(missing, ingest.get_embeddings().embed_documents([texts[i] for i in missing])))
        FALLBACK_CACHE.parent.mkdir(exist_ok=True)
        FALLBACK_CACHE.write_text(json.dumps(cache), encoding="utf-8")
    copy = chromadb.EphemeralClient().get_or_create_collection(
        f"copy_{name}", metadata={"hnsw:space": "cosine"}, embedding_function=None)
    copy.add(ids=records["ids"], embeddings=[cache[i] for i in records["ids"]],
             documents=records["documents"], metadatas=records["metadatas"])
    return copy


def all_chunks(name):
    """Every chunk of a collection (for BM25 and friends on Day 2): [{"id", "text", "metadata"}]."""
    records = get_collection(name).get(include=["documents", "metadatas"])
    return [{"id": i, "text": d, "metadata": m}
            for i, d, m in zip(records["ids"], records["documents"], records["metadatas"])]
