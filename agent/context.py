import os
from anthropic import Anthropic
from execution import extract_text
import observability

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = os.environ["ANTHROPIC_MODEL"]

# Cada cuántos mensajes del historial externo se dispara un resumen, y cuántos
# mensajes recientes se dejan sin tocar (crudos) después de resumir.
SUMMARY_THRESHOLD = 12
KEEP_LAST = 4


def maybe_summarize(messages):
    """Si la conversación externa (entre turnos de usuario) creció demasiado, reemplaza
    los mensajes más viejos por un resumen compacto, para no mandar todo el historial
    completo al modelo en cada turno."""
    if len(messages) <= SUMMARY_THRESHOLD:
        return messages

    older, recent = messages[:-KEEP_LAST], messages[-KEEP_LAST:]
    summary_text = _summarize(older)
    summary_message = {
        "role": "user",
        "content": f"[Summary of {len(older)} earlier messages]\n{summary_text}",
    }
    print(f"\n[CONTEXT] Summarized {len(older)} older messages to keep the context small.")
    return [summary_message] + recent


def _summarize(messages):
    flattened = []
    for m in messages:
        content = m["content"]
        if isinstance(content, str):
            flattened.append(f"{m['role']}: {content}")
        else:
            flattened.append(f"{m['role']}: [tool call/result exchange, {len(content)} block(s)]")
    text_blob = "\n".join(flattened)

    with observability.generation("context.summarize", MODEL) as log_usage:
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": (
                    "Summarize the key facts, decisions and open items from this conversation "
                    f"in at most 5 bullet points, keeping it concise:\n\n{text_blob}"
                ),
            }],
        )
        log_usage(response)
    return extract_text(response.content)
