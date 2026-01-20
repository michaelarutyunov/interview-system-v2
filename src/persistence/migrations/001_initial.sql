-- Interview System v2 - Initial Schema
-- Supports: sessions, conversational graph (utterances), knowledge graph (nodes/edges)

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

    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,

    -- Metrics (denormalized for quick access)
    turn_count INTEGER NOT NULL DEFAULT 0,
    coverage_score REAL DEFAULT 0.0
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

    -- Provenance: which utterances contributed to this node
    source_utterance_ids JSON NOT NULL DEFAULT '[]',

    -- Temporal (single timestamp, not bi-temporal)
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),

    -- Contradiction handling: if this node supersedes another
    superseded_by TEXT REFERENCES kg_nodes(id),

    -- Prevent duplicate nodes (same label+type) unless one supersedes
    UNIQUE(session_id, label, node_type, superseded_by)
);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_session ON kg_nodes(session_id);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON kg_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_label ON kg_nodes(session_id, label);

-- =============================================================================
-- Knowledge Graph Edges
-- =============================================================================

CREATE TABLE IF NOT EXISTS kg_edges (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Relationship
    source_node_id TEXT NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,
    target_node_id TEXT NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,
    edge_type TEXT NOT NULL CHECK (edge_type IN ('leads_to', 'revises')),

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
-- Scoring History (for diagnostics and debugging)
-- =============================================================================

CREATE TABLE IF NOT EXISTS scoring_history (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,

    -- Scores
    coverage_score REAL NOT NULL,
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
-- Concept Elements (for coverage tracking)
-- =============================================================================

CREATE TABLE IF NOT EXISTS concept_elements (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Element definition
    element_id TEXT NOT NULL,
    label TEXT NOT NULL,
    element_type TEXT NOT NULL DEFAULT 'attribute',
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),

    -- Coverage tracking
    is_covered INTEGER NOT NULL DEFAULT 0,
    covered_at TEXT,
    covered_by_node_id TEXT REFERENCES kg_nodes(id),

    UNIQUE(session_id, element_id)
);

CREATE INDEX IF NOT EXISTS idx_elements_session ON concept_elements(session_id);
CREATE INDEX IF NOT EXISTS idx_elements_covered ON concept_elements(session_id, is_covered);
