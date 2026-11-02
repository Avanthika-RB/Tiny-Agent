"""Week 4 ingestion pipeline: load -> clean -> chunk -> hash -> embed -> store.

Run from the week4 folder.

The pipeline (Day 5):
    python rag/ingest.py ingest              load, clean, chunk, hash, embed and store ONLY what changed
    python rag/ingest.py ingest --dry-run    print what would change, touch nothing
    python rag/ingest.py rebuild             delete the collections and manifest.json, ingest from scratch
    Add --strategy NAME to ingest or rebuild to do only one strategy, e.g. --strategy fixed_200

Looking at individual stages (they save to rag/build/ and do not touch Chroma):
    python rag/ingest.py load      read kb/ and kb_other_formats/ into Documents  -> build/loaded.json
    python rag/ingest.py clean     clean every Document (prints before/after HTML)  -> build/cleaned.json
    python rag/ingest.py chunk     split with every strategy, print chunk stats     -> build/chunks_<strategy>.json
    python rag/ingest.py show recursive_500 kb/03     print one article's chunks (to compare with chunkviz)
    python rag/ingest.py first3 kb/01                first 3 chunks from fixed_200, recursive_500, markdown_headers

Strategies: fixed_200, fixed_500_overlap, recursive_500 (Day 3),
            markdown_headers, markdown_headers_noprefix, semantic (Day 4).

How ingest decides what to do (Day 5):
  - Every chunk's id in Chroma is the sha256 hash of its normalised text, so identical text is
    stored once, even if it comes from two files (the HTML and markdown printer articles).
  - manifest.json records, per source file: its file hash, and per collection the chunk count,
    the chunk hashes, the embedding model and when it was ingested.
  - A file whose hash has not changed is skipped without chunking or embedding anything.
  - A changed file is re-chunked; only chunks with new hashes are embedded. Chunks the file no
    longer has are deleted, unless another file still has them.
  - A file deleted from disk has its chunks removed (same rule).

Every Document has the same shape:
    {"text": "...", "metadata": {"source": "kb/03-printer-setup-and-issues.md", "format": "md", "title": "..."}}
Every chunk adds "chunk_index", "strategy" and "hash" (and "header_path" for the markdown strategies).
"""

import hashlib
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import chromadb
from bs4 import BeautifulSoup
from dotenv import find_dotenv, load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_text_splitters import CharacterTextSplitter, MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from pypdf import PdfReader

WEEK4 = Path(__file__).resolve().parent.parent
SOURCE_DIRS = [WEEK4 / "kb", WEEK4 / "kb_other_formats"]
BUILD = Path(__file__).resolve().parent / "build"
CHROMA_PATH = WEEK4 / "chroma_db"
EMBED_MODEL = "nvidia/nemotron-3.5-embed-1b"


# ===========================================================================
# STAGE 1: LOAD. One loader per format, all returning the same Document shape.
# Loaders only turn a file into text with its structure (headings, list items)
# marked the markdown way. They do NOT tidy the text: that is clean_text's job.
# ===========================================================================
def make_doc(path, fmt, text, title):
    return {"text": text, "metadata": {"source": path.relative_to(WEEK4).as_posix(), "format": fmt, "title": title}}


def first_heading(text):
    for line in text.splitlines():
        if line.strip():
            return line.strip().lstrip("#").strip()
    return ""


def load_markdown(path):
    text = path.read_text(encoding="utf-8")
    return make_doc(path, "md", text, first_heading(text))


def load_text(path):
    text = path.read_text(encoding="utf-8")
    return make_doc(path, "txt", text, first_heading(text))


def load_html(path):
    """HTML -> markdown-style text. <h1>..<h3> become #..###, <li> become '1.' or '-' items,
    <p> become paragraphs. <head>, <style> and <script> are dropped. Each element's text is
    kept exactly as written in the file, line breaks and all."""
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    title = soup.title.get_text() if soup.title else path.stem
    for tag in soup(["head", "style", "script"]):
        tag.decompose()

    blocks = []
    for el in soup.body.find_all(["h1", "h2", "h3", "h4", "p", "li", "tr"]):
        text = el.get_text()
        if el.name.startswith("h"):
            blocks.append("#" * int(el.name[1]) + " " + text)
        elif el.name == "li":
            if el.parent.name == "ol":
                number = el.parent.find_all("li", recursive=False).index(el) + 1
                blocks.append(f"{number}. {text}")
            else:
                blocks.append(f"- {text}")
        elif el.name == "tr":
            cells = [c.get_text() for c in el.find_all(["th", "td"])]
            blocks.append("| " + " | ".join(cells) + " |")
        elif el.name == "p" and el.find_parent("li") is None:
            blocks.append(text)
    # Join blocks the markdown way: a blank line between blocks, but list items and table
    # rows that follow each other sit on consecutive lines (one list, one table).
    text = ""
    for i, block in enumerate(blocks):
        if i:
            prev = blocks[i - 1]
            same_list = block[:1] in "|-" and prev[:1] == block[:1] or (block[:1].isdigit() and prev[:1].isdigit())
            text += "\n" if same_list else "\n\n"
        text += block
    h1 = soup.find("h1")
    return make_doc(path, "html", text, h1.get_text() if h1 else title)


def load_pdf(path):
    """PDF -> plain text, page by page. A PDF has no heading markup, so headings come out
    as ordinary lines. That is a real limit of PDF, not something cleaning can fully undo."""
    pages = [page.extract_text() or "" for page in PdfReader(str(path)).pages]
    text = "\n".join(pages)
    return make_doc(path, "pdf", text, first_heading(text))


LOADERS = {".md": load_markdown, ".txt": load_text, ".html": load_html, ".pdf": load_pdf}


def load_all_documents():
    docs = []
    for folder in SOURCE_DIRS:
        for path in sorted(folder.iterdir()):
            loader = LOADERS.get(path.suffix.lower())
            if loader is not None:
                docs.append(loader(path))
    return docs


def stage_load():
    docs = load_all_documents()
    for d in docs:
        m = d["metadata"]
        print(f"  {m['format']:<4} {len(d['text']):>5} chars  {m['source']}  ({m['title']})")
    save("loaded.json", docs)
    print(f"Loaded {len(docs)} documents -> {BUILD / 'loaded.json'}")
    return docs


#stage 2
def clean_text(text):
    """Return a cleaned version of one document's text.

    Goal: the HTML printer article and the markdown printer article must come out
    exactly the same, so that on Day 5 they produce the same hashes.
    """
    text = text.replace("\r\n", "\n") #all lines end with \n
    text = text.replace("‘", "'").replace("’", "'")   #make curly quotes straight
    text = text.replace("“", '"').replace("”", '"')  

    lines = [line.strip() for line in text.split("\n")] #remove spaces at start/end of lines
    text = "\n".join(lines)

    cleaned_blocks = [] #goes through text 1 paragraph/block at a time seperated by blank line
    for block in text.split("\n\n"):
        cleaned_lines = []
        for line in block.split("\n"):
            line = " ".join(line.split()) #single spaces
            if line == "":
                continue
            if cleaned_lines and not starts_new_line(line):
                cleaned_lines[-1] = cleaned_lines[-1] + " " + line #join rest of previous sentence onto line
            else:
                cleaned_lines.append(line)
        if cleaned_lines:
            cleaned_blocks.append("\n".join(cleaned_lines))
    return "\n\n".join(cleaned_blocks) #join blocks together


def starts_new_line(line):
    """Headings, list items and table rows must always stay on their own line."""
    if line.startswith("#"):          # heading: "# Title", "## Section"
        return True
    if line.startswith("- ") or line.startswith("* "):   # bullet item
        return True
    if line.startswith("|"):          # table row
        return True
    # Numbered item such as "3. Do something": digits, then ". "
    first_word = line.split(" ")[0]   # "3."
    return first_word.endswith(".") and first_word[:-1].isdigit()


def stage_clean():
    docs = load("loaded.json")
    cleaned = [{"text": clean_text(d["text"]), "metadata": d["metadata"]} for d in docs]
    for before, after in zip(docs, cleaned):
        if before["metadata"]["format"] == "html":
            print(f"--- BEFORE clean ({before['metadata']['source']}, first 600 chars) ---")
            print(before["text"][:600])
            print(f"\n--- AFTER clean ---")
            print(after["text"][:600])
    md = next((d for d in cleaned if d["metadata"]["source"] == "kb/03-printer-setup-and-issues.md"), None)
    html = next((d for d in cleaned if d["metadata"]["format"] == "html"), None)
    if md and html:
        same = md["text"].strip() == html["text"].strip()
        print(f"\nCleaned HTML printer article == cleaned markdown printer article? {same}")
    save("cleaned.json", cleaned)
    print(f"Cleaned {len(cleaned)} documents -> {BUILD / 'cleaned.json'}")
    return cleaned


# ===========================================================================
# STAGE 3: CHUNK. One function per strategy. Each returns a list of chunk Documents.
# ===========================================================================
def split_with(splitter, docs, strategy):
    chunks = []
    for d in docs:
        for i, piece in enumerate(splitter.split_text(d["text"])):
            chunks.append({"text": piece, "metadata": {**d["metadata"], "chunk_index": i, "strategy": strategy}})
    return chunks


def chunk_fixed_200(docs):
    # separator="" makes it a true fixed-size window: cut every 200 characters, wherever that lands.
    # (With the default separator "\n\n" it would only cut between paragraphs, and keep long
    #  paragraphs whole, so it would not really be fixed-size.)
    return split_with(CharacterTextSplitter(separator="", chunk_size=200, chunk_overlap=0), docs, "fixed_200")


def chunk_fixed_500_overlap(docs):
    return split_with(CharacterTextSplitter(separator="", chunk_size=500, chunk_overlap=100), docs, "fixed_500_overlap")


def chunk_recursive_500(docs):
    # Tries to cut at "\n\n" first, then "\n", then " ", then anywhere, so pieces end at natural breaks.
    return split_with(RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100), docs, "recursive_500")


HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]


def chunk_markdown(docs, strategy, prefix):
    """Day 4. Step 1: MarkdownHeaderTextSplitter cuts the document at every #, ## and ### heading,
    and moves the heading text into metadata (h1, h2, h3). Step 2: any section still longer
    than 500 characters is cut again with the recursive splitter (500 / 100).
    The header path (e.g. "VPN Access Guide > Regional gateways") always goes into metadata.
    prefix=True ALSO writes it at the top of the chunk text, so it is part of what gets embedded."""
    by_header = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS)
    too_long = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = []
    for d in docs:
        index = 0
        for section in by_header.split_text(d["text"]):
            path = " > ".join(section.metadata[key] for _, key in HEADERS if key in section.metadata)
            body = section.page_content.replace("  \n", "\n")   # the splitter joins lines with "  \n"
            for piece in too_long.split_text(body):
                text = f"{path}\n\n{piece}" if prefix and path else piece
                chunks.append({"text": text, "metadata": {**d["metadata"], "chunk_index": index,
                                                          "strategy": strategy, "header_path": path}})
                index += 1
    return chunks


def chunk_markdown_headers(docs):
    return chunk_markdown(docs, "markdown_headers", prefix=True)


def chunk_markdown_headers_noprefix(docs):
    return chunk_markdown(docs, "markdown_headers_noprefix", prefix=False)


def chunk_semantic(docs):
    """Day 4. SemanticChunker splits the text into sentences, embeds EVERY sentence, and cuts
    where the meaning jumps: wherever the distance between neighbouring sentences is above the
    95th percentile of all those distances. That needs one embedding per sentence, so it is the
    slowest strategy by far, and the chunk sizes vary a lot."""
    splitter = SemanticChunker(get_embeddings(), breakpoint_threshold_type="percentile")
    return split_with(splitter, docs, "semantic")


STRATEGIES = {
    "fixed_200": chunk_fixed_200,
    "fixed_500_overlap": chunk_fixed_500_overlap,
    "recursive_500": chunk_recursive_500,
    "markdown_headers": chunk_markdown_headers,
    "markdown_headers_noprefix": chunk_markdown_headers_noprefix,
    "semantic": chunk_semantic,
}


def stats(chunks):
    sizes = [len(c["text"]) for c in chunks]
    return {"chunks": len(sizes), "avg": sum(sizes) / len(sizes), "min": min(sizes), "max": max(sizes)}


def stage_chunk(names):
    docs = load("cleaned.json")
    for name in names:
        start = time.perf_counter()
        chunks = STRATEGIES[name](docs)
        seconds = time.perf_counter() - start
        s = stats(chunks)
        save(f"chunks_{name}.json", chunks)
        record_time(name, "chunk", seconds)
        print(f"  {name:<26} {s['chunks']:>4} chunks  avg {s['avg']:6.1f}  min {s['min']:>4}  max {s['max']:>4}  "
              f"({seconds:.2f}s)")
        if name == "semantic":
            print_distribution(chunks)


def print_distribution(chunks):
    """How many chunks fall in each size range, as a text bar chart."""
    buckets = [(0, 100), (100, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 10**6)]
    sizes = [len(c["text"]) for c in chunks]
    print("     size distribution:")
    for low, high in buckets:
        n = sum(low <= x < high for x in sizes)
        label = f"{low}-{high}" if high < 10**6 else f"{low}+"
        print(f"     {label:>10} chars  {n:>3}  {'#' * n}")


def record_time(name, stage, seconds):
    """Keep chunk and embed timings in build/timing.json so store can report the full ingest time."""
    path = BUILD / "timing.json"
    timing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    timing.setdefault(name, {})[stage] = seconds
    save("timing.json", timing)


# ===========================================================================
# STAGE 4: EMBED. Passage mode, in batches, retrying when the API says "slow down" (429).
# ===========================================================================
BATCH_SIZE = 32       # texts per API call
MAX_TRIES = 5         # give up after this many tries of one batch


class RetryingEmbeddings(Embeddings):
    """NVIDIAEmbeddings with two protections against API limits:
      - batching: texts are sent BATCH_SIZE at a time, never all at once;
      - backoff: if a call fails with 429 Too Many Requests, wait and try again,
        doubling the wait each time (1s, 2s, 4s, 8s), plus a little randomness.
    SemanticChunker uses this object too, so its many sentence embeddings are protected as well."""

    def __init__(self):
        load_dotenv(find_dotenv(usecwd=True))
        self.inner = NVIDIAEmbeddings(model=EMBED_MODEL, truncate="END")

    def embed_documents(self, texts):
        vectors = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start:start + BATCH_SIZE]
            vectors.extend(with_backoff(lambda: self.inner.embed_documents(batch)))
        return vectors

    def embed_query(self, text):
        return with_backoff(lambda: self.inner.embed_query(text))


def with_backoff(call):
    for attempt in range(1, MAX_TRIES + 1):
        try:
            return call()
        except Exception as error:
            rate_limited = "429" in str(error) or "Too Many Requests" in str(error)
            if not rate_limited or attempt == MAX_TRIES:
                raise
            wait = 2 ** (attempt - 1) + random.random()
            print(f"      (rate limited, waiting {wait:.1f}s, then try {attempt + 1} of {MAX_TRIES})")
            time.sleep(wait)


_embeddings = None


def get_embeddings():
    """One shared RetryingEmbeddings object for the whole run."""
    global _embeddings
    if _embeddings is None:
        _embeddings = RetryingEmbeddings()
    return _embeddings


# ===========================================================================
# STAGE 5: INGEST. Hash every chunk, compare with the manifest, and only embed and
# store what changed. Running it twice in a row changes nothing the second time.
# ===========================================================================
MANIFEST_PATH = WEEK4 / "manifest.json"


def chunk_hash(text):
    """Content hash of a chunk: sha256 of its text, lowercased with all whitespace collapsed.
    The same text always gives the same hash, whichever file it came from. It is used as the
    Chroma id, so a chunk that is already stored can never be stored twice."""
    normalised = " ".join(text.lower().split())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def file_hash(source):
    """Hash of the raw file on disk. If it is the same as last time, the file has not changed."""
    return hashlib.sha256((WEEK4 / source).read_bytes()).hexdigest()


def load_manifest():
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"embedding_model": EMBED_MODEL, "files": {}}


def save_manifest(manifest):
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def stage_ingest(names, dry_run=False):
    started = time.perf_counter()
    manifest = load_manifest()
    if manifest["files"] and manifest["embedding_model"] != EMBED_MODEL:
        raise SystemExit("The embedding model changed since the last ingest. Run: python rag/ingest.py rebuild")

    # Load and clean every file (cheap), then hash the raw files to see which changed.
    docs = {d["metadata"]["source"]: {"text": clean_text(d["text"]), "metadata": d["metadata"]}
            for d in load_all_documents()}
    hash_now = {source: file_hash(source) for source in docs}
    removed_files = [s for s in manifest["files"] if s not in docs]

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    existing_collections = {c.name for c in client.list_collections()}
    if dry_run:
        print("DRY RUN: nothing will be embedded, written to Chroma, or saved to manifest.json.\n")

    rows = []
    for name in names:
        counts = {"added": 0, "updated": 0, "deleted": 0, "skipped": 0}
        if name in existing_collections:
            col = client.get_collection(name)
            stored = set(col.get(include=[])["ids"])
        else:
            col = None if dry_run else client.create_collection(
                name, metadata={"hnsw:space": "cosine", "embedding_model": EMBED_MODEL}, embedding_function=None)
            stored = set()

        # Who uses each hash right now, according to the manifest: {hash: {source, ...}}
        users = {}
        for source, entry in manifest["files"].items():
            for h in entry.get("collections", {}).get(name, {}).get("hashes", []):
                users.setdefault(h, set()).add(source)
        maybe_unused = set()   # hashes some file stopped using; deleted at the end if nobody uses them

        for source, doc in docs.items():
            previous = manifest["files"].get(source, {}).get("collections", {}).get(name)
            if previous and previous["file_hash"] == hash_now[source]:
                counts["skipped"] += len(previous["hashes"])      # unchanged file: no chunking, no embedding
                continue

            # Changed or new file: chunk it and hash every chunk.
            new = {}
            for c in STRATEGIES[name]([doc]):
                h = chunk_hash(c["text"])
                c["metadata"]["hash"] = h
                new.setdefault(h, c)            # identical chunks inside one file collapse to one
            old_hashes = previous["hashes"] if previous else []

            to_add = [c for h, c in new.items() if h not in stored]
            already = [h for h in new if h in stored]
            moved = [h for h in already if h in old_hashes and old_hashes.index(h) != list(new).index(h)]
            file_counts = {"added": len(to_add), "updated": len(moved), "deleted": 0,
                           "skipped": len(already) - len(moved)}

            if to_add and not dry_run:
                vectors = get_embeddings().embed_documents([c["text"] for c in to_add])
                col.add(ids=[c["metadata"]["hash"] for c in to_add], embeddings=vectors,
                        documents=[c["text"] for c in to_add], metadatas=[c["metadata"] for c in to_add])
            if moved and not dry_run:
                col.update(ids=moved, metadatas=[new[h]["metadata"] for h in moved])
            stored.update(new)

            for h in set(old_hashes) - set(new):
                users.get(h, set()).discard(source)
                maybe_unused.add(h)
            for h in new:
                users.setdefault(h, set()).add(source)

            for key in counts:
                counts[key] += file_counts[key]
            print(f"  {name:<26} {source:<55} +{file_counts['added']} added  ~{file_counts['updated']} updated  "
                  f"={file_counts['skipped']} already stored")
            if not dry_run:
                entry = manifest["files"].setdefault(source, {"collections": {}})
                entry.update({"file_hash": hash_now[source], "format": doc["metadata"]["format"],
                              "embedding_model": EMBED_MODEL,
                              "ingested_at": datetime.now().isoformat(timespec="seconds")})
                entry["collections"][name] = {"file_hash": hash_now[source], "chunks": len(new),
                                              "hashes": list(new)}

        # Files that were deleted from disk: everything they used is now possibly unused.
        for source in removed_files:
            for h in manifest["files"][source].get("collections", {}).get(name, {}).get("hashes", []):
                users.get(h, set()).discard(source)
                maybe_unused.add(h)

        # Delete chunks nobody uses any more. A chunk another file still uses (the .txt copy of
        # the software article, say) stays, and its metadata is pointed at that other file.
        to_delete = [h for h in maybe_unused if not users.get(h) and h in stored]
        to_repoint = [h for h in maybe_unused if users.get(h) and h in stored]
        if to_delete and not dry_run:
            col.delete(ids=to_delete)
        if to_repoint and not dry_run:
            current = col.get(ids=to_repoint, include=["metadatas"])
            for h, meta in zip(current["ids"], current["metadatas"]):
                if meta["source"] not in users[h]:
                    new_source = sorted(users[h])[0]
                    index = manifest["files"][new_source]["collections"][name]["hashes"].index(h)
                    col.update(ids=[h], metadatas=[{**meta, **docs[new_source]["metadata"], "chunk_index": index}])
                    counts["updated"] += 1
        counts["deleted"] += len(to_delete)
        if to_delete:
            print(f"  {name:<26} {'(chunks no file uses any more)':<55} -{len(to_delete)} deleted")

        size = (col.count() if col else 0) if not dry_run else len(stored) - len(to_delete)
        rows.append((name, counts, size))

    if not dry_run:
        for source in removed_files:
            del manifest["files"][source]
        manifest["embedding_model"] = EMBED_MODEL
        save_manifest(manifest)

    print(f"\n| Collection | Added | Updated | Deleted | Skipped | Chunks in collection |")
    print(f"|---|---|---|---|---|---|")
    for name, c, size in rows:
        print(f"| {name} | {c['added']} | {c['updated']} | {c['deleted']} | {c['skipped']} | {size} |")
    changes = sum(c["added"] + c["updated"] + c["deleted"] for _, c, _ in rows)
    verb = "would change" if dry_run else "changed"
    print(f"\n{changes} chunks {verb}. Took {time.perf_counter() - started:.1f}s."
          + ("" if dry_run else f" Manifest: {MANIFEST_PATH.name}"))


def rebuild(names):
    """Start clean: delete the collections and the manifest, then ingest everything."""
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    for c in client.list_collections():
        if c.name in names:
            client.delete_collection(c.name)
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()
    print(f"Deleted {len(names)} collections and manifest.json. Ingesting from scratch...\n")
    stage_ingest(names)


# ===========================================================================
# Helpers and command line
# ===========================================================================
def save(filename, data):
    BUILD.mkdir(exist_ok=True)
    (BUILD / filename).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def load(filename):
    path = BUILD / filename
    if not path.exists():
        raise SystemExit(f"{path} does not exist yet. Run the earlier stage first.")
    return json.loads(path.read_text(encoding="utf-8"))


def show(strategy, file_part):
    """Print one article's chunks for one strategy, numbered, to compare with chunkviz."""
    chunks = [c for c in load(f"chunks_{strategy}.json") if file_part in c["metadata"]["source"]]
    sources = sorted({c["metadata"]["source"] for c in chunks})
    if len(sources) != 1:
        raise SystemExit(f"'{file_part}' matches {len(sources)} files: {sources}. Be more specific.")
    print(f"{strategy}: {len(chunks)} chunks from {sources[0]}\n")
    for c in chunks:
        path = c["metadata"].get("header_path")
        print(f"----- chunk {c['metadata']['chunk_index']} ({len(c['text'])} chars)"
              + (f"  header_path: {path}" if path else "") + " -----")
        print(c["text"])


def first3(file_part):
    """For day4-notes.md: the first 3 chunks of one article from three strategies, one after another."""
    for strategy in ["fixed_200", "recursive_500", "markdown_headers"]:
        chunks = [c for c in load(f"chunks_{strategy}.json") if file_part in c["metadata"]["source"]]
        print(f"\n{'=' * 70}\n{strategy}  ({chunks[0]['metadata']['source']})\n{'=' * 70}")
        for c in chunks[:3]:
            print(f"--- chunk {c['metadata']['chunk_index']} ({len(c['text'])} chars) ---")
            print(c["text"] + "\n")


def main():
    args = sys.argv[1:]
    if len(args) == 3 and args[0] == "show":
        show(args[1], args[2])
        return
    if len(args) == 2 and args[0] == "first3":
        first3(args[1])
        return
    if not args or args[0] not in ("load", "clean", "chunk", "ingest", "rebuild", "all"):
        print(__doc__)
        return
    stage = args[0]
    names = list(STRATEGIES)
    if "--strategy" in args:
        names = [args[args.index("--strategy") + 1]]
        if names[0] not in STRATEGIES:
            raise SystemExit(f"Unknown strategy. Choose from: {', '.join(STRATEGIES)}")

    if stage == "load":
        stage_load()
    elif stage == "clean":
        stage_clean()
    elif stage == "chunk":
        stage_chunk(names)
    elif stage in ("ingest", "all"):
        stage_ingest(names, dry_run="--dry-run" in args)
    elif stage == "rebuild":
        rebuild(names)


if __name__ == "__main__":
    main()
