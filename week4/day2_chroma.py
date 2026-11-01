"""Day 2: what is a vector database. Chroma by hand.

    python day2_chroma.py --list-models               print the embedding models your key can use
    python day2_chroma.py --second-model <model-id>   run everything, including the two-model comparison
    python day2_chroma.py                             run everything except the two-model comparison

Uses the same 20 sentences and printer question as Day 1 (imported from day1_embeddings.py).
Every run starts by deleting the two Day 2 collections, so you can run it as often as you like.

Steps (each prints a header):
  1. PersistentClient + a collection with cosine distance
  2. Add the 20 sentences with ids and metadata (topic)
  3. Query with the printer question, k=3
  4. Query with a metadata filter (topic = vpn)
  5. Query with a document filter (text contains a word)
  6. Add a 21st sentence, query, update it, delete it, count, peek
  7. Look at what Chroma wrote to disk
  8. A second collection with a second embedding model: compare top 3, vector lengths,
     and what happens if you try to mix the two models in one collection
"""

import os
import sys
from pathlib import Path

import chromadb
from dotenv import find_dotenv, load_dotenv
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

from day1_embeddings import MODEL, QUESTION, SENTENCES

DB_PATH = Path(__file__).parent / "chroma_db"
MAIN = "day2_main"
SECOND = "day2_second"
K = 3


def header(text):
    print(f"\n{'=' * 78}\n{text}\n{'=' * 78}")


def show(result, label=""):
    """Print one Chroma query result. Chroma returns lists of lists (one inner list per query)."""
    if label:
        print(label)
    ids = result["ids"][0]
    if not ids:
        print("   (no results)")
    for rank, (i, doc, meta, dist) in enumerate(
        zip(ids, result["documents"][0], result["metadatas"][0], result["distances"][0]), start=1
    ):
        # With cosine space, Chroma's distance = 1 - cosine similarity. Smaller distance = closer.
        print(f"   {rank}. {i} [{meta['topic']:<8}] distance={dist:.3f} (similarity {1 - dist:.3f})  {doc}")


def fresh_collection(client, name):
    """Delete the collection if it exists from an earlier run, then create it with cosine distance."""
    if name in [c.name for c in client.list_collections()]:
        client.delete_collection(name)
    # metadata={"hnsw:space": "cosine"}: use cosine distance instead of Chroma's default L2.
    # embedding_function=None: we embed ourselves with NVIDIA, so Chroma must not use its own model.
    return client.create_collection(name, metadata={"hnsw:space": "cosine"}, embedding_function=None)


def list_models():
    for m in NVIDIAEmbeddings.get_available_models():
        print(m.id)


def main():
    load_dotenv(find_dotenv(usecwd=True))
    args = sys.argv[1:]
    if args == ["--list-models"]:
        list_models()
        return
    second_model = args[1] if len(args) == 2 and args[0] == "--second-model" else None

    emb = NVIDIAEmbeddings(model=MODEL, truncate="END")
    texts = [s for _, s in SENTENCES]
    topics = [t for t, _ in SENTENCES]
    ids = [f"s{n:02d}" for n in range(1, len(texts) + 1)]   # s01 ... s20

    # ---------------------------------------------------------------- 1
    header("1. PersistentClient and a collection with cosine distance")
    client = chromadb.PersistentClient(path=str(DB_PATH))
    col = fresh_collection(client, MAIN)
    print(f"Database folder: {DB_PATH}")
    print(f"Collection '{col.name}', id {col.id}, metadata {col.metadata}")

    # ---------------------------------------------------------------- 2
    header("2. Add the 20 sentences (passage mode) with ids and metadata")
    vectors = emb.embed_documents(texts)
    col.add(
        ids=ids,
        embeddings=vectors,
        documents=texts,
        metadatas=[{"topic": t} for t in topics],
    )
    print(f"Model {MODEL}, {len(vectors[0])} dimensions. count() = {col.count()}")

    # ---------------------------------------------------------------- 3
    header(f"3. Query: \"{QUESTION}\", k={K}")
    q = emb.embed_query(QUESTION)                # query mode, as learned on Day 1
    show(col.query(query_embeddings=[q], n_results=K))

    # ---------------------------------------------------------------- 4
    header("4. Same question, metadata filter: where={'topic': 'vpn'}")
    print("Only VPN sentences are searched, so the best VPN matches come back even though the question is about printers.")
    show(col.query(query_embeddings=[q], n_results=K, where={"topic": "vpn"}))

    # ---------------------------------------------------------------- 5
    header("5. Same question, document filter: where_document={'$contains': 'password'}")
    print("Only sentences whose TEXT contains 'password' are searched (an exact word match, not meaning).")
    show(col.query(query_embeddings=[q], n_results=K, where_document={"$contains": "password"}))

    # ---------------------------------------------------------------- 6
    header("6. Add a 21st sentence, query, update it, delete it, count, peek")
    new_text = "The printer went offline after the office Wi-Fi password was changed."
    col.add(ids=["s21"], embeddings=emb.embed_documents([new_text]), documents=[new_text], metadatas=[{"topic": "printer"}])
    print(f"Added s21. count() = {col.count()}")
    show(col.query(query_embeddings=[q], n_results=K), "Query again (does s21 make the top 3?):")

    updated = "Restart the printer and check its network cable if it shows offline."
    # Updating the text means the vector must be updated too. If you only changed `documents`,
    # Chroma would keep the OLD vector and search would still find the old meaning.
    col.update(ids=["s21"], documents=[updated], embeddings=emb.embed_documents([updated]))
    print(f"\nUpdated s21 -> {col.get(ids=['s21'])['documents'][0]}")
    show(col.query(query_embeddings=[q], n_results=K), "Query after the update:")

    col.delete(ids=["s21"])
    print(f"\nDeleted s21. count() = {col.count()}   get(ids=['s21']) -> {col.get(ids=['s21'])['ids']}")

    peek = col.peek(3)
    print("\npeek(3): the first 3 stored records")
    for i, doc, meta, vec in zip(peek["ids"], peek["documents"], peek["metadatas"], peek["embeddings"]):
        print(f"   {i} {meta} {doc}\n      vector: {len(vec)} numbers, starts {[round(float(x), 4) for x in vec[:4]]}")

    # ---------------------------------------------------------------- 7
    header("7. What Chroma wrote to disk")
    for root, _, files in os.walk(DB_PATH):
        for f in sorted(files):
            path = Path(root) / f
            print(f"   {path.relative_to(DB_PATH)}  {path.stat().st_size:,} bytes")
    print("\nchroma.sqlite3: a SQLite database with the collections, ids, documents and metadata.")
    print("Each long-id folder: one collection's vector index (HNSW), the structure that makes nearest-")
    print("neighbour search fast. The folder name is Chroma's internal id for that index, not the collection id.")
    print("data_level0.bin is where the vectors themselves are stored; it grows with count x dimensions.")

    # ---------------------------------------------------------------- 8
    header("8. A second embedding model, side by side")
    if not second_model:
        print("Skipped. Run with --second-model <model-id> (see --list-models).")
        return
    emb2 = NVIDIAEmbeddings(model=second_model, truncate="END")
    col2 = fresh_collection(client, SECOND)
    vectors2 = emb2.embed_documents(texts)
    col2.add(ids=ids, embeddings=vectors2, documents=texts, metadatas=[{"topic": t} for t in topics])
    q2 = emb2.embed_query(QUESTION)
    print(f"Model 1: {MODEL}  ->  {len(vectors[0])} dimensions")
    print(f"Model 2: {second_model}  ->  {len(vectors2[0])} dimensions\n")
    show(col.query(query_embeddings=[q], n_results=K), f"Top {K} with model 1 ({MAIN}):")
    show(col2.query(query_embeddings=[q2], n_results=K), f"\nTop {K} with model 2 ({SECOND}):")

    print("\nTrying to search the model 1 collection with a model 2 query vector:")
    try:
        col.query(query_embeddings=[q2], n_results=K)
        print("   It ran, but the result is meaningless: the two models' numbers do not mean the same things.")
    except Exception as error:
        print(f"   Refused: {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
