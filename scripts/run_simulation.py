#!/usr/bin/env python3
"""
Run a synthetic interview simulation.

Usage:
    python scripts/run_simulation.py headphones_mec health_conscious 10
    python scripts/run_simulation.py meal_planning_jtbd health_conscious 5
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging first (before importing other modules)
from src.core.logging import configure_logging

configure_logging()

from pathlib import Path
from src.services.simulation_service import SimulationService
from src.services.session_service import SessionService
from src.persistence.repositories.session_repo import SessionRepository
from src.persistence.repositories.graph_repo import GraphRepository
from src.api.dependencies import (
    get_shared_extraction_client,
    get_shared_generation_client,
)
from src.core.config import settings


async def main():
    if len(sys.argv) < 3:
        print("Usage: python run_simulation.py <concept_id> <persona_id> [max_turns]")
        print("\nAvailable concepts:")
        # List available concepts dynamically
        from pathlib import Path as P
        for cf in sorted(P("config/concepts").glob("*.yaml")):
            import yaml
            cd = yaml.safe_load(cf.read_text())
            print(f"  - {cd['id']} ({cd['methodology']})")
        print("\nAvailable personas:")
        from src.llm.prompts.synthetic import get_available_personas

        for pid, pname in get_available_personas().items():
            print(f"  - {pid}: {pname}")
        sys.exit(1)

    concept_id = sys.argv[1]
    persona_id = sys.argv[2]
    max_turns = int(sys.argv[3]) if len(sys.argv) > 3 else 10

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
    # Find the most recently written JSON for this simulation
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
