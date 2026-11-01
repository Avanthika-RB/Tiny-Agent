"""Week 4 ingestion pipeline: load -> clean -> chunk -> embed -> store.

Run from the week4 folder. Each stage reads the previous stage's output from rag/build/,
so you can run them one at a time and look at what each produced:

    python rag/ingest.py load      read kb/ and kb_other_formats/ into Documents  -> build/loaded.json
    python rag/ingest.py clean     clean every Document (prints before/after HTML)  -> build/cleaned.json
    python rag/ingest.py chunk     split with every strategy, print chunk stats     -> build/chunks_<strategy>.json
    python rag/ingest.py embed     embed every chunk (passage mode)                 -> build/vectors_<strategy>.json
    python rag/ingest.py store     write each strategy to its own Chroma collection, print stats
    python rag/ingest.py all       all five stages in order

    Add --strategy NAME to chunk/embed/store/all to do only one strategy, e.g. --strategy fixed_200

    python rag/ingest.py show recursive_500 kb/03     print one article's chunks (to compare with chunkviz)
    python rag/ingest.py first3 kb/01                first 3 chunks from fixed_200, recursive_500, markdown_headers

Strategies: fixed_200, fixed_500_overlap, recursive_500 (Day 3),
            markdown_headers, markdown_headers_noprefix, semantic (Day 4).
The semantic strategy calls the embedding model while chunking, so its chunk stage needs the API.

Every Document, at every stage, has the same shape:
    {"text": "...", "metadata": {"source": "kb/03-printer-setup-and-issues.md", "format": "md", "title": "..."}}
Every chunk adds "chunk_index" and "strategy" to that metadata.
"""

import json
import sys
import time
from pathlib import Path

import chromadb
from bs4 import BeautifulSoup
from dotenv import find_dotenv, load_dotenv
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


def stage_load():
    docs = []
    for folder in SOURCE_DIRS:
        for path in sorted(folder.iterdir()):
            loader = LOADERS.get(path.suffix.lower())
            if loader is None:
                print(f"  skipped (no loader): {path.name}")
                continue
            docs.append(loader(path))
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
# STAGE 4: EMBED. Passage mode (embed_documents) for everything we store.
# ===========================================================================
def get_embeddings():
    load_dotenv(find_dotenv(usecwd=True))
    return NVIDIAEmbeddings(model=EMBED_MODEL, truncate="END")


def stage_embed(names):
    emb = get_embeddings()
    for name in names:
        chunks = load(f"chunks_{name}.json")
        start = time.perf_counter()
        vectors = emb.embed_documents([c["text"] for c in chunks])   # the library sends these in batches
        seconds = time.perf_counter() - start
        save(f"vectors_{name}.json", {"model": EMBED_MODEL, "seconds": seconds, "vectors": vectors})
        record_time(name, "embed", seconds)
        print(f"  {name:<26} {len(vectors):>4} vectors x {len(vectors[0])} dims  ({seconds:.1f}s)")


# ===========================================================================
# STAGE 5: STORE. One Chroma collection per strategy, rebuilt from scratch each run.
# (Day 5 replaces "rebuild from scratch" with hashing and incremental updates.)
# ===========================================================================
def stage_store(names):
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    existing = {c.name for c in client.list_collections()}
    rows = []
    for name in names:
        chunks = load(f"chunks_{name}.json")
        embedded = load(f"vectors_{name}.json")
        start = time.perf_counter()
        if name in existing:
            client.delete_collection(name)
        col = client.create_collection(
            name, metadata={"hnsw:space": "cosine", "embedding_model": embedded["model"]}, embedding_function=None
        )
        col.add(
            ids=[f"{c['metadata']['source']}#{c['metadata']['chunk_index']}" for c in chunks],
            embeddings=embedded["vectors"],
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
        )
        s = stats(chunks)
        timing = json.loads((BUILD / "timing.json").read_text(encoding="utf-8")).get(name, {})
        total = timing.get("chunk", 0) + embedded["seconds"] + time.perf_counter() - start
        rows.append((name, s, col.count(), total))
    print(f"\n| Collection | Chunks | Avg chars | Min | Max | Ingest time (s) |")
    print(f"|---|---|---|---|---|---|")
    for name, s, count, seconds in rows:
        print(f"| {name} | {count} | {s['avg']:.0f} | {s['min']} | {s['max']} | {seconds:.1f} |")
    print("\n(Ingest time = chunking + embedding + storing.)")


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
    if not args or args[0] not in ("load", "clean", "chunk", "embed", "store", "all"):
        print(__doc__)
        return
    stage = args[0]
    names = list(STRATEGIES)
    if "--strategy" in args:
        names = [args[args.index("--strategy") + 1]]
        if names[0] not in STRATEGIES:
            raise SystemExit(f"Unknown strategy. Choose from: {', '.join(STRATEGIES)}")

    if stage in ("load", "all"):
        print("== load =="); stage_load()
    if stage in ("clean", "all"):
        print("\n== clean =="); stage_clean()
    if stage in ("chunk", "all"):
        print("\n== chunk =="); stage_chunk(names)
    if stage in ("embed", "all"):
        print("\n== embed =="); stage_embed(names)
    if stage in ("store", "all"):
        print("\n== store =="); stage_store(names)


if __name__ == "__main__":
    main()
