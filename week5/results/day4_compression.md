# Day 4: contextual compression

Retrieval: production config (alpha 0.6, pool 10, rerank to 5), top 5. The chat model copies out only the sentences that help. Then it answers from the full chunks and from the compressed ones, and an LLM judge scores each answer 0-2 against the expected answer. Made by `python rag/day4.py compress`. All prompts in results/llm_log.jsonl.

| q | Kind | Full chars | Compressed chars | Score, full | Score, compressed | Judge on the compressed answer |
|---|---|---|---|---|---|---|
| 1 | exact_token | 1658 | 102 | 2 | 2 | The answer correctly provides the error code 1103, the key fact requested. |
| 4 | procedure | 1517 | 324 | 1 | 1 | The answer correctly identifies switching UDP to TCP but omits the required reconnect and restart steps. |
| 9 | procedure | 2075 | 258 | 2 | 2 | The answer covers all expected steps (System Settings, Users and Groups, Change Password, and updating Keychain entries) accurately and without errors. |
| 12 | procedure | 2202 | 233 | 2 | 2 | The answer correctly includes all key facts: helpdesk MFA reset, video call identity check, and about 20 minutes. |
| 15 | exact_token | 1703 | 48 | 2 | 2 | The answer correctly states IPP as the protocol for macOS printers. |
| 17 | procedure | 2119 | 208 | 2 | 2 | The answer correctly includes the key fix of removing and re-adding the printer via IP address. |
| 22 | procedure | 1970 | 911 | 2 | 2 | It accurately covers all four required checks (browser tabs, disk space, last restart, running sync) in the correct order without adding incorrect or invented facts. |
| 25 | fact | 2324 | 51 | 2 | 2 | The answer correctly states both the 50 GB mailbox size limit and the 45 GB warning threshold. |
| 27 | context | 2173 | 567 | 2 | 2 | The answer accurately identifies that IT cannot grant access, confirms the owner team manages permissions, and correctly directs the user to contact the team lead, matching all key facts of the expected answer. |
| 29 | fact | 1906 | 168 | 2 | 2 | The answer accurately provides both the duration (60 minutes) and the approver (your manager). |

Total answer score: full 19/20, compressed 19/20. Context size: 19647 -> 2870 characters (85% smaller). Extra LLM calls per question for compression: 1.
