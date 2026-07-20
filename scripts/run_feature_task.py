"""Test 4 del plan: corre el pedido real de agregar prioridad/fecha de vencimiento +
filtro a flask-class a través del pipeline completo (agente principal delegando en
Explorer, Researcher, Implementer, Tester y Reviewer).

Requiere crédito disponible en la cuenta de Anthropic asociada a ANTHROPIC_API_KEY (.env).

Uso: desde la carpeta agent/, con el venv activado:
    python ../scripts/run_feature_task.py
"""
import os
import sys

AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent")
sys.path.insert(0, AGENT_DIR)

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(AGENT_DIR, "..", ".env"))

from state import TaskState
import main_agent
import memory

REQUEST = (
    "Add 'priority' (integer, default 0) and 'due_date' (optional datetime) fields to the "
    "Todo model in this Flask app, plus a way to filter and sort the task list by priority "
    "and completion status via query parameters on the index route. The app already has a "
    "real SQLite database created once via init_db.py, and there is no migrations tool "
    "installed. There are no automated tests yet — add some covering the new behavior, and "
    "make sure the existing routes (/, /delete/<id>, /update/<id>) still work. "
    "Use the Explorer, Researcher, Implementer, Tester and Reviewer subagents as "
    "appropriate instead of doing everything yourself."
)


def main():
    project_memory = memory.load_memory()
    modes = {"plan_mode": False, "supervision_on": False}
    messages = [{"role": "user", "content": REQUEST}]
    task_state = TaskState(original_request=REQUEST)

    final_text = main_agent.run_task(messages, modes, task_state, project_memory)

    print("\n\n================= FINAL ANSWER =================\n")
    print(final_text)

    state_path = main_agent.state_path_for(task_state)
    task_state.save(state_path)
    memory.record_from_task(project_memory, task_state)
    memory.save_memory(project_memory)

    print("\n\n================= STATE SAVED AT =================")
    print(state_path)


if __name__ == "__main__":
    main()
