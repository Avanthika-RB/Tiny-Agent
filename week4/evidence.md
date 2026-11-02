# Evidence: top 3 chunks per collection for questions 5, 8 and 9

Created by `python rag/compare.py`. HIT means that chunk contains the whole expected answer.

## Q5 (procedure): What are the steps to add a printer on macOS?

Must contain, in one chunk: `Open System Settings, then Printers and Scanners`, `Click Add Printer, Scanner, or Fax`, `Select the IP tab`, `Protocol should be IPP`, `Generic PostScript Printer`, `Click Add and print a test page`

### fixed_200

**1. miss** (distance 0.400, kb_other_formats/03-printer-setup-and-issues.pdf)

```
anufacturer driver; the generic one is faster and is the only one the print server supports.
6. Print a test page. macOS
1. Open System Settings, then Printers and Scanners.
2. Click Add Printer, Scan
```

**2. miss** (distance 0.433, kb/03-printer-setup-and-issues.md)

```
not download a manufacturer driver; the generic one is faster and is the only one the print server supports.
6. Print a test page.

### macOS

1. Open System Settings, then Printers and Scanners.
2.
```

**3. miss** (distance 0.462, kb/03-printer-setup-and-issues.md)

```
Click Add Printer, Scanner, or Fax.
3. Select the IP tab.
4. Enter the IP address. Protocol should be IPP. Leave Queue empty.
5. For Use, pick Generic PostScript Printer.
6. Click Add and print a test
```

### fixed_500_overlap

**1. HIT** (distance 0.382, kb/03-printer-setup-and-issues.md)

```
not download a manufacturer driver; the generic one is faster and is the only one the print server supports.
6. Print a test page.

### macOS

1. Open System Settings, then Printers and Scanners.
2. Click Add Printer, Scanner, or Fax.
3. Select the IP tab.
4. Enter the IP address. Protocol should be IPP. Leave Queue empty.
5. For Use, pick Generic PostScript Printer.
6. Click Add and print a test page.

## Common problems

### Printer shows offline

Remove the printer and re-add it using the IP
```

**2. HIT** (distance 0.408, kb_other_formats/03-printer-setup-and-issues.pdf)

```
anufacturer driver; the generic one is faster and is the only one the print server supports.
6. Print a test page. macOS
1. Open System Settings, then Printers and Scanners.
2. Click Add Printer, Scanner, or Fax.
3. Select the IP tab.
4. Enter the IP address. Protocol should be IPP. Leave Queue empty.
5. For Use, pick Generic PostScript Printer.
6. Click Add and print a test page. Common problems Printer shows offline Remove the printer and re-add it using the IP address. This fixes the problem
```

**3. miss** (distance 0.491, kb/03-printer-setup-and-issues.md)

```
printers that have been retired.

## Adding a printer

### Windows

1. Open Settings, then Bluetooth and devices, then Printers and scanners.
2. Click Add device, wait ten seconds, then click Add manually.
3. Choose Add a printer using an IP address or hostname.
4. Enter the IP address from the label. Leave the port name as suggested.
5. When asked for a driver, choose the generic PCL6 driver. Do not download a manufacturer driver; the generic one is faster and is the only one the print server
```

### recursive_500

**1. HIT** (distance 0.313, kb/03-printer-setup-and-issues.md)

```
### macOS

1. Open System Settings, then Printers and Scanners.
2. Click Add Printer, Scanner, or Fax.
3. Select the IP tab.
4. Enter the IP address. Protocol should be IPP. Leave Queue empty.
5. For Use, pick Generic PostScript Printer.
6. Click Add and print a test page.

## Common problems

### Printer shows offline
```

**2. miss** (distance 0.314, kb_other_formats/03-printer-setup-and-issues.pdf)

```
1. Open Settings, then Bluetooth and devices, then Printers and scanners.
2. Click Add device, wait ten seconds, then click Add manually.
3. Choose Add a printer using an IP address or hostname.
4. Enter the IP address from the label. Leave the port name as suggested.
5. When asked for a driver, choose the generic PCL6 driver. Do not download a manufacturer driver; the generic one is faster and is the only one the print server supports.
6. Print a test page. macOS
```

**3. miss** (distance 0.353, kb_other_formats/03-printer-setup-and-issues.pdf)

```
6. Print a test page. macOS
1. Open System Settings, then Printers and Scanners.
2. Click Add Printer, Scanner, or Fax.
3. Select the IP tab.
4. Enter the IP address. Protocol should be IPP. Leave Queue empty.
5. For Use, pick Generic PostScript Printer.
```

### markdown_headers

**1. HIT** (distance 0.247, kb/03-printer-setup-and-issues.md | Printer Setup and Issues > Adding a printer > macOS)

```
Printer Setup and Issues > Adding a printer > macOS

1. Open System Settings, then Printers and Scanners.
2. Click Add Printer, Scanner, or Fax.
3. Select the IP tab.
4. Enter the IP address. Protocol should be IPP. Leave Queue empty.
5. For Use, pick Generic PostScript Printer.
6. Click Add and print a test page.
```

**2. miss** (distance 0.314, kb_other_formats/03-printer-setup-and-issues.pdf)

```
1. Open Settings, then Bluetooth and devices, then Printers and scanners.
2. Click Add device, wait ten seconds, then click Add manually.
3. Choose Add a printer using an IP address or hostname.
4. Enter the IP address from the label. Leave the port name as suggested.
5. When asked for a driver, choose the generic PCL6 driver. Do not download a manufacturer driver; the generic one is faster and is the only one the print server supports.
6. Print a test page. macOS
```

**3. miss** (distance 0.353, kb_other_formats/03-printer-setup-and-issues.pdf)

```
6. Print a test page. macOS
1. Open System Settings, then Printers and Scanners.
2. Click Add Printer, Scanner, or Fax.
3. Select the IP tab.
4. Enter the IP address. Protocol should be IPP. Leave Queue empty.
5. For Use, pick Generic PostScript Printer.
```

### markdown_headers_noprefix

**1. miss** (distance 0.314, kb_other_formats/03-printer-setup-and-issues.pdf)

```
1. Open Settings, then Bluetooth and devices, then Printers and scanners.
2. Click Add device, wait ten seconds, then click Add manually.
3. Choose Add a printer using an IP address or hostname.
4. Enter the IP address from the label. Leave the port name as suggested.
5. When asked for a driver, choose the generic PCL6 driver. Do not download a manufacturer driver; the generic one is faster and is the only one the print server supports.
6. Print a test page. macOS
```

**2. miss** (distance 0.353, kb_other_formats/03-printer-setup-and-issues.pdf)

```
6. Print a test page. macOS
1. Open System Settings, then Printers and Scanners.
2. Click Add Printer, Scanner, or Fax.
3. Select the IP tab.
4. Enter the IP address. Protocol should be IPP. Leave Queue empty.
5. For Use, pick Generic PostScript Printer.
```

**3. HIT** (distance 0.448, kb/03-printer-setup-and-issues.md | Printer Setup and Issues > Adding a printer > macOS)

```
1. Open System Settings, then Printers and Scanners.
2. Click Add Printer, Scanner, or Fax.
3. Select the IP tab.
4. Enter the IP address. Protocol should be IPP. Leave Queue empty.
5. For Use, pick Generic PostScript Printer.
6. Click Add and print a test page.
```

### semantic

**1. miss** (distance 0.346, kb/03-printer-setup-and-issues.md)

```
Print a test page. ### macOS

1. Open System Settings, then Printers and Scanners. 2. Click Add Printer, Scanner, or Fax. 3. Select the IP tab. 4. Enter the IP address. Protocol should be IPP. Leave Queue empty.
```

**2. miss** (distance 0.365, kb_other_formats/03-printer-setup-and-issues.pdf)

```
Print a test page. macOS
1. Open System Settings, then Printers and Scanners. 2. Click Add Printer, Scanner, or Fax. 3. Select the IP tab. 4. Enter the IP address. Protocol should be IPP. Leave Queue empty.
```

**3. miss** (distance 0.476, kb_other_formats/03-printer-setup-and-issues.pdf)

```
Printer Setup and Issues Finding your printer Every office printer has a label on the front with its name and IP address. Printer names follow the pattern SITE-FLOOR-NUMBER, for example AUS-02-03 is the third printer on the second floor in Austin. Always add printers by IP address rather than by name. Name-based discovery depends on a directory service that is often slow and sometimes lists printers that have been retired. Adding a printer Windows
1. Open Settings, then Bluetooth and devices, then Printers and scanners. 2. Click Add device, wait ten seconds, then click Add manually. 3. Choose Add a printer using an IP address or hostname. 4. Enter the IP address from the label. Leave the port name as suggested.
```

## Q8 (context): Which VPN gateway should someone in Bangalore use, and why is its default protocol different?

Must contain, in one chunk: `vpn-in.example.com`, `ISP filtering`

### fixed_200

**1. miss** (distance 0.607, kb/01-vpn-access-guide.md)

```
ol default | Notes |
|---|---|---|---|
| Americas | vpn-us.example.com | UDP | Highest capacity |
| Europe | vpn-eu.example.com | UDP | Maintenance window Sundays 02:00 to 04:00 CET |
| India | vpn-in
```

**2. miss** (distance 0.616, kb/01-vpn-access-guide.md)

```
.example.com | TCP | TCP default because of ISP filtering |
| APAC | vpn-apac.example.com | UDP | Serves Taipei and Seoul |

## Policy

Personal devices may not connect to the VPN. The client checks f
```

**3. miss** (distance 0.651, kb/01-vpn-access-guide.md)

```
house staff do not have VPN enabled by default because their tools are available on the local network only; they can request access through a ticket with manager approval.

The VPN uses split tunnelli
```

### fixed_500_overlap

**1. HIT** (distance 0.577, kb/01-vpn-access-guide.md)

```
ol default | Notes |
|---|---|---|---|
| Americas | vpn-us.example.com | UDP | Highest capacity |
| Europe | vpn-eu.example.com | UDP | Maintenance window Sundays 02:00 to 04:00 CET |
| India | vpn-in.example.com | TCP | TCP default because of ISP filtering |
| APAC | vpn-apac.example.com | UDP | Serves Taipei and Seoul |

## Policy

Personal devices may not connect to the VPN. The client checks for a device certificate that is only installed on company-managed laptops. Attempting to install the
```

**2. miss** (distance 0.643, kb/01-vpn-access-guide.md)

```
hable while the VPN is up or when you are in the office. If the drive letter is missing entirely, see the Shared Drive article.

### Authentication loop

If the client keeps asking for your password after you have entered it correctly, your account may be locked. Use the self-service password portal to unlock it, wait five minutes, then try again.

## Regional gateways

| Region | Gateway | Protocol default | Notes |
|---|---|---|---|
| Americas | vpn-us.example.com | UDP | Highest capacity |
|
```

**3. miss** (distance 0.646, kb/01-vpn-access-guide.md)

```
d drives when the VPN is disconnected.

## Connecting for the first time

1. Open the VPN client from the Start menu on Windows or the Applications folder on macOS.
2. Enter the gateway address shown on your onboarding card. Do not use a gateway from another region; it will connect but be slow.
3. Sign in with your work email and password.
4. Approve the push notification on your registered phone. If you do not receive it within 30 seconds, open the authenticator app and use the six-digit code i
```

### recursive_500

**1. HIT** (distance 0.465, kb/01-vpn-access-guide.md)

```
## Regional gateways

| Region | Gateway | Protocol default | Notes |
|---|---|---|---|
| Americas | vpn-us.example.com | UDP | Highest capacity |
| Europe | vpn-eu.example.com | UDP | Maintenance window Sundays 02:00 to 04:00 CET |
| India | vpn-in.example.com | TCP | TCP default because of ISP filtering |
| APAC | vpn-apac.example.com | UDP | Serves Taipei and Seoul |

## Policy
```

**2. miss** (distance 0.642, kb/01-vpn-access-guide.md)

```
1. Open the VPN client from the Start menu on Windows or the Applications folder on macOS.
2. Enter the gateway address shown on your onboarding card. Do not use a gateway from another region; it will connect but be slow.
3. Sign in with your work email and password.
4. Approve the push notification on your registered phone. If you do not receive it within 30 seconds, open the authenticator app and use the six-digit code instead.
```

**3. miss** (distance 0.689, kb/01-vpn-access-guide.md)

```
The VPN uses split tunnelling. Traffic to internal addresses goes through the tunnel; everything else uses your normal internet connection. This is why video calls still work when the VPN is slow, and why you cannot reach shared drives when the VPN is disconnected.

## Connecting for the first time
```

### markdown_headers

**1. HIT** (distance 0.443, kb/01-vpn-access-guide.md | VPN Access Guide > Regional gateways)

```
VPN Access Guide > Regional gateways

| Region | Gateway | Protocol default | Notes |
|---|---|---|---|
| Americas | vpn-us.example.com | UDP | Highest capacity |
| Europe | vpn-eu.example.com | UDP | Maintenance window Sundays 02:00 to 04:00 CET |
| India | vpn-in.example.com | TCP | TCP default because of ISP filtering |
| APAC | vpn-apac.example.com | UDP | Serves Taipei and Seoul |
```

**2. miss** (distance 0.668, kb/01-vpn-access-guide.md | VPN Access Guide > Connecting for the first time)

```
VPN Access Guide > Connecting for the first time

1. Open the VPN client from the Start menu on Windows or the Applications folder on macOS.
2. Enter the gateway address shown on your onboarding card. Do not use a gateway from another region; it will connect but be slow.
3. Sign in with your work email and password.
4. Approve the push notification on your registered phone. If you do not receive it within 30 seconds, open the authenticator app and use the six-digit code instead.
```

**3. miss** (distance 0.684, kb/01-vpn-access-guide.md | VPN Access Guide > Overview)

```
VPN Access Guide > Overview

by default because their tools are available on the local network only; they can request access through a ticket with manager approval.
```

### markdown_headers_noprefix

**1. HIT** (distance 0.451, kb/01-vpn-access-guide.md | VPN Access Guide > Regional gateways)

```
| Region | Gateway | Protocol default | Notes |
|---|---|---|---|
| Americas | vpn-us.example.com | UDP | Highest capacity |
| Europe | vpn-eu.example.com | UDP | Maintenance window Sundays 02:00 to 04:00 CET |
| India | vpn-in.example.com | TCP | TCP default because of ISP filtering |
| APAC | vpn-apac.example.com | UDP | Serves Taipei and Seoul |
```

**2. miss** (distance 0.642, kb/01-vpn-access-guide.md | VPN Access Guide > Connecting for the first time)

```
1. Open the VPN client from the Start menu on Windows or the Applications folder on macOS.
2. Enter the gateway address shown on your onboarding card. Do not use a gateway from another region; it will connect but be slow.
3. Sign in with your work email and password.
4. Approve the push notification on your registered phone. If you do not receive it within 30 seconds, open the authenticator app and use the six-digit code instead.
```

**3. miss** (distance 0.688, kb/01-vpn-access-guide.md | VPN Access Guide > Overview)

```
The VPN uses split tunnelling. Traffic to internal addresses goes through the tunnel; everything else uses your normal internet connection. This is why video calls still work when the VPN is slow, and why you cannot reach shared drives when the VPN is disconnected.
```

### semantic

**1. HIT** (distance 0.518, kb/01-vpn-access-guide.md)

```
Use the self-service password portal to unlock it, wait five minutes, then try again. ## Regional gateways

| Region | Gateway | Protocol default | Notes |
|---|---|---|---|
| Americas | vpn-us.example.com | UDP | Highest capacity |
| Europe | vpn-eu.example.com | UDP | Maintenance window Sundays 02:00 to 04:00 CET |
| India | vpn-in.example.com | TCP | TCP default because of ISP filtering |
| APAC | vpn-apac.example.com | UDP | Serves Taipei and Seoul |

## Policy

Personal devices may not connect to the VPN. The client checks for a device certificate that is only installed on company-managed laptops.
```

**2. miss** (distance 0.636, kb/01-vpn-access-guide.md)

```
# VPN Access Guide

## Overview

The corporate VPN gives employees secure access to internal systems when working outside the office. All laptops issued after January 2025 ship with the VPN client preinstalled. Older laptops may need a manual install from the Software Center. VPN access is enabled by default for employees in Supply Chain Ops, Logistics, Finance Ops, Planning, and Procurement. Warehouse staff do not have VPN enabled by default because their tools are available on the local network only; they can request access through a ticket with manager approval. The VPN uses split tunnelling. Traffic to internal addresses goes through the tunnel; everything else uses your normal internet connection. This is why video calls still work when the VPN is slow, and why you cannot reach shared drives when the VPN is disconnected. ## Connecting for the first time

1. Open the VPN client from the Start menu on Windows or the Applications folder on macOS. 2. Enter the gateway address shown on your onboarding card. Do not use a gateway from another region; it will connect but be slow. 3. Sign in with your work email and password. 4. Approve the push notification on your registered phone. If you do not receive it within 30 seconds, open the authenticator app and use the six-digit code instead. 5. Wait for the status to show Connected. The first connection downloads a configuration profile and can take up to two minutes. ## Troubleshooting

### VPN disconnects every few minutes

This is almost always a protocol issue on home networks. Open the VPN client, go to Settings, then Connection, and switch the protocol from UDP to TCP. Reconnect. If it still drops, restart the laptop once. If the problem continues on a wired connection too, file a ticket and include the time of the last three disconnects. ### Connected but cannot reach shared drives

Confirm the status shows Connected and not Connecting. Then open File Explorer and reconnect the drive. Shared drives are only reachable while the VPN is up or when you are in the office. If the drive letter is missing entirely, see the Shared Drive article. ### Authentication loop

If the client keeps asking for your password after you have entered it correctly, your account may be locked.
```

**3. miss** (distance 0.820, kb_other_formats/03-printer-setup-and-issues.pdf)

```
5. When asked for a driver, choose the generic PCL6 driver. Do not download a manufacturer driver; the generic one is faster and is the only one the print server supports. 6.
```

## Q9 (context): What is the macOS path for the Finance shared drive?

Must contain, in one chunk: `smb://files.example.com/finance`

### fixed_200

**1. HIT** (distance 0.542, kb/05-collaboration-tools.md)

```
Chain Ops |
| Finance | \\\\files.example.com\\finance | smb://files.example.com/finance | Finance Ops |
| Logistics | \\\\files.example.com\\logistics | smb://files.example.com/logistics | Logistics
```

**2. miss** (distance 0.542, kb/05-collaboration-tools.md)

```
r, Go, Connect to Server, and enter the smb path.

| Drive | Windows path | macOS path | Owner team |
|---|---|---|---|
| Ops shared | \\\\files.example.com\\ops | smb://files.example.com/ops | Supply
```

**3. miss** (distance 0.612, kb/05-collaboration-tools.md)

```
n File Explorer and reconnect the drive. If the drive letter is missing, open File Explorer, right-click This PC, choose Map network drive, and enter the path from the table below. On macOS, use Finde
```

### fixed_500_overlap

**1. HIT** (distance 0.405, kb/05-collaboration-tools.md)

```
n File Explorer and reconnect the drive. If the drive letter is missing, open File Explorer, right-click This PC, choose Map network drive, and enter the path from the table below. On macOS, use Finder, Go, Connect to Server, and enter the smb path.

| Drive | Windows path | macOS path | Owner team |
|---|---|---|---|
| Ops shared | \\\\files.example.com\\ops | smb://files.example.com/ops | Supply Chain Ops |
| Finance | \\\\files.example.com\\finance | smb://files.example.com/finance | Finance
```

**2. HIT** (distance 0.659, kb/05-collaboration-tools.md)

```
Chain Ops |
| Finance | \\\\files.example.com\\finance | smb://files.example.com/finance | Finance Ops |
| Logistics | \\\\files.example.com\\logistics | smb://files.example.com/logistics | Logistics |
| Warehouse | \\\\files.example.com\\wh | smb://files.example.com/wh | Warehouse |

### Access denied on a folder

Folder permissions are managed by the owner team listed in the table, not by IT. Ask the team lead to add you. IT can tell you who the owner is but cannot grant access.
```

**3. miss** (distance 0.761, kb/05-collaboration-tools.md)

```
cause.

### Mailbox full

The mailbox limit is 50 GB. Outlook warns at 45 GB. Empty Deleted Items and Junk first, then sort the inbox by size and remove large attachments you no longer need. Archive folders do not count against the limit; move old mail there.

## Shared drives

### Drive not mapping

Shared drives require the VPN when you are outside the office. Connect to the VPN first, then open File Explorer and reconnect the drive. If the drive letter is missing, open File Explorer, right-c
```

### recursive_500

**1. HIT** (distance 0.486, kb/05-collaboration-tools.md)

```
| Drive | Windows path | macOS path | Owner team |
|---|---|---|---|
| Ops shared | \\\\files.example.com\\ops | smb://files.example.com/ops | Supply Chain Ops |
| Finance | \\\\files.example.com\\finance | smb://files.example.com/finance | Finance Ops |
| Logistics | \\\\files.example.com\\logistics | smb://files.example.com/logistics | Logistics |
| Warehouse | \\\\files.example.com\\wh | smb://files.example.com/wh | Warehouse |

### Access denied on a folder
```

**2. miss** (distance 0.583, kb/05-collaboration-tools.md)

```
## Shared drives

### Drive not mapping

Shared drives require the VPN when you are outside the office. Connect to the VPN first, then open File Explorer and reconnect the drive. If the drive letter is missing, open File Explorer, right-click This PC, choose Map network drive, and enter the path from the table below. On macOS, use Finder, Go, Connect to Server, and enter the smb path.
```

**3. miss** (distance 0.678, kb/01-vpn-access-guide.md)

```
### Connected but cannot reach shared drives

Confirm the status shows Connected and not Connecting. Then open File Explorer and reconnect the drive. Shared drives are only reachable while the VPN is up or when you are in the office. If the drive letter is missing entirely, see the Shared Drive article.

### Authentication loop
```

### markdown_headers

**1. HIT** (distance 0.452, kb/05-collaboration-tools.md | Collaboration Tools: Teams, Outlook, and Shared Drives > Shared drives > Drive not mapping)

```
Collaboration Tools: Teams, Outlook, and Shared Drives > Shared drives > Drive not mapping

| Drive | Windows path | macOS path | Owner team |
|---|---|---|---|
| Ops shared | \\\\files.example.com\\ops | smb://files.example.com/ops | Supply Chain Ops |
| Finance | \\\\files.example.com\\finance | smb://files.example.com/finance | Finance Ops |
| Logistics | \\\\files.example.com\\logistics | smb://files.example.com/logistics | Logistics |
| Warehouse | \\\\files.example.com\\wh | smb://files.example.com/wh | Warehouse |
```

**2. miss** (distance 0.558, kb/05-collaboration-tools.md | Collaboration Tools: Teams, Outlook, and Shared Drives > Shared drives > Drive not mapping)

```
Collaboration Tools: Teams, Outlook, and Shared Drives > Shared drives > Drive not mapping

Shared drives require the VPN when you are outside the office. Connect to the VPN first, then open File Explorer and reconnect the drive. If the drive letter is missing, open File Explorer, right-click This PC, choose Map network drive, and enter the path from the table below. On macOS, use Finder, Go, Connect to Server, and enter the smb path.
| Drive | Windows path | macOS path | Owner team |
|---|---|---|---|
```

**3. miss** (distance 0.685, kb/01-vpn-access-guide.md | VPN Access Guide > Troubleshooting > Connected but cannot reach shared drives)

```
VPN Access Guide > Troubleshooting > Connected but cannot reach shared drives

Confirm the status shows Connected and not Connecting. Then open File Explorer and reconnect the drive. Shared drives are only reachable while the VPN is up or when you are in the office. If the drive letter is missing entirely, see the Shared Drive article.
```

### markdown_headers_noprefix

**1. HIT** (distance 0.438, kb/05-collaboration-tools.md | Collaboration Tools: Teams, Outlook, and Shared Drives > Shared drives > Drive not mapping)

```
| Drive | Windows path | macOS path | Owner team |
|---|---|---|---|
| Ops shared | \\\\files.example.com\\ops | smb://files.example.com/ops | Supply Chain Ops |
| Finance | \\\\files.example.com\\finance | smb://files.example.com/finance | Finance Ops |
| Logistics | \\\\files.example.com\\logistics | smb://files.example.com/logistics | Logistics |
| Warehouse | \\\\files.example.com\\wh | smb://files.example.com/wh | Warehouse |
```

**2. miss** (distance 0.553, kb/05-collaboration-tools.md | Collaboration Tools: Teams, Outlook, and Shared Drives > Shared drives > Drive not mapping)

```
Shared drives require the VPN when you are outside the office. Connect to the VPN first, then open File Explorer and reconnect the drive. If the drive letter is missing, open File Explorer, right-click This PC, choose Map network drive, and enter the path from the table below. On macOS, use Finder, Go, Connect to Server, and enter the smb path.
| Drive | Windows path | macOS path | Owner team |
|---|---|---|---|
```

**3. miss** (distance 0.659, kb/01-vpn-access-guide.md | VPN Access Guide > Troubleshooting > Connected but cannot reach shared drives)

```
Confirm the status shows Connected and not Connecting. Then open File Explorer and reconnect the drive. Shared drives are only reachable while the VPN is up or when you are in the office. If the drive letter is missing entirely, see the Shared Drive article.
```

### semantic

**1. HIT** (distance 0.513, kb/05-collaboration-tools.md)

```
On macOS, use Finder, Go, Connect to Server, and enter the smb path. | Drive | Windows path | macOS path | Owner team |
|---|---|---|---|
| Ops shared | \\\\files.example.com\\ops | smb://files.example.com/ops | Supply Chain Ops |
| Finance | \\\\files.example.com\\finance | smb://files.example.com/finance | Finance Ops |
| Logistics | \\\\files.example.com\\logistics | smb://files.example.com/logistics | Logistics |
| Warehouse | \\\\files.example.com\\wh | smb://files.example.com/wh | Warehouse |

### Access denied on a folder

Folder permissions are managed by the owner team listed in the table, not by IT. Ask the team lead to add you.
```

**2. miss** (distance 0.708, kb/05-collaboration-tools.md)

```
# Collaboration Tools: Teams, Outlook, and Shared Drives

## Teams

### Audio not working in meetings

Open Teams, go to Settings, then Devices, and check that the correct microphone and speaker are selected. Headsets sometimes register as two devices; pick the one with "Hands-Free" in the name for calls. On macOS, also open System Settings, Privacy and Security, Microphone, and confirm Teams is allowed. If other people cannot hear you but you can hear them, it is almost always the microphone permission. ### Camera shows a black screen

Close every other application that could be using the camera, especially browser tabs with video. On Windows, open Settings, Privacy, Camera, and confirm desktop apps are allowed. If the camera works in another app but not Teams, sign out of Teams and sign back in. ## Outlook

### Keeps asking for password

Close Outlook. On Windows, open Credential Manager, choose Windows Credentials, and remove every entry that starts with MicrosoftOffice. Reopen Outlook and sign in once. On macOS, open Keychain Access and delete the entries for Exchange, then reopen Outlook. If you changed your password recently and skipped the lock-and-unlock step, that is the cause. ### Mailbox full

The mailbox limit is 50 GB. Outlook warns at 45 GB. Empty Deleted Items and Junk first, then sort the inbox by size and remove large attachments you no longer need. Archive folders do not count against the limit; move old mail there. ## Shared drives

### Drive not mapping

Shared drives require the VPN when you are outside the office. Connect to the VPN first, then open File Explorer and reconnect the drive. If the drive letter is missing, open File Explorer, right-click This PC, choose Map network drive, and enter the path from the table below.
```

**3. miss** (distance 0.787, kb_other_formats/03-printer-setup-and-issues.pdf)

```
Print a test page. macOS
1. Open System Settings, then Printers and Scanners. 2. Click Add Printer, Scanner, or Fax. 3. Select the IP tab. 4. Enter the IP address. Protocol should be IPP. Leave Queue empty.
```
