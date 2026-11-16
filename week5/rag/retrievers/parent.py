"""Day 4: parent-document retrieval, also called small-to-big.

Search SMALL chunks (the 200-character `fixed_200` collection from Week 4): a small chunk is about
one thing, so its vector is precise. But return each small chunk's PARENT: the whole section it
came from, taken from the `markdown_headers` collection. The parent has the full context (every
step of a procedure, the whole table) that a 200-character piece cuts off.

Which parent? The markdown_headers chunk from the same file that shares the most text with the
small chunk (longest run of common characters). A small chunk on a section boundary goes to the
section holding most of it. Several small chunks of one section give that section once.
"""

from difflib import SequenceMatcher

import common

CHILD = "fixed_200"
PARENT = common.BASELINE        # markdown_headers
CHILD_POOL = 30                 # small chunks looked at per question before turning them into parents
_map = None


def squash(text):
    return " ".join(text.lower().split())


def parent_map():
    """{small chunk id: its parent chunk}. Built once."""
    global _map
    if _map is None:
        parents = common.all_chunks(PARENT)
        _map = {}
        for child in common.all_chunks(CHILD):
            same_file = [p for p in parents if p["metadata"]["source"] == child["metadata"]["source"]]
            if not same_file:     # a copy stored under another file name: fall back to the same article
                article = child["metadata"]["source"].split("/")[-1][:2]
                same_file = [p for p in parents if p["metadata"]["source"].split("/")[-1][:2] == article]
            c = squash(child["text"])

            def shared(p):
                t = squash(p["text"])
                return SequenceMatcher(None, c, t, autojunk=False).find_longest_match(0, len(c), 0, len(t)).size
            _map[child["id"]] = max(same_file, key=shared)
    return _map


def to_parents(children):
    """Small chunks, best first -> their parents, best first, each parent once.
    A parent keeps the distance of its best small chunk."""
    mapping = parent_map()
    seen, parents = set(), []
    for child in children:
        parent = mapping[child["id"]]
        if parent["id"] not in seen:
            seen.add(parent["id"])
            parents.append({**parent, "distance": child.get("distance"), "child_text": child["text"]})
    return parents


def make_parent():
    """Plain version for the Day 4 comparison: dense search on the small chunks, return parents."""
    def retrieve(question, k):
        children = common.query(CHILD, common.embed_query(question), CHILD_POOL)
        return to_parents(children)[:k]
    retrieve.__name__ = "parent_document"
    return retrieve
