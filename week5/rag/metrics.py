"""Retrieval metrics, plain Python, no library.

Every function takes:
    ranked  the retrieved results in rank order, each one a label: the gold key it matched
            (for example "01/Policy"), or None if it matched no gold section
    gold    {gold key: grade}. Grade 2 = answers the question, grade 1 = related.

Rules (the same in every function):
  - A gold section counts once. If two retrieved chunks both match "01/Policy", only the
    first one counts; the second is a duplicate and earns nothing.
  - hit and MRR use grade 2 only ("does it ANSWER the question").
  - recall and nDCG use every graded section (grade 1 counts too).

    python rag/metrics.py      checks every function against the hand-worked example in STARTER_README.md
"""

import math


def first_occurrences(ranked):
    """[(rank, key)] for each gold key the first time it appears. Ranks start at 1."""
    seen = set()
    result = []
    for rank, key in enumerate(ranked, start=1):
        if key is not None and key not in seen:
            seen.add(key)
            result.append((rank, key))
    return result


def hit_at_k(ranked, gold, k):
    """1 if a grade-2 section is in the top k, else 0."""
    return int(any(gold.get(key) == 2 for key in ranked[:k] if key is not None))


def recall_at_k(ranked, gold, k):
    """Fraction of the gold sections (any grade) found in the top k."""
    if not gold:
        return 0.0
    found = {key for key in ranked[:k] if key in gold}
    return len(found) / len(gold)


def reciprocal_rank(ranked, gold):
    """1 / rank of the first grade-2 section. 0 if none was retrieved."""
    for rank, key in enumerate(ranked, start=1):
        if gold.get(key) == 2:
            return 1 / rank
    return 0.0


def dcg_at_k(ranked, gold, k):
    """Sum of grade / log2(rank + 1) over the top k, each gold section counted once."""
    return sum(gold[key] / math.log2(rank + 1)
               for rank, key in first_occurrences(ranked[:k]) if key in gold)


def ndcg_at_k(ranked, gold, k):
    """DCG divided by the best possible DCG (all gold sections at the top, highest grade first)."""
    ideal_order = sorted(gold, key=gold.get, reverse=True)
    ideal = dcg_at_k(ideal_order, gold, k)
    return dcg_at_k(ranked, gold, k) / ideal if ideal else 0.0


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def percentile(values, p):
    """p-th percentile (0-100) with linear interpolation between the two nearest values."""
    values = sorted(values)
    if not values:
        return 0.0
    position = (len(values) - 1) * p / 100
    low = math.floor(position)
    high = math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def check():
    """The hand-worked example: gold = {A: 2, B: 1}, retrieved = [C, A, D, B, E]."""
    gold = {"A": 2, "B": 1}
    ranked = ["C", "A", "D", "B", "E"]
    ranked_labels = [key if key in gold else None for key in ranked]
    expected = {
        "hit@3": 1, "recall@3": 0.5, "recall@5": 1.0, "MRR": 0.5,
        "DCG@5": 1.6926, "IDCG@5": 2.6309, "nDCG@5": 0.6433,
    }
    got = {
        "hit@3": hit_at_k(ranked_labels, gold, 3),
        "recall@3": recall_at_k(ranked_labels, gold, 3),
        "recall@5": recall_at_k(ranked_labels, gold, 5),
        "MRR": reciprocal_rank(ranked_labels, gold),
        "DCG@5": dcg_at_k(ranked_labels, gold, 5),
        "IDCG@5": dcg_at_k(["A", "B"], gold, 5),
        "nDCG@5": ndcg_at_k(ranked_labels, gold, 5),
    }
    ok = True
    for name, want in expected.items():
        same = abs(got[name] - want) < 0.0001
        ok &= same
        print(f"  {name:<9} expected {want:<7} got {got[name]:.4f}  {'OK' if same else 'WRONG'}")
    print("All metrics match the hand-worked example." if ok else "Something is wrong: fix the code, not the example.")
    return ok


if __name__ == "__main__":
    check()
