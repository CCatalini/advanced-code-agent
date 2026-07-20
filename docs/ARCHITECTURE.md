# Arquitectura

## Vista general

```
                    ┌─────────────────────┐
   usuario ───────► │  main_agent.py      │  (agente principal)
                    │  conversation_mode()│
                    │  run_task()         │
                    └─────────┬───────────┘
                              │ tool: call_subagent(role, task)
                              ▼
                    ┌─────────────────────┐
                    │  orchestrator.py    │
                    │  call_subagent()    │──► loop de messages.create propio,
                    └─────────┬───────────┘    system prompt y tools propias del rol
                              │
        ┌───────────┬─────────┼─────────┬────────────┐
        ▼           ▼         ▼         ▼            ▼
    Explorer   Researcher  Implementer  Tester    Reviewer
   (solo lee)  (rag+web)  (lee+escribe) (+run_cmd) (solo lee)

Todos comparten:
  - state.py     -> TaskState (pizarrón de la tarea en curso)
  - memory.py    -> project_memory.json (memoria entre sesiones)
  - execution.py -> execute_tool() (permisos, políticas, detección de loops)
  - policy.py    -> agent.config.yaml (qué se puede leer/escribir/correr)
  - observability.py -> Langfuse + log local
```

Sin frameworks de orquestación (LangChain/LangGraph/CrewAI/AutoGen): la coordinación es
control de flujo Python puro. Un subagente **es** una función que corre su propio loop de
`messages.create`, invocada por el agente principal a través de una tool más
(`call_subagent`) — el mismo mecanismo, aplicado recursivamente, que el plan mode ya usaba
en el TP de clase para pausar y esperar aprobación.

## Rol del agente principal — `agent/main_agent.py`

Recibe el pedido del usuario (`conversation_mode`), crea un `TaskState` nuevo por pedido,
corre el loop interno (`run_task`) hasta que el modelo devuelve texto final, y decide en
cada iteración si resuelve algo con sus propias tools (`read_file`, `write_file`,
`run_command`, `list_files`, `web_search`) o si delega en un subagente vía `call_subagent`.
Al cerrar cada turno: guarda el `TaskState` a disco, actualiza la memoria persistente del
proyecto, y resume la conversación externa si se volvió demasiado larga.

## Rol de cada subagente

| Subagente | Responsabilidad | Tools | Puede escribir código |
|---|---|---|---|
| **Explorer** | Entender el repo: estructura, modelo de datos, rutas, convenciones | `list_files`, `read_file` | No |
| **Researcher** | Buscar en el RAG (y, si no alcanza, en la web) la información para decidir bien | `rag_search`, `web_search` | No |
| **Implementer** | Aplicar los cambios de código concretos, a partir de lo que ya investigaron Explorer/Researcher | `read_file`, `write_file`, `list_files` | Sí |
| **Tester** | Validar el resultado — correr tests, o escribirlos si no existen | `read_file`, `write_file`, `run_command`, `list_files` | Sí (solo tests) |
| **Reviewer** | Revisar el diff contra el pedido original | `read_file`, `list_files` | No |

Cada uno tiene su propio system prompt (`agent/subagents/<rol>.py`) que además de describir
la responsabilidad, marca explícitamente sus límites (ej. Reviewer nunca modifica nada,
Researcher tiene que citar de dónde sale cada afirmación).

## Estructura del estado compartido

**`TaskState`** (`agent/state.py`, vive una tarea, se persiste en
`logs/runs/advanced-coding-agent/<timestamp>.json`):

```python
original_request: str          # el pedido del usuario, tal cual
plan: list                     # (reservado para planes explícitos)
progress: list                 # pasos completados, con quién los hizo
subagent_results: dict         # {"Explorer": [...], "Researcher": [...], ...}
sources: dict                  # {"rag": [...], "web": [...], "repo": [...], "memory": [...]}
files_modified: list           # paths tocados con write_file
observations: list             # notas de loops detectados, falta de evidencia, etc.
tool_call_log: list            # huella de llamadas, usada por el detector de loops
```

**`project_memory.json`** (`agent/memory.py`, vive para siempre, en `memory/`):
arquitectura detectada, archivos importantes, dependencias, comandos útiles, convenciones,
decisiones tomadas, bugs investigados, resúmenes de sesiones previas. Se inyecta en el
system prompt del agente principal como un resumen compacto (`compact_summary()`), nunca
como el JSON completo.

## Políticas de seguridad

`agent.config.yaml` + `agent/policy.py`: definen qué no se puede leer/escribir y qué
comandos están prohibidos o requieren aprobación. Se validan en `execution.py`, en el único
punto por el que pasan **todas** las tool calls (del agente principal y de los 5
subagentes) — no hay forma de saltearse la política llamando a una tool "por otro lado".
