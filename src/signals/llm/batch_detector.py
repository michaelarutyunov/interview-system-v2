"""LLM batch detector — single call producing per-concept + global ratings.

Loads the base prompt (sibling `llm_signal_baseprompt.md`), injects per-concept
and global rubrics from signal classes, and returns a nested dict partitioned
into `concepts` and `global` sections. Derives `response.semantic.llm.response_depth` categorical
from per-concept elaboration aggregation for backward compatibility with
`llm_response_trend` and the question-generation prompt.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from statistics import mean
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from src.core.exceptions import ScorerFailureError
from src.llm.client import LLMClient

if TYPE_CHECKING:
    from src.signals.llm.llm_signal_base import BaseLLMSignal

log = logging.getLogger(__name__)

_BASE_PROMPT_FILENAME = "llm_signal_baseprompt.md"

# Embedded output format + example — per Phase B-plan B.4 "static constants,
# not separate files".

_OUTPUT_FORMAT = """\
Output a JSON object with two top-level sections: `concepts` and `global`.

{
  "concepts": {
    "<exact concept name from the provided list>": {
      "elaboration": {"score": <1-5>, "rationale": "<max 15 words>"},
      "charge":      {"score": <1-5>, "rationale": "<max 15 words>"}
    }
  },
  "global": {
    "engagement": {"score": <1-5>, "rationale": "<max 15 words>"},
    "certainty":  {"score": <1-5>, "rationale": "<max 15 words>"}
  }
}

Rules:
- Use the EXACT concept name from the provided list as the key.
- Every concept from the list MUST appear in `concepts`.
- Every score MUST be an integer 1-5. Use the full range. Do not default to 3.
- Rationale: one sentence, max 15 words, justifying this score and not one higher or lower.
- Output JSON only. No text before or after the JSON object.
"""

_OUTPUT_EXAMPLE = """\
{
  "concepts": {
    "cold brew more efficient than pour-over": {
      "elaboration": {"score": 3, "rationale": "Comparative reasoning with practical specifics"},
      "charge":      {"score": 4, "rationale": "Mildly positive, practical satisfaction"}
    },
    "making a big batch on Sunday": {
      "elaboration": {"score": 2, "rationale": "One-sentence procedural detail, no elaboration"},
      "charge":      {"score": 3, "rationale": "Neutral, purely descriptive"}
    }
  },
  "global": {
    "engagement": {"score": 3, "rationale": "Answers fully but does not volunteer context"},
    "certainty":  {"score": 4, "rationale": "Confident, no hedging on practical claims"}
  }
}
"""

_RESPONSE_TRUNCATE = 500
_QUESTION_TRUNCATE = 200
_QUOTE_TRUNCATE = 200


def _score_to_category(mean_score: float, n: int) -> str:
    """Derive categorical `response.semantic.llm.response_depth` from mean per-concept elaboration.

    See `docs/drafts/signal-migration-contract.md` §3. Downstream consumers
    (llm_response_trend, node_base.all_response_depths,
    question.py prompt) expect strings: surface / shallow / moderate / deep.
    """
    if n == 0:
        return "surface"
    # Normalize 1-5 -> [0,1]: (s-1)/4
    norm = (mean_score - 1.0) / 4.0
    if n == 1 and norm <= 0.25:
        return "surface"
    if norm < 0.34:
        return "shallow"
    if norm < 0.67:
        return "moderate"
    return "deep"


class LLMBatchDetector:
    """Single-call LLM orchestrator for per-concept + global signals."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self._base_prompt = self._load_base_prompt()

    @property
    def _base_prompt_path(self) -> Path:
        return Path(__file__).parent / _BASE_PROMPT_FILENAME

    def _load_base_prompt(self) -> str:
        path = self._base_prompt_path
        if not path.exists():
            raise FileNotFoundError(f"Base prompt template not found: {path}")
        return path.read_text()

    # ------------------------------------------------------------------ prompt

    def _partition_classes(
        self, signal_classes: List[Type["BaseLLMSignal"]]
    ) -> tuple[list[Type["BaseLLMSignal"]], list[Type["BaseLLMSignal"]]]:
        per_concept: list[Type["BaseLLMSignal"]] = []
        global_: list[Type["BaseLLMSignal"]] = []
        for cls in signal_classes:
            scope = getattr(cls, "scope", None)
            if scope == "per_concept":
                per_concept.append(cls)
            elif scope == "global":
                global_.append(cls)
            else:
                raise ValueError(
                    f"Signal class {cls.__name__} has no `scope` attribute — "
                    "register it with @llm_global_signal or @llm_per_concept_signal."
                )
        return per_concept, global_

    @staticmethod
    def _short_name(signal_cls: Type["BaseLLMSignal"]) -> str:
        """Strip the `llm.` namespace for LLM-facing keys."""
        return signal_cls.signal_name.split(".")[-1]  # type: ignore[attr-defined]

    def _render_rubrics(self, classes: list[Type["BaseLLMSignal"]]) -> tuple[str, str]:
        names = ", ".join(self._short_name(c) for c in classes)
        blocks = []
        for cls in classes:
            header = self._short_name(cls)
            blocks.append(f"### {header}\n\n{cls.RUBRIC.strip()}")  # type: ignore[attr-defined]
        return names, "\n\n".join(blocks)

    @staticmethod
    def _concept_fields(c: Any) -> tuple[str, list[str]]:
        """Extract (text, quotes) whether c is a dict or an ExtractedConcept."""
        if isinstance(c, dict):
            name = c.get("text") or c.get("name", "")
            quotes = c.get("source_quotes") or (
                [c["source_quote"]] if c.get("source_quote") else []
            )
        else:
            name = getattr(c, "text", None) or getattr(c, "name", "")
            quotes = getattr(c, "source_quotes", None) or (
                [getattr(c, "source_quote")] if getattr(c, "source_quote", None) else []
            )
        return name, [q for q in quotes if q]

    def _render_concepts(self, concepts: list[Any]) -> str:
        lines = []
        for c in concepts:
            name, quotes = self._concept_fields(c)
            quote_text = " | ".join(q[:_QUOTE_TRUNCATE] for q in quotes)
            lines.append(f"- {name}: {quote_text}" if quote_text else f"- {name}")
        return "\n".join(lines) if lines else "(none provided)"

    def _build_prompt(
        self,
        response_text: str,
        question: str,
        concepts: list[Any],
        per_concept_classes: list[Type["BaseLLMSignal"]],
        global_classes: list[Type["BaseLLMSignal"]],
    ) -> str:
        pc_names, pc_rubrics = self._render_rubrics(per_concept_classes)
        gl_names, gl_rubrics = self._render_rubrics(global_classes)
        return self._base_prompt.format(
            question=question[:_QUESTION_TRUNCATE] if question else "N/A",
            response=response_text[:_RESPONSE_TRUNCATE] if response_text else "",
            concepts=self._render_concepts(concepts),
            per_concept_signal_names=pc_names,
            global_signal_names=gl_names,
            per_concept_rubrics=pc_rubrics,
            global_rubrics=gl_rubrics,
            output_format=_OUTPUT_FORMAT,
            output_example=_OUTPUT_EXAMPLE,
        )

    # ----------------------------------------------------------------- parsing

    @staticmethod
    def _clamp_score(raw: Any) -> int:
        """Clamp any raw LLM value to an int in [1, 5], defaulting to 3."""
        if isinstance(raw, dict) and "score" in raw:
            raw_score: Any = raw["score"]
        else:
            raw_score = raw
        if not isinstance(raw_score, (int, float, str)):
            log.warning(
                "Non-numeric LLM score %r — falling back to neutral 3.", raw_score
            )
            return 3
        try:
            score = int(raw_score)
        except (TypeError, ValueError):
            log.warning(
                "Unparseable LLM score %r — falling back to neutral 3.", raw_score
            )
            return 3
        return max(1, min(5, score))

    @staticmethod
    def _normalize(score: int) -> float:
        return (score - 1) / 4.0

    def _parse_response(
        self,
        raw: Dict[str, Any],
        concepts: list[Any],
        per_concept_classes: list[Type["BaseLLMSignal"]],
        global_classes: list[Type["BaseLLMSignal"]],
    ) -> Dict[str, Any]:
        """Extract nested {concepts, global} from LLM JSON and normalize."""
        raw_concepts = raw.get("concepts", {}) if isinstance(raw, dict) else {}
        raw_global = raw.get("global", {}) if isinstance(raw, dict) else {}

        # -- per-concept -----------------------------------------------------
        per_concept_out: Dict[str, Dict[str, float]] = {}
        elaboration_raw_scores: list[int] = []

        for concept in concepts:
            name, _ = self._concept_fields(concept)
            entry = raw_concepts.get(name, {}) if isinstance(raw_concepts, dict) else {}
            record: Dict[str, float] = {}
            for cls in per_concept_classes:
                short = self._short_name(cls)
                if not isinstance(entry, dict) or short not in entry:
                    log.warning(
                        "LLM output missing per-concept %s for '%s' — applying "
                        "prompt-contract fallback (elaboration=1, charge=3).",
                        short,
                        name,
                    )
                    fallback = 1 if short == "elaboration" else 3
                    score = fallback
                else:
                    score = self._clamp_score(entry[short])
                if short == "elaboration":
                    elaboration_raw_scores.append(score)
                record[cls.signal_name] = self._normalize(score)  # type: ignore[attr-defined]
            per_concept_out[name] = record

        # -- global ----------------------------------------------------------
        global_out: Dict[str, Any] = {}
        for cls in global_classes:
            short = self._short_name(cls)
            if not isinstance(raw_global, dict) or short not in raw_global:
                log.warning(
                    "LLM output missing global '%s' — falling back to neutral 3.", short
                )
                score = 3
            else:
                score = self._clamp_score(raw_global[short])
            global_out[cls.signal_name] = self._normalize(score)  # type: ignore[attr-defined]

        # -- derived llm.response_depth -------------------------------------
        if elaboration_raw_scores:
            depth = _score_to_category(
                mean(elaboration_raw_scores), len(elaboration_raw_scores)
            )
        else:
            depth = "surface"
        global_out["response.semantic.llm.response_depth"] = depth

        return {"concepts": per_concept_out, "global": global_out}

    # ------------------------------------------------------------------ detect

    async def detect(
        self,
        response_text: str,
        question: str,
        concepts: list[Any],
        signal_classes: Optional[List[Type["BaseLLMSignal"]]] = None,
    ) -> Dict[str, Any]:
        """Run one LLM call, return {concepts: {...}, global: {...}}.

        Args:
            response_text: respondent's answer.
            question: interviewer question.
            concepts: list of extracted concepts (objects with `.name` and
                `.source_quote(s)`, or dicts with the same keys). Required;
                per-concept signals need concept targets.
            signal_classes: optional override; defaults to all auto-discovered
                @llm_global_signal / @llm_per_concept_signal classes.

        Raises:
            ScorerFailureError: LLM call failed or returned unparseable JSON.
            ValueError: concepts empty or a signal class has no `scope`.
        """
        if not concepts:
            log.warning(
                "LLMBatchDetector.detect called with empty concepts list — "
                "per-concept signals will be empty, global signals still detected."
            )

        if signal_classes is None:
            from src.signals.llm.decorator import _registered_llm_signals

            signal_classes = list(_registered_llm_signals.values())

        per_concept, global_ = self._partition_classes(signal_classes)
        if not per_concept and not global_:
            raise ValueError("No LLM signal classes registered.")

        prompt = self._build_prompt(
            response_text, question, concepts, per_concept, global_
        )
        log.debug("LLM batch prompt built (%d chars).", len(prompt))

        try:
            response = await self.llm_client.complete(
                prompt=prompt,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            log.error("LLM batch call failed: %s", e, exc_info=True)
            raise ScorerFailureError(f"LLM signal detection failed: {e}") from e

        try:
            raw = json.loads(response.content)
        except (json.JSONDecodeError, ValueError) as e:
            log.error(
                "LLM response is not valid JSON: %s. Body: %r",
                e,
                response.content[:500],
                exc_info=True,
            )
            raise ScorerFailureError(f"Invalid LLM response: {e}") from e

        result = self._parse_response(raw, concepts, per_concept, global_)
        log.info(
            "LLM batch detection complete: %d concepts, %d global keys.",
            len(result["concepts"]),
            len(result["global"]),
        )
        return result
