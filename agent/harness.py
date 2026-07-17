import os
from dotenv import load_dotenv
from anthropic import Anthropic
from tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = os.environ["ANTHROPIC_MODEL"]
READ_ONLY_TOOLS = {"read_file", "list_files", "web_search"}


def conversation_mode():
    """
    Loop externo:
    Mantiene el sistema activo después de la ejecución de una tarea,
    generando un historial de mensajes entre el usuario y el agente.
    """
    messages = []
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
        final_text = run_task(messages, modes)
        print(f"\nAgent: {final_text}")
        print_mode_reminder(modes)


def run_task(messages, modes):
    """Loop interno: ejecuta tools hasta que el modelo devuelva texto final."""
    plan_approved = not modes["plan_mode"]
    iteration = 0

    while True:
        iteration += 1
        print(f"\n--- internal loop iteration {iteration} ---")
        awaiting_approval = modes["plan_mode"] and not plan_approved
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOL_SCHEMAS,
            messages=messages,
            system=build_system_prompt(modes["plan_mode"], plan_approved),
            # Mientras el plan no esté aprobado, se bloquea el uso de tools
            tool_choice={"type": "none"} if awaiting_approval else {"type": "auto"},
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            text = extract_text(response.content)

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
                    result = execute_tool(block.name, block.input, modes)
                except Exception as e:
                    # error de tool se reenvía al modelo, evita que explote
                    result = f"Error executing {block.name}: {e}"
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })
        messages.append({"role": "user", "content": tool_results})


def build_system_prompt(plan_mode, plan_approved):
    if plan_mode and not plan_approved:
        return (
            "Before using any tool, respond ONLY with a numbered plan of the "
            "steps you will follow to fulfill the request. "
            "Don't call any tool yet, wait for approval."
        )
    return "You are a coding agent. Use the available tools to fulfill the user's request."


def execute_tool(name, tool_input, modes):
    """Ejecuta una tool, pidiendo confirmación si supervisión está activa."""
    if modes["supervision_on"] and name not in READ_ONLY_TOOLS:
        print(f"\n[SUPERVISION] The agent wants to execute: {name}({tool_input})")
        answer = input("Do you approve this action? (y/n/off): ").strip().lower()
        if answer == "off":
            turn_off_modes(modes)
        elif answer not in ("y", "yes"):
            return "Action rejected by the user."
    print(f"  [tool] executing {name}({tool_input})")
    return TOOL_FUNCTIONS[name](**tool_input)


def extract_text(content_blocks):
    for block in content_blocks:
        if block.type == "text":
            return block.text
    return ""


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
