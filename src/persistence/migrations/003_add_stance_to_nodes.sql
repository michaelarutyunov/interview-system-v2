-- Add stance attribute to kg_nodes table
-- Supports ADR-006: Enhanced Scoring and Strategy Architecture
-- Used by ContrastOpportunityScorer to detect opposite-stance nodes

-- Add stance column with default value 0 (neutral)
ALTER TABLE kg_nodes ADD COLUMN stance INTEGER NOT NULL DEFAULT 0 CHECK (stance IN (-1, 0, 1));

-- Add index for stance-based queries (used by contrast strategy)
CREATE INDEX IF NOT EXISTS idx_kg_nodes_stance ON kg_nodes(stance);
