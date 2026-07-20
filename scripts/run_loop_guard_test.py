"""Test 3 del plan (parte determinística): demuestra que el detector de loops de
execution.py escala de una llamada normal -> aviso suave -> aviso fuerte -> corte
duro, cuando la misma tool call se repite con el mismo resultado. No llama a la API
de Anthropic (no consume crédito): ejercita execute_tool() directamente.

Uso: desde agent/, con el venv activado:
    python ../scripts/run_loop_guard_test.py
"""
import os
import sys

AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent")
sys.path.insert(0, AGENT_DIR)
os.environ.setdefault("ANTHROPIC_API_KEY", "not-needed-for-this-test")
os.environ.setdefault("ANTHROPIC_MODEL", "not-needed-for-this-test")

from state import TaskState
from execution import execute_tool


def main():
    task_state = TaskState(original_request="Test 3 — loop guard demo")
    modes = {"plan_mode": False, "supervision_on": False}
    failing_command = {"command": 'python -c "import nonexistent_module_xyz"'}

    for i in range(5):
        result = execute_tool("run_command", failing_command, modes, task_state)
        tag = result.splitlines()[0][:80]
        print(f"call {i + 1}: {tag}")

    print("\n================= OBSERVATIONS RECORDED =================\n")
    for obs in task_state.observations:
        print("-", obs)


if __name__ == "__main__":
    main()
