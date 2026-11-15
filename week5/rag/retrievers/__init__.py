"""One file per retrieval technique. Every retriever is a function: retrieve(question, k) -> list of chunks,
each chunk {"id", "text", "metadata", ...}, best first."""
