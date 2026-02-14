"""LLM batch detector — orchestrates single LLM call for all signals.

Collects prompt specifications from all registered LLM signals and makes
one API call to Kimi K2.5 (via scoring LLM client).
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from src.core.exceptions import ScorerFailureError
from src.llm.client import LLMClient

if TYPE_CHECKING:
    from src.signals.llm.llm_signal_base import BaseLLMSignal

log = logging.getLogger(__name__)


class LLMBatchDetector:
    """Orchestrates batch LLM signal detection.

    Loads high_level.md base prompt, injects signal-specific rubrics
    from signals.md, and makes a single API call.
    """

    def __init__(self, llm_client: LLMClient):
        """Initialize batch detector.

        Args:
            llm_client: Scoring LLM client (Kimi K2.5) for making API calls
        """
        self.llm_client = llm_client

        # Load prompts
        self._high_level_prompt = self._load_high_level_prompt()
        self._signal_rubrics = self._load_signal_rubrics()
        self._output_example = self._load_output_example()

        log.debug("LLMBatchDetector initialized with prompts from %s", self._prompts_dir)

    @property
    def _prompts_dir(self) -> Path:
        """Path to prompts directory."""
        return Path(__file__).parent / "prompts"

    def _load_high_level_prompt(self) -> str:
        """Load high_level.md base prompt template."""
        return self._load_template("high_level.md")

    def _load_template(self, template_name: str) -> str:
        """Load a prompt template file.

        Args:
            template_name: Name of template file (e.g., "signals.md")

        Returns:
            Template content as string
        """
        template_path = self._prompts_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {template_path}")

        with open(template_path) as f:
            return f.read()

    def _load_signal_rubrics(self) -> Dict[str, str]:
        """Parse signals.md to extract rubric sections.

        Returns:
            Dictionary mapping signal key to its rubric content
            e.g., {"response_depth": "## response_depth\\n1=...", ...}
        """
        signals_md_path = self._prompts_dir / "signals.md"
        if not signals_md_path.exists():
            raise FileNotFoundError(f"Signals rubric not found: {signals_md_path}")

        with open(signals_md_path) as f:
            content = f.read()

        # Parse by signal sections (signal_name: description at column 0)
        # signals.md uses indentation-based structure:
        #   response_depth: How much elaboration...   <- header (no indent)
        #       1 = Minimal or single-word answer     <- content (indented)
        rubrics: Dict[str, List[str]] = {}
        current_signal = None

        for line in content.split("\n"):
            stripped = line.strip()
            # Signal header: starts at column 0, contains ":", not a comment
            if line and not line[0].isspace() and ":" in stripped and not stripped.startswith("#"):
                current_signal = stripped.split(":")[0].strip().lower()
                # Include the description after the colon as first line of rubric
                description = ":".join(stripped.split(":")[1:]).strip()
                rubrics[current_signal] = [description] if description else []
            elif current_signal and stripped and not stripped.startswith("#"):
                rubrics[current_signal].append(stripped)

        # Join rubric content
        return {signal: "\n".join(lines) for signal, lines in rubrics.items()}

    def _load_output_example(self) -> Dict[str, Any]:
        """Load output_example.json to show expected format.

        Returns:
            Dictionary with signal examples
        """
        example_path = self._prompts_dir / "output_example.json"
        if not example_path.exists():
            raise FileNotFoundError(f"Output example not found: {example_path}")

        with open(example_path) as f:
            return json.load(f)

    def _build_prompt(
        self,
        response_text: str,
        question: str | None = None,
        signal_classes: Optional[List[Type]] = None,
    ) -> str:
        """Build the complete prompt with all signal rubrics.

        Args:
            response_text: User's response to analyze
            question: Question that was asked (optional context)
            signal_classes: List of signal classes to include (for rubric_key mapping)
        """
        # Start with high-level system prompt
        prompt = self._high_level_prompt.format(
            response=response_text[:500] + "..." if len(response_text) > 500 else response_text,
            question=question[:200] + "..." if question and len(question) > 200 else (question or "N/A"),
        )

        # Inject signal rubrics for specified signal classes using rubric_key
        # (non-namespaced key for LLM communication)
        rubrics = self._signal_rubrics
        if signal_classes:
            for signal_cls in signal_classes:
                rubric_key = getattr(signal_cls, '_rubric_key', None)
                if rubric_key and rubric_key in rubrics:
                    prompt += f"\n\n## {rubric_key.replace('_', ' ').title()}\n"
                    prompt += rubrics[rubric_key]
        else:
            # Fallback: use all rubrics (legacy behavior)
            for signal_key, rubric_content in rubrics.items():
                prompt += f"\n\n## {signal_key.replace('llm.', '').title().replace('_', ' ')}\n"
                prompt += rubric_content

        # Add output format instructions
        prompt += "\n\n" + self._output_format_instructions(signal_classes)

        return prompt

    def _output_format_instructions(self, signal_classes: Optional[List[Type]] = None) -> str:
        """Generate output format instructions from example.

        Args:
            signal_classes: List of signal classes to include (for rubric_key mapping)
        """
        instructions = """Output a JSON object with these exact keys:

"""
        # Use signal classes to get correct rubric_key (non-namespaced) for output format
        if signal_classes:
            for signal_cls in signal_classes:
                rubric_key = getattr(signal_cls, '_rubric_key', None)
                if rubric_key:
                    instructions += f'  "{rubric_key}": {{"score": <integer 1-5>, "rationale": "<one sentence explanation, max 20 words>}}'
        else:
            # Fallback: use example keys (legacy behavior)
            example = self._output_example
            schema = {signal: data.get("score", {}) for signal, data in example.items()}
            for signal_name in schema.keys():
                instructions += f'  "{signal_name}": {{"score": <integer 1-5>, "rationale": "<one sentence explanation, max 20 words>}}'

        instructions += "\n}"
        instructions += """

Each score MUST be an integer from 1 to 5. Use the full range. Do not default to 3.

The rationale field should briefly justify the score in one sentence (max 20 words).
"""
        return instructions

    async def detect(
        self,
        response_text: str,
        question: str | None = None,
        signal_classes: Optional[List[Type]] = None,
    ) -> Dict[str, Any]:
        """Detect all LLM signals in a single batch call.

        Args:
            response_text: User's response to analyze
            question: Optional question for context
            signal_classes: List of LLM signal class types (for collecting prompt specs)

        Returns:
            Dictionary mapping signal_name → detected value (1-5 integers)

        Raises:
            ScorerFailureError: If LLM call fails or returns invalid response
        """
        if signal_classes is None:
            # Auto-discover all BaseLLMSignal subclasses
            from src.signals.llm.decorator import _registered_llm_signals
            # Collect all registered signal classes
            signal_classes = list(_registered_llm_signals.values())
            log.debug(f"Auto-discovered {len(signal_classes)} LLM signal classes")
        else:
            log.debug(f"Using {len(signal_classes)} explicitly provided signal classes")

        # Collect prompt specs from each signal class
        # Each signal class has _get_prompt_spec() classmethod from decorator
        prompt = self._build_prompt(response_text, question, signal_classes)

        log.debug(f"Built batch prompt ({len(prompt)} chars) for {len(signal_classes)} signals")

        # Make single LLM call
        try:
            response = await self.llm_client.complete(
                prompt=prompt,
            )
            response_text = response.content

            log.debug(f"LLM batch response: {response_text[:200]}...")

        except Exception as e:
            log.error(f"LLM batch call failed: {e}", exc_info=True)
            raise ScorerFailureError(f"LLM signal detection failed: {e}") from e

        # Parse JSON response
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse LLM response as JSON: {e}", exc_info=True)
            raise ScorerFailureError(f"Invalid LLM response: {e}") from e

        # Validate and normalize results
        # Ensure all expected signal keys are present
        detected_signals = {}
        for signal_cls in signal_classes:
            signal_name = signal_cls.signal_name  # namespaced: "llm.response_depth"
            rubric_key = getattr(signal_cls, '_rubric_key', None)  # non-namespaced: "response_depth"

            # Look up by rubric_key (what LLM returns), store by signal_name (internal)
            lookup_key = rubric_key if rubric_key else signal_name.replace('llm.', '')
            if lookup_key not in result:
                log.warning(
                    f"Signal '{lookup_key}' (maps to '{signal_name}') not found in LLM response",
                )
                continue
            raw_value = result[lookup_key]

            # Handle dict format {"score": N, "rationale": "..."} or just integer
            if isinstance(raw_value, dict) and "score" in raw_value:
                detected_signals[signal_name] = raw_value["score"]
            else:
                detected_signals[signal_name] = raw_value

            # Validate score is integer 1-5
            if not isinstance(detected_signals[signal_name], int):
                log.warning(
                    f"Signal '{signal_name}' has non-integer value: {detected_signals[signal_name]}"
                )
                # Try to convert if it's a string number
                try:
                    detected_signals[signal_name] = int(detected_signals[signal_name])
                except (ValueError, TypeError):
                    log.error(f"Invalid score for '{signal_name}': {detected_signals[signal_name]}")

            # Validate score range
            score = detected_signals[signal_name]
            if isinstance(score, int) and not (1 <= score <= 5):
                log.warning(
                    f"Signal '{signal_name}' has out-of-range score: {score}"
                )
                score = max(1, min(5, score))

            # Normalize based on signal type
            # Categorical signals: keep as string categories
            # Continuous signals: normalize to [0, 1]
            CATEGORICAL_SIGNALS = {"llm.response_depth"}  # Add others as needed

            if signal_name in CATEGORICAL_SIGNALS:
                # Map 1-5 to categorical strings for downstream compatibility
                score_to_category = {
                    1: "surface",
                    2: "shallow",
                    3: "moderate",
                    4: "deep",
                    5: "deep",
                }
                if isinstance(score, int):
                    detected_signals[signal_name] = score_to_category.get(score, "moderate")
            else:
                # Normalize Likert 1-5 to [0, 1]: (value - 1) / 4
                if isinstance(score, int):
                    detected_signals[signal_name] = (score - 1) / 4

        log.info(f"LLM batch detection complete: {detected_signals}")

        return detected_signals

    @staticmethod
    def _registered_classes() -> List[Type["BaseLLMSignal"]]:
        """Get all registered LLM signal classes."""
        from src.signals.llm.decorator import _registered_llm_signals
        return list(_registered_llm_signals.values())
