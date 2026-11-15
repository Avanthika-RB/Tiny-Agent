"""Day 1 baseline: plain dense similarity search on one Week 4 collection.

The question is embedded in query mode (cached, see common.embed_query) and Chroma returns the
k chunks with the smallest cosine distance. No filters, no reranking, nothing else.
"""

import common


def make_dense(collection=common.BASELINE):
    def retrieve(question, k):
        return common.query(collection, common.embed_query(question), k)
    retrieve.__name__ = f"dense_{collection}"
    return retrieve


def dense_ranking(question, collection=common.BASELINE):
    """EVERY chunk of the collection, best first, with its cosine similarity (1 - distance).
    Hybrid search needs the dense score of every chunk, not just the top k."""
    chunks = common.query(collection, common.embed_query(question), common.count(collection))
    for c in chunks:
        c["score"] = 1 - c["distance"]
    return chunks
