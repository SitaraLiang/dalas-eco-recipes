import pickle
import faiss
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"

def test_vectors():
    vectors = pickle.load(open(DATA_DIR / "text_vectors.pkl", "rb"))
    dim = vectors.shape[1]
    print("Text vectors shape:", vectors.shape)

    assert dim == 384, "Hybrid dim mismatch! Should be 384."
    print("vector dimension OK")

    # test normalization
    norms = np.linalg.norm(vectors, axis=1)
    print("Avg norm:", norms.mean())
    assert abs(norms.mean() - 1.0) < 1e-3
    print("FAISS-ready normalization OK")

def test_faiss_retrieval():
    index = faiss.read_index(str(DATA_DIR / "recipes_faiss.index"))
    vectors = pickle.load(open(DATA_DIR / "text_vectors.pkl", "rb"))

    query = vectors[0:1]
    D, I = index.search(query, 5)

    print("Top-5 neighbors:", I[0])
    print("Scores:", D[0])

    assert I[0][0] == 0, "Nearest neighbor should be itself."
    print("FAISS retrieval OK")

if __name__ == "__main__":
    test_vectors()
    test_faiss_retrieval()
