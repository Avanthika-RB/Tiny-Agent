# Day 4: grid, production config, ablation

Made by `python rag/tune.py`. Tuning metrics are on the 30 provided questions (what the choice is based on); held-out = my 5 added questions, never used to choose. Latency is over all 35.

## Grid (8 runs)

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

Best on the tuning questions: run 4 (alpha 0.6, pool 10, rerank to 5).

## Parent-document on top of the best grid config

| Config | hit@3 | recall@5 | MRR | nDCG@5 | held-out nDCG@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|
| Run 4 | 1.000 | 1.000 | 1.000 | 0.996 | 1.000 | 333.9 | 353.9 |
| Run 4 + parent-document | 1.000 | 1.000 | 1.000 | 0.994 | 1.000 | 334.8 | 345.8 |

Parent-document is NOT in the production config (it did not score higher on the tuning questions).

## PRODUCTION

| Config | hit@3 | recall@5 | MRR | nDCG@5 | held-out nDCG@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|
| PRODUCTION: alpha 0.6, pool 10, rerank to 5 | 1.000 | 1.000 | 1.000 | 0.996 | 1.000 | 333.9 | 353.9 |

Saved to results/production.json: `{"alpha": 0.6, "k_candidates": 10, "top_n": 5, "rerank": true, "multi_query": false, "parent": false}`

## Ablation (all 35 questions)

Each row switches ONE component. "minus" = production has it and it was removed; "plus" = production does not have it and it was added. Delta = this row minus production.

| Production ... | recall@5 | delta | nDCG@5 | delta | MRR | delta | p50 ms |
|---|---|---|---|---|---|---|---|
| (production itself) | 1.000 | | 0.996 | | 1.000 | | 333.9 |
| minus BM25 | 1.000 | +0.000 | 0.996 | +0.000 | 1.000 | +0.000 | 331.7 |
| minus Reranker | 1.000 | +0.000 | 0.999 | +0.002 | 1.000 | +0.000 | 3.5 |
| plus Multi-query | 1.000 | +0.000 | 0.996 | +0.000 | 1.000 | +0.000 | 4826.3 |
| plus Parent-document | 1.000 | +0.000 | 0.995 | -0.001 | 1.000 | +0.000 | 341.4 |

## FINAL PRODUCTION (reranker dropped)

Without the reranker the tuning score is the same or better and latency falls from 334 ms to 3.5 ms, so the reranker is removed.

| Config | hit@3 | recall@5 | MRR | nDCG@5 | held-out nDCG@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|
| FINAL PRODUCTION: alpha 0.6, top 5, no rerank | 1.000 | 1.000 | 1.000 | 0.998 | 1.000 | 3.5 | 4.5 |

Saved to results/production.json: `{"alpha": 0.6, "k_candidates": 10, "top_n": 5, "rerank": false, "multi_query": false, "parent": false}`
