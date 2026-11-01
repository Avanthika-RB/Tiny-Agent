"""Day 1: what is an embedding. No pipeline yet.

    python day1_embeddings.py                          use the main embedding model
    python day1_embeddings.py --model nvidia/nv-embedqa-e5-v5   use the fallback model

What it does:
  1. Embeds 20 short sentences (4 topics x 5) with embed_documents (passage mode).
  2. Prints the vector length (the number of dimensions).
  3. Computes cosine similarity between every pair and prints the 20 x 20 matrix,
     plus a 4 x 4 summary of the average similarity between topics.
  4. Embeds one question with embed_query (query mode) and ranks the 20 sentences.
  5. Does it WRONG on purpose: embeds the question with embed_documents (passage
     mode) and ranks again. Prints both rankings side by side.
"""

import sys

import numpy as np
from dotenv import find_dotenv, load_dotenv
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

MODEL = "nvidia/nemotron-3.5-embed-1b"
QUESTION = "how do I fix a printer that is offline"

# 20 sentences: 5 per topic.
SENTENCES = [
    ("printer", "The office printer shows offline even though it is switched on."),
    ("printer", "Paper keeps jamming in tray two of the printer."),
    ("printer", "Reinstalling the printer driver fixed the blank pages."),
    ("printer", "You must add the network printer by its IP address."),
    ("printer", "Low toner makes printed pages look faded and streaky."),
    ("password", "My password expired and I cannot log in this morning."),
    ("password", "Passwords must be at least twelve characters long."),
    ("password", "Use the self-service portal to reset a forgotten password."),
    ("password", "After five wrong attempts the account gets locked."),
    ("password", "Never share your password with anyone, even IT staff."),
    ("vpn", "The VPN disconnects every few minutes when I work from home."),
    ("vpn", "You need the VPN to reach internal sites from outside the office."),
    ("vpn", "Update the VPN client if the connection keeps failing."),
    ("vpn", "Multi-factor approval is required each time the VPN connects."),
    ("vpn", "Split tunnelling sends only company traffic through the VPN."),
    ("random", "It is going to rain all weekend in Seattle."),
    ("random", "The football match went to a penalty shootout."),
    ("random", "Add a pinch of salt before the pasta water boils."),
    ("random", "My cat sleeps on the windowsill every afternoon."),
    ("random", "The new bakery downtown sells excellent croissants."),
]
TOPICS = ["printer", "password", "vpn", "random"]


def cosine_matrix(vectors):
    """Cosine similarity between every pair of rows.

    cosine(a, b) = (a . b) / (|a| * |b|). Dividing each row by its length first
    makes every vector length 1, so a plain dot product IS the cosine.
    """
    v = np.array(vectors)
    unit = v / np.linalg.norm(v, axis=1, keepdims=True)
    return unit @ unit.T


def cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def print_matrix(matrix, labels):
    print("       " + "".join(f"{i:>6}" for i in range(len(labels))))
    for i, row in enumerate(matrix):
        print(f"{i:>2} {labels[i][:3]:<4}" + "".join(f"{x:6.2f}" for x in row))


def print_topic_summary(matrix, topics_of_rows):
    """Average similarity between every pair of topics (diagonal excluded)."""
    print(f"{'':>10}" + "".join(f"{t:>10}" for t in TOPICS))
    for t1 in TOPICS:
        cells = []
        for t2 in TOPICS:
            values = [
                matrix[i][j]
                for i, a in enumerate(topics_of_rows)
                for j, b in enumerate(topics_of_rows)
                if a == t1 and b == t2 and i != j
            ]
            cells.append(f"{np.mean(values):10.3f}")
        print(f"{t1:>10}" + "".join(cells))


def rank(question_vector, sentence_vectors):
    scores = [cosine(question_vector, v) for v in sentence_vectors]
    return sorted(range(len(scores)), key=lambda i: scores[i], reverse=True), scores


def main():
    model = MODEL
    if len(sys.argv) == 3 and sys.argv[1] == "--model":
        model = sys.argv[2]

    load_dotenv(find_dotenv(usecwd=True))   # finds the .env in Tiny-Agent, above this folder
    emb = NVIDIAEmbeddings(model=model, truncate="END")
    print(f"Embedding model: {model}\n")

    texts = [s for _, s in SENTENCES]
    topics_of_rows = [t for t, _ in SENTENCES]

    # 1-2. Passage mode for the sentences we are storing.
    vectors = emb.embed_documents(texts)
    print(f"Embedded {len(vectors)} sentences. Vector length (dimensions): {len(vectors[0])}")
    print(f"First 5 numbers of sentence 0: {[round(float(x), 4) for x in vectors[0][:5]]}\n")

    # 3. Similarity matrix.
    matrix = cosine_matrix(vectors)
    print("=== Cosine similarity, 20 x 20 (rows/columns 0-4 printer, 5-9 password, 10-14 vpn, 15-19 random) ===")
    print_matrix(matrix, topics_of_rows)
    print("\n=== Average similarity between topics (the four blocks) ===")
    print_topic_summary(matrix, topics_of_rows)

    # 4. The right way: the question in QUERY mode.
    q_query = emb.embed_query(QUESTION)
    right_order, right_scores = rank(q_query, vectors)

    # 5. The wrong way: the question in PASSAGE mode, as if it were a document.
    q_passage = emb.embed_documents([QUESTION])[0]
    wrong_order, wrong_scores = rank(q_passage, vectors)

    print(f"\n=== Ranking for: \"{QUESTION}\" ===")
    print(f"{'#':>2}  {'RIGHT: embed_query (query mode)':<58} {'WRONG: embed_documents (passage mode)':<58}")
    for place in range(len(texts)):
        r, w = right_order[place], wrong_order[place]
        left = f"{right_scores[r]:.3f} [{topics_of_rows[r][:3]}] {texts[r][:42]}"
        right = f"{wrong_scores[w]:.3f} [{topics_of_rows[w][:3]}] {texts[w][:42]}"
        print(f"{place + 1:>2}  {left:<58} {right:<58}")

    print(f"\nQuery vs passage embedding of the SAME question, cosine: {cosine(q_query, q_passage):.3f}")
    top5_right = sum(topics_of_rows[i] == "printer" for i in right_order[:5])
    top5_wrong = sum(topics_of_rows[i] == "printer" for i in wrong_order[:5])
    print(f"Printer sentences in the top 5: query mode {top5_right}/5, passage mode {top5_wrong}/5")


if __name__ == "__main__":
    main()
