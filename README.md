# Coding Agent Avanzado

Sistema multiagente de coding assistant: un agente principal que coordina 5 subagentes
especializados (Explorer, Researcher, Implementer, Tester, Reviewer), con RAG propio,
memoria persistente de proyecto, políticas de seguridad configurables y observabilidad —
sin frameworks de orquestación (LangChain/LangGraph/CrewAI/AutoGen).

Documentación completa en [`docs/`](docs/):
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura y estado compartido.
- [`docs/RAG.md`](docs/RAG.md) — fuentes, chunking, embeddings, almacenamiento.
- [`docs/USE_CASE.md`](docs/USE_CASE.md) — caso de uso y criterio de éxito.
- [`docs/EVIDENCE.md`](docs/EVIDENCE.md) — tareas ejecutadas y qué se observa.
- [`docs/REFLECTION.md`](docs/REFLECTION.md) — qué funcionó, qué falló, mejoras.

## Instalación

Requiere Python 3.9+.

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install anthropic python-dotenv tavily-python pyyaml numpy sentence-transformers pytest langfuse
```

## Configuración

1. Copiá `.env.example` a `.env` y completá:
   ```
   ANTHROPIC_API_KEY=...
   ANTHROPIC_MODEL=claude-sonnet-5
   TAVILY_API_KEY=...
   # Opcionales — sin esto, la observabilidad sigue funcionando en modo local (ver abajo)
   LANGFUSE_PUBLIC_KEY=...
   LANGFUSE_SECRET_KEY=...
   ```
2. Cloná el proyecto sobre el que va a trabajar el agente (el "caso de uso") en cualquier
   carpeta, y apuntá `workspace:` en [`agent.config.yaml`](agent.config.yaml) a esa carpeta
   (relativo a la raíz de este repo). Por default apunta a `../flask-class`.
3. (Solo una vez, o cuando cambie `rag_corpus/`) generá el índice del RAG:
   ```bash
   cd agent
   python rag/ingest.py
   ```

## Ejecución

Modo conversación interactivo:
```bash
cd agent
python main_agent.py
```
Te va a preguntar si querés activar **plan mode** (el agente propone un plan y espera tu
aprobación antes de tocar nada) y **supervisión** (te pide confirmar cada acción que no sea
de solo lectura). Podés escribir `off` en cualquier momento para desactivar ambos.

Scripts de demostración (no interactivos, pensados para las pruebas del TP):
```bash
python scripts/run_feature_task.py     # Test 4: caso de uso completo (usa la API)
python scripts/run_reviewer_only.py    # Termina el Test 4 sin rehacer los otros 4 subagentes (usa la API)
python scripts/run_rag_test.py         # Test 1: RAG con citas de fuentes (usa la API)
python scripts/run_memory_test.py      # Test 2: memoria persistente entre sesiones (usa la API)
python scripts/run_loop_guard_test.py  # Test 3: detección de loops (NO usa la API)
```

## Tests locales (no usan la API de Anthropic)

`agent/tests/` tiene 43 tests de `pytest` sobre `policy.py`, `state.py`, `memory.py`,
`context.py`, `execution.py` y `rag/retrieve.py` — ninguno llama a `messages.create` (el
retrieval del RAG corre 100% local con `sentence-transformers`, y las llamadas al modelo
en `context.py` se reemplazan por un stub). Se pueden correr todas las veces que haga
falta sin gastar crédito:
```bash
cd agent
python -m pytest tests/ -v
```

## Políticas del agente

Ver [`agent.config.yaml`](agent.config.yaml): qué no se puede leer/escribir, qué comandos
están prohibidos, y cuáles requieren aprobación manual. Se valida antes de cada tool call
en `agent/policy.py` + `agent/execution.py`.

## Observabilidad

Si `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` no están configuradas, el sistema sigue
funcionando normalmente y deja un log local en `logs/observability.jsonl` (modelo, tokens,
latencia, costo estimado por cada llamada al LLM). Con las keys configuradas (cuenta
gratuita en [cloud.langfuse.com](https://cloud.langfuse.com)), además se envían trazas
completas a la UI de Langfuse.
