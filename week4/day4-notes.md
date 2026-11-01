# Day 4 notes

## First 3 chunks of kb/01-vpn-access-guide.md, side by side

| | fixed_200 | recursive_500 | markdown_headers |
|---|---|---|---|
| 1 | **chunk 0 (200 chars)**<br># VPN Access Guide<br><br>## Overview<br><br>The corporate VPN gives employees secure access to internal systems when working outside the office. All laptops issued after January 2025 ship with the VPN client pre | **chunk 0 (31 chars)**<br># VPN Access Guide<br><br>## Overview | **chunk 0 (527 chars)**<br>VPN Access Guide > Overview<br><br>The corporate VPN gives employees secure access to internal systems when working outside the office. All laptops issued after January 2025 ship with the VPN client preinstalled. Older laptops may need a manual install from the Software Center. VPN access is enabled by default for employees in Supply Chain Ops, Logistics, Finance Ops, Planning, and Procurement. Warehouse staff do not have VPN enabled by default because their tools are available on the local network only; they can request access |
| 2 | **chunk 1 (200 chars)**<br>installed. Older laptops may need a manual install from the Software Center. VPN access is enabled by default for employees in Supply Chain Ops, Logistics, Finance Ops, Planning, and Procurement. Ware | **chunk 1 (498 chars)**<br>The corporate VPN gives employees secure access to internal systems when working outside the office. All laptops issued after January 2025 ship with the VPN client preinstalled. Older laptops may need a manual install from the Software Center. VPN access is enabled by default for employees in Supply Chain Ops, Logistics, Finance Ops, Planning, and Procurement. Warehouse staff do not have VPN enabled by default because their tools are available on the local network only; they can request access | **chunk 1 (164 chars)**<br>VPN Access Guide > Overview<br><br>by default because their tools are available on the local network only; they can request access through a ticket with manager approval. |
| 3 | **chunk 2 (200 chars)**<br>house staff do not have VPN enabled by default because their tools are available on the local network only; they can request access through a ticket with manager approval.<br><br>The VPN uses split tunnelli | **chunk 2 (135 chars)**<br>by default because their tools are available on the local network only; they can request access through a ticket with manager approval. | **chunk 2 (294 chars)**<br>VPN Access Guide > Overview<br><br>The VPN uses split tunnelling. Traffic to internal addresses goes through the tunnel; everything else uses your normal internet connection. This is why video calls still work when the VPN is slow, and why you cannot reach shared drives when the VPN is disconnected. |

(Created with `python rag/ingest.py first3 kb/01`.)

## fixed_200

- Every 200 characters is its own chunk
- half of a word can be in the next chunk if its cut off

## recursive_500

- New chunk after heading
- Repeat/overlap with the ending of chunk 1 and chunk 2

## markdown_headers

- Header is on each chunk
- Then continues the paragraphs with next chunk
