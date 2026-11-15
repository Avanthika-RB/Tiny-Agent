"""Day 3: reranking and query transformation, on top of the Day 2 winner.

    python rag/day3.py                   everything, writes results/day3.md
    python rag/day3.py --no-llm          reranking only (no chat model calls)
    python rag/day3.py --list-rerankers  print the reranker models in NVIDIA's catalog

Day 2 winner: weighted hybrid, alpha 0.7 (0.7 dense + 0.3 BM25), on the markdown_headers chunks.
Every Day 3 technique is that search plus one thing.
"""

import sys

import common
from evaluate import evaluate, fmt
from retrievers.hybrid import make_weighted, weighted_ranking
from retrievers.rerank import list_rerankers, make_rerank
from retrievers import rerank as rerank_module
from retrievers.transforms import GENERATED, make_hyde, make_multi_query, make_rewrite

WINNER_ALPHA = 0.7
POOLS = [10, 20, 40]
SHOW_QIDS = [2, 10, 31]          # questions whose generated queries are printed for you to judge


def winner_ranking(text):
    return weighted_ranking(text, WINNER_ALPHA)


def winner_ranking_with_vector(text, vector):
    return weighted_ranking(text, WINNER_ALPHA, vector=vector)


def row(label, s, llm_calls, rerank_calls):
    return (f"| {label} | {fmt(s['hit@3'])} | {fmt(s['recall@3'])} | {fmt(s['recall@5'])} | {fmt(s['MRR'])} | "
            f"{fmt(s['nDCG@5'])} | {s['p50 ms']:.1f} | {s['p95 ms']:.1f} | {llm_calls} | {rerank_calls} |")


def top_section(r):
    c = r["top"][0]
    return (c["header_path"].split(" > ", 1)[-1] if c["header_path"] else c["source"]) + (" (HIT)" if c["label"] else " (miss)")


def main():
    if "--list-rerankers" in sys.argv:
        list_rerankers()
        return
    use_llm = "--no-llm" not in sys.argv
    questions = common.load_eval_set()
    runs = {}

    plan = [(f"Day 2 winner (hybrid alpha={WINNER_ALPHA})", make_weighted(WINNER_ALPHA), "day3_winner", 0, 0)]
    plan += [(f"+ rerank, pool {p}, top 3", make_rerank(winner_ranking, p, 3), f"day3_rerank_pool{p}_top3", 0, 1)
             for p in POOLS]
    plan += [("+ rerank, pool 20, top 5", make_rerank(winner_ranking, 20, 5), "day3_rerank_pool20_top5", 0, 1)]
    if use_llm:
        plan += [
            ("Multi-query (3) + RRF", make_multi_query(winner_ranking), "day3_multi_query", 1, 0),
            ("HyDE", make_hyde(winner_ranking_with_vector), "day3_hyde", 1, 0),
            ("Rewrite / step-back", make_rewrite(winner_ranking), "day3_rewrite", 1, 0),
        ]
    costs = {}
    for label, retriever, name, llm_calls, rerank_calls in plan:
        print(f"{label} ...")
        runs[label] = evaluate(retriever, name, questions)
        costs[label] = (llm_calls, rerank_calls)

    lines = ["# Day 3: reranking and query transformation", "",
             f"Every technique = the Day 2 winner (weighted hybrid, alpha {WINNER_ALPHA}, on `{common.BASELINE}`) plus one thing. "
             "All 35 questions. Latency includes the reranker and LLM calls. Made by `python rag/day3.py`.", "",
             f"Reranker: `{rerank_module.USED_MODEL}`. Chat model: `{common.CHAT_MODEL}` (falls back to `{common.CHAT_BACKUP}`).", "",
             "## All techniques", "",
             "| Technique | hit@3 | recall@3 | recall@5 | MRR | nDCG@5 | p50 ms | p95 ms | Extra LLM calls / q | Reranker calls / q |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for label, run in runs.items():
        lines.append(row(label, run["summary"]["all"], *costs[label]))
    lines += ["", "A \"top 3\" reranker returns only 3 chunks, so its recall@5 is the same as its recall@3.", ""]

    lines += ["## Candidate pool: recall@3 against latency (find the knee)", "",
              "| Pool | recall@3 | hit@3 | MRR | p50 ms | p95 ms |", "|---|---|---|---|---|---|"]
    base = runs[f"Day 2 winner (hybrid alpha={WINNER_ALPHA})"]["summary"]["all"]
    lines.append(f"| no rerank | {fmt(base['recall@3'])} | {fmt(base['hit@3'])} | {fmt(base['MRR'])} | "
                 f"{base['p50 ms']:.1f} | {base['p95 ms']:.1f} |")
    for p in POOLS:
        s = runs[f"+ rerank, pool {p}, top 3"]["summary"]["all"]
        lines.append(f"| {p} | {fmt(s['recall@3'])} | {fmt(s['hit@3'])} | {fmt(s['MRR'])} | {s['p50 ms']:.1f} | {s['p95 ms']:.1f} |")
    lines += ["", "The knee is the pool size after which recall stops improving but latency keeps growing.", ""]

    if use_llm:
        winner = {r["qid"]: r for r in base_run(runs)["questions"]}
        eval_set = {q["qid"]: q for q in questions}
        lines += ["## What the chat model generated, for 3 questions (judge them yourself)", ""]
        for qid in SHOW_QIDS:
            q = eval_set[qid]["question"]
            lines += [f"### q{qid}: {q}", "",
                      "Multi-query rephrasings:"] + [f"- {r}" for r in GENERATED["multi_query"].get(q, [])] + [
                      "", f"HyDE paragraph: {GENERATED['hyde'].get(q, '')}", "",
                      f"Rewrite: {GENERATED['rewrite'].get(q, '')}", ""]

        for label, key in [("HyDE", "hyde"), ("Multi-query (3) + RRF", "multi_query"), ("Rewrite / step-back", "rewrite")]:
            changed = [r for r in runs[label]["questions"]
                       if abs(r["scores"]["nDCG@5"] - winner[r["qid"]]["scores"]["nDCG@5"]) > 1e-9]
            lines += [f"## {label} vs the Day 2 winner, per question", "",
                      f"Only questions where nDCG@5 changed ({len(changed)} of {len(questions)}).", ""]
            if not changed:
                lines += ["No question changed.", ""]
                continue
            lines += ["| q | Kind | Winner nDCG@5 | New nDCG@5 | New rank-1 chunk | Generated |", "|---|---|---|---|---|---|"]
            for r in changed:
                generated = GENERATED[key].get(r["question"], "")
                if isinstance(generated, list):
                    generated = " / ".join(generated)
                generated = " ".join(str(generated).split())[:160]
                lines.append(f"| {r['qid']} | {r['kind']} | {fmt(winner[r['qid']]['scores']['nDCG@5'])} | "
                             f"{fmt(r['scores']['nDCG@5'])} | {top_section(r)} | {generated} |")
            lines.append("")
        lines.append("Every prompt and answer is in results/llm_log.jsonl.")

    text = "\n".join(lines) + "\n"
    (common.RESULTS / "day3.md").write_text(text, encoding="utf-8")
    print("\n" + text + "\nSaved results/day3.md")


def base_run(runs):
    return runs[f"Day 2 winner (hybrid alpha={WINNER_ALPHA})"]


if __name__ == "__main__":
    main()
