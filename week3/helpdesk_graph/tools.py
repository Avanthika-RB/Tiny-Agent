"""The helpdesk tools, shared by every graph version.

These are the Week 2 tools from helpdesk_agent/agent.py, moved into their own
file so graph_v1 to graph_v5 can all import them instead of copying them.
"""

import json
import re
from datetime import datetime
from pathlib import Path

from langchain.tools import tool

# The data files live next to this file, so it works from any folder.
DATA_DIR = Path(__file__).parent / "data"
EMPLOYEES_FILE = DATA_DIR / "employees.json"
KNOWN_ISSUES_FILE = DATA_DIR / "known_issues.json"
TICKETS_FILE = DATA_DIR / "tickets.json"

VALID_PRIORITIES = ["low", "medium", "high"]


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
    ticket_id = f"TKT-{1001 + len(tickets)}" #have a timestamp with the date and ticket details, more dynamic 
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
