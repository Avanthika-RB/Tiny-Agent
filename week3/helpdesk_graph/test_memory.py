"""Day 4 test: a fix that failed last week must not be suggested on a new thread.

    python test_memory.py

Uses the real model. Nothing is approved, so no tickets are created.
Test 1 puts a failure dated 7 days ago straight into the Store, then starts a new thread.
Test 2 does it through conversation: thread A gets a fix, says it didn't work, then
thread B (a different thread, same employee) asks about the same problem.
"""

from datetime import date, timedelta

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

import graph_v4

EMAIL = "priya.menon@example.com"
PROBLEM = f"{EMAIL}, Outlook keeps asking for my password"
FIX_ID = "KI-004"   # the known fix for Outlook password prompts


def fresh_graph():
    """A new graph with empty memory, so tests cannot affect each other."""
    store = InMemoryStore()
    return graph_v4.builder.compile(checkpointer=InMemorySaver(), store=store), store


def say(graph, thread_id, text):
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": graph_v4.RECURSION_LIMIT}
    graph.invoke({"messages": [{"role": "user", "content": text}]}, config)
    return graph.get_state(config)


def agent_said(snapshot, text):
    return any(text in m.content for m in snapshot.values["messages"] if isinstance(m, AIMessage))


def what_happened(snapshot):
    """A short description of how the run ended, for the PASS line."""
    if snapshot.values.get("pending_action"):
        return "proposed a ticket"
    if snapshot.values.get("last_suggested"):
        return f"suggested a different fix, {snapshot.values['last_suggested']}"
    return "no fix and no ticket"


def test_failure_from_last_week():
    graph, store = fresh_graph()
    last_week = (date.today() - timedelta(days=7)).isoformat()
    store.put(graph_v4.memory_namespace(EMAIL), FIX_ID,
              {"issue_id": FIX_ID, "outcome": "failed", "date": last_week})

    snapshot = say(graph, "new-thread", PROBLEM)

    assert not agent_said(snapshot, f"known fix for this ({FIX_ID}"), "suggested a fix that failed last week"
    # Passing means KI-004 was not suggested. The agent may still offer a DIFFERENT fix
    # (such as KI-003) or propose a ticket. Both are fine.
    print(f"PASS test_failure_from_last_week ({what_happened(snapshot)})")


def test_failure_remembered_across_threads():
    graph, store = fresh_graph()

    first = say(graph, "thread-A", PROBLEM)
    assert agent_said(first, FIX_ID), "thread A should suggest the known fix first"
    say(graph, "thread-A", "I tried that and it didn't work")
    saved = store.get(graph_v4.memory_namespace(EMAIL), FIX_ID)
    assert saved and saved.value["outcome"] == "failed", "the failure was not saved to the Store"

    second = say(graph, "thread-B", PROBLEM)
    assert not agent_said(second, f"known fix for this ({FIX_ID}"), "thread B suggested the failed fix again"
    print(f"PASS test_failure_remembered_across_threads (thread B: {what_happened(second)})")


if __name__ == "__main__":
    test_failure_from_last_week()
    test_failure_remembered_across_threads()
    print("All memory tests passed.")


#python graph_v4.py --timing
#PS C:\Users\avant\Desktop\CS\Tiny-Agent\week3\helpdesk_graph> python graph_v4.py --timing
 # parallel     2.58s  priya.menon@example.com: Outlook keeps asking for my password
 # sequential   3.94s  priya.menon@example.com: Outlook keeps asking for my password
 # parallel     4.86s  james.okafor@example.com: wifi is dead at my desk
 # sequential   2.60s  james.okafor@example.com: wifi is dead at my desk
 # parallel     3.02s  aisha.khan@example.com: my shared drive is not mapping
 # sequential   2.94s  aisha.khan@example.com: my shared drive is not mapping
#parallel total: 10.47s
#sequential total: 9.49s

#Notes to write: Checkpointer memory vs Store memory. One sentence each, then when you would use which.
#checkpointer memory saves the whole state like msgs, employee, last_suggested with sqliteSaver and survives a restart.
#inmemoryStore doesnt save whole state and only facts chosen to save, it doesnt survive a restart but can look up info about the person.
#use checkpointer if you need message history for current convo, store for needing saved info about the person and their fix/issues. 