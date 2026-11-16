# Retrieval Interview Bank

Answer each in your own words, two to four sentences. Where you have a number from your own
results this week, use it. Interviewers remember candidates who say "on my corpus, reranking
raised recall@3 from X to Y at a cost of Z ms".

## Fundamentals

**1. What is the difference between dense and sparse retrieval? Give one question each one wins.**

Dense retrieval finds chunks with similar meaning by turning question and chunk into embedding vectors.

sparse retrieval like bm25 scores chunks by words they share, and counting rare words as more.

sparse has an issue where it cant find the information if the words arent exactly the same, like "jet engine" and"fans running loudly"

**2. What does an embedding model do at query time versus at indexing time?**

at indexing time, it embeds every chunk once and stored vectors in vectorDB.

at query time, embeds user question in query mode, and vector is compared with stored ones. indexing is done before, query time is done at each question.

**3. Why do we chunk documents at all? What goes wrong with chunks that are too small? Too large?**

we chunk documents because whole articles are too long. if chunk is too small, then the answers are cut in half like chunks stopping at a middle of the sentence.

if its to large, theres many topics and too much irrelevant info that doesnt need to be grabbed.

**4. What is a vector database doing that a normal database cannot?**

vector db stores vectors and finds nearest ones with similarity.

normal database finds exact matches.

**5. Explain cosine similarity to someone who has not done linear algebra.**

cosine similarity measures the difference between arrows pointing in the same direction including distance and length.

## Metrics

**6. Define recall@k, MRR, and nDCG. When would you report each?**

recall@k is relevant sections that appear in the top k. report this when model reads all K chunks.

MRR is 1/rank of first correct result. report when top result matters most

nDCG puts most relevant results highest, using graded relevance. report when caring about the order.

recall@k in my results was the best, having 1.000

**7. Why is hit@1 a bad metric for a RAG system that passes 5 chunks to the model?**

hit@1 counts it as a failure even though there was a hit later. Model reads all 5 chunks and answer at rank 3, so hit@5 or recall@5 is better.

**8. How do you build an evaluation set when you have no user queries yet?**

build eval set by covering the different types: fact, procedure, exact tokens, or using irrelevant words. can make an eval set combining these and grade it.

**9. Your retrieval recall@5 is 0.9 but users say answers are wrong. What do you check next?**

check if other chunks contain the right answer, see if parts of the right answer are there. use groundedness judge check to mesasure if the model uses these chunks.

## Techniques

**10. What is BM25 and why does it still matter in 2026?**

BM25 is a formula to score keywords. chunks score higher when containing specific words like rare words. it still matters in 2026 because of cheap cost and is used together with dense for hybrid.

**11. Explain reciprocal rank fusion. Why rank-based rather than score-based?**

RRF merges ranked lists and sorts the totals. Ranks are used because dense and bm25 are different scoring scales. rank based uses the positions of where each chunk ranked in list instead of using scores of the chunks.

**12. What is a cross-encoder and why can it not replace the first-stage retriever?**

its a reranker that reads the question and chunk and scores how well the answer is. its slow when passing through a model for running on a chunk each time, so we rerank a small pool. it cant replace because its more accurate than comparing 2 seperate vectors.

**13. How do you choose the candidate pool size before reranking?**

measure recall and pool sizes and pick knee.

**14. What is multi-query retrieval and what does it cost?**

LLM writes several rephrasings of the question, can be different wordings. costs an extra LLM call per question.

**15. Explain HyDE. When does it backfire?**

HyDE asks LLM to write hypothetical answer and searches answers embeding. it backfires when LLM makes wrong details like error code is different.

**16. What is parent-document (small-to-big) retrieval and what problem does it solve?**

search small chunks but return larger parent section. it solves tradeoff between small chunks that match well and large chunks that contian whole answer. markdown_header chunks are whole sections so it didnt help me much.

**17. What is MMR and when would you turn it on?**

maximal marginal relevance picks results one at a time, choosing chunk that is different from already picked chunks and is relevant info. when answer is near the same, this is turned on to get different answers.

**18. When does metadata filtering help, and how can it hurt recall?**

it helps when you know right subset like to search for vpn article for a vpn question. hurts when filter is wrong.

**19. What is contextual compression and what does it trade away?**

after retrieval llm keeps only relevant sentences, it trades away latency and cost.

## Design and production

**20. Walk me through your production retrieval pipeline and the metric gain from each stage.**

question is embedded in query mode, hybrid search ranks every chunk by .6 times density similarity and .4times bm25 score. over markdown_headers chunks, and top 5 are returned with their source and section. no reranker and no llm step. dense alone as 0.999 and recall@5 is 1.000, the scores are high. every stage after that increased latency and didnt improve score.

**21. Your ablation showed removing the reranker cost the most. Why might that be true on this corpus and false on another? on mine its the opposite, removing reranker made results slightly better from 0.996 to 0.999, and 100x faster. on a larger corpus with many similar documents, first stage would rank the right chunk lower more often.**

**22. A stakeholder wants k=20 because "more context is better". What do you say?**

on my data recall@5 is already 1.00 so the answer is in the top 5 for every question, k=20 adds no new answers, only 15 more chunks of more noise.

**23. How do you keep retrieval quality from regressing when someone edits the system prompt or swaps the embedding model?**

use same eval set and rerun at every change and compare against saved baseline numbers, rerun tools and langsmith.

**24. How would you tell, from a single LangSmith trace, whether a bad answer came from retrieval or from the model?**

see if right section isnt in the search step in langsmith trace, then itd be a retrieval problem. if its there but wrong answer then its from the model.

**25. If you had one more week and a GPU, what would you do to improve retrieval further, and how would you measure it? (The answer should mention fine-tuning the embedding model on domain pairs. That is the next segment.)**

could make a new eval set, my original scores were close to perfect with 1.000 on most scores, not much room for improvement, so seeing a different eval set with lower scores and trying to increase them would help improve retrieval further with results.
