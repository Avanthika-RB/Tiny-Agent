# Week 3 Starter

Two small data files for the three new tools on Day 2. Copy them into your helpdesk_graph/data/
folder next to employees.json, known_issues.json and tickets.json from Week 2.

- data/outages.json: four outages, two active and two resolved. check_outages(location) should
  return only ACTIVE outages whose location matches the employee's location. Note that Austin
  and Bangalore have active outages. Look at which employees are in those cities.
- data/password_resets.json: empty list. reset_password(email) appends an entry with the email,
  a timestamp, and a fake temporary password or reset link. It must only ever be called after
  the approve node says yes.

Suggested new test cases (add to your Week 2 test_cases.md to make 15):

| # | First message | Expected path | Expected outcome |
|---|---------------|---------------|------------------|
| 11 | "james.okafor@example.com, wifi is dead at my desk" | identify -> classify(new_issue) -> check_outage (Austin, active) -> inform_outage -> END | Told about OUT-101, no search, no ticket |
| 12 | "carlos.ruiz@example.com, any update on TKT-1001?" | identify -> classify(ticket_status) -> status_lookup -> respond | Status of the ticket, or "no such ticket" if you reset tickets.json |
| 13 | "mei.lin@example.com, I need my password reset" then approve with "yes" | identify -> classify(password_reset) -> approve (interrupt) -> run_tools -> respond | Entry appears in password_resets.json |
| 14 | Same as 13 but answer "no" at the approval | ... -> approve -> respond | Nothing written, polite cancellation |
| 15 | "ghost@example.com, my screen is broken" then "still.ghost@example.com" | identify -> ask_email -> identify -> handoff -> END | After 2 failed lookups, handoff message, no further tool calls |

Also re-run case 7 (Aisha, macOS, shared drive) after Day 2. It should now pass because of the
OS check in your edge function, not because of a prompt rule.

## Setup gotchas (read before you lose two hours on them)

1. Structured output on NVIDIA endpoints (Day 2). If `with_structured_output(IntentSchema)`
   errors with something about response_format or json_schema, pass
   `method="function_calling"`. The NVIDIA endpoint supports tool calling; not every model
   supports JSON-schema mode.

2. Second model for fallback (Day 5). Any other chat model on build.nvidia.com works, for
   example `meta/llama-3.3-70b-instruct`. Same API key, same base_url.

3. LangGraph Studio (Day 5). Needs the CLI: `pip install "langgraph-cli[inmem]"`. Then
   `langgraph dev` in the folder with langgraph.json. It opens Studio in your browser,
   signed in with your LangSmith account, pointed at localhost. If the browser blocks it,
   use Chrome or Firefox, not Safari.

4. SqliteSaver (Day 3). `pip install langgraph-checkpoint-sqlite`. It is a context manager:
   `with SqliteSaver.from_conn_string("checkpoints.db") as saver:` and compile the graph
   inside the block. Delete checkpoints.db when you want a clean start.

5. Long-term memory design (Day 4). The Store only helps if something writes to it. When the
   user says a fix did not work, record {issue_id, outcome: "failed", date} under the
   employee's namespace. On a later thread, read it before suggesting fixes. You decide
   whether the write happens in a node or inside a tool. Either is defensible.

6. LLM-as-judge (Day 6). Your evaluator can call the same NVIDIA model. Give it the
   question, the agent's reply, and a short rubric, and ask for a score of 0 or 1 with one
   sentence of reasoning. Keep temperature at 0.
