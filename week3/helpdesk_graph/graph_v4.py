"""graph_v4: graph_v3 plus parallelism, a subgraph, and long-term memory.

Day 4 adds:
  - Send fan-out: on new_issue, the outage check and the known-issue search run
    at the same time, then join again. They both write to one field, `found`,
    so it needs a reducer (merge_found) to combine their results.
  - A triage subgraph: check_outage, search_issues, suggest_fix, inform_outage
    and propose_ticket live in their own StateGraph with their own state
    (TriageState), added to the main graph as one node called "triage".
  - Long-term memory with a Store: when an employee says a fix did not work,
    it is saved under their email. On a NEW thread, that fix is never suggested again.

    python graph_v4.py                     chat in a new conversation
    python graph_v4.py --thread NAME       continue (or start) the conversation called NAME
    python graph_v4.py --timing            time the parallel triage against the sequential one
    python graph_v4.py --draw              save pictures of the graph to graph_v4.png and graph_v4_triage.png

    In the chat: 'state', 'history', 'memory', 'travel <n> <low|medium|high>', 'new', 'quit'
    The Store is InMemoryStore, so memory lasts until you quit. Use 'new' to test it across threads.
"""

import operator
import os
import re
import sys
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.config import get_store
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command, Send, interrupt
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from tools import (
    create_ticket,
    find_active_outages,
    find_employee,
    find_known_issues,
    get_ticket_status,
    reset_password,
)

MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
RECURSION_LIMIT = 25
MAX_EMAIL_ATTEMPTS = 2
CHECKPOINT_DB = str(Path(__file__).parent / "checkpoints.db")


#state is split into 2, main graph state and triagestate for triage subgraph. 
class State(TypedDict):
    messages: Annotated[list, add_messages]   # shared with triage
    employee: dict | None                      # shared with triage
    intent: Literal["new_issue", "ticket_status", "password_reset", "other"] | None
    fix_failed: bool                           # the employee says the last fix did not work
    attempts: int
    pending_action: dict | None                # shared: triage's propose_ticket sets it
    tool_result: str | None
    last_suggested: str | None                 # shared: the fix id suggest_fix gave in THIS thread


def merge_found(old: dict, new: dict) -> dict:
    """The fan-in reducer. check_outage and search_issues run in the SAME step and
    both write `found`. Without a reducer LangGraph would not know which one wins
    and raises InvalidUpdateError. This keeps both: {"outage": ...} + {"known_issues": ...}."""
    return {**(old or {}), **(new or {})}


class TriageState(TypedDict):
    # shared with the parent (same names)
    messages: Annotated[list, add_messages]
    employee: dict | None
    pending_action: dict | None
    last_suggested: str | None
    # private to triage
    found: Annotated[dict, merge_found]        # outage, known_issues, skipped (fixes that failed before)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
load_dotenv()
api_key = os.environ.get("NVIDIA_API_KEY")
if not api_key:
    raise SystemExit("NVIDIA_API_KEY is not set. Add it to the .env file.")

model = ChatOpenAI(
    model=MODEL,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key,
    temperature=0,
    max_retries=5,
)


# Schemas for structured output: the model must answer by filling these in.
class IntentSchema(BaseModel):
    """What the employee wants in their latest message."""
    intent: Literal["new_issue", "ticket_status", "password_reset", "other"] = Field(
        description=(
            "new_issue: reporting an IT problem, or saying a suggested fix did not work. "
            "ticket_status: asking about an existing ticket. "
            "password_reset: ONLY when the employee explicitly asks for their password to be reset or changed. "
            "An app or Outlook that keeps asking for a password is a new_issue, not a password_reset. "
            "other: anything else, such as thanks or small talk."
        )
    )
    fix_failed: bool = Field(
        description="True only if the employee's LATEST message says a fix the assistant suggested did not work."
    )


class RelevantIssues(BaseModel):
    """Which candidate fixes really match the employee's problem."""
    issue_ids: list[str] = Field(
        description="Ids of fixes that match the problem and that the employee has NOT already tried. Empty list if none."
    )


class TicketDraft(BaseModel):
    """A support ticket to propose to the employee."""
    summary: str = Field(description="One sentence describing the problem.")
    priority: Literal["low", "medium", "high"] = Field(
        description="high for security issues such as lost or stolen devices, medium for things that block work, low otherwise."
    )


# with_structured_output makes the model return one of these objects instead of text.
# method="function_calling" is needed on NVIDIA endpoints (see STARTER_README.md).
classifier = model.with_structured_output(IntentSchema, method="function_calling")
issue_picker = model.with_structured_output(RelevantIssues, method="function_calling")
ticket_writer = model.with_structured_output(TicketDraft, method="function_calling")

#helpers
EMAIL_PATTERN = r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"   # stops before a trailing full stop
YES_WORDS = {"yes", "y", "yeah", "yep", "sure", "ok", "okay", "go ahead", "please do", "do it"}

# Which words in a problem description mean an outage's service is involved.
OUTAGE_KEYWORDS = {
    "Office Wi-Fi": ["wifi", "wi-fi", "internet", "network", "wireless"],
    "VPN gateway": ["vpn"],
    "Printer fleet": ["printer", "print", "printing"],
    "Shared drives": ["shared drive", "network drive", "mapped drive"],
}


def human_texts(state):
    return [m.content for m in state["messages"] if isinstance(m, HumanMessage)]


def problem_text(state):
    """Everything the employee has said in this conversation, as one string."""
    return " ".join(human_texts(state))


def last_user_text(state):
    texts = human_texts(state)
    return texts[-1] if texts else ""


def said_yes(state):
    text = last_user_text(state).strip().lower().rstrip(".!")
    return text in YES_WORDS or text.startswith("yes")


def outage_matches_problem(outage, text):
    """True if the problem mentions the service that is down."""
    text = text.lower()
    return any(word in text for word in OUTAGE_KEYWORDS.get(outage["service"], []))


#nodes main graph
def identify(state: State):
    """Find an email in the employee's latest message and look it up."""
    match = re.search(EMAIL_PATTERN, last_user_text(state))
    if match is None:
        return {}  # no email given yet: nothing changes, after_identify sends us to ask_email
    employee = find_employee(match.group())
    if employee is None:
        return {"attempts": state.get("attempts", 0) + 1}
    return {"employee": employee}


def ask_email(state: State):
    if state.get("attempts", 0) == 0:
        text = "Hi! Before I can help, I need to identify you. What's your work email?"
    else:
        text = "I couldn't find an employee with that email. Could you double-check it and send it again?"
    return {"messages": [AIMessage(content=text)]}


def handoff(state: State):
    text = (
        "I wasn't able to verify your email after two tries, so I can't continue here. "
        "A member of the helpdesk team will follow up with you."
    )
    return {"messages": [AIMessage(content=text)]}


def classify(state: State):
    """Ask the model what the employee wants, and whether they are saying the last fix failed."""
    conversation = "\n".join(
        f"{'Employee' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in state["messages"]
    )
    result = classifier.invoke(
        [
            SystemMessage(content="Classify what the employee wants in their LATEST message, using the whole conversation for context."),
            HumanMessage(content=conversation),
        ]
    )
    return {"intent": result.intent, "fix_failed": result.fix_failed, "tool_result": None}


def memory_namespace(email):
    """Store namespace for one employee. Everything about them lives under their email.
    Namespace labels may not contain dots (LangGraph raises InvalidNamespaceError),
    so priya.menon@example.com becomes priya_menon@example_com."""
    return ("employees", email.replace(".", "_"), "fix_outcomes")


def record_failure(state: State):
    """LONG-TERM MEMORY WRITE. The employee said the fix we suggested did not work.
    Save it in the Store under their email, so every future thread knows."""
    store = get_store()
    issue_id = state["last_suggested"]
    store.put(
        memory_namespace(state["employee"]["email"]),
        issue_id,                                                    # key: one entry per fix
        {"issue_id": issue_id, "outcome": "failed", "date": date.today().isoformat()},
    )
    return {"last_suggested": None}


#triage subgraph
def check_outage(state: TriageState):
    """Branch 1 of the fan-out: is there an active outage that explains the problem?"""
    location = state["employee"]["location"]
    relevant = [
        o for o in find_active_outages(location)
        if outage_matches_problem(o, problem_text(state))
    ]
    return {"found": {"outage": relevant[0] if relevant else None}}


def search_issues(state: TriageState):
    """Branch 2 of the fan-out: search known issues, drop fixes that already failed
    for this employee (LONG-TERM MEMORY READ), then let the model keep only fixes that fit."""
    candidates = find_known_issues(problem_text(state))

    store = get_store()
    past = store.search(memory_namespace(state["employee"]["email"]), limit=100)
    failed = {item.key: item.value["date"] for item in past if item.value["outcome"] == "failed"}
    skipped = [{"id": i["id"], "date": failed[i["id"]]} for i in candidates if i["id"] in failed]
    candidates = [i for i in candidates if i["id"] not in failed]

    if not candidates:
        return {"found": {"known_issues": [], "skipped": skipped}}
    listing = "\n".join(f"{i['id']}: {i['title']}. Fix: {i['fix']}" for i in candidates)
    choice = issue_picker.invoke(
        [
            SystemMessage(content="Pick which candidate fixes match the employee's problem. Leave out any fix the employee says they already tried, even in different words."),
            HumanMessage(content=f"Employee's messages: {problem_text(state)}\n\nCandidate fixes:\n{listing}"),
        ]
    )
    kept = [i for i in candidates if i["id"] in choice.issue_ids]
    return {"found": {"known_issues": kept, "skipped": skipped}}


def join(state: TriageState):
    """The fan-in point. It runs once, after BOTH branches have finished.
    It changes nothing; after_join reads the merged `found` and picks the next node."""
    return {}


def inform_outage(state: TriageState):
    o = state["found"]["outage"]
    text = (
        f"There's an active outage that explains this: {o['service']} in {o['location']} ({o['id']}). "
        f"{o['message']} It's expected to be fixed by {o['eta']}. No ticket is needed."
    )
    return {"messages": [AIMessage(content=text)]}


def suggest_fix(state: TriageState):
    """Show the first fix that applies to the employee's OS. The text comes from the data, never the model."""
    os_name = state["employee"]["os"]
    issue = next(i for i in state["found"]["known_issues"] if os_name in i["applies_to"])
    text = (
        f"There's a known fix for this ({issue['id']}: {issue['title']}), and it applies to your {os_name}:\n"
        f"{issue['fix']}\n\nIf that doesn't help, tell me and I'll file a ticket."
    )
    # last_suggested is shared, so the parent remembers which fix to record if it fails.
    return {"messages": [AIMessage(content=text)], "last_suggested": issue["id"]}


def propose_ticket(state: TriageState):
    """Draft a ticket. The approve node (in the main graph) asks before anything is created."""
    draft = ticket_writer.invoke(
        [
            SystemMessage(content="Draft a support ticket for this employee's IT problem."),
            HumanMessage(content=problem_text(state)),
        ]
    )
    pending = {
        "tool": "create_ticket",
        "args": {
            "employee_email": state["employee"]["email"],
            "summary": draft.summary,
            "priority": draft.priority,
        },
    }
    skipped = state["found"].get("skipped", [])
    if skipped:
        earlier = ", ".join(f"{s['id']} (tried {s['date']})" for s in skipped)
        it_them = "them" if len(skipped) > 1 else "it"
        intro = f"You told us before that {earlier} didn't work, so I won't suggest {it_them} again. I'd like to file a ticket:\n"
    else:
        intro = "I couldn't find a known fix that applies here, so I'd like to file a ticket:\n"
    text = intro + f"- Summary: {draft.summary}\n- Priority: {draft.priority}"
    return {"pending_action": pending, "last_suggested": None, "messages": [AIMessage(content=text)]}


# --- triage edge functions ---
def fan_out(state: TriageState):
    """Send: start BOTH branches at once, each with its own copy of the state."""
    return [Send("check_outage", state), Send("search_issues", state)]


def after_join(state: TriageState):
    """Outage first (it explains everything), then the OS check in code, else a ticket."""
    found = state["found"]
    if found.get("outage"):
        return "inform_outage"
    os_name = state["employee"]["os"]
    for issue in found.get("known_issues", []):
        if os_name in issue["applies_to"]:
            return "suggest_fix"
    return "propose_ticket"


def build_triage(parallel=True):
    """parallel=True is the real one. parallel=False runs the same nodes one after
    the other, only so --timing can compare the two."""
    t = StateGraph(TriageState)
    for name, node in [
        ("check_outage", check_outage), ("search_issues", search_issues), ("join", join),
        ("inform_outage", inform_outage), ("suggest_fix", suggest_fix), ("propose_ticket", propose_ticket),
    ]:
        t.add_node(name, node)
    if parallel:
        t.add_conditional_edges(START, fan_out, ["check_outage", "search_issues"])
        t.add_edge(["check_outage", "search_issues"], "join")   # wait for BOTH, then join
    else:
        t.add_edge(START, "check_outage")
        t.add_edge("check_outage", "search_issues")
        t.add_edge("search_issues", "join")
    t.add_conditional_edges("join", after_join, ["inform_outage", "suggest_fix", "propose_ticket"])
    for end_node in ["inform_outage", "suggest_fix", "propose_ticket"]:
        t.add_edge(end_node, END)
    return t.compile()


triage_graph = build_triage(parallel=True)


#nodes more main graph
def propose_reset(state: State):
    """Prepare the reset. The approve node asks for confirmation before anything happens."""
    email = state["employee"]["email"]
    return {"pending_action": {"tool": "reset_password", "args": {"email": email}}}


def approve(state: State) -> Command[Literal["run_tools", "respond"]]:
    """The approval gate. Every create_ticket and reset_password passes through here.

    interrupt() pauses the whole graph and saves it in the checkpointer. Nothing
    after this line runs until someone resumes the graph with
    Command(resume="yes") or Command(resume="no"). When it resumes, this node
    runs again from the top, and interrupt() returns the human's answer.
    """
    pending = state["pending_action"]
    if pending["tool"] == "create_ticket":
        args = pending["args"]
        question = f"Create a ticket for {args['employee_email']}: \"{args['summary']}\", priority {args['priority']}?"
    else:
        question = f"Reset the password for {pending['args']['email']}?"

    answer = interrupt({"question": question, "action": pending})

    if str(answer).strip().lower() in YES_WORDS or str(answer).strip().lower().startswith("yes"):
        return Command(goto="run_tools")
    return Command(
        update={"pending_action": None, "tool_result": "Cancelled at the approval step, so nothing was done. Tell them it has been cancelled."},
        goto="respond",
    )


ACTIONS = {"create_ticket": create_ticket, "reset_password": reset_password}


def run_tools(state: State):
    """Approved: run the pending tool, then clear it."""
    pending = state["pending_action"]
    result = ACTIONS[pending["tool"]].invoke(pending["args"])
    return {"tool_result": result, "pending_action": None}


def status_lookup(state: State):
    match = re.search(r"TKT-\d+", problem_text(state), re.IGNORECASE)
    if match is None:
        return {"tool_result": "The employee did not give a ticket id, so ask them for it."}
    return {"tool_result": get_ticket_status.invoke({"ticket_id": match.group()})}


def respond(state: State):
    """Let the model turn a tool result (or small talk) into a short, friendly reply."""
    result = state.get("tool_result") or "No tool was run. Reply briefly and offer help with IT problems."
    reply = model.invoke(
        [
            SystemMessage(content="You are an IT helpdesk assistant talking directly to the employee (say 'you', never 'the employee'). Write a short, friendly reply based only on the result given. Never invent ticket ids, links, or details that are not in the result."),
            HumanMessage(content=f"Employee's latest message: {last_user_text(state)}\nResult: {result}"),
        ]
    )
    return {"messages": [AIMessage(content=reply.content)], "tool_result": None}


#edge functions main graph
def route_start(state: State):
    if state.get("employee") is None:
        if state.get("attempts", 0) >= MAX_EMAIL_ATTEMPTS:
            return "handoff"
        return "identify"
    return "classify"


def after_identify(state: State):
    """Behaviour 3, bounded retry: a counter in state drives the edge."""
    if state.get("employee") is not None:
        return "classify"
    if state.get("attempts", 0) >= MAX_EMAIL_ATTEMPTS:
        return "handoff"
    return "ask_email"


def route_intent(state: State):
    """Intent routing. A new issue that says the last fix failed is recorded first."""
    if state["intent"] == "new_issue":
        if state.get("fix_failed") and state.get("last_suggested"):
            return "record_failure"
        return "triage"
    return {
        "ticket_status": "status_lookup",
        "password_reset": "propose_reset",
        "other": "respond",
    }[state["intent"]]


def after_triage(state: State):
    """If triage proposed a ticket, it must go through the approval gate."""
    return "approve" if state.get("pending_action") else END


#graph
builder = StateGraph(State)
for name, node in [
    ("identify", identify), ("ask_email", ask_email), ("handoff", handoff),
    ("classify", classify), ("record_failure", record_failure),
    ("triage", triage_graph),              # the whole subgraph is ONE node here
    ("propose_reset", propose_reset), ("approve", approve), ("run_tools", run_tools),
    ("status_lookup", status_lookup), ("respond", respond),
]:
    builder.add_node(name, node)

builder.add_conditional_edges(START, route_start, ["handoff", "identify", "classify"])
builder.add_conditional_edges("identify", after_identify, ["classify", "handoff", "ask_email"])
builder.add_conditional_edges("classify", route_intent,
                              ["record_failure", "triage", "status_lookup", "propose_reset", "respond"])
builder.add_edge("record_failure", "triage")
builder.add_conditional_edges("triage", after_triage, ["approve", END])
builder.add_edge("propose_reset", "approve")
builder.add_edge("run_tools", "respond")
builder.add_edge("status_lookup", "respond")
for end_node in ["ask_email", "handoff", "respond"]:
    builder.add_edge(end_node, END)

#run
def make_config(thread_id):
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT}


def describe(node_name, update):
    """A one-line summary of what a node changed, so you can follow the path."""
    if not update:
        return ""
    parts = []
    if update.get("employee"):
        parts.append(f"employee={update['employee']['name']} ({update['employee']['os']}, {update['employee']['location']})")
    if "attempts" in update:
        parts.append(f"attempts={update['attempts']}")
    if update.get("intent"):
        parts.append(f"intent={update['intent']}, fix_failed={update.get('fix_failed')}")
    found = update.get("found") or {}
    if "outage" in found:
        parts.append(f"outage={found['outage']['id'] if found['outage'] else None}")
    if "known_issues" in found:
        parts.append(f"known_issues={[i['id'] for i in found['known_issues']]}")
    if found.get("skipped"):
        parts.append(f"skipped (failed before)={[s['id'] for s in found['skipped']]}")
    if update.get("last_suggested"):
        parts.append(f"last_suggested={update['last_suggested']}")
    if node_name == "record_failure":
        parts.append("saved the failed fix to the Store")
    if update.get("pending_action"):
        parts.append(f"pending_action={update['pending_action']['tool']}")
    if update.get("tool_result"):
        parts.append(f"result={update['tool_result']}")
    return ", ".join(parts)


def run(graph, graph_input, config):
    """Stream one run, printing each node (subgraph nodes too). Returns the interrupt payload if the graph paused."""
    paused = None
    replies = []
    # subgraphs=True also streams the nodes INSIDE triage. namespace is () for the
    # main graph and ("triage:<id>",) for nodes inside the subgraph.
    for namespace, chunk in graph.stream(graph_input, config=config, stream_mode="updates", subgraphs=True):
        for node_name, update in chunk.items():
            if node_name == "__interrupt__":
                paused = update[0].value
                print("  [approve] paused, waiting for a human")
                continue
            if namespace:
                print(f"    triage > [{node_name}] {describe(node_name, update)}")
            elif node_name == "triage":
                # The subgraph's output repeats the whole conversation, so its replies
                # are taken from the triage > lines above instead.
                print("  [triage] finished")
                continue
            else:
                print(f"  [{node_name}] {describe(node_name, update)}")
            for message in (update or {}).get("messages", []):
                if isinstance(message, AIMessage):
                    replies.append(message.content)
    for reply in replies:
        print(f"\nAgent: {reply}")
    return paused


def ask_human(graph, paused, config):
    """Show what is about to happen, read yes/no, and resume the graph with it."""
    while paused is not None:
        print(f"\n*** APPROVAL NEEDED: {paused['question']}")
        try:
            answer = input("Approve? (yes/no): ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        paused = run(graph, Command(resume=answer), config)


def show_state(graph, config):
    snapshot = graph.get_state(config)
    values = snapshot.values
    print(f"  next node(s): {snapshot.next or '(none, finished)'}")
    for key in ["employee", "intent", "fix_failed", "attempts", "pending_action", "last_suggested", "tool_result"]:
        value = values.get(key)
        if key == "employee" and value:
            value = f"{value['name']} ({value['os']}, {value['location']})"
        print(f"  {key}: {value}")
    print(f"  messages: {len(values.get('messages', []))}")


def show_memory(store):
    """Everything in the long-term Store, for every employee."""
    items = store.search((), limit=1000)
    if not items:
        print("  (the Store is empty)")
    for item in items:
        print(f"  {item.namespace} {item.key}: {item.value}")


def show_history(graph, config):
    """List every checkpoint for this thread, newest first, numbered for 'travel'."""
    history = list(graph.get_state_history(config))
    for n, snap in enumerate(history):
        pending = snap.values.get("pending_action")
        extra = f" pending={pending['tool']} priority={pending['args'].get('priority')}" if pending else ""
        print(f"  [{n}] step {snap.metadata.get('step')}: next={snap.next or '(end)'}, "
              f"messages={len(snap.values.get('messages', []))}{extra}")
    return history


def time_travel(graph, config, n, priority):
    """Go back to checkpoint n, change the pending ticket's priority, and resume from there."""
    history = list(graph.get_state_history(config))
    if not 0 <= n < len(history):
        print("  No such checkpoint. Type 'history' to see the numbers.")
        return None
    past = history[n]
    pending = past.values.get("pending_action")
    if not pending or pending["tool"] != "create_ticket" or "approve" not in past.next:
        print("  Pick a checkpoint whose next node is approve and that has a pending create_ticket.")
        return None
    changed = {**pending, "args": {**pending["args"], "priority": priority}}
    # update_state writes a NEW checkpoint branching off the old one. Its config
    # points at that new branch, so resuming continues from there.
    new_config = graph.update_state(past.config, {"pending_action": changed})
    print(f"  Forked from checkpoint [{n}] with priority={priority}. Resuming...")
    return run(graph, None, new_config)


def chat(graph, thread_id, store):
    config = make_config(thread_id)
    print(f"IT Helpdesk (graph_v4). Conversation (thread): {thread_id}")
    print(f"To continue this conversation later, run: python graph_v4.py --thread {thread_id}")
    print("Commands: 'state', 'history', 'memory', 'travel <n> <low|medium|high>', 'new', 'quit'.")

    # If this thread was killed while waiting for approval, ask again now.
    snapshot = graph.get_state(config)
    if snapshot.interrupts:
        print("(This conversation was paused waiting for approval.)")
        ask_human(graph, snapshot.interrupts[0].value, config)
    elif snapshot.values.get("messages"):
        print(f"(Continuing a saved conversation with {len(snapshot.values['messages'])} messages.)")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        command = user_input.lower().split()
        if command[0] in ("quit", "exit"):
            break
        if command[0] == "new":
            thread_id = str(uuid.uuid4())[:8]
            config = make_config(thread_id)
            print(f"(Started a new conversation: {thread_id}. Continue it later with --thread {thread_id})")
            continue
        if command[0] == "state":
            show_state(graph, config)
            continue
        if command[0] == "memory":
            show_memory(store)
            continue
        if command[0] == "history":
            show_history(graph, config)
            continue
        if command[0] == "travel" and len(command) == 3 and command[1].isdigit():
            paused = time_travel(graph, config, int(command[1]), command[2])
            ask_human(graph, paused, config)
            continue
        try:
            paused = run(graph, {"messages": [{"role": "user", "content": user_input}]}, config)
            ask_human(graph, paused, config)
        except GraphRecursionError:
            print(f"\nAgent: Sorry, I couldn't finish that within {RECURSION_LIMIT} steps.")


TIMING_CASES = [
    ("priya.menon@example.com", "Outlook keeps asking for my password"),
    ("james.okafor@example.com", "wifi is dead at my desk"),
    ("aisha.khan@example.com", "my shared drive is not mapping"),
]


def timing():
    """Run the triage subgraph on the same cases, parallel vs sequential, and compare wall time."""
    store = InMemoryStore()
    versions = {
        "parallel": build_triage(parallel=True),
        "sequential": build_triage(parallel=False),
    }
    totals = {name: 0.0 for name in versions}
    for email, problem in TIMING_CASES:
        employee = find_employee(email)
        for name, sub in versions.items():
            graph = StateGraph(TriageState)
            graph.add_node("triage", sub)
            graph.add_edge(START, "triage")
            graph = graph.compile(store=store)
            start = time.perf_counter()
            graph.invoke({"messages": [HumanMessage(content=problem)], "employee": employee})
            seconds = time.perf_counter() - start
            totals[name] += seconds
            print(f"  {name:<10} {seconds:6.2f}s  {email}: {problem}")
    for name, total in totals.items():
        print(f"{name} total: {total:.2f}s")


def main():
    args = sys.argv[1:]
    if args == ["--timing"]:
        timing()
        return
    store = InMemoryStore()   # long-term memory: shared by EVERY thread while the program runs
    with SqliteSaver.from_conn_string(CHECKPOINT_DB) as saver:
        graph = builder.compile(checkpointer=saver, store=store)
        if args == ["--draw"]:
            folder = Path(__file__).parent
            (folder / "graph_v4.png").write_bytes(graph.get_graph().draw_mermaid_png())
            (folder / "graph_v4_triage.png").write_bytes(triage_graph.get_graph().draw_mermaid_png())
            print(f"Saved graph_v4.png and graph_v4_triage.png in {folder}")
        elif len(args) == 2 and args[0] == "--thread":
            chat(graph, args[1], store)
        else:
            chat(graph, str(uuid.uuid4())[:8], store)


if __name__ == "__main__":
    main()
