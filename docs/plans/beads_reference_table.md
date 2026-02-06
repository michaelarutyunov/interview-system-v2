# Beads Reference Table - Dual Graph Architecture Implementation

**Generated:** 2026-02-05
**Total Tasks:** 32 tasks across 5 phases

---

## Phase 1: SRL Preprocessing Infrastructure (6 tasks)

| Task ID | Model | Title | Dependencies | Status |
|---------|-------|-------|--------------|--------|
| interview-system-v2-gnkd | **Sonnet** | Create SRLService with spaCy integration | None | Ready |
| interview-system-v2-lr0k | **Sonnet** | Add SRLPreprocessingStage to pipeline | gnkd | Blocked |
| interview-system-v2-1ih9 | **Sonnet** | Modify ExtractionStage to inject SRL hints | lr0k | Blocked |
| interview-system-v2-mm6l | **Sonnet** | Add spaCy dependencies and configuration | None | Ready |
| interview-system-v2-6j7u | **Sonnet** | Update pipeline contracts for SRL stage | None | Ready |
| interview-system-v2-4foi | **Sonnet** | Test SRL with synthetic interview baseline | gnkd, lr0k, 1ih9, mm6l | Blocked |

**Execution Order:** gnkd + mm6l + 6j7u (parallel) → lr0k → 1ih9 → 4foi

---

## Phase 2: Canonical Slot Discovery Foundation (7 tasks)

| Task ID | Model | Title | Dependencies | Status |
|---------|-------|-------|--------------|--------|
| interview-system-v2-0kx2 | **Opus** | Design and create database migration for canonical slots | 4foi (Phase 1 complete) | Blocked |
| interview-system-v2-46hu | **Sonnet** | Create canonical graph domain models | None | Ready |
| interview-system-v2-eejs | **Sonnet** | Create CanonicalSlotRepository | 0kx2, 46hu | Blocked |
| interview-system-v2-lmyr | **Sonnet** | Create EmbeddingService with spaCy vectors | None | Ready |
| interview-system-v2-vub0 | **Opus** | Create CanonicalSlotService with LLM slot discovery | eejs, lmyr | Blocked |
| interview-system-v2-yuhv | **Sonnet** | Create SlotDiscoveryStage and wire into pipeline | vub0 | Blocked |
| interview-system-v2-j99v | **Sonnet** | Update pipeline contracts for slot discovery | None | Ready |

**Execution Order:** 0kx2 + 46hu + lmyr + j99v (parallel) → eejs → vub0 (Opus) → yuhv

---

## Phase 3: Dual Graph Integration (6 tasks)

| Task ID | Model | Title | Dependencies | Status |
|---------|-------|-------|--------------|--------|
| interview-system-v2-coxo | **Sonnet** | Add edge aggregation to GraphService | eejs, yuhv (Phase 2 complete) | Blocked |
| interview-system-v2-eusq | **Sonnet** | Modify GraphUpdateStage to aggregate canonical edges | coxo | Blocked |
| interview-system-v2-sa6h | **Sonnet** | Create CanonicalGraphService for state computation | None | Ready |
| interview-system-v2-ty40 | **Sonnet** | Modify StateComputationStage for dual graph states | sa6h | Blocked |
| interview-system-v2-ht0e | **Sonnet** | Modify NodeStateTracker to track canonical slots | None | Ready |
| interview-system-v2-0nl3 | **Sonnet** | Add JSON schema for dual-graph output | sa6h | Blocked |

**Execution Order:** coxo + sa6h + ht0e (parallel) → eusq (from coxo) + ty40 + 0nl3 (from sa6h)

---

## Phase 4: Signal Pool Extensions (3 tasks)

| Task ID | Model | Title | Dependencies | Status |
|---------|-------|-------|--------------|--------|
| interview-system-v2-3pna | **Sonnet** | Create canonical graph signal detectors | ty40 (Phase 3 complete) | Blocked |
| interview-system-v2-9x6n | **Sonnet** | Register canonical signals in registry | 3pna | Blocked |
| interview-system-v2-7k2a | **Sonnet** | Update methodology YAMLs with canonical signals (optional) | 9x6n | Blocked |

**Execution Order:** 3pna → 9x6n → 7k2a (sequential)

---

## Phase 5: Validation & Refinement (6 tasks)

| Task ID | Model | Title | Dependencies | Status |
|---------|-------|-------|--------------|--------|
| interview-system-v2-3ag1 | **Sonnet** | Run comprehensive synthetic interview test suite | 9x6n (Phase 4 complete) | Blocked |
| interview-system-v2-pong | **Sonnet** | Create metrics comparison script | None | Ready |
| interview-system-v2-817x | **Opus** | Manual quality review of canonical slots | 3ag1 | Blocked |
| interview-system-v2-gjb5 | **Sonnet** | Tune thresholds based on test results | 817x | Blocked |
| interview-system-v2-tdos | **Sonnet** | Update all documentation for dual-graph system | None | Ready |
| interview-system-v2-wjgf | **Sonnet** | Final validation and success criteria check | 3ag1, 817x, tdos | Blocked |

**Execution Order:** 3ag1 + pong + tdos (parallel) → 817x (Opus) → gjb5 → wjgf

---

## Complete Dependency Graph

```
Phase 1: SRL Preprocessing
├─ gnkd (Sonnet) ────────┐
├─ mm6l (Sonnet) ────────┤
├─ 6j7u (Sonnet) ────────┼──→ 4foi (Sonnet)
├─ lr0k (Sonnet) ────────┤
└─ 1ih9 (Sonnet) ────────┘
        ↓
Phase 2: Canonical Slots
├─ 0kx2 (Opus) ──────────┐
├─ 46hu (Sonnet) ────────┼──→ eejs (Sonnet) ───┐
├─ lmyr (Sonnet) ────────┘                      ├──→ vub0 (Opus) ──→ yuhv (Sonnet)
└─ j99v (Sonnet) ───────────────────────────────┘
        ↓
Phase 3: Dual Graph
├─ coxo (Sonnet) ────→ eusq (Sonnet)
├─ sa6h (Sonnet) ────→ ty40 (Sonnet)
├─                  └──→ 0nl3 (Sonnet)
└─ ht0e (Sonnet)
        ↓
Phase 4: Signals
└─ 3pna (Sonnet) ──→ 9x6n (Sonnet) ──→ 7k2a (Sonnet)
        ↓
Phase 5: Validation
├─ 3ag1 (Sonnet) ────────┐
├─ pong (Sonnet) ────────┤
├─ tdos (Sonnet) ────────┼──→ wjgf (Sonnet)
└─ 817x (Opus) ──────────┤
         └── gjb5 (Sonnet)
```

---

## Model Distribution Summary

| Model | Count | Task IDs |
|-------|-------|----------|
| **Sonnet 4.5** | 28 | gnkd, lr0k, 1ih9, mm6l, 6j7u, 4foi, 46hu, eejs, lmyr, yuhv, j99v, coxo, eusq, sa6h, ty40, ht0e, 0nl3, 3pna, 9x6n, 7k2a, 3ag1, pong, gjb5, tdos, wjgf |
| **Opus 4.6** | 4 | 0kx2, vub0, 817x, *(1 reserved for emergent complexity)* |

### Opus Usage Rationale

1. **interview-system-v2-0kx2** (Phase 2)
   - Database schema design
   - Architectural decision about canonical graph structure
   - Defines foundation for all subsequent work

2. **interview-system-v2-vub0** (Phase 2)
   - CanonicalSlotService implementation
   - Complex LLM prompting strategy
   - Slot merging via embedding similarity
   - Promotion logic with evidence thresholds
   - Most algorithmically complex component

3. **interview-system-v2-817x** (Phase 5)
   - Manual quality review of canonical slots
   - Qualitative assessment requiring judgment
   - False merge rate estimation
   - Recommendations for threshold tuning

4. **Reserved** - For emergent architectural decisions during implementation

---

## Currently Ready Tasks (No Dependencies)

**Phase 1 (3 ready):**
- interview-system-v2-gnkd (Sonnet) - CREATE SRLService
- interview-system-v2-mm6l (Sonnet) - ADD dependencies
- interview-system-v2-6j7u (Sonnet) - UPDATE contracts

**Phase 2 (3 ready):**
- interview-system-v2-46hu (Sonnet) - CREATE domain models
- interview-system-v2-lmyr (Sonnet) - CREATE EmbeddingService
- interview-system-v2-j99v (Sonnet) - UPDATE contracts

**Phase 3 (2 ready):**
- interview-system-v2-sa6h (Sonnet) - CREATE CanonicalGraphService
- interview-system-v2-ht0e (Sonnet) - MODIFY NodeStateTracker

**Phase 5 (2 ready):**
- interview-system-v2-pong (Sonnet) - CREATE metrics script
- interview-system-v2-tdos (Sonnet) - UPDATE documentation

**Total Ready:** 10 tasks (but should follow phase order)

---

## Critical Path (Longest Chain)

```
gnkd → lr0k → 1ih9 → 4foi → 0kx2 → eejs → vub0 → yuhv → coxo → eusq → 3pna → 9x6n → 3ag1 → 817x → gjb5 → wjgf
```

**Length:** 16 tasks
**Estimated Duration:** 7-10 sessions (assuming parallel work within phases)

---

## Quick Reference Commands

```bash
# View all open tasks
bd list --status=open

# View ready tasks (no blockers)
bd ready

# Show specific task details
bd show <task-id>

# Start working on a task
bd update <task-id> --status=in_progress

# Complete a task
bd close <task-id>

# View task dependencies
bd show <task-id> | grep -A 5 "Dependencies"

# Check project statistics
bd stats

# Sync with git
bd sync
```

---

## Task Naming Convention

All tasks follow the pattern: `[Model] Action Verb + Component/Target`

Examples:
- `[Sonnet] Create SRLService with spaCy integration`
- `[Opus] Design and create database migration for canonical slots`
- `[Sonnet] Modify ExtractionStage to inject SRL hints`

**Model Prefix:** Indicates which LLM to use for implementation
**Action Verb:** Create, Add, Modify, Update, Test, Review, Tune
**Component:** The specific file/service/module being changed

---

## Success Metrics Checkpoints

| Checkpoint | Phase | Metric | Target |
|------------|-------|--------|--------|
| **SRL Baseline** | Phase 1 | Edge/node ratio improvement | 0.53 → 0.7+ |
| **SRL Baseline** | Phase 1 | Latency increase | <200ms/turn |
| **Slots Created** | Phase 2 | Canonical slots exist | >0 with correct node_type |
| **Slots Mapped** | Phase 2 | Surface nodes mapped | 100% of nodes |
| **Edges Aggregated** | Phase 3 | Canonical edges created | Provenance tracked |
| **Dual States** | Phase 3 | Both states computed | Surface + canonical |
| **Signals Active** | Phase 4 | New signals detectable | Values returned |
| **Node Reduction** | Phase 5 | Canonical vs surface | 20-35% reduction |
| **Edge Improvement** | Phase 5 | Canonical edge/concept ratio | 1.5-2.5 |
| **False Merges** | Phase 5 | Manual review | <5% false positives |
| **Final Validation** | Phase 5 | All targets met | Ready for production |

---

## Notes

- **Dependencies are enforced** - Beads system won't allow starting blocked tasks
- **Phase order matters** - Each phase builds on previous phase
- **Parallel execution possible** - Tasks without dependencies can be worked simultaneously
- **Model allocation is advisory** - Can adjust if needed, but Opus recommended for noted tasks
- **Testing is integrated** - Each phase includes validation before moving forward
- **Documentation is tracked** - Contract updates are explicit tasks

---

**Last Updated:** 2026-02-05
**Status:** All tasks created and synced
**Ready to begin:** Phase 1 tasks (gnkd, mm6l, 6j7u)
