"""Tests de context.py. `_summarize` se reemplaza por un stub: lo que se prueba acá es
la lógica de CUÁNDO resumir y qué se conserva, no la calidad del resumen del modelo (eso
ya se ejercitó manualmente en conversation_mode). Cero costo de API."""
import context


def _messages(n):
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"message {i}"} for i in range(n)]


def test_no_summary_below_threshold(monkeypatch):
    monkeypatch.setattr(context, "_summarize", lambda msgs: "SHOULD NOT BE CALLED")
    messages = _messages(context.SUMMARY_THRESHOLD)
    result = context.maybe_summarize(messages)
    assert result == messages  # sin cambios, no llegó al umbral


def test_summary_triggers_above_threshold(monkeypatch):
    monkeypatch.setattr(context, "_summarize", lambda msgs: "5 bullet summary")
    messages = _messages(context.SUMMARY_THRESHOLD + 1)

    result = context.maybe_summarize(messages)

    assert len(result) == context.KEEP_LAST + 1  # 1 mensaje-resumen + los últimos crudos
    assert "5 bullet summary" in result[0]["content"]
    assert result[0]["role"] == "user"


def test_keeps_last_messages_verbatim(monkeypatch):
    monkeypatch.setattr(context, "_summarize", lambda msgs: "summary")
    messages = _messages(context.SUMMARY_THRESHOLD + 5)

    result = context.maybe_summarize(messages)

    assert result[-context.KEEP_LAST:] == messages[-context.KEEP_LAST:]


def test_summarize_receives_only_the_older_messages(monkeypatch):
    received = {}

    def fake_summarize(msgs):
        received["count"] = len(msgs)
        return "summary"

    monkeypatch.setattr(context, "_summarize", fake_summarize)
    total = context.SUMMARY_THRESHOLD + 5
    context.maybe_summarize(_messages(total))

    assert received["count"] == total - context.KEEP_LAST
