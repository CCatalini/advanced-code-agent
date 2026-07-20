# RAG — fuentes, chunking, embeddings, almacenamiento

## Fuentes

10 documentos markdown en [`rag_corpus/`](../rag_corpus/), escritos específicamente para este proyecto. 
Cubren exactamente lo que el caso de uso necesita para decidir bien:

1. `flask-routing-and-query-params.md`
2. `flask-sqlalchemy-models-and-columns.md`
3. `flask-sqlalchemy-migrations-vs-create-all.md` (el documento clave del caso de uso)
4. `flask-sqlalchemy-queries.md`
5. `flask-sqlalchemy-session-and-transactions.md`
6. `flask-instance-folder-and-config.md`
7. `flask-testing-with-test-client.md`
8. `flask-templates-and-jinja.md`
9. `flask-single-file-vs-app-factory.md`
10. `flask-tool-schema-design-notes.md`

## Estrategia de chunking

Por párrafo (split en `\n\n`), agrupando párrafos consecutivos hasta ~120 palabras por
chunk, con 1 párrafo de solapamiento entre chunks consecutivos para no cortar una idea a
la mitad (`agent/rag/ingest.py`, función `chunk_document`). Resultado real: **31 chunks**
a partir de los 10 documentos.

Se descartó chunking semántico (por embeddings de oraciones) o un tamaño fijo en
caracteres: con documentos cortos y ya temáticamente acotados, el chunking por párrafo da
buen recall sin la complejidad de una segunda pasada de modelo.

## Embeddings

[`sentence-transformers`](https://www.sbert.net/), modelo `all-MiniLM-L6-v2` (384
dimensiones), corrido localmente — sin API key ni costo de red. Se generan una sola vez
con `python agent/rag/ingest.py` y se normalizan (`normalize_embeddings=True`) para que la
similitud coseno se pueda calcular como un simple producto punto en el momento de la
consulta.

## Almacenamiento

Nada de Chroma/FAISS/pgvector: para 31 chunks, numpy + JSON alcanza y se explica en dos
frases.
- `agent/rag/store/chunks.json` — texto de cada chunk + metadata (documento de origen).
- `agent/rag/store/embeddings.npy` — matriz numpy (31 × 384), un vector por chunk, en el
  mismo orden que `chunks.json`.

## Retrieval

`agent/rag/retrieve.py`, función `retrieve(query, k=4)`: embebe la query con el mismo
modelo, calcula similitud coseno contra toda la matriz (`embeddings @ query_embedding`),
devuelve el top-k con `(texto, fuente, score)`. `RELEVANCE_THRESHOLD = 0.35`
(`has_relevant_evidence`) es el umbral que usa el Researcher para decidir si cae a
`web_search` en vez de confiar en el RAG.

## Verificación

Query de prueba: *"How do I add a new column to a Flask-SQLAlchemy model when the database
already exists and there are no migrations?"* → top-3 resultados con scores 0.730, 0.722,
0.687, los tres genuinamente relevantes (`flask-tool-schema-design-notes.md` y
`flask-sqlalchemy-models-and-columns.md`). Ver la corrida completa del Researcher citando
estas fuentes en `docs/EVIDENCE.md`.

## Tests automáticos (sin costo de API)

[`agent/tests/test_rag_retrieve.py`](../agent/tests/test_rag_retrieve.py) ejercita
`retrieve()` contra el índice real con el modelo de embeddings local — verifica que la
query de schema drift trae `flask-sqlalchemy-migrations-vs-create-all.md`, que la de
filtros trae `flask-sqlalchemy-queries.md`, y que los scores vienen ordenados
descendente. Como los embeddings son locales, correr `pytest agent/tests/` no gasta nada
de crédito de Anthropic — es la forma de re-verificar la calidad del retrieval las veces
que haga falta sin preocuparse por el costo.

## Cómo diferenciar fuentes en las respuestas

Cada resultado de `rag_search` se etiqueta `[RAG: <archivo> | score=...]` antes de
devolverse (`agent/tools.py`, función `rag_search`). El system prompt del Researcher
(`agent/subagents/researcher.py`) exige explícitamente etiquetar cada afirmación de su
respuesta final como `[RAG: ...]`, `[WEB: <url>]` o `[INFERENCE]` — nunca presentar una
inferencia propia como si fuera un hecho documentado.
