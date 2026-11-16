# Failure analysis: production config

Production config: hybrid search (0.6 dense + 0.4 BM25) on `markdown_headers`, top 5, no reranker.
At the retrieval level it gets hit@3 1.000, recall@5 1.000, MRR 1.000 and nDCG@5 0.999 on all 35
questions, so only one question is less than perfect. The rest of the list comes from plugging the
search into the helpdesk agent (Day 4: the 15 helpdesk cases and the LangSmith experiments).

## Every remaining failure, classified

| # | What went wrong | Category | Why |
|---|---|---|---|
| 1 | **q9** (Mac password steps), nDCG@5 0.95: the Phishing section ranked 2nd, above the related "Changing your password" section | query | "password" appears in many sections, and the BM25 half of hybrid search rewards it. The real answer (On macOS) was still ranked 1st. |
| 2 | **Helpdesk case 8** (stolen laptop): the agent suggested the "Licences" section | missing data | No article covers lost or stolen devices, and vector search always returns 5 chunks even when none of them are relevant. |
| 3 | **Helpdesk case 7** (Aisha, macOS, shared drive): she got the table of smb paths but not the "Finder, Go, Connect to Server" sentence | chunking | The instruction sentence and the table ended up in two different chunks. |
| 4 | Every technique scored about 1.000, so nothing could show an improvement | metric | The eval set is too easy for 6 short articles on clearly different topics, and section-level matching is generous: any chunk from the gold section counts, even one without the answer. |
| 5 | The groundedness judge gave 0 to replies that only filed a ticket | metric | The judge treats the ticket summary or ticket id as "facts not in the search results". |
| 6 | Helpdesk case 7 counted as a tool_order failure even though the macOS fix is correct | metric | The dataset's expected outcome (file a ticket) was written for the old keyword search, which had no macOS fix. |

## The two largest categories: what I would change next

**Metric (3 failures).**
- Make the eval set harder: more questions that span two articles and more paraphrases with no shared words.
- Use answer-level matching: the chunk must contain the expected answer, like Week 4's `must_contain`.
- Fix the groundedness rubric so a reply that only files a ticket counts as grounded.
- Update case 7's expected outcome now that the articles contain a macOS fix.

**Missing data and chunking (1 each).**
- Add an article on lost or stolen devices.
- Add a relevance cut-off, so the search can say "nothing relevant" instead of always returning 5 chunks.
- Keep a table in the same chunk as the sentence that introduces it.
