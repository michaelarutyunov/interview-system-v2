# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Turn numbering off-by-one error** (`context_loading_stage.py`): Corrected `turn_number` calculation to properly distinguish between completed turns (`turn_count`) and current turn (`turn_number`). The current turn is now correctly calculated as `turn_count + 1`.
  - **Impact**: Ensures accurate phase determination and proper interview termination logic
  - **Location**: `src/services/turn_pipeline/stages/context_loading_stage.py:115`

- **Pydantic v2 migration** (`strategy_selection_stage.py`): Replaced deprecated `.dict()` method with `.model_dump()` for serializing node data.
  - **Impact**: Maintains compatibility with Pydantic v2, preventing deprecation warnings
  - **Location**: `src/services/turn_pipeline/stages/strategy_selection_stage.py:49`

- **Graph edge attribute pollution** (`ui/components/graph.py`): Fixed structural metadata keys being added as edge attributes in NetworkX graph visualization.
  - **Impact**: Cleaner graph exports and proper separation of structural vs. data attributes
  - **Location**: `ui/components/graph.py:135-141`

### Documentation
- Updated `docs/data_flow_paths.md` to clarify the distinction between `turn_count` (completed turns) and `turn_number` (current turn)
- Updated `docs/pipeline_contracts.md` to note Pydantic v2 compatibility in StrategySelectionStage
- Added this CHANGELOG.md for tracking project changes

---

## [Previous Releases]

For changes prior to the current version, please refer to the git commit history:

```bash
git log --oneline --reverse
```

### Key Historical Features

#### Two-Tier Scoring System
- **Tier 1 (Hard Constraints)**: KnowledgeCeilingScorer, ElementExhaustedScorer, RecentRedundancyScorer
- **Tier 2 (Weighted Additive)**: CoverageGapScorer, AmbiguityScorer, DepthBreadthBalanceScorer, EngagementScorer, StrategyDiversityScorer, NoveltyScorer
- See `docs/adr/004-two-tier-scoring-system.md` for details

#### Turn Pipeline Architecture
- Modular 6-stage pipeline for processing each interview turn
- See `docs/adr/008-internal-api-boundaries-pipeline-pattern.md` for details

#### YAML-Based Methodology Schemas
- Flexible schema definitions for different research methodologies
- See `docs/adr/007-yaml-based-methodology-schema.md` for details
