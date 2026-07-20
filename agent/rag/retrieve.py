import json
import os

import numpy as np
from sentence_transformers import SentenceTransformer

import observability

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORE_DIR = os.path.join(BASE_DIR, "store")
CHUNKS_PATH = os.path.join(STORE_DIR, "chunks.json")
EMBEDDINGS_PATH = os.path.join(STORE_DIR, "embeddings.npy")

MODEL_NAME = "all-MiniLM-L6-v2"
RELEVANCE_THRESHOLD = 0.35

_model = None
_chunks = None
_embeddings = None


def _load():
    global _model, _chunks, _embeddings
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    if _chunks is None or _embeddings is None:
        if not os.path.exists(CHUNKS_PATH) or not os.path.exists(EMBEDDINGS_PATH):
            raise FileNotFoundError(
                "RAG index not found. Run `python rag/ingest.py` once before using rag_search."
            )
        with open(CHUNKS_PATH) as f:
            _chunks = json.load(f)
        _embeddings = np.load(EMBEDDINGS_PATH)


def retrieve(query, k=4):
    """Devuelve hasta k chunks (texto, fuente, score) ordenados por similitud coseno.
    Como los embeddings ya están normalizados, el producto punto ES la similitud coseno."""
    with observability.span("rag_retrieve", query=query, k=k) as s:
        _load()
        query_embedding = _model.encode([query], normalize_embeddings=True)[0]
        scores = _embeddings @ query_embedding
        top_indices = np.argsort(-scores)[:k]
        results = [
            {"text": _chunks[i]["text"], "source": _chunks[i]["source"], "score": float(scores[i])}
            for i in top_indices
        ]
        if s is not None:
            s.update(output={"sources": [r["source"] for r in results], "scores": [r["score"] for r in results]})
        return results


def has_relevant_evidence(results):
    return bool(results) and results[0]["score"] >= RELEVANCE_THRESHOLD
