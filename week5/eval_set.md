# Evaluation Set (30 questions)

kind: fact | procedure | context | exact_token | paraphrase.
Grade 2 = the section that answers it. Grade 1 = related section (counts for nDCG, not for hit).

| # | Kind | Question | Gold article / section (grade) | Expected answer |
|---|---|---|---|---|
| 1 | exact_token | What error code appears when you try to install the VPN client on a personal laptop? | 01 / Policy (2); 01 / Connecting for the first time (1) | 1103 |
| 2 | context | Which VPN gateway should someone based in Bangalore use? | 01 / Regional gateways (2) | vpn-in.example.com |
| 3 | context | Why is the India VPN gateway on TCP by default? | 01 / Regional gateways (2) | ISP filtering |
| 4 | procedure | My VPN keeps dropping every couple of minutes at home. What do I change? | 01 / VPN disconnects every few minutes (2); 01 / Troubleshooting (1) | Switch protocol UDP to TCP, reconnect, restart once |
| 5 | paraphrase | Does the VPN route all my internet traffic through the office? | 01 / Overview (2) | No, split tunnelling: only internal addresses |
| 6 | fact | Can warehouse staff use the VPN? | 01 / Overview (2) | Not by default; request via ticket with manager approval |
| 7 | fact | How long is a password valid before it expires? | 02 / Password rules (2) | 180 days |
| 8 | paraphrase | How many old passwords are remembered so you cannot reuse them? | 02 / Password rules (2) | 12 |
| 9 | procedure | Steps to change my password on a Mac, including the keychain part | 02 / On macOS (2); 02 / Changing your password (1) | System Settings, Users and Groups, Change Password, then update Keychain entries |
| 10 | paraphrase | Outlook keeps asking for my password since I changed it yesterday. Why? | 05 / Keeps asking for password (2); 02 / On Windows (1) | Skipped the lock-and-unlock step; clear Credential Manager entries |
| 11 | fact | After how many failed logins does the account lock, and for how long? | 02 / Locked account (2) | 5 attempts in 15 minutes, 30 minutes |
| 12 | procedure | I got a new phone and already wiped the old one. How do I get MFA working? | 02 / Multi-factor authentication (2) | Helpdesk MFA reset, video call identity check, about 20 minutes |
| 13 | procedure | What should I do if I typed my password into a phishing page? | 02 / Phishing (2) | Change password immediately, inform security team same day |
| 14 | exact_token | What driver do I pick when adding a printer on Windows? | 03 / Windows (2); 03 / Adding a printer (1) | Generic PCL6 |
| 15 | exact_token | Which protocol do I choose for a printer on macOS? | 03 / macOS (2) | IPP |
| 16 | context | What does the printer name AUS-02-03 mean? | 03 / Finding your printer (2) | Austin, floor 2, printer 3 |
| 17 | procedure | The printer says offline for me. Quickest fix? | 03 / Printer shows offline (2) | Remove and re-add by IP address |
| 18 | paraphrase | My prints come out with streaks. Should I try to fix the printer? | 03 / Prints are blank or streaked (2) | No, hardware; file a low priority ticket |
| 19 | fact | Can I print from my personal phone? | 03 / Printing from a personal device (2) | Not supported; email to yourself |
| 20 | fact | When are OS updates pushed and how long do I have to restart? | 04 / Update policy (2) | Second Tuesday monthly, seven days |
| 21 | paraphrase | Laptop is crawling since this morning's update. Is something broken? | 04 / Slow after an update (2) | Indexing and scan after update, 30 to 90 minutes, two restarts |
| 22 | procedure | What should I check before opening a ticket about a slow laptop? | 04 / General slowness (2) | Tabs, disk space, last full restart, running sync |
| 23 | context | My battery does not last a two hour meeting anymore. What can I do? | 04 / Battery (2) | Battery replacement under low priority ticket |
| 24 | paraphrase | Other people cannot hear me in Teams but I can hear them | 05 / Audio not working in meetings (2) | Microphone permission; Settings, Devices; macOS Privacy, Microphone |
| 25 | fact | What is the Outlook mailbox size limit and when does it warn? | 05 / Mailbox full (2) | 50 GB limit, warns at 45 GB |
| 26 | exact_token | What is the smb path for the Finance shared drive on a Mac? | 05 / Drive not mapping (2); 05 / Shared drives (1) | smb://files.example.com/finance |
| 27 | context | I get access denied on a folder in the Logistics drive. Can IT fix it? | 05 / Access denied on a folder (2); 05 / Drive not mapping (1) | No, owner team (Logistics) grants access |
| 28 | fact | How long does a software request take to be approved? | 06 / Requesting software not in the catalogue (2) | 3 to 5 working days, up to 3 weeks for new software |
| 29 | fact | How long does temporary admin access last and who approves it? | 06 / Temporary administrator rights (2) | 60 minutes, your manager |
| 30 | paraphrase | I got a new laptop and my paid software will not activate. What happened? | 06 / Licences (2) | Licence still on old device; uninstall there or file ticket with asset tag |

## My 5 added questions (held out: never tuned on, reported separately)

| # | Kind | Question | Gold article / section (grade) | Expected answer |
|---|---|---|---|---|
| 31 | paraphrase | My laptop sounds like a jet engine even when I'm not doing anything. Should I report it? | 04 / Fans running constantly (2) | Restart first; if fans are loud at idle for more than a day after a restart, file a ticket (dust, Facilities cleans it) |
| 32 | exact_token | Which VPN gateway has a maintenance window on Sundays? | 01 / Regional gateways (2) | vpn-eu.example.com, Sundays 02:00 to 04:00 CET |
| 33 | procedure | Teams shows a black screen instead of my camera. What should I try? | 05 / Camera shows a black screen (2) | Close other apps using the camera; on Windows allow desktop apps in Privacy, Camera; sign out and back in to Teams |
| 34 | context | The VPN says I'm connected but my shared drive still won't open. What now? | 01 / Connected but cannot reach shared drives (2); 05 / Drive not mapping (1) | Check it says Connected not Connecting, then reconnect the drive in File Explorer; if the drive letter is missing, map it with the path from the Shared drives table |
| 35 | fact | Can I add a grammar checker extension to my browser? | 06 / Browser extensions (2) | Only after a security review, because it reads page content on every site; request it like software |
