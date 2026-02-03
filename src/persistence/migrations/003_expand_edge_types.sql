-- Migration 003: Expand edge_type CHECK constraint to support methodology-specific edge types
--
-- Problem: The original schema only allowed 'leads_to' and 'revises' edge types.
-- This was too restrictive for methodology-centric architecture where each methodology
-- defines its own semantic edge types.
--
-- JTBD methodology uses: triggered_by, enables, supports
-- Laddering uses: leads_to, revises
-- Means-End Chain uses: leads_to, means_to, ends_to
--
-- Solution: Expand the CHECK constraint to include all methodology-specific edge types.

-- SQLite doesn't support ALTER TABLE to modify CHECK constraints directly.
-- We need to recreate the table with the new constraint.

-- Step 1: Create a backup of the existing edges
CREATE TABLE IF NOT EXISTS kg_edges_backup AS SELECT * FROM kg_edges;

-- Step 2: Drop the old table
DROP TABLE IF EXISTS kg_edges;

-- Step 3: Recreate with expanded edge_type constraint
CREATE TABLE kg_edges (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Relationship
    source_node_id TEXT NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,
    target_node_id TEXT NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,
    edge_type TEXT NOT NULL CHECK (
        edge_type IN (
            -- Generic types (used across methodologies)
            'leads_to', 'revises',
            -- JTBD (Jobs to be Done) methodology types
            'occurs_in', 'triggered_by', 'addresses', 'conflicts_with', 'enables', 'supports',
            -- Means-End Chain methodology types
            'means_to', 'ends_to'
        )
    ),

    -- Confidence and properties
    confidence REAL NOT NULL DEFAULT 0.8 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    properties JSON DEFAULT '{}',

    -- Provenance
    source_utterance_ids JSON NOT NULL DEFAULT '[]',

    -- Temporal
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),

    -- Prevent duplicate edges
    UNIQUE(source_node_id, target_node_id, edge_type)
);

-- Step 4: Restore data from backup
INSERT INTO kg_edges SELECT * FROM kg_edges_backup;

-- Step 5: Recreate indexes
CREATE INDEX IF NOT EXISTS idx_kg_edges_session ON kg_edges(session_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_source ON kg_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_target ON kg_edges(target_node_id);

-- Step 6: Drop backup table
DROP TABLE kg_edges_backup;
