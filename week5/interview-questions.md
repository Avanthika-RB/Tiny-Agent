# Retrieval Interview Bank

Answer each in your own words, two to four sentences. Where you have a number from your own
results this week, use it. Interviewers remember candidates who say "on my corpus, reranking
raised recall@3 from X to Y at a cost of Z ms".

## Fundamentals
1. What is the difference between dense and sparse retrieval? Give one question each one wins.
2. What does an embedding model do at query time versus at indexing time?
3. Why do we chunk documents at all? What goes wrong with chunks that are too small? Too large?
4. What is a vector database doing that a normal database cannot?
5. Explain cosine similarity to someone who has not done linear algebra.

## Metrics
6. Define recall@k, MRR, and nDCG. When would you report each?
7. Why is hit@1 a bad metric for a RAG system that passes 5 chunks to the model?
8. How do you build an evaluation set when you have no user queries yet?
9. Your retrieval recall@5 is 0.9 but users say answers are wrong. What do you check next?

## Techniques
10. What is BM25 and why does it still matter in 2026?
11. Explain reciprocal rank fusion. Why rank-based rather than score-based?
12. What is a cross-encoder and why can it not replace the first-stage retriever?
13. How do you choose the candidate pool size before reranking?
14. What is multi-query retrieval and what does it cost?
15. Explain HyDE. When does it backfire?
16. What is parent-document (small-to-big) retrieval and what problem does it solve?
17. What is MMR and when would you turn it on?
18. When does metadata filtering help, and how can it hurt recall?
19. What is contextual compression and what does it trade away?

## Design and production
20. Walk me through your production retrieval pipeline and the metric gain from each stage.
21. Your ablation showed removing the reranker cost the most. Why might that be true on this corpus
    and false on another?
22. A stakeholder wants k=20 because "more context is better". What do you say?
23. How do you keep retrieval quality from regressing when someone edits the system prompt or
    swaps the embedding model?
24. How would you tell, from a single LangSmith trace, whether a bad answer came from retrieval or
    from the model?
25. If you had one more week and a GPU, what would you do to improve retrieval further, and how
    would you measure it? (The answer should mention fine-tuning the embedding model on domain
    pairs. That is the next segment.)
