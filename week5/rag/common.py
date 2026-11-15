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
BASELINE = "markdown_headers"               # chosen on Day 1. Every technique from Day 2 on searches THESE chunks.
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


_passage_cache = {}


def embed_passage(text):
    """Passage-mode embedding of a text that is not a question (HyDE's hypothetical answer).
    Kept in memory for the run only: the text changes whenever the LLM's answer does."""
    if text not in _passage_cache:
        _passage_cache[text] = ingest.get_embeddings().embed_documents([text])[0]
    return _passage_cache[text]


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


def query(name, vector, n, where=None):
    """Top-n chunks of one collection for a query vector: [{"id", "text", "metadata", "distance"}].

    Same Windows workaround as week4/rag/compare.py: if Chroma cannot open the saved index
    ("Nothing found on disk"), the chunks are read, embedded again in passage mode (cached by
    chunk hash, shared with Week 4), and searched in an in-memory Chroma copy instead.
    """
    import chromadb.errors
    args = {"query_embeddings": [vector], "n_results": n, "include": ["documents", "metadatas", "distances"]}
    if where:
        args["where"] = where          # metadata filter, applied BEFORE the similarity search
    if name in _memory_copies:
        result = _memory_copies[name].query(**args)
    else:
        col = get_collection(name)
        try:
            result = col.query(**args)
        except chromadb.errors.InternalError as error:
            if "Nothing found on disk" not in str(error):
                raise
            _memory_copies[name] = in_memory_copy(name, col)
            result = _memory_copies[name].query(**args)
    return [
        {"id": i, "text": doc, "metadata": meta, "distance": dist}
        for i, doc, meta, dist in zip(result["ids"][0], result["documents"][0],
                                      result["metadatas"][0], result["distances"][0])
    ]


def stored_vectors(name, records):
    """The passage vectors of a collection's chunks, {id: vector}. Read from Chroma if it can;
    on the Windows bug, embedded again in passage mode (cached by chunk hash, shared with Week 4)."""
    import chromadb.errors
    try:
        got = get_collection(name).get(ids=records["ids"], include=["embeddings"])
        return {i: list(v) for i, v in zip(got["ids"], got["embeddings"])}
    except chromadb.errors.InternalError as error:
        if "Nothing found on disk" not in str(error):
            raise
    cache = json.loads(FALLBACK_CACHE.read_text(encoding="utf-8")) if FALLBACK_CACHE.exists() else {}
    missing = [i for i in records["ids"] if i not in cache]
    if missing:
        texts = dict(zip(records["ids"], records["documents"]))
        cache.update(zip(missing, ingest.get_embeddings().embed_documents([texts[i] for i in missing])))
        FALLBACK_CACHE.parent.mkdir(exist_ok=True)
        FALLBACK_CACHE.write_text(json.dumps(cache), encoding="utf-8")
    return {i: cache[i] for i in records["ids"]}


def in_memory_copy(name, col):
    import chromadb
    print(f"  ({name}: Chroma could not open its saved index, so it is searched from an in-memory copy)")
    records = col.get(include=["documents", "metadatas"])
    vectors = stored_vectors(name, records)
    copy = chromadb.EphemeralClient().get_or_create_collection(
        f"copy_{name}", metadata={"hnsw:space": "cosine"}, embedding_function=None)
    copy.add(ids=records["ids"], embeddings=[vectors[i] for i in records["ids"]],
             documents=records["documents"], metadatas=records["metadatas"])
    return copy


_vectors = {}


def chunk_vectors(name):
    """{chunk id: passage vector} for every chunk of a collection (MMR needs them)."""
    if name not in _vectors:
        records = get_collection(name).get(include=["documents", "metadatas"])
        _vectors[name] = stored_vectors(name, records)
    return _vectors[name]


def count(name):
    return get_collection(name).count()


# The chat model for query-time LLM calls (Day 2 article guess, Day 3 transforms)
CHAT_MODEL = "nvidia/nemotron-3-super-120b-a12b"            # the assignment's choice
CHAT_BACKUP = "nvidia/nemotron-3.5-lightning-30b-a3b"       # the model the helpdesk uses, if the first is retired
LLM_LOG = RESULTS / "llm_log.jsonl"
_chat = None


def chat(prompt, purpose):
    """One LLM call at temperature 0. Every prompt and answer is appended to results/llm_log.jsonl
    (gotcha 4: log every generated query, so a weird result can be explained)."""
    global _chat
    if _chat is None:
        import os
        from dotenv import find_dotenv, load_dotenv
        from langchain_openai import ChatOpenAI
        load_dotenv(find_dotenv(usecwd=True))
        make = lambda model: ChatOpenAI(model=model, base_url="https://integrate.api.nvidia.com/v1",
                                        api_key=os.environ["NVIDIA_API_KEY"], temperature=0, max_retries=3)
        _chat = make(CHAT_MODEL).with_fallbacks([make(CHAT_BACKUP)])
    reply = _chat.invoke(prompt)
    answer = reply.content.strip()
    RESULTS.mkdir(exist_ok=True)
    with LLM_LOG.open("a", encoding="utf-8") as log:
        log.write(json.dumps({"purpose": purpose, "prompt": prompt, "answer": answer,
                              "model": reply.response_metadata.get("model_name")}) + "\n")
    return answer


def all_chunks(name):
    """Every chunk of a collection (for BM25 and friends on Day 2): [{"id", "text", "metadata"}]."""
    records = get_collection(name).get(include=["documents", "metadatas"])
    return [{"id": i, "text": d, "metadata": m}
            for i, d, m in zip(records["ids"], records["documents"], records["metadatas"])]
