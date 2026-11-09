import json
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from chunk import load_and_chunk
from config import EMBED_MODEL

def build_indexes():
    chunks = load_and_chunk()
    texts = [c["text"] for c in chunks]

    # --- Dense index ---cl
    encoder = SentenceTransformer(EMBED_MODEL)
    # normalize_embeddings=True makes inner product equivalent to cosine similarity
    embeddings = encoder.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    embeddings = embeddings.astype(np.float32)
    index = faiss.IndexFlatIP(embeddings.shape[1])  # inner product on normalized vectors
    index.add(embeddings)
    faiss.write_index(index, "prototype/faiss.index")

    # --- Sparse (BM25) index ---
    tokenized = [t.lower().split() for t in texts]
    bm25 = BM25Okapi(tokenized)
    with open("prototype/bm25.pkl", "wb") as f:
        pickle.dump({"bm25": bm25, "chunks": chunks}, f)

    # Save chunks separately for easy lookup
    with open("prototype/chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"Indexed {len(chunks)} chunks.")

if __name__ == "__main__":
    build_indexes()