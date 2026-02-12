"""LLM signal decorator for creating signal classes with metadata.

This decorator eliminates boilerplate by providing signal metadata
and handling prompt template loading. Each signal class becomes just:
    @llm_signal(signal_name="...", rubric_key="...", description="...")
    class MySignal(BaseLLMSignal):
        pass
"""

from pathlib import Path
from typing import Callable, Type, Any

from src.signals.llm.llm_signal_base import BaseLLMSignal

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def _load_prompt_template(template_name: str) -> str:
    """Load a prompt template from the prompts directory.

    Args:
        template_name: Name of template file (e.g., "high_level.md")

    Returns:
        Template content as string
    """
    template_path = PROMPTS_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")

    with open(template_path) as f:
        return f.read_text()


def _parse_signals_rubrics() -> dict[str, str]:
    """Parse signals.md to extract rubric sections.

    Returns:
        Dictionary mapping signal key to its rubric content
        e.g., {"response_depth": "## response_depth\\n1=...", ...}
    """
    signals_md_path = PROMPTS_DIR / "signals.md"
    if not signals_md_path.exists():
        raise FileNotFoundError(f"Signals rubric not found: {signals_md_path}")

    with open(signals_md_path) as f:
        content = f.read_text()

    # Parse by signal sections (## signal_name)
    rubrics = {}
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
    for signal in rubrics:
        rubrics[signal] = "\n".join(rubrics[signal])

    return rubrics


def _load_output_example() -> dict:
    """Load output_example.json to show expected format.

    Returns:
        Dictionary with signal examples
    """
    example_path = PROMPTS_DIR / "output_example.json"
    if not example_path.exists():
        raise FileNotFoundError(f"Output example not found: {example_path}")

    import json
    with open(example_path) as f:
        return json.load(f)


def llm_signal(
    signal_name: str,
    rubric_key: str,
    description: str,
    output_schema: dict | None = None,
) -> Callable[[Type[BaseLLMSignal]], Type[BaseLLMSignal]]:
    """Decorator that creates an LLM signal class with metadata.

    The decorator handles all boilerplate for creating signal classes:
    - Sets signal_name, description, output_schema as class attributes
    - Creates _get_prompt_spec() that returns the rubric from signals.md
    - Creates _get_output_schema() that returns the output schema

    Args:
        signal_name: Namespaced signal name (e.g., "llm.response_depth")
        rubric_key: Key in signals.md (e.g., "response_depth")
        description: Human-readable description of what signal measures
        output_schema: Optional JSON schema for output validation

    Returns:
        Decorator function that creates the signal class

    Example:
        @llm_signal(
            signal_name="llm.response_depth",
            rubric_key="response_depth",
            description="Assesses quantity of elaboration (1-5)",
        )
        class ResponseDepthSignal(BaseLLMSignal):
            pass  # Everything handled by decorator!
    """

    def decorator(cls: Type[BaseLLMSignal]) -> Type[BaseLLMSignal]:
        # Create new class that inherits from BaseLLMSignal
        class_name_from_attr = signal_name.replace("llm.", "").title().replace("_", "")

        class DynamicSignalClass(cls):
            signal_name = signal_name
            description = description
            _rubric_key = rubric_key
            _output_schema = output_schema or {}

            @classmethod
            def _get_prompt_spec(cls) -> str:
                """Return the signal rubric from signals.md."""
                rubrics = _parse_signals_rubrics()
                if rubric_key not in rubrics:
                    raise ValueError(f"Rubric key '{rubric_key}' not found in signals.md")
                return rubrics[rubric_key]

            @classmethod
            def _get_output_schema(cls) -> dict:
                """Return the output schema for this signal."""
                if cls._output_schema:
                    return cls._output_schema
                # Default schema from output_example.json
                example = _load_output_example()
                if signal_name in example:
                    return example[signal_name]
                else:
                    return {"type": "integer", "minimum": 1, "maximum": 5}

            async def _analyze_with_llm(self, response_text: str) -> dict:
                """Placeholder — actual LLM analysis handled by batch detector."""
                raise NotImplementedError("LLM analysis handled by batch detector")

        # Set the class name dynamically
        DynamicSignalClass.__name__ = f"{cls.__name__}_{class_name_from_attr}"
        DynamicSignalClass.__module__ = cls.__module__

        return DynamicSignalClass

    return decorator(cls)


# Ensure backward compatibility - decorator can be used as:
# @llm_signal(...)  OR @llm_signal decorator
_llm_signal_func: Callable[[Type[BaseLLMSignal]], Type[BaseLLMSignal]] = llm_signal  # type: ignore
llm_signal: Any = _llm_signal_func  # type: ignore
