"""Tests for extraction prompt functions."""

import inspect
import pytest

from src.llm.prompts.extraction import (
    get_extraction_system_prompt,
    get_extractability_system_prompt,
)


def test_get_extraction_system_prompt_requires_methodology():
    """methodology must be a required parameter with no default."""
    sig = inspect.signature(get_extraction_system_prompt)
    param = sig.parameters["methodology"]
    assert param.default is inspect.Parameter.empty, (
        "get_extraction_system_prompt: 'methodology' must not have a default value"
    )


def test_get_extractability_system_prompt_requires_methodology():
    """methodology must be a required parameter with no default."""
    sig = inspect.signature(get_extractability_system_prompt)
    param = sig.parameters["methodology"]
    assert param.default is inspect.Parameter.empty, (
        "get_extractability_system_prompt: 'methodology' must not have a default value"
    )


def test_get_extraction_system_prompt_raises_without_methodology():
    """Calling without methodology raises TypeError."""
    with pytest.raises(TypeError):
        get_extraction_system_prompt()  # type: ignore[call-arg]


def test_get_extractability_system_prompt_raises_without_methodology():
    """Calling without methodology raises TypeError."""
    with pytest.raises(TypeError):
        get_extractability_system_prompt()  # type: ignore[call-arg]


def test_get_extraction_system_prompt_accepts_explicit_methodology():
    """Calling with an explicit methodology returns a non-empty string."""
    result = get_extraction_system_prompt(methodology="means_end_chain_v2_strict")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_extractability_system_prompt_accepts_explicit_methodology():
    """Calling with an explicit methodology returns a non-empty string."""
    result = get_extractability_system_prompt(methodology="means_end_chain_v2_strict")
    assert isinstance(result, str)
    assert len(result) > 0
