# Results

All numbers on the 35-question eval set, same collection, same embedding model, unless noted.

## Day 1: Baseline per Week 4 collection (dense only)
| Collection | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
| fixed_200 | 1.000 | 1.000 | 1.000 | 0.992 | 2.2 | 3.2 |
| fixed_500_overlap | 1.000 | 1.000 | 1.000 | 0.999 | 1.8 | 2.2 |
| recursive_500 | 1.000 | 1.000 | 1.000 | 0.998 | 1.6 | 2.2 |
| markdown_headers | 1.000 | 1.000 | 1.000 | 0.999 | 1.3 | 1.8 |
| markdown_headers_noprefix | 1.000 | 1.000 | 1.000 | 0.996 | 1.4 | 2.0 |
| semantic | 1.000 | 1.000 | 0.981 | 0.992 | 1.5 | 2.2 |
Chosen baseline: markdown_headers 

## Day 2: Sparse, hybrid, filter, MMR
| Technique | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms | Wins on (kind) |
|---|---|---|---|---|---|---|---|
| Baseline dense | 1.000 | 1.000 | 1.000 | 0.999 | 1.4 | 1.6 | - |
| BM25 | 0.914 | 0.971 | 0.914 | 0.923 | 0.1 | 0.2 | - |
| Hybrid RRF k=60 | 0.971 | 0.971 | 0.957 | 0.961 | 3.3 | 4.1 | - |
| Hybrid alpha=0.3 | 0.971 | 1.000 | 0.964 | 0.969 | 3.2 | 4.0 | - |
| Hybrid alpha=0.5 | 1.000 | 1.000 | 0.971 | 0.977 | 3.0 | 3.3 | - |
| Hybrid alpha=0.7 | 1.000 | 1.000 | 1.000 | 1.000 | 3.1 | 3.6 | - |
| MMR lambda=0.5 | 1.000 | 0.886 | 1.000 | 0.945 | 101.2 | 117.7 | - |
| Dense + LLM-guessed article filter (all 35) | 0.914 | 0.943 | 0.914 | 0.935 | 2179.8 | 4689.7 | - |
| Dense, named-area questions only (25 q) | 1.000 | 1.000 | 1.000 | 0.998 | 1.7 | 2.3 |  |
| Dense + prefilter by named area (25 q) | 1.000 | 1.000 | 1.000 | 0.998 | 1.9 | 2.4 |  |

"Wins on": the kinds where this technique alone has the best nDCG@5 (ties broken by MRR). A kind where several techniques share the best score has no winner.

## Day 3: Rerank and query transforms
| Technique | hit@3 | recall@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms | Extra LLM calls / q | Reranker calls / q |
|---|---|---|---|---|---|---|---|---|---|
| Day 2 winner (hybrid alpha=0.7) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 4.4 | 6.5 | 0 | 0 |
| + rerank, pool 10, top 3 | 1.000 | 0.986 | 0.986 | 1.000 | 0.992 | 339.8 | 853.8 | 0 | 1 |
| + rerank, pool 20, top 3 | 1.000 | 0.986 | 0.986 | 1.000 | 0.992 | 388.9 | 478.1 | 0 | 1 |
| + rerank, pool 40, top 3 | 1.000 | 0.986 | 0.986 | 1.000 | 0.992 | 785.8 | 810.1 | 0 | 1 |
| + rerank, pool 20, top 5 | 1.000 | 0.986 | 1.000 | 1.000 | 0.996 | 396.1 | 420.3 | 0 | 1 |
| Multi-query (3) + RRF | 1.000 | 1.000 | 1.000 | 1.000 | 0.999 | 4158.9 | 7720.5 | 1 | 0 |
| HyDE | 1.000 | 0.986 | 0.986 | 0.986 | 0.986 | 3951.5 | 8448.1 | 1 | 0 |
| Rewrite / step-back | 1.000 | 0.986 | 1.000 | 0.971 | 0.982 | 4593.7 | 16443.7 | 1 | 0 |

A "top 3" reranker returns only 3 chunks, so its recall@5 is the same as its recall@3.

## Day 4: Small-to-big, grid, ablation
### Parent-document (all 35 questions) day4_parent.md
| Technique | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
| Dense on markdown_headers (baseline) | 1.000 | 1.000 | 1.000 | 0.999 | 1.4 | 2.0 |
| Day 2 winner: hybrid alpha 0.7 on markdown_headers | 1.000 | 1.000 | 1.000 | 1.000 | 3.1 | 4.3 |
| Dense on fixed_200 (small chunks, returned as they are) | 1.000 | 1.000 | 1.000 | 0.992 | 2.1 | 3.1 |
| Parent-document: dense on fixed_200, return the parent section | 1.000 | 1.000 | 0.981 | 0.979 | 3.1 | 4.4 |
| Parent-document with hybrid alpha 0.7 | 1.000 | 1.000 | 0.938 | 0.949 | 5.3 | 7.0 |

### Grid and production (30 tuning questions) day4_tuning.md
| Config | hit@3 | recall@5 | MRR | nDCG@5 | held-out nDCG@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|
| Grid run 1: alpha 0.4, pool 10, rerank to 3 | 1.000 | 0.983 | 1.000 | 0.990 | 1.000 | 340.2 | 870.1 |
| Grid run 2: alpha 0.4, pool 10, rerank to 5 | 1.000 | 1.000 | 1.000 | 0.996 | 1.000 | 336.0 | 486.4 |
| Grid run 3: alpha 0.6, pool 10, rerank to 3 | 1.000 | 0.983 | 1.000 | 0.990 | 1.000 | 336.4 | 346.0 |
| Grid run 4: alpha 0.6, pool 10, rerank to 5 | 1.000 | 1.000 | 1.000 | 0.996 | 1.000 | 333.9 | 353.9 |
| Grid run 5: alpha 0.4, pool 20, rerank to 3 | 1.000 | 0.983 | 1.000 | 0.990 | 1.000 | 384.6 | 413.0 |
| Grid run 6: alpha 0.4, pool 20, rerank to 5 | 1.000 | 1.000 | 1.000 | 0.996 | 1.000 | 390.7 | 454.0 |
| Grid run 7: alpha 0.6, pool 20, rerank to 3 | 1.000 | 0.983 | 1.000 | 0.990 | 1.000 | 388.7 | 408.1 |
| Grid run 8: alpha 0.6, pool 20, rerank to 5 | 1.000 | 1.000 | 1.000 | 0.996 | 1.000 | 387.2 | 404.4 |
| PRODUCTION: alpha 0.6, top 5, no rerank | 1.000 | 1.000 | 1.000 | 0.998 | 3.5 |

Production is hybrid search (0.6 dense + 0.4 BM25) returning the top 5, with no reranker. It scores recall@5 1.000 and nDCG@5 0.998 on the 30 tuning questions and 1.000 on my 5 held-out questions, at 3.5 ms p50. The best grid run with a reranker scored slightly lower (0.996) and took 334 ms, about 100 times slower for no gain, so the reranker isn’t worth its cost on this small knowledge base.

### Ablation day4_tuning.md
Each row switches ONE component. "minus" = production has it and it was removed; "plus" = production does not have it and it was added. Delta = this row minus production. The ablation starts from the grid winner (with the reranker). Removing the reranker gave the best result, which is why production has no reranker.

| Production ... | recall@5 | delta | nDCG@5 | delta | MRR | delta | p50 ms |
|---|---|---|---|---|---|---|---|
| (production itself) | 1.000 | | 0.996 | | 1.000 | | 333.9 |
| minus BM25 | 1.000 | +0.000 | 0.996 | +0.000 | 1.000 | +0.000 | 331.7 |
| minus Reranker | 1.000 | +0.000 | 0.999 | +0.002 | 1.000 | +0.000 | 3.5 |
| plus Multi-query | 1.000 | +0.000 | 0.996 | +0.000 | 1.000 | +0.000 | 4826.3 |
| plus Parent-document | 1.000 | +0.000 | 0.995 | -0.001 | 1.000 | +0.000 | 341.4 |

## Day 5: Failure categories on production config
| qid | Question | Category (chunking / embedding / query / missing data / metric) | Note |
|---|---|---|---|
