"""
SQLite database connection management.

Provides async database initialization and connection factory.
Uses aiosqlite for async SQLite access.

Schema is defined in schema.sql (consolidated, no migrations).
"""

import aiosqlite
from pathlib import Path
from typing import AsyncGenerator
import structlog

from src.core.config import settings

log = structlog.get_logger(__name__)

# Path to consolidated schema file
SCHEMA_FILE = Path(__file__).parent / "schema.sql"


async def init_database(db_path: Path | None = None) -> None:
    """
    Initialize database from consolidated schema.

    Args:
        db_path: Optional path to database file. Uses settings.database_path if not provided.

    Creates database file if it doesn't exist and applies consolidated schema.
    Existing databases are left intact (idempotent schema using CREATE TABLE IF NOT EXISTS).
    """
    db_path = db_path or settings.database_path

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    log.info("initializing_database", path=str(db_path))

    if not SCHEMA_FILE.exists():
        log.error("schema_file_not_found", path=str(SCHEMA_FILE))
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE}")

    async with aiosqlite.connect(db_path) as db:
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

        await db.commit()

    log.info("database_initialized", path=str(db_path))


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Async generator that yields a database connection.

    Use as a FastAPI dependency:

        @app.get("/sessions")
        async def list_sessions(db: aiosqlite.Connection = Depends(get_db)):
            ...

    The connection is automatically closed when the request completes.
    """
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

    Caller is responsible for closing the connection:

        db = await get_db_connection()
        try:
            # use db
        finally:
            await db.close()
    """
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
