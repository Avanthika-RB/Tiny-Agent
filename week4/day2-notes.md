Day 2: What is a vector database. Chroma by hand.
• chromadb.PersistentClient. Create a collection with cosine space. Add the 20 sentences with
ids and metadata (topic). Query with the printer question, k=3.
• Query with a metadata filter: only topic=vpn. Query with a where_document contains filter.
• Add a 21st sentence. Query again. Update it. Delete it. Count. Peek. Look at the chroma_db
folder on disk and see what Chroma actually wrote.
• Create a second collection using the fallback embedding model. Same 20 sentences, same
question. Compare the top 3. Note the vector lengths differ.
Concepts: Vector store, collection, ids, metadata, distance metric, upsert, filtering, persistence.
Notes to write: day2-notes.md: what a collection is, what ids and metadata are for, what happens on
disk, why you cannot mix embedding models inside one collection.


python day2_chroma.py --second-model nvidia/nemotron-3-embed-1b

What is a collection?
A collection is saved in the chromaDB in a table thats a group of records that has id, embedding(vector), and metadata.

What are ids and metadata for?
IDs are there so that you can identify it and update/delete the record easily. 
Metadata is for filtering a search, like for topic: vpn. This makes it easy to know where the result is from and to identify it in within chunks. 

What happens on disk?
Chroma writes chroma.sqlite3 and uses HNSW vector index to find nearest vector indexes which is saved in the collection. All of this data is stored in the disk so we dont have to worry about losing the data with crashes, and easy to retrieve that info. 

Why cant you mix embedding models inside one collection?
Each model has its own space of meaning, a collection and the queries against it must use one model. changing models means re-embedding everthing. every vector has to be the same size (2048 example) so mixing models doesnt work. 
