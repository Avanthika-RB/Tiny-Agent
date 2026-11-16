"""Day 6: the three evaluators used by langsmith_eval.py.

    tool_order      custom Python. 1 if the graph used the expected tools in the expected order, else 0.
    llm_judge       LLM-as-judge with a rubric: correct, polite, no invented fixes. 0 or 1 plus one
                    sentence of reasoning. Temperature 0, the same NVIDIA model as the graph.
    pairwise_better compares two experiments on the same example and says which reply was better.

The first two are "row" evaluators: LangSmith calls them once per example with
    inputs             the example's inputs (first message, approval answer)
    outputs            what the target returned (tools, reply, ...), see langsmith_eval.target
    reference_outputs  the example's reference (expected tools, expected outcome)
and they return {"key": name, "score": number, "comment": text}.
pairwise_better is a "comparative" evaluator: it gets the runs from BOTH experiments for one example.
"""

import json
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv()

JUDGE_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"     # the same model as graph_v5
KNOWN_ISSUES = json.loads((Path(__file__).parent / "data" / "known_issues.json").read_text(encoding="utf-8"))

# check_outages and search_known_issues run at the same time (the Send fan-out),
# so either can finish first. Their order is not a mistake, so it is ignored.
PARALLEL = {"check_outages", "search_known_issues"}


def normalize(tools):
    """Sort each stretch of tools that run in parallel, so the two possible orders compare equal."""
    result, group = [], []
    for name in tools:
        if name in PARALLEL:
            group.append(name)
            continue
        result += sorted(group)
        group = []
        result.append(name)
    return result + sorted(group)


# ---------------------------------------------------------------------------
# (a) custom Python: tool order
# ---------------------------------------------------------------------------
def tool_order(outputs: dict, reference_outputs: dict) -> dict:
    got = normalize(outputs.get("tools", []))
    expected = normalize(reference_outputs.get("tools", []))
    return {
        "key": "tool_order",
        "score": int(got == expected),
        "comment": f"expected {expected or 'no tools'}, got {got or 'no tools'}",
    }


# ---------------------------------------------------------------------------
# (b) LLM-as-judge with a rubric
# ---------------------------------------------------------------------------
class Verdict(BaseModel):
    """The judge's verdict on one helpdesk conversation."""
    reasoning: str = Field(description="ONE sentence explaining the score.")
    score: int = Field(description="1 if the reply passes ALL three rubric checks, 0 if it fails any of them.")


class Preference(BaseModel):
    """Which of two helpdesk replies is better."""
    reasoning: str = Field(description="ONE sentence explaining the choice.")
    better: str = Field(description='"A", "B", or "tie" if they are equally good.')


RUBRIC = """You grade an IT helpdesk assistant's replies to an employee. Score 1 only if ALL three hold:
1. Correct: the replies reach the expected outcome given below (same fix, outage, ticket, priority, or handoff).
2. Polite: friendly and professional, talks to the employee directly.
3. No invented fixes: every fix step it gives comes from the known-issues list below, and it does not
   make up ticket ids, outages, or statuses. Saying it has no fix and offering a ticket is fine.
Otherwise score 0. Give exactly one sentence of reasoning."""


def known_issues_text():
    return "\n".join(f"{i['id']} ({', '.join(i['applies_to'])}): {i['title']}. Fix: {i['fix']}" for i in KNOWN_ISSUES)


_judge = None


def judge_model():
    """Built on first use, so importing this file needs no API key."""
    global _judge
    if _judge is None:
        _judge = ChatOpenAI(
            model=JUDGE_MODEL,
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.environ.get("NVIDIA_API_KEY"),
            temperature=0,
            max_retries=5,
        )
    return _judge


def describe_run(inputs, outputs):
    messages = [inputs["message"]] + inputs.get("follow_ups", [])
    lines = [f"Employee: {m}" for m in messages]
    if inputs.get("approval") and outputs.get("approval_asked"):
        lines.append(f"(The assistant asked for approval; the employee answered \"{inputs['approval']}\".)")
    lines += [f"Assistant: {r}" for r in outputs.get("replies", [])]
    return "\n".join(lines)


def llm_judge(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    verdict = judge_model().with_structured_output(Verdict, method="function_calling").invoke(
        [
            ("system", RUBRIC),
            ("human",
             f"Known issues:\n{known_issues_text()}\n\n"
             f"Expected outcome: {reference_outputs['outcome']}\n\n"
             f"Conversation:\n{describe_run(inputs, outputs)}"),
        ]
    )
    return {"key": "llm_judge", "score": 1 if verdict.score == 1 else 0, "comment": verdict.reasoning}


# ---------------------------------------------------------------------------
# Week 5 Day 4: retrieval hit and groundedness
# ---------------------------------------------------------------------------
def section_of(item):
    """The "article/section" keys a retrieved item stands for."""
    if item["id"].startswith("KI-"):
        from langsmith_dataset import KI_SECTIONS
        return {KI_SECTIONS[item["id"]]} if item["id"] in KI_SECTIONS else set()
    article = item["source"].split("/")[-1][:2]
    return {f"{article}/{part.strip()}" for part in item["section"].split(">") if part.strip()}


def retrieval_hit(inputs: dict, outputs: dict) -> dict:
    """1 if the search returned the help-article section that holds the fix, else 0.
    Only for the 5 cases that have such a section (1, 2, 3, 7, 9); the others get no score."""
    from langsmith_dataset import GOLD_SECTIONS, case_of
    gold = GOLD_SECTIONS.get(case_of(inputs["message"]))
    if gold is None:
        return {"key": "retrieval_hit", "score": None, "comment": "no help-article section for this case"}
    found = [item for item in outputs.get("retrieved", []) if gold in section_of(item)]
    return {"key": "retrieval_hit", "score": int(bool(found)),
            "comment": f"gold {gold}; " + (f"found as {found[0]['id']}" if found else
                                           f"retrieved: {[item['id'] for item in outputs.get('retrieved', [])] or 'nothing'}")}


GROUNDED_RUBRIC = """You check an IT helpdesk assistant for invented information. Below are the search results it
was given and what it said to the employee. Score 1 if every fix step and fact it gave is supported by the search
results (or it gave no fix at all: only asked for an email, reported an outage, proposed or filed a ticket, or
looked up a ticket). Score 0 if it gave any fix step or fact that is not in the search results.
Give exactly one sentence of reasoning."""


def groundedness(inputs: dict, outputs: dict) -> dict:
    retrieved = "\n".join(f"{i['id']}: {i['title']}. {i['text']}" for i in outputs.get("retrieved", [])) or "(no search was run)"
    verdict = judge_model().with_structured_output(Verdict, method="function_calling").invoke(
        [("system", GROUNDED_RUBRIC),
         ("human", f"Search results:\n{retrieved}\n\nWhat the assistant said:\n{chr(10).join(outputs.get('replies', []))}")]
    )
    return {"key": "groundedness", "score": 1 if verdict.score == 1 else 0, "comment": verdict.reasoning}


# ---------------------------------------------------------------------------
# (c) pairwise: which of two experiments did better on this example
# ---------------------------------------------------------------------------
def pairwise_better(runs: list, example) -> dict:
    """runs = [run from experiment A, run from experiment B] for the same example.
    The two replies are shown in random order, so the judge cannot simply prefer whichever comes first."""
    shown = runs[:]
    random.shuffle(shown)
    choice = judge_model().with_structured_output(Preference, method="function_calling").invoke(
        [
            ("system", RUBRIC.replace("Score 1 only if ALL three hold", "Use these three checks")
                             .replace("Otherwise score 0. Give exactly one sentence of reasoning.",
                                      "Say which conversation, A or B, does better on these checks, or tie. One sentence of reasoning.")),
            ("human",
             f"Known issues:\n{known_issues_text()}\n\n"
             f"Expected outcome: {example.outputs['outcome']}\n\n"
             f"Conversation A:\n{describe_run(example.inputs, shown[0].outputs or {})}\n\n"
             f"Conversation B:\n{describe_run(example.inputs, shown[1].outputs or {})}"),
        ]
    )
    better = choice.better.strip().upper()
    if better == "A":
        scores = {shown[0].id: 1, shown[1].id: 0}
    elif better == "B":
        scores = {shown[0].id: 0, shown[1].id: 1}
    else:
        scores = {shown[0].id: 0.5, shown[1].id: 0.5}
    return {"key": "pairwise_better", "scores": scores, "comment": choice.reasoning}
