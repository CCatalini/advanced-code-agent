"""Wrapper de observabilidad sobre Langfuse. Si no hay LANGFUSE_PUBLIC_KEY/SECRET_KEY en
el entorno (cuenta gratuita que el grupo tiene que crear en https://cloud.langfuse.com),
todo esto degrada a no-op salvo el log local en logs/observability.jsonl, que sirve como
evidencia mínima incluso antes de tener la cuenta configurada."""
import json
import os
import time
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone

ENABLED = bool(os.environ.get("LANGFUSE_PUBLIC_KEY")) and bool(os.environ.get("LANGFUSE_SECRET_KEY"))

_client = None
if ENABLED:
    from langfuse import get_client
    _client = get_client()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_LOG_PATH = os.path.join(BASE_DIR, "..", "logs", "observability.jsonl")

# USD por millón de tokens (aproximado, a partir del pricing público de Anthropic —
# alcanza para una estimación de costo, no reemplaza la factura real).
PRICING_PER_MTOK = {
    "claude-sonnet-5": {"input": 3.0, "output": 15.0},
    "claude-opus-4-8": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5-20251001": {"input": 0.8, "output": 4.0},
}
DEFAULT_PRICE = {"input": 3.0, "output": 15.0}


def estimate_cost_usd(model, input_tokens, output_tokens):
    price = PRICING_PER_MTOK.get(model, DEFAULT_PRICE)
    return (input_tokens / 1_000_000) * price["input"] + (output_tokens / 1_000_000) * price["output"]


@contextmanager
def span(name, **metadata):
    """Span genérico (subagente, tool call, retrieval). No-op si Langfuse no está configurado."""
    if not ENABLED:
        yield None
        return
    with _client.start_as_current_span(name=name, metadata=metadata) as s:
        yield s


@contextmanager
def generation(name, model):
    """Envuelve una llamada a messages.create. Devuelve una función `log_usage(response)`
    para llamar después de la llamada real, que mide latencia, tokens y costo estimado —
    y los deja tanto en Langfuse (si está activo) como en el log local (siempre)."""
    start = time.time()
    ctx = _client.start_as_current_generation(name=name, model=model) if ENABLED else nullcontext()
    with ctx as gen:
        def log_usage(response):
            usage = getattr(response, "usage", None)
            if usage is None:
                return
            latency = time.time() - start
            cost = estimate_cost_usd(model, usage.input_tokens, usage.output_tokens)
            if ENABLED and gen is not None:
                gen.update(
                    usage_details={"input": usage.input_tokens, "output": usage.output_tokens},
                    cost_details={"total": cost},
                    metadata={"latency_seconds": round(latency, 3)},
                )
            _append_local_log(name, model, usage.input_tokens, usage.output_tokens, latency, cost)
        yield log_usage


def _append_local_log(name, model, input_tokens, output_tokens, latency, cost):
    os.makedirs(os.path.dirname(LOCAL_LOG_PATH), exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_seconds": round(latency, 3),
        "estimated_cost_usd": round(cost, 6),
    }
    with open(LOCAL_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
