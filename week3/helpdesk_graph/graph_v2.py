"""graph_v2: the helpdesk agent as a graph with real routing.

Day 2 adds three tools, a typed State, and five behaviours:
  1. Intent routing      classify uses structured output, an edge routes on state["intent"]
  2. Outage short-circuit check_outage -> inform_outage -> END, skipping search and tickets
  3. Bounded retry       unknown email -> ask_email; after 2 failed lookups -> handoff
  4. No-fix fallback     the OS check is in Python (after_triage), not in the prompt
  5. Command             check_outage updates state AND chooses the next node in one return

    python graph_v2.py          chat in the terminal (type 'new' or 'quit')
    python graph_v2.py --draw   save a picture of the graph to graph_v2.png
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
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command
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

MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"
RECURSION_LIMIT = 25
MAX_EMAIL_ATTEMPTS = 2

#state
class State(TypedDict):
    messages: Annotated[list, add_messages]   # the conversation, appended to
    employee: dict | None                      # the employee record once identified
    intent: Literal["new_issue", "ticket_status", "password_reset", "other"] | None
    outage: dict | None                        # an active outage relevant to the problem
    attempts: int                              # how many email lookups have failed
    pending_action: dict | None                # a ticket or reset waiting for "yes"
    known_issues: list                         # fixes found by triage (extra field)
    tool_result: str | None                    # result for respond to explain (extra field)

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
# method="function_calling" is needed on NVIDIA endpoints.
classifier = model.with_structured_output(IntentSchema, method="function_calling")
issue_picker = model.with_structured_output(RelevantIssues, method="function_calling")
ticket_writer = model.with_structured_output(TicketDraft, method="function_calling")

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
    """Draft a ticket and ask the employee to confirm before creating it."""
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
        f"- Summary: {draft.summary}\n- Priority: {draft.priority}\n\nShall I create it? (yes/no)"
    )
    return {"pending_action": pending, "messages": [AIMessage(content=text)]}

def propose_reset(state: State):
    """Day 3 replaces this with an approve node that uses interrupt()."""
    email = state["employee"]["email"]
    pending = {"tool": "reset_password", "args": {"email": email}}
    text = f"I can reset the password for {email}. Shall I go ahead? (yes/no)"
    return {"pending_action": pending, "messages": [AIMessage(content=text)]}

def status_lookup(state: State):
    match = re.search(r"TKT-\d+", problem_text(state), re.IGNORECASE)
    if match is None:
        return {"tool_result": "The employee did not give a ticket id, so ask them for it."}
    return {"tool_result": get_ticket_status.invoke({"ticket_id": match.group()})}

ACTIONS = {"create_ticket": create_ticket, "reset_password": reset_password}

def run_action(state: State):
    """The employee said yes: run the pending tool, then clear it."""
    pending = state["pending_action"]
    result = ACTIONS[pending["tool"]].invoke(pending["args"])
    return {"tool_result": result, "pending_action": None}

def cancel(state: State):
    text = "No problem, I won't go ahead with that. Let me know if there's anything else I can help with."
    return {"pending_action": None, "messages": [AIMessage(content=text)]}

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

#edge functions, each one looks at the state and returns the name of the next node.
def route_start(state: State):
    """Where a new user message goes first."""
    if state.get("pending_action"):                 # we asked "shall I...?" last turn
        return "run_action" if said_yes(state) else "cancel"
    if state.get("employee") is None:               # not identified yet
        if state.get("attempts", 0) >= MAX_EMAIL_ATTEMPTS:
            return "handoff"                        # already gave up: no more lookups
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
    ("propose_reset", propose_reset), ("status_lookup", status_lookup),
    ("run_action", run_action), ("cancel", cancel), ("respond", respond),
]:
    builder.add_node(name, node)

builder.add_conditional_edges(START, route_start,
                              ["run_action", "cancel", "handoff", "identify", "classify"])
builder.add_conditional_edges("identify", after_identify, ["classify", "handoff", "ask_email"])
builder.add_conditional_edges("classify", route_intent,
                              ["check_outage", "status_lookup", "propose_reset", "respond"])
# check_outage has no edges here: its Command(goto=...) chooses inform_outage or triage.
builder.add_conditional_edges("triage", after_triage, ["suggest_fix", "propose_ticket"])

builder.add_edge("status_lookup", "respond")
builder.add_edge("run_action", "respond")
for end_node in ["ask_email", "handoff", "inform_outage", "suggest_fix",
                 "propose_ticket", "propose_reset", "cancel", "respond"]:
    builder.add_edge(end_node, END)   # these wait for the employee's next message

graph = builder.compile(checkpointer=InMemorySaver())

#run
def new_config():
    return {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": RECURSION_LIMIT}

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

def chat():
    config = new_config()
    print("IT Helpdesk (graph_v2). Describe your problem.")
    print("Type 'new' to start a new conversation, or 'quit' to exit.")
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break
        if user_input.lower() == "new":
            config = new_config()
            print("(Started a new conversation.)")
            continue
        try:
            replies = []
            for chunk in graph.stream(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
                stream_mode="updates",
            ):
                for node_name, update in chunk.items():
                    print(f"  [{node_name}] {describe(node_name, update)}")
                    for message in (update or {}).get("messages", []):
                        replies.append(message.content)
            for reply in replies:
                print(f"\nAgent: {reply}")
        except GraphRecursionError:
            print(f"\nAgent: Sorry, I couldn't finish that within {RECURSION_LIMIT} steps.")

def draw():
    png = graph.get_graph().draw_mermaid_png()
    path = Path(__file__).parent / "graph_v2.png"
    path.write_bytes(png)
    print(f"Saved {path}")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--draw":
        draw()
    else:
        chat()

# 4: triage looks for known fix. Then after_triage, instead of a rule we check in the function if search results match problem

# 5: in this code, uses command in check_outages. 
#use command when nodes result decides where to go next, can have routing and updating at the same time
#use conditional edge when routing is seperate.

#Notes to write: For each of the five behaviours: who decides, the model, your code, or a human?
#Intent Routing: model
#Outage short circuit: code, looks at outage.json
#Bounded retry: code, then human responds to identify information
#No-fix fallback: model with seeing if ticket is needed and code with after_triage
#Command: code
# model handles things that need judgement about the language, then human verifies

# C:\Users\avant\Desktop\CS\Tiny-Agent\week3\helpdesk_graph> python graph_v2.py