# LLM Signal Detection

## Core Mechanics

All LLM signals are computed in a **single batched API call** per turn via `LLMBatchDetector`. The batch sends all active signals together rather than one call per signal, keeping latency flat regardless of signal count.

Signal classes are defined with zero boilerplate using the `@llm_signal` decorator. The decorator wires up `signal_name`, `rubric_key`, `description`, and a `_get_prompt_spec()` classmethod that reads the rubric from `src/signals/llm/prompts/signals.md`. The class body is always `pass` — the decorator handles everything.

Rubrics in `signals.md` define a 1–5 integer scale. At detection time all six per-turn signals are **normalised to [0, 1]** via `(score - 1) / 4`. The exception is `response_depth`, which is treated categorically (the integer band drives discrete strategy weights such as `response_depth.low`).

`llm.global_response_trend` is **not** a per-turn signal. It is a session-level aggregate computed separately in `GlobalSignalDetectionService` from the rolling history of per-turn scores. Its values are categorical strings (`improving`, `degrading`, `stable`).

A signal is **only active** if it appears in the methodology YAML under `signals: llm:`. Signals absent from that list are never sent to the LLM and never appear in scoring.

## Correctness Requirements

1. `rubric_key` in `@llm_signal(...)` must exactly match a top-level key in `src/signals/llm/prompts/signals.md` — a mismatch raises `ValueError` at runtime.
2. The class body decorated with `@llm_signal` must be `pass`; adding methods or attributes bypasses the decorator's wiring.
3. Every new signal class must be imported and listed in `__all__` in `src/signals/llm/signals/__init__.py`, otherwise the batch detector cannot discover it.
4. The signal name must appear in the methodology YAML `signals: llm:` list for it to fire during interviews.
5. Continuous signals normalise to [0, 1] — strategy weight keys must use `.low`, `.mid`, `.high` bin names, not raw integers.
6. `llm.global_response_trend` weight keys use categorical strings (`improving`, `degrading`, `stable`), not numeric bins.

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| Signal always 0 / never appears in logs | Signal not listed under `signals: llm:` in methodology YAML | Add signal name to the YAML list |
| `ValueError: Rubric key '...' not found in signals.md` | `rubric_key` in decorator does not match key in `signals.md` | Align spelling between decorator and rubric file |
| New signal class never detected | Missing from `__all__` in `src/signals/llm/signals/__init__.py` | Add import and export entry |
| Strategy weight never triggers for a continuous signal | Weight key uses integer (e.g. `3`) instead of bin name | Replace with `.low`, `.mid`, or `.high` |
| `global_response_trend` always `stable` | Session history too short or LLM call failed silently | Check `GlobalSignalDetectionService` logs; minimum history requires 2+ turns |

## Key Files

| File | Purpose |
|------|---------|
| `src/signals/llm/decorator.py` | `@llm_signal` decorator and `_registered_llm_signals` registry |
| `src/signals/llm/prompts/signals.md` | 1–5 rubric definitions for all 6 per-turn signals |
| `src/signals/llm/signals/` | One file per signal (`depth.py`, `specificity.py`, `certainty.py`, `valence.py`, `engagement.py`, `intellectual_engagement.py`) |
| `src/signals/llm/signals/__init__.py` | `__all__` export list — must include every signal class |
| `src/signals/llm/llm_signal_base.py` | `BaseLLMSignal` base class |
| `src/signals/session/llm_response_trend.py` | `llm.global_response_trend` session-level signal |
| `src/services/global_signal_detection_service.py` | Computes `global_response_trend` from rolling history |
| `config/methodologies/*.yaml` | `signals: llm:` lists that gate which signals are active |
