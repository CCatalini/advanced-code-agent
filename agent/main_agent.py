import os
from dotenv import load_dotenv

load_dotenv()

from anthropic import Anthropic
from tools import TOOL_SCHEMAS
from execution import execute_tool, extract_text
from orchestrator import call_subagent, CALL_SUBAGENT_SCHEMA
from subagents import SUBAGENT_REGISTRY
from state import TaskState
import context
import memory
import observability

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = os.environ["ANTHROPIC_MODEL"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNS_DIR = os.path.join(BASE_DIR, "..", "logs", "runs", "advanced-coding-agent")

MAIN_AGENT_TOOL_SCHEMAS = TOOL_SCHEMAS + [CALL_SUBAGENT_SCHEMA]


def conversation_mode():
    """
    Loop externo:
    Mantiene el sistema activo después de la ejecución de una tarea,
    generando un historial de mensajes entre el usuario y el agente.
    """
    messages = []
    project_memory = memory.load_memory()
    print("\n========= The agent is ready. =========\n Type 'exit' to end the session.")

    modes = {
        "plan_mode": ask_yes_no("\nDo you want to enable plan mode?"),
        "supervision_on": ask_yes_no("Do you want to enable supervision?"),
    }

    print("\nConfiguration:")
    print(f"  Plan mode:   {'ON' if modes['plan_mode'] else 'OFF'}")
    print(f"  Supervision: {'ON' if modes['supervision_on'] else 'OFF'}")

    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "cancel", "ex", "0"):
            break
        if user_input.lower() == "off":
            turn_off_modes(modes)
            continue

        messages.append({"role": "user", "content": user_input})
        task_state = TaskState(original_request=user_input)
        with observability.span("user_task", request=user_input):
            final_text = run_task(messages, modes, task_state, project_memory)
        print(f"\nAgent: {final_text}")
        print_mode_reminder(modes)

        task_state.save(state_path_for(task_state))
        memory.record_from_task(project_memory, task_state)
        memory.save_memory(project_memory)
        messages[:] = context.maybe_summarize(messages)


def run_task(messages, modes, task_state, project_memory):
    """Loop interno: ejecuta tools (y subagentes) hasta que el modelo devuelva texto final."""
    plan_approved = not modes["plan_mode"]
    iteration = 0

    while True:
        iteration += 1
        print(f"\n--- internal loop iteration {iteration} ---")
        awaiting_approval = modes["plan_mode"] and not plan_approved
        with observability.generation("main_agent.messages_create", MODEL) as log_usage:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                tools=MAIN_AGENT_TOOL_SCHEMAS,
                messages=messages,
                system=build_system_prompt(modes["plan_mode"], plan_approved, project_memory),
                # Mientras el plan no esté aprobado, se bloquea el uso de tools
                tool_choice={"type": "none"} if awaiting_approval else {"type": "auto"},
            )
            log_usage(response)
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            text = extract_text(response.content)

            if response.stop_reason == "max_tokens" and not awaiting_approval:
                print("\n[WARNING] Response was truncated (max_tokens). Asking the model to wrap up concisely.")
                messages.append({
                    "role": "user",
                    "content": "Your previous response was cut off for being too long. "
                               "Give a concise final summary instead of continuing it.",
                })
                continue

            if awaiting_approval:
                if not text.strip():
                    print("\n[PROPOSED PLAN] The model returned no plan text, asking it to try again.")
                    messages.append({
                        "role": "user",
                        "content": "You didn't return a plan. Please provide a numbered plan before proceeding."
                    })
                    continue

                print(f"\n[PROPOSED PLAN]\n{text}")
                while True:
                    answer = input(
                        "\nDo you approve the plan? "
                        "(y / n / off / or type the changes you want): "
                    ).strip()
                    if answer:
                        break
                    print("Empty response. Type 'y', 'n', 'off', or the changes you want.")
                decision = answer.lower()

                if decision == "off":
                    turn_off_modes(modes)
                    plan_approved = True
                    messages.append({"role": "user", "content": "Plan approved, proceed to execute it."})
                elif decision in ("n", "no", "exit", "cancel", "ex", "0"):
                    return "Plan rejected by the user."
                elif decision in ("y", "yes"):
                    plan_approved = True
                    messages.append({"role": "user", "content": "Plan approved, proceed to execute it."})
                else:
                    messages.append({"role": "user", "content": f"Adjust the plan with this: {answer}"})
                continue

            return text

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                try:
                    if block.name == "call_subagent":
                        result = call_subagent(
                            role=block.input["role"],
                            task_description=block.input["task"],
                            state=task_state,
                            modes=modes,
                        )
                    else:
                        with observability.span(f"tool:{block.name}", role="main_agent", input=block.input):
                            result = execute_tool(block.name, block.input, modes, task_state)
                except Exception as e:
                    # error de tool se reenvía al modelo, evita que explote
                    result = f"Error executing {block.name}: {e}"
                if str(result).startswith("[HARD_STOP]"):
                    task_state.add_observation("run_task halted by the loop guard.")
                    return (
                        "I stopped: I was repeating the same action without making progress. "
                        f"{result}"
                    )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })
        messages.append({"role": "user", "content": tool_results})


def build_system_prompt(plan_mode, plan_approved, project_memory):
    roles = ", ".join(SUBAGENT_REGISTRY.keys())
    base = (
        "You are the main agent of a multi-agent coding system. You have direct tools "
        "(read_file, write_file, run_command, list_files, web_search) and a call_subagent "
        f"tool to delegate to specialized subagents. Available subagents: {roles}. "
        "Delegate to a subagent when the sub-task clearly matches its responsibility, "
        "instead of using low-level tools yourself for everything.\n\n"
        f"Persistent project memory:\n{memory.compact_summary(project_memory)}"
    )
    if plan_mode and not plan_approved:
        return base + (
            "\n\nBefore using any tool, respond ONLY with a numbered plan of the "
            "steps you will follow to fulfill the request. "
            "Don't call any tool yet, wait for approval."
        )
    return base


def state_path_for(task_state):
    run_id = task_state.started_at.replace(":", "-")
    return os.path.join(RUNS_DIR, f"{run_id}.json")


def turn_off_modes(modes):
    turned_off = [name for name, key in (("plan mode", "plan_mode"), ("supervision", "supervision_on")) if modes[key]]
    modes["plan_mode"] = False
    modes["supervision_on"] = False
    if turned_off:
        print(f"[{' and '.join(turned_off)} turned off]")
    else:
        print("[Both modes were already off]")


def print_mode_reminder(modes):
    active = [name for name, key in (("plan mode", "plan_mode"), ("supervision", "supervision_on")) if modes[key]]
    if active:
        print(f"[{' and '.join(active)} still ON — send 'off' to turn it off]")


def ask_yes_no(question: str) -> bool:
    return input(f"{question} (y/n): ").strip().lower() in ("y", "yes")


if __name__ == "__main__":
    conversation_mode()
