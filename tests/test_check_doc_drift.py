# tests/test_check_doc_drift.py
"""Tests for the doc drift detector (scripts/check_doc_drift.py).

We test the core logic functions in isolation by patching git calls.
"""

import pytest
from unittest.mock import patch
from pathlib import Path


from scripts.check_doc_drift import (
    load_mapping,
    get_last_doc_commit,
    get_source_changes_since,
    check_drift,
    DriftWarning,
)


# --- load_mapping ---


def test_load_mapping_returns_list_of_entries(tmp_path):
    config = tmp_path / "doc_mapping.yaml"
    config.write_text("""
mappings:
  - sources: ["src/foo.py"]
    doc: "docs/foo.md"
  - sources: ["src/bar/*.py"]
    doc: "docs/bar.md"
""")
    result = load_mapping(config)
    assert len(result) == 2
    assert result[0]["sources"] == ["src/foo.py"]
    assert result[0]["doc"] == "docs/foo.md"


def test_load_mapping_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_mapping(tmp_path / "nonexistent.yaml")


# --- get_last_doc_commit ---


def test_get_last_doc_commit_returns_hash():
    with patch("scripts.check_doc_drift.run_git") as mock_git:
        mock_git.return_value = "abc1234\n"
        result = get_last_doc_commit("docs/foo.md", repo_root=Path("."))
    assert result == "abc1234"
    mock_git.assert_called_once_with(
        ["git", "log", "-1", "--format=%H", "--", "docs/foo.md"], cwd=Path(".")
    )


def test_get_last_doc_commit_returns_none_for_untracked_doc():
    with patch("scripts.check_doc_drift.run_git") as mock_git:
        mock_git.return_value = ""
        result = get_last_doc_commit("docs/new.md", repo_root=Path("."))
    assert result is None


# --- get_source_changes_since ---


def test_get_source_changes_since_returns_commit_list():
    with patch("scripts.check_doc_drift.run_git") as mock_git:
        mock_git.return_value = "def5678 fix something\nabc1234 another fix\n"
        result = get_source_changes_since(
            since_commit="abc1234", source_globs=["src/foo.py"], repo_root=Path(".")
        )
    assert len(result) == 2
    assert result[0] == "def5678 fix something"


def test_get_source_changes_since_returns_empty_when_no_changes():
    with patch("scripts.check_doc_drift.run_git") as mock_git:
        mock_git.return_value = ""
        result = get_source_changes_since(
            since_commit="abc1234", source_globs=["src/foo.py"], repo_root=Path(".")
        )
    assert result == []


def test_get_source_changes_since_returns_empty_when_no_prior_commit():
    result = get_source_changes_since(
        since_commit=None, source_globs=["src/foo.py"], repo_root=Path(".")
    )
    assert result == []


# --- check_drift ---


def test_check_drift_no_warning_when_one_change():
    """One change since last doc update is acceptable — not drift."""
    mapping = [{"sources": ["src/foo.py"], "doc": "docs/foo.md"}]
    with (
        patch("scripts.check_doc_drift.get_last_doc_commit") as mock_doc,
        patch("scripts.check_doc_drift.get_source_changes_since") as mock_src,
    ):
        mock_doc.return_value = "abc1234"
        mock_src.return_value = ["def5678 one change"]
        warnings = check_drift(mapping, repo_root=Path("."))
    assert warnings == []


def test_check_drift_warning_when_two_or_more_changes():
    """Two or more changes without a doc update triggers a warning."""
    mapping = [{"sources": ["src/foo.py"], "doc": "docs/foo.md"}]
    with (
        patch("scripts.check_doc_drift.get_last_doc_commit") as mock_doc,
        patch("scripts.check_doc_drift.get_source_changes_since") as mock_src,
    ):
        mock_doc.return_value = "abc1234"
        mock_src.return_value = ["def5678 second change", "ccc9999 first change"]
        warnings = check_drift(mapping, repo_root=Path("."))
    assert len(warnings) == 1
    w = warnings[0]
    assert isinstance(w, DriftWarning)
    assert w.doc == "docs/foo.md"
    assert len(w.changes) == 2


def test_check_drift_no_warning_when_doc_never_committed():
    """Untracked doc (None commit) skips drift check — can't compare."""
    mapping = [{"sources": ["src/foo.py"], "doc": "docs/new.md"}]
    with patch("scripts.check_doc_drift.get_last_doc_commit") as mock_doc:
        mock_doc.return_value = None
        warnings = check_drift(mapping, repo_root=Path("."))
    assert warnings == []


def test_check_drift_multiple_mappings():
    """Each mapping checked independently."""
    mapping = [
        {"sources": ["src/foo.py"], "doc": "docs/foo.md"},
        {"sources": ["src/bar.py"], "doc": "docs/bar.md"},
    ]

    def mock_src(since_commit, source_globs, repo_root):
        if "src/foo.py" in source_globs:
            return ["c1 change", "c2 change"]  # drift
        return ["c3 change"]  # no drift

    with (
        patch("scripts.check_doc_drift.get_last_doc_commit") as mock_doc,
        patch("scripts.check_doc_drift.get_source_changes_since", side_effect=mock_src),
    ):
        mock_doc.return_value = "abc1234"
        warnings = check_drift(mapping, repo_root=Path("."))

    assert len(warnings) == 1
    assert warnings[0].doc == "docs/foo.md"
