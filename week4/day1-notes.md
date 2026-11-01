run python day1_embeddings.py  

Day 1: What is an embedding. No pipeline yet.
• Set up: venv, requirements.txt with pinned versions, NVIDIA_API_KEY in .env.
• Write 20 short sentences: 5 about printers, 5 about passwords, 5 about VPN, 5 random
(weather, football, recipes). Embed them with NVIDIAEmbeddings.embed_documents.
• Print the vector length. Compute cosine similarity between every pair with numpy. Print the 20
by 20 matrix. The four topic blocks should be visible.
• Embed one question (&quot;how do I fix a printer that is offline&quot;) with embed_query and rank the 20
sentences. Then do it WRONG on purpose: embed the question with embed_documents
(passage mode). Compare the rankings. This is why input_type matters.
Concepts: Embedding, dimension, cosine similarity, query vs passage embeddings, embedding model.
Notes to write: day1-notes.md: what is a dimension, what does cosine similarity measure, why is the
same text embedded two different ways.

What is a dimension?
It says we embedded 20 sentences with vector length (dimension) at 2048. Dimension is the vector length where every sentence became a list of 2048 numbers where each is a coordinate in 2048-dimensional space, 1 number doesnt have much meaning but shows the similarity between different points in that space. 

What does cosine similarity measure?
It measures how close the vectors point in a direction, measures similarity between the text by making arrows/angles between each point. 

Then we rank by seeing which sentences score higher than others for the same question

Why is the same text embedded two different ways?
There is query and passage, 2 different ways or modes used. This is because model uses query mode for questions and passage mode for stored text. This puts the questions near answers so that search can return the closest stored text to the questions vector. 
