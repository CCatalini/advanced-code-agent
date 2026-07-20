"""Script de ingesta del RAG: chunking + embeddings + guardado en disco.
Se corre una sola vez (o cada vez que cambie rag_corpus/): python rag/ingest.py
"""
import glob
import json
import os

import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.join(BASE_DIR, "..", "..", "rag_corpus")
STORE_DIR = os.path.join(BASE_DIR, "store")
CHUNKS_PATH = os.path.join(STORE_DIR, "chunks.json")
EMBEDDINGS_PATH = os.path.join(STORE_DIR, "embeddings.npy")

MODEL_NAME = "all-MiniLM-L6-v2"
MAX_WORDS_PER_CHUNK = 120
OVERLAP_PARAGRAPHS = 1


def chunk_document(text, source):
    """Chunking simple por párrafos, agrupando hasta ~MAX_WORDS_PER_CHUNK palabras,
    con 1 párrafo de solapamiento entre chunks consecutivos."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = []
    current_words = 0

    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]
        para_words = len(para.split())
        if current_words + para_words > MAX_WORDS_PER_CHUNK and current:
            chunks.append("\n\n".join(current))
            # solapamiento: retrocedemos OVERLAP_PARAGRAPHS párrafos
            overlap_start = max(0, len(current) - OVERLAP_PARAGRAPHS)
            current = current[overlap_start:]
            current_words = sum(len(p.split()) for p in current)
        current.append(para)
        current_words += para_words
        i += 1

    if current:
        chunks.append("\n\n".join(current))

    return [{"text": c, "source": source} for c in chunks]


def build_corpus():
    all_chunks = []
    for path in sorted(glob.glob(os.path.join(CORPUS_DIR, "*.md"))):
        source = os.path.basename(path)
        with open(path) as f:
            text = f.read()
        all_chunks.extend(chunk_document(text, source))
    return all_chunks


def main():
    print(f"Cargando modelo de embeddings '{MODEL_NAME}'...")
    model = SentenceTransformer(MODEL_NAME)

    chunks = build_corpus()
    print(f"{len(chunks)} chunks generados a partir de {len(set(c['source'] for c in chunks))} documentos.")

    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    os.makedirs(STORE_DIR, exist_ok=True)
    with open(CHUNKS_PATH, "w") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    np.save(EMBEDDINGS_PATH, np.array(embeddings, dtype=np.float32))

    print(f"Guardado: {CHUNKS_PATH}")
    print(f"Guardado: {EMBEDDINGS_PATH} shape={embeddings.shape}")


if __name__ == "__main__":
    main()
