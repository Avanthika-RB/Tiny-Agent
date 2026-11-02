# rag/: the Week 4 ingestion pipeline

Two scripts:

- `ingest.py` turns the knowledge base articles into six Chroma collections, one per chunking strategy, and keeps them up to date.
- `compare.py` asks every collection the same 10 test questions and measures hit@3.

Run everything from the `week4` folder, with the venv active and `NVIDIA_API_KEY` in the `.env` file at the top of the repo.

```
cd week4
.venv\Scripts\activate
pip install -r requirements.txt
```

Embedding model: `nvidia/nemotron-3.5-embed-1b` (set as `EMBED_MODEL` in `ingest.py`). The two models named in the assignment had been retired by NVIDIA.

## The pipeline

```
python rag/ingest.py ingest              load, clean, chunk, hash, embed and store only what changed
python rag/ingest.py ingest --dry-run    print what would change; touch nothing
python rag/ingest.py rebuild             delete the collections and manifest.json, ingest from scratch
```

Add `--strategy NAME` to `ingest` or `rebuild` to work on one collection only, for example `--strategy fixed_200`.

`ingest` prints one line per file it had to process, then a summary table:

```
| Collection | Added | Updated | Deleted | Skipped | Chunks in collection |
```

- **Added**: chunks with a new hash, embedded and stored.
- **Updated**: chunks that already existed but whose metadata changed (their position in the file, or the file they belong to).
- **Deleted**: chunks no file uses any more.
- **Skipped**: chunks that were already stored, counted per file. Duplicates count here, so this can be bigger than the collection.
- **Chunks in collection**: what is actually in Chroma after the run.

A run with no changes reports `0 chunks changed`, makes no API calls and takes well under a second.

## Looking at the stages one by one

These save to `rag/build/` and never touch Chroma.

```
python rag/ingest.py load                     read kb/ and kb_other_formats/      -> build/loaded.json
python rag/ingest.py clean                    clean every document; prints the HTML file before and after,
                                              and checks the HTML printer article equals the markdown one
                                                                                  -> build/cleaned.json
python rag/ingest.py chunk                    split with all six strategies, print chunk statistics
                                                                                  -> build/chunks_<strategy>.json
python rag/ingest.py show recursive_500 kb/03 print one article's chunks for one strategy
python rag/ingest.py first3 kb/01             first 3 chunks from fixed_200, recursive_500, markdown_headers
```

## The stages

| Stage | Function | What it does |
|---|---|---|
| Load | `load_markdown`, `load_text`, `load_html`, `load_pdf` | One loader per format. Every one returns `{"text", "metadata": {"source", "format", "title"}}`. The HTML loader turns headings and list items into markdown (`##`, `1.`) and drops `<head>` and `<style>`. |
| Clean | `clean_text` | Line endings to `\n`, curly quotes to straight, trims every line, joins sentences that were wrapped onto new lines, one blank line between blocks. After cleaning, the HTML printer article is identical to the markdown one. |
| Chunk | `chunk_<strategy>` | Six strategies (table below). Every chunk gets `chunk_index`, `strategy` and `hash` in its metadata, plus `header_path` for the markdown strategies. |
| Hash | `chunk_hash` | sha256 of the chunk text, lowercased with whitespace collapsed. Used as the chunk's Chroma id. |
| Embed | `RetryingEmbeddings` | Passage mode (`embed_documents`), 32 texts per call. On a 429 Too Many Requests it waits 1, 2, 4, 8 seconds and retries, up to 5 tries. |
| Store | `stage_ingest` | One Chroma collection per strategy, cosine distance, embedding model recorded in the collection metadata. |

| Collection | Splitter | Settings |
|---|---|---|
| `fixed_200` | CharacterTextSplitter | 200 characters, no overlap, `separator=""` (a true fixed window) |
| `fixed_500_overlap` | CharacterTextSplitter | 500 characters, 100 overlap, `separator=""` |
| `recursive_500` | RecursiveCharacterTextSplitter | 500 characters, 100 overlap |
| `markdown_headers` | MarkdownHeaderTextSplitter on `#`, `##`, `###`, then recursive 500/100 | header path written at the top of the chunk text and kept in metadata |
| `markdown_headers_noprefix` | same | header path in metadata only |
| `semantic` | SemanticChunker | NVIDIA embeddings, percentile breakpoints |

## What manifest.json means

`manifest.json` (in `week4`) is the pipeline's memory of what it has already done. For every source file it records:

```json
"kb/03-printer-setup-and-issues.md": {
  "file_hash": "...sha256 of the file on disk...",
  "format": "md",
  "embedding_model": "nvidia/nemotron-3.5-embed-1b",
  "ingested_at": "2026-11-01T16:10:12",
  "collections": {
    "recursive_500": { "file_hash": "...", "chunks": 6, "hashes": ["...", "..."] },
    "...": {}
  }
}
```

How `ingest` uses it:

1. **Unchanged file**: its hash matches the manifest, so it is skipped without chunking or embedding anything.
2. **Changed file**: re-chunked. Only chunks whose hash is not already in the collection are embedded. Chunks the file no longer has are deleted, unless another file still has them.
3. **New file**: chunked and embedded like a changed file.
4. **Deleted file**: its chunks are deleted from every collection, except chunks another file still has. Those are kept and pointed at that other file. (Removing `kb/06-software-requests-and-policy.md` keeps its chunks, because the `.txt` copy has the same text.)
5. **Embedding model changed**: `ingest` stops and asks for `rebuild`, because one collection cannot mix models.

Deduplication falls out of the hashing: the HTML printer article and the `.txt` software article produce exactly the same hashes as their markdown versions, so they add 0 chunks. The PDF does not, because its extracted text differs.

## Measuring: compare.py

```
python rag/compare.py          10 questions x 6 collections, k=3: hit@3 grid, totals, evidence.md
python rag/compare.py show 8   the top 3 chunks of every collection for question 8
```

- Each question is embedded once in query mode (`embed_query`) and searched in every collection with `n_results=3`.
- A collection gets **Y** for a question if one of its top 3 chunks contains every piece of the expected answer (`must_contain` in `QUESTIONS`). `Y (2)` means the first such chunk was ranked 2nd.
- The top 3 chunks of every collection for questions 5, 8 and 9 are written to `week4/evidence.md`.

**Windows note.** Chroma 1.5.x on Windows sometimes cannot read a collection's saved index in a later process ("Error creating hnsw segment reader: Nothing found on disk"). When that happens, `compare.py` reads the collection's chunks, re-embeds them in passage mode (cached in `rag/build/fallback_vectors.json`) and runs the same query on an in-memory copy. The results are the same; it prints a note for each collection where it had to do this.

## Files

| File | What it is |
|---|---|
| `rag/ingest.py` | the pipeline |
| `rag/compare.py` | the hit@3 comparison |
| `rag/build/` | intermediate files (ignored by git, rebuilt by the scripts) |
| `chroma_db/` | the six collections (ignored by git; `python rag/ingest.py rebuild` recreates them) |
| `manifest.json` | what has been ingested, per file and collection |
| `results.md`, `evidence.md`, `chunking-analysis.md` | the Day 6 measurement and analysis |
