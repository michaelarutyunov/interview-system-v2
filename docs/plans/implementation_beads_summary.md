# Implementation Beads Summary - Dual Graph Architecture

**Generated:** 2026-02-05
**Status:** Ready for execution
**Total Tasks:** 32 tasks across 5 epics

---

## Epic Overview

| Epic ID | Phase | Title | Tasks | Status |
|---------|-------|-------|-------|--------|
| interview-system-v2-s18h | Phase 1 | SRL Preprocessing Infrastructure | 6 | Ready |
| interview-system-v2-qsjj | Phase 2 | Canonical Slot Discovery Foundation | 7 | Blocked by Phase 1 |
| interview-system-v2-egxc | Phase 3 | Dual Graph Integration | 6 | Blocked by Phase 2 |
| interview-system-v2-ssjc | Phase 4 | Signal Pool Extensions | 3 | Blocked by Phase 3 |
| interview-system-v2-l0h9 | Phase 5 | Validation & Refinement | 6 | Blocked by Phase 4 |

---

## Phase 1: SRL Preprocessing Infrastructure (6 tasks)

**Epic:** interview-system-v2-s18h
**Duration:** 1-2 sessions | **Risk:** LOW

### Tasks

| ID | Model | Title | Dependencies |
|----|-------|-------|--------------|
| interview-system-v2-gnkd | **Sonnet** | Create SRLService with spaCy integration | None (START HERE) |
| interview-system-v2-lr0k | **Sonnet** | Add SRLPreprocessingStage to pipeline | gnkd |
| interview-system-v2-1ih9 | **Sonnet** | Modify ExtractionStage to inject SRL hints | lr0k |
| interview-system-v2-mm6l | **Sonnet** | Add spaCy dependencies and configuration | None (parallel) |
| interview-system-v2-6j7u | **Sonnet** | Update pipeline contracts for SRL stage | None (parallel) |
| interview-system-v2-4foi | **Sonnet** | Test SRL with synthetic interview baseline | gnkd, lr0k, 1ih9, mm6l |

### Execution Order
1. **Start:** gnkd, mm6l, 6j7u (parallel)
2. **After gnkd:** lr0k
3. **After lr0k:** 1ih9
4. **After all:** 4foi (testing)

---

## Phase 2: Canonical Slot Discovery Foundation (7 tasks)

**Epic:** interview-system-v2-qsjj
**Duration:** 2-3 sessions | **Risk:** MEDIUM

### Tasks

| ID | Model | Title | Dependencies |
|----|-------|-------|--------------|
| interview-system-v2-0kx2 | **Opus** | Design and create database migration for canonical slots | Phase 1 complete (4foi) |
| interview-system-v2-46hu | **Sonnet** | Create canonical graph domain models | None (parallel to 0kx2) |
| interview-system-v2-eejs | **Sonnet** | Create CanonicalSlotRepository | 0kx2, 46hu |
| interview-system-v2-lmyr | **Sonnet** | Create EmbeddingService with spaCy vectors | None (parallel) |
| interview-system-v2-vub0 | **Opus** | Create CanonicalSlotService with LLM slot discovery | eejs, lmyr |
| interview-system-v2-yuhv | **Sonnet** | Create SlotDiscoveryStage and wire into pipeline | vub0 |
| interview-system-v2-j99v | **Sonnet** | Update pipeline contracts for slot discovery | None (parallel) |

### Execution Order
1. **Start:** 0kx2, 46hu, lmyr, j99v (parallel)
2. **After 0kx2 + 46hu:** eejs
3. **After eejs + lmyr:** vub0 (OPUS - complex logic)
4. **After vub0:** yuhv

### Model Allocation Rationale
- **Opus for 0kx2:** Schema design is architectural decision
- **Opus for vub0:** Complex LLM prompting, slot merging, promotion logic
- **Sonnet for rest:** Straightforward implementation following patterns

---

## Phase 3: Dual Graph Integration (6 tasks)

**Epic:** interview-system-v2-egxc
**Duration:** 1-2 sessions | **Risk:** MEDIUM

### Tasks

| ID | Model | Title | Dependencies |
|----|-------|-------|--------------|
| interview-system-v2-coxo | **Sonnet** | Add edge aggregation to GraphService | Phase 2 complete (yuhv) |
| interview-system-v2-eusq | **Sonnet** | Modify GraphUpdateStage to aggregate canonical edges | coxo |
| interview-system-v2-sa6h | **Sonnet** | Create CanonicalGraphService for state computation | None (parallel to coxo) |
| interview-system-v2-ty40 | **Sonnet** | Modify StateComputationStage for dual graph states | sa6h |
| interview-system-v2-ht0e | **Sonnet** | Modify NodeStateTracker to track canonical slots | None (parallel) |
| interview-system-v2-0nl3 | **Sonnet** | Add JSON schema for dual-graph output | sa6h |

### Execution Order
1. **Start:** coxo, sa6h, ht0e (parallel)
2. **After coxo:** eusq
3. **After sa6h:** ty40, 0nl3

### Model Allocation Rationale
- **All Sonnet:** Straightforward implementation, clear patterns established

---

## Phase 4: Signal Pool Extensions (3 tasks)

**Epic:** interview-system-v2-ssjc
**Duration:** 1 session | **Risk:** LOW

### Tasks

| ID | Model | Title | Dependencies |
|----|-------|-------|--------------|
| interview-system-v2-3pna | **Sonnet** | Create canonical graph signal detectors | Phase 3 complete (ty40) |
| interview-system-v2-9x6n | **Sonnet** | Register canonical signals in registry | 3pna |
| interview-system-v2-7k2a | **Sonnet** | Update methodology YAMLs with canonical signals (optional) | 9x6n |

### Execution Order
1. **Sequential:** 3pna → 9x6n → 7k2a

### Model Allocation Rationale
- **All Sonnet:** Simple signal detector pattern, straightforward registration

---

## Phase 5: Validation & Refinement (6 tasks)

**Epic:** interview-system-v2-l0h9
**Duration:** 1-2 sessions | **Risk:** LOW

### Tasks

| ID | Model | Title | Dependencies |
|----|-------|-------|--------------|
| interview-system-v2-3ag1 | **Sonnet** | Run comprehensive synthetic interview test suite | Phase 4 complete (9x6n) |
| interview-system-v2-pong | **Sonnet** | Create metrics comparison script | None (parallel) |
| interview-system-v2-817x | **Opus** | Manual quality review of canonical slots | 3ag1 |
| interview-system-v2-gjb5 | **Sonnet** | Tune thresholds based on test results | 817x |
| interview-system-v2-tdos | **Sonnet** | Update all documentation for dual-graph system | None (parallel) |
| interview-system-v2-wjgf | **Sonnet** | Final validation and success criteria check | 3ag1, 817x, tdos |

### Execution Order
1. **Start:** 3ag1, pong, tdos (parallel)
2. **After 3ag1:** 817x (OPUS - qualitative assessment)
3. **After 817x:** gjb5
4. **After 3ag1 + 817x + tdos:** wjgf

### Model Allocation Rationale
- **Opus for 817x:** Qualitative assessment requires judgment and analysis
- **Sonnet for rest:** Testing, scripting, documentation - straightforward

---

## Model Allocation Summary

| Model | Task Count | Use Cases |
|-------|-----------|-----------|
| **Sonnet 4.5** | 28 tasks | Standard implementation, following established patterns |
| **Opus 4.6** | 4 tasks | Architectural decisions, complex logic, qualitative analysis |

### Opus Tasks (4)
1. **interview-system-v2-0kx2** - Database schema design (architectural)
2. **interview-system-v2-vub0** - CanonicalSlotService with LLM slot discovery (complex prompting/merging)
3. **interview-system-v2-817x** - Manual quality review (qualitative assessment)
4. *(Note: 4th could be added if architectural decisions arise during implementation)*

### Sonnet Tasks (28)
- All other implementation tasks
- Follows established patterns from existing codebase
- Clear acceptance criteria
- Testable and verifiable

---

## Dependency Chain Overview

```
Phase 1 (SRL)
  ├─ gnkd (SRLService) ────┐
  ├─ mm6l (Dependencies) ──┼─→ 4foi (Testing)
  ├─ 6j7u (Contracts) ─────┤
  ├─ lr0k (Stage) ─────────┤
  └─ 1ih9 (Extraction) ────┘
         ↓
Phase 2 (Canonical Slots)
  ├─ 0kx2 (Migration) ─────┐
  ├─ 46hu (Models) ────────┼─→ eejs (Repository) ─┐
  ├─ lmyr (Embeddings) ────┘                       ├─→ vub0 (Service) ─→ yuhv (Stage)
  └─ j99v (Contracts) ─────────────────────────────┘
         ↓
Phase 3 (Dual Graph)
  ├─ coxo (Edge Agg) ──→ eusq (GraphUpdate)
  ├─ sa6h (CanonGraphSvc) ──→ ty40 (StateComp)
  ├─ ht0e (Tracker) ────────────┘
  └─ 0nl3 (JSON) ───────────────┘
         ↓
Phase 4 (Signals)
  └─ 3pna (Detectors) ──→ 9x6n (Registry) ──→ 7k2a (YAMLs)
         ↓
Phase 5 (Validation)
  ├─ 3ag1 (Tests) ──────┐
  ├─ pong (Script) ─────┤
  ├─ tdos (Docs) ───────┼─→ wjgf (Final Validation)
  └─ 817x (Review) ─────┤
         └─ gjb5 (Tune) ┘
```

---

## Ready-to-Start Tasks (No Dependencies)

Run `bd ready` to see all tasks ready to start. Currently:

**Phase 1 (3 tasks ready):**
- interview-system-v2-gnkd (Sonnet)
- interview-system-v2-mm6l (Sonnet)
- interview-system-v2-6j7u (Sonnet)

---

## Verification Checklist

Before considering each phase complete:

### Phase 1
- [ ] SRL runs without errors, adds <200ms latency
- [ ] Edge/node ratio shows any improvement
- [ ] Pipeline contracts updated

### Phase 2
- [ ] Database migration runs successfully
- [ ] Canonical slots created with correct node_type
- [ ] Surface-to-slot mappings correct
- [ ] Pipeline runs without errors

### Phase 3
- [ ] Canonical edges aggregated with provenance
- [ ] Both graph states computed correctly
- [ ] JSON output includes dual-graph structure
- [ ] NodeStateTracker uses canonical slots

### Phase 4
- [ ] New signals return reasonable values
- [ ] Signals registered and detectable
- [ ] Strategy selection uses canonical signals (if YAMLs updated)

### Phase 5
- [ ] All 4 test scenarios complete
- [ ] Metrics meet targets (20-35% node reduction, etc.)
- [ ] False merge rate <5%
- [ ] Documentation updated
- [ ] Success criteria validated

---

## Success Metrics (Phase 5 Targets)

| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| **Node Reduction** | 0% | 20-35% | HIGH |
| **Surface Edge/Node Ratio** | 0.53 | 1.0+ (target: 2-3) | HIGH |
| **Canonical Edge/Concept Ratio** | N/A | 1.5-2.5 | HIGH |
| **Surface Orphan %** | 26% | <15% | MEDIUM |
| **Canonical Orphan %** | N/A | <10% | MEDIUM |
| **Latency Increase** | 0ms | <3s per turn | MEDIUM |
| **False Merge Rate** | N/A | <5% | HIGH |

---

## Notes

- **Model allocation is in task titles:** `[Sonnet]` or `[Opus]`
- **Dependencies prevent out-of-order work:** beads system enforces dependency chain
- **Priority P2:** Medium priority for all tasks (consistent across project)
- **Priority P3:** Lower priority for optional/tuning tasks
- **Parallel execution:** Tasks without dependencies can be worked simultaneously
- **Inter-phase blocks:** Each phase waits for previous phase completion

---

## Next Steps

1. **Review this summary** - Ensure tasks are clear and actionable
2. **Start Phase 1** - Begin with ready tasks (gnkd, mm6l, 6j7u)
3. **Use `bd ready`** - Check available tasks at any time
4. **Use `bd show <id>`** - View detailed task descriptions
5. **Update status** - `bd update <id> --status=in_progress` when starting
6. **Close tasks** - `bd close <id>` when complete
7. **Sync frequently** - `bd sync` to push progress

---

**Total Estimated Duration:** 7-10 sessions across 5 phases
**Ready to begin!**
