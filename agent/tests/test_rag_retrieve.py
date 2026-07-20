"""Tests del pipeline de retrieval del RAG. Usa el índice real (rag/store/) y el modelo
de embeddings LOCAL (sentence-transformers) — no llama a la API de Anthropic en ningún
momento, así que se puede correr sin gastar crédito."""
from rag.retrieve import retrieve, has_relevant_evidence


def test_retrieve_returns_k_results():
    results = retrieve("how do I add a column to an existing SQLAlchemy model", k=3)
    assert len(results) == 3
    assert all({"text", "source", "score"} <= result.keys() for result in results)


def test_retrieve_surfaces_the_migrations_doc_for_schema_drift_query():
    results = retrieve(
        "the database already exists and create_all() won't add my new column, what do I do",
        k=3,
    )
    sources = [r["source"] for r in results]
    assert "flask-sqlalchemy-migrations-vs-create-all.md" in sources


def test_retrieve_surfaces_query_docs_for_filtering_question():
    results = retrieve("how do I filter and sort a Flask-SQLAlchemy query by a column", k=3)
    sources = [r["source"] for r in results]
    assert "flask-sqlalchemy-queries.md" in sources


def test_has_relevant_evidence_true_for_on_topic_query():
    results = retrieve("Flask-SQLAlchemy db.session commit and rollback", k=4)
    assert has_relevant_evidence(results) is True


def test_has_relevant_evidence_false_for_empty_results():
    assert has_relevant_evidence([]) is False


def test_scores_are_sorted_descending():
    results = retrieve("Jinja templates and render_template", k=5)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
