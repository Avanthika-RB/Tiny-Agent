"""Day 4: grid search, the production config, and the ablation.

    python rag/tune.py

1. Grid: hybrid + rerank with k_candidates {10, 20} x alpha {0.4, 0.6} x rerank top_n {3, 5} = 8 runs.
   Chosen on the 30 TUNING questions only (gotcha 6): best nDCG@5, then recall@5, then lower p50.
   My 5 held-out questions are reported next to it but never used to choose.
2. Parent-document: the best grid config is run again with parent-document switched on. It joins
   the production config only if that scores higher on the tuning questions.
3. Production config: saved to results/production.json (the agent reads it on Day 4 part 2).
4. Ablation: from the production config, switch ONE component at a time (BM25, reranker,
   multi-query, parent-document): remove it if production has it, add it if not. The biggest
   drop when removed = the most valuable component.
5. Final check: if removing the reranker scores at least as well on the tuning questions, the
   reranker only adds latency, so the final production config drops it. The grid itself always
   reranks, so without this step a reranker would be chosen even when it does not earn its cost.
Writes results/day4_tuning.md.
"""

import itertools
import json

import common
from evaluate import evaluate, fmt
from retrievers.pipeline import describe, make_pipeline

GRID = {"k_candidates": [10, 20], "alpha": [0.4, 0.6], "top_n": [3, 5]}
PRODUCTION_FILE = common.RESULTS / "production.json"


def choose_key(run):
    s = run["summary"]["tuning"]
    return (round(s["nDCG@5"], 4), round(s["recall@5"], 4), -s["p50 ms"])


def table_row(label, run):
    t, h = run["summary"]["tuning"], run["summary"]["held_out"]
    return (f"| {label} | {fmt(t['hit@3'])} | {fmt(t['recall@5'])} | {fmt(t['MRR'])} | {fmt(t['nDCG@5'])} | "
            f"{fmt(h['nDCG@5'])} | {run['summary']['all']['p50 ms']:.1f} | {run['summary']['all']['p95 ms']:.1f} |")


def run_config(config, name):
    print(f"{describe(**config)} ...")
    return evaluate(make_pipeline(**config), name)


def main():
    lines = ["# Day 4: grid, production config, ablation", "",
             "Made by `python rag/tune.py`. Tuning metrics are on the 30 provided questions (what the choice is based on); "
             "held-out = my 5 added questions, never used to choose. Latency is over all 35.", ""]

    # 1. Grid
    grid = []
    for i, (k, alpha, top_n) in enumerate(itertools.product(GRID["k_candidates"], GRID["alpha"], GRID["top_n"]), start=1):
        config = {"alpha": alpha, "k_candidates": k, "top_n": top_n, "rerank": True, "multi_query": False, "parent": False}
        grid.append((i, config, run_config(config, f"day4_grid_{i}")))
    best_i, best_config, best_run = max(grid, key=lambda g: choose_key(g[2]))

    header = ["| Config | hit@3 | recall@5 | MRR | nDCG@5 | held-out nDCG@5 | p50 ms | p95 ms |",
              "|---|---|---|---|---|---|---|---|"]
    lines += ["## Grid (8 runs)", ""] + header
    lines += [table_row(f"Grid run {i}: {describe(**config)}", run) for i, config, run in grid]
    lines += ["", f"Best on the tuning questions: run {best_i} ({describe(**best_config)}).", ""]

    # 2. Parent-document on top of the best grid config
    with_parent = {**best_config, "parent": True}
    parent_run = run_config(with_parent, "day4_best_plus_parent")
    use_parent = choose_key(parent_run) > choose_key(best_run)
    production = with_parent if use_parent else best_config
    production_run = parent_run if use_parent else best_run

    lines += ["## Parent-document on top of the best grid config", ""] + header
    lines += [table_row(f"Run {best_i}", best_run), table_row(f"Run {best_i} + parent-document", parent_run)]
    lines += ["", f"Parent-document {'IS' if use_parent else 'is NOT'} in the production config "
                  f"({'it scored higher' if use_parent else 'it did not score higher'} on the tuning questions).", ""]

    # 3. Production
    PRODUCTION_FILE.write_text(json.dumps(production, indent=1), encoding="utf-8")
    lines += ["## PRODUCTION", ""] + header + [table_row(f"PRODUCTION: {describe(**production)}", production_run)]
    lines += ["", f"Saved to results/production.json: `{json.dumps(production)}`", ""]

    # 4. Ablation
    toggles = [
        ("BM25", {"alpha": 1.0} if production["alpha"] < 1.0 else {"alpha": 0.6}),
        ("Reranker", {"rerank": not production["rerank"]}),
        ("Multi-query", {"multi_query": not production["multi_query"]}),
        ("Parent-document", {"parent": not production["parent"]}),
    ]
    has = {"BM25": production["alpha"] < 1.0, "Reranker": production["rerank"],
           "Multi-query": production["multi_query"], "Parent-document": production["parent"]}
    p = production_run["summary"]["all"]
    lines += ["## Ablation (all 35 questions)", "",
              "Each row switches ONE component. \"minus\" = production has it and it was removed; "
              "\"plus\" = production does not have it and it was added. Delta = this row minus production.", "",
              "| Production ... | recall@5 | delta | nDCG@5 | delta | MRR | delta | p50 ms |", "|---|---|---|---|---|---|---|---|",
              f"| (production itself) | {fmt(p['recall@5'])} | | {fmt(p['nDCG@5'])} | | {fmt(p['MRR'])} | | {p['p50 ms']:.1f} |"]
    no_rerank = None
    for label, change in toggles:
        config = {**production, **change}
        run = run_config(config, f"day4_ablation_{label.lower().replace('-', '_')}")
        if label == "Reranker" and production["rerank"]:
            no_rerank = (config, run)
        s = run["summary"]["all"]
        sign = "minus" if has[label] else "plus"
        lines.append(f"| {sign} {label} | {fmt(s['recall@5'])} | {s['recall@5'] - p['recall@5']:+.3f} | "
                     f"{fmt(s['nDCG@5'])} | {s['nDCG@5'] - p['nDCG@5']:+.3f} | {fmt(s['MRR'])} | "
                     f"{s['MRR'] - p['MRR']:+.3f} | {s['p50 ms']:.1f} |")

    # 5. Final check: does the reranker earn its latency?
    if no_rerank and choose_key(no_rerank[1]) >= choose_key(production_run):
        production, production_run = no_rerank
        PRODUCTION_FILE.write_text(json.dumps(production, indent=1), encoding="utf-8")
        lines += ["", "## FINAL PRODUCTION (reranker dropped)", "",
                  "Without the reranker the tuning score is the same or better and latency falls from "
                  f"{p['p50 ms']:.0f} ms to {production_run['summary']['all']['p50 ms']:.1f} ms, so the reranker is removed.", ""]
        lines += header + [table_row(f"FINAL PRODUCTION: {describe(**production)}", production_run)]
        lines += ["", f"Saved to results/production.json: `{json.dumps(production)}`"]

    text = "\n".join(lines) + "\n"
    (common.RESULTS / "day4_tuning.md").write_text(text, encoding="utf-8")
    print("\n" + text + "\nSaved results/day4_tuning.md and results/production.json")


if __name__ == "__main__":
    main()
