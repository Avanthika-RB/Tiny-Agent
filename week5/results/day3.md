# Day 3: reranking and query transformation

Every technique = the Day 2 winner (weighted hybrid, alpha 0.7, on `markdown_headers`) plus one thing. All 35 questions. Latency includes the reranker and LLM calls. Made by `python rag/day3.py`.

Reranker: `nvidia/llama-nemotron-rerank-vl-1b-v2`. Chat model: `nvidia/nemotron-3-super-120b-a12b` (falls back to `nvidia/nemotron-3.5-lightning-30b-a3b`).

## All techniques

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

## Candidate pool: recall@3 against latency (find the knee)

| Pool | recall@3 | hit@3 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|
| no rerank | 1.000 | 1.000 | 1.000 | 4.4 | 6.5 |
| 10 | 0.986 | 1.000 | 1.000 | 339.8 | 853.8 |
| 20 | 0.986 | 1.000 | 1.000 | 388.9 | 478.1 |
| 40 | 0.986 | 1.000 | 1.000 | 785.8 | 810.1 |

The knee is the pool size after which recall stops improving but latency keeps growing.

## What the chat model generated, for 3 questions (judge them yourself)

### q2: Which VPN gateway should someone based in Bangalore use?

Multi-query rephrasings:
- Which VPN gateway is appropriate for someone in Bangalore?
- What VPN gateway should a Bangalore-based user connect through?
- Which gateway should someone located in Bangalore use for VPN access?

HyDE paragraph: Users based in Bangalore should connect to the Asia-Pacific (ap-south) VPN gateway, as it is geographically optimized for the region and provides the lowest latency when accessing internal company resources. This gateway also ensures compliance with local data residency policies and avoids unnecessary routing through distant data centers. In the VPN client, select the `vpn-ap-south.company.com` endpoint from the region dropdown menu, and verify the connection status before attempting to reach restricted services. If the gateway option is unavailable or you experience connectivity issues, please contact the IT help desk for assistance with account-specific configurations.

Rewrite: VPN gateway

### q10: Outlook keeps asking for my password since I changed it yesterday. Why?

Multi-query rephrasings:
- Since I updated my password yesterday, Outlook keeps prompting me to sign in. Why is this happening?
- Outlook keeps asking for my credentials again after I changed my password yesterday. What's causing this?
- After resetting my password yesterday, Outlook keeps looping back to the login screen. Why won't it stop?

HyDE paragraph: Outlook caches your login credentials locally to improve performance, so when you change your password on the server, the application continues using the stored old password. This mismatch triggers repeated password prompts until the cached credentials are cleared or updated. The issue is typically resolved by removing the saved password from Windows Credential Manager and re-authenticating in Outlook.

Rewrite: Outlook password prompt

### q31: My laptop sounds like a jet engine even when I'm not doing anything. Should I report it?

Multi-query rephrasings:
- My laptop’s fan roars even when I’m not running anything. Should I open a helpdesk ticket?
- The notebook sounds like a jet engine while idle. Is this something to report to IT?
- Constant loud fan noise on my laptop with no activity. Do I need to contact support?

HyDE paragraph: If your laptop sounds like a jet engine while idle, it usually means the cooling system is working harder than necessary, often due to dust buildup, failing fans, or background processes straining the CPU. While you can try checking your task manager and ensuring your vents are clear, you should definitely report the issue to IT. They can diagnose whether it’s a simple maintenance need or a sign of hardware failure that needs immediate attention. Addressing it early can prevent overheating and extend your laptop’s lifespan.

Rewrite: laptop fan noise

## HyDE vs the Day 2 winner, per question

Only questions where nDCG@5 changed (4 of 35).

| q | Kind | Winner nDCG@5 | New nDCG@5 | New rank-1 chunk | Generated |
|---|---|---|---|---|---|
| 1 | exact_token | 1.000 | 0.760 | Policy (HIT) | When attempting to install the VPN client on a personal laptop, the setup typically fails and displays error code 0x80070005, which signifies that the installat |
| 4 | procedure | 1.000 | 0.950 | Troubleshooting > VPN disconnects every few minutes (HIT) | VPN connections that drop frequently at home are often caused by router firmware instability, ISP throttling, or conflicting wireless settings. Begin by updatin |
| 10 | paraphrase | 1.000 | 0.860 | Changing your password > On Windows (HIT) | Outlook caches your login credentials locally to improve performance, so when you change your password on the server, the application continues using the stored |
| 27 | context | 1.000 | 0.950 | Shared drives > Access denied on a folder (HIT) | If you receive an “Access Denied” message when trying to open a folder on the Logistics drive, this typically means your user account lacks the necessary permis |

## Multi-query (3) + RRF vs the Day 2 winner, per question

Only questions where nDCG@5 changed (1 of 35).

| q | Kind | Winner nDCG@5 | New nDCG@5 | New rank-1 chunk | Generated |
|---|---|---|---|---|---|
| 4 | procedure | 1.000 | 0.950 | Troubleshooting > VPN disconnects every few minutes (HIT) | My VPN keeps losing connection every few minutes at home. What settings should I modify? / My home VPN keeps dropping repeatedly. Which configuration needs an u |

## Rewrite / step-back vs the Day 2 winner, per question

Only questions where nDCG@5 changed (4 of 35).

| q | Kind | Winner nDCG@5 | New nDCG@5 | New rank-1 chunk | Generated |
|---|---|---|---|---|---|
| 4 | procedure | 1.000 | 0.924 | Troubleshooting > VPN disconnects every few minutes (HIT) | VPN connection drops |
| 9 | procedure | 1.000 | 0.950 | Changing your password > On macOS (HIT) | Mac password keychain |
| 22 | procedure | 1.000 | 0.631 | Slow after an update (miss) | slow laptop |
| 27 | context | 1.000 | 0.860 | Shared drives > Drive not mapping (HIT) | access denied Logistics drive |

Every prompt and answer is in results/llm_log.jsonl.
