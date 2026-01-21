# Performance Documentation

## Overview

This document outlines performance requirements, testing strategies, and validation results for the Adaptive Interview System v2.

## PRD Requirements

From PRD Section 2.2 (Success Metrics):

| Metric | Target | Measurement |
|--------|--------|-------------|
| Interview completion rate | ≥90% | Sessions reaching natural close |
| Element coverage | ≥80% | Stimulus elements explored |
| **Response latency** | **<5s p95** | Time from user input to system response |
| Extraction accuracy | ≥80% | Concepts correctly identified (sampled review) |
| Graph coherence | <10% orphan nodes | Nodes without relationships |

### Key Performance Indicator

**Response latency: p95 < 5 seconds**

This is the primary performance requirement measured from:
- User input received → System response generated
- Includes: extraction, graph updates, strategy selection, question generation
- Does NOT include: network latency, UI rendering

## Testing

### Unit Tests

Location: `tests/performance/test_latency.py`

Run with:
```bash
pytest tests/performance/test_latency.py -v
```

#### Test Classes

**TestTurnLatency**
- `test_single_turn_latency_under_5s` - Validates single turn meets p95 target
- `test_multiple_turns_average_latency` - Validates consistent performance
- `test_graph_query_latency` - Graph state query performance
- `test_export_latency` - Graph export performance

**TestThroughput**
- `test_concurrent_session_capacity` - Concurrent session handling

**TestResourceUsage**
- `test_memory_leak_check` - Memory leak detection

**TestLatencyPercentiles**
- `test_p95_latency_meets_prd` - p95 percentile validation

### Benchmark Script

Location: `scripts/benchmark.py`

Run with:
```bash
python scripts/benchmark.py --runs 10 --sessions 1
```

Options:
- `--runs N`: Number of turns per session (default: 10)
- `--sessions M`: Number of concurrent sessions (default: 1)
- `--live`: Run with real LLM calls (requires API key)

#### Benchmark Modes

**Mock Benchmark** (default)
- Uses mock services
- No API calls required
- Fast iteration for development
- Tests orchestration layer

**Live Benchmark** (optional)
- Real LLM API calls
- Requires `OPENAI_API_KEY` or `--api-key`
- End-to-end latency measurement
- Production-like conditions

#### Output

Benchmark provides:
- Average latency (ms)
- Median latency (ms)
- p95 latency (ms)
- p99 latency (ms)
- Min/Max latency (ms)
- PRD validation (PASS/FAIL)

Example output:
```
Benchmark: Mock (10 turns × 1 sessions)
============================================================

📊 Latency Statistics (n=10):
  Average: 45ms
  Median:  44ms
  Min:     38ms
  Max:     62ms
  p95:     60ms
  p99:     62ms

✅ PRD Validation:
  p95 < 5000ms: ✓ PASS
```

## Target Architecture

### Current Design (v2)

**Single-user, event-loop architecture:**
- FastAPI with async/await
- SQLite for persistence
- Single event loop for all I/O
- No connection pooling needed

**Latency Budget:**
| Component | Target | Notes |
|-----------|--------|-------|
| Extraction | 2-3s | LLM call (dominates) |
| Graph update | 50ms | SQLite operations |
| Strategy selection | 100ms | Graph queries + scoring |
| Question generation | 1-2s | LLM call |
| **Total** | **<5s** | PRD requirement |

### Performance Considerations

**Optimizations:**
1. Async I/O throughout (no blocking)
2. Minimal database round-trips
3. Graph state caching (per turn)
4. Connection reuse

**Bottlenecks:**
1. LLM API latency (unavoidable)
2. Network latency to LLM provider
3. Complex graph queries (as graph grows)

**Scaling Considerations (Future):**
- Connection pooling for multi-user
- Graph query optimization (indexes)
- LLM response caching
- Batch processing for bulk operations

## Monitoring

### Key Metrics

Track in production:
1. **Turn latency** - p50, p95, p99 (ms)
2. **Error rate** - Failed extractions, generations
3. **Resource usage** - Memory, CPU per session
4. **Database latency** - Query times (ms)

### Logging

Performance-critical logs:
```
- turn_processed (includes latency_ms)
- extraction_completed (includes LLM latency)
- graph_state_computed (includes query time)
- question_generated (includes LLM latency)
```

### Profiling

For performance investigation:
```bash
# Python profiler
python -m cProfile -o profile.stats scripts/benchmark.py

# Memory profiler
python -m memory_profiler scripts/benchmark.py
```

## Validation

### Pre-Release Checklist

- [ ] All `tests/performance/` tests pass
- [ ] Benchmark script shows p95 < 5s (mock)
- [ ] Benchmark script shows p95 < 5s (live, if tested)
- [ ] No memory leaks detected in 10-turn test
- [ ] Graph queries remain fast (<100ms) with 50+ nodes
- [ ] Concurrent sessions show no blocking

### Performance Regression

To detect performance regressions:
1. Run benchmark before significant changes
2. Compare p95 latency to baseline
3. Investigate if p95 increases >20%

## Known Limitations

1. **Mock benchmarks** don't include real LLM latency
2. **Single-threaded** - no testing of true concurrency
3. **Small datasets** - tests use limited node/edge counts
4. **Cold start** - doesn't measure warm cache performance

## Future Improvements

1. **Load testing** - Simulate multi-user scenarios
2. **Stress testing** - Large graphs (1000+ nodes)
3. **Long-running tests** - 100+ turn sessions
4. **Production monitoring** - APM integration
5. **Performance budgets** - Automated regression detection

## References

- PRD Section 2.2: Success Metrics
- PRD Section 8.6: Response Structure
- Architecture: `docs/ARCHITECTURE.md`
