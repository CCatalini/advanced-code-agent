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
    print("The agent is ready. \nType 'exit' to end the session.")

    plan_mode = ask_yes_no("\nDo you want to enable plan mode?")
    supervision_on = ask_yes_no("Do you want to enable supervision?")

    print("\nConfiguration:")
    print(f"  Plan mode:   {'ON' if plan_mode else 'OFF'}")
    print(f"  Supervision: {'ON' if supervision_on else 'OFF'}")

    while True:
        user_input = input("\nYou: ")
        if user_input.strip().lower() == "exit":
            break
        messages.append({"role": "user", "content": user_input})
        final_text = run_task(messages, plan_mode=plan_mode, supervision_on=supervision_on)
        print(f"\nAgent: {final_text}")


def run_task(messages, plan_mode=False, supervision_on=False):
    """Loop interno: ejecuta tools hasta que el modelo devuelva texto final."""
    plan_approved = not plan_mode

    while True:
        awaiting_approval = plan_mode and not plan_approved
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOL_SCHEMAS,
            messages=messages,
            system=build_system_prompt(plan_mode, plan_approved),
            # Mientras el plan no esté aprobado, se bloquea el uso de tools
            tool_choice={"type": "none"} if awaiting_approval else {"type": "auto"},
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            text = extract_text(response.content)

            if awaiting_approval:
                print(f"\n[PROPOSED PLAN]\n{text}")
                answer = input(
                    "Do you approve the plan? (yes / cancel / or type the changes you want): "
                ).strip()
                decision = answer.lower()

                if decision == "cancel":
                    return "Plan rejected by the user."
                elif decision in ("y", "yes"):
                    plan_approved = True
                    messages.append({"role": "user", "content": "Plan approved, proceed to execute it."})
                else:
                    # Cualquier otra respuesta se interpreta como pedido de modificación.
                    messages.append({"role": "user", "content": f"Adjust the plan with this: {answer}"})
                continue

            return text

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                try:
                    result = execute_tool(block.name, block.input, supervision_on)
                except Exception as e:
                    # error de tool se reenvía al modelo
                    result = f"Error executing {block.name}: {e}"
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })
        messages.append({"role": "user", "content": tool_results})


def build_system_prompt(plan_mode, plan_approved):
    """Arma la instrucción de sistema según el estado de plan mode."""
    if plan_mode and not plan_approved:
        return (
            "Before using any tool, respond ONLY with a numbered plan of the "
            "steps you will follow to fulfill the request. "
            "Don't call any tool yet, wait for approval."
        )
    return "You are a coding agent. Use the available tools to fulfill the user's request."


def execute_tool(name, tool_input, supervision_on=False):
    """Ejecuta una tool real, pidiendo confirmación si supervisión está activa."""
    if supervision_on and name not in READ_ONLY_TOOLS:
        print(f"\n[SUPERVISION] The agent wants to execute: {name}({tool_input})")
        if not ask_yes_no("Do you approve this action?"):
            return "Action rejected by the user."
    print(f"  [tool] executing {name}({tool_input})")
    return TOOL_FUNCTIONS[name](**tool_input)


def extract_text(content_blocks):
    for block in content_blocks:
        if block.type == "text":
            return block.text
    return ""


def ask_yes_no(question: str) -> bool:
    return input(f"{question} (y/n): ").strip().lower() in ("y", "yes")


if __name__ == "__main__":
    conversation_mode()
