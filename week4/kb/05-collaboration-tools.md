# Collaboration Tools: Teams, Outlook, and Shared Drives

## Teams

### Audio not working in meetings

Open Teams, go to Settings, then Devices, and check that the correct microphone and speaker are selected. Headsets sometimes register as two devices; pick the one with "Hands-Free" in the name for calls. On macOS, also open System Settings, Privacy and Security, Microphone, and confirm Teams is allowed. If other people cannot hear you but you can hear them, it is almost always the microphone permission.

### Camera shows a black screen

Close every other application that could be using the camera, especially browser tabs with video. On Windows, open Settings, Privacy, Camera, and confirm desktop apps are allowed. If the camera works in another app but not Teams, sign out of Teams and sign back in.

## Outlook

### Keeps asking for password

Close Outlook. On Windows, open Credential Manager, choose Windows Credentials, and remove every entry that starts with MicrosoftOffice. Reopen Outlook and sign in once. On macOS, open Keychain Access and delete the entries for Exchange, then reopen Outlook. If you changed your password recently and skipped the lock-and-unlock step, that is the cause.

### Mailbox full

The mailbox limit is 50 GB. Outlook warns at 45 GB. Empty Deleted Items and Junk first, then sort the inbox by size and remove large attachments you no longer need. Archive folders do not count against the limit; move old mail there.

## Shared drives

### Drive not mapping

Shared drives require the VPN when you are outside the office. Connect to the VPN first, then open File Explorer and reconnect the drive. If the drive letter is missing, open File Explorer, right-click This PC, choose Map network drive, and enter the path from the table below. On macOS, use Finder, Go, Connect to Server, and enter the smb path.

| Drive | Windows path | macOS path | Owner team |
|---|---|---|---|
| Ops shared | \\\\files.example.com\\ops | smb://files.example.com/ops | Supply Chain Ops |
| Finance | \\\\files.example.com\\finance | smb://files.example.com/finance | Finance Ops |
| Logistics | \\\\files.example.com\\logistics | smb://files.example.com/logistics | Logistics |
| Warehouse | \\\\files.example.com\\wh | smb://files.example.com/wh | Warehouse |

### Access denied on a folder

Folder permissions are managed by the owner team listed in the table, not by IT. Ask the team lead to add you. IT can tell you who the owner is but cannot grant access.
