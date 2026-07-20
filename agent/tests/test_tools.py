"""Tests de tools.py que no requieren ninguna API externa: resolución de WORKSPACE desde
la config, y el formato de salida de rag_search (que sí usa el modelo local de
embeddings, pero no la API de Anthropic ni la web)."""
import os

import tools


def test_workspace_resolves_to_an_existing_directory():
    assert os.path.isdir(tools.WORKSPACE)


def test_list_files_reads_from_the_configured_workspace():
    listing = tools.list_files(".")
    assert "app.py" in listing


def test_rag_search_tags_each_result_with_its_source_and_score():
    output = tools.rag_search("how do I filter a Flask-SQLAlchemy query", k=2)
    assert output.count("[RAG:") == 2
    assert "score=" in output
