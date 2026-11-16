# Day 4: parent-document (small-to-big)

Search the 200-character chunks, return the whole markdown_headers section each one came from. Made by `python rag/day4.py parent`.

## Procedure and context questions only (13 questions)

| Technique | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
| Dense on markdown_headers (baseline) | 1.000 | 1.000 | 1.000 | 0.996 | 1.4 | 1.7 |
| Day 2 winner: hybrid alpha 0.7 on markdown_headers | 1.000 | 1.000 | 1.000 | 1.000 | 3.1 | 3.8 |
| Dense on fixed_200 (small chunks, returned as they are) | 1.000 | 1.000 | 1.000 | 0.989 | 2.0 | 2.4 |
| Parent-document: dense on fixed_200, return the parent section | 1.000 | 1.000 | 1.000 | 0.987 | 2.9 | 3.9 |
| Parent-document with hybrid alpha 0.7 | 1.000 | 1.000 | 0.923 | 0.936 | 5.7 | 7.8 |

## All 35 questions

| Technique | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
| Dense on markdown_headers (baseline) | 1.000 | 1.000 | 1.000 | 0.999 | 1.4 | 2.0 |
| Day 2 winner: hybrid alpha 0.7 on markdown_headers | 1.000 | 1.000 | 1.000 | 1.000 | 3.1 | 4.3 |
| Dense on fixed_200 (small chunks, returned as they are) | 1.000 | 1.000 | 1.000 | 0.992 | 2.1 | 3.1 |
| Parent-document: dense on fixed_200, return the parent section | 1.000 | 1.000 | 0.981 | 0.979 | 3.1 | 4.4 |
| Parent-document with hybrid alpha 0.7 | 1.000 | 1.000 | 0.938 | 0.949 | 5.3 | 7.0 |

## Small chunks vs their parents, per question (only where nDCG@5 changed)

| q | Kind | Small chunks nDCG@5 | Parents nDCG@5 | Parents rank-1 section |
|---|---|---|---|---|
| 1 | exact_token | 0.907 | 0.924 | Policy |
| 4 | procedure | 1.000 | 0.907 | Troubleshooting > VPN disconnects every few minutes |
| 9 | procedure | 0.950 | 0.924 | Changing your password > On macOS |
| 10 | paraphrase | 0.950 | 1.000 | Outlook > Keeps asking for password |
| 15 | exact_token | 1.000 | 0.500 | kb_other_formats/03-printer-setup-and-issues.pdf |
| 27 | context | 0.950 | 1.000 | Shared drives > Access denied on a folder |
| 34 | context | 0.950 | 1.000 | Troubleshooting > Connected but cannot reach shared drives |
