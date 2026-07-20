"""Tests de state.py: estructura de TaskState y la huella de tool calls que usa el
detector de loops. Nada de esto llama a la API."""
from state import TaskState


def test_records_original_request():
    state = TaskState(original_request="add priority column")
    assert state.original_request == "add priority column"
    assert state.plan == []
    assert state.files_modified == []


def test_record_subagent_result_updates_results_and_progress():
    state = TaskState(original_request="x")
    state.record_subagent_result("Explorer", "explore repo", "found app.py", 3)
    assert state.subagent_results["Explorer"][0]["result"] == "found app.py"
    assert state.subagent_results["Explorer"][0]["iterations"] == 3
    assert state.progress[-1] == {"step": "explore repo", "status": "done", "by": "Explorer"}


def test_add_file_modified_is_deduplicated():
    state = TaskState(original_request="x")
    state.add_file_modified("app.py")
    state.add_file_modified("app.py")
    assert state.files_modified == ["app.py"]


def test_add_source_groups_by_kind():
    state = TaskState(original_request="x")
    state.add_source("rag", {"query": "schema drift"})
    state.add_source("web", {"query": "sqlite alter table"})
    assert len(state.sources["rag"]) == 1
    assert len(state.sources["web"]) == 1


def test_repeated_call_count_escalates_on_identical_calls():
    state = TaskState(original_request="x")
    call = ("run_command", {"command": "pytest -q"}, "1 failed")

    assert state.repeated_call_count(*call) == 0
    state.note_tool_call(*call)

    assert state.repeated_call_count(*call) == 1
    state.note_tool_call(*call)

    assert state.repeated_call_count(*call) == 2
    state.note_tool_call(*call)

    assert state.repeated_call_count(*call) == 3


def test_repeated_call_count_resets_on_different_result():
    state = TaskState(original_request="x")
    state.note_tool_call("run_command", {"command": "pytest -q"}, "1 failed")
    state.note_tool_call("run_command", {"command": "pytest -q"}, "1 failed")

    # mismo tool call, pero esta vez el resultado cambió (por ejemplo, ahora pasa)
    assert state.repeated_call_count("run_command", {"command": "pytest -q"}, "2 passed") == 0


def test_repeated_call_count_ignores_different_arguments():
    state = TaskState(original_request="x")
    state.note_tool_call("read_file", {"path": "app.py"}, "content A")
    assert state.repeated_call_count("read_file", {"path": "other.py"}, "content A") == 0
