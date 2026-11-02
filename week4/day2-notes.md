# Day 2 notes

Run:

```
python day2_chroma.py --second-model nvidia/nemotron-3-embed-1b
```

## What is a collection?

A collection is saved in the chromaDB in a table thats a group of records that has id, embedding(vector), and metadata.

## What are ids and metadata for?

IDs are there so that you can identify it and update/delete the record easily.

Metadata is for filtering a search, like for topic: vpn. This makes it easy to know where the result is from and to identify it in within chunks.

## What happens on disk?

Chroma writes chroma.sqlite3 and uses HNSW vector index to find nearest vector indexes which is saved in the collection. All of this data is stored in the disk so we dont have to worry about losing the data with crashes, and easy to retrieve that info.

## Why cant you mix embedding models inside one collection?

Each model has its own space of meaning, a collection and the queries against it must use one model. changing models means re-embedding everthing. every vector has to be the same size (2048 example) so mixing models doesnt work.
