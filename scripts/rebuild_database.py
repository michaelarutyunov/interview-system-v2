#!/usr/bin/env python3
"""
Rebuild the database from scratch.

This script:
1. Deletes the existing database file
2. Re-initializes the database using init_database()

WARNING: This will DELETE ALL SESSION RECORDS.
Use only for development/testing purposes.
"""

import asyncio

import structlog

from src.core.config import settings
from src.persistence.database import init_database

log = structlog.get_logger(__name__)


async def rebuild_database() -> None:
    """
    Delete the existing database and recreate it.

    Returns:
        None
    """
    db_path = settings.database_path

    # Check if database exists
    if not db_path.exists():
        log.info(
            "database_not_found",
            path=str(db_path),
            message="No existing database to delete",
        )
    else:
        # Get file size for logging
        file_size = db_path.stat().st_size
        log.warning(
            "deleting_database",
            path=str(db_path),
            size_bytes=file_size,
            size_mb=f"{file_size / (1024 * 1024):.2f}",
        )

        # Delete the database
        db_path.unlink()
        log.info("database_deleted", path=str(db_path))

    # Re-initialize the database
    log.info("reinitializing_database", path=str(db_path))
    await init_database()

    # Verify the database was created
    if db_path.exists():
        new_size = db_path.stat().st_size
        log.info(
            "database_rebuilt",
            path=str(db_path),
            size_bytes=new_size,
            size_kb=f"{new_size / 1024:.2f}",
        )
    else:
        log.error("database_rebuild_failed", path=str(db_path))


if __name__ == "__main__":
    log.info("starting_database_rebuild")
    asyncio.run(rebuild_database())
    log.info("database_rebuild_complete")
