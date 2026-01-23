#!/usr/bin/env python3
"""
AST-based logging checker.

Ensures that:
1. Files using structlog have the proper import
2. Files using print() instead of logging are flagged
3. Files using get_logger() import from src.core.logging
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


class LoggingChecker(ast.NodeVisitor):
    """AST visitor to check for logging compliance."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.issues: List[Tuple[int, int, str]] = []
        self.has_logging_import = False
        self.has_get_logger = False
        self.uses_print = False
        self.uses_logging = False

    def visit_Import(self, node: ast.Import) -> None:
        """Check for 'import structlog'."""
        for alias in node.names:
            if alias.name == "structlog":
                self.has_logging_import = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check for 'from src.core.logging import get_logger'."""
        if node.module and "src.core.logging" in node.module:
            for alias in node.names:
                if alias.name == "get_logger":
                    self.has_get_logger = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check for print() calls and logging usage."""
        # Check for print() calls
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self.uses_print = True
            self.issues.append(
                (
                    node.lineno,
                    node.col_offset,
                    "print() call detected; use logging instead",
                )
            )

        # Check if logging methods are used
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ("debug", "info", "warning", "error", "critical", "exception"):
                self.uses_logging = True

        self.generic_visit(node)

    def report(self) -> List[str]:
        """Generate report of issues found."""
        report_lines = []

        # Check if file uses logging but doesn't have get_logger import
        if self.uses_logging and not self.has_get_logger:
            report_lines.append(
                f"{self.filepath}: Uses logging methods but missing "
                "'from src.core.logging import get_logger'"
            )

        # Report all issues
        for lineno, col_offset, message in self.issues:
            report_lines.append(f"{self.filepath}:{lineno}:{col_offset}: {message}")

        return report_lines


def check_file(filepath: Path) -> List[str]:
    """Check a single Python file for logging compliance."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        return [f"{filepath}: Error reading file: {e}"]

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        return [f"{filepath}: Syntax error: {e}"]

    checker = LoggingChecker(str(filepath))
    checker.visit(tree)
    return checker.report()


def should_check_file(filepath: Path) -> bool:
    """Determine if a file should be checked."""
    # Skip test files (they may use print for debugging)
    if "test" in filepath.stem:
        return False

    # Skip the checker script itself
    if filepath.name == "check_logging.py":
        return False

    # Only check Python files
    return filepath.suffix == ".py"


def main() -> int:
    """Main entry point."""
    if len(sys.argv) > 1:
        # Check specific files or directories
        paths = [Path(p) for p in sys.argv[1:]]
    else:
        # Check entire src directory
        src_dir = Path(__file__).parent.parent / "src"
        if not src_dir.exists():
            print(f"Error: {src_dir} does not exist", file=sys.stderr)
            return 1
        paths = [src_dir]

    all_issues: List[str] = []

    for path in paths:
        if path.is_file():
            if should_check_file(path):
                all_issues.extend(check_file(path))
        elif path.is_dir():
            for py_file in path.rglob("*.py"):
                if should_check_file(py_file):
                    all_issues.extend(check_file(py_file))

    if all_issues:
        for issue in sorted(all_issues):
            print(issue)
        print(f"\nFound {len(all_issues)} issue(s)")
        return 1
    else:
        print("No logging issues found")
        return 0


if __name__ == "__main__":
    sys.exit(main())
