import copy
import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_PATH = os.path.join(BASE_DIR, "..", "memory", "project_memory.json")

DEFAULT_MEMORY = {
    "architecture": "",
    "important_files": [],
    "dependencies": [],
    "useful_commands": [],
    "conventions": [],
    "decisions": [],
    "investigated_bugs": [],
    "session_summaries": [],
}


def load_memory():
    """Lee la memoria persistente del proyecto (sobrevive entre conversaciones).
    Siempre deep-copia DEFAULT_MEMORY: como sus valores son listas mutables, una copia
    superficial dejaría que mutar el resultado (ej. memory["decisions"].append(...))
    contamine el diccionario global entre llamadas dentro del mismo proceso."""
    if not os.path.exists(MEMORY_PATH):
        return copy.deepcopy(DEFAULT_MEMORY)
    with open(MEMORY_PATH) as f:
        data = json.load(f)
    return {**copy.deepcopy(DEFAULT_MEMORY), **data}


def save_memory(memory):
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    with open(MEMORY_PATH, "w") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


def compact_summary(memory, max_items=5):
    """Resumen corto para inyectar en el system prompt — nunca el JSON completo."""
    lines = []
    if memory["architecture"]:
        lines.append(f"Architecture: {memory['architecture']}")
    if memory["conventions"]:
        lines.append("Conventions: " + "; ".join(memory["conventions"][-max_items:]))
    if memory["decisions"]:
        lines.append("Past decisions: " + "; ".join(memory["decisions"][-max_items:]))
    if memory["session_summaries"]:
        lines.append("Last session: " + memory["session_summaries"][-1]["summary"])
    return "\n".join(lines) if lines else "No previous memory recorded for this project."


def record_from_task(memory, task_state):
    """muestra en el cierre de la sesión lo que se aprendió en esta tarea puntual."""
    if task_state.files_modified:
        memory["decisions"].append(
            f"{task_state.started_at}: modified {', '.join(task_state.files_modified)} "
            f"to address '{task_state.original_request}'"
        )
    subagents_used = ", ".join(task_state.subagent_results.keys()) or "none"
    memory["session_summaries"].append({
        "date": datetime.now(timezone.utc).isoformat(),
        "summary": f"Request: {task_state.original_request}. Subagents used: {subagents_used}.",
    })
