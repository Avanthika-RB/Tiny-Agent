"""Day 3: query transformation. The chat model changes the QUERY before searching; the search
itself is the Day 2 winner. Each technique costs one extra LLM call per question.

  multi-query  3 rephrasings of the question; search the original and each rephrasing; fuse the
               4 rankings with RRF (k=60). Different wordings can reach chunks one wording misses.
  HyDE         the model writes a HYPOTHETICAL answer paragraph; that paragraph is embedded (passage
               mode, because it is written like a passage) and searched instead of the question.
               An answer looks more like the chunk that holds it than a question does, but if the
               model invents the wrong answer it can pull the search to the wrong section.
  rewrite      the model rewrites the question into a clean, slightly more general search query
               (step-back), and that is searched instead.

Every prompt and answer goes to results/llm_log.jsonl (gotcha 4), and the outputs are kept in
GENERATED for the Day 3 report. Temperature 0 (set in common.chat).
"""

import re

import common
from retrievers.hybrid import rrf

GENERATED = {"multi_query": {}, "hyde": {}, "rewrite": {}}


def rephrasings(question):
    answer = common.chat(
        "Write 3 different rephrasings of this IT helpdesk question, using different words where you can. "
        "One per line, no numbering, nothing else.\n\n"
        f"Question: {question}", purpose="multi_query")
    lines = [re.sub(r"^\s*(\d+[.)]|[-*])\s*", "", line).strip() for line in answer.splitlines()]
    result = [line for line in lines if line][:3]
    GENERATED["multi_query"][question] = result
    return result


def hypothetical_answer(question):
    answer = common.chat(
        "Write a short paragraph (3 to 4 sentences) that could appear in a company IT help article and "
        "answers this question. Write it as the article would, not as a chat reply.\n\n"
        f"Question: {question}", purpose="hyde")
    GENERATED["hyde"][question] = answer
    return answer


def rewritten(question):
    answer = common.chat(
        "Rewrite this IT helpdesk question as a short search query for the company's help articles. "
        "Remove chatty words, keep product names, codes and error messages, and use the general topic "
        "if the question is very specific. Reply with the query only.\n\n"
        f"Question: {question}", purpose="rewrite")
    query = answer.strip().strip('"').splitlines()[0] if answer.strip() else question
    GENERATED["rewrite"][question] = query
    return query


def make_multi_query(ranking):
    """ranking(text) -> every chunk best first (the Day 2 winner)."""
    def retrieve(question, k):
        queries = [question] + rephrasings(question)
        return rrf([ranking(q) for q in queries])[:k]
    retrieve.__name__ = "multi_query"
    return retrieve


def make_hyde(ranking_with_vector):
    """ranking_with_vector(text, vector) -> every chunk best first. The dense part uses the
    hypothetical answer's vector; the BM25 part uses the hypothetical answer's words."""
    def retrieve(question, k):
        paragraph = hypothetical_answer(question)
        return ranking_with_vector(paragraph, common.embed_passage(paragraph))[:k]
    retrieve.__name__ = "hyde"
    return retrieve


def make_rewrite(ranking):
    def retrieve(question, k):
        return ranking(rewritten(question))[:k]
    retrieve.__name__ = "rewrite"
    return retrieve
