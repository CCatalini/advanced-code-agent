import os
from dotenv import load_dotenv
from anthropic import Anthropic
from tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = os.environ["ANTHROPIC_MODEL"]


def extract_text(content_blocks):
    """
    Busca el bloque de tipo 'text' dentro de la respuesta del modelo
    'Content' puede incluir bloques de otros tipos (ej: 'thinking') antes del texto.
    """
    for block in content_blocks:
        if block.type == "text":
            return block.text
    return ""


def execute_tool(name, tool_input):
    print(f"  [tool] ejecutando {name}({tool_input})")
    return TOOL_FUNCTIONS[name](**tool_input)


def run_task(messages):
    while True:
        response = client.messages.create(
            model=MODEL, max_tokens=1024, tools=TOOL_SCHEMAS, messages=messages
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return extract_text(response.content)

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })
        messages.append({"role": "user", "content": tool_results})


def chat_loop():
    messages = []
    print("Agente listo. Escribí 'salir' para terminar.")
    while True:
        user_input = input("\nVos: ")
        if user_input.strip().lower() == "salir":
            break
        messages.append({"role": "user", "content": user_input})
        final_text = run_task(messages)
        print(f"\nAgente: {final_text}")


if __name__ == "__main__":
    chat_loop()
