-- Interview System v2 - Consolidated Schema
-- This file represents the final state after all migrations.
-- Replaces the migration-based approach with a single schema definition.
--
-- To apply: sqlite3 interview.db < schema.sql
-- Or delete migrations/ and this becomes init_database schema

PRAGMA foreign_keys = ON;

-- =============================================================================
-- Sessions
-- =============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    methodology TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    concept_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),

    -- Configuration
    config JSON NOT NULL DEFAULT '{}',

    -- Node state tracker (persisted across turns)
    node_tracker_state TEXT,

    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,

    -- Metrics (denormalized for quick access)
    turn_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at);

-- =============================================================================
-- Utterances (Conversational Graph)
-- =============================================================================

CREATE TABLE IF NOT EXISTS utterances (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    speaker TEXT NOT NULL CHECK (speaker IN ('system', 'user')),

    -- Content
    text TEXT NOT NULL,

    -- Extracted metadata
    discourse_markers JSON DEFAULT '[]',

    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE(session_id, turn_number, speaker)
);

CREATE INDEX IF NOT EXISTS idx_utterances_session ON utterances(session_id);
CREATE INDEX IF NOT EXISTS idx_utterances_turn ON utterances(session_id, turn_number);

-- =============================================================================
-- Knowledge Graph Nodes
-- =============================================================================

CREATE TABLE IF NOT EXISTS kg_nodes (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Content
    label TEXT NOT NULL,
    node_type TEXT NOT NULL,

    -- Confidence and properties
    confidence REAL NOT NULL DEFAULT 0.8 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    properties JSON DEFAULT '{}',

    -- Stance attribute (ADR-006: Enhanced Scoring and Strategy Architecture)
    -- Used by ContrastOpportunityScorer to detect opposite-stance nodes
    stance INTEGER NOT NULL DEFAULT 0 CHECK (stance IN (-1, 0, 1)),

    -- Provenance: which utterances contributed to this node
    source_utterance_ids JSON NOT NULL DEFAULT '[]',

    -- Temporal (single timestamp, not bi-temporal)
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),

    -- Embedding: numpy float32 array serialized via tobytes()
    -- Model: all-MiniLM-L6-v2 (384-dim). Deserialize with np.frombuffer(blob, dtype=np.float32)
    -- Used for surface semantic dedup (threshold 0.80, same node_type required)
    embedding BLOB,

    -- Contradiction handling: if this node supersedes another
    superseded_by TEXT REFERENCES kg_nodes(id),

    -- Prevent duplicate nodes (same label+type) unless one supersedes
    UNIQUE(session_id, label, node_type, superseded_by)
);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_session ON kg_nodes(session_id);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON kg_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_label ON kg_nodes(session_id, label);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_stance ON kg_nodes(stance);

-- =============================================================================
-- Knowledge Graph Edges
-- =============================================================================

CREATE TABLE IF NOT EXISTS kg_edges (
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

CREATE INDEX IF NOT EXISTS idx_kg_edges_session ON kg_edges(session_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_source ON kg_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_target ON kg_edges(target_node_id);

-- =============================================================================
-- Canonical Slots (Dual-Graph Architecture - Phase 2)
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

    -- Embedding: numpy float32 array serialized via tobytes()
    -- Model: all-MiniLM-L6-v2 (384-dim). Deserialize with np.frombuffer(blob, dtype=np.float32)
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
-- Surface-to-Slot Mapping (Dual-Graph Architecture)
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
-- Canonical Edges (Dual-Graph Architecture)
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

-- =============================================================================
-- Scoring History (for diagnostics and debugging)
-- =============================================================================

CREATE TABLE IF NOT EXISTS scoring_history (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,

    -- Scores
    depth_score REAL NOT NULL,
    saturation_score REAL NOT NULL,
    novelty_score REAL DEFAULT NULL,
    richness_score REAL DEFAULT NULL,

    -- Strategy selection
    strategy_selected TEXT NOT NULL,
    strategy_reasoning TEXT,

    -- All scorer outputs (for debugging)
    scorer_details JSON DEFAULT '{}',

    -- Timestamp
    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE(session_id, turn_number)
);

CREATE INDEX IF NOT EXISTS idx_scoring_session ON scoring_history(session_id);

-- =============================================================================
-- Qualitative Signals (LLM-extracted diagnostic signals)
-- =============================================================================

CREATE TABLE IF NOT EXISTS qualitative_signals (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,

    -- Signal extraction metadata
    llm_model TEXT,
    extraction_latency_ms INTEGER,
    extraction_errors TEXT,  -- JSON array of error messages

    -- Individual signals (JSON)
    uncertainty_signal TEXT,  -- JSON or NULL
    reasoning_signal TEXT,    -- JSON or NULL
    emotional_signal TEXT,   -- JSON or NULL
    contradiction_signal TEXT,  -- JSON or NULL
    knowledge_ceiling_signal TEXT,  -- JSON or NULL
    concept_depth_signal TEXT,  -- JSON or NULL

    -- Timestamp
    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    -- Ensure one entry per turn
    UNIQUE(session_id, turn_number)
);

CREATE INDEX IF NOT EXISTS idx_qualitative_signals_session ON qualitative_signals(session_id);
CREATE INDEX IF NOT EXISTS idx_qualitative_signals_turn ON qualitative_signals(session_id, turn_number);
