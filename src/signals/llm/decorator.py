"""LLM signal decorators for per-concept and global response rating.

Two decorators partition signal classes by scope:
- `@llm_global_signal`   — one score per response (engagement, certainty)
- `@llm_per_concept_signal` — one score per extracted concept (elaboration, charge)

Both decorators:
- Register the class in `_registered_llm_signals` for auto-discovery by batch_detector
- Set `signal_name`, `description`, `scope` as class attributes
- Validate at import time that the class defines a non-empty `RUBRIC: str` class
  constant covering the 1-5 rating bands.

LLM I/O is owned by `batch_detector`; `_analyze_with_llm` on the base class stays
`NotImplementedError`.
"""

import re
from typing import Callable, Dict, Literal, Type

from src.signals.llm.llm_signal_base import BaseLLMSignal

# Registry: namespaced signal name -> class
_registered_llm_signals: Dict[str, Type[BaseLLMSignal]] = {}

_RUBRIC_BAND_PATTERN = re.compile(
    r"^\s*1\s*=.*^\s*2\s*=.*^\s*3\s*=.*^\s*4\s*=.*^\s*5\s*=",
    re.MULTILINE | re.DOTALL,
)


def _validate_rubric(cls: Type[BaseLLMSignal], signal_name: str) -> str:
    """Ensure `cls.RUBRIC` exists, is a non-empty string, and covers bands 1-5.

    Raises ValueError at import time so malformed signals fail fast.
    """
    rubric = getattr(cls, "RUBRIC", None)
    if not isinstance(rubric, str) or not rubric.strip():
        raise ValueError(
            f"Signal class {cls.__name__} ({signal_name}) must define a non-empty "
            "class attribute `RUBRIC: str`."
        )
    if not _RUBRIC_BAND_PATTERN.search(rubric):
        raise ValueError(
            f"Signal {signal_name} RUBRIC must include all five numbered bands "
            "`1 =` through `5 =`."
        )
    return rubric


def _make_decorator(
    scope: Literal["global", "per_concept"],
    signal_name: str,
    description: str,
) -> Callable[[Type[BaseLLMSignal]], Type[BaseLLMSignal]]:
    def decorator(cls: Type[BaseLLMSignal]) -> Type[BaseLLMSignal]:
        _validate_rubric(cls, signal_name)

        cls.signal_name = signal_name  # type: ignore[attr-defined]
        cls.description = description  # type: ignore[attr-defined]
        cls.scope = scope  # type: ignore[attr-defined]

        if signal_name in _registered_llm_signals:
            raise ValueError(
                f"Duplicate LLM signal registration: {signal_name} "
                f"(existing: {_registered_llm_signals[signal_name].__name__}, "
                f"new: {cls.__name__})"
            )
        _registered_llm_signals[signal_name] = cls
        return cls

    return decorator


def llm_global_signal(
    signal_name: str,
    description: str,
) -> Callable[[Type[BaseLLMSignal]], Type[BaseLLMSignal]]:
    """Decorator for response-level (one scalar per response) LLM signals."""
    return _make_decorator("global", signal_name, description)


def llm_per_concept_signal(
    signal_name: str,
    description: str,
) -> Callable[[Type[BaseLLMSignal]], Type[BaseLLMSignal]]:
    """Decorator for per-concept (one scalar per extracted concept) LLM signals."""
    return _make_decorator("per_concept", signal_name, description)
