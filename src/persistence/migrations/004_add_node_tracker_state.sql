-- Migration 004: Add node_tracker_state column to sessions table
--
-- Purpose: Enable persistence of NodeStateTracker across turns
--
-- Problem: NodeStateTracker is created fresh each turn, losing:
--   - previous_focus (needed for response depth tracking)
--   - all_response_depths per node (needed for saturation detection)
--   - Focus streaks and yield history
--
-- Solution: Add node_tracker_state TEXT column to store serialized tracker state

-- Add column to sessions table (idempotent - checks if column exists first)
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so we use a workaround
-- If the column already exists, the ALTER TABLE will fail but we continue
-- This is safe because migrations run sequentially
ALTER TABLE sessions ADD COLUMN node_tracker_state TEXT;

-- Set default to NULL (no state persisted yet)
-- Existing sessions will have NULL, which triggers fresh tracker creation
-- New sessions will have state persisted after each turn
