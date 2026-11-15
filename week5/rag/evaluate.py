"""The evaluation harness. Every technique this week goes through evaluate(), so every technique
gets the same questions, the same matching, the same metrics and the same latency measurement.

Run from the week5 folder:

    python rag/evaluate.py check            metrics vs the hand-worked example, and every gold section exists
    python rag/evaluate.py baseline         Day 1: dense search on all six Week 4 collections
    python rag/evaluate.py worst [COLL]     the 5 worst questions for the baseline (default: best collection)
    python rag/evaluate.py show QID [COLL]  one question: its top 5 chunks and what each matched

Metrics, at k=3 and k=5 (see metrics.py for the exact rules):
    hit@k     1 if a grade-2 section is in the top k
    recall@k  share of the gold sections (grade 1 and 2) found in the top k
    MRR       1 / rank of the first grade-2 section, over the top 5 (0 if none)
    nDCG@k    graded: rewards finding grade 2 above grade 1, and both near the top
    p50, p95  latency of one retrieve call in milliseconds (median and 95th percentile)

Latency: question embeddings are cached (gotcha 5), so they are made once before timing starts
and p50/p95 measure the search itself. What the embedding call costs is printed separately.
Results are reported three ways: all 35, the 30 provided (tuning set) and my 5 (held out).
"""

import json
import sys
import time

import common
import matching
import metrics

K_MAX = 5
METRIC_NAMES = ["hit@3", "hit@5", "recall@3", "recall@5", "MRR", "nDCG@3", "nDCG@5"]


def score(labels, gold):
    return {
        "hit@3": metrics.hit_at_k(labels, gold, 3),
        "hit@5": metrics.hit_at_k(labels, gold, 5),
        "recall@3": metrics.recall_at_k(labels, gold, 3),
        "recall@5": metrics.recall_at_k(labels, gold, 5),
        "MRR": metrics.reciprocal_rank(labels[:K_MAX], gold),
        "nDCG@3": metrics.ndcg_at_k(labels, gold, 3),
        "nDCG@5": metrics.ndcg_at_k(labels, gold, 5),
    }


def summarize(rows):
    if not rows:
        return {}
    summary = {name: metrics.mean(r["scores"][name] for r in rows) for name in METRIC_NAMES}
    times = [r["ms"] for r in rows]
    summary.update({"p50 ms": metrics.percentile(times, 50), "p95 ms": metrics.percentile(times, 95), "n": len(rows)})
    return summary


def evaluate(retriever, name, questions=None, save=True):
    """Run every question through retriever(question, k) and score it.
    Returns {"name", "summary": {"all", "tuning", "held_out", "by_kind"}, "questions": [...]}."""
    questions = questions or common.load_eval_set()
    for q in questions:                       # embed every question before the clock starts
        common.embed_query(q["question"])
    retriever(questions[0]["question"], K_MAX)   # warm-up: opens the collection, not timed

    rows = []
    for q in questions:
        start = time.perf_counter()
        chunks = retriever(q["question"], K_MAX)
        ms = (time.perf_counter() - start) * 1000
        gold = common.gold_of(q)
        labels = matching.label(chunks, gold)
        rows.append({
            "qid": q["qid"], "kind": q["kind"], "question": q["question"],
            "held_out": q["qid"] >= common.HELD_OUT_FROM, "ms": ms,
            "gold": gold, "labels": labels, "scores": score(labels, gold),
            "top": [{"source": c["metadata"]["source"], "header_path": c["metadata"].get("header_path", ""),
                     "text": c["text"], "label": lab, "distance": c.get("distance")}
                    for c, lab in zip(chunks, labels)],
        })

    kinds = sorted({r["kind"] for r in rows})
    result = {
        "name": name,
        "summary": {
            "all": summarize(rows),
            "tuning": summarize([r for r in rows if not r["held_out"]]),
            "held_out": summarize([r for r in rows if r["held_out"]]),
            "by_kind": {kind: summarize([r for r in rows if r["kind"] == kind]) for kind in kinds},
        },
        "questions": rows,
    }
    if save:
        folder = common.RESULTS / "runs"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{name}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


def load_run(name):
    path = common.RESULTS / "runs" / f"{name}.json"
    if not path.exists():
        raise SystemExit(f"No saved run {name}. Run `python rag/evaluate.py baseline` first.")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------
def fmt(value):
    return f"{value:.3f}"


def template_row(label, s):
    """The columns of results-template.md: hit@3, recall@5, MRR, nDCG@5, p50, p95."""
    return (f"| {label} | {fmt(s['hit@3'])} | {fmt(s['recall@5'])} | {fmt(s['MRR'])} | "
            f"{fmt(s['nDCG@5'])} | {s['p50 ms']:.1f} | {s['p95 ms']:.1f} |")


def full_row(label, s):
    return "| " + label + " | " + " | ".join(fmt(s[m]) for m in METRIC_NAMES) + f" | {s['p50 ms']:.1f} | {s['p95 ms']:.1f} |"


TEMPLATE_HEADER = ["| Collection | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms |", "|---|---|---|---|---|---|---|"]
FULL_HEADER = ["| Collection | " + " | ".join(METRIC_NAMES) + " | p50 ms | p95 ms |", "|---|" + "---|" * (len(METRIC_NAMES) + 2)]


def baseline():
    runs = {}
    for name in common.COLLECTIONS:
        from retrievers.dense import make_dense
        print(f"dense on {name} ...")
        runs[name] = evaluate(make_dense(name), f"dense_{name}")

    best = max(runs, key=lambda n: (runs[n]["summary"]["tuning"]["recall@5"], runs[n]["summary"]["tuning"]["nDCG@5"]))
    kinds = list(runs[best]["summary"]["by_kind"])
    embed = common.embedding_ms()

    lines = ["# Day 1: baseline, dense only, per Week 4 collection", "",
             f"Embedding model {common.EMBED_MODEL}. Top {K_MAX} chunks per question. Made by `python rag/evaluate.py baseline`.", "",
             "## All 35 questions (template columns)", ""] + TEMPLATE_HEADER
    lines += [template_row(n, runs[n]["summary"]["all"]) for n in runs]
    for group, title in [("tuning", "The 30 provided questions (tuning set)"), ("held_out", "My 5 added questions (held out)")]:
        lines += ["", f"## {title}", ""] + TEMPLATE_HEADER
        lines += [template_row(n, runs[n]["summary"][group]) for n in runs]
    lines += ["", "## All metrics at k=3 and k=5 (all 35)", ""] + FULL_HEADER
    lines += [full_row(n, runs[n]["summary"]["all"]) for n in runs]
    lines += ["", "## recall@5 by question kind (all 35)", "",
              "| Collection | " + " | ".join(f"{k} (n={runs[best]['summary']['by_kind'][k]['n']})" for k in kinds) + " |",
              "|---|" + "---|" * len(kinds)]
    lines += ["| " + n + " | " + " | ".join(fmt(runs[n]["summary"]["by_kind"][k]["recall@5"]) for k in kinds) + " |" for n in runs]
    lines += ["", f"Highest recall@5 on the 30 tuning questions (ties broken by nDCG@5): **{best}**.",
              "", f"Latency is the search only. Embedding one question took p50 {metrics.percentile(embed, 50):.0f} ms, "
                  f"p95 {metrics.percentile(embed, 95):.0f} ms when it was first cached." if embed else ""]
    text = "\n".join(lines) + "\n"
    common.RESULTS.mkdir(exist_ok=True)
    (common.RESULTS / "day1_baseline.md").write_text(text, encoding="utf-8")
    print("\n" + text)
    print(f"Saved results/day1_baseline.md and results/runs/dense_*.json")


def describe_chunk(c, gold):
    where = c["source"] + (f" | {c['header_path']}" if c["header_path"] else "")
    mark = f"HIT {c['label']} (grade {gold[c['label']]})" if c["label"] else "miss"
    return f"{mark}  [{where}]  {' '.join(c['text'].split())[:110]}"


def margin(row):
    """How close the question came to failing: distance of the best chunk that is NOT an answer,
    minus distance of the best chunk that IS one (grade 2). Small = fragile, negative = a wrong
    chunk ranked above the answer. None if the retriever gives no distances."""
    answer = [c["distance"] for c in row["top"] if c["label"] and row["gold"].get(c["label"]) == 2]
    other = [c["distance"] for c in row["top"] if not (c["label"] and row["gold"].get(c["label"]) == 2)]
    if not answer or not other or answer[0] is None or other[0] is None:
        return None
    return other[0] - answer[0]


def worst(collection=None):
    if collection is None:
        runs = {n: load_run(f"dense_{n}") for n in common.COLLECTIONS
                if (common.RESULTS / "runs" / f"dense_{n}.json").exists()}
        collection = max(runs, key=lambda n: (runs[n]["summary"]["tuning"]["recall@5"], runs[n]["summary"]["tuning"]["nDCG@5"]))
    run = load_run(f"dense_{collection}")
    def badness(r):
        m = margin(r)
        return (r["scores"]["nDCG@5"], r["scores"]["MRR"], r["scores"]["recall@5"], m if m is not None else 99)
    rows = sorted(run["questions"], key=badness)[:5]
    imperfect = sum(1 for r in run["questions"] if r["scores"]["nDCG@5"] < 0.9999)
    eval_set = {q["qid"]: q for q in common.load_eval_set()}

    lines = [f"# Day 1: the 5 worst questions for the baseline (dense_{collection})", "",
             "Sorted by nDCG@5, then MRR, then margin (how close the answer came to being beaten by a wrong chunk).",
             f"Only {imperfect} of {len(run['questions'])} questions score below a perfect nDCG@5; the rest of this list "
             "is the most fragile perfect ones." if imperfect < 5 else "",
             "Made by `python rag/evaluate.py worst`.", ""]
    for r in rows:
        q = eval_set[r["qid"]]
        s = r["scores"]
        lines += [f"## q{r['qid']} ({r['kind']}): {r['question']}", "",
                  f"- Gold: " + ", ".join(f"{k} (grade {g})" for k, g in r["gold"].items()),
                  f"- Expected answer: {q['expected_answer']}",
                  f"- hit@3 {s['hit@3']}, recall@5 {fmt(s['recall@5'])}, MRR {fmt(s['MRR'])}, nDCG@5 {fmt(s['nDCG@5'])}"
                  + (f", margin {margin(r):.3f}" if margin(r) is not None else ""),
                  "- Top 5:"]
        lines += [f"  {i}. {describe_chunk(c, r['gold'])}" for i, c in enumerate(r["top"], start=1)]
        lines += ["", "**Why I think it failed:** ", ""]
    text = "\n".join(lines)
    (common.RESULTS / "day1_worst5.md").write_text(text + "\n", encoding="utf-8")
    print(text)
    print("Saved results/day1_worst5.md. Write one line under each 'Why I think it failed'.")


def show(qid, collection="markdown_headers"):
    from retrievers.dense import make_dense
    q = next(q for q in common.load_eval_set() if q["qid"] == qid)
    gold = common.gold_of(q)
    chunks = make_dense(collection)(q["question"], K_MAX)
    labels = matching.label(chunks, gold)
    print(f"q{qid} ({q['kind']}): {q['question']}\nGold: {gold}\nExpected: {q['expected_answer']}\n")
    for i, (c, lab) in enumerate(zip(chunks, labels), start=1):
        all_hits = [k for k in gold if matching.matches(c, k)]
        top = {"source": c["metadata"]["source"], "header_path": c["metadata"].get("header_path", ""),
               "text": c["text"], "label": lab}
        print(f"{i}. distance {c['distance']:.3f}  {describe_chunk(top, gold)}\n   matches: {all_hits or 'nothing'}")
    print("\nScores:", {k: round(v, 3) for k, v in score(labels, gold).items()})


def main():
    args = sys.argv[1:]
    if args[:1] == ["check"]:
        ok = metrics.check()
        print("All gold sections found in week4/kb." if matching.check_gold() else "Fix the sections above.")
    elif args[:1] == ["baseline"]:
        baseline()
    elif args[:1] == ["worst"]:
        worst(args[1] if len(args) > 1 else None)
    elif args[:1] == ["show"] and len(args) >= 2 and args[1].isdigit():
        show(int(args[1]), *args[2:3])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
