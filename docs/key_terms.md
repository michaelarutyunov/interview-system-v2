# Signal Firing Rates

Every turn, the engine evaluates dozens of signals (from graph topology, LLM ratings, session state). A signal fires when its value crosses a threshold
that makes it actionable for strategy scoring.

Firing rate = "what fraction of turns did this signal activate?"

Example from a real run: convgraph.node.chain.gap.above fires on ~40% of turns in a healthy MEC interview (you need a gap above to ascend), but
convgraph.node.is_orphan might fire on only 10% (most nodes get connected quickly).

Why it matters in review: A signal with 0% firing rate is dead weight — it's configured in the YAML but never triggers, meaning its associated strategy
can never win. A signal with 100% firing rate doesn't differentiate — every candidate gets the same boost, so it's wasted computation.

---
# Budget Decomposition

Each strategy's score is a weighted sum of signal contributions. The budget is the total score mass, decomposed into where it comes from:

- Positive mass — signals that push the score up (e.g., chain.gap.above: +0.3)
- Negative mass — signals that push the score down (e.g., self_count: -0.5 to prevent repetition)
- Gate mass — hard blocks (strategy is ineligible if the gate signal is false)

Total score = +2.1 (structural positives) - 0.5 (repetition brake) + 0.3 (phase bonus) = 1.9

Why it matters: If a strategy has 90% positive mass from a single structural signal and only 10% negative mass from the repetition brake, it takes many
consecutive uses before the brake catches up — the strategy dominates regardless of context. This is the "base score asymmetry overwhelms repetition
brakes" failure mode documented in CLAUDE.md (seen in CJM deepen_stage with base=2.3 vs brake=-0.6).

---
# Penalty Asymmetry

A specific case of budget decomposition — comparing whether penalties and bonuses are balanced across strategies.

If strategy A has +0.3 when its gate signal fires, but the brake for using it repeatedly is only -0.1, that's an asymmetry: the reward outweighs the cost
by 3:1. The strategy will repeat until the brake accumulates enough turns to matter.

Conversely, if strategy B has +0.2 reward but -0.5 brake, it gets punished too aggressively and rarely fires twice.

Why it matters: Balanced strategies create natural diversity. Asymmetric ones create monoculture (one strategy wins every turn) or starvation (a strategy
never wins despite being valid).

---
# Phase Multiplier Differentials

The interview has three phases (exploratory, focused, closing). Each methodology YAML defines signal weights per phase:

phases:
early:
    signal_weights:
    convgraph.node.coverage.low: 0.4   # reward exploring new ground
late:
    signal_weights:
    convgraph.node.coverage.low: 0.1   # don't explore, go deep

A phase multiplier differential is the gap between how much a signal contributes in one phase vs another. If coverage.low has weight 0.4 in early but 0.1
in late, the differential is 4:1 — the strategy relying on it will dominate early but fade late, which is the intended behavior.

Why it matters: If the differentials are too small (e.g., 0.3 vs 0.25), the phase system isn't actually changing behavior — the interview feels the same
throughout. If they're inverted (higher weight in the wrong phase), strategies fight against the intended interview arc.