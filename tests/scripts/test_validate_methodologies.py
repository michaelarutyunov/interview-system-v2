"""Tests for scripts/validate_methodologies.py."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "validate_methodologies.py"
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "methodologies"


def _run_validator(config_dir: Path) -> subprocess.CompletedProcess:
    """Run the validator script with a custom config dir via monkeypatching."""
    # We invoke the script's main() directly by patching the config_dir via
    # an env var isn't available. Instead, invoke as subprocess with a small
    # wrapper that overrides the glob path.
    code = f"""
import sys
from pathlib import Path

project_root = Path({str(SCRIPT.parent.parent)!r})
config_dir = Path({str(config_dir)!r})

# Replicate main() logic but with fixture config dir
from src.methodologies.registry import MethodologyRegistry

yaml_files = sorted(config_dir.glob("*.yaml"))
any_errors = False
for yaml_path in yaml_files:
    registry = MethodologyRegistry(config_dir=yaml_path.parent)
    try:
        registry.get_methodology(yaml_path.stem)
    except ValueError as exc:
        any_errors = True
        print(f"FAIL {{yaml_path.name}}")
        for line in str(exc).splitlines():
            print(f"    {{line}}")

sys.exit(1 if any_errors else 0)
"""
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(SCRIPT.parent.parent),
    )


def test_bad_signal_key_exits_nonzero():
    """Validator exits 1 when a YAML has an unknown signal key."""
    result = _run_validator(FIXTURES_DIR)
    assert result.returncode != 0, (
        f"Expected non-zero exit for bad fixture, got 0.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert "unknown signal weight key" in combined or "FAIL" in combined, (
        f"Expected error message in output.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_valid_configs_exit_zero():
    """Validator exits 0 for all current production methodology configs."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(SCRIPT.parent.parent),
    )
    assert result.returncode == 0, (
        f"Expected exit 0 for valid configs.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
