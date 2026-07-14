import os
from dotenv import load_dotenv
from anthropic import Anthropic
from tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-5"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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
            return response.content[0].text

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


if __name__ == "__main__":
    # task1 = [{"role": "user", "content": "Leé el archivo hola.txt y decime qué dice."}]
    # task2 = [{"role": "user", "content": "Listá los archivos del workspace, después creá uno nuevo llamado"
    #                                         "resumen.txt que diga cuántos archivos había."}]
    #   task3 = [{"role": "user", "content": "Buscá en la web información sobre la historia de la inteligencia artificial "
    #                                       "y escribí un resumen de 1000 caracteres en un archivo llamado ia_history.txt."}]

    task4 = [{"role": "user", "content": "Corré el comando 'wc -l ia_history.txt' en el workspace y decime cuántas "
                                         "líneas tiene el archivo."}]
    # print(run_task(task1))
    # print(run_task(task2))
    # print(run_task(task3))
    print(run_task(task4))
