import json
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from config import EMBED_MODEL, TOP_K

# Load everything once at import time
_encoder = SentenceTransformer(EMBED_MODEL)
_index = faiss.read_index("prototype/faiss.index")
with open("prototype/bm25.pkl", "rb") as f:
    _bm25_data = pickle.load(f)
_bm25 = _bm25_data["bm25"]
_chunks = _bm25_data["chunks"]

def rrf(rank_lists, k=60):
    """rank_lists: list of lists of chunk indices, ordered best-first."""
    scores = {}
    for ranks in rank_lists:
        for pos, idx in enumerate(ranks, start=1):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + pos)
    return sorted(scores.items(), key=lambda x: -x[1])

def retrieve(query: str, top_k: int = TOP_K, dense_k: int = 50, sparse_k: int = 50):
    # Dense retrieval
    qv = _encoder.encode([query], normalize_embeddings=True).astype(np.float32)
    _, dense_idx = _index.search(qv, dense_k)
    dense_ranks = [int(i) for i in dense_idx[0] if i != -1]

    # Sparse retrieval
    tokens = query.lower().split()
    sparse_idx = _bm25.get_top_n(tokens, list(range(len(_chunks))), n=sparse_k)
    sparse_ranks = [int(i) for i in sparse_idx]

    # Fuse
    fused = rrf([dense_ranks, sparse_ranks])
    results = []
    for idx, score in fused[:top_k]:
        chunk = _chunks[idx].copy()
        chunk["rrf_score"] = score
        results.append(chunk)
    return results

if __name__ == "__main__":
    q = "What should I do when I don't understand everything while immersing?"
    for r in retrieve(q):
        print(f"[{r['rrf_score']:.4f}] {r['title']} — {r['text'][:120]}...")