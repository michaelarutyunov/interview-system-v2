-- Migration: Add scoring_candidates table for transparency UI
-- This table stores all (strategy, focus) candidates considered during turn processing,
-- enabling the UI to display why certain questions were selected over alternatives.

-- =============================================================================
-- Scoring Candidates (for transparency UI)
-- =============================================================================

CREATE TABLE IF NOT EXISTS scoring_candidates (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,

    -- Candidate identification
    strategy_id TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    focus_type TEXT NOT NULL,
    focus_description TEXT,

    -- Scoring results
    final_score REAL NOT NULL,
    is_selected INTEGER NOT NULL DEFAULT 0,
    vetoed_by TEXT,

    -- Tier 1 veto results (JSON)
    tier1_results JSON DEFAULT '[]',

    -- Tier 2 scorer breakdown (JSON)
    tier2_results JSON DEFAULT '[]',

    -- Reasoning trace
    reasoning TEXT,

    -- Timestamp
    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    -- Ensure uniqueness per turn
    UNIQUE(session_id, turn_number, strategy_id, focus_type)
);

CREATE INDEX IF NOT EXISTS idx_scoring_candidates_session ON scoring_candidates(session_id);
CREATE INDEX IF NOT EXISTS idx_scoring_candidates_turn ON scoring_candidates(session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_scoring_candidates_selected ON scoring_candidates(session_id, turn_number, is_selected);
