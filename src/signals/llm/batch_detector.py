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
        return Path(__file__).parent.parent / "prompts"

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

        # Parse by signal sections (## signal_name)
        rubrics: Dict[str, List[str]] = {}
        current_signal = None

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("## ") and not line.startswith("## "):
                # This is a signal section header
                current_signal = line[3:].strip().lower()
                rubrics[current_signal] = []
            elif current_signal and line and not line.startswith("#") and line.strip():
                # This is rubric content for current signal
                rubrics[current_signal].append(line)

        # Join rubric content
        return {signal: "\n".join(content) for signal, content in rubrics.items()}

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
    ) -> str:
        """Build the complete prompt with all signal rubrics.

        Args:
            response_text: User's response to analyze
            question: Question that was asked (optional context)
        """
        # Start with high-level system prompt
        prompt = self._high_level_prompt.format(
            response=response_text[:100] + "..." if len(response_text) > 100 else response_text,
            question=question[:100] + "..." if question and len(question) > 100 else (question or "N/A"),
        )

        # Inject signal rubrics for all registered LLM signals
        rubrics = self._signal_rubrics
        for signal_key, rubric_content in rubrics.items():
            prompt += f"\n\n## {signal_key.replace('llm.', '').title().replace('_', ' ')}\n"
            prompt += rubric_content

        # Add output format instructions
        prompt += "\n\n" + self._output_format_instructions()

        return prompt

    def _output_format_instructions(self) -> str:
        """Generate output format instructions from example."""
        example = self._output_example

        # Build schema from example
        schema = {signal: data.get("score", {}) for signal, data in example.items()}

        instructions = """Output a JSON object with these exact keys:

"""
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
        prompt = self._build_prompt(response_text, question)

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
            signal_name = signal_cls.signal_name
            if signal_name not in result:
                log.warning(
                    f"Signal '{signal_name}' not found in LLM response",
                )
                continue
            detected_signals[signal_name] = result[signal_name]

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
