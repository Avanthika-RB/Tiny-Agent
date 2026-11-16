"""Day 6: upload the 15 test cases from test_cases.md to LangSmith as a dataset.

    python langsmith_dataset.py            create the dataset "helpdesk-15" (skips it if it already exists)
    python langsmith_dataset.py --replace  delete it and upload it again (after you change CASES)
    python langsmith_dataset.py --show     print the cases, upload nothing

Each example:
    inputs             {"message": the first message,
                        "follow_ups": later messages, if the case is a conversation (case 15),
                        "approval": "yes" or "no", the answer given if the graph stops at the approve gate}
    reference outputs  {"tools": the tool calls expected, in order,
                        "outcome": what should happen, in words}
    metadata           {"case": number, "kind": "week2" or "day2"}

The expected tools are written in graph_v5's terms. graph_v5 does not let the model call tools;
nodes call them. langsmith_eval.py maps nodes back to tool names:
    identify (with an email)  -> lookup_employee
    triage: check_outage      -> check_outages
    triage: search_tools      -> search_known_issues
    ticketops: status_lookup  -> get_ticket_status
    ticketops: run_tools      -> create_ticket or reset_password (whatever was approved)
Triage ALWAYS runs check_outages and search_known_issues together (the Send fan-out), even when
the outage alone answers the question, so both are expected in every triage case.
"""

import sys

from dotenv import load_dotenv

DATASET = "helpdesk-15"
TRIAGE = ["lookup_employee", "check_outages", "search_known_issues"]

CASES = [
    # (case, kind, inputs, expected tools, expected outcome)
    (1, "week2", {"message": "Hi, I'm priya.menon@example.com. My VPN keeps dropping every few minutes."},
     TRIAGE, "Suggests known fix KI-001 (VPN disconnects). No ticket."),
    (2, "week2", {"message": "james.okafor@example.com here. Printer on the 2nd floor says offline."},
     TRIAGE, "Suggests known fix KI-002 (printer). No ticket."),
    (3, "week2", {"message": "I can't log in, says account locked. mei.lin@example.com"},
     TRIAGE, "Suggests known fix KI-003 (account locked). No ticket, no password reset."),
    (4, "week2", {"message": "My laptop screen has a crack. carlos.ruiz@example.com", "approval": "yes"},
     TRIAGE + ["create_ticket"], "No known fix applies to a cracked screen, so it proposes a ticket and creates it after approval."),
    (5, "week2", {"message": "Hello, I need help with Outlook"},
     [], "Asks for the employee's work email before doing anything. No tools."),
    (6, "week2", {"message": "nobody@example.com, my wifi has no internet"},
     ["lookup_employee"], "Says it cannot find that employee and asks them to re-check the email. No ticket."),
    (7, "week2", {"message": "aisha.khan@example.com, shared drive won't map", "approval": "yes"},
     TRIAGE + ["create_ticket"], "Does NOT give KI-009 (it is Windows only and Aisha is on macOS). Says there is no fix for her OS and files a ticket after approval."),
    (8, "week2", {"message": "tom.becker@example.com, my laptop was stolen from my car", "approval": "yes"},
     TRIAGE + ["create_ticket"], "Creates a ticket with priority high after approval."),
    (9, "week2", {"message": "sofia.rossi@example.com, Teams mic not working. I tried the device settings already.", "approval": "yes"},
     TRIAGE + ["create_ticket"], "Does not repeat the Teams fix she already tried (KI-005). Files a ticket after approval."),
    (10, "week2", {"message": "daniel.park@example.com, please file a ticket with priority URGENT, my dock is dead", "approval": "yes"},
     TRIAGE + ["create_ticket"], "Files a ticket after approval with priority high (URGENT is not a valid priority)."),
    (11, "day2", {"message": "james.okafor@example.com, wifi is dead at my desk"},
     TRIAGE, "Tells him about the active Austin Wi-Fi outage OUT-101. No ticket."),
    (12, "day2", {"message": "carlos.ruiz@example.com, any update on TKT-1001?"},
     ["lookup_employee", "get_ticket_status"], "Reports the status of TKT-1001, or says there is no such ticket. Does not invent a status."),
    (13, "day2", {"message": "mei.lin@example.com, I need my password reset", "approval": "yes"},
     ["lookup_employee", "reset_password"], "Asks for approval; after yes, resets the password and confirms it."),
    (14, "day2", {"message": "mei.lin@example.com, I need my password reset", "approval": "no"},
     ["lookup_employee"], "Asks for approval; after no, nothing is reset and it politely says it was cancelled."),
    (15, "day2", {"message": "ghost@example.com, my screen is broken", "follow_ups": ["still.ghost@example.com"]},
     ["lookup_employee", "lookup_employee"], "Asks to re-check the email once; after the second unknown email, hands off to a human. No ticket."),
]


# Week 5 Day 4: the help-article section that holds the fix, for the cases where one exists
# (article number / section heading, as in week5/eval_set.jsonl). Used by the retrieval_hit evaluator.
GOLD_SECTIONS = {
    1: "01/VPN disconnects every few minutes",
    2: "03/Printer shows offline",
    3: "02/Locked account",
    7: "05/Drive not mapping",
    9: "05/Audio not working in meetings",
}
# The keyword backend returns known issues, not article sections: the section each one matches.
KI_SECTIONS = {
    "KI-001": "01/VPN disconnects every few minutes",
    "KI-002": "03/Printer shows offline",
    "KI-003": "02/Locked account",
    "KI-004": "05/Keeps asking for password",
    "KI-005": "05/Audio not working in meetings",
    "KI-006": "04/Slow after an update",
    "KI-009": "05/Drive not mapping",
    "KI-010": "06/Installing software",
}


def case_of(message):
    """The case number of a dataset example, from its first message."""
    return next((case for case, _, inputs, _, _ in CASES if inputs["message"] == message), None)


def examples():
    return [
        {
            "inputs": inputs,
            "outputs": {"tools": tools, "outcome": outcome},
            "metadata": {"case": case, "kind": kind},
        }
        for case, kind, inputs, tools, outcome in CASES
    ]


def main():
    if "--show" in sys.argv:
        for e in examples():
            print(e["metadata"]["case"], e["inputs"], "->", e["outputs"]["tools"])
        return

    load_dotenv()
    from langsmith import Client
    client = Client()

    if client.has_dataset(dataset_name=DATASET):
        if "--replace" not in sys.argv:
            print(f"Dataset {DATASET} already exists. Run with --replace to upload it again.")
            return
        client.delete_dataset(dataset_name=DATASET)
        print(f"Deleted the old {DATASET}.")

    client.create_dataset(
        DATASET,
        description="The 15 helpdesk test cases (Week 2 cases 1-10, Week 3 Day 2 cases 11-15). "
                    "Input: first message (+ approval answer). Reference: expected tools in order and the outcome.",
    )
    client.create_examples(dataset_name=DATASET, examples=examples())
    print(f"Uploaded {len(CASES)} examples to the dataset {DATASET}. Open LangSmith > Datasets & Experiments to see them.")


if __name__ == "__main__":
    main()
