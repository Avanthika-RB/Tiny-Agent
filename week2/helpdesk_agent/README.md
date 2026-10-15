# Helpdesk Agent Starter

Starter data for the Week 2 IT Helpdesk Triage Agent. The agent code is yours to write.

## What is here

- data/employees.json: 8 employees with team, laptop, OS, location, and VPN flag.
- data/known_issues.json: 10 known issues. Each has keywords for matching, the OS it applies to, and a fix.
- data/tickets.json: empty list. Your create_ticket tool appends here.
- test_cases.md: 10 test cases with expected tool calls and outcomes, plus two multi-turn checks.

## Hints, not rules

- Your search_known_issues tool can simply count keyword hits per issue and return the top 2 or 3. Return the id, title, and fix as a string the model can read.
- Notice the applies_to field. Case 7 in the test file exists because of it. Decide whether your tool filters by OS, or whether you let the model work it out from the employee lookup.
- Your create_ticket tool should validate priority and return an error string, not raise. Case 10 tests this.
- Ticket ids: generate them yourself, for example TKT-1001, TKT-1002. Never let the model make them up.
- Feel free to add employees or issues. If you do, add a test case that uses them.
