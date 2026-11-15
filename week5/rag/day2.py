"""Day 2: sparse, hybrid, prefilter and MMR, all on the baseline collection's chunks.

    python rag/day2.py              run every Day 2 technique, write results/day2.md
    python rag/day2.py --no-llm     the same without the LLM article guess (no chat model calls)

Every technique goes through evaluate() with the same 35 questions, matching and metrics as Day 1.
"""

import sys

import common
from evaluate import evaluate, fmt
from retrievers.bm25 import make_bm25
from retrievers.dense import make_dense
from retrievers.hybrid import make_rrf, make_weighted
from retrievers.mmr import make_mmr
from retrievers.prefilter import GUESSES, make_llm_prefilter, make_rule_prefilter, named_area

ALPHAS = [0.3, 0.5, 0.7]


def first_answer_rank(row):
    """Rank of the first grade-2 chunk, or None if no answer in the top 5."""
    return next((i for i, lab in enumerate(row["labels"], start=1) if lab and row["gold"].get(lab) == 2), None)


def rank_text(rank):
    return str(rank) if rank else "not in top 5"


def by_qid(run):
    return {r["qid"]: r for r in run["questions"]}


def main_row(label, s, wins):
    return (f"| {label} | {fmt(s['hit@3'])} | {fmt(s['recall@5'])} | {fmt(s['MRR'])} | {fmt(s['nDCG@5'])} | "
            f"{s['p50 ms']:.1f} | {s['p95 ms']:.1f} | {wins} |")


def kind_winners(runs):
    """For each kind, the technique with the best nDCG@5 (then MRR). Shared best = no winner."""
    kinds = list(next(iter(runs.values()))["summary"]["by_kind"])
    winners = {}
    for kind in kinds:
        key = lambda n: (round(runs[n]["summary"]["by_kind"][kind]["nDCG@5"], 4),
                         round(runs[n]["summary"]["by_kind"][kind]["MRR"], 4))
        best = max(key(n) for n in runs)
        top = [n for n in runs if key(n) == best]
        winners[kind] = top
    return kinds, winners


def main():
    use_llm = "--no-llm" not in sys.argv
    questions = common.load_eval_set()
    b = common.BASELINE

    print(f"All techniques search the chunks of {b}.")
    runs = {}
    plan = [
        ("Baseline dense", make_dense(b), "day2_dense"),
        ("BM25", make_bm25(b), "day2_bm25"),
        ("Hybrid RRF k=60", make_rrf(b), "day2_rrf60"),
    ] + [(f"Hybrid alpha={a}", make_weighted(a, b), f"day2_alpha_{a}") for a in ALPHAS] + [
        ("MMR lambda=0.5", make_mmr(0.5, b), "day2_mmr_0.5"),
    ]
    if use_llm:
        plan.append(("Dense + LLM-guessed article filter (all 35)", make_llm_prefilter(b), "day2_prefilter_llm"))
    for label, retriever, name in plan:
        print(f"{label} ...")
        runs[label] = evaluate(retriever, name, questions)

    # The rule prefilter only applies to questions that name one area. Compare it with plain
    # dense on exactly those questions, or the comparison is not fair.
    subset = [q for q in questions if named_area(q["question"])]
    print(f"Prefilter by named area ({len(subset)} questions) ...")
    pre_dense = evaluate(make_dense(b), "day2_dense_named_area", subset)
    pre_rule = evaluate(make_rule_prefilter(b), "day2_prefilter_rule", subset)

    kinds, winners = kind_winners(runs)
    wins = {label: [k for k in kinds if winners[k] == [label]] for label in runs}

    lines = ["# Day 2: sparse, hybrid, prefilter, MMR", "",
             f"Every technique searches the same chunks: the `{b}` collection. All 35 questions unless noted. "
             "Made by `python rag/day2.py`.", "",
             "## All techniques", "",
             "| Technique | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms | Wins on (kind) |",
             "|---|---|---|---|---|---|---|---|"]
    for label, run in runs.items():
        lines.append(main_row(label, run["summary"]["all"], ", ".join(wins[label]) or "-"))
    lines.append(main_row(f"Dense, named-area questions only ({len(subset)} q)", pre_dense["summary"]["all"], ""))
    lines.append(main_row(f"Dense + prefilter by named area ({len(subset)} q)", pre_rule["summary"]["all"], ""))
    lines += ["", "\"Wins on\": the kinds where this technique alone has the best nDCG@5 (ties broken by MRR). "
                  "A kind where several techniques share the best score has no winner.", ""]

    lines += ["## nDCG@5 by question kind", "",
              "| Technique | " + " | ".join(f"{k} (n={runs['BM25']['summary']['by_kind'][k]['n']})" for k in kinds) + " |",
              "|---|" + "---|" * len(kinds)]
    for label, run in runs.items():
        cells = []
        for k in kinds:
            value = fmt(run["summary"]["by_kind"][k]["nDCG@5"])
            cells.append(f"**{value}**" if label in winners[k] else value)
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines += ["", "Bold = best for that kind (shared bests are all bold).", ""]

    lines += ["## Alpha sweep (alpha = weight on dense; 0 = pure BM25, 1 = pure dense)", "",
              "| alpha | recall@5 | hit@3 | MRR | nDCG@5 |", "|---|---|---|---|---|"]
    sweep = [(0.0, runs["BM25"])] + [(a, runs[f"Hybrid alpha={a}"]) for a in ALPHAS] + [(1.0, runs["Baseline dense"])]
    for alpha, run in sweep:
        s = run["summary"]["all"]
        lines.append(f"| {alpha} | {fmt(s['recall@5'])} | {fmt(s['hit@3'])} | {fmt(s['MRR'])} | {fmt(s['nDCG@5'])} |")

    dense, bm25 = by_qid(runs["Baseline dense"]), by_qid(runs["BM25"])
    lines += ["", "## Dense vs BM25, per question", "",
              "Rank of the first chunk that answers the question (grade 2). Only questions where the two differ.", "",
              "| q | Kind | Question | Dense | BM25 |", "|---|---|---|---|---|"]
    for q in questions:
        rd, rb = first_answer_rank(dense[q["qid"]]), first_answer_rank(bm25[q["qid"]])
        if rd != rb:
            lines.append(f"| {q['qid']} | {q['kind']} | {q['question']} | {rank_text(rd)} | {rank_text(rb)} |")

    mmr_rows = by_qid(runs["MMR lambda=0.5"])
    lines += ["", "## MMR vs dense, per question", "",
              "nDCG@5 and how many of the top 5 came from a different source file (more = more diverse). "
              "Only questions where nDCG@5 changed.", "",
              "| q | Kind | Dense nDCG@5 | MMR nDCG@5 | Dense: files in top 5 | MMR: files in top 5 |", "|---|---|---|---|---|---|"]
    for q in questions:
        d, m = dense[q["qid"]], mmr_rows[q["qid"]]
        if abs(d["scores"]["nDCG@5"] - m["scores"]["nDCG@5"]) > 1e-9:
            files = lambda r: len({c["source"] for c in r["top"]})
            lines.append(f"| {q['qid']} | {q['kind']} | {fmt(d['scores']['nDCG@5'])} | {fmt(m['scores']['nDCG@5'])} | "
                         f"{files(d)} | {files(m)} |")

    lines += ["", f"## Prefilter by named area ({len(subset)} questions)", "",
              "A question qualifies if it names exactly one area (see AREA_WORDS in retrievers/prefilter.py). "
              "Both rows are on exactly these questions.", "",
              "| Technique | hit@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms | |", "|---|---|---|---|---|---|---|---|",
              main_row("Dense", pre_dense["summary"]["all"], ""),
              main_row("Dense + prefilter", pre_rule["summary"]["all"], "")]

    if use_llm:
        lines += ["", "## LLM article guess (all 35)", "",
                  "| q | Question | Guessed | Gold (grade 2) | Right? |", "|---|---|---|---|---|"]
        right = 0
        for q in questions:
            gold = sorted({g["article"] for g in q["gold"] if g["grade"] == 2})
            guess = GUESSES.get(q["question"])
            ok = guess in gold
            right += ok
            lines.append(f"| {q['qid']} | {q['question']} | {guess} | {', '.join(gold)} | {'yes' if ok else '**no**'} |")
        lines += ["", f"The LLM guessed the right article for {right} of {len(questions)} questions. "
                      "Every prompt and answer is in results/llm_log.jsonl."]

    text = "\n".join(lines) + "\n"
    (common.RESULTS / "day2.md").write_text(text, encoding="utf-8")
    print("\n" + text + "\nSaved results/day2.md")


if __name__ == "__main__":
    main()
