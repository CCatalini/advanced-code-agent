"""Tests de execution.py: política, aprobación sin terminal interactiva, y escalada del
detector de loops. Usa subprocess real (run_command) pero nunca llama a la API de
Anthropic."""
import sys
import types

from execution import execute_tool
from state import TaskState


def test_policy_blocks_denied_read_without_touching_the_filesystem():
    result = execute_tool("read_file", {"path": ".env"}, modes={})
    assert result.startswith("Blocked by policy")


def test_policy_blocks_denied_command():
    result = execute_tool("run_command", {"command": "rm -rf instance/"}, modes={})
    assert result.startswith("Blocked by policy")


def test_approval_required_command_auto_rejects_without_a_tty(monkeypatch):
    monkeypatch.setattr(sys, "stdin", types.SimpleNamespace(isatty=lambda: False))
    result = execute_tool("run_command", {"command": "pip install requests"}, modes={"supervision_on": False})
    assert "no interactive terminal is attached" in result
    assert "Report this as blocked instead of retrying" in result


def test_loop_guard_escalates_on_identical_failing_command():
    state = TaskState(original_request="test loop guard")
    modes = {"supervision_on": False}
    failing_command = {"command": 'python3 -c "import nonexistent_module_xyz"'}

    first = execute_tool("run_command", failing_command, modes, state)
    second = execute_tool("run_command", failing_command, modes, state)
    third = execute_tool("run_command", failing_command, modes, state)
    fourth = execute_tool("run_command", failing_command, modes, state)

    assert not first.startswith("[")  # ejecución normal, sin aviso todavía
    assert second.startswith("[REPEATED ACTION]")
    assert third.startswith("[LOOP DETECTED]")
    assert fourth.startswith("[HARD_STOP]")


def test_loop_guard_does_not_trigger_on_varying_commands():
    state = TaskState(original_request="test no false positives")
    modes = {"supervision_on": False}

    r1 = execute_tool("run_command", {"command": "echo one"}, modes, state)
    r2 = execute_tool("run_command", {"command": "echo two"}, modes, state)
    r3 = execute_tool("run_command", {"command": "echo three"}, modes, state)

    assert not r1.startswith("[")
    assert not r2.startswith("[")
    assert not r3.startswith("[")
