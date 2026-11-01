# Week 4 Starter: Data Ingestion Pipeline

## What is here

- kb/: six IT knowledge base articles in markdown. Headers, numbered procedures, two tables, and long
  paragraphs, on purpose. Each chunking technique will fail visibly somewhere in here.
- kb_other_formats/: the printer article as HTML (and PDF if present), the software article as plain
  text. These exist so your loader step handles more than one format. The content is identical to the
  markdown versions. Your deduplication step should notice that.
- questions.md: ten retrieval test questions with expected answers and where they live. Three kinds:
  fact, procedure, context.
- results-template.md: the empty grid to fill in.

## Tech stack

Install:

    pip install chromadb langchain-chroma langchain-nvidia-ai-endpoints langchain-text-splitters langchain-experimental langchain-community unstructured markdown pypdf beautifulsoup4

Embedding model, hosted on build.nvidia.com, same NVIDIA_API_KEY as before:

    from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
    emb = NVIDIAEmbeddings(model="nvidia/llama-nemotron-embed-1b-v2", truncate="END")

If that model is unavailable in the catalog, fall back to "nvidia/nv-embedqa-e5-v5" (English only, 512 token
limit, so truncate="END" matters). Check https://build.nvidia.com/models?q=embed for what is live.

One thing most tutorials skip: NVIDIA retrieval models embed queries and passages differently. The LangChain
class handles it for you: embed_documents() uses passage mode, embed_query() uses query mode. If you call the
raw API yourself, you must pass input_type="passage" when ingesting and input_type="query" when searching.
Mixing them up quietly makes retrieval worse. Try it once on purpose on Day 1 and see.

Vector store: Chroma in persistent local mode. No server, no Docker.

    import chromadb
    client = chromadb.PersistentClient(path="./chroma_db")

Splitters, all from langchain_text_splitters unless noted:
- CharacterTextSplitter (fixed size)
- RecursiveCharacterTextSplitter
- MarkdownHeaderTextSplitter
- SemanticChunker from langchain_experimental.text_splitter

## Gotchas

1. Chroma collection names must be 3 to 63 characters, start and end with a letter or digit, no spaces.
2. Chroma's default distance is L2. Set metadata={"hnsw:space": "cosine"} when you create each collection so
   the scores are comparable with what the videos talk about.
3. Embedding 6 documents five times is a few hundred API calls. Batch them (the LangChain class does) and
   expect the semantic chunker to be the slowest because it embeds every sentence to find breakpoints.
4. MarkdownHeaderTextSplitter keeps the header text in metadata, not in the chunk text, by default. Decide
   whether to prepend the header path to the chunk text before embedding. Try both. This single decision
   changes the context-question results more than anything else.
5. For deduplication, hash the normalised chunk text (lowercase, collapsed whitespace), not the raw file.
   The HTML and markdown versions of the printer article should produce the same hashes after normalisation
   if your cleaning step is good. They will not if it is sloppy. That is the test.
