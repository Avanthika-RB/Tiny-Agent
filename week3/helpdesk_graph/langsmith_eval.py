"""Day 6: run graph_v5 on the dataset in LangSmith, score it, compare experiments.

Needs in the .env file: LANGSMITH_TRACING=true, LANGSMITH_API_KEY, LANGSMITH_PROJECT=helpdesk.
Upload the dataset first: python langsmith_dataset.py

    python langsmith_eval.py try 7                       run case 7 here only (nothing uploaded), print what came out
    python langsmith_eval.py run                         experiment on graph_v5 as built        (prefix v5)
    python langsmith_eval.py run --variant prompt_os_rule  experiment on the reverted variant    (prefix v5-prompt-os-rule)
    python langsmith_eval.py run --hub                   same as run, but the supervisor prompt comes from the Prompt Hub
    python langsmith_eval.py compare EXP_A EXP_B         pairwise evaluator on two experiments (names from LangSmith)
    python langsmith_eval.py live                        5 normal conversations into the helpdesk project
                                                         (for the online evaluator and the annotation queue)
    python langsmith_eval.py queue                       make the annotation queue and send it the last 5 runs

Week 5 Day 4: --backend rag (the default) or --backend keyword picks what search_known_issues uses.
    python langsmith_eval.py all --backend rag           all 15 cases here (nothing uploaded), table in week5/results/
    python langsmith_eval.py run --backend keyword       LangSmith experiment, old keyword search   (prefix v5-keyword)
    python langsmith_eval.py run --backend rag           LangSmith experiment, Week 5 production RAG (prefix v5-rag)
Then compare the two in LangSmith (Datasets > helpdesk-15 > tick both > Compare).

The target runs each example in a NEW thread with an in-memory checkpointer and store, so
examples never see each other. tickets.json and password_resets.json are backed up before the
run and put back after it, because cases 4, 7-10 and 13 really create tickets and resets.
"""

import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

HERE = Path(__file__).resolve().parent
DATA_FILES = [HERE / "data" / "tickets.json", HERE / "data" / "password_resets.json"]
QUEUE_NAME = "helpdesk-review"
LIVE_CASES = [1, 4, 7, 11, 12]      # the 5 conversations for `live`

# Set by main() BEFORE graph_v5 is imported, because graph_v5 reads them when it loads.
graph_v5 = None


def load_graph(variant="", hub=False, backend="rag"):
    global graph_v5
    os.environ["SEARCH_BACKEND"] = backend
    os.environ["HELPDESK_VARIANT"] = variant
    os.environ["PROMPT_FROM_HUB"] = "1" if hub else "0"
    import graph_v5 as module
    graph_v5 = module


# ---------------------------------------------------------------------------
# The target: one example in, what the graph did out
# ---------------------------------------------------------------------------
def node_to_tool(namespace, node, update, message, pending):
    """Which tool (if any) this node update stands for. See langsmith_dataset.py for the mapping."""
    agent = namespace[0].split(":")[0] if namespace else ""
    if not agent and node == "identify" and re.search(graph_v5.EMAIL_PATTERN, message):
        return "lookup_employee"
    if agent == "triage" and node == "check_outage":
        return "check_outages"
    if agent == "triage" and node == "search_tools":
        return "search_known_issues"
    if agent == "ticketops" and node == "status_lookup" and re.search(r"TKT-\d+", message, re.I):
        return "get_ticket_status"
    if agent == "ticketops" and node == "run_tools" and pending:
        return pending["tool"]
    return None


KI_LINE = re.compile(r"^(KI-\d+): (.*?) \(applies to: .*?\)\. Fix: (.*)$", re.M)


def parse_search(text):
    """The search_known_issues result as [{id, title, source, section, text}], for either backend."""
    from rag_search import parse
    items = parse(text)
    items += [{"id": m.group(1), "title": m.group(2), "source": "data/known_issues.json", "section": "",
               "text": m.group(3)} for m in KI_LINE.finditer(text)]
    return items


def target(inputs: dict) -> dict:
    """What evaluate() calls for each example. LangSmith traces it as the experiment's run."""
    out = run_example(inputs)
    from langsmith.run_helpers import get_current_run_tree
    span = get_current_run_tree()
    if span is not None:     # the intents the supervisor chose, on the experiment row
        span.add_metadata({"intent": out["routes"], "case_tools": out["tools"]})
    return out


def run_example(inputs, tags=None):
    """Run one example through graph_v5 and report what it did."""
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.store.memory import InMemoryStore
    from langgraph.types import Command
    from langchain_core.messages import AIMessage

    app = graph_v5.builder.compile(checkpointer=InMemorySaver(), store=InMemoryStore())
    config = graph_v5.make_config(f"eval-{uuid.uuid4().hex[:8]}")
    config["tags"] = ["graph_v5", f"variant:{graph_v5.VARIANT or 'v5'}"] + (tags or [])
    email = re.search(graph_v5.EMAIL_PATTERN, inputs["message"])
    config["metadata"] = {"employee": email.group() if email else "unknown", "variant": graph_v5.VARIANT or "v5"}

    out = {"tools": [], "replies": [], "routes": [], "approval_asked": None,
           "ticket_priority": None, "outage": None, "fix_suggested": None, "retrieved": [],
           "backend": os.environ.get("SEARCH_BACKEND", "rag")}
    pending = None

    def stream(graph_input, message):
        nonlocal pending
        for namespace, chunk in app.stream(graph_input, config=config, stream_mode="updates", subgraphs=True):
            for node, update in chunk.items():
                if node == "__interrupt__":
                    out["approval_asked"] = update[0].value["question"]
                    continue
                if not namespace and node in ("triage", "ticketops"):
                    continue          # the subgraph's whole output again; its nodes were already seen
                update = update or {}
                tool = node_to_tool(namespace, node, update, message, pending)
                if tool:
                    out["tools"].append(tool)
                if tool == "search_known_issues" and update.get("search_messages"):
                    out["retrieved"] = parse_search(update["search_messages"][-1].content)
                if update.get("pending_action"):
                    pending = update["pending_action"]
                    if pending["tool"] == "create_ticket":
                        out["ticket_priority"] = pending["args"]["priority"]
                if node == "supervisor" and update.get("route"):
                    out["routes"].append(update["route"])
                found = update.get("found") or {}
                if found.get("outage"):
                    out["outage"] = found["outage"]["id"]
                if update.get("last_suggested"):
                    out["fix_suggested"] = update["last_suggested"]
                for m in update.get("messages", []):
                    if isinstance(m, AIMessage) and not m.tool_calls:
                        out["replies"].append(m.content)

    for message in [inputs["message"]] + inputs.get("follow_ups", []):
        stream({"messages": [{"role": "user", "content": message}]}, message)
        for _ in range(3):          # answer the approve gate if the graph stopped there
            if not app.get_state(config).interrupts:
                break
            stream(Command(resume=inputs.get("approval") or "no"), message)

    out["reply"] = "\n\n".join(out["replies"])
    return out


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
class SavedData:
    """Back up tickets.json and password_resets.json, put them back afterwards."""
    def __enter__(self):
        for f in DATA_FILES:
            shutil.copy(f, f.with_suffix(".json.bak"))

    def __exit__(self, *exc):
        for f in DATA_FILES:
            shutil.move(f.with_suffix(".json.bak"), f)


def try_case(number):
    from evaluators import tool_order
    from langsmith_dataset import CASES
    case = next(c for c in CASES if c[0] == number)
    _, _, inputs, tools, outcome = case
    with SavedData():
        out = run_example(inputs)
    print(json.dumps(out, indent=2))
    print("\ntool_order:", tool_order(out, {"tools": tools}))
    print("expected outcome:", outcome)


def print_summary(results, keys=("tool_order", "llm_judge")):
    rows, totals, counts = [], {}, {}
    for r in results:
        case = r["example"].metadata.get("case")
        scores = {e.key: e.score for e in r["evaluation_results"]["results"]}
        comments = {e.key: e.comment for e in r["evaluation_results"]["results"]}
        rows.append((case, scores, comments))
        for k, v in scores.items():
            if v is not None:
                totals[k] = totals.get(k, 0) + v
                counts[k] = counts.get(k, 0) + 1
    rows.sort(key=lambda row: row[0] or 0)
    print("\n| Case | " + " | ".join(keys) + " | judge's reason |")
    print("|---|" + "---|" * (len(keys) + 1))
    for case, scores, comments in rows:
        cells = ["-" if scores.get(k) is None else str(scores.get(k)) for k in keys]
        print(f"| {case} | " + " | ".join(cells) + f" | {comments.get(keys[-1])} |")
    print("| **Total** | " + " | ".join(f"**{totals.get(k, 0)}/{counts.get(k, 0)}**" for k in keys) + " | |")


def run_experiment(variant, hub, backend="rag"):
    from langsmith import evaluate
    from evaluators import groundedness, llm_judge, retrieval_hit, tool_order
    from langsmith_dataset import DATASET

    prefix = "v5" + f"-{backend}" + (f"-{variant.replace('_', '-')}" if variant else "") + ("-hub" if hub else "")
    print(f"Running the experiment {prefix}* on {DATASET} (one example at a time) ...")
    with SavedData():
        results = evaluate(
            target,
            data=DATASET,
            evaluators=[tool_order, retrieval_hit, groundedness, llm_judge],
            experiment_prefix=prefix,
            description=f"graph_v5, search backend={backend}, variant={variant or 'none'}, supervisor prompt from {'hub' if hub else 'code'}",
            metadata={"backend": backend, "variant": variant or "v5", "prompt": "hub" if hub else "local",
                      "model": graph_v5.MODEL},
            max_concurrency=1,      # one at a time: the examples share tickets.json
        )
    print_summary(results, keys=("tool_order", "retrieval_hit", "groundedness", "llm_judge"))
    print(f"\nExperiment name: {results.experiment_name}  (use it with `compare`)")


def run_all(backend):
    """Week 5 Day 4: all 15 helpdesk cases, here only (nothing uploaded to an experiment).
    Scores tool order and retrieval hit; writes week5/results/day4_agent_<backend>.md."""
    from evaluators import retrieval_hit, tool_order
    from langsmith_dataset import CASES
    lines = [f"# Day 4: the 15 helpdesk test cases, search backend = {backend}", "",
             f"Made by `python langsmith_eval.py all --backend {backend}` in week3/helpdesk_graph.", "",
             "| Case | Expected tools | Got | tool_order | retrieval_hit | Top search result | Reply |", "|---|---|---|---|---|---|---|"]
    totals = {"tool_order": [0, 0], "retrieval_hit": [0, 0]}
    with SavedData():
        for number, _, inputs, tools, outcome in CASES:
            print(f"case {number} ...")
            out = run_example(inputs, tags=[f"backend:{backend}", f"case:{number}"])
            order = tool_order(out, {"tools": tools})["score"]
            hit = retrieval_hit(inputs, out)["score"]
            for key, value in (("tool_order", order), ("retrieval_hit", hit)):
                if value is not None:
                    totals[key][0] += value
                    totals[key][1] += 1
            top = out["retrieved"][0] if out["retrieved"] else None
            top_text = f"{top['id']} {top['title']}" + (f" ({top['source']})" if top["section"] else "") if top else "-"
            reply = " ".join(out["reply"].split())[:160].replace("|", "/")
            lines.append(f"| {number} | {', '.join(tools) or '-'} | {', '.join(out['tools']) or '-'} | {order} | "
                         f"{'-' if hit is None else hit} | {top_text} | {reply} |")
    lines += ["", f"tool_order {totals['tool_order'][0]}/{totals['tool_order'][1]}, "
                  f"retrieval_hit {totals['retrieval_hit'][0]}/{totals['retrieval_hit'][1]} "
                  "(retrieval_hit only for cases 1, 2, 3, 7, 9, which have a help-article section with the fix)."]
    text = "\n".join(lines) + "\n"
    folder = HERE.parents[1] / "week5" / "results"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"day4_agent_{backend}.md").write_text(text, encoding="utf-8")
    print("\n" + text + f"\nSaved week5/results/day4_agent_{backend}.md")


def compare(exp_a, exp_b):
    from langsmith.evaluation import evaluate_comparative
    from evaluators import pairwise_better
    results = evaluate_comparative((exp_a, exp_b), evaluators=[pairwise_better], experiment_prefix="pairwise",
                                   max_concurrency=1)
    print("Done. In LangSmith open the dataset, tab Pairwise Experiments, to see which experiment won each example.")
    return results


def live():
    """5 ordinary conversations (not an experiment), so they land in the tracing project."""
    from langsmith_dataset import CASES
    with SavedData():
        for number, _, inputs, _, _ in CASES:
            if number in LIVE_CASES:
                out = run_example(inputs, tags=["live", f"case:{number}"])
                print(f"case {number}: tools={out['tools']}\n   reply: {out['reply'][:120]!r}")
    print(f"\nSent {len(LIVE_CASES)} conversations to the project {os.environ.get('LANGSMITH_PROJECT')}.")


def queue():
    from langsmith import Client
    client = Client()
    project = os.environ.get("LANGSMITH_PROJECT", "default")
    existing = list(client.list_annotation_queues(name=QUEUE_NAME))
    q = existing[0] if existing else client.create_annotation_queue(
        name=QUEUE_NAME,
        description="Review helpdesk replies: was it correct, polite, and free of invented fixes?",
    )
    runs = list(client.list_runs(project_name=project, is_root=True, limit=5))
    client.add_runs_to_annotation_queue(q.id, run_ids=[r.id for r in runs])
    print(f"Sent {len(runs)} runs from {project} to the annotation queue {QUEUE_NAME}.")
    print("Open LangSmith > Annotation queues > helpdesk-review to score them.")


def main():
    args = sys.argv[1:]
    variant = ""
    if "--variant" in args:
        variant = args[args.index("--variant") + 1]
    hub = "--hub" in args
    backend = args[args.index("--backend") + 1] if "--backend" in args else "rag"

    if args[:1] == ["compare"] and len(args) == 3:
        compare(args[1], args[2])
        return
    if args[:1] == ["queue"]:
        queue()
        return

    load_graph(variant, hub, backend)
    if args[:1] == ["try"] and len(args) >= 2 and args[1].isdigit():
        try_case(int(args[1]))
    elif args[:1] == ["all"]:
        run_all(backend)
    elif args[:1] == ["run"]:
        run_experiment(variant, hub, backend)
    elif args[:1] == ["live"]:
        live()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
