import os
import subprocess
from tavily import TavilyClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.join(BASE_DIR, "..", "workspace")


def read_file(path):
    """Lee el contenido completo de un archivo dado su path relativo al workspace."""
    full_path = os.path.join(WORKSPACE, path)
    with open(full_path, "r") as f:
        return f.read()


def write_file(path: str, content: str) -> str:
    """Escribe contenido en un archivo del workspace, creándolo (junto con sus carpetas) si no existe."""
    full_path = os.path.join(WORKSPACE, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)  # crea carpetas intermedias si no existen
    with open(full_path, "w") as f:
        f.write(content)
    return f"File written to {path}"


def run_command(command):
    """Ejecuta un comando de shell dentro del workspace y devuelve stdout/stderr."""
    result = subprocess.run(command, shell=True, cwd=WORKSPACE, capture_output=True, text=True, timeout=30)
    return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


def list_files(path="."):
    """Lista los archivos y carpetas dentro de un directorio del workspace."""
    full_path = os.path.join(WORKSPACE, path)
    return "\n".join(os.listdir(full_path))


def web_search(query):
    """Busca en la web usando Tavily y devuelve los resultados encontrados."""
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
        "description": "Reads the full contents of a text file given its path relative to the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Path relative to the workspace"}},
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Writes content to a file, "
                       "creating it if it doesn't exist and overwriting it if it does.",
        "input_schema": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}
        }, "required": ["path", "content"]}
    },
    {
        "name": "run_command",
        "description": "Runs a terminal command inside the workspace and returns stdout and stderr.",
        "input_schema": {"type": "object", "properties": {
            "command": {"type": "string"}
        }, "required": ["command"]}
    },
    {
        "name": "list_files",
        "description": "Lists the files and folders inside a workspace directory.",
        "input_schema": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Default: '.'"}
        }, "required": []}
    },
    {
        "name": "web_search",
        "description": "Searches the web for current information when the task requires external or recent knowledge.",
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string"}
        }, "required": ["query"]}
    }
]
