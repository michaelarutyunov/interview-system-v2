#!/usr/bin/env python3
"""Run a synthetic interview simulation.

Usage:
    uv run python scripts/run_simulation.py --concept glp1_food_mec --persona baseline_cooperative --max-turns 10

Legacy positional form (no longer supported):
    python scripts/run_simulation.py glp1_food_mec baseline_cooperative 10
    -> Use --concept, --persona, --max-turns flags instead.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging first (before importing other modules)
from src.core.logging import configure_logging  # noqa: E402

configure_logging()

from src.services.simulation_service import SimulationService  # noqa: E402
from src.services.session_service import SessionService  # noqa: E402
from src.persistence.repositories.session_repo import SessionRepository  # noqa: E402
from src.persistence.repositories.graph_repo import GraphRepository  # noqa: E402
from src.api.dependencies import (  # noqa: E402
    get_shared_extraction_client,
    get_shared_generation_client,
)
from src.core.config import settings  # noqa: E402


def _detect_legacy_positional_args() -> list[str] | None:
    """Detect if the user passed positional args instead of --flags."""
    if not sys.argv[1:]:
        return None
    # If first arg doesn't start with --, it's likely a positional invocation
    if not sys.argv[1].startswith("-"):
        return sys.argv[1:]
    return None


def _print_legacy_migration_hint(positional_args: list[str]) -> None:
    """Print a helpful migration hint for the legacy positional form."""
    concept = positional_args[0] if len(positional_args) > 0 else "<concept_id>"
    persona = positional_args[1] if len(positional_args) > 1 else "<persona_id>"
    max_turns = positional_args[2] if len(positional_args) > 2 else "10"
    print(
        f"Error: Positional args are no longer supported.\n"
        f"\n"
        f"Instead of:\n"
        f"  python scripts/run_simulation.py {concept} {persona} {max_turns}\n"
        f"\n"
        f"Use:\n"
        f"  uv run python scripts/run_simulation.py --concept {concept} --persona {persona} --max-turns {max_turns}\n"
        f"\n"
        f"Run with --help for full options."
    )
    sys.exit(2)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with help text listing available options."""
    concept_lines = []
    for cf in sorted(Path("config/concepts").glob("*.yaml")):
        import yaml

        cd = yaml.safe_load(cf.read_text())
        concept_lines.append(f"  {cd['id']:<40s} ({cd['methodology']})")

    persona_lines = []
    from src.llm.prompts.synthetic import get_available_personas

    for pid, pname in get_available_personas().items():
        persona_lines.append(f"  {pid:<30s} {pname}")

    epilog_parts = []
    if concept_lines:
        epilog_parts.append("Available concepts (see config/concepts/):")
        epilog_parts.extend(concept_lines)
    if persona_lines:
        epilog_parts.append("")
        epilog_parts.append("Available personas (see config/personas/):")
        epilog_parts.extend(persona_lines)

    parser = argparse.ArgumentParser(
        description="Run a single synthetic interview simulation.",
        epilog="\n".join(epilog_parts),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--concept",
        required=True,
        help="Concept ID (e.g. glp1_food_mec, zerofizz_beverage_mec)",
    )
    parser.add_argument(
        "--persona",
        required=True,
        help="Persona ID (e.g. baseline_cooperative, brief_responder)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Max interview turns (default: 10, matches SimulationService.DEFAULT_MAX_TURNS)",
    )
    return parser


async def main():
    # Detect legacy positional form before argparse sees it
    legacy_args = _detect_legacy_positional_args()
    if legacy_args is not None:
        _print_legacy_migration_hint(legacy_args)

    parser = _build_parser()
    args = parser.parse_args()

    concept_id = args.concept
    persona_id = args.persona
    max_turns = args.max_turns

    print("Running simulation:")
    print(f"  Concept: {concept_id}")
    print(f"  Persona: {persona_id}")
    print(f"  Max turns: {max_turns}")
    print()

    # Initialize repositories (need DB connection for GraphRepository)
    import aiosqlite

    db = await aiosqlite.connect(str(settings.database_path))
    session_repo = SessionRepository(str(settings.database_path))
    graph_repo = GraphRepository(db)

    # Create session service
    session_service = SessionService(
        session_repo=session_repo,
        graph_repo=graph_repo,
        extraction_llm_client=get_shared_extraction_client(),
        generation_llm_client=get_shared_generation_client(),
    )

    # Create simulation service
    simulation_service = SimulationService(session_service=session_service)

    # Run simulation
    result = await simulation_service.simulate_interview(
        concept_id=concept_id,
        persona_id=persona_id,
        max_turns=max_turns,
    )

    # Close database connection
    await db.close()

    # Print summary
    print(f"\n{'=' * 60}")
    print("SIMULATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total turns: {result.total_turns}")
    print(f"Status: {result.status}")
    print("\nGraph summary:")
    total_nodes = len(result.nodes)
    total_edges = len(result.edges)
    print(f"  Nodes: {total_nodes}")
    print(f"  Edges: {total_edges}")
    if total_nodes > 0:
        print(f"  Edge-to-node ratio: {total_edges / total_nodes:.2f}")

    print("\nStrategy sequence:")
    for turn in result.turns:
        term = f" ({turn.termination_reason})" if turn.termination_reason else ""
        print(f"  Turn {turn.turn_number}: {turn.strategy_selected or 'N/A'}{term}")

    print("\nJSON saved to: synthetic_interviews/")

    # Generate scoring decomposition CSV
    output_dir = Path("synthetic_interviews")
    json_files = sorted(
        output_dir.glob(f"*_{result.concept_id}_{result.persona_id}.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if json_files:
        from scripts.generate_scoring_csv import generate_scoring_csv

        csv_path = generate_scoring_csv(json_files[0])
        print(f"Scoring CSV saved to: {csv_path}")


if __name__ == "__main__":
    asyncio.run(main())
