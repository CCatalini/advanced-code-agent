import os
import subprocess
from tavily import TavilyClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.join(BASE_DIR, "..", "workspace")


def read_file(path):
    full_path = os.path.join(WORKSPACE, path)
    with open(full_path, "r") as f:
        return f.read()


def write_file(path, content):
    full_path = os.path.join(WORKSPACE, path)
    with open(full_path, "w") as f:
        f.write(content)
    return f"Archivo {path} escrito ({len(content)} chars)."


def run_command(command):
    result = subprocess.run(command, shell=True, cwd=WORKSPACE, capture_output=True, text=True, timeout=30)
    return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


def list_files(path="."):
    full_path = os.path.join(WORKSPACE, path)
    return "\n".join(os.listdir(full_path))


def web_search(query):
    tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    return tavily.search(query)["results"]


TOOL_FUNCTIONS = {
    "read_file": read_file,
    "write_file": write_file,
    "run_command": run_command,
    "list_files": list_files,
    "web_search": web_search
}


TOOL_SCHEMAS = [
    {
        "name": "read_file",
        "description": "Lee el contenido completo de un archivo de texto dado su path relativo al workspace.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Path relativo al workspace"}},
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Escribe contenido en un archivo, "
                       "si no existe crealo y si ya existe borrá el contenido anterior.",
        "input_schema": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}
        }, "required": ["path", "content"]}
    },
    {
        "name": "run_command",
        "description": "Ejecuta un comando de terminal dentro del workspace y devuelve stdout y stderr.",
        "input_schema": {"type": "object", "properties": {
            "command": {"type": "string"}
        }, "required": ["command"]}
    },
    {
        "name": "list_files",
        "description": "Lista los archivos y carpetas dentro de un directorio del workspace.",
        "input_schema": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Default: '.'"}
        }, "required": []}
    },
    {
        "name": "web_search",
        "description": "Busca información actual en la web cuando la tarea requiere conocimiento externo o reciente.",
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string"}
        }, "required": ["query"]}
    }
]
