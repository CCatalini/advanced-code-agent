"""Tests de memory.py. Todos redirigen MEMORY_PATH a un archivo temporal, para no pisar
la memoria real del proyecto (memory/project_memory.json) que ya tiene evidencia de
corridas reales. Nada de esto llama a la API."""
import copy

import memory
from state import TaskState


def _fresh_memory():
    return copy.deepcopy(memory.DEFAULT_MEMORY)


def test_load_memory_returns_default_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_PATH", str(tmp_path / "does_not_exist.json"))
    result = memory.load_memory()
    assert result == memory.DEFAULT_MEMORY
    assert result is not memory.DEFAULT_MEMORY  # no debe devolver la misma referencia mutable


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    path = str(tmp_path / "project_memory.json")
    monkeypatch.setattr(memory, "MEMORY_PATH", path)

    mem = memory.load_memory()
    mem["conventions"].append("routes live in app.py")
    memory.save_memory(mem)

    reloaded = memory.load_memory()
    assert reloaded["conventions"] == ["routes live in app.py"]


def test_compact_summary_with_no_history():
    assert memory.compact_summary(_fresh_memory()) == (
        "No previous memory recorded for this project."
    )


def test_compact_summary_includes_recent_conventions_and_decisions():
    mem = _fresh_memory()
    mem["conventions"] = ["uses Flask-SQLAlchemy", "no migrations tool installed"]
    mem["decisions"] = ["added priority column via manual ALTER TABLE"]
    summary = memory.compact_summary(mem)
    assert "no migrations tool installed" in summary
    assert "added priority column via manual ALTER TABLE" in summary


def test_compact_summary_only_keeps_last_n_items():
    mem = _fresh_memory()
    mem["decisions"] = [f"decision {i}" for i in range(10)]
    summary = memory.compact_summary(mem, max_items=2)
    assert "decision 8" in summary and "decision 9" in summary
    assert "decision 0" not in summary


def test_record_from_task_appends_decision_when_files_changed():
    mem = _fresh_memory()
    state = TaskState(original_request="add priority column")
    state.add_file_modified("app.py")
    state.record_subagent_result("Implementer", "add column", "done", 2)

    memory.record_from_task(mem, state)

    assert len(mem["decisions"]) == 1
    assert "app.py" in mem["decisions"][0]
    assert len(mem["session_summaries"]) == 1
    assert "Implementer" in mem["session_summaries"][0]["summary"]


def test_record_from_task_skips_decision_when_no_files_changed():
    mem = _fresh_memory()
    state = TaskState(original_request="just a question")

    memory.record_from_task(mem, state)

    assert mem["decisions"] == []
    assert len(mem["session_summaries"]) == 1  # el resumen de sesión sí se agrega siempre
