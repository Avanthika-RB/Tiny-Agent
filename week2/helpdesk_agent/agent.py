import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError

MODEL = "nvidia/nemotron-3-super-120b-a12b"
RECURSION_LIMIT = 15

# The data files live next to this script, so it works from any folder.
DATA_DIR = Path(__file__).parent / "data"
EMPLOYEES_FILE = DATA_DIR / "employees.json"
KNOWN_ISSUES_FILE = DATA_DIR / "known_issues.json"
TICKETS_FILE = DATA_DIR / "tickets.json"

VALID_PRIORITIES = ["low", "medium", "high"]

# 2. Try a known fix before filing a ticket. Use search_known_issues and share the fix if one matches.
# 6. If the user says they already tried the known fix, don't repeat it. Offer to create a ticket instead.
SYSTEM_PROMPT = """You are an IT helpdesk triage assistant for a company's Ops team.

Rules:
1. Always identify the employee first. If they have not given their work email, ask for it. Then call lookup_employee before doing anything else.
2. Try a known fix before filing a ticket. Use search_known_issues, and only share a fix if its "applies to" list includes the employee's OS. If no fix applies to their OS, say so and offer a ticket. Never make up your own fix steps.
3. Confirm with the user before creating a ticket. Tell them the summary and priority you plan to use, and only call create_ticket after they say yes.
4. Never invent ticket ids. Only report a ticket id that create_ticket returned.
5. Ticket priority must be low, medium, or high.
6. If the user says they already tried something that matches the known fix (even in different words), do not repeat the fix or ask if they tried it. Go straight to offering a ticket.
Keep replies short and friendly."""


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@tool(parse_docstring=True)
def lookup_employee(email: str) -> str:
    """Look up an employee by their work email address.

    Args:
        email: The employee's work email, for example priya.menon@example.com.
    """
    email = email.strip().lower()
    for employee in load_json(EMPLOYEES_FILE):
        if employee["email"] == email:
            return (
                f"Name: {employee['name']}, Team: {employee['team']}, "
                f"Laptop: {employee['laptop']}, OS: {employee['os']}, "
                f"Location: {employee['location']}, "
                f"VPN enabled: {'yes' if employee['vpn_enabled'] else 'no'}"
            )
    return f"No employee found with email {email}."


@tool(parse_docstring=True)
def search_known_issues(query: str) -> str:
    """Search the list of known IT issues for fixes that match a problem description.

    Args:
        query: A short description of the problem, for example "vpn keeps disconnecting".
    """
    query = query.lower()
    scored = []
    for issue in load_json(KNOWN_ISSUES_FILE):
        # Count how many of the issue's keywords appear as whole words in the query.
        hits = sum(
            1 for keyword in issue["keywords"]
            if re.search(r"\b" + re.escape(keyword) + r"\b", query)
        )
        if hits > 0:
            scored.append((hits, issue))

    if not scored:
        return "No known issues match that description."

    # Highest number of keyword hits first, then keep the top 3.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    lines = []
    for hits, issue in scored[:3]:
        lines.append(
            f"{issue['id']}: {issue['title']} "
            f"(applies to: {', '.join(issue['applies_to'])}). Fix: {issue['fix']}"
        )
    return "\n".join(lines)


@tool(parse_docstring=True)
def create_ticket(employee_email: str, summary: str, priority: str) -> str:
    """Create an IT support ticket. Only call this after the user has confirmed.

    Args:
        employee_email: The work email of the employee the ticket is for.
        summary: A one-sentence description of the problem.
        priority: How urgent the ticket is. Must be low, medium, or high.
    """
    if priority.strip().lower() not in VALID_PRIORITIES:
        return f"Error: priority must be one of low, medium, high. '{priority}' is not allowed."
    priority = priority.strip().lower()

    email = employee_email.strip().lower()
    if not any(e["email"] == email for e in load_json(EMPLOYEES_FILE)):
        return f"Error: no employee found with email {email}. Ticket not created."

    tickets = load_json(TICKETS_FILE)
    # The code makes the id, never the model: TKT-1001, TKT-1002, ...
    ticket_id = f"TKT-{1001 + len(tickets)}"
    tickets.append(
        {
            "id": ticket_id,
            "employee_email": email,
            "summary": summary,
            "priority": priority,
            "status": "open",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    save_json(TICKETS_FILE, tickets)
    return f"Created ticket {ticket_id} with priority {priority}."


# Middleware that runs around every tool call, so each call and its result is printed.
@wrap_tool_call
def print_tool_calls(request, handler):
    name = request.tool_call["name"]
    args = request.tool_call["args"]
    result = handler(request)
    print(f"  [tool] {name}({args})")
    # Indent every line of the result so multi-line results stay readable.
    print("         -> " + str(result.content).replace("\n", "\n            "))
    return result

load_dotenv()
api_key = os.environ.get("NVIDIA_API_KEY")
if not api_key:
    raise SystemExit("NVIDIA_API_KEY is not set. Add it to the .env file.")

model = ChatOpenAI(
    model=MODEL,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key,
    temperature=0,
)

agent = create_agent(
    model,
    tools=[lookup_employee, search_known_issues, create_ticket],
    system_prompt=SYSTEM_PROMPT,
    middleware=[print_tool_calls],
    # The checkpointer saves the conversation after every turn, keyed by thread_id,
    # so the agent remembers earlier messages in the same conversation.
    checkpointer=InMemorySaver(),
)


def new_config():
    # A new thread_id starts a fresh conversation with no memory of the old one.
    return {
        "configurable": {"thread_id": str(uuid.uuid4())},
        "recursion_limit": RECURSION_LIMIT,
    }


config = new_config()
print("IT Helpdesk. Describe your problem.")
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
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
        )
        print(f"\nAgent: {result['messages'][-1].content}")
    except GraphRecursionError:
        print(f"\nAgent: Sorry, I couldn't finish that within {RECURSION_LIMIT} steps. Please try rephrasing.")
