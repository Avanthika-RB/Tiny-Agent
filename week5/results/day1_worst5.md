# Day 1: the 5 worst questions for the baseline (dense_fixed_500_overlap)

Sorted by nDCG@5, then MRR, then margin (how close the answer came to being beaten by a wrong chunk).
Only 1 of 35 questions score below a perfect nDCG@5; the rest of this list is the most fragile perfect ones.
Made by `python rag/evaluate.py worst`.

## q1 (exact_token): What error code appears when you try to install the VPN client on a personal laptop?

- Gold: 01/Policy (grade 2), 01/Connecting for the first time (grade 1)
- Expected answer: 1103
- hit@3 1, recall@5 1.000, MRR 1.000, nDCG@5 0.950, margin 0.213
- Top 5:
  1. HIT 01/Policy (grade 2)  [kb/01-vpn-access-guide.md]  or a device certificate that is only installed on company-managed laptops. Attempting to install the client on
  2. HIT 01/Policy (grade 2)  [kb/01-vpn-access-guide.md]  ol default | Notes | |---|---|---|---| | Americas | vpn-us.example.com | UDP | Highest capacity | | Europe | v
  3. HIT 01/Connecting for the first time (grade 1)  [kb/01-vpn-access-guide.md]  If you do not receive it within 30 seconds, open the authenticator app and use the six-digit code instead. 5. 
  4. miss  [kb/01-vpn-access-guide.md]  # VPN Access Guide ## Overview The corporate VPN gives employees secure access to internal systems when workin
  5. HIT 01/Connecting for the first time (grade 1)  [kb/01-vpn-access-guide.md]  d drives when the VPN is disconnected. ## Connecting for the first time 1. Open the VPN client from the Start 

**Why I think it failed:** 

I think it failed because of the order that the related sections came in. Its only a .050 difference in score because its the right answer, but related section came in later. 

## q14 (exact_token): What driver do I pick when adding a printer on Windows?

- Gold: 03/Windows (grade 2), 03/Adding a printer (grade 1)
- Expected answer: Generic PCL6
- hit@3 1, recall@5 1.000, MRR 1.000, nDCG@5 1.000, margin 0.011
- Top 5:
  1. HIT 03/Windows (grade 2)  [kb/03-printer-setup-and-issues.md]  printers that have been retired. ## Adding a printer ### Windows 1. Open Settings, then Bluetooth and devices,
  2. HIT 03/Adding a printer (grade 1)  [kb_other_formats/03-printer-setup-and-issues.pdf]  rs that have been retired. Adding a printer Windows 1. Open Settings, then Bluetooth and devices, then Printer
  3. HIT 03/Windows (grade 2)  [kb_other_formats/03-printer-setup-and-issues.pdf]  Printer Setup and Issues Finding your printer Every office printer has a label on the front with its name and 
  4. HIT 03/Adding a printer (grade 1)  [kb/03-printer-setup-and-issues.md]  # Printer Setup and Issues ## Finding your printer Every office printer has a label on the front with its name
  5. HIT 03/Windows (grade 2)  [kb/03-printer-setup-and-issues.md]  not download a manufacturer driver; the generic one is faster and is the only one the print server supports. 6

**Why I think it failed:** 

I think it failed because even though it said the right answer, it is repeating the same information multiple times. 

## q2 (context): Which VPN gateway should someone based in Bangalore use?

- Gold: 01/Regional gateways (grade 2)
- Expected answer: vpn-in.example.com
- hit@3 1, recall@5 1.000, MRR 1.000, nDCG@5 1.000, margin 0.033
- Top 5:
  1. HIT 01/Regional gateways (grade 2)  [kb/01-vpn-access-guide.md]  ol default | Notes | |---|---|---|---| | Americas | vpn-us.example.com | UDP | Highest capacity | | Europe | v
  2. miss  [kb/01-vpn-access-guide.md]  d drives when the VPN is disconnected. ## Connecting for the first time 1. Open the VPN client from the Start 
  3. HIT 01/Regional gateways (grade 2)  [kb/01-vpn-access-guide.md]  hable while the VPN is up or when you are in the office. If the drive letter is missing entirely, see the Shar
  4. miss  [kb/01-vpn-access-guide.md]  house staff do not have VPN enabled by default because their tools are available on the local network only; th
  5. miss  [kb/01-vpn-access-guide.md]  # VPN Access Guide ## Overview The corporate VPN gives employees secure access to internal systems when workin

**Why I think it failed:** 

I think it failed because even though the gateway answer is there, it talks about a city in india whereas the article says the state, india. 

## q31 (paraphrase): My laptop sounds like a jet engine even when I'm not doing anything. Should I report it?

- Gold: 04/Fans running constantly (grade 2)
- Expected answer: Restart first; if fans are loud at idle for more than a day after a restart, file a ticket (dust, Facilities cleans it)
- hit@3 1, recall@5 1.000, MRR 1.000, nDCG@5 1.000, margin 0.075
- Top 5:
  1. HIT 04/Fans running constantly (grade 2)  [kb/04-laptop-performance-and-updates.md]  stuck browser tab. Restart first. If the fans run loud at idle for more than a day after a restart, file a tic
  2. HIT 04/Fans running constantly (grade 2)  [kb/04-laptop-performance-and-updates.md]  ables and are expected to lose about 20 percent of capacity after two years. A laptop that no longer lasts a t
  3. miss  [kb/04-laptop-performance-and-updates.md]  . Sleeping the laptop for two weeks is not a restart. Shut it down fully once a week. 4. Whether a backup or s
  4. miss  [kb/04-laptop-performance-and-updates.md]  After a major update the laptop rebuilds its search index and scans files for the security agent. This takes b
  5. miss  [kb/04-laptop-performance-and-updates.md]  e a ticket and include a screenshot of Task Manager or Activity Monitor sorted by CPU. ## General slowness Bef

**Why I think it failed:** 

It gave the right answer, but had some misses because its the next closest chunks. 

## q9 (procedure): Steps to change my password on a Mac, including the keychain part

- Gold: 02/On macOS (grade 2), 02/Changing your password (grade 1)
- Expected answer: System Settings, Users and Groups, Change Password, then update Keychain entries
- hit@3 1, recall@5 1.000, MRR 1.000, nDCG@5 1.000, margin 0.076
- Top 5:
  1. HIT 02/On macOS (grade 2)  [kb/02-password-and-account-security.md]  an hour. ### On macOS 1. Open System Settings, then Users and Groups. 2. Click Change Password next to your ac
  2. HIT 02/Changing your password (grade 1)  [kb/02-password-and-account-security.md]  d because they are easier to remember and harder to guess than short complex strings. ## Changing your passwor
  3. miss  [kb/05-collaboration-tools.md]  back in. ## Outlook ### Keeps asking for password Close Outlook. On Windows, open Credential Manager, choose W
  4. miss  [kb/02-password-and-account-security.md]  # Password and Account Security ## Password rules Passwords must be at least 14 characters and contain three o
  5. miss  [kb/02-password-and-account-security.md]  assword on a page you reached from an email link. The real sign-in page always shows the company logo and the 

**Why I think it failed:** 

First two are hits, then misses because after getting the right answer, it then finds the next related chunk that has similar wording or vectors.
