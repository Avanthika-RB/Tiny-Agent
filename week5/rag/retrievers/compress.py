"""Day 4: contextual compression. After retrieval, the chat model copies out ONLY the sentences
that help answer the question, so the agent reads less (and less noise). Retrieval metrics cannot
see this (the same chunks are retrieved either way), so day4.py measures it with an LLM judge on
the ANSWERS written from the full chunks vs from the compressed ones.
"""

import re

import common


def compress(question, chunks):
    """One LLM call for all chunks. Returns one string per chunk (empty if nothing was relevant)."""
    numbered = "\n\n".join(f"[{i}]\n{c['text']}" for i, c in enumerate(chunks, start=1))
    answer = common.chat(
        "Below are numbered passages from IT help articles and a question. For each passage, copy "
        "word for word ONLY the sentences that help answer the question. Write the passage number in "
        "brackets, then the copied sentences. If nothing in a passage helps, write the number and NONE.\n\n"
        f"Question: {question}\n\n{numbered}", purpose="compression")
    parts = {int(n): text.strip() for n, text in re.findall(r"\[(\d+)\]\s*(.*?)(?=\n?\[\d+\]|\Z)", answer, re.S)}
    return ["" if parts.get(i, "").upper().startswith("NONE") else parts.get(i, "")
            for i in range(1, len(chunks) + 1)]
