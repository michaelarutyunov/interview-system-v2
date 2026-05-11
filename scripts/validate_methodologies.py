"""Validate all methodology YAML configs against the MethodologyRegistry.

Iterates every *.yaml under config/methodologies/ (excluding legacy/),
loads and validates each, then reports errors grouped by file.
Exits 0 if all configs are valid, 1 if any errors are found.
"""

import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config" / "methodologies"
    legacy_dir = config_dir / "legacy"

    yaml_files = sorted(
        f for f in config_dir.glob("*.yaml") if not f.is_relative_to(legacy_dir)
    )

    if not yaml_files:
        print("No methodology YAML files found.", file=sys.stderr)
        return 1

    from src.methodologies.registry import MethodologyRegistry

    any_errors = False

    for yaml_path in yaml_files:
        registry = MethodologyRegistry(config_dir=yaml_path.parent)
        try:
            registry.get_methodology(yaml_path.stem)
            print(f"OK  {yaml_path.name}")
        except ValueError as exc:
            any_errors = True
            print(f"FAIL {yaml_path.name}")
            for line in str(exc).splitlines():
                print(f"    {line}")

    return 1 if any_errors else 0


if __name__ == "__main__":
    sys.exit(main())
