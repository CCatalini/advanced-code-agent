import os
import subprocess
from tavily import TavilyClient
from rag.retrieve import retrieve as rag_retrieve
import policy

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.abspath(os.path.join(BASE_DIR, "..", policy.CONFIG["workspace"]))


def read_file(path):
    """Lee el contenido completo de un archivo dado su path relativo al workspace."""
    full_path = os.path.join(WORKSPACE, path)
    with open(full_path, "r") as f:
        return f.read()


def write_file(path: str, content: str) -> str:
    """Escribe contenido en un archivo del workspace, creándolo (junto con sus carpetas) si no existe."""
    full_path = os.path.join(WORKSPACE, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
    return f"File written to {path}"


def run_command(command):
    """Ejecuta un comando de shell dentro del workspace y devuelve stdout/stderr."""
    result = subprocess.run(command, shell=True, cwd=WORKSPACE, capture_output=True, text=True, timeout=60)
    return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


def list_files(path="."):
    """Lista los archivos y carpetas dentro de un directorio del workspace."""
    full_path = os.path.join(WORKSPACE, path)
    return "\n".join(os.listdir(full_path))


def web_search(query):
    """Busca en la web usando Tavily y devuelve los resultados encontrados."""
    tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    return tavily.search(query)["results"]


def rag_search(query, k=4):
    """Busca en el corpus indexado (RAG) los fragmentos más relevantes para la query.
    Cada resultado trae su fuente y su score, para poder citarlos y decidir si hace
    falta caer a web_search."""
    results = rag_retrieve(query, k=k)
    if not results:
        return "No relevant chunks found in the RAG index."
    lines = [f"[RAG: {r['source']} | score={r['score']:.3f}] {r['text']}" for r in results]
    return "\n\n".join(lines)


TOOL_FUNCTIONS = {
    "read_file": read_file,
    "write_file": write_file,
    "run_command": run_command,
    "list_files": list_files,
    "web_search": web_search,
    "rag_search": rag_search,
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
    },
    {
        "name": "rag_search",
        "description": "Searches the indexed technical documentation corpus (RAG) for the k most relevant "
                       "chunks to a query, with their source file and similarity score. Always try this "
                       "before web_search: only fall back to web_search if the top result's score is low "
                       "or doesn't actually answer the question.",
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string"},
            "k": {"type": "integer", "description": "How many chunks to retrieve. Default: 4"}
        }, "required": ["query"]}
    }
]
