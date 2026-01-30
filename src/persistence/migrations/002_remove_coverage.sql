-- Migration 002: Remove coverage-driven mode infrastructure
-- The system is purely exploratory; coverage tracking was dead code.
--
-- For existing databases: drops coverage_score columns and concept_elements table.
-- For new databases: these columns/table don't exist (removed from 001_initial.sql),
-- so these statements will be no-ops or fail gracefully.

-- Drop concept_elements table (coverage tracking)
DROP TABLE IF EXISTS concept_elements;
