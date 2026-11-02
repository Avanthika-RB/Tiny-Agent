# Retrieval Results

hit@3: Y if any of the top 3 chunks contains the expected answer, N otherwise.
Fill in your PREDICTION column before running anything.

| Q | Kind | Prediction (which wins?) | fixed_200 | fixed_500_overlap | recursive_500 | markdown_headers | markdown_headers_noprefix | semantic |
|---|------|--------------------------|-----------|-------------------|---------------|------------------|---------------------------|----------|
| 1 | fact | fixed_200, fixed_500_overlap, markdown_headers | Y(1) | Y(1) | Y(1) | Y(1) | Y(1) | Y(1) |
| 2 | fact | fixed_200, fixed_500_overlap, markdown_headers | Y(1) | Y(1) | Y(1) | Y(1) | Y(1) | Y(1) |
| 3 | fact | fixed_200, fixed_500_overlap, markdown_headers | Y(1) | Y(1) | Y(1) | Y(1) | Y(1) | Y(1) |
| 4 | fact | fixed_200, fixed_500_overlap, markdown_headers | Y(1) | Y(1) | Y(1) | Y(1) | Y(1) | Y(1) |
| 5 | procedure | fixed_500_overlap, markdown_headers | N | Y(1) | Y(1) | Y(1) | Y(3) | N |
| 6 | procedure | fixed_500_overlap, markdown_headers| N | Y(1) | Y(1) | Y(1) | Y(1) | Y(1) |
| 7 | procedure | fixed_500_overlap, markdown_headers| N | N | Y(1) | Y(1) | Y(1) | N |
| 8 | context | markdown_headers| N | Y(1) | Y(1) | Y(1) | Y(1) | Y(1) |
| 9 | context | markdown_headers| Y(1) | Y(1) | Y(1) | Y(1) | Y(1) | Y(1) |
| 10 | context | markdown_headers | Y(1) | Y(1) | Y(1) | Y(1) | Y(1) | Y(1) |
| **Total** | n/a | **6/10** | **9/10** | **10/10** | **10/10** | **10/10** | **8/10** |

## Chunk statistics
### after day 4
| Collection | Chunks | Avg chars | Min | Max | Ingest time (s) |
|---|---|---|---|---|---|
| fixed_200 | 106 | 194 | 65 | 200 | 2.0 |
| fixed_500_overlap | 55 | 458 | 114 | 500 | 1.4 |
| recursive_500 | 64 | 339 | 31 | 498 | 1.4 |
| markdown_headers | 63 | 359 | 119 | 548 | 1.7 |
| markdown_headers_noprefix | 63 | 305 | 81 | 498 | 1.5 |
| semantic | 30 | 685 | 47 | 2258 | 7.0 |

### after day 5 with duplicates removed
 python rag/ingest.py ingest
| Collection | Added | Updated | Deleted | Skipped | Chunks in collection |
|---|---|---|---|---|---|
| fixed_200 | 0 | 0 | 0 | 106 | 84 |
| fixed_500_overlap | 0 | 0 | 0 | 55 | 43 |
| recursive_500 | 0 | 0 | 0 | 64 | 51 |
| markdown_headers | 0 | 0 | 0 | 63 | 49 |
| markdown_headers_noprefix | 0 | 0 | 0 | 63 | 49 |
| semantic | 0 | 0 | 0 | 30 | 23 |