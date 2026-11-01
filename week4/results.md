# Retrieval Results

hit@3: Y if any of the top 3 chunks contains the expected answer, N otherwise.
Fill in your PREDICTION column before running anything.

| Q | Kind | Prediction (which wins?) | fixed_200 | fixed_500_overlap | recursive_500 | markdown_headers | semantic |
|---|------|--------------------------|-----------|-------------------|---------------|------------------|----------|
| 1 | fact | | | | | | |
| 2 | fact | | | | | | |
| 3 | fact | | | | | | |
| 4 | fact | | | | | | |
| 5 | procedure | | | | | | |
| 6 | procedure | | | | | | |
| 7 | procedure | | | | | | |
| 8 | context | | | | | | |
| 9 | context | | | | | | |
| 10 | context | | | | | | |
| **Total** | | | | | | | |

## Chunk statistics

| Collection | Chunks | Avg chars | Min | Max | Ingest time (s) |
|---|---|---|---|---|---|
| fixed_200 | 106 | 194 | 65 | 200 | 2.5 |
| fixed_500_overlap | 55 | 458 | 114 | 500 | 1.6 |
| recursive_500 | 64 | 339 | 31 | 498 | 2.2 |
| markdown_headers | | | | | |
| markdown_headers_noprefix | | | | | |
| semantic | | | | | |


after day 4
| Collection | Chunks | Avg chars | Min | Max | Ingest time (s) |
|---|---|---|---|---|---|
| fixed_200 | 106 | 194 | 65 | 200 | 2.0 |
| fixed_500_overlap | 55 | 458 | 114 | 500 | 1.4 |
| recursive_500 | 64 | 339 | 31 | 498 | 1.4 |
| markdown_headers | 63 | 359 | 119 | 548 | 1.7 |
| markdown_headers_noprefix | 63 | 305 | 81 | 498 | 1.5 |
| semantic | 30 | 685 | 47 | 2258 | 7.0 |