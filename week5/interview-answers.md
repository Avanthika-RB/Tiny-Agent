# Retrieval interview bank: my answers

Numbers are from my own Week 5 results (`results/`), on 6 help articles and a 35-question eval set.

## Fundamentals

**1. What is the difference between dense and sparse retrieval? Give one question each one wins.**
Dense retrieval turns the question and each chunk into embedding vectors and finds chunks with similar *meaning*. Sparse retrieval (BM25) scores chunks by the *words* they share with the question, with rare words counting more. Dense wins paraphrases: for "my laptop sounds like a jet engine", dense ranked the "Fans running constantly" section 1st, while BM25 didn't have it in the top 5, because the article says "fans run loud". Sparse should win exact tokens such as an error code (1103) or a printer name (AUS-02-03). On my corpus dense already got those right, so BM25 scored lower overall (nDCG@5 0.923 vs 0.999).

**2. What does an embedding model do at query time versus at indexing time?**
At indexing time it embeds every chunk once, in passage mode, and the vectors are stored in the vector database. At query time it embeds only the user's question, in query mode, and that vector is compared with the stored ones. Indexing is done once ahead of time; query time happens on every question, so it costs latency (about 271 ms per question for me, which is why I cache question vectors in the eval).

**3. Why do we chunk documents at all? What goes wrong with chunks that are too small? Too large?**
Whole articles are too long to embed precisely and too long to pass to the model, and one vector for a whole article blurs many topics together. Chunks that are too small cut answers in half: in Week 4, 200-character chunks split the India VPN gateway row between "vpn-in" and ".example.com", and fixed_200 scored only 6/10 there. Chunks that are too large mix several topics, so the vector matches loosely and the model reads a lot of irrelevant text.

**4. What is a vector database doing that a normal database cannot?**
It stores vectors and finds the *nearest* ones to a query vector by similarity, using an index (HNSW in Chroma) so it doesn't compare against every row. A normal database finds exact matches, like "email = x", not "closest in meaning". Chroma also stores each chunk's text and metadata, so I can filter (for example by source article) and return the text with the match.

**5. Explain cosine similarity to someone who has not done linear algebra.**
Think of each sentence as an arrow pointing in some direction in a space of meanings. Cosine similarity measures how much two arrows point the same way: 1 means the same direction (same meaning), 0 means unrelated. It ignores how long the arrows are and only looks at direction, which is why a short and a long text about the same thing can still match.

## Metrics

**6. Define recall@k, MRR, and nDCG. When would you report each?**
Recall@k is the share of the relevant sections that appear in the top k. MRR is 1 divided by the rank of the first correct result (rank 1 gives 1.0, rank 2 gives 0.5). nDCG rewards putting the most relevant results highest, using graded relevance (an answering section counts more than a related one). Report recall@k when the model reads all k chunks (did the answer get in at all?), MRR when the top result matters most, and nDCG when you have graded labels and care about order. On my data recall@5 was 1.000 almost everywhere, so nDCG@5 was the only metric that separated techniques.

**7. Why is hit@1 a bad metric for a RAG system that passes 5 chunks to the model?**
The model reads all 5 chunks, so an answer at rank 3 is just as usable as one at rank 1. hit@1 would count it as a failure, and you might "fix" something that works and pick the wrong technique. hit@5 or recall@5 measures what the model actually sees.

**8. How do you build an evaluation set when you have no user queries yet?**
Write questions from the documents themselves, covering different kinds: facts, procedures, questions that need context, exact tokens (codes, names) and paraphrases that use none of the article's words. For each one, label the gold section(s) with a grade (2 = answers it, 1 = related) and the expected answer. Keep a few questions held out that you never tune on: I added 5 of my own and reported them separately from the 30 I tuned on.

**9. Your retrieval recall@5 is 0.9 but users say answers are wrong. What do you check next?**
First check whether the right chunk contains the *full* answer, or only part of it (for Aisha, the macOS smb table came back without the "Finder, Go, Connect to Server" sentence). Then check the generation step: did the model use the chunk, or ignore it and invent something? That's what a groundedness judge measures. Also check whether the eval questions look like real user questions, since a high score on an easy eval set (mine was about 1.000) can hide real failures.

## Techniques

**10. What is BM25 and why does it still matter in 2026?**
BM25 is a keyword scoring formula: chunks score higher when they contain the question's words, especially rare words, with a correction for long chunks. It still matters because embeddings can blur exact tokens (error codes, product names, file paths), and BM25 is extremely cheap: 0.1 ms per question in my runs vs 1.4 ms for dense. It's usually used together with dense search as a hybrid.

**11. Explain reciprocal rank fusion. Why rank-based rather than score-based?**
RRF merges several ranked lists: each chunk gets 1 / (60 + its rank) from each list, and the totals are sorted. It uses ranks because dense similarity and BM25 scores are on completely different scales (about 0.2 to 0.8 vs 0 to 15), so adding raw scores would let one method dominate. On my data, though, the score-based weighted hybrid with alpha 0.7 (nDCG@5 1.000) beat RRF (0.961), because I normalised the scores first and could weight the stronger method more.

**12. What is a cross-encoder and why can it not replace the first-stage retriever?**
A cross-encoder (a reranker) reads the question and a chunk *together* and scores how well the chunk answers it, which is more precise than comparing two separate vectors. But it needs one model pass per (question, chunk) pair and can't use a pre-built index, so running it on every chunk would be far too slow. That's why it only reranks a small pool from a fast first stage: mine took 340 ms for a pool of 10 and 786 ms for 40, against 3.5 ms for the first stage alone.

**13. How do you choose the candidate pool size before reranking?**
Measure recall and latency for several pool sizes and pick the knee: the smallest pool where recall stops improving. In my sweep, pools 10, 20 and 40 all gave recall@3 0.986 while latency went 340, 389, 786 ms, so the knee was at 10 or below. Bigger pools only help if the first stage often ranks the right chunk lower than the pool cut-off.

**14. What is multi-query retrieval and what does it cost?**
An LLM writes several rephrasings of the question, you search with each, and fuse the result lists (I used the original plus 3 rephrasings, fused with RRF). Different wordings can reach chunks that one wording misses. It costs one extra LLM call per question: my p50 went from 4.4 ms to about 4,159 ms, and nDCG@5 stayed the same (0.999 vs 1.000), so it wasn't worth it here.

**15. Explain HyDE. When does it backfire?**
HyDE asks the LLM to write a hypothetical answer and searches with that answer's embedding, because an answer looks more like the chunk that holds it than a question does. It backfires when the LLM invents the wrong details: for "what error code appears…", it wrote "0x80070005" instead of the real 1103, and nDCG@5 for that question dropped to 0.760. Overall HyDE scored 0.986 vs 1.000 for plain hybrid.

**16. What is parent-document (small-to-big) retrieval and what problem does it solve?**
You search small chunks (precise, because each is about one thing) but return the larger parent section they came from (complete, with every step of a procedure). It solves the trade-off between small chunks that match well and large chunks that contain the whole answer. On my corpus it didn't help (0.987 vs 0.996 on procedure and context questions) because my markdown_headers chunks are already whole sections.

**17. What is MMR and when would you turn it on?**
Maximal marginal relevance picks results one at a time, each time choosing a chunk that is relevant but different from the ones already picked. Turn it on when the top results are near-duplicates, like the markdown and PDF copies of my printer article taking two slots. On my data it hurt (nDCG@5 0.945 vs 0.999) because it pushed out relevant chunks just to be different, and it took 101 ms.

**18. When does metadata filtering help, and how can it hurt recall?**
It helps when you know the right subset for sure, like searching only the VPN article for a VPN question, which removes distractors and is cheap. It hurts when the filter is wrong, because the right chunk is removed entirely. When an LLM guessed the article, it was wrong on 3 of 35 questions that mention two topics (for example "Outlook keeps asking for my password", which it sent to the password article), and nDCG@5 dropped from 0.999 to 0.935.

**19. What is contextual compression and what does it trade away?**
After retrieval, an LLM keeps only the sentences relevant to the question, so the model reads less text and less noise. It trades away latency and cost (one extra LLM call per question) and risks dropping a sentence that mattered. In my test the context shrank by 85% (19,647 to 2,870 characters) and answer quality stayed the same: 19/20 with full chunks and 19/20 compressed.

## Design and production

**20. Walk me through your production retrieval pipeline and the metric gain from each stage.**
The question is embedded in query mode, then hybrid search ranks every chunk by 0.6 times the dense similarity plus 0.4 times the BM25 score (each normalised to 0 to 1), over the markdown_headers chunks, and the top 5 are returned with their source and section. There's no reranker and no LLM step. The honest gains are small, because dense alone was already 0.999 nDCG@5: hybrid kept recall@5 at 1.000 and scored 0.998 on the tuning set and 1.000 on my held-out questions at 3.5 ms. Every extra stage I tried (reranker, multi-query, HyDE, parent-document) added latency without improving the score.

**21. Your ablation showed removing the reranker cost the most. Why might that be true on this corpus and false on another?**
On my corpus the opposite happened: removing the reranker made results slightly better (0.999 vs 0.996) and 100 times faster, because the first stage already put the right section at rank 1. On a larger corpus with many similar documents, the first stage would rank the right chunk lower more often, and a cross-encoder that reads question and chunk together would earn its cost. The value of a component depends on how much room the earlier stages leave.

**22. A stakeholder wants k=20 because "more context is better". What do you say?**
On my data recall@5 is already 1.000, so the answer is in the top 5 for every question, and k=20 adds no new answers, only 15 more chunks of noise. More context also costs tokens, slows the model, and gives it more irrelevant text to be misled by: the agent suggested an irrelevant "Licences" chunk for a stolen laptop when nothing relevant existed. Compression showed the model answered just as well with 85% less text (19/20 both ways), so less context is not hurting answers.

**23. How do you keep retrieval quality from regressing when someone edits the system prompt or swaps the embedding model?**
Keep the eval set and harness as a regression test and rerun it on every change: the same 35 questions, the same matching function, compared against the saved baseline numbers. For the agent, rerun the LangSmith experiments (tool order, retrieval hit, groundedness) and compare them with the previous experiment. An embedding model change also requires re-embedding every chunk; my pipeline records the model in each collection and refuses to mix models.

**24. How would you tell, from a single LangSmith trace, whether a bad answer came from retrieval or from the model?**
Open the search step and read what it returned. If the right section isn't there, it's a retrieval problem. If the right section is there but the answer says something different or extra, the model ignored or misused it, which is a generation problem. In my traces, the search step shows the KB chunks with source and section, so you can check this directly.

**25. If you had one more week and a GPU, what would you do to improve retrieval further, and how would you measure it?**
First make the eval set harder and match at the answer level, because on my current set everything scores about 1.000 and no improvement could show. Then fine-tune the embedding model on domain pairs (helpdesk questions paired with the sections that answer them), so it learns company-specific vocabulary like gateway names and drive paths. I'd measure it with the same harness: recall@5 and nDCG@5 on the held-out questions, before and after fine-tuning, plus latency.
