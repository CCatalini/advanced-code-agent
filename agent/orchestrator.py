import os
from anthropic import Anthropic
from tools import TOOL_SCHEMAS
from execution import execute_tool, extract_text
from subagents import SUBAGENT_REGISTRY
import observability

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = os.environ["ANTHROPIC_MODEL"]

CALL_SUBAGENT_SCHEMA = {
    "name": "call_subagent",
    "description": (
        "Delegates a sub-task to a specialized subagent instead of using low-level tools "
        "directly. Available roles: " + ", ".join(SUBAGENT_REGISTRY.keys()) + ". "
        "Use this when the sub-task clearly matches a subagent's responsibility."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "role": {"type": "string", "enum": list(SUBAGENT_REGISTRY.keys())},
            "task": {"type": "string", "description": "Concrete description of the sub-task to solve"},
        },
        "required": ["role", "task"],
    },
}


def call_subagent(role, task_description, state, modes):
    """Corre un loop de messages.create independiente para el subagente `role`, con su
    propio system prompt y su propio subconjunto de tools. Guarda el resultado en `state`
    y devuelve un resumen (no el historial completo) para el agente principal."""
    if role not in SUBAGENT_REGISTRY:
        return f"Error: subagent '{role}' does not exist. Valid roles: {list(SUBAGENT_REGISTRY.keys())}"

    system_prompt, allowed_tools = SUBAGENT_REGISTRY[role]
    tool_schemas = [s for s in TOOL_SCHEMAS if s["name"] in allowed_tools]
    messages = [{"role": "user", "content": task_description}]
    iteration = 0

    with observability.span(f"subagent:{role}", task=task_description):
        while True:
            iteration += 1
            with observability.generation(f"subagent:{role}.messages_create", MODEL) as log_usage:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=4096,
                    tools=tool_schemas,
                    system=system_prompt,
                    messages=messages,
                )
                log_usage(response)
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                text = extract_text(response.content)
                if response.stop_reason == "max_tokens":
                    print(f"\n[WARNING] {role}'s response was truncated (max_tokens). Asking it to wrap up.")
                    messages.append({
                        "role": "user",
                        "content": "Your previous response was cut off for being too long. "
                                   "Give a concise final summary instead of continuing it.",
                    })
                    continue
                state.record_subagent_result(role, task_description, text, iteration)
                return f"[{role}] {text}"

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    if block.name not in allowed_tools:
                        result = f"Tool '{block.name}' is not permitted for role {role}."
                    else:
                        try:
                            with observability.span(f"tool:{block.name}", role=role, input=block.input):
                                result = execute_tool(block.name, block.input, modes, state)
                            _track_side_effects(block.name, block.input, role, state)
                        except Exception as e:
                            result = f"Error executing {block.name}: {e}"
                    if str(result).startswith("[HARD_STOP]"):
                        halt_message = f"[{role}] Stopped: repeating the same action without making progress. {result}"
                        state.record_subagent_result(role, task_description, halt_message, iteration)
                        return halt_message
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
            messages.append({"role": "user", "content": tool_results})


def _track_side_effects(tool_name, tool_input, role, state):
    """Anota en el TaskState compartido lo que un subagente modificó o consultó, para
    que la sección de fuentes y de archivos modificados quede completa sin que cada
    subagente tenga que reportarlo a mano en su texto final."""
    if tool_name == "write_file":
        state.add_file_modified(tool_input.get("path"))
    elif tool_name == "rag_search":
        state.add_source("rag", {"role": role, "query": tool_input.get("query")})
    elif tool_name == "web_search":
        state.add_source("web", {"role": role, "query": tool_input.get("query")})
    elif tool_name in ("read_file", "list_files"):
        state.add_source("repo", {"role": role, "path": tool_input.get("path", ".")})
