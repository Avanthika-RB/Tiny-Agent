# VPN Access Guide

## Overview

The corporate VPN gives employees secure access to internal systems when working outside the office. All laptops issued after January 2025 ship with the VPN client preinstalled. Older laptops may need a manual install from the Software Center. VPN access is enabled by default for employees in Supply Chain Ops, Logistics, Finance Ops, Planning, and Procurement. Warehouse staff do not have VPN enabled by default because their tools are available on the local network only; they can request access through a ticket with manager approval.

The VPN uses split tunnelling. Traffic to internal addresses goes through the tunnel; everything else uses your normal internet connection. This is why video calls still work when the VPN is slow, and why you cannot reach shared drives when the VPN is disconnected.

## Connecting for the first time

1. Open the VPN client from the Start menu on Windows or the Applications folder on macOS.
2. Enter the gateway address shown on your onboarding card. Do not use a gateway from another region; it will connect but be slow.
3. Sign in with your work email and password.
4. Approve the push notification on your registered phone. If you do not receive it within 30 seconds, open the authenticator app and use the six-digit code instead.
5. Wait for the status to show Connected. The first connection downloads a configuration profile and can take up to two minutes.

## Troubleshooting

### VPN disconnects every few minutes

This is almost always a protocol issue on home networks. Open the VPN client, go to Settings, then Connection, and switch the protocol from UDP to TCP. Reconnect. If it still drops, restart the laptop once. If the problem continues on a wired connection too, file a ticket and include the time of the last three disconnects.

### Connected but cannot reach shared drives

Confirm the status shows Connected and not Connecting. Then open File Explorer and reconnect the drive. Shared drives are only reachable while the VPN is up or when you are in the office. If the drive letter is missing entirely, see the Shared Drive article.

### Authentication loop

If the client keeps asking for your password after you have entered it correctly, your account may be locked. Use the self-service password portal to unlock it, wait five minutes, then try again.

## Regional gateways

| Region | Gateway | Protocol default | Notes |
|---|---|---|---|
| Americas | vpn-us.example.com | UDP | Highest capacity |
| Europe | vpn-eu.example.com | UDP | Maintenance window Sundays 02:00 to 04:00 CET |
| India | vpn-in.example.com | TCP | TCP default because of ISP filtering |
| APAC | vpn-apac.example.com | UDP | Serves Taipei and Seoul |

## Policy

Personal devices may not connect to the VPN. The client checks for a device certificate that is only installed on company-managed laptops. Attempting to install the client on a personal machine will fail at step 3 above with error code 1103.
