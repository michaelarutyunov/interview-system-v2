# ADR-017: Strategy Weight Calibration for Phase Balance

## Status

Accepted 2026-02-04

## Context

Following the phase detection fix (ADR-016), late-phase strategies began activating correctly. However, simulation testing revealed two issues:

1. **Mid-phase `clarify` dominance**: With weight 1.0 and high orphan counts common in exploratory interviews, `clarify` was consistently selected over other strategies
2. **Late-phase `reflect` dominance**: With weight 1.8 and bonus 0.4, `reflect` dominated (8 consecutive selections in one 10-turn simulation)

This reduced strategy variety and made interviews feel repetitive.

## Decision

Calibrate strategy weights to improve balance and variety:

### Mid-Phase Changes
- `clarify`: 1.0 → 0.8 (reduce dominance when orphan_count is high)
- Other weights remain unchanged

### Late-Phase Changes
- `reflect` weight: 1.8 → 1.2 (reduce multiplicative boost)
- `reflect` bonus: 0.4 → 0.2 (reduce additive bonus)
- Other weights remain unchanged

### Rationale

The `clarify` weight reduction addresses orphan_count-driven over-selection. When many nodes lack connections, `clarify`'s `graph.orphan_count: 0.7` signal gives it an unfair advantage.

The `reflect` reduction addresses late-phase over-selection. The original 1.8× + 0.4 bonus was too strong, effectively suppressing `revitalize` and other late-phase strategies.

## Consequences

### Positive

1. **Improved strategy variety** - No single strategy dominates throughout a phase
2. **Better `revitalize` activation** - Late-phase revitalization strategies now receive fair consideration
3. **More natural interview flow** - Strategy changes feel less forced

### Negative

1. **May reduce deepening** - Lower `reflect` weight could reduce validation depth in late phase
2. **Requires ongoing tuning** - Different respondent personas may require different calibration

### Mitigations

- Weights are configurable per methodology in YAML
- Simulation testing allows validation before production use
- ADR-016's pure node-count phase detection ensures phases transition predictably

## Related

- [ADR-016: Pure Node-Count Phase Detection](./016-pure-node-count-phase-detection.md)
- [Strategy Weight Configuration](../../config/methodologies/means_end_chain.yaml)
- [Phase-Based Strategy Selection](../SYSTEM_DESIGN.md#phase-based-weights-and-bonuses)

## History

- 2026-02-04: Initial calibration based on simulation testing
- 2026-02-04: Accepted
