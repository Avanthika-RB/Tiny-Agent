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
| Technique | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | Wins on (kind) |
|---|---|---|---|---|---|---|
| Baseline dense | | | | | | |
| BM25 | | | | | | |
| Hybrid RRF k=60 | | | | | | |
| Hybrid alpha=0.3 | | | | | | |
| Hybrid alpha=0.5 | | | | | | |
| Hybrid alpha=0.7 | | | | | | |
| Dense + metadata prefilter (6 q only) | | | | | | |
| MMR lambda=0.5 | | | | | | |

## Day 3: Rerank and query transforms
| Technique | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | Extra LLM calls / q |
|---|---|---|---|---|---|---|
| Day 2 winner | | | | | | 0 |
| + rerank, pool 10, top 3 | | | | | | 0 |
| + rerank, pool 20, top 3 | | | | | | 0 |
| + rerank, pool 40, top 3 | | | | | | 0 |
| Multi-query (3) + RRF | | | | | | 1 |
| HyDE | | | | | | 1 |
| Rewrite / step-back | | | | | | 1 |

## Day 4: Small-to-big, grid, ablation
| Config | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms |
|---|---|---|---|---|---|
| Parent-document | | | | | |
| Grid run 1..8 | | | | | |
| PRODUCTION | | | | | |

| Ablation: production minus ... | recall@5 | delta |
|---|---|---|
| BM25 | | |
| Reranker | | |
| Multi-query | | |
| Parent-document | | |

## Day 5: Failure categories on production config
| qid | Question | Category (chunking / embedding / query / missing data / metric) | Note |
|---|---|---|---|
