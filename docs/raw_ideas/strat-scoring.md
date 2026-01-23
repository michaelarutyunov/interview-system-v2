
# deepen  (depth)
Boost ≈ AmbiguityScorer × 1.4  +  CoverageGapScorer(if “no_reaction” gap) × 1.3
Penalised ≈ NoveltyScorer(if 4+ repeats) × 0.7  +  StrategyDiversityScorer(if used ≥ 3 in last 5) × 0.6
Instinct: “I still hear hedging words / no concrete example → stay here and dig.”

# broaden  (breadth)
Boost ≈ DepthBreadthBalanceScorer(if depth > target) × 1.5  +  CoverageGapScorer(if “unmentioned” gap) × 1.2
Penalised ≈ EngagementScorer(if low momentum) × 0.8  (keeps it simple)
Instinct: “Chains are getting long; let’s collect other islands before we drown in detail.”

# cover_element  (coverage)
Boost ≈ CoverageGapScorer(if any gap on this element) × 1.5  (highest raw weight)
Penalised ≈ NoveltyScorer(if element mentioned 2+ times already) × 0.8
Instinct: “Guide says we must talk about X and it hasn’t surfaced yet → ask X.”

# bridge  (peripheral)
Boost ≈ PeripheralReadinessScorer × 1.6  (new scorer)
+ ClusterSaturationScorer(if saturation > 0.8) × 1.2
Penalised ≈ AmbiguityScorer(if clarity < 0.5) × 0.7  (clarify first)
Instinct: “Current island feels complete and I see a neighbouring island → draw a ferry route.”

# contrast  (contrast)
Boost ≈ ContrastOpportunityScorer × 1.5  (new scorer)
+ DepthBreadthBalanceScorer(if cluster solid) × 1.1
Penalised ≈ EngagementScorer(if low energy) × 0.8  (save challenge for when safe)
Instinct: “They just claimed ‘always’; I have a gentle counter-example ready → test the boundary.”

# clarify  (clarification)
Boost ≈ AmbiguityScorer(if confidence < 0.5) × 1.5  (highest ambiguity weight)
Penalised ≈ StrategyDiversityScorer(if clarify used last 2 turns) × 0.6  (avoid nagging)
Instinct: “Term is fuzzy, respondent hedging → meaning check before we continue.”

# ease  (interaction)
Boost ≈ EngagementScorer(if momentum < threshold 3 turns) × 1.4
Penalised ≈ ContrastOpportunityScorer × 0.5  (never challenge when energy low)
Instinct: “Short answers, no elaboration → soften, encourage, simplify.”

# synthesis  (transition)
Boost ≈ ClusterSaturationScorer × 1.5  (new scorer)
+ CoverageGapScorer(if local gaps = 0) × 1.1
Penalised ≈ AmbiguityScorer(if clarity < 0.6) × 0.7  (don’t summarise muddle)
Instinct: “This chunk feels finished → member-check summary, then move.”

# reflection  (reflection)
Boost ≈ StrategyDiversityScorer(if all else used recently) × 1.2  (fallback)
+ EngagementScorer(if high momentum) × 1.1  (safe to go meta)
Penalised ≈ CoverageGapScorer(if ≥ 2 gaps) × 0.6  (defer meta until basics covered)
Instinct: “Everything else scores low → invite bigger-picture thoughts.”

# closing  (closing)
Boost ≈ CoverageGapScorer(if gaps = 0) × 1.3  +  turn-count gate (≥ N)
Penalised ≈ every scorer × 0.5 until minimum turns reached
Instinct: “Guide empty, story thick, time polite → wrap-up cue.”