# Week 5 Starter: Retrieval Pipeline

## What is here
- eval_set.jsonl / eval_set.md: 30 questions over your Week 4 knowledge base. Each has the gold
  article and section with a grade (2 = answers it, 1 = related), a kind, and the expected answer.
  Add 5 of your own on Day 1. Kinds are balanced on purpose: exact_token questions should favour
  BM25, paraphrase questions should favour dense, procedure and context should favour parent-document.
- interview-questions.md: 25 questions. You answer them on Day 5.
- results-template.md: the tables to fill.

## Tech stack
    pip install rank_bm25 langchain-classic langchain-community langsmith numpy

Reranker (hosted on build.nvidia.com, same key):

    from langchain_nvidia_ai_endpoints import NVIDIARerank
    reranker = NVIDIARerank(model="nvidia/llama-nemotron-rerank-1b-v2", top_n=3)
    reranker.compress_documents(documents=candidates, query=question)

If that name is not in the catalog, check https://build.nvidia.com/models?q=rerank for the current one.

BM25:

    from rank_bm25 import BM25Okapi
    tokenised = [tokenise(c.page_content) for c in chunks]
    bm25 = BM25Okapi(tokenised)
    scores = bm25.get_scores(tokenise(question))

LangChain retrievers you will meet: EnsembleRetriever (hybrid), MultiQueryRetriever,
ParentDocumentRetriever, ContextualCompressionRetriever. Build at least BM25 + RRF yourself in plain
Python before using EnsembleRetriever, so you know what it does.

## How a chunk matches gold
A retrieved chunk is a hit for a question if its metadata source article AND its header path (or the
section it came from) match a gold entry. For collections without header metadata (fixed_200 etc.),
match by checking whether the chunk text overlaps the gold section text by at least 50 characters.
Write this matching function once, on Day 1, and reuse it everywhere. Inconsistent matching is the
most common way people fool themselves with retrieval metrics.

## Hand-worked metric check (verify metrics.py against this)
Question with gold = {A (grade 2), B (grade 1)}. Retrieved ranked list = [C, A, D, B, E].
- hit@3 = 1 (A is in top 3)
- recall@3 = 1/2 = 0.5 (A found, B not, out of 2 relevant); recall@5 = 1.0
- MRR = 1/2 = 0.5 (first relevant at rank 2)
- DCG@5 = 2/log2(3) + 1/log2(5) = 1.2619 + 0.4307 = 1.6926
- IDCG@5 = 2/log2(2) + 1/log2(3) = 2 + 0.6309 = 2.6309
- nDCG@5 = 0.6433
If your code prints anything else, fix the code, not the example.

## Reciprocal rank fusion, the formula
score(doc) = sum over retrievers of 1 / (k + rank_in_that_retriever), k = 60, ranks start at 1.
Docs missing from a retriever contribute 0 from that retriever. Sort by score descending.

## Gotchas
1. Compare techniques on the SAME chunks. Build BM25 over the exact chunk texts in your baseline
   collection, not over the raw articles, or the comparison is meaningless.
2. Latency: time the whole retrieve call including the reranker and any LLM calls. Report p50 and
   p95, not the mean. One slow call hides in a mean.
3. The reranker has an input limit. Pass the chunk text, not the chunk plus header plus metadata dump.
4. Multi-query and HyDE depend on the chat model's output. Set temperature 0 and log the generated
   queries so a weird result is explainable.
5. Rate limits: 35 questions x several techniques x reranker calls adds up. Cache embeddings for the
   questions on Day 1 and reuse them all week.
6. Do not tune on the eval set and then report on the same eval set as if it were new. Hold out your
   own 5 added questions: tune on the 30, report both.
