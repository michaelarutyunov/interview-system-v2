"""Eval harness: run a simulation matrix and record results to the scoreboard.

Usage:
    uv run python scripts/run_eval_matrix.py \
        --methodology mec \
        --concept zerofizz_beverage_mec \
        --personas baseline_cooperative,brief_responder \
        --replicates 10 \
        --max-turns 15 \
        --label "mec_baseline_2026_04"

Runs (persona × replicate) simulations, computes metrics, writes to eval_runs table.
"""

import argparse
import asyncio
import hashlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiosqlite

DB_PATH = str(Path(__file__).parent.parent / "data" / "interview.db")


def compute_config_hash(methodology_name: str) -> str:
    """Hash the methodology YAML content to produce a config_hash."""
    config_path = Path("config/methodologies") / f"{methodology_name}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Methodology config not found: {config_path}")
    content = config_path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]


def make_replicate_seed(persona_id: str, replicate_idx: int) -> str:
    """Deterministic seed from persona + replicate index."""
    return hashlib.sha256(f"{persona_id}:{replicate_idx}".encode()).hexdigest()[:12]


async def _add_max_chain_depth_if_needed(db_path: str) -> None:
    """Add max_chain_depth column to eval_runs if missing."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("PRAGMA table_info(eval_runs)")
        columns = {c[1] for c in await cursor.fetchall()}
        if "max_chain_depth" not in columns:
            await db.execute(
                "ALTER TABLE eval_runs ADD COLUMN max_chain_depth INTEGER DEFAULT 0"
            )
            await db.commit()


async def _migrate_eval_runs_if_needed(db_path: str) -> None:
    """Migrate eval_runs to include run_label in the unique constraint.

    Preserves all existing data by rewriting ids to include the label slug.
    """
    async with aiosqlite.connect(db_path) as db:
        # Check if eval_runs exists
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='eval_runs'"
        )
        if not await cursor.fetchone():
            return  # Table doesn't exist yet; new schema will be created below

        # Check if already migrated: run_label must be NOT NULL
        cursor = await db.execute("PRAGMA table_info(eval_runs)")
        columns = await cursor.fetchall()
        run_label_col = [c for c in columns if c[1] == "run_label"]
        if run_label_col and run_label_col[0][3] == 1:
            return  # notnull == 1, already migrated

        print("Migrating eval_runs schema to include run_label in unique constraint...")

        await db.executescript("""
            CREATE TABLE eval_runs_new (
                id TEXT PRIMARY KEY,
                config_hash TEXT NOT NULL,
                methodology TEXT NOT NULL,
                concept_id TEXT NOT NULL,
                persona_id TEXT NOT NULL,
                replicate_seed TEXT NOT NULL,
                run_label TEXT NOT NULL DEFAULT '',
                session_id TEXT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                node_count INTEGER DEFAULT 0,
                orphan_ratio REAL DEFAULT 0.0,
                canonical_slot_coverage REAL DEFAULT 0.0,
                total_turns INTEGER DEFAULT 0,
                structural_completeness INTEGER DEFAULT 0,
                max_chain_depth INTEGER DEFAULT 0,
                ontology_breadth REAL DEFAULT 0.0,
                exploration_depth REAL DEFAULT 0.0,
                error_flag INTEGER DEFAULT 0,
                error_message TEXT,
                UNIQUE(config_hash, persona_id, replicate_seed, run_label),
                FOREIGN KEY (config_hash) REFERENCES eval_config_registry(config_hash)
            );

            INSERT INTO eval_runs_new
            SELECT
                id || '_' || COALESCE(run_label, ''),
                config_hash, methodology, concept_id, persona_id, replicate_seed,
                COALESCE(run_label, ''),
                session_id, timestamp,
                node_count, orphan_ratio, canonical_slot_coverage, total_turns,
                structural_completeness, ontology_breadth, exploration_depth,
                error_flag, error_message
            FROM eval_runs;

            DROP TABLE eval_runs;
            ALTER TABLE eval_runs_new RENAME TO eval_runs;

            CREATE INDEX IF NOT EXISTS idx_eval_runs_config
                ON eval_runs(config_hash, methodology);
            CREATE INDEX IF NOT EXISTS idx_eval_runs_persona
                ON eval_runs(config_hash, persona_id);
        """)
        await db.commit()
        print("Migration complete.")


async def ensure_eval_tables(db_path: str) -> None:
    """Create eval_runs and eval_config_registry tables if they don't exist."""
    async with aiosqlite.connect(db_path) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS eval_config_registry (
                config_hash TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                methodology TEXT NOT NULL,
                yaml_path TEXT NOT NULL,
                registered_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS eval_runs (
                id TEXT PRIMARY KEY,
                config_hash TEXT NOT NULL,
                methodology TEXT NOT NULL,
                concept_id TEXT NOT NULL,
                persona_id TEXT NOT NULL,
                replicate_seed TEXT NOT NULL,
                run_label TEXT NOT NULL DEFAULT '',
                session_id TEXT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                node_count INTEGER DEFAULT 0,
                orphan_ratio REAL DEFAULT 0.0,
                canonical_slot_coverage REAL DEFAULT 0.0,
                total_turns INTEGER DEFAULT 0,
                structural_completeness INTEGER DEFAULT 0,
                max_chain_depth INTEGER DEFAULT 0,
                ontology_breadth REAL DEFAULT 0.0,
                exploration_depth REAL DEFAULT 0.0,
                error_flag INTEGER DEFAULT 0,
                error_message TEXT,
                UNIQUE(config_hash, persona_id, replicate_seed, run_label),
                FOREIGN KEY (config_hash) REFERENCES eval_config_registry(config_hash)
            );

            CREATE INDEX IF NOT EXISTS idx_eval_runs_config
                ON eval_runs(config_hash, methodology);
            CREATE INDEX IF NOT EXISTS idx_eval_runs_persona
                ON eval_runs(config_hash, persona_id);
        """)
        await db.commit()


async def register_config(
    db_path: str, config_hash: str, label: str, methodology: str
) -> None:
    """Register a config_hash with a human-readable label."""
    yaml_path = f"config/methodologies/{methodology}.yaml"
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT OR IGNORE INTO eval_config_registry
               (config_hash, label, methodology, yaml_path, registered_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                config_hash,
                label,
                methodology,
                yaml_path,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()


async def record_run(db_path: str, run: dict) -> None:
    """Insert a single eval run result."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO eval_runs
               (id, config_hash, methodology, concept_id, persona_id, replicate_seed,
                session_id, run_label, timestamp,
                node_count, orphan_ratio, canonical_slot_coverage, total_turns,
                structural_completeness, max_chain_depth, ontology_breadth, exploration_depth,
                error_flag, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run["id"],
                run["config_hash"],
                run["methodology"],
                run["concept_id"],
                run["persona_id"],
                run["replicate_seed"],
                run.get("session_id"),
                run.get("run_label", ""),
                datetime.now(timezone.utc).isoformat(),
                run.get("node_count", 0),
                run.get("orphan_ratio", 0.0),
                run.get("canonical_slot_coverage", 0.0),
                run.get("total_turns", 0),
                run.get("structural_completeness", 0),
                run.get("max_chain_depth", 0),
                run.get("ontology_breadth", 0.0),
                run.get("exploration_depth", 0.0),
                int(run.get("error_flag", False)),
                run.get("error_message"),
            ),
        )
        await db.commit()


def set_deterministic_temperatures() -> dict:
    """Force temperature=0 for extraction, slot_scoring, signal_scoring. Returns originals."""
    from src.core.config import interview_config

    originals = {}
    for call_type in ["extraction", "slot_scoring", "signal_scoring"]:
        config = getattr(interview_config.llm, call_type)
        originals[call_type] = config.temperature
        config.temperature = 0.0
    return originals


def restore_temperatures(originals: dict) -> None:
    """Restore original temperatures."""
    from src.core.config import interview_config

    for call_type, temp in originals.items():
        getattr(interview_config.llm, call_type).temperature = temp


def clear_llm_client_caches() -> None:
    """Clear LRU-cached LLM clients so next call uses updated temperatures."""
    from src.api.dependencies import (
        get_shared_extraction_client,
        get_shared_generation_client,
    )

    get_shared_extraction_client.cache_clear()
    get_shared_generation_client.cache_clear()


async def run_single_cell(
    concept_id: str,
    persona_id: str,
    replicate_seed: str,
    max_turns: int,
    semaphore: asyncio.Semaphore,
) -> dict:
    """Run a single simulation cell. Returns dict with session_id or error."""
    async with semaphore:
        db = None
        try:
            import aiosqlite
            from src.core.config import settings
            from src.services.simulation_service import SimulationService
            from src.services.session_service import SessionService
            from src.persistence.repositories.session_repo import SessionRepository
            from src.persistence.repositories.graph_repo import GraphRepository
            from src.api.dependencies import (
                get_shared_extraction_client,
                get_shared_generation_client,
            )

            db = await aiosqlite.connect(str(settings.database_path))
            session_repo = SessionRepository(str(settings.database_path))
            graph_repo = GraphRepository(db)
            session_service = SessionService(
                session_repo=session_repo,
                graph_repo=graph_repo,
                extraction_llm_client=get_shared_extraction_client(),
                generation_llm_client=get_shared_generation_client(),
            )
            sim_service = SimulationService(session_service=session_service)

            result = await sim_service.simulate_interview(
                concept_id=concept_id,
                persona_id=persona_id,
                max_turns=max_turns,
            )
            return {
                "session_id": result.session_id,
                "methodology": result.methodology,
                "error_flag": False,
            }
        except Exception as e:
            return {
                "session_id": None,
                "methodology": None,
                "error_flag": True,
                "error_message": str(e)[:500],
            }
        finally:
            if db:
                await db.close()


async def run_matrix(
    methodology: str,
    concept_id: str,
    personas: list[str],
    replicates: int,
    max_turns: int,
    label: str,
    max_parallel: int,
) -> None:
    """Run the full eval matrix and record results."""
    config_hash = compute_config_hash(methodology)

    print(f"Config hash: {config_hash}")
    print(f"Methodology: {methodology}")
    print(f"Concept: {concept_id}")
    print(f"Personas: {len(personas)}")
    print(f"Replicates: {replicates}")
    print(f"Total cells: {len(personas) * replicates}")
    print(f"Max parallel: {max_parallel}")
    print()

    await _migrate_eval_runs_if_needed(DB_PATH)
    await _add_max_chain_depth_if_needed(DB_PATH)
    await ensure_eval_tables(DB_PATH)
    await register_config(DB_PATH, config_hash, label, methodology)

    # Force temperature=0 for deterministic call types
    originals = set_deterministic_temperatures()
    clear_llm_client_caches()

    semaphore = asyncio.Semaphore(max_parallel)
    total = len(personas) * replicates
    completed = 0
    errors = 0
    start_time = time.time()

    try:
        tasks = []
        task_meta = []

        for persona_id in personas:
            for rep_idx in range(replicates):
                seed = make_replicate_seed(persona_id, rep_idx)
                tasks.append(
                    run_single_cell(concept_id, persona_id, seed, max_turns, semaphore)
                )
                task_meta.append((persona_id, seed))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            persona_id, seed = task_meta[i]

            if isinstance(result, Exception):
                run = {
                    "id": f"{config_hash}_{persona_id}_{seed}_{label}",
                    "config_hash": config_hash,
                    "methodology": methodology,
                    "concept_id": concept_id,
                    "persona_id": persona_id,
                    "replicate_seed": seed,
                    "run_label": label,
                    "error_flag": True,
                    "error_message": str(result)[:500],
                }
                errors += 1
            else:
                res: dict = result  # type: ignore[assignment]
                run_id = f"{config_hash}_{persona_id}_{seed}_{label}"
                run = {
                    "id": run_id,
                    "config_hash": config_hash,
                    "methodology": res.get("methodology", methodology),
                    "concept_id": concept_id,
                    "persona_id": persona_id,
                    "replicate_seed": seed,
                    "run_label": label,
                }
                run.update(res)

                if not res.get("error_flag") and res.get("session_id"):
                    from scripts.eval_metrics import compute_metrics

                    metrics = await compute_metrics(DB_PATH, res["session_id"])
                    run["node_count"] = metrics.node_count
                    run["orphan_ratio"] = metrics.orphan_ratio
                    run["canonical_slot_coverage"] = metrics.canonical_slot_coverage
                    run["total_turns"] = metrics.total_turns
                    run["structural_completeness"] = metrics.structural_completeness
                    run["max_chain_depth"] = metrics.max_chain_depth
                    run["ontology_breadth"] = metrics.ontology_breadth
                    run["exploration_depth"] = metrics.exploration_depth
                    if metrics.error_flag:
                        run["error_flag"] = True
                        run["error_message"] = "Metric computation failed"
                else:
                    errors += 1

            await record_run(DB_PATH, run)
            completed += 1
            if completed % 5 == 0 or completed == total:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                print(f"  [{completed}/{total}] {rate:.1f} runs/min, {errors} errors")

    finally:
        restore_temperatures(originals)
        clear_llm_client_caches()

    elapsed = time.time() - start_time
    print(f"\nDone: {completed} runs in {elapsed:.0f}s ({errors} errors)")


METHODOLOGY_MAP = {
    "mec": "means_end_chain_v2_strict",
    "mec_flex": "means_end_chain_v2_flex",
    "jtbd": "jobs_to_be_done_v2",
    "cit": "critical_incident_v2",
    "cjm": "customer_journey_mapping_v2",
    "rg": "repertory_grid_v2",
}


def main():
    parser = argparse.ArgumentParser(
        description="Run eval matrix for methodology tuning"
    )
    parser.add_argument(
        "--methodology",
        required=True,
        help="Methodology short name (mec, jtbd, cit, cjm, rg) or full YAML name",
    )
    parser.add_argument("--concept", required=True, help="Concept ID")
    parser.add_argument("--personas", required=True, help="Comma-separated persona IDs")
    parser.add_argument(
        "--replicates",
        type=int,
        default=10,
        help="Replicates per persona (default: 10)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=15,
        help="Max turns per simulation (default: 15)",
    )
    parser.add_argument("--label", required=True, help="Human-readable config label")
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=4,
        help="Max concurrent simulations (default: 4)",
    )
    args = parser.parse_args()

    methodology: str = METHODOLOGY_MAP.get(args.methodology, args.methodology)
    personas = [p.strip() for p in args.personas.split(",")]

    asyncio.run(
        run_matrix(
            methodology=methodology,
            concept_id=args.concept,
            personas=personas,
            replicates=args.replicates,
            max_turns=args.max_turns,
            label=args.label,
            max_parallel=args.max_parallel,
        )
    )


if __name__ == "__main__":
    main()
