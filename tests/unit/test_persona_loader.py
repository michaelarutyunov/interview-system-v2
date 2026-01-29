"""Tests for persona loader."""

import pytest
from src.core.persona_loader import (
    load_persona,
    list_personas,
    load_all_personas,
    clear_cache,
    PersonaConfig,
)


class TestListPersonas:
    """Tests for list_personas."""

    def test_returns_dict(self):
        """list_personas returns dict of persona_id to name."""
        personas = list_personas()
        assert isinstance(personas, dict)

    def test_has_expected_personas(self):
        """Contains expected persona IDs."""
        personas = list_personas()
        expected = ["health_conscious", "price_sensitive", "convenience_seeker", "quality_focused", "sustainability_minded"]
        for persona_id in expected:
            assert persona_id in personas


class TestLoadPersona:
    """Tests for load_persona."""

    def test_loads_health_conscious(self):
        """Loads health_conscious persona successfully."""
        persona = load_persona("health_conscious")
        assert persona.id == "health_conscious"
        assert persona.name == "Health-Conscious Millennial"
        assert len(persona.traits) > 0
        assert persona.speech_pattern

    def test_loads_all_personas(self):
        """Can load all available personas."""
        personas = list_personas()
        for persona_id in personas.keys():
            persona = load_persona(persona_id)
            assert isinstance(persona, PersonaConfig)

    def test_raises_for_unknown_persona(self):
        """Raises FileNotFoundError for unknown persona."""
        with pytest.raises(FileNotFoundError):
            load_persona("unknown_persona")


class TestLoadAllPersonas:
    """Tests for load_all_personas."""

    def test_returns_dict(self):
        """load_all_personas returns dict of persona_id to PersonaConfig."""
        personas = load_all_personas()
        assert isinstance(personas, dict)

    def test_all_values_are_persona_config(self):
        """All values are PersonaConfig instances."""
        personas = load_all_personas()
        for persona in personas.values():
            assert isinstance(persona, PersonaConfig)


class TestCache:
    """Tests for persona caching."""

    def test_clear_cache(self):
        """clear_cache empties the cache."""
        # Load a persona to populate cache
        load_persona("health_conscious")
        clear_cache()
        # Should be able to load again after clearing
        persona = load_persona("health_conscious")
        assert persona.id == "health_conscious"
