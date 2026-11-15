"""Day 2: hybrid search = dense + BM25 combined, two ways.

1. Reciprocal rank fusion (RRF): uses only the RANKS, never the scores.
       score(chunk) = sum over retrievers of 1 / (k + rank in that retriever),  k = 60, ranks start at 1
   A chunk a retriever did not return adds 0 from that retriever.
2. Weighted fusion: uses the SCORES. Dense similarities and BM25 scores live on different scales
   (about 0.2-0.8 vs 0-15), so each is min-max normalised to 0..1 first, then
       score(chunk) = alpha * dense + (1 - alpha) * bm25
   alpha is the weight on DENSE: alpha=1 is pure dense, alpha=0 is pure BM25.
"""

import common
from retrievers.bm25 import get_index
from retrievers.dense import dense_ranking


def rrf(rankings, k=60):
    """rankings: several lists of chunks, each best first. Returns one fused list, best first."""
    scores, chunks = {}, {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            scores[chunk["id"]] = scores.get(chunk["id"], 0.0) + 1 / (k + rank)
            chunks.setdefault(chunk["id"], chunk)
    fused = sorted(scores, key=lambda cid: -scores[cid])
    return [{**chunks[cid], "score": scores[cid]} for cid in fused]


def min_max(chunks):
    values = [c["score"] for c in chunks]
    low, high = min(values), max(values)
    return {c["id"]: (c["score"] - low) / (high - low) if high > low else 0.0 for c in chunks}


def weighted(dense, sparse, alpha):
    d, s = min_max(dense), min_max(sparse)
    chunks = {c["id"]: c for c in dense + sparse}
    scores = {cid: alpha * d.get(cid, 0.0) + (1 - alpha) * s.get(cid, 0.0) for cid in chunks}
    return [{**chunks[cid], "score": scores[cid]} for cid in sorted(scores, key=lambda cid: -scores[cid])]


def make_rrf(collection=common.BASELINE, k=60):
    index = get_index(collection)

    def retrieve(question, top):
        return rrf([dense_ranking(question, collection), index.ranking(question)], k)[:top]
    retrieve.__name__ = f"hybrid_rrf_k{k}"
    return retrieve


def make_weighted(alpha, collection=common.BASELINE):
    index = get_index(collection)

    def retrieve(question, top):
        return weighted(dense_ranking(question, collection), index.ranking(question), alpha)[:top]
    retrieve.__name__ = f"hybrid_alpha_{alpha}"
    return retrieve
