import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


@dataclass
class TaskState:
    """Estado compartido de una tarea: lo escriben el agente principal y los subagentes."""
    original_request: str
    plan: list = field(default_factory=list)
    progress: list = field(default_factory=list)
    subagent_results: dict = field(default_factory=dict)
    sources: dict = field(default_factory=lambda: {"rag": [], "web": [], "repo": [], "memory": []})
    files_modified: list = field(default_factory=list)
    observations: list = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tool_call_log: list = field(default_factory=list)

    def record_subagent_result(self, role, task, result, iterations):
        self.subagent_results.setdefault(role, []).append({
            "task": task,
            "result": result,
            "iterations": iterations,
        })
        self.progress.append({"step": task, "status": "done", "by": role})

    def add_observation(self, note):
        self.observations.append(note)

    def add_file_modified(self, path):
        if path not in self.files_modified:
            self.files_modified.append(path)

    def add_source(self, kind, entry):
        self.sources.setdefault(kind, []).append(entry)

    def _fingerprint(self, tool_name, tool_input, result):
        args_key = json.dumps(tool_input, sort_keys=True, default=str)
        return f"{tool_name}:{args_key}", str(result)[:300]

    def repeated_call_count(self, tool_name, tool_input, result):
        """Cuántas veces seguidas (mirando hacia atrás) se repitió esta misma tool call
        con exactamente el mismo resultado. 0 si la última no coincide."""
        fingerprint, result_snippet = self._fingerprint(tool_name, tool_input, result)
        count = 0
        for entry in reversed(self.tool_call_log):
            if entry["fingerprint"] == fingerprint and entry["result"] == result_snippet:
                count += 1
            else:
                break
        return count

    def note_tool_call(self, tool_name, tool_input, result):
        fingerprint, result_snippet = self._fingerprint(tool_name, tool_input, result)
        self.tool_call_log.append({"fingerprint": fingerprint, "result": result_snippet})

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
