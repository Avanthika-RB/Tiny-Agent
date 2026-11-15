"""Day 2: metadata prefilter. Search only the chunks of ONE article (filter on the `source`
metadata in Chroma, applied BEFORE the similarity search).

Two ways to choose the article:
  - rule: the question names an area. Area words below; a question qualifies only if it names
    exactly one area. Evaluated on those questions only.
  - LLM: for EVERY question, the chat model guesses which of the 6 articles answers it. One extra
    LLM call per question. If the guess is wrong, the right chunks are filtered out: that is the risk.
"""

import re
from functools import lru_cache

import common

ARTICLES = {
    "01": "VPN Access Guide",
    "02": "Password and Account Security",
    "03": "Printer Setup and Issues",
    "04": "Laptop Performance and Updates",
    "05": "Collaboration Tools: Teams, Outlook, and Shared Drives",
    "06": "Software Requests and Policy",
}
AREA_WORDS = {
    "01": ["vpn"],
    "02": ["password", "passwords", "mfa", "phishing"],
    "03": ["printer", "print", "prints"],
    "05": ["teams", "outlook", "mailbox", "shared drive", "smb"],
    "06": ["software", "licence", "extension"],
}


def named_area(question):
    """The one article a question names, or None (names no area, or more than one)."""
    text = question.lower()
    found = {a for a, words in AREA_WORDS.items()
             if any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in words)}
    return found.pop() if len(found) == 1 else None


@lru_cache(maxsize=None)
def sources_of(article, collection=common.BASELINE):
    """Every source file of that article in the collection (the .md and its HTML/PDF/TXT copies)."""
    return tuple(sorted({c["metadata"]["source"] for c in common.all_chunks(collection)
                         if c["metadata"]["source"].split("/")[-1].startswith(article)}))


def guess_article(question):
    listing = "\n".join(f"{num}: {title}" for num, title in ARTICLES.items())
    answer = common.chat(
        "Which help article answers this IT helpdesk question? Reply with the two-digit number only.\n\n"
        f"Articles:\n{listing}\n\nQuestion: {question}", purpose="prefilter_article_guess")
    match = re.search(r"\b0[1-6]\b", answer)
    return match.group() if match else None


def filtered_search(question, article, k, collection=common.BASELINE):
    vector = common.embed_query(question)
    if article is None:
        return common.query(collection, vector, k)          # no guess: plain dense
    return common.query(collection, vector, k, where={"source": {"$in": list(sources_of(article, collection))}})


def make_rule_prefilter(collection=common.BASELINE):
    def retrieve(question, k):
        return filtered_search(question, named_area(question), k, collection)
    retrieve.__name__ = "prefilter_rule"
    return retrieve


GUESSES = {}


def make_llm_prefilter(collection=common.BASELINE):
    def retrieve(question, k):
        GUESSES[question] = guess_article(question)
        return filtered_search(question, GUESSES[question], k, collection)
    retrieve.__name__ = "prefilter_llm"
    return retrieve
