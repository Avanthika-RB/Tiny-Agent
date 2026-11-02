"""Day 6: query every collection with the same 10 questions and measure hit@3.

Run from the week4 folder, AFTER filling in the Prediction column in results.md:

    python rag/compare.py            all 10 questions x 6 collections: hit@3 grid, totals, evidence.md
    python rag/compare.py show 8     the top 3 chunks of every collection for question 8
    python rag/compare.py ask "my printer shows offline" [collection]
                                     any question, top 3 from one collection (default markdown_headers)

hit@3 = Y if any of the top 3 chunks contains the expected answer, N otherwise.
"Contains the answer" is checked strictly: ONE chunk must contain every piece listed in
`must_contain` for that question (case and whitespace ignored). For a procedure question that
means every step, so a chunk with half a list is a miss. Check the evidence yourself: the rule
is a choice, and a borderline case is worth a sentence in your analysis.

Each question is embedded once, in QUERY mode (embed_query), and the same vector is used for
every collection, because all six collections were built with the same embedding model.
"""

import json
import sys
from pathlib import Path

import chromadb
import chromadb.errors

from ingest import BUILD, CHROMA_PATH, EMBED_MODEL, STRATEGIES, WEEK4, get_embeddings

K = 3
COLLECTIONS = list(STRATEGIES)
EVIDENCE_QUESTIONS = [5, 8, 9]

QUESTIONS = [
    # (number, kind, question, must_contain: every piece must be in ONE chunk)
    (1, "fact", "What error code do you get when installing the VPN client on a personal device?",
     ["1103"]),
    (2, "fact", "How many previous passwords can a new password not match?",
     ["previous 12"]),
    (3, "fact", "What is the mailbox size limit?",
     ["50 GB"]),
    (4, "fact", "How long does a temporary administrator elevation last?",
     ["60-minute"]),
    (5, "procedure", "What are the steps to add a printer on macOS?",
     ["Open System Settings, then Printers and Scanners", "Click Add Printer, Scanner, or Fax",
      "Select the IP tab", "Protocol should be IPP", "Generic PostScript Printer",
      "Click Add and print a test page"]),
    (6, "procedure", "How do I change my password on Windows, including the step people usually skip?",
     ["Ctrl+Alt+Delete", "Choose Change a password", "the new password twice",
      "Lock and unlock the laptop"]),
    (7, "procedure", "What should I check, in order, before filing a ticket for a slow laptop?",
     ["browser tabs are open", "more than 90 percent full", "since the last full restart",
      "backup or sync is running"]),
    (8, "context", "Which VPN gateway should someone in Bangalore use, and why is its default protocol different?",
     ["vpn-in.example.com", "ISP filtering"]),
    (9, "context", "What is the macOS path for the Finance shared drive?",
     ["smb://files.example.com/finance"]),
    (10, "context", "My fans are loud all the time. Is that a ticket or something I fix myself?",
     ["Restart first", "more than a day"]),
]


def squash(text):
    """Lowercase and collapse whitespace, so a line break inside a chunk does not hide a match."""
    return " ".join(text.lower().split())


def is_hit(chunk_text, must_contain):
    text = squash(chunk_text)
    return all(squash(piece) in text for piece in must_contain)


_in_memory = {}
CACHE_PATH = BUILD / "fallback_vectors.json"


def query_collection(name, col, vector):
    """Top-K query. On Windows, Chroma 1.5.x sometimes cannot read a collection's saved vector
    index in a new process ("Error creating hnsw segment reader: Nothing found on disk"), and it
    then refuses to return the stored vectors too. The chunk texts and metadata are still
    readable, so in that case: read them, embed the texts again in passage mode (exactly as
    ingest did, so the vectors are the same), put them in a temporary in-memory Chroma
    collection with the same cosine distance, and run the same query there. Re-embedded
    vectors are cached in rag/build/fallback_vectors.json by chunk hash, so it is done once."""
    if name not in _in_memory:
        try:
            return col.query(query_embeddings=[vector], n_results=K,
                             include=["documents", "metadatas", "distances"])
        except chromadb.errors.InternalError as error:
            if "Nothing found on disk" not in str(error):
                raise
            print(f"  ({name}: Chroma could not open its saved index on this machine, "
                  f"so it is searched from an in-memory copy of its chunks)")
            records = col.get(include=["documents", "metadatas"])
            cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
            missing = [i for i in records["ids"] if i not in cache]
            if missing:
                texts = dict(zip(records["ids"], records["documents"]))
                vectors = get_embeddings().embed_documents([texts[i] for i in missing])   # passage mode
                cache.update(zip(missing, vectors))
                BUILD.mkdir(exist_ok=True)
                CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")
            copy = chromadb.EphemeralClient().get_or_create_collection(
                f"copy_{name}", metadata={"hnsw:space": "cosine"}, embedding_function=None)
            copy.add(ids=records["ids"], embeddings=[cache[i] for i in records["ids"]],
                     documents=records["documents"], metadatas=records["metadatas"])
            _in_memory[name] = copy
    return _in_memory[name].query(query_embeddings=[vector], n_results=K,
                                  include=["documents", "metadatas", "distances"])


def run_queries():
    """Ask every question against every collection. Returns {question number: {collection: [top 3]}}."""
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collections = {}
    for name in COLLECTIONS:
        col = client.get_collection(name)
        model = col.metadata.get("embedding_model")
        if model != EMBED_MODEL:
            raise SystemExit(f"{name} was built with {model}, but queries use {EMBED_MODEL}. Run rebuild first.")
        collections[name] = col

    emb = get_embeddings()
    results = {}
    for number, kind, question, must in QUESTIONS:
        vector = emb.embed_query(question)       # QUERY mode, as on Day 1
        results[number] = {}
        for name, col in collections.items():
            r = query_collection(name, col, vector)
            results[number][name] = [
                {"rank": i + 1, "distance": d, "text": doc, "source": m["source"],
                 "header_path": m.get("header_path", ""), "hit": is_hit(doc, must)}
                for i, (doc, m, d) in enumerate(zip(r["documents"][0], r["metadatas"][0], r["distances"][0]))
            ]
    BUILD.mkdir(exist_ok=True)
    (BUILD / "compare.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    return results


def print_grid(results):
    print(f"\n| Q | Kind | " + " | ".join(COLLECTIONS) + " |")
    print("|---|---|" + "---|" * len(COLLECTIONS))
    totals = {name: 0 for name in COLLECTIONS}
    by_kind = {kind: {name: 0 for name in COLLECTIONS} for kind in ("fact", "procedure", "context")}
    for number, kind, _, _ in QUESTIONS:
        cells = []
        for name in COLLECTIONS:
            top = results[number][name]
            first = next((c["rank"] for c in top if c["hit"]), None)
            cells.append(f"Y ({first})" if first else "N")
            if first:
                totals[name] += 1
                by_kind[kind][name] += 1
        print(f"| {number} | {kind} | " + " | ".join(cells) + " |")
    print("| **Total** | | " + " | ".join(f"**{totals[n]}/10**" for n in COLLECTIONS) + " |")
    for kind, counts in by_kind.items():
        n = sum(1 for q in QUESTIONS if q[1] == kind)
        print(f"| {kind} | | " + " | ".join(f"{counts[c]}/{n}" for c in COLLECTIONS) + " |")
    print("\nY (2) = hit, and the first chunk containing the answer was ranked 2nd.")


def format_top3(number, name, top):
    lines = [f"### {name}", ""]
    for c in top:
        where = c["source"] + (f" | {c['header_path']}" if c["header_path"] else "")
        mark = "HIT" if c["hit"] else "miss"
        lines.append(f"**{c['rank']}. {mark}** (distance {c['distance']:.3f}, {where})")
        lines.append("")
        lines.append("```")
        lines.append(c["text"])
        lines.append("```")
        lines.append("")
    return lines


def write_evidence(results):
    lines = ["# Evidence: top 3 chunks per collection for questions 5, 8 and 9", "",
             "Created by `python rag/compare.py`. HIT means that chunk contains the whole expected answer.", ""]
    for number in EVIDENCE_QUESTIONS:
        _, kind, question, must = QUESTIONS[number - 1]
        lines += [f"## Q{number} ({kind}): {question}", "",
                  "Must contain, in one chunk: " + ", ".join(f"`{m}`" for m in must), ""]
        for name in COLLECTIONS:
            lines += format_top3(number, name, results[number][name])
    path = WEEK4 / "evidence.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved the top 3 chunks for questions {EVIDENCE_QUESTIONS} to {path.name}")


def show(number):
    path = BUILD / "compare.json"
    if not path.exists():
        run_queries()
    results = json.loads(path.read_text(encoding="utf-8"))   # JSON keys are strings: "8", not 8
    _, kind, question, must = QUESTIONS[number - 1]
    print(f"Q{number} ({kind}): {question}\nMust contain, in one chunk: {must}\n")
    for name in COLLECTIONS:
        print("\n".join(format_top3(number, name, results[str(number)][name])))


def ask(question, name="markdown_headers"):
    """Ask any question of one collection and print its top 3 chunks (for demos)."""
    col = chromadb.PersistentClient(path=str(CHROMA_PATH)).get_collection(name)
    vector = get_embeddings().embed_query(question)          # query mode
    r = query_collection(name, col, vector)
    print(f"{name}, top {K} for: {question}\n")
    for rank, (cid, doc, meta, dist) in enumerate(
            zip(r["ids"][0], r["documents"][0], r["metadatas"][0], r["distances"][0]), start=1):
        where = meta["source"] + (f" | {meta['header_path']}" if meta.get("header_path") else "")
        print(f"--- {rank}. distance {dist:.3f}, {where}\n    id (hash): {cid}\n{doc}\n")


def main():
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "show" and args[1].isdigit():
        show(int(args[1]))
        return
    if len(args) in (2, 3) and args[0] == "ask":
        ask(*args[1:])
        return
    if args:
        print(__doc__)
        return
    results = run_queries()
    print_grid(results)
    write_evidence(results)


if __name__ == "__main__":
    main()
