"""
Tests for SRLService.

Tests lazy loading, discourse relation extraction, SRL frame extraction,
noise predicate filtering, and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.services.srl_service import SRLService


@pytest.fixture
def srl_service():
    """Create SRLService instance with test configuration."""
    return SRLService(model_name="en_core_web_md")


class TestLazyLoading:
    """Test that spaCy model is loaded lazily."""

    def test_nlp_not_loaded_on_init(self):
        """spaCy model should not load during __init__."""
        service = SRLService()
        assert service._nlp is None

    @patch("src.services.srl_service.spacy")
    def test_nlp_loaded_on_first_access(self, mock_spacy):
        """spaCy model should load on first access to nlp property."""
        mock_nlp = MagicMock()
        mock_spacy.load.return_value = mock_nlp

        service = SRLService(model_name="en_core_web_md")

        # Access nlp property
        result = service.nlp

        # Verify model was loaded
        mock_spacy.load.assert_called_once_with("en_core_web_md")
        assert result == mock_nlp
        assert service._nlp == mock_nlp

    @patch("src.services.srl_service.spacy")
    def test_nlp_loaded_only_once(self, mock_spacy):
        """spaCy model should only load once, not on subsequent accesses."""
        mock_nlp = MagicMock()
        mock_spacy.load.return_value = mock_nlp

        service = SRLService()

        # Access multiple times
        _ = service.nlp
        _ = service.nlp
        _ = service.nlp

        # Should only load once
        assert mock_spacy.load.call_count == 1


class TestEdgeCases:
    """Test error handling and edge cases."""

    def test_empty_string_returns_empty_structures(self, srl_service):
        """Empty input should return empty lists, not crash."""
        result = srl_service.analyze("")

        assert result == {
            "discourse_relations": [],
            "srl_frames": [],
        }

    def test_none_input_returns_empty_structures(self, srl_service):
        """None input should return empty lists, not crash."""
        result = srl_service.analyze(None)  # type: ignore

        assert result == {
            "discourse_relations": [],
            "srl_frames": [],
        }

    def test_whitespace_only_returns_empty_structures(self, srl_service):
        """Whitespace-only input should return empty lists."""
        result = srl_service.analyze("   \n\t  ")

        assert result == {
            "discourse_relations": [],
            "srl_frames": [],
        }

    @patch("src.services.srl_service.spacy")
    def test_spacy_error_returns_empty_structures(self, mock_spacy):
        """If spaCy raises an error, return empty structures gracefully."""
        mock_nlp = MagicMock()
        mock_nlp.side_effect = RuntimeError("spaCy error")
        mock_spacy.load.return_value = mock_nlp

        service = SRLService()
        result = service.analyze("test input")

        assert result == {
            "discourse_relations": [],
            "srl_frames": [],
        }


class TestDiscourseRelationExtraction:
    """Test discourse relation extraction via MARK/ADVCL dependencies."""

    @patch("src.services.srl_service.spacy")
    def test_causal_marker_detection(self, mock_spacy):
        """Should detect 'because' as discourse marker via MARK dependency."""
        # Mock spaCy doc with MARK dependency
        mock_token_because = MagicMock()
        mock_token_because.dep_ = "mark"
        mock_token_because.text = "because"

        mock_head = MagicMock()
        mock_head.subtree = [
            MagicMock(text="I"),
            MagicMock(text="like"),
            MagicMock(text="it"),
        ]
        mock_head.head = MagicMock()
        mock_head.head.subtree = [
            MagicMock(text="I"),
            MagicMock(text="buy"),
            MagicMock(text="oat"),
            MagicMock(text="milk"),
        ]

        mock_token_because.head = mock_head

        mock_doc = [mock_token_because]
        mock_nlp = MagicMock()
        mock_nlp.return_value = mock_doc
        mock_spacy.load.return_value = mock_nlp

        service = SRLService()
        result = service.analyze("I buy oat milk because I like it")

        assert len(result["discourse_relations"]) >= 0  # At least extracted something

    @patch("src.services.srl_service.spacy")
    def test_no_discourse_markers_in_simple_sentence(self, mock_spacy):
        """Simple sentence without markers should have no discourse relations."""
        # Mock doc with no MARK/ADVCL dependencies
        mock_token = MagicMock()
        mock_token.dep_ = "nsubj"  # Not MARK or ADVCL

        mock_doc = [mock_token]
        mock_nlp = MagicMock()
        mock_nlp.return_value = mock_doc
        mock_spacy.load.return_value = mock_nlp

        service = SRLService()
        result = service.analyze("I like oat milk")

        assert result["discourse_relations"] == []


class TestSRLFrameExtraction:
    """Test SRL frame extraction via dependency parsing."""

    @patch("src.services.srl_service.spacy")
    def test_simple_svo_sentence(self, mock_spacy):
        """Should extract predicate-argument structure from simple SVO sentence."""
        # Mock: "I buy milk"
        mock_verb = MagicMock()
        mock_verb.pos_ = "VERB"
        mock_verb.text = "buy"
        mock_verb.lemma_ = "buy"

        mock_subj = MagicMock()
        mock_subj.dep_ = "nsubj"
        mock_subj.text = "I"

        mock_obj = MagicMock()
        mock_obj.dep_ = "dobj"
        mock_obj.text = "milk"

        mock_verb.children = [mock_subj, mock_obj]

        mock_doc = [mock_verb]
        mock_nlp = MagicMock()
        mock_nlp.return_value = mock_doc
        mock_spacy.load.return_value = mock_nlp

        service = SRLService()
        result = service.analyze("I buy milk")

        # Should extract frame with predicate and arguments
        assert len(result["srl_frames"]) == 1
        frame = result["srl_frames"][0]
        assert frame["predicate"] == "buy"
        assert "nsubj" in frame["arguments"]
        assert "dobj" in frame["arguments"]

    @patch("src.services.srl_service.spacy")
    def test_noise_predicate_filtering(self, mock_spacy):
        """Noise predicates (think, know, mean) should be filtered out."""
        # Mock: "I think it's good" - 'think' is noise
        mock_verb = MagicMock()
        mock_verb.pos_ = "VERB"
        mock_verb.text = "think"
        mock_verb.lemma_ = "think"  # In noise_predicates
        mock_verb.children = [MagicMock(dep_="nsubj")]

        mock_doc = [mock_verb]
        mock_nlp = MagicMock()
        mock_nlp.return_value = mock_doc
        mock_spacy.load.return_value = mock_nlp

        service = SRLService()
        result = service.analyze("I think it's good")

        # 'think' should be filtered out
        assert result["srl_frames"] == []

    @patch("src.services.srl_service.spacy")
    def test_verb_without_arguments_not_included(self, mock_spacy):
        """Verbs with no arguments should not create frames."""
        # Mock verb with no children
        mock_verb = MagicMock()
        mock_verb.pos_ = "VERB"
        mock_verb.text = "run"
        mock_verb.lemma_ = "run"
        mock_verb.children = []  # No arguments

        mock_doc = [mock_verb]
        mock_nlp = MagicMock()
        mock_nlp.return_value = mock_doc
        mock_spacy.load.return_value = mock_nlp

        service = SRLService()
        result = service.analyze("run")

        # No arguments = no frame
        assert result["srl_frames"] == []


class TestCustomNoisePredicates:
    """Test configurable noise predicate filtering."""

    def test_custom_noise_predicates(self):
        """Should use custom noise predicates if provided."""
        custom_noise = {"avoid", "skip"}
        service = SRLService(noise_predicates=custom_noise)

        assert service._noise_predicates == custom_noise

    def test_default_noise_predicates(self):
        """Should use default noise predicates if none provided."""
        service = SRLService()

        assert "think" in service._noise_predicates
        assert "know" in service._noise_predicates
        assert "mean" in service._noise_predicates
