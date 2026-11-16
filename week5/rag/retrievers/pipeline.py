"""Day 4: the full retrieval pipeline, every component switchable, so tune.py can run the grid and
the ablation with ONE function.

    question
      -> [multi-query: + 3 LLM rephrasings, the rankings fused with RRF]       (multi_query)
      -> hybrid search: alpha * dense + (1 - alpha) * BM25, every chunk ranked  (alpha; 1.0 = no BM25)
         over the small 200-char chunks if parent=True, else markdown_headers
      -> [parent-document: small chunks -> their sections, each section once] (parent)
      -> keep the best k_candidates
      -> [rerank with the cross-encoder]                                       (rerank)
      -> the best top_n
"""

import common
from retrievers import parent as parent_doc
from retrievers.dense import dense_ranking
from retrievers.hybrid import rrf, weighted_ranking
from retrievers.rerank import rerank as rerank_chunks
from retrievers.transforms import rephrasings


def make_pipeline(alpha=0.7, k_candidates=20, top_n=5, rerank=True, multi_query=False, parent=False, name=None):
    collection = parent_doc.CHILD if parent else common.BASELINE

    def ranking(text):
        if alpha >= 1.0:
            return dense_ranking(text, collection)
        return weighted_ranking(text, alpha, collection)

    def retrieve(question, k):
        if multi_query:
            ranked = rrf([ranking(q) for q in [question] + rephrasings(question)])
        else:
            ranked = ranking(question)
        if parent:
            ranked = parent_doc.to_parents(ranked)
        candidates = ranked[:k_candidates]
        n = min(top_n, k)
        return rerank_chunks(question, candidates, n) if rerank else candidates[:n]

    retrieve.__name__ = name or describe(alpha, k_candidates, top_n, rerank, multi_query, parent)
    return retrieve


def describe(alpha, k_candidates, top_n, rerank, multi_query, parent):
    parts = [f"alpha {alpha}" if alpha < 1.0 else "dense only"]
    if multi_query:
        parts.append("multi-query")
    if parent:
        parts.append("parent-doc")
    parts.append(f"pool {k_candidates}, rerank to {top_n}" if rerank else f"top {top_n}, no rerank")
    return ", ".join(parts)
