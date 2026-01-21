"""
SQLite database connection management.

Provides async database initialization, connection factory, and migration support.
Uses aiosqlite for async SQLite access.
"""

import aiosqlite
from pathlib import Path
from typing import AsyncGenerator
import structlog

from src.core.config import settings

log = structlog.get_logger(__name__)

# Path to migrations directory
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def init_database(db_path: Path | None = None) -> None:
    """
    Initialize database and run migrations.

    Args:
        db_path: Optional path to database file. Uses settings.database_path if not provided.

    Creates the database file if it doesn't exist and applies all migrations.
    """
    db_path = db_path or settings.database_path

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    log.info("initializing_database", path=str(db_path))

    async with aiosqlite.connect(db_path) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")

        # Enable WAL mode for better concurrent read performance
        await db.execute("PRAGMA journal_mode = WAL")

        # Run migrations
        await _run_migrations(db)

        await db.commit()

    log.info("database_initialized", path=str(db_path))


async def _run_migrations(db: aiosqlite.Connection) -> None:
    """
    Run all SQL migration files in order.

    Migrations are .sql files in the migrations directory, sorted by name.
    Each migration is run in full (no partial migration tracking for simplicity).
    """
    if not MIGRATIONS_DIR.exists():
        log.warning("migrations_dir_not_found", path=str(MIGRATIONS_DIR))
        return

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    for migration_file in migration_files:
        log.debug("running_migration", file=migration_file.name)

        sql = migration_file.read_text()

        # Execute all statements in the migration
        await db.executescript(sql)

    log.info("migrations_complete", count=len(migration_files))


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
                "path": str(settings.database_path)
            }
    except Exception as e:
        log.error("database_health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }
