"""Day 3: two-stage retrieval. Stage 1 = the Day 2 winner fetches a POOL of candidates (10, 20 or
40). Stage 2 = NVIDIA's reranker, a cross-encoder, reads the question and each candidate TOGETHER
and scores how well that chunk answers it. Keep the best top_n.

Why two stages: the first stage (a bi-encoder: question and chunk embedded separately) is fast
enough to search every chunk but less precise. The cross-encoder is more precise but needs one
model pass per (question, chunk) pair, so it only sees the pool.

Gotcha 3: only the chunk TEXT goes to the reranker, no metadata. Long texts are cut at the end.
"""

import os

from langchain_core.documents import Document

import common

RERANK_MODELS = [                              # tried in this order; the first that answers is used
    "nvidia/llama-nemotron-rerank-1b-v2",      # the assignment's
    "nvidia/llama-3.2-nv-rerankqa-1b-v2",
    "nvidia/nv-rerankqa-mistral-4b-v3",
]
_reranker = None
_by_top_n = {}
USED_MODEL = None


def reranker(top_n):
    """The reranker that keeps the best top_n. The model is chosen once, on the first call."""
    global _reranker, USED_MODEL
    if _reranker is None:
        from dotenv import find_dotenv, load_dotenv
        from langchain_nvidia_ai_endpoints import NVIDIARerank
        load_dotenv(find_dotenv(usecwd=True))
        errors = []
        try:                           # then every reranker in NVIDIA's catalog, in case all of the above are retired
            catalog = [m.id for m in NVIDIARerank.get_available_models() if "rerank" in m.id and m.id not in RERANK_MODELS]
        except Exception:
            catalog = []
        import warnings
        warnings.filterwarnings("ignore", message=".*(deprecated|unknown).*")
        for model in RERANK_MODELS + catalog:
            try:
                candidate = NVIDIARerank(model=model, truncate="END", api_key=os.environ.get("NVIDIA_API_KEY"))
                candidate.compress_documents(documents=[Document(page_content="test")], query="test")
                _reranker, USED_MODEL = candidate, model
                break
            except Exception as error:
                errors.append(f"{model}: {str(error).splitlines()[0][:100]}")
        if _reranker is None:
            raise SystemExit("No reranker model answered:\n  " + "\n  ".join(errors) +
                             "\nRun `python rag/day3.py --list-rerankers` and add a working name to RERANK_MODELS.")
        print(f"  (reranker: {USED_MODEL})")
    if top_n not in _by_top_n:
        from langchain_nvidia_ai_endpoints import NVIDIARerank
        _by_top_n[top_n] = NVIDIARerank(model=USED_MODEL, truncate="END", top_n=top_n,
                                        api_key=os.environ.get("NVIDIA_API_KEY"))
    return _by_top_n[top_n]


def rerank(question, candidates, top_n):
    docs = [Document(page_content=c["text"], metadata={"position": i}) for i, c in enumerate(candidates)]
    model = reranker(top_n)
    ranked = common.ingest.with_backoff(lambda: model.compress_documents(documents=docs, query=question))
    return [{**candidates[d.metadata["position"]], "rerank_score": d.metadata.get("relevance_score")}
            for d in ranked]


def make_rerank(first_stage_ranking, pool, top_n):
    """first_stage_ranking(question) -> every chunk, best first (the Day 2 winner)."""
    def retrieve(question, k):
        candidates = first_stage_ranking(question)[:pool]
        return rerank(question, candidates, min(top_n, k))
    retrieve.__name__ = f"rerank_pool{pool}_top{top_n}"
    return retrieve


def list_rerankers():
    """Try every reranker in the catalog with one tiny request: the catalog still lists retired ones."""
    import warnings
    from dotenv import find_dotenv, load_dotenv
    from langchain_nvidia_ai_endpoints import NVIDIARerank
    warnings.filterwarnings("ignore")
    load_dotenv(find_dotenv(usecwd=True))
    for m in NVIDIARerank.get_available_models():
        try:
            NVIDIARerank(model=m.id, truncate="END").compress_documents(documents=[Document(page_content="test")], query="test")
            print(f"OK    {m.id}")
        except Exception as error:
            print(f"FAIL  {m.id}  {str(error).splitlines()[0][:80] if str(error).strip() else type(error).__name__}")
