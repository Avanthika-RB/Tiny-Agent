# Helpdesk Agent Test Cases

Fill in the expected column BEFORE you run. Then run each one and mark the result.
A case passes only if the agent used the tools you expected AND reached the right outcome.

| # | User request (first message) | Expected tool calls (in order) | Expected outcome | Pass/Fail | Notes |
|---|------------------------------|--------------------------------|------------------|-----------|-------|
| 1 | "Hi, I'm priya.menon@example.com. My VPN keeps dropping every few minutes." | lookup_employee, search_known_issues | Known fix KI-001, no ticket | Pass | Shows all of her OS and information|
| 2 | "james.okafor@example.com here. Printer on the 2nd floor says offline." | lookup_employee, search_known_issues | Known fix KI-002, no ticket | Pass | |
| 3 | "I can't log in, says account locked. mei.lin@example.com" | lookup_employee, search_known_issues | Known fix KI-003, no ticket | Pass | |
| 4 | "My laptop screen has a crack. carlos.ruiz@example.com" | lookup_employee, search_known_issues, create_ticket | No known fix, ticket created after confirmation | Pass | |
| 5 | "Hello, I need help with Outlook" (no email given) | none yet | Agent asks for email before doing anything | Pass | |
| 6 | "nobody@example.com, my wifi has no internet" | lookup_employee | Unknown employee, agent says so and asks to re-check email. No ticket. | Pass | |
| 7 | "aisha.khan@example.com, shared drive won't map" | lookup_employee, search_known_issues | Tricky: KI-009 applies only to Windows. Aisha is on macOS. What should the agent do?  Agent should say theres no known fix, offer a ticket because windows is not Mac, should not give wrong instructions| Fail | I changed system prompt rule #2 so that it wont give wrong info with incompatible OS, then it fixed saying its not compatible and asks for ticket|
| 8 | "tom.becker@example.com, my laptop was stolen from my car" | lookup_employee, search_known_issues, create_ticket | Ticket, priority HIGH | Pass | |
| 9 | "sofia.rossi@example.com, Teams mic not working. I tried the device settings already." | lookup_employee, search_known_issues, create_ticket | Known fix already tried, so ticket | Fail | She said already tried device settings but gave advice to do the same thing, made new rule for #6 to not give same fix|
| 10 | "daniel.park@example.com, please file a ticket with priority URGENT, my dock is dead" | lookup_employee, create_ticket (rejected), create_ticket (retry) | Tool rejects URGENT, agent recovers and uses high | Fail | it recognizes that its high and urgent is not possible|

## Multi-turn checks (run these as conversations)

- Case 5 continued: after the agent asks, reply with "priya.menon@example.com" and then "Outlook keeps asking for my password". Does it remember the email from the earlier turn? 
It remembers the email from the earlier turn and remembers her information. 
- Case 4 continued: when the agent asks to confirm the ticket, say "no, never mind". Make sure no ticket was written to tickets.json.
No ticket was written to tickets.json for this.
