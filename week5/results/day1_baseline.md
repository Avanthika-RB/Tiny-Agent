# Day 1: baseline, dense only, per Week 4 collection

Embedding model nvidia/nemotron-3.5-embed-1b. Top 5 chunks per question. Made by `python rag/evaluate.py baseline`.

## All 35 questions (template columns)

| Collection | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
| fixed_200 | 1.000 | 1.000 | 1.000 | 0.992 | 2.2 | 3.2 |
| fixed_500_overlap | 1.000 | 1.000 | 1.000 | 0.999 | 1.8 | 2.2 |
| recursive_500 | 1.000 | 1.000 | 1.000 | 0.998 | 1.6 | 2.2 |
| markdown_headers | 1.000 | 1.000 | 1.000 | 0.999 | 1.3 | 1.8 |
| markdown_headers_noprefix | 1.000 | 1.000 | 1.000 | 0.996 | 1.4 | 2.0 |
| semantic | 1.000 | 1.000 | 0.981 | 0.992 | 1.5 | 2.2 |

## The 30 provided questions (tuning set)

| Collection | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
| fixed_200 | 1.000 | 1.000 | 1.000 | 0.992 | 2.2 | 3.3 |
| fixed_500_overlap | 1.000 | 1.000 | 1.000 | 0.998 | 1.7 | 2.3 |
| recursive_500 | 1.000 | 1.000 | 1.000 | 0.997 | 1.6 | 2.2 |
| markdown_headers | 1.000 | 1.000 | 1.000 | 0.998 | 1.4 | 1.9 |
| markdown_headers_noprefix | 1.000 | 1.000 | 1.000 | 0.996 | 1.4 | 2.1 |
| semantic | 1.000 | 1.000 | 0.978 | 0.990 | 1.6 | 2.2 |

## My 5 added questions (held out)

| Collection | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
| fixed_200 | 1.000 | 1.000 | 1.000 | 0.990 | 2.0 | 2.4 |
| fixed_500_overlap | 1.000 | 1.000 | 1.000 | 1.000 | 1.8 | 1.9 |
| recursive_500 | 1.000 | 1.000 | 1.000 | 1.000 | 1.5 | 1.6 |
| markdown_headers | 1.000 | 1.000 | 1.000 | 1.000 | 1.3 | 1.4 |
| markdown_headers_noprefix | 1.000 | 1.000 | 1.000 | 1.000 | 1.2 | 1.3 |
| semantic | 1.000 | 1.000 | 1.000 | 1.000 | 1.5 | 2.2 |

## All metrics at k=3 and k=5 (all 35)

| Collection | hit@3 | hit@5 | recall@3 | recall@5 | MRR | nDCG@3 | nDCG@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| fixed_200 | 1.000 | 1.000 | 0.986 | 1.000 | 1.000 | 0.987 | 0.992 | 2.2 | 3.2 |
| fixed_500_overlap | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.999 | 0.999 | 1.8 | 2.2 |
| recursive_500 | 1.000 | 1.000 | 0.986 | 1.000 | 1.000 | 0.993 | 0.998 | 1.6 | 2.2 |
| markdown_headers | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.999 | 0.999 | 1.3 | 1.8 |
| markdown_headers_noprefix | 1.000 | 1.000 | 0.986 | 1.000 | 1.000 | 0.992 | 0.996 | 1.4 | 2.0 |
| semantic | 1.000 | 1.000 | 1.000 | 1.000 | 0.981 | 0.992 | 0.992 | 1.5 | 2.2 |

## recall@5 by question kind (all 35)

| Collection | context (n=6) | exact_token (n=5) | fact (n=9) | paraphrase (n=8) | procedure (n=7) |
|---|---|---|---|---|---|
| fixed_200 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| fixed_500_overlap | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| recursive_500 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| markdown_headers | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| markdown_headers_noprefix | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| semantic | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

Highest recall@5 on the 30 tuning questions (ties broken by nDCG@5): **fixed_500_overlap**.

Latency is the search only. Embedding one question took p50 271 ms, p95 322 ms when it was first cached.
