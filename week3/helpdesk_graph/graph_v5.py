"""graph_v5: graph_v4 made robust, split into a supervisor and two specialist agents.

Day 5 adds:
  - Tool errors: search_known_issues now fails 30% of the time at random. The
    search runs in a ToolNode with a RetryPolicy: a failure is retried (up to 3
    tries). If every try fails, handle_tool_errors turns the error into a
    ToolMessage, so the graph carries on and the model sees the error instead of a crash.
  - Model fallback: every model call is primary.with_fallbacks([backup]).
    Run with --broken-primary to point the primary at a model that does not exist.
  - Supervisor: a supervisor node decides which specialist works next, and when
    the job is done. The specialists are subgraphs:
        Triage agent     outages, known issues, propose a ticket   (Day 4 subgraph)
        TicketOps agent  create a ticket, ticket status, password reset (with the approve gate)
  - Studio: langgraph.json points at the `graph` variable at the bottom of this file.
    Run `langgraph dev` in this folder.

    python graph_v5.py                     chat in a new conversation
    python graph_v5.py --thread NAME       continue (or start) the conversation called NAME
    python graph_v5.py --broken-primary    chat with a primary model that does not exist (proves the fallback)
    python graph_v5.py --fallback-demo     one model call with the broken primary, prints which model answered
    python graph_v5.py --draw              save graph_v5.png, graph_v5_triage.png, graph_v5_ticketops.png

    In the chat: 'state', 'history', 'memory', 'travel <n> <low|medium|high>', 'new', 'quit'
"""

import os
import random
import re
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.config import get_store
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.runtime import get_runtime
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command, RetryPolicy, Send, interrupt
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from tools import (
    KNOWN_ISSUES_FILE,
    create_ticket,
    find_active_outages,
    find_employee,
    get_ticket_status,
    load_json,
    reset_password,
)
from tools import search_known_issues as real_search_known_issues

MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
BACKUP_MODEL = "meta/muse-glimmer-30b"      # the starter README's suggestion
BROKEN_MODEL = "nvidia/this-model-does-not-exist"  # used by --broken-primary
RECURSION_LIMIT = 40
MAX_EMAIL_ATTEMPTS = 2
SEARCH_FAILURE_RATE = 0.3
SEARCH_ATTEMPTS = 3
CHECKPOINT_DB = str(Path(__file__).parent / "checkpoints.db")


# ===========================================================================
# STATE
# Main graph: State. Triage agent: TriageState. TicketOps agent: OpsState.
# A key with the same name in a specialist's state and in State is shared.
# ===========================================================================
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]   # shared with both specialists
    employee: dict | None                      # shared with both specialists
    attempts: int
    route: str | None                          # the supervisor's latest decision (for printing and Studio)
    worked: list                               # specialists already sent in for the latest message
    ops_task: str | None                       # shared with TicketOps: what it should do
    fix_failed: bool                           # shared with Triage: the employee says the last fix failed
    pending_action: dict | None                # shared: Triage proposes, TicketOps approves and runs
    last_suggested: str | None                 # shared with Triage: the fix id suggested in this thread


def merge_found(old: dict, new: dict) -> dict:
    """Fan-in reducer: check_outage and the search branch both write `found`."""
    return {**(old or {}), **(new or {})}


class TriageState(TypedDict):
    # shared
    messages: Annotated[list[AnyMessage], add_messages]
    employee: dict | None
    pending_action: dict | None
    last_suggested: str | None
    fix_failed: bool
    # private
    found: Annotated[dict, merge_found]            # outage, known_issues, skipped, search_error
    search_messages: Annotated[list, add_messages]  # the search tool call and its ToolMessage


class OpsState(TypedDict):
    # shared
    messages: Annotated[list[AnyMessage], add_messages]
    employee: dict | None
    pending_action: dict | None
    ops_task: str | None
    # private
    tool_result: str | None


# ---------------------------------------------------------------------------
# Models, each with a fallback
# ---------------------------------------------------------------------------
load_dotenv()
api_key = os.environ.get("NVIDIA_API_KEY")
if not api_key:
    raise SystemExit("NVIDIA_API_KEY is not set. Add it to the .env file.")

BROKEN_PRIMARY = "--broken-primary" in sys.argv or "--fallback-demo" in sys.argv
PRIMARY_MODEL = BROKEN_MODEL if BROKEN_PRIMARY else MODEL


def make_model(name, retries):
    return ChatOpenAI(
        model=name,
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        temperature=0,
        max_retries=retries,
    )


primary = make_model(PRIMARY_MODEL, 5)
backup = make_model(BACKUP_MODEL, 2)

# with_fallbacks: if the primary raises (wrong model name, 500 after its retries,
# timeout), the same input is sent to the backup instead.
model = primary.with_fallbacks([backup])


def structured(schema):
    """Structured output with a fallback. The fallback has to be built for each schema,
    because with_fallbacks wraps a finished runnable, not a bare model."""
    return primary.with_structured_output(schema, method="function_calling").with_fallbacks(
        [backup.with_structured_output(schema, method="function_calling")]
    )


# Schemas for structured output
class Route(BaseModel):
    """The supervisor's decision about the employee's latest message."""
    next: Literal["triage", "ticketops", "done"] = Field(
        description=(
            "triage: a NEW IT problem, or the employee says a suggested fix did not work. "
            "ticketops: the employee asks about an existing ticket, or explicitly asks for a password reset. "
            "done: the latest message has been fully handled already, or it is only thanks or small talk."
        )
    )
    ops_task: Literal["ticket_status", "password_reset", "none"] = Field(
        description="When next is ticketops: ticket_status or password_reset. Otherwise none."
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
    summary: str = Field(description="One sentence describing the problem. Do not include the email address.")
    priority: Literal["low", "medium", "high"] = Field(
        description="high for security issues such as lost or stolen devices, medium for things that block work, low otherwise."
    )


router = structured(Route)
issue_picker = structured(RelevantIssues)
ticket_writer = structured(TicketDraft)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
EMAIL_PATTERN = r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
YES_WORDS = {"yes", "y", "yeah", "yep", "sure", "ok", "okay", "go ahead", "please do", "do it"}
OUTAGE_KEYWORDS = {
    "Office Wi-Fi": ["wifi", "wi-fi", "internet", "network", "wireless"],
    "VPN gateway": ["vpn"],
    "Printer fleet": ["printer", "print", "printing"],
    "Shared drives": ["shared drive", "network drive", "mapped drive"],
}


def human_texts(state):
    return [m.text for m in state["messages"] if isinstance(m, HumanMessage)]   # .text works for plain strings and for Studio's list-of-blocks content


def problem_text(state):
    return " ".join(human_texts(state))


def last_user_text(state):
    texts = human_texts(state)
    return texts[-1] if texts else ""


def conversation_text(state):
    return "\n".join(
        f"{'Employee' if isinstance(m, HumanMessage) else 'Assistant'}: {m.text}"
        for m in state["messages"]
    )


def outage_matches_problem(outage, text):
    text = text.lower()
    return any(word in text for word in OUTAGE_KEYWORDS.get(outage["service"], []))


def issue_by_id(issue_id):
    return next((i for i in load_json(KNOWN_ISSUES_FILE) if i["id"] == issue_id), None)


def memory_namespace(email):
    """Store namespace for one employee (namespace labels may not contain dots)."""
    return ("employees", email.replace(".", "_"), "fix_outcomes")


# ===========================================================================
# THE FLAKY TOOL
# ===========================================================================
class SearchUnavailable(Exception):
    """A transient failure: the known-issues service timed out."""


@tool
def search_known_issues(query: str) -> str:
    """Search the list of known IT issues for fixes that match a problem description.

    Args:
        query: A short description of the problem.
    """
    if random.random() < SEARCH_FAILURE_RATE:
        raise SearchUnavailable("the known-issues service timed out")
    return real_search_known_issues.invoke({"query": query})


def handle_search_error(error: SearchUnavailable) -> str:
    """handle_tool_errors for the search ToolNode.

    Before the last try: re-raise, so the node FAILS and its RetryPolicy runs it again.
    On the last try: return text. ToolNode turns that text into a ToolMessage with
    status="error", so the graph carries on and the model sees what went wrong.
    """
    attempt = get_runtime().execution_info.node_attempt
    if attempt < SEARCH_ATTEMPTS:
        print(f"      (search_known_issues failed on try {attempt}: {error}. Retrying...)")
        raise error
    print(f"      (search_known_issues failed on try {attempt}: {error}. Giving up.)")
    return f"Error: search_known_issues failed {attempt} times ({error}). No fixes could be looked up."


# ===========================================================================
# MAIN GRAPH NODES
# ===========================================================================
def new_turn(state: State):
    """Every new message starts a fresh round for the supervisor."""
    return {"worked": [], "ops_task": None, "route": None}


def identify(state: State):
    """Find an email in the employee's latest message and look it up."""
    match = re.search(EMAIL_PATTERN, last_user_text(state))
    if match is None:
        return {}
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


def supervisor(state: State) -> Command[Literal["triage", "ticketops", "finish"]]:
    """The supervisor. Picks the next specialist, or decides the job is done.

    Two rules are code, because they must hold every time:
      1. A ticket Triage proposed always goes to TicketOps (the only agent that may
         create tickets, and only through the approve gate).
      2. No specialist runs twice for the same message, so the agents cannot loop.
    Everything else is the model's judgement.
    """
    worked = state.get("worked", [])

    if state.get("pending_action") and "ticketops" not in worked:
        return Command(
            update={"route": "ticketops (create_ticket)", "ops_task": "create_ticket", "worked": worked + ["ticketops"]},
            goto="ticketops",
        )

    decision = router.invoke(
        [
            SystemMessage(content=(
                "You are the supervisor of an IT helpdesk with two specialist agents. "
                "Decide who handles the employee's LATEST message next, or whether it is done. "
                "An app or Outlook that keeps asking for a password is a triage problem, not a password reset."
            )),
            HumanMessage(content=(
                f"Conversation:\n{conversation_text(state)}\n\n"
                f"Specialists that have already worked on the latest message: {', '.join(worked) or 'none'}"
            )),
        ]
    )

    goto = decision.next
    if goto in worked or (goto == "ticketops" and decision.ops_task == "none"):
        goto = "done"
    if goto == "done":
        return Command(update={"route": "done"}, goto="finish")

    update = {"route": goto, "worked": worked + [goto]}
    if goto == "triage":
        update["fix_failed"] = decision.fix_failed
    else:
        update["ops_task"] = decision.ops_task
    return Command(update=update, goto=goto)


def finish(state: State):
    """The supervisor said done. If no specialist replied to this message, answer it briefly."""
    if state.get("worked"):
        return {}
    reply = model.invoke(
        [
            SystemMessage(content="You are an IT helpdesk assistant talking directly to the employee. Reply in one or two friendly sentences and offer help with IT problems."),
            HumanMessage(content=last_user_text(state)),
        ]
    )
    return {"messages": [AIMessage(content=reply.content)]}


# ===========================================================================
# TRIAGE AGENT (subgraph)
# ===========================================================================
def record_failure(state: TriageState):
    """Long-term memory write, only when the employee says the last fix failed."""
    if not (state.get("fix_failed") and state.get("last_suggested")):
        return {}
    issue_id = state["last_suggested"]
    get_store().put(
        memory_namespace(state["employee"]["email"]),
        issue_id,
        {"issue_id": issue_id, "outcome": "failed", "date": date.today().isoformat()},
    )
    return {"last_suggested": None, "fix_failed": False}


def fan_out(state: TriageState):
    """Send: start the outage check and the search at the same time."""
    return [Send("check_outage", state), Send("plan_search", state)]


def check_outage(state: TriageState):
    location = state["employee"]["location"]
    relevant = [
        o for o in find_active_outages(location)
        if outage_matches_problem(o, problem_text(state))
    ]
    return {"found": {"outage": relevant[0] if relevant else None}}


def plan_search(state: TriageState):
    """Write the tool call for the ToolNode to run. The query is the employee's own words."""
    call = AIMessage(
        content="",
        tool_calls=[{"name": "search_known_issues", "args": {"query": problem_text(state)}, "id": f"search-{uuid.uuid4().hex[:8]}"}],
    )
    return {"search_messages": [call]}


# The ToolNode runs search_known_issues. It reads and writes search_messages (a
# private key) instead of messages, so tool calls never clutter the conversation.
search_tools = ToolNode(
    [search_known_issues],
    messages_key="search_messages",
    handle_tool_errors=handle_search_error,
)
search_retry = RetryPolicy(max_attempts=SEARCH_ATTEMPTS, initial_interval=0.5, retry_on=SearchUnavailable)


def pick_issues(state: TriageState):
    """Read the ToolMessage. Drop fixes that failed before (Store). Let the model keep fixes that fit."""
    result = state["search_messages"][-1]
    if result.status == "error":
        return {"found": {"known_issues": [], "skipped": [], "search_error": result.content}}

    lines = {m.group(1): m.group(0) for m in re.finditer(r"^(KI-\d+):.*$", result.content, re.M)}

    past = get_store().search(memory_namespace(state["employee"]["email"]), limit=100)
    failed = {item.key: item.value["date"] for item in past if item.value["outcome"] == "failed"}
    skipped = [{"id": i, "date": failed[i]} for i in lines if i in failed]
    remaining = {i: line for i, line in lines.items() if i not in failed}

    if not remaining:
        return {"found": {"known_issues": [], "skipped": skipped}}
    choice = issue_picker.invoke(
        [
            SystemMessage(content="Pick which candidate fixes match the employee's problem. Leave out any fix the employee says they already tried, even in different words."),
            HumanMessage(content=f"Employee's messages: {problem_text(state)}\n\nSearch results:\n" + "\n".join(remaining.values())),
        ]
    )
    kept = [issue_by_id(i) for i in remaining if i in choice.issue_ids]
    return {"found": {"known_issues": [i for i in kept if i], "skipped": skipped}}


def join(state: TriageState):
    """Fan-in: runs once both branches are done."""
    return {}


def after_join(state: TriageState):
    """Outage first, then the OS check in code, else a ticket."""
    found = state["found"]
    if found.get("outage"):
        return "inform_outage"
    os_name = state["employee"]["os"]
    for issue in found.get("known_issues", []):
        if os_name in issue["applies_to"]:
            return "suggest_fix"
    return "propose_ticket"


def inform_outage(state: TriageState):
    o = state["found"]["outage"]
    text = (
        f"There's an active outage that explains this: {o['service']} in {o['location']} ({o['id']}). "
        f"{o['message']} It's expected to be fixed by {o['eta']}. No ticket is needed."
    )
    return {"messages": [AIMessage(content=text)]}


def suggest_fix(state: TriageState):
    os_name = state["employee"]["os"]
    issue = next(i for i in state["found"]["known_issues"] if os_name in i["applies_to"])
    text = (
        f"There's a known fix for this ({issue['id']}: {issue['title']}), and it applies to your {os_name}:\n"
        f"{issue['fix']}\n\nIf that doesn't help, tell me and I'll file a ticket."
    )
    return {"messages": [AIMessage(content=text)], "last_suggested": issue["id"]}


def propose_ticket(state: TriageState):
    """Draft a ticket and hand it to the supervisor (pending_action). TicketOps creates it."""
    found = state["found"]
    note = ""
    if found.get("search_error"):
        note = f"\nNote: {found['search_error']}"
    draft = ticket_writer.invoke(
        [
            SystemMessage(content="Draft a support ticket for this employee's IT problem."),
            HumanMessage(content=problem_text(state) + note),
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
    skipped = found.get("skipped", [])
    if found.get("search_error"):
        intro = "I couldn't search the known fixes just now (the search service kept failing), so I'd like to file a ticket:\n"
    elif skipped:
        earlier = ", ".join(f"{s['id']} (tried {s['date']})" for s in skipped)
        it_them = "them" if len(skipped) > 1 else "it"
        intro = f"You told us before that {earlier} didn't work, so I won't suggest {it_them} again. I'd like to file a ticket:\n"
    else:
        intro = "I couldn't find a known fix that applies here, so I'd like to file a ticket:\n"
    text = intro + f"- Summary: {draft.summary}\n- Priority: {draft.priority}"
    return {"pending_action": pending, "last_suggested": None, "messages": [AIMessage(content=text)]}


def build_triage():
    t = StateGraph(TriageState)
    t.add_node("record_failure", record_failure)
    t.add_node("check_outage", check_outage)
    t.add_node("plan_search", plan_search)
    t.add_node("search_tools", search_tools, retry_policy=search_retry)
    t.add_node("pick_issues", pick_issues)
    t.add_node("join", join)
    t.add_node("inform_outage", inform_outage)
    t.add_node("suggest_fix", suggest_fix)
    t.add_node("propose_ticket", propose_ticket)

    t.add_edge(START, "record_failure")
    t.add_conditional_edges("record_failure", fan_out, ["check_outage", "plan_search"])
    t.add_edge("plan_search", "search_tools")
    t.add_edge("search_tools", "pick_issues")
    t.add_edge(["check_outage", "pick_issues"], "join")   # wait for BOTH branches
    t.add_conditional_edges("join", after_join, ["inform_outage", "suggest_fix", "propose_ticket"])
    for end_node in ["inform_outage", "suggest_fix", "propose_ticket"]:
        t.add_edge(end_node, END)
    return t.compile()


# ===========================================================================
# TICKETOPS AGENT (subgraph)
# ===========================================================================
def propose_reset(state: OpsState):
    return {"pending_action": {"tool": "reset_password", "args": {"email": state["employee"]["email"]}}}


def approve(state: OpsState) -> Command[Literal["run_tools", "respond"]]:
    """The approval gate (Day 3), now inside TicketOps. interrupt() pauses the whole
    graph, including the parent, until Command(resume=...) arrives."""
    pending = state["pending_action"]
    if pending["tool"] == "create_ticket":
        args = pending["args"]
        question = f"Create a ticket for {args['employee_email']}: \"{args['summary']}\", priority {args['priority']}?"
    else:
        question = f"Reset the password for {pending['args']['email']}?"

    answer = str(interrupt({"question": question, "action": pending})).strip().lower()

    if answer in YES_WORDS or answer.startswith("yes"):
        return Command(goto="run_tools")
    return Command(
        update={"pending_action": None, "tool_result": "Cancelled at the approval step, so nothing was done. Tell them it has been cancelled."},
        goto="respond",
    )


ACTIONS = {"create_ticket": create_ticket, "reset_password": reset_password}


def run_tools(state: OpsState):
    pending = state["pending_action"]
    result = ACTIONS[pending["tool"]].invoke(pending["args"])
    return {"tool_result": result, "pending_action": None}


def status_lookup(state: OpsState):
    match = re.search(r"TKT-\d+", problem_text(state), re.IGNORECASE)
    if match is None:
        return {"tool_result": "The employee did not give a ticket id, so ask them for it."}
    return {"tool_result": get_ticket_status.invoke({"ticket_id": match.group()})}


def respond(state: OpsState):
    result = state.get("tool_result") or "Nothing was done. Offer help with IT problems."
    reply = model.invoke(
        [
            SystemMessage(content="You are an IT helpdesk assistant talking directly to the employee (say 'you', never 'the employee'). Write a short, friendly reply based only on the result given. Never invent ticket ids, links, or details that are not in the result."),
            HumanMessage(content=f"Employee's latest message: {last_user_text(state)}\nResult: {result}"),
        ]
    )
    return {"messages": [AIMessage(content=reply.content)]}


def route_ops(state: OpsState):
    return {
        "create_ticket": "approve",
        "password_reset": "propose_reset",
        "ticket_status": "status_lookup",
    }[state["ops_task"]]


def build_ticketops():
    o = StateGraph(OpsState)
    for name, node in [
        ("propose_reset", propose_reset), ("approve", approve), ("run_tools", run_tools),
        ("status_lookup", status_lookup), ("respond", respond),
    ]:
        o.add_node(name, node)
    o.add_conditional_edges(START, route_ops, ["approve", "propose_reset", "status_lookup"])
    o.add_edge("propose_reset", "approve")
    o.add_edge("run_tools", "respond")
    o.add_edge("status_lookup", "respond")
    o.add_edge("respond", END)
    return o.compile()


triage_agent = build_triage()
ticketops_agent = build_ticketops()


# ===========================================================================
# MAIN GRAPH EDGE FUNCTIONS AND WIRING
# ===========================================================================
def route_start(state: State):
    if state.get("employee") is None:
        if state.get("attempts", 0) >= MAX_EMAIL_ATTEMPTS:
            return "handoff"
        return "identify"
    return "supervisor"


def after_identify(state: State):
    if state.get("employee") is not None:
        return "supervisor"
    if state.get("attempts", 0) >= MAX_EMAIL_ATTEMPTS:
        return "handoff"
    return "ask_email"


builder = StateGraph(State)
for name, node in [
    ("new_turn", new_turn), ("identify", identify), ("ask_email", ask_email), ("handoff", handoff),
    ("supervisor", supervisor), ("finish", finish),
    ("triage", triage_agent), ("ticketops", ticketops_agent),
]:
    builder.add_node(name, node)

builder.add_edge(START, "new_turn")
builder.add_conditional_edges("new_turn", route_start, ["handoff", "identify", "supervisor"])
builder.add_conditional_edges("identify", after_identify, ["supervisor", "handoff", "ask_email"])
# supervisor has no edges here: its Command(goto=...) picks triage, ticketops or finish.
builder.add_edge("triage", "supervisor")      # every specialist reports back to the supervisor
builder.add_edge("ticketops", "supervisor")
for end_node in ["ask_email", "handoff", "finish"]:
    builder.add_edge(end_node, END)

# For LangGraph Studio (langgraph.json points here). Studio adds its own
# checkpointer and store, so this one is compiled without them.
graph = builder.compile()


# ===========================================================================
# Running it in the terminal
# ===========================================================================
def make_config(thread_id):
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT}


def describe(node_name, update):
    if not update:
        return ""
    parts = []
    if update.get("employee"):
        parts.append(f"employee={update['employee']['name']} ({update['employee']['os']}, {update['employee']['location']})")
    if "attempts" in update:
        parts.append(f"attempts={update['attempts']}")
    if node_name == "supervisor":
        parts.append(f"-> {update.get('route')}")
        if update.get("fix_failed"):
            parts.append("fix_failed=True")
    found = update.get("found") or {}
    if "outage" in found:
        parts.append(f"outage={found['outage']['id'] if found['outage'] else None}")
    if "known_issues" in found:
        parts.append(f"known_issues={[i['id'] for i in found['known_issues']]}")
    if found.get("skipped"):
        parts.append(f"skipped (failed before)={[s['id'] for s in found['skipped']]}")
    if found.get("search_error"):
        parts.append("search_error (model will see it)")
    if node_name == "search_tools":
        message = update["search_messages"][-1]
        parts.append(f"ToolMessage status={message.status}")
    if node_name == "record_failure" and update:
        parts.append("saved the failed fix to the Store")
    if update.get("last_suggested"):
        parts.append(f"last_suggested={update['last_suggested']}")
    if update.get("pending_action"):
        parts.append(f"pending_action={update['pending_action']['tool']}")
    if update.get("tool_result"):
        parts.append(f"result={update['tool_result']}")
    return ", ".join(parts)


def run(graph, graph_input, config):
    """Stream one run, printing every node, inside the specialists too."""
    paused = None
    replies = []
    for namespace, chunk in graph.stream(graph_input, config=config, stream_mode="updates", subgraphs=True):
        for node_name, update in chunk.items():
            if node_name == "__interrupt__":
                if paused is None:
                    paused = update[0].value
                    print("  [approve] paused, waiting for a human")
                continue
            if namespace:
                agent = namespace[0].split(":")[0]
                print(f"    {agent} > [{node_name}] {describe(node_name, update)}")
            elif node_name in ("triage", "ticketops"):
                print(f"  [{node_name}] finished, back to the supervisor")
                continue   # its output repeats the whole conversation
            else:
                print(f"  [{node_name}] {describe(node_name, update)}")
            for message in (update or {}).get("messages", []):
                if isinstance(message, AIMessage) and not message.tool_calls:
                    replies.append(message.content)
    for reply in replies:
        print(f"\nAgent: {reply}")
    return paused


def ask_human(graph, paused, config):
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
    for key in ["employee", "route", "worked", "ops_task", "fix_failed", "attempts", "pending_action", "last_suggested"]:
        value = values.get(key)
        if key == "employee" and value:
            value = f"{value['name']} ({value['os']}, {value['location']})"
        print(f"  {key}: {value}")
    print(f"  messages: {len(values.get('messages', []))}")


def show_memory(store):
    items = store.search((), limit=1000)
    if not items:
        print("  (the Store is empty)")
    for item in items:
        print(f"  {item.namespace} {item.key}: {item.value}")


def show_history(graph, config):
    history = list(graph.get_state_history(config))
    for n, snap in enumerate(history):
        pending = snap.values.get("pending_action")
        extra = f" pending={pending['tool']} priority={pending['args'].get('priority')}" if pending else ""
        print(f"  [{n}] step {snap.metadata.get('step')}: next={snap.next or '(end)'}, "
              f"messages={len(snap.values.get('messages', []))}{extra}")
    return history


def time_travel(graph, config, n, priority):
    """Go back to the checkpoint right after Triage proposed the ticket, change the
    priority, and resume. The supervisor then sends the changed ticket to TicketOps."""
    history = list(graph.get_state_history(config))
    if not 0 <= n < len(history):
        print("  No such checkpoint. Type 'history' to see the numbers.")
        return None
    past = history[n]
    pending = past.values.get("pending_action")
    if not pending or pending["tool"] != "create_ticket" or past.next != ("supervisor",):
        print("  Pick a checkpoint whose next node is supervisor and that has a pending create_ticket.")
        return None
    changed = {**pending, "args": {**pending["args"], "priority": priority}}
    new_config = graph.update_state(past.config, {"pending_action": changed})
    print(f"  Forked from checkpoint [{n}] with priority={priority}. Resuming...")
    return run(graph, None, new_config)


def chat(graph, thread_id, store):
    config = make_config(thread_id)
    print(f"IT Helpdesk (graph_v5). Conversation (thread): {thread_id}")
    print(f"To continue this conversation later, run: python graph_v5.py --thread {thread_id}")
    if BROKEN_PRIMARY:
        print(f"(Primary model is set to {PRIMARY_MODEL}, which does not exist. Every answer comes from the backup, {BACKUP_MODEL}.)")
    print("Commands: 'state', 'history', 'memory', 'travel <n> <low|medium|high>', 'new', 'quit'.")

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


def fallback_demo():
    """One plain model call with the broken primary. response_metadata says who answered."""
    print(f"Primary: {PRIMARY_MODEL}")
    print(f"Backup:  {BACKUP_MODEL}")
    reply = model.invoke("Say hello in five words.")
    print(f"Reply: {reply.content}")
    print(f"Answered by: {reply.response_metadata.get('model_name')}")


def main():
    args = [a for a in sys.argv[1:] if a != "--broken-primary"]
    if "--fallback-demo" in sys.argv:
        fallback_demo()
        return
    if args == ["--draw"]:
        folder = Path(__file__).parent
        (folder / "graph_v5.png").write_bytes(graph.get_graph().draw_mermaid_png())
        (folder / "graph_v5_triage.png").write_bytes(triage_agent.get_graph().draw_mermaid_png())
        (folder / "graph_v5_ticketops.png").write_bytes(ticketops_agent.get_graph().draw_mermaid_png())
        print(f"Saved graph_v5.png, graph_v5_triage.png and graph_v5_ticketops.png in {folder}")
        return
    store = InMemoryStore()
    with SqliteSaver.from_conn_string(CHECKPOINT_DB) as saver:
        app = builder.compile(checkpointer=saver, store=store)
        if len(args) == 2 and args[0] == "--thread":
            chat(app, args[1], store)
        else:
            chat(app, str(uuid.uuid4())[:8], store)


if __name__ == "__main__":
    main()


#Notes to write: When is multi-agent worth it, and when is it just a bigger single graph?
# its worth it if you need agents that each have its own small set of tools and each agent has a specific purpose.
#  bigger single graph is worth it when you can see all the routing/flow 