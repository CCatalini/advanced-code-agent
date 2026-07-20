import sys

from tools import TOOL_FUNCTIONS
import policy

READ_ONLY_TOOLS = {"read_file", "list_files", "web_search", "rag_search"}


def _check_policy(name, tool_input):
    """Valida la tool call contra agent.config.yaml ANTES de ejecutarla. Se llama siempre,
    tenga o no supervisión activa: las políticas de permisos no son opcionales."""
    if name == "read_file":
        policy.check_read(tool_input.get("path", ""))
    elif name == "write_file":
        policy.check_write(tool_input.get("path", ""))
    elif name == "run_command":
        policy.check_command(tool_input.get("command", ""))


def execute_tool(name, tool_input, modes, state=None):
    """Ejecuta una tool, validando políticas, pidiendo confirmación si corresponde, y
    detectando si esta misma llamada se está repitiendo sin avanzar. Compartida por el
    agente principal y el orchestrator para que todos los subagentes respeten las mismas
    reglas y el mismo detector de loops (via `state`, el TaskState de la tarea en curso)."""
    try:
        _check_policy(name, tool_input)
    except policy.PolicyError as e:
        print(f"\n[POLICY] Blocked: {e}")
        return f"Blocked by policy: {e}"

    needs_approval = (
        (modes.get("supervision_on") and name not in READ_ONLY_TOOLS)
        or (name == "run_command" and policy.command_requires_approval(tool_input.get("command", "")))
    )
    if needs_approval:
        print(f"\n[SUPERVISION] The agent wants to execute: {name}({tool_input})")
        if not sys.stdin.isatty():
            # No hay una terminal interactiva del otro lado (script/demo en background):
            # no tiene sentido bloquear en input()
            print("[SUPERVISION] No interactive terminal attached — auto-rejecting.")
            return (
                "Action rejected: this command requires human approval "
                "(agent.config.yaml commands.require_approval), but no interactive "
                "terminal is attached to approve it. Report this as blocked instead of "
                "retrying — it will keep being rejected the same way."
            )
        answer = input("Do you approve this action? (y/n/off): ").strip().lower()
        if answer == "off":
            modes["plan_mode"] = False
            modes["supervision_on"] = False
            print("[plan mode and supervision turned off]")
        elif answer not in ("y", "yes"):
            return "Action rejected by the user."

    print(f"  [tool] executing {name}({tool_input})")
    result = TOOL_FUNCTIONS[name](**tool_input)

    if state is not None and name not in ("list_files",):
        repeats = state.repeated_call_count(name, tool_input, result)
        state.note_tool_call(name, tool_input, result)

        if repeats >= 3:
            # si corre por 4ta vez seguida corta el loop por si el modelo no "corta solo"
            print(f"\n[HARD STOP] '{name}' repeated {repeats + 1}x — forcing the loop to stop.")
            state.add_observation(
                f"Hard stop: '{name}' was called with identical arguments {repeats + 1} times "
                "in a row with the same result. Execution was halted automatically."
            )
            return (
                f"[HARD_STOP] Automatic loop guard triggered: '{name}' was called with the "
                f"exact same arguments {repeats + 1} times in a row and got the exact same "
                "result every time. Execution has been halted — this is not a suggestion, no "
                f"further tool calls will run this turn.\n\nLast result was:\n{result}"
            )
        elif repeats == 2:
            print(f"\n[LOOP DETECTED] '{name}' repeated {repeats + 1}x with the same result.")
            state.add_observation(
                f"Loop detected: '{name}' called with the same arguments returned the same "
                f"result {repeats + 1} times in a row."
            )
            return (
                f"[LOOP DETECTED] This exact tool call has now returned the same result "
                f"{repeats + 1} times in a row. Do NOT repeat it again unchanged. Stop, "
                "diagnose why it keeps failing or not helping, and either change your "
                "approach (a different tool, delegate to another subagent, re-read the "
                "actual error) or clearly report to the user what you tried, what's missing, "
                f"and what you need to proceed.\n\nLast result was:\n{result}"
            )
        elif repeats == 1:
            return (
                "[REPEATED ACTION] This exact tool call just returned the same result as the "
                "previous time. Repeating it again unchanged will be treated as a loop — "
                f"reconsider your approach before retrying.\n\n{result}"
            )

    return result


def extract_text(content_blocks):
    for block in content_blocks:
        if block.type == "text":
            return block.text
    return ""
