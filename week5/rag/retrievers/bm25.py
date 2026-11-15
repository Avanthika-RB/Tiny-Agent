"""Day 2: BM25, sparse keyword search, over the SAME chunk texts as the baseline collection.

Tokenisation choices (they matter more than the BM25 parameters):
  - lowercase everything;
  - keep "compound" tokens whole AND split into parts: "vpn-in.example.com" gives
    vpn-in.example.com, vpn, in, example, com. So an exact path or host name scores highly when
    the question contains it, and its parts still match questions that use only one word;
  - numbers and codes stay tokens: 1103, pcl6, ipp, smb, aus-02-03;
  - drop a short list of English stopwords (the, a, how, do, my ...), which carry no meaning
    and would otherwise match every chunk;
  - no stemming: "printer" and "printers" are different tokens. Simple, and easy to explain.
BM25Okapi with its default parameters (k1=1.5, b=0.75).
"""

import re

from rank_bm25 import BM25Okapi

import common

STOPWORDS = set("""
a an and are as at be but by can do does for from how i if in is it its me my of on or so that
the their them then there this to was what when where which who why will with you your i'm
""".split())

COMPOUND = re.compile(r"[a-z0-9]+(?:[.\-/:_][a-z0-9]+)*")


def tokenise(text):
    tokens = []
    for compound in COMPOUND.findall(text.lower()):
        parts = re.findall(r"[a-z0-9]+", compound)
        if len(parts) > 1:
            tokens.append(compound)
        tokens += [p for p in parts if p not in STOPWORDS]
    return tokens


class BM25Index:
    def __init__(self, collection=common.BASELINE):
        self.chunks = common.all_chunks(collection)
        self.bm25 = BM25Okapi([tokenise(c["text"]) for c in self.chunks])

    def ranking(self, question):
        """EVERY chunk, best first, with its BM25 score."""
        scores = self.bm25.get_scores(tokenise(question))
        ranked = sorted(zip(scores, range(len(self.chunks))), key=lambda pair: -pair[0])
        return [{**self.chunks[i], "score": float(s)} for s, i in ranked]


_indexes = {}


def get_index(collection=common.BASELINE):
    if collection not in _indexes:
        _indexes[collection] = BM25Index(collection)
    return _indexes[collection]


def make_bm25(collection=common.BASELINE):
    index = get_index(collection)

    def retrieve(question, k):
        return index.ranking(question)[:k]
    retrieve.__name__ = "bm25"
    return retrieve
