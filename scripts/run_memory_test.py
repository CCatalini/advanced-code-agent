"""Test 2 del plan: demuestra que la memoria persistente de proyecto sobrevive entre
sesiones. Se corre DESPUÉS de run_feature_task.py (que ya dejó una entrada en
memory/project_memory.json): esta 'sesión nueva' carga esa memoria y le pregunta al
agente principal por la convención del proyecto, sin pasarle el historial de la sesión
anterior — solo el resumen compacto que main_agent inyecta en el system prompt.

Uso: desde agent/, con el venv activado, DESPUÉS de correr run_feature_task.py:
    python ../scripts/run_memory_test.py
"""
import os
import sys

AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent")
sys.path.insert(0, AGENT_DIR)

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(AGENT_DIR, "..", ".env"))

from state import TaskState
import main_agent
import memory

QUESTION = (
    "Sin explorar el repositorio de nuevo: según lo que ya sabés de sesiones anteriores, "
    "¿qué cambios se hicieron en este proyecto y por qué hubo que recrear la base de datos "
    "en vez de solo agregar una columna?"
)


def main():
    project_memory = memory.load_memory()

    print("================= COMPACT MEMORY SUMMARY (lo que se inyecta en el system prompt) =================\n")
    print(memory.compact_summary(project_memory))

    print("\n\n================= NUEVA SESION: pregunta sin historial previo =================\n")
    modes = {"plan_mode": False, "supervision_on": False}
    messages = [{"role": "user", "content": QUESTION}]
    task_state = TaskState(original_request=QUESTION)

    final_text = main_agent.run_task(messages, modes, task_state, project_memory)

    print("\n================= RESPUESTA DEL AGENTE =================\n")
    print(final_text)

    print("\n================= SUBAGENTES USADOS EN ESTA 'SESION NUEVA' =================")
    print(list(task_state.subagent_results.keys()) or "Ninguno — respondió solo con memoria.")


if __name__ == "__main__":
    main()
