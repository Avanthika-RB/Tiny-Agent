"""graph_v3: graph_v2 plus persistence and human-in-the-loop.

Day 3 adds:
  - SqliteSaver: conversations are saved to checkpoints.db, so they survive the
    program being killed. Restart with the same --thread and carry on.
  - One approve node: create_ticket and reset_password both go through it. It
    calls interrupt(), which pauses the graph until a human answers yes or no.
  - State inspection: type 'state' or 'history' in the chat.
  - Time travel: type 'travel <n> <priority>' to go back to checkpoint n
    (from 'history'), change the ticket priority, and resume from there.

    python graph_v3.py                     chat in a new conversation
    python graph_v3.py --thread NAME       continue (or start) the conversation called NAME
    python graph_v3.py --draw              save a picture of the graph to graph_v3.png

    In the chat: 'state', 'history', 'travel <n> <low|medium|high>', 'new', 'quit'
"""

import os
import re
import sys
import uuid
from pathlib import Path
from typing import Annotated, Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt
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

#state
class State(TypedDict):
    messages: Annotated[list, add_messages]   # the conversation, appended to
    employee: dict | None                      # the employee record once identified
    intent: Literal["new_issue", "ticket_status", "password_reset", "other"] | None
    outage: dict | None                        # an active outage relevant to the problem
    attempts: int                              # how many email lookups have failed
    pending_action: dict | None                # the ticket or reset waiting for approval
    known_issues: list                         # fixes found by triage
    tool_result: str | None                    # result for respond to explain

#model
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
            "password_reset: asking for their password to be reset. "
            "other: anything else, such as thanks or small talk."
        )
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


#nodes
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
    """Ask the model what the employee wants. Structured output, so the answer is one of four values."""
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
    # A new request starts fresh: clear results left over from earlier in the conversation.
    return {"intent": result.intent, "outage": None, "known_issues": [], "tool_result": None}


def check_outage(state: State) -> Command[Literal["inform_outage", "triage"]]:
    """Behaviour 5, Command: update the state AND choose the next node in one return."""
    location = state["employee"]["location"]
    relevant = [
        o for o in find_active_outages(location)
        if outage_matches_problem(o, problem_text(state))
    ]
    outage = relevant[0] if relevant else None
    # Routing decision (yours to explain): a relevant outage short-circuits the graph.
    goto = "inform_outage" if outage else "triage"
    return Command(update={"outage": outage}, goto=goto)


def inform_outage(state: State):
    o = state["outage"]
    text = (
        f"There's an active outage that explains this: {o['service']} in {o['location']} ({o['id']}). "
        f"{o['message']} It's expected to be fixed by {o['eta']}. No ticket is needed."
    )
    return {"messages": [AIMessage(content=text)]}


def triage(state: State):
    """Search known issues, then let the model keep only fixes that really fit."""
    candidates = find_known_issues(problem_text(state))
    if not candidates:
        return {"known_issues": []}
    listing = "\n".join(f"{i['id']}: {i['title']}. Fix: {i['fix']}" for i in candidates)
    choice = issue_picker.invoke(
        [
            SystemMessage(content="Pick which candidate fixes match the employee's problem. Leave out any fix the employee says they already tried, even in different words."),
            HumanMessage(content=f"Employee's messages: {problem_text(state)}\n\nCandidate fixes:\n{listing}"),
        ]
    )
    kept = [i for i in candidates if i["id"] in choice.issue_ids]
    return {"known_issues": kept}


def suggest_fix(state: State):
    """Show the first fix that applies to the employee's OS. The text comes from the data, never the model."""
    os_name = state["employee"]["os"]
    issue = next(i for i in state["known_issues"] if os_name in i["applies_to"])
    text = (
        f"There's a known fix for this ({issue['id']}: {issue['title']}), and it applies to your {os_name}:\n"
        f"{issue['fix']}\n\nIf that doesn't help, tell me and I'll file a ticket."
    )
    return {"messages": [AIMessage(content=text)]}


def propose_ticket(state: State):
    """Draft a ticket. The approve node asks for confirmation before anything is created."""
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
    text = (
        "I couldn't find a known fix that applies here, so I'd like to file a ticket:\n"
        f"- Summary: {draft.summary}\n- Priority: {draft.priority}"
    )
    return {"pending_action": pending, "messages": [AIMessage(content=text)]}


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
        update={"pending_action": None, "tool_result": "The employee said no, so nothing was done. Confirm politely that it was cancelled."},
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
            SystemMessage(content="You are an IT helpdesk assistant. Write a short, friendly reply based only on the result given. Never invent ticket ids, links, or details that are not in the result."),
            HumanMessage(content=f"Employee's latest message: {last_user_text(state)}\nResult: {result}"),
        ]
    )
    return {"messages": [AIMessage(content=reply.content)], "tool_result": None}


#edge functions
def route_start(state: State):
    """Where a new user message goes first. (No pending-action branch any more:
    approval now happens inside the same run, at the approve node.)"""
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
    """Behaviour 1, intent routing: route on a value in state, not on tool calls."""
    return {
        "new_issue": "check_outage",
        "ticket_status": "status_lookup",
        "password_reset": "propose_reset",
        "other": "respond",
    }[state["intent"]]


def after_triage(state: State):
    """Behaviour 4, the OS check in code. This replaces prompt rule 2."""
    os_name = state["employee"]["os"]
    for issue in state.get("known_issues", []):
        if os_name in issue["applies_to"]:
            return "suggest_fix"
    return "propose_ticket"   # no fix found, or none applies to this OS


#graph
builder = StateGraph(State)
for name, node in [
    ("identify", identify), ("ask_email", ask_email), ("handoff", handoff),
    ("classify", classify), ("check_outage", check_outage), ("inform_outage", inform_outage),
    ("triage", triage), ("suggest_fix", suggest_fix), ("propose_ticket", propose_ticket),
    ("propose_reset", propose_reset), ("approve", approve), ("run_tools", run_tools),
    ("status_lookup", status_lookup), ("respond", respond),
]:
    builder.add_node(name, node)

builder.add_conditional_edges(START, route_start, ["handoff", "identify", "classify"])
builder.add_conditional_edges("identify", after_identify, ["classify", "handoff", "ask_email"])
builder.add_conditional_edges("classify", route_intent,
                              ["check_outage", "status_lookup", "propose_reset", "respond"])
# check_outage and approve have no edges here: their Command(goto=...) chooses.
builder.add_conditional_edges("triage", after_triage, ["suggest_fix", "propose_ticket"])

builder.add_edge("propose_ticket", "approve")   # both sensitive actions share ONE gate
builder.add_edge("propose_reset", "approve")
builder.add_edge("run_tools", "respond")
builder.add_edge("status_lookup", "respond")
for end_node in ["ask_email", "handoff", "inform_outage", "suggest_fix", "respond"]:
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
        parts.append(f"intent={update['intent']}")
    if "outage" in update and node_name == "check_outage":
        parts.append(f"outage={update['outage']['id'] if update['outage'] else None}")
    if "known_issues" in update and node_name == "triage":
        parts.append(f"known_issues={[i['id'] for i in update['known_issues']]}")
    if update.get("pending_action"):
        parts.append(f"pending_action={update['pending_action']['tool']}")
    if update.get("tool_result"):
        parts.append(f"result={update['tool_result']}")
    return ", ".join(parts)


def run(graph, graph_input, config):
    """Stream one run, printing each node. Returns the interrupt payload if the graph paused."""
    paused = None
    replies = []
    for chunk in graph.stream(graph_input, config=config, stream_mode="updates"):
        for node_name, update in chunk.items():
            if node_name == "__interrupt__":
                paused = update[0].value
                print("  [approve] paused, waiting for a human")
                continue
            print(f"  [{node_name}] {describe(node_name, update)}")
            for message in (update or {}).get("messages", []):
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
    for key in ["employee", "intent", "outage", "attempts", "pending_action", "known_issues", "tool_result"]:
        value = values.get(key)
        if key == "employee" and value:
            value = f"{value['name']} ({value['os']}, {value['location']})"
        if key == "known_issues" and value:
            value = [i["id"] for i in value]
        print(f"  {key}: {value}")
    print(f"  messages: {len(values.get('messages', []))}")


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


def chat(graph, thread_id):
    config = make_config(thread_id)
    print(f"IT Helpdesk (graph_v3). Conversation (thread): {thread_id}")
    print(f"To continue this conversation later, run: python graph_v3.py --thread {thread_id}")
    print("Commands: 'state', 'history', 'travel <n> <low|medium|high>', 'new', 'quit'.")

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


def main():
    args = sys.argv[1:]
    # SqliteSaver is a context manager: the database stays open inside the with block,
    # so the graph is compiled and run inside it.
    with SqliteSaver.from_conn_string(CHECKPOINT_DB) as saver:
        graph = builder.compile(checkpointer=saver)
        if args == ["--draw"]:
            path = Path(__file__).parent / "graph_v3.png"
            path.write_bytes(graph.get_graph().draw_mermaid_png())
            print(f"Saved {path}")
        elif len(args) == 2 and args[0] == "--thread":
            chat(graph, args[1])
        else:
            chat(graph, str(uuid.uuid4())[:8])


if __name__ == "__main__":
    main()


#Notes to write: What is the difference between a thread and a checkpoint? Draw it.
# thread is what you pass in the command line "--thread case5" as an example thats 1 whole
#conversation, and a checkpoint is a saved version in its history where you can revert back to
#different checkpoints. 