"""Day 2: maximal marginal relevance (MMR): relevant AND different from what is already picked.

Take the top 20 dense candidates. Pick chunks one at a time; each time choose the chunk with the
highest
    lambda * similarity(question, chunk) - (1 - lambda) * max similarity(chunk, chunks already picked)
lambda = 1 is plain dense search; lambda = 0 only cares about being different. Here lambda = 0.5.
Similarities are cosine similarities of the stored passage vectors.
"""

import math

import common

CANDIDATES = 20


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def mmr(candidates, vectors, lam, k):
    picked = []
    remaining = list(candidates)
    while remaining and len(picked) < k:
        def value(c):
            redundancy = max((cosine(vectors[c["id"]], vectors[p["id"]]) for p in picked), default=0.0)
            return lam * (1 - c["distance"]) - (1 - lam) * redundancy
        best = max(remaining, key=value)
        picked.append(best)
        remaining.remove(best)
    return picked


def make_mmr(lam=0.5, collection=common.BASELINE):
    vectors = common.chunk_vectors(collection)

    def retrieve(question, k):
        candidates = common.query(collection, common.embed_query(question), CANDIDATES)
        return mmr(candidates, vectors, lam, k)
    retrieve.__name__ = f"mmr_{lam}"
    return retrieve
