"""
SQLite database connection management.

Provides async database initialization and connection factory.
Uses aiosqlite for async SQLite access.

Schema is defined in schema.sql (consolidated, no migrations).

In-memory mode: when DATABASE_PATH=:memory:, a single shared aiosqlite
connection is created at startup and reused for all requests. This ensures
all requests see the same in-memory database. Call close_shared_connection()
during application shutdown.
"""

import aiosqlite
from pathlib import Path
from typing import AsyncGenerator, Optional
import structlog

from src.core.config import settings

log = structlog.get_logger(__name__)

# Path to consolidated schema file
SCHEMA_FILE = Path(__file__).parent / "schema.sql"

# Shared connection for :memory: mode (None in file-based mode)
_shared_connection: Optional[aiosqlite.Connection] = None


def _is_memory_path(db_path: Path) -> bool:
    """Return True if the given path represents an in-memory SQLite database."""
    return str(db_path) == ":memory:"


async def _apply_schema(db: aiosqlite.Connection) -> None:
    """Apply the consolidated schema and idempotent migrations to a connection."""
    # Enable foreign keys
    await db.execute("PRAGMA foreign_keys = ON")

    # Enable WAL mode for better concurrent read performance
    await db.execute("PRAGMA journal_mode = WAL")

    # Apply consolidated schema (idempotent - CREATE TABLE IF NOT EXISTS)
    schema_sql = SCHEMA_FILE.read_text()
    await db.executescript(schema_sql)

    # Migrations for existing databases (idempotent)
    # Add embedding column to kg_nodes (surface semantic dedup)
    try:
        await db.execute("ALTER TABLE kg_nodes ADD COLUMN embedding BLOB")
        log.info("migration_applied", migration="kg_nodes_add_embedding")
    except Exception:
        pass  # Column already exists

    try:
        await db.execute(
            "ALTER TABLE kg_nodes ADD COLUMN source_quotes TEXT DEFAULT '[]'"
        )
        log.info("migration_applied", migration="kg_nodes_add_source_quotes")
    except Exception:
        pass  # Column already exists

    # Velocity tracking columns for saturation signals
    for col, ddl in [
        ("surface_velocity_peak", "REAL NOT NULL DEFAULT 0.0"),
        ("prev_surface_node_count", "INTEGER NOT NULL DEFAULT 0"),
        ("canonical_velocity_peak", "REAL NOT NULL DEFAULT 0.0"),
        ("prev_canonical_node_count", "INTEGER NOT NULL DEFAULT 0"),
        ("focus_history", "TEXT NOT NULL DEFAULT '[]'"),
    ]:
        try:
            await db.execute(f"ALTER TABLE sessions ADD COLUMN {col} {ddl}")
            log.info("migration_applied", migration=f"sessions_add_{col}")
        except Exception:
            pass  # Column already exists

    # Add 'triggers' edge type to kg_edges CHECK constraint (V2 JTBD methodology)
    # SQLite can't ALTER a CHECK constraint, so patch sqlite_master directly.
    try:
        cursor = await db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='kg_edges'"
        )
        row = await cursor.fetchone()
        if row and "'triggers'" not in row[0] and "'triggered_by'" in row[0]:
            new_sql = row[0].replace(
                "'occurs_in', 'triggered_by',",
                "'occurs_in', 'triggered_by', 'triggers',",
            )
            await db.execute("PRAGMA writable_schema = ON")
            await db.execute(
                "UPDATE sqlite_master SET sql = ? WHERE type='table' AND name='kg_edges'",
                (new_sql,),
            )
            await db.execute("PRAGMA writable_schema = OFF")
            log.info("migration_applied", migration="kg_edges_add_triggers_edge_type")
    except Exception as e:
        log.warning(
            "migration_skipped",
            migration="kg_edges_add_triggers_edge_type",
            error=str(e),
        )

    await db.commit()


async def init_database(db_path: Path | None = None) -> None:
    """
    Initialize database from consolidated schema.

    Args:
        db_path: Optional path to database file. Uses settings.database_path if not provided.

    Creates database file if it doesn't exist and applies consolidated schema.
    Existing databases are left intact (idempotent schema using CREATE TABLE IF NOT EXISTS).

    In :memory: mode, creates and retains a shared connection for the lifetime of
    the process. Subsequent calls to get_db() / get_db_connection() reuse it.
    """
    global _shared_connection

    db_path = db_path or settings.database_path

    log.info("initializing_database", path=str(db_path))

    if not SCHEMA_FILE.exists():
        log.error("schema_file_not_found", path=str(SCHEMA_FILE))
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE}")

    if _is_memory_path(db_path):
        # Create the single shared connection (kept open for the process lifetime)
        _shared_connection = await aiosqlite.connect(":memory:")
        _shared_connection.row_factory = aiosqlite.Row
        await _apply_schema(_shared_connection)
        # Do NOT close — it must persist for all future requests
        log.info("database_initialized", path=":memory:", mode="shared_connection")
        return

    # File-based mode: ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        await _apply_schema(db)

    log.info("database_initialized", path=str(db_path))


async def close_shared_connection() -> None:
    """
    Close the shared in-memory connection (if open).

    Call this during application shutdown when running in :memory: mode.
    Safe to call in file-based mode (no-op).
    """
    global _shared_connection
    if _shared_connection is not None:
        await _shared_connection.close()
        _shared_connection = None
        log.info("shared_connection_closed")


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Async generator that yields a database connection.

    Use as a FastAPI dependency:

        @app.get("/sessions")
        async def list_sessions(db: aiosqlite.Connection = Depends(get_db)):
            ...

    In file-based mode the connection is closed when the request completes.
    In :memory: mode the shared connection is yielded and NOT closed.
    """
    if _is_memory_path(settings.database_path):
        if _shared_connection is None:
            raise RuntimeError(
                "Shared in-memory connection not initialised. "
                "Call init_database() during application startup."
            )
        yield _shared_connection
        return

    db = await aiosqlite.connect(settings.database_path)

    try:
        # Enable foreign keys for this connection
        await db.execute("PRAGMA foreign_keys = ON")

        # Use Row factory for dict-like access
        db.row_factory = aiosqlite.Row

        yield db
    finally:
        await db.close()


async def get_db_connection() -> aiosqlite.Connection:
    """
    Get a single database connection (for non-FastAPI contexts).

    In file-based mode, caller is responsible for closing the connection:

        db = await get_db_connection()
        try:
            # use db
        finally:
            await db.close()

    In :memory: mode, the returned connection is the shared connection.
    Do NOT close it — it must remain open for the process lifetime.
    """
    if _is_memory_path(settings.database_path):
        if _shared_connection is None:
            raise RuntimeError(
                "Shared in-memory connection not initialised. "
                "Call init_database() during application startup."
            )
        return _shared_connection

    db = await aiosqlite.connect(settings.database_path)
    await db.execute("PRAGMA foreign_keys = ON")
    db.row_factory = aiosqlite.Row
    return db


async def check_database_health() -> dict:
    """
    Check database health for health endpoint.

    Returns:
        Dict with health status and basic metrics.
    """
    try:
        if _is_memory_path(settings.database_path):
            if _shared_connection is None:
                return {
                    "status": "unhealthy",
                    "error": "shared connection not initialised",
                }
            db = _shared_connection
            cursor = await db.execute("SELECT COUNT(*) FROM sessions")
            row = await cursor.fetchone()
            session_count = row[0] if row else 0
            cursor = await db.execute("PRAGMA integrity_check")
            integrity = await cursor.fetchone()
            return {
                "status": "healthy",
                "session_count": session_count,
                "integrity": integrity[0] if integrity else "unknown",
                "path": ":memory:",
            }

        async with aiosqlite.connect(settings.database_path) as db:
            # Check we can query
            cursor = await db.execute("SELECT COUNT(*) FROM sessions")
            row = await cursor.fetchone()
            session_count = row[0] if row else 0

            # Check integrity
            cursor = await db.execute("PRAGMA integrity_check")
            integrity = await cursor.fetchone()

            return {
                "status": "healthy",
                "session_count": session_count,
                "integrity": integrity[0] if integrity else "unknown",
                "path": str(settings.database_path),
            }
    except Exception as e:
        log.error("database_health_check_failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}
