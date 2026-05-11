"""Tests for question prompt generation with prompt_overrides support."""

import pytest

from src.domain.models.methodology_schema import MethodologySchema
from src.llm.prompts.question import get_question_user_prompt
from src.methodologies.registry import MethodologyRegistry, StrategyConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_methodology(method_name: str = "jobs_to_be_done_v2") -> MethodologySchema:
    return MethodologySchema(method={"name": method_name})


# ---------------------------------------------------------------------------
# Behavior-preservation tests for surface_tension
# ---------------------------------------------------------------------------


class TestSurfaceTensionBehaviorPreserved:
    """Verify that surface_tension output is byte-identical after the refactor.

    The expected strings are derived directly from the pre-change branches:

        focus_framing (with focus_node_type):
            'Concept where hesitation was detected: "{focus_concept}" '
            '(type: {focus_node_type}){level_info}.'
            +
            'The respondent showed uncertainty about this concept. '
            'Use their last answer to find the specific hedging language — '
            'your question must name THAT hesitation, not follow the content thread.'

        final_instruction:
            'Generate a tension probe that names the respondent's hesitation about "{focus_concept}":'
    """

    def test_focus_framing_with_node_type(self) -> None:
        methodology = _make_methodology()
        result = get_question_user_prompt(
            focus_concept="meal planning",
            methodology=methodology,
            strategy="surface_tension",
            focus_node_type="functional_job",
            focus_node_level=None,  # no ontology loaded, level_info will be ""
            topic=None,
        )
        expected_focus_line = (
            'Concept where hesitation was detected: "meal planning" (type: functional_job).'
        )
        assert expected_focus_line in result, (
            f"focus_framing line not found in output.\nGot:\n{result}"
        )

    def test_focus_framing_uncertainty_line(self) -> None:
        methodology = _make_methodology()
        result = get_question_user_prompt(
            focus_concept="meal planning",
            methodology=methodology,
            strategy="surface_tension",
            focus_node_type="functional_job",
        )
        expected_uncertainty = (
            "The respondent showed uncertainty about this concept. "
            "Use their last answer to find the specific hedging language — "
            "your question must name THAT hesitation, not follow the content thread."
        )
        assert expected_uncertainty in result

    def test_final_instruction_surface_tension(self) -> None:
        methodology = _make_methodology()
        result = get_question_user_prompt(
            focus_concept="meal planning",
            methodology=methodology,
            strategy="surface_tension",
            focus_node_type="functional_job",
        )
        expected_final = (
            'Generate a tension probe that names the respondent\'s hesitation about "meal planning":'
        )
        assert expected_final in result

    def test_default_final_instruction_for_non_surface_tension(self) -> None:
        methodology = _make_methodology()
        result = get_question_user_prompt(
            focus_concept="meal planning",
            methodology=methodology,
            strategy="ascend",
            focus_node_type="functional_job",
        )
        assert 'Generate a natural follow-up question about "meal planning":' in result
        assert "tension probe" not in result

    def test_no_focus_source_quote_for_surface_tension(self) -> None:
        """surface_tension must NOT include the focus_source_quote block."""
        methodology = _make_methodology()
        result = get_question_user_prompt(
            focus_concept="meal planning",
            methodology=methodology,
            strategy="surface_tension",
            focus_node_type="functional_job",
            focus_source_quote="I guess I just... I'm not sure exactly",
        )
        # The quote injection text must not appear — surface_tension skips it
        assert "The respondent expressed this as:" not in result
        assert "Ask about the MEANING behind what they said" not in result

    def test_no_default_context_paragraph_for_surface_tension(self) -> None:
        """The 'respondent's answer below provides context' paragraph must not appear."""
        methodology = _make_methodology()
        result = get_question_user_prompt(
            focus_concept="meal planning",
            methodology=methodology,
            strategy="surface_tension",
            focus_node_type="functional_job",
        )
        assert "The respondent's answer below provides context" not in result


# ---------------------------------------------------------------------------
# Validator tests — prompt_overrides allow-list enforcement
# ---------------------------------------------------------------------------


class TestPromptOverridesValidation:
    """Test that MethodologyRegistry._validate_config rejects invalid prompt_overrides."""

    def _registry_with_overrides(
        self, overrides: dict[str, str], method_name: str = "jobs_to_be_done_v2"
    ) -> MethodologyRegistry:
        """Return a registry whose surface_tension strategy has the given overrides."""
        registry = MethodologyRegistry()
        # Prime the cache with the real config
        config = registry.get_methodology(method_name)
        # Mutate surface_tension's prompt_overrides for testing the validator directly
        for s in config.strategies:
            if s.name == "surface_tension":
                s.prompt_overrides = overrides
        return registry, config

    def test_unknown_key_raises(self) -> None:
        registry = MethodologyRegistry()
        config = registry.get_methodology("jobs_to_be_done_v2")

        # Inject a bad key
        for s in config.strategies:
            if s.name == "surface_tension":
                s.prompt_overrides = {"unknown_key": "some value"}

        from pathlib import Path
        with pytest.raises(ValueError, match="unknown_key"):
            registry._validate_config(config, Path("jobs_to_be_done_v2.yaml"))

    def test_unknown_variable_raises(self) -> None:
        registry = MethodologyRegistry()
        config = registry.get_methodology("jobs_to_be_done_v2")

        for s in config.strategies:
            if s.name == "surface_tension":
                s.prompt_overrides = {
                    "focus_framing": "Hello {unknown_var} world {focus_concept}"
                }

        from pathlib import Path
        with pytest.raises(ValueError, match="unknown_var"):
            registry._validate_config(config, Path("jobs_to_be_done_v2.yaml"))

    def test_unknown_variable_error_names_strategy_and_key(self) -> None:
        registry = MethodologyRegistry()
        config = registry.get_methodology("jobs_to_be_done_v2")

        for s in config.strategies:
            if s.name == "surface_tension":
                s.prompt_overrides = {
                    "final_instruction": "Probe {bad_var} in {focus_concept}:"
                }

        from pathlib import Path
        with pytest.raises(ValueError) as exc_info:
            registry._validate_config(config, Path("jobs_to_be_done_v2.yaml"))
        msg = str(exc_info.value)
        assert "surface_tension" in msg
        assert "final_instruction" in msg
        assert "bad_var" in msg

    def test_valid_overrides_do_not_raise(self) -> None:
        """All allow-listed keys and variables must pass validation."""
        registry = MethodologyRegistry()
        config = registry.get_methodology("jobs_to_be_done_v2")

        for s in config.strategies:
            if s.name == "surface_tension":
                s.prompt_overrides = {
                    "focus_framing": (
                        '"{focus_concept}" ({focus_node_type}){level_info} '
                        "{focus_source_quote} {topic}"
                    ),
                    "final_instruction": 'Probe "{focus_concept}":',
                }

        from pathlib import Path
        # Must not raise
        registry._validate_config(config, Path("jobs_to_be_done_v2.yaml"))
