# Day 2: sparse, hybrid, prefilter, MMR

Every technique searches the same chunks: the `markdown_headers` collection. All 35 questions unless noted. Made by `python rag/day2.py`.

## All techniques

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

## nDCG@5 by question kind

| Technique | context (n=6) | exact_token (n=5) | fact (n=9) | paraphrase (n=8) | procedure (n=7) |
|---|---|---|---|---|---|
| Baseline dense | **1.000** | **1.000** | **1.000** | **1.000** | 0.993 |
| BM25 | 0.905 | 0.981 | 0.959 | 0.869 | 0.912 |
| Hybrid RRF k=60 | 0.938 | **1.000** | **1.000** | 0.875 | **1.000** |
| Hybrid alpha=0.3 | 0.938 | 0.990 | **1.000** | 0.923 | 0.993 |
| Hybrid alpha=0.5 | 0.938 | **1.000** | **1.000** | 0.954 | 0.993 |
| Hybrid alpha=0.7 | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** |
| MMR lambda=0.5 | 0.920 | 0.856 | **1.000** | 0.970 | 0.931 |
| Dense + LLM-guessed article filter (all 35) | 0.897 | **1.000** | 0.889 | 0.923 | 0.993 |

Bold = best for that kind (shared bests are all bold).

## Alpha sweep (alpha = weight on dense; 0 = pure BM25, 1 = pure dense)

| alpha | recall@5 | hit@3 | MRR | nDCG@5 |
|---|---|---|---|---|
| 0.0 | 0.971 | 0.914 | 0.914 | 0.923 |
| 0.3 | 1.000 | 0.971 | 0.964 | 0.969 |
| 0.5 | 1.000 | 1.000 | 0.971 | 0.977 |
| 0.7 | 1.000 | 1.000 | 1.000 | 1.000 |
| 1.0 | 1.000 | 1.000 | 1.000 | 0.999 |

## Dense vs BM25, per question

Rank of the first chunk that answers the question (grade 2). Only questions where the two differ.

| q | Kind | Question | Dense | BM25 |
|---|---|---|---|---|
| 2 | context | Which VPN gateway should someone based in Bangalore use? | 1 | 4 |
| 7 | fact | How long is a password valid before it expires? | 1 | 2 |
| 22 | procedure | What should I check before opening a ticket about a slow laptop? | 1 | 4 |
| 31 | paraphrase | My laptop sounds like a jet engine even when I'm not doing anything. Should I report it? | 1 | not in top 5 |

## MMR vs dense, per question

nDCG@5 and how many of the top 5 came from a different source file (more = more diverse). Only questions where nDCG@5 changed.

| q | Kind | Dense nDCG@5 | MMR nDCG@5 | Dense: files in top 5 | MMR: files in top 5 |
|---|---|---|---|---|---|
| 1 | exact_token | 1.000 | 0.760 | 1 | 4 |
| 4 | procedure | 0.950 | 0.760 | 1 | 4 |
| 9 | procedure | 1.000 | 0.760 | 2 | 3 |
| 10 | paraphrase | 1.000 | 0.760 | 3 | 3 |
| 14 | exact_token | 1.000 | 0.760 | 2 | 4 |
| 26 | exact_token | 1.000 | 0.760 | 3 | 5 |
| 27 | context | 1.000 | 0.760 | 2 | 5 |
| 34 | context | 1.000 | 0.760 | 2 | 4 |

## Prefilter by named area (25 questions)

A question qualifies if it names exactly one area (see AREA_WORDS in retrievers/prefilter.py). Both rows are on exactly these questions.

| Technique | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms | |
|---|---|---|---|---|---|---|---|
| Dense | 1.000 | 1.000 | 1.000 | 0.998 | 1.7 | 2.3 |  |
| Dense + prefilter | 1.000 | 1.000 | 1.000 | 0.998 | 1.9 | 2.4 |  |

## LLM article guess (all 35)

| q | Question | Guessed | Gold (grade 2) | Right? |
|---|---|---|---|---|
| 1 | What error code appears when you try to install the VPN client on a personal laptop? | 01 | 01 | yes |
| 2 | Which VPN gateway should someone based in Bangalore use? | 01 | 01 | yes |
| 3 | Why is the India VPN gateway on TCP by default? | 01 | 01 | yes |
| 4 | My VPN keeps dropping every couple of minutes at home. What do I change? | 01 | 01 | yes |
| 5 | Does the VPN route all my internet traffic through the office? | 01 | 01 | yes |
| 6 | Can warehouse staff use the VPN? | 01 | 01 | yes |
| 7 | How long is a password valid before it expires? | 02 | 02 | yes |
| 8 | How many old passwords are remembered so you cannot reuse them? | 02 | 02 | yes |
| 9 | Steps to change my password on a Mac, including the keychain part | 02 | 02 | yes |
| 10 | Outlook keeps asking for my password since I changed it yesterday. Why? | 02 | 05 | **no** |
| 11 | After how many failed logins does the account lock, and for how long? | 02 | 02 | yes |
| 12 | I got a new phone and already wiped the old one. How do I get MFA working? | 02 | 02 | yes |
| 13 | What should I do if I typed my password into a phishing page? | 02 | 02 | yes |
| 14 | What driver do I pick when adding a printer on Windows? | 03 | 03 | yes |
| 15 | Which protocol do I choose for a printer on macOS? | 03 | 03 | yes |
| 16 | What does the printer name AUS-02-03 mean? | 03 | 03 | yes |
| 17 | The printer says offline for me. Quickest fix? | 03 | 03 | yes |
| 18 | My prints come out with streaks. Should I try to fix the printer? | 03 | 03 | yes |
| 19 | Can I print from my personal phone? | 03 | 03 | yes |
| 20 | When are OS updates pushed and how long do I have to restart? | 04 | 04 | yes |
| 21 | Laptop is crawling since this morning's update. Is something broken? | 04 | 04 | yes |
| 22 | What should I check before opening a ticket about a slow laptop? | 04 | 04 | yes |
| 23 | My battery does not last a two hour meeting anymore. What can I do? | 04 | 04 | yes |
| 24 | Other people cannot hear me in Teams but I can hear them | 05 | 05 | yes |
| 25 | What is the Outlook mailbox size limit and when does it warn? | 05 | 05 | yes |
| 26 | What is the smb path for the Finance shared drive on a Mac? | 05 | 05 | yes |
| 27 | I get access denied on a folder in the Logistics drive. Can IT fix it? | 05 | 05 | yes |
| 28 | How long does a software request take to be approved? | 06 | 06 | yes |
| 29 | How long does temporary admin access last and who approves it? | 02 | 06 | **no** |
| 30 | I got a new laptop and my paid software will not activate. What happened? | 06 | 06 | yes |
| 31 | My laptop sounds like a jet engine even when I'm not doing anything. Should I report it? | 04 | 04 | yes |
| 32 | Which VPN gateway has a maintenance window on Sundays? | 01 | 01 | yes |
| 33 | Teams shows a black screen instead of my camera. What should I try? | 05 | 05 | yes |
| 34 | The VPN says I'm connected but my shared drive still won't open. What now? | 05 | 01 | **no** |
| 35 | Can I add a grammar checker extension to my browser? | 06 | 06 | yes |

The LLM guessed the right article for 32 of 35 questions. Every prompt and answer is in results/llm_log.jsonl.
