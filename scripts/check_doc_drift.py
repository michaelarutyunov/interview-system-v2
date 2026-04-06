#!/usr/bin/env python3
"""Doc drift detector.

Warns when source files have been modified more than once since their
corresponding doc was last updated. One deferred update is acceptable;
two or more signals drift.

Also validates cross-references in the codified context infrastructure:
- CLAUDE.md key file map entries exist on disk
- Agent IDs in trigger table have corresponding AGENT.md files
- Context docs referenced in agent specs exist
- Source files referenced in context docs exist
- No context docs are orphaned (unreferenced by agents or CLAUDE.md)

Usage:
    uv run python scripts/check_doc_drift.py [--repo-root PATH] [--config PATH]

Exit code: always 0 (warns but never blocks).
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class DriftWarning:
    doc: str
    changes: list[str]  # list of "hash message" strings


@dataclass
class ReferenceWarning:
    category: str  # "missing_file", "missing_agent", "missing_doc", "orphan_doc"
    location: str  # where the reference is (e.g., "CLAUDE.md line 42")
    reference: str  # what's being referenced (e.g., file path, agent ID)
    detail: str  # additional context


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def run_git(cmd: list[str], cwd: Path) -> str:
    """Run a git command and return stdout. Returns empty string on error."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def get_last_doc_commit(doc: str, repo_root: Path) -> str | None:
    """Return the hash of the last commit that touched `doc`, or None."""
    output = run_git(["git", "log", "-1", "--format=%H", "--", doc], cwd=repo_root)
    result = output.strip()
    return result if result else None


def get_source_changes_since(
    since_commit: str | None,
    source_globs: list[str],
    repo_root: Path,
) -> list[str]:
    """Return commits that touched any source glob since `since_commit`.

    Returns empty list if since_commit is None (doc never committed).
    Each entry is "hash short-message".
    """
    if since_commit is None:
        return []

    cmd = [
        "git", "log",
        "--oneline",
        f"{since_commit}..HEAD",
        "--",
        *source_globs,
    ]
    output = run_git(cmd, cwd=repo_root)
    lines = [line for line in output.splitlines() if line.strip()]
    return lines


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def load_mapping(config_path: Path) -> list[dict]:
    """Load and return the mappings list from doc_mapping.yaml."""
    if not config_path.exists():
        raise FileNotFoundError(f"Mapping config not found: {config_path}")
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data.get("mappings", [])


def check_drift(
    mapping: list[dict],
    repo_root: Path,
) -> list[DriftWarning]:
    """Check all mappings for drift. Returns list of DriftWarning."""
    warnings: list[DriftWarning] = []

    for entry in mapping:
        doc = entry["doc"]
        sources = entry["sources"]

        last_doc_commit = get_last_doc_commit(doc, repo_root)
        if last_doc_commit is None:
            # Doc not yet committed — skip
            continue

        changes = get_source_changes_since(last_doc_commit, sources, repo_root)

        # Allow one deferred update; two or more is drift
        if len(changes) > 1:
            warnings.append(DriftWarning(doc=doc, changes=changes))

    return warnings


# ---------------------------------------------------------------------------
# Cross-reference validation (new for codified context principles)
# ---------------------------------------------------------------------------

def extract_agent_table_from_claude_md(claude_md_path: Path) -> list[dict]:
    """Extract the agent routing table from CLAUDE.md.

    Returns list of {"modifying": str, "agent": str} dicts.
    """
    if not claude_md_path.exists():
        return []

    content = claude_md_path.read_text()

    # Find the Agent Routing section
    match = re.search(r'## Agent Routing.*?(?=##|\Z)', content, re.DOTALL)
    if not match:
        return []

    table_text = match.group(0)

    # Parse the markdown table
    lines = table_text.split('\n')
    agents = []
    for line in lines:
        if '|' not in line or line.strip().startswith('|---'):
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 3:
            modifying = parts[1]
            agent = parts[2]
            if modifying and agent and not modifying.startswith('Modifying'):
                # Remove backticks and markdown formatting
                modifying_clean = modifying.replace('`', '').strip()
                agent_clean = agent.replace('`', '').strip()
                if agent_clean != "extraction-specialist (not yet created)":  # Skip uncreated agents
                    agents.append({"modifying": modifying_clean, "agent": agent_clean})

    return agents


def extract_context_docs_from_agent(agent_path: Path) -> list[str]:
    """Extract list of context docs referenced in an agent's AGENT.md."""
    if not agent_path.exists():
        return []

    content = agent_path.read_text()

    # Find Context Documents section
    match = re.search(r'## Context Documents.*?(?=##|\Z)', content, re.DOTALL)
    if not match:
        return []

    section_text = match.group(0)

    # Extract markdown links like `.claude/context/strategy-scoring.md`
    docs = re.findall(r'`(\.claude/context/[^`]+)`', section_text)
    # Also extract docs/ paths
    docs.extend(re.findall(r'`(docs/[^`]+)`', section_text))
    # Extract src/ file references
    docs.extend(re.findall(r'`(src/[^`]+)`', section_text))

    return docs


def extract_source_files_from_context_doc(doc_path: Path) -> list[str]:
    """Extract list of source files referenced in a context doc."""
    if not doc_path.exists():
        return []

    content = doc_path.read_text()

    # Extract code blocks with file paths (common pattern: "src/path/to/file.py")
    files = re.findall(r'(src/[a-zA-Z0-9_/]+\.py)', content)
    # Also look for config paths
    files.extend(re.findall(r'(config/[a-zA-Z0-9_/.]+\.yaml)', content))

    return list(set(files))


def check_agent_cross_references(repo_root: Path) -> list[ReferenceWarning]:
    """Validate agent table and agent spec cross-references."""
    warnings: list[ReferenceWarning] = []
    claude_md = repo_root / "CLAUDE.md"
    agents_dir = repo_root / ".claude" / "agents"

    # Get agent table from CLAUDE.md
    agent_entries = extract_agent_table_from_claude_md(claude_md)

    # Check each agent ID has a corresponding AGENT.md
    for entry in agent_entries:
        agent_id = entry["agent"]
        agent_md = agents_dir / agent_id / "AGENT.md"
        if not agent_md.exists():
            warnings.append(ReferenceWarning(
                category="missing_agent",
                location="CLAUDE.md Agent Routing table",
                reference=agent_id,
                detail=f"Agent ID '{agent_id}' listed in trigger table but .claude/agents/{agent_id}/AGENT.md does not exist"
            ))

    # Check all agent spec context doc references exist
    if agents_dir.exists():
        for agent_subdir in agents_dir.iterdir():
            agent_md = agent_subdir / "AGENT.md"
            if agent_md.exists():
                context_docs = extract_context_docs_from_agent(agent_md)
                for doc_ref in context_docs:
                    doc_path = repo_root / doc_ref
                    if not doc_path.exists():
                        warnings.append(ReferenceWarning(
                            category="missing_doc",
                            location=str(agent_md.relative_to(repo_root)),
                            reference=doc_ref,
                            detail=f"Agent spec references '{doc_ref}' but file does not exist"
                        ))

    return warnings


def check_context_doc_source_references(repo_root: Path, context_dir: Path) -> list[ReferenceWarning]:
    """Validate that source files referenced in context docs exist."""
    warnings: list[ReferenceWarning] = []

    if not context_dir.exists():
        return warnings

    for doc_file in context_dir.glob("*.md"):
        source_files = extract_source_files_from_context_doc(doc_file)
        for src_ref in source_files:
            src_path = repo_root / src_ref
            if not src_path.exists():
                warnings.append(ReferenceWarning(
                    category="missing_file",
                    location=str(doc_file.relative_to(repo_root)),
                    reference=src_ref,
                    detail=f"Context doc references '{src_ref}' but file does not exist"
                ))

    return warnings


def check_orphaned_context_docs(repo_root: Path, context_dir: Path) -> list[ReferenceWarning]:
    """Check for context docs not referenced by any agent or CLAUDE.md."""
    warnings: list[ReferenceWarning] = []

    if not context_dir.exists():
        return warnings

    # Collect all referenced context docs
    referenced_docs = set()

    # From CLAUDE.md
    claude_md = repo_root / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text()
        referenced_docs.update(re.findall(r'`(\.claude/context/[^`]+\.md)`', content))

    # From agent specs
    agents_dir = repo_root / ".claude" / "agents"
    if agents_dir.exists():
        for agent_subdir in agents_dir.iterdir():
            agent_md = agent_subdir / "AGENT.md"
            if agent_md.exists():
                docs = extract_context_docs_from_agent(agent_md)
                referenced_docs.update([d for d in docs if d.startswith(".claude/context/")])

    # Check for orphaned docs
    for doc_file in context_dir.glob("*.md"):
        rel_path = f".claude/context/{doc_file.name}"
        if rel_path not in referenced_docs:
            warnings.append(ReferenceWarning(
                category="orphan_doc",
                location=f".claude/context/{doc_file.name}",
                reference=doc_file.name,
                detail=f"Context doc exists but is not referenced by CLAUDE.md or any agent spec"
            ))

    return warnings


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def format_warnings(warnings: list[DriftWarning]) -> str:
    if not warnings:
        return ""
    lines = ["⚠  Doc drift detected:"]
    for w in warnings:
        lines.append(f"  {w.doc} — {len(w.changes)} source changes since last update")
        for change in w.changes:
            lines.append(f"    → {change}")
    return "\n".join(lines)


def format_reference_warnings(warnings: list[ReferenceWarning]) -> str:
    if not warnings:
        return ""
    lines = ["⚠  Cross-reference validation failed:"]
    for w in warnings:
        lines.append(f"  [{w.category}] {w.location}")
        lines.append(f"    → {w.detail}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Check for doc drift.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to doc_mapping.yaml (default: <repo-root>/.claude/doc_mapping.yaml)",
    )
    parser.add_argument(
        "--skip-xref",
        action="store_true",
        help="Skip cross-reference validation (only check doc drift)",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    config_path = args.config or repo_root / ".claude" / "doc_mapping.yaml"
    context_dir = repo_root / ".claude" / "context"

    # 1. Check doc drift (original functionality)
    try:
        mapping = load_mapping(config_path)
    except FileNotFoundError as e:
        print(f"check_doc_drift: {e}", file=sys.stderr)
        mapping = []

    drift_warnings = check_drift(mapping, repo_root)
    drift_output = format_warnings(drift_warnings)
    if drift_output:
        print(drift_output)

    # 2. Check cross-references (new for codified context principles)
    if not args.skip_xref:
        ref_warnings: list[ReferenceWarning] = []

        # Agent table and agent spec cross-references
        ref_warnings.extend(check_agent_cross_references(repo_root))

        # Context doc source file references
        ref_warnings.extend(check_context_doc_source_references(repo_root, context_dir))

        # Orphaned context docs
        ref_warnings.extend(check_orphaned_context_docs(repo_root, context_dir))

        ref_output = format_reference_warnings(ref_warnings)
        if ref_output:
            print(ref_output)

    sys.exit(0)  # Always exit 0 — warn, never block


if __name__ == "__main__":
    main()
