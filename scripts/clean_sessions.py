#!/usr/bin/env python3
"""Clean all sessions from the database."""

import asyncio
import aiosqlite

async def main():
    db_path = "data/interview.db"

    # First count
    db = await aiosqlite.connect(db_path)
    cur = await db.execute('SELECT COUNT(*) FROM sessions')
    row = await cur.fetchone()
    assert row is not None
    count = row[0]
    print(f"Found {count} sessions")

    if count == 0:
        print("No sessions to delete.")
        await db.close()
        return

    # Delete all sessions
    confirm = input(f"Delete all {count} sessions? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled.")
        await db.close()
        return

    await db.execute('DELETE FROM sessions')
    await db.execute('DELETE FROM utterances')
    await db.execute('DELETE FROM kg_nodes')
    await db.execute('DELETE FROM kg_edges')
    await db.execute('DELETE FROM scoring_history')
    await db.commit()

    # Verify
    cur = await db.execute('SELECT COUNT(*) FROM sessions')
    row = await cur.fetchone()
    assert row is not None
    remaining = row[0]

    print(f"✓ Deleted {count - remaining} sessions")
    print(f"✓ Remaining: {remaining}")

    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
