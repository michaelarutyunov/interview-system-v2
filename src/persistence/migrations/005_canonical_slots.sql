-- Migration 005: Canonical Slots Dual-Graph Architecture
--
-- Purpose: Add tables for the canonical (abstract) layer of the dual-graph.
-- Surface nodes (kg_nodes) map to canonical slots via embedding similarity.
-- Canonical edges aggregate surface edges between mapped slots.
--
-- Tables:
--   canonical_slots         - Abstract concept slots (candidate → active lifecycle)
--   surface_to_slot_mapping - Maps surface kg_nodes to canonical slots
--   canonical_edges         - Aggregated edges between canonical slots

PRAGMA foreign_keys = ON;

-- =============================================================================
-- Canonical Slots
-- =============================================================================

CREATE TABLE IF NOT EXISTS canonical_slots (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Identity
    slot_name TEXT NOT NULL,
    description TEXT,
    node_type TEXT NOT NULL,

    -- Lifecycle
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active')),
    support_count INTEGER NOT NULL DEFAULT 0,
    first_seen_turn INTEGER NOT NULL,
    promoted_turn INTEGER,

    -- Embedding: numpy array serialized via tobytes()
    -- Deserialize with np.frombuffer(blob, dtype=np.float32)
    embedding BLOB,

    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    promoted_at TEXT,

    UNIQUE(session_id, slot_name, node_type)
);

CREATE INDEX IF NOT EXISTS idx_canonical_slots_session ON canonical_slots(session_id);
CREATE INDEX IF NOT EXISTS idx_canonical_slots_status ON canonical_slots(session_id, status);
CREATE INDEX IF NOT EXISTS idx_canonical_slots_type ON canonical_slots(session_id, node_type);

-- =============================================================================
-- Surface-to-Slot Mapping
-- =============================================================================

CREATE TABLE IF NOT EXISTS surface_to_slot_mapping (
    surface_node_id TEXT PRIMARY KEY REFERENCES kg_nodes(id) ON DELETE CASCADE,
    canonical_slot_id TEXT NOT NULL REFERENCES canonical_slots(id) ON DELETE CASCADE,
    similarity_score REAL NOT NULL,
    assigned_turn INTEGER NOT NULL,
    assigned_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_surface_mapping_slot ON surface_to_slot_mapping(canonical_slot_id);

-- =============================================================================
-- Canonical Edges
-- =============================================================================

CREATE TABLE IF NOT EXISTS canonical_edges (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Relationship between canonical slots
    source_slot_id TEXT NOT NULL REFERENCES canonical_slots(id) ON DELETE CASCADE,
    target_slot_id TEXT NOT NULL REFERENCES canonical_slots(id) ON DELETE CASCADE,
    edge_type TEXT NOT NULL,

    -- Aggregation
    support_count INTEGER NOT NULL DEFAULT 1,
    surface_edge_ids TEXT NOT NULL DEFAULT '[]',

    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE(session_id, source_slot_id, target_slot_id, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_canonical_edges_session ON canonical_edges(session_id);
CREATE INDEX IF NOT EXISTS idx_canonical_edges_source ON canonical_edges(source_slot_id);
CREATE INDEX IF NOT EXISTS idx_canonical_edges_target ON canonical_edges(target_slot_id);
