# Retrieval Test Questions

Ten questions against the six knowledge base articles. For each one, query every collection with k=3
and record whether any of the top 3 chunks contains the answer. Fill in results.md as a grid.

Three kinds of question. Expect different chunking strategies to win on different kinds.

## Single-fact questions (the answer is one sentence somewhere)

| # | Question | Answer lives in | Expected answer |
|---|----------|-----------------|-----------------|
| 1 | What error code do you get when installing the VPN client on a personal device? | 01, Policy | 1103 |
| 2 | How many previous passwords can a new password not match? | 02, Password rules | 12 |
| 3 | What is the mailbox size limit? | 05, Outlook, Mailbox full | 50 GB |
| 4 | How long does a temporary administrator elevation last? | 06, Temporary administrator rights | 60 minutes |

## Procedure questions (the answer is a numbered list; a chunk that splits the list fails)

| # | Question | Answer lives in | Expected answer |
|---|----------|-----------------|-----------------|
| 5 | What are the steps to add a printer on macOS? | 03, Adding a printer, macOS | All 6 steps, including Generic PostScript Printer |
| 6 | How do I change my password on Windows, including the step people usually skip? | 02, Changing your password, Windows | 4 steps, the lock-and-unlock step |
| 7 | What should I check, in order, before filing a ticket for a slow laptop? | 04, General slowness | 4 checks: tabs, disk, restart, sync |

## Context questions (the answer only makes sense with its heading or table row)

| # | Question | Answer lives in | Expected answer |
|---|----------|-----------------|-----------------|
| 8 | Which VPN gateway should someone in Bangalore use, and why is its default protocol different? | 01, Regional gateways table | vpn-in.example.com, TCP because of ISP filtering |
| 9 | What is the macOS path for the Finance shared drive? | 05, Shared drives table | smb://files.example.com/finance |
| 10 | My fans are loud all the time. Is that a ticket or something I fix myself? | 04, Fans running constantly | Restart first; ticket if still loud after a day |

## Why these three kinds

- Fixed-size chunks tend to pass the fact questions and fail the procedure questions, because a 200-character
  window cuts a six-step list in half.
- Header-aware chunks tend to win the context questions, because the heading travels with the chunk as metadata.
  A chunk that says "smb://files.example.com/finance" without the table header does not know it is the Finance drive.
- Semantic chunks are unpredictable. Sometimes they keep a whole procedure together beautifully. Sometimes they
  merge two unrelated paragraphs because the embedding similarity happened to be high.

Write down which collection wins each row BEFORE you look at the results. Then compare.
