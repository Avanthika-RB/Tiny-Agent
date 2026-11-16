# Retrieval design: IT helpdesk knowledge base

**Decision:** production retrieval is **hybrid search (0.6 dense + 0.4 BM25) over the `markdown_headers` chunks, top 5, no reranker, no LLM calls.** It scores nDCG@5 0.999 and recall@5 1.000 on all 35 eval questions at 3.5 ms p50. It is the backend of `search_known_issues` in the helpdesk agent (`week3/helpdesk_graph/graph_v5.py`).

## 1. Setup

| | |
|---|---|
| Corpus | 6 help articles in `week4/kb` (VPN, passwords, printers, laptops, Teams/Outlook/shared drives, software), plus HTML, PDF and TXT copies of two of them |
| Chunks | the six Week 4 collections in `week4/chroma_db`. Production uses `markdown_headers`: one chunk per section, header path written at the top |
| Embeddings | `nvidia/nemotron-3.5-embed-1b`, query mode for questions, passage mode for chunks. Question vectors cached in `week5/rag/cache` |
| Eval set | `eval_set.jsonl`: 35 questions with graded gold sections (2 = answers it, 1 = related). The 30 provided are the **tuning set**; my 5 added (q31 to q35) are **held out** and never used to choose |
| Matching | `rag/matching.py`: a chunk is a hit if it is from the gold article and its header path contains the gold section, or (chunks with no header path) it shares 50 or more characters with the section's text |
| Metrics | `rag/metrics.py`: hit@3, recall@5, MRR, nDCG@5 (graded), p50 and p95 latency of the whole retrieve call |

## 2. Baseline (Day 1): dense search on each Week 4 collection

Every collection scored hit@3 and recall@5 1.000. nDCG@5 ranged from 0.992 (fixed_200, semantic) to 0.999 (fixed_500_overlap, markdown_headers). **Chosen baseline: `markdown_headers`** (nDCG@5 0.999, p50 1.3 ms): it ties for the best score, it is the fastest, and its chunks are whole sections with header metadata.

The baseline is already near perfect: 6 short articles on clearly different topics are easy to tell apart. This is the most important fact for reading everything below. Hit and recall cannot go up, so techniques can only be told apart by nDCG, MRR, latency and cost.

## 3. Full comparison (all 35 questions)

| Technique | recall@5 | MRR | nDCG@5 | p50 ms | Extra calls per question |
|---|---|---|---|---|---|
| Dense (baseline) | 1.000 | 1.000 | 0.999 | 1.4 | none |
| BM25 | 0.971 | 0.914 | 0.923 | 0.1 | none |
| Hybrid RRF (k=60) | 0.971 | 0.957 | 0.961 | 3.3 | none |
| Hybrid alpha 0.3 / 0.5 / 0.7 | 1.000 | 0.964 / 0.971 / 1.000 | 0.969 / 0.977 / 1.000 | about 3 | none |
| MMR (lambda 0.5) | 0.886 | 1.000 | 0.945 | 101 | none |
| Dense + LLM-guessed article filter | 0.943 | 0.914 | 0.935 | 2180 | 1 LLM |
| Hybrid 0.7 + rerank, pool 10 / 20 / 40, top 3 | 0.986 | 1.000 | 0.992 | 340 / 389 / 786 | 1 reranker |
| Hybrid 0.7 + rerank, pool 20, top 5 | 1.000 | 1.000 | 0.996 | 396 | 1 reranker |
| Multi-query (3 rephrasings + RRF) | 1.000 | 1.000 | 0.999 | 4159 | 1 LLM |
| HyDE | 0.986 | 0.986 | 0.986 | 3952 | 1 LLM |
| Rewrite / step-back | 1.000 | 0.971 | 0.982 | 4594 | 1 LLM |
| Parent-document (search fixed_200, return the section) | 1.000 | 0.981 | 0.979 | 3.1 | none |
| Grid: hybrid + rerank, 8 runs (30 tuning q) | 0.983 to 1.000 | 1.000 | 0.990 to 0.996 | 334 to 391 | 1 reranker |
| **Production: hybrid 0.6, top 5, no rerank** | **1.000** | **1.000** | **0.999** (0.998 tuning, 1.000 held out) | **3.5** | **none** |

What the comparison showed:
- **BM25** loses on paraphrases ("jet engine" vs "fans run loud", "Bangalore" vs "India") and does not win exact-token questions, because dense already gets them right.
- **The reranker** never improved recall. Pool size 10, 20 and 40 gave the same recall@3, so the knee is at 10 or below.
- **HyDE** invented details (error code "0x80070005" instead of 1103) that pulled the search off course.
- **Rewrite** made q22 too general ("slow laptop") and found the wrong section first.
- **Parent-document**, "usually the biggest win", was refuted here: 0.987 vs 0.996 on procedure and context questions, because the `markdown_headers` chunks are already whole sections.
- **Contextual compression** kept answer quality the same (LLM judge 19/20 with and without) while cutting the context by 85%, for one extra LLM call per question.

## 4. Ablation (from the grid winner: hybrid 0.6, pool 10, rerank to 5)

| Change | recall@5 | nDCG@5 | p50 ms |
|---|---|---|---|
| Grid winner itself | 1.000 | 0.996 | 334 |
| minus BM25 | 1.000 | 0.996 | 332 |
| **minus reranker** | 1.000 | **0.999** | **3.5** |
| plus multi-query | 1.000 | 0.996 | 4826 |
| plus parent-document | 1.000 | 0.995 | 341 |

No removal hurt. Removing the reranker made results slightly better and about 100 times faster, which is why production has no reranker. On this corpus no single component is clearly "most valuable": plain dense search already does the job.

## 5. Latency and cost

| | p50 per question | Calls per question |
|---|---|---|
| Embed the question (once, then cached) | 271 ms | 1 embedding |
| Production search | 3.5 ms | none |
| + reranker | +330 to 780 ms | 1 reranker |
| + any LLM query transform | +about 4 s | 1 LLM |
| + compression | about 4 s | 1 LLM |

Production adds only the embedding call to each question, so the agent's speed is set by its chat model (about 11 to 12 s per helpdesk case), not by retrieval.

## 6. In the agent (Day 4)

`search_known_issues` now returns the 5 production chunks with source and section, in place of keyword matching over 10 known issues (`SEARCH_BACKEND=keyword` brings the old search back). LangSmith experiments on the 15 helpdesk cases, keyword vs RAG:

| | retrieval_hit | groundedness | tool_order | llm_judge |
|---|---|---|---|---|
| Keyword | 0.80 | 0.20 | 0.93 | 0.33 |
| RAG | **1.00** | **0.50** | 0.71 | 0.36 |

RAG finds better information. The tool_order drop is RAG giving a fix where the dataset expects a ticket: correct for Aisha on macOS, wrong for the stolen laptop (see section 7). Experiments: `v5-keyword-433717cd`, `v5-rag-e7e4cc62`, screenshot `results/Screenshot.png`.

## 7. Failure categories (details in failure-analysis.md)

| Category | Count | Example |
|---|---|---|
| Metric | 3 | The eval set is saturated; the groundedness judge scores ticket-only replies 0; case 7's expected outcome is out of date |
| Query | 1 | q9: "password" pulls the Phishing section to rank 2 |
| Missing data | 1 | Stolen laptop: no article, but the search still returns 5 chunks |
| Chunking | 1 | Aisha's macOS fix: the instruction sentence and the table are in different chunks |

## 8. Next steps

1. **A harder eval set and answer-level matching.** More cross-article and no-shared-words questions, and a hit only if the chunk contains the expected answer. Without this, no further technique can show a gain.
2. **A relevance cut-off.** Return nothing when the best score is low, so a question the articles don't cover leads to a ticket instead of an unrelated fix.
3. **Fix the groundedness rubric** and update case 7's expected outcome.
4. **Keep tables with their introducing sentence** when chunking.
5. **Revisit the reranker and parent-document on a larger corpus**, where the first stage is less precise and sections are longer.

## 9. How to rebuild this

From `week5`, with the Week 4 venv:

1. `python rag/evaluate.py check` checks the metrics and gold sections.
2. `python rag/evaluate.py baseline` runs Day 1.
3. `python rag/day2.py`, `python rag/day3.py` and `python rag/day4.py parent` run Days 2, 3 and 4.
4. `python rag/tune.py` runs the grid and ablation, and writes `results/production.json`.
5. `python rag/day4.py compress` runs the compression check.

The agent reads `results/production.json`, so a new production config needs no code change. All tables are in `results/`.
