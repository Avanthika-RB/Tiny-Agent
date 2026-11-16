"""Day 4: parent-document and contextual compression. (The grid and ablation are in tune.py.)

    python rag/day4.py parent      parent-document vs normal chunks, on procedure + context questions and on all 35
    python rag/day4.py compress    answer quality with full vs compressed chunks, LLM judge, 10 questions

Order for the day: parent, then `python rag/tune.py` (grid, production config, ablation), then compress
(it uses the production config if tune.py has saved one).
"""

import json
import re
import sys

import common
from evaluate import evaluate, fmt
from retrievers.compress import compress
from retrievers.dense import make_dense
from retrievers.hybrid import make_weighted
from retrievers.parent import make_parent
from retrievers.pipeline import describe, make_pipeline

COMPRESS_QIDS = [1, 4, 9, 12, 15, 17, 22, 25, 27, 29]     # 10 tuning questions, every kind


def row(label, s):
    return (f"| {label} | {fmt(s['hit@3'])} | {fmt(s['recall@5'])} | {fmt(s['MRR'])} | {fmt(s['nDCG@5'])} | "
            f"{s['p50 ms']:.1f} | {s['p95 ms']:.1f} |")


def parent():
    questions = common.load_eval_set()
    subset = [q for q in questions if q["kind"] in ("procedure", "context")]
    plan = [
        ("Dense on markdown_headers (baseline)", make_dense()),
        ("Day 2 winner: hybrid alpha 0.7 on markdown_headers", make_weighted(0.7)),
        ("Dense on fixed_200 (small chunks, returned as they are)", make_dense("fixed_200")),
        ("Parent-document: dense on fixed_200, return the parent section", make_parent()),
        ("Parent-document with hybrid alpha 0.7", make_pipeline(alpha=0.7, k_candidates=5, top_n=5, rerank=False, parent=True)),
    ]
    header = ["| Technique | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms |", "|---|---|---|---|---|---|---|"]
    sub_rows, all_rows, runs = [], [], {}
    for i, (label, retriever) in enumerate(plan):
        print(f"{label} ...")
        runs[label] = evaluate(retriever, f"day4_parent_{i}", questions)
        sub = evaluate(retriever, f"day4_parent_{i}_proc_ctx", subset, save=False)
        sub_rows.append(row(label, sub["summary"]["all"]))
        all_rows.append(row(label, runs[label]["summary"]["all"]))

    lines = ["# Day 4: parent-document (small-to-big)", "",
             "Search the 200-character chunks, return the whole markdown_headers section each one came from. "
             "Made by `python rag/day4.py parent`.", "",
             f"## Procedure and context questions only ({len(subset)} questions)", ""] + header + sub_rows
    lines += ["", "## All 35 questions", ""] + header + all_rows

    small = {r["qid"]: r for r in runs[plan[2][0]]["questions"]}
    par = {r["qid"]: r for r in runs[plan[3][0]]["questions"]}
    lines += ["", "## Small chunks vs their parents, per question (only where nDCG@5 changed)", "",
              "| q | Kind | Small chunks nDCG@5 | Parents nDCG@5 | Parents rank-1 section |", "|---|---|---|---|---|"]
    for q in questions:
        a, b = small[q["qid"]], par[q["qid"]]
        if abs(a["scores"]["nDCG@5"] - b["scores"]["nDCG@5"]) > 1e-9:
            top = b["top"][0]
            where = top["header_path"].split(" > ", 1)[-1] if top["header_path"] else top["source"]
            lines.append(f"| {q['qid']} | {q['kind']} | {fmt(a['scores']['nDCG@5'])} | {fmt(b['scores']['nDCG@5'])} | {where} |")
    text = "\n".join(lines) + "\n"
    (common.RESULTS / "day4_parent.md").write_text(text, encoding="utf-8")
    print("\n" + text + "\nSaved results/day4_parent.md")


def answer(question, context):
    return common.chat(
        "You are an IT helpdesk assistant. Answer the employee's question using ONLY the help article text "
        "below. If it does not contain the answer, say so.\n\n"
        f"Help article text:\n{context}\n\nQuestion: {question}", purpose="compression_answer")


def judge(question, expected, given):
    reply = common.chat(
        "Grade an IT helpdesk answer against the expected answer.\n"
        "Score 2 if it gives all the key facts of the expected answer correctly, 1 if it gives some of them "
        "or is vague, 0 if it is wrong, invents facts, or says it cannot answer.\n"
        "Reply exactly as: SCORE: <0, 1 or 2> - <one sentence reason>\n\n"
        f"Question: {question}\nExpected answer: {expected}\nAnswer to grade: {given}", purpose="compression_judge")
    match = re.search(r"SCORE:\s*([012])", reply)
    reason = reply.split("-", 1)[-1].strip() if "-" in reply else reply
    return (int(match.group(1)) if match else 0), reason


def compress_eval():
    path = common.RESULTS / "production.json"
    if path.exists():
        config = json.loads(path.read_text(encoding="utf-8"))
        retriever, label = make_pipeline(**config), f"production config ({describe(**config)})"
    else:
        retriever, label = make_weighted(0.7), "Day 2 winner (hybrid alpha 0.7); run tune.py first to use the production config"
    eval_set = {q["qid"]: q for q in common.load_eval_set()}

    rows, totals = [], {"full": 0, "compressed": 0, "full_chars": 0, "compressed_chars": 0}
    for qid in COMPRESS_QIDS:
        q = eval_set[qid]
        print(f"q{qid} ...")
        chunks = retriever(q["question"], 5)
        full = "\n\n".join(c["text"] for c in chunks)
        short = "\n\n".join(s for s in compress(q["question"], chunks) if s)
        scores = {}
        for kind, context in [("full", full), ("compressed", short)]:
            given = answer(q["question"], context or "(nothing)")
            scores[kind] = judge(q["question"], q["expected_answer"], given)
            totals[kind] += scores[kind][0]
        totals["full_chars"] += len(full)
        totals["compressed_chars"] += len(short)
        rows.append(f"| {qid} | {q['kind']} | {len(full)} | {len(short)} | {scores['full'][0]} | {scores['compressed'][0]} | "
                    f"{scores['compressed'][1]} |")

    lines = ["# Day 4: contextual compression", "",
             f"Retrieval: {label}, top 5. The chat model copies out only the sentences that help. Then it answers "
             "from the full chunks and from the compressed ones, and an LLM judge scores each answer 0-2 against "
             "the expected answer. Made by `python rag/day4.py compress`. All prompts in results/llm_log.jsonl.", "",
             "| q | Kind | Full chars | Compressed chars | Score, full | Score, compressed | Judge on the compressed answer |",
             "|---|---|---|---|---|---|---|"] + rows
    n = len(COMPRESS_QIDS)
    lines += ["", f"Total answer score: full {totals['full']}/{2 * n}, compressed {totals['compressed']}/{2 * n}. "
                  f"Context size: {totals['full_chars']} -> {totals['compressed_chars']} characters "
                  f"({100 * (1 - totals['compressed_chars'] / max(totals['full_chars'], 1)):.0f}% smaller). "
                  "Extra LLM calls per question for compression: 1."]
    text = "\n".join(lines) + "\n"
    (common.RESULTS / "day4_compression.md").write_text(text, encoding="utf-8")
    print("\n" + text + "\nSaved results/day4_compression.md")


def main():
    args = sys.argv[1:]
    if args[:1] == ["parent"]:
        parent()
    elif args[:1] == ["compress"]:
        compress_eval()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
