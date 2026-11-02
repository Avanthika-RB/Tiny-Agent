Day 7 Reflection
– Explain chunking to someone who has never heard of it, in five sentences.
Chunking is breaking down a large document like pdfs into smaller pieces of text. Then turn it into vector embeddings and with these embeddings, we can find the similarities between words. Its turned into numbers that have meaning. Cutting the chunks is important because it can get a better or more correct answer if the chunk is broken up differently, which is why in this project it tests different methods like fixed_200 and markdown headers.
– What question would you ask about a new document set before choosing a chunking strategy?
I would ask the size needed and if its okay to split into small chunks, or if a chunk that splits the list fails, or if it needs a markdown. Ask for its limitations. 
– Your pipeline ran three times and changed nothing the last two. Why does that matter in production?
It matters in production because its cheap to run if its already saved with chromaDB. Its very fast and doesnt have to take time to run again, because there's no need to re-embed if nothing has changed. 
– What is still confusing?
Im still learning these new topics on RAG, its tough to be confident about all the details in the code but with time I will be more confident in any questions asked in this field. Im still unsure about all the details on hashing and manifest deciding what to add, update, delete. 

Concept checklist
Rate each 1 to 3. 1 = heard of it. 2 = used it but shaky. 3 = can explain without notes and point to the
code.
☐ 2 Embedding, dimension, cosine similarity
☐ 2 Query vs passage embedding modes
☐ 2 Vector store, collection, ids, metadata, distance metric
☐ 2 Persistence: what Chroma writes to disk
☐ 2 Document loaders for markdown, HTML, text, PDF
☐ 2 Text cleaning and normalisation
☐ 2 Fixed-size splitting and overlap
☐ 2 Recursive character splitting
☐ 2 Header-aware splitting and header metadata
☐ 2 Prefixing context into chunk text
☐ 2 Semantic chunking and its cost
☐ 2 Chunk metadata design
☐ 1 Content hashing and deduplication
☐ 1 Manifest and change detection
☐ 2 Incremental ingestion, deletions, idempotency
☐ 2 Batching and backoff against API limits
☐ 2 hit@k and building an evaluation set
☐ 2 Predicting before measuring