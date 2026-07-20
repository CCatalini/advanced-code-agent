"""Resume helper: la corrida completa de Test 4 (run_feature_task.py) llegó a tener el
Implementer y el Tester terminados (código real en flask-class + 18 tests de pytest en
verde), pero se cortó por falta de crédito de la API justo antes de que el Reviewer diera
su veredicto. Este script no repite todo el pipeline (Explorer/Researcher/Implementer/
Tester ya hicieron su trabajo y está en disco) — solo corre el Reviewer sobre el diff
real ya aplicado, que es la única pieza que faltó.

Uso: desde agent/, con el venv activado:
    python ../scripts/run_reviewer_only.py
"""
import os
import subprocess
import sys

AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent")
sys.path.insert(0, AGENT_DIR)

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(AGENT_DIR, "..", ".env"))

from state import TaskState
from orchestrator import call_subagent
import policy

ORIGINAL_REQUEST = (
    "Add 'priority' (integer, default 0) and 'due_date' (optional datetime) fields to the "
    "Todo model in this Flask app, plus a way to filter and sort the task list by priority "
    "and completion status via query parameters on the index route. Tests were added "
    "covering the new behavior, and the existing routes should still work."
)


def _git_diff_stat():
    return subprocess.run(
        ["git", "diff", "--stat"], cwd=policy.CONFIG["workspace"] and os.path.join(AGENT_DIR, "..", policy.CONFIG["workspace"]),
        capture_output=True, text=True,
    ).stdout


def _pytest_result():
    result = subprocess.run(
        ["bash", "-c", "source .venv/bin/activate && pytest -q"],
        cwd=os.path.join(AGENT_DIR, "..", policy.CONFIG["workspace"]),
        capture_output=True, text=True,
    )
    return result.stdout[-2000:]


def main():
    task_state = TaskState(original_request=ORIGINAL_REQUEST)
    modes = {"plan_mode": False, "supervision_on": False}

    review_task = (
        f"The Implementer and Tester already completed this request:\n{ORIGINAL_REQUEST}\n\n"
        f"Independent pytest run just now (for your reference, not something you need to "
        f"re-run yourself unless you want to double check specific behavior):\n{_pytest_result()}\n\n"
        "Read app.py, init_db.py, templates/index.html, templates/update.html and the tests/ "
        "directory to review the actual change. Give your verdict."
    )

    result = call_subagent("Reviewer", review_task, task_state, modes)

    print("\n================= REVIEWER VERDICT =================\n")
    print(result)


if __name__ == "__main__":
    main()
