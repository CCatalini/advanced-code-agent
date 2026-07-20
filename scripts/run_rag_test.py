"""Test 1 del plan: le pide al Researcher que resuelva el problema de schema drift
(agregar columnas a un modelo Flask-SQLAlchemy sobre una DB ya creada, sin migraciones),
y muestra las fuentes RAG citadas. Requiere crédito de Anthropic disponible.

Uso: desde agent/, con el venv activado:
    python ../scripts/run_rag_test.py
"""
import os
import sys

AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent")
sys.path.insert(0, AGENT_DIR)

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(AGENT_DIR, "..", ".env"))

from state import TaskState
from orchestrator import call_subagent

QUERY_TASK = (
    "We need to add priority and due_date columns to an existing Flask-SQLAlchemy Todo "
    "model, and a route to filter/sort by them. The app already has a real SQLite "
    "database created once via a script that calls db.create_all(), with no migrations "
    "tool installed. Find out what we need to know before making this change safely."
)


def main():
    task_state = TaskState(original_request="Test 1 — RAG sourcing demo")
    modes = {"plan_mode": False, "supervision_on": False}

    result = call_subagent("Researcher", QUERY_TASK, task_state, modes)

    print("\n================= RESEARCHER ANSWER =================\n")
    print(result)
    print("\n================= SOURCES RECORDED IN TaskState =================\n")
    print(task_state.sources)


if __name__ == "__main__":
    main()
