-- Migration 006: Remove unused scoring_candidates table
-- Related to DPOS epic task jbog
--
-- The scoring_candidates table was never populated in production.
-- Scoring data is tracked in scoring_history instead.

DROP TABLE IF EXISTS scoring_candidates;

-- Note: Indexes are automatically dropped with the table:
-- - idx_scoring_candidates_session
-- - idx_scoring_candidates_turn
-- - idx_scoring_candidates_selected
