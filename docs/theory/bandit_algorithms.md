# Bandit Algorithms for Adaptive Interview Sequencing in Conversational AI

Multi-armed bandit algorithms provide the mathematical foundation for real-time question selection in adaptive interview systems, with **Upper Confidence Bound (UCB)** and **Thompson Sampling** emerging as the dominant approaches alongside information-theoretic methods. The core exploration-exploitation tradeoff maps directly to the challenge of balancing discovery of new topics versus deepening established understanding—a problem now being deployed at scale by Amazon, Duolingo, and Microsoft in production dialogue systems. This report synthesizes algorithmic foundations, practical implementations, and specific applications to knowledge graph construction through strategic interviewing.

---

## UCB algorithms balance optimism with proven regret guarantees

The UCB1 algorithm, introduced by Auer, Cesa-Bianchi, and Fischer in 2002, computes a score for each action (question) as the empirical mean reward plus an exploration bonus: **UCB_i(t) = μ̂_i + √(2·ln(t)/n_i)**. This "optimism under uncertainty" principle ensures logarithmic regret—specifically O(√KT·log(T)) for K arms over T rounds—while requiring only O(K) computation per step. For dialogue systems, this translates to preferring underexplored topics while gradually shifting toward high-value questions as evidence accumulates.

Non-stationary variants address evolving conversation contexts where user knowledge or preferences change during interaction. **Discounted UCB (D-UCB)** applies exponential discounting to weight recent observations more heavily, making it suitable for gradual shifts in user engagement or understanding. **Sliding Window UCB (SW-UCB)** instead maintains only the last τ observations, better handling abrupt context switches such as topic changes mid-interview. Garivier and Moulines (2011) proved that SW-UCB achieves regret O(√Υ_T·K·T·log(T)) where Υ_T represents the number of environmental changes—critical for interviews where user mood or knowledge state can shift suddenly.

**LinUCB** extends bandits to incorporate contextual features, enabling personalized question selection based on dialogue state. Introduced by Li et al. (2010) for Yahoo news recommendation (achieving **12.5% CTR improvement**), LinUCB models expected reward as linear in context features: E[r|x] = x^⊤θ. The algorithm maintains a covariance matrix A and response vector b per arm, computing confidence bounds via ellipsoid geometry. For dialogue applications, features might encode user demographics, conversation history embeddings, slot-filling status, and topic relevance scores. The key update equations—A ← A + xx^⊤ and b ← b + rx—require O(d²) per step for d-dimensional features, making LinUCB practical for real-time systems with hundreds of context dimensions.

Dialogue-specific UCB variants have emerged to leverage conversational feedback beyond behavioral signals. **ConUCB** (Zhang et al., 2020) incorporates user responses about abstract key-terms (e.g., "Italian food," "action movies") to achieve smaller regret bounds than standard LinUCB. This approach is particularly relevant for interview systems where users can express preferences about topic categories rather than just individual questions.

---

## Thompson Sampling offers Bayesian elegance with computational advantages

Thompson Sampling, first proposed in 1933 but rediscovered for modern applications by Russo and Van Roy, takes a fundamentally different approach: sample parameters from the posterior distribution, then act optimally with respect to that sample. For Bernoulli rewards (binary outcomes like successful knowledge elicitation), this involves maintaining Beta(α, β) distributions per question and sampling θ̂ ~ Beta(α, β) each round. The posterior update is simply **(α, β) ← (α + r, β + 1-r)** when a question is asked and receives reward r.

The algorithm naturally implements probability matching—the probability of selecting an action equals the probability it is optimal given current evidence. This Bayesian interpretation provides principled uncertainty quantification and, crucially, **handles delayed feedback and batch updates without modification**. In dialogue systems where reward signals (interview success, knowledge graph quality) may only appear at conversation end, Thompson Sampling's ability to aggregate observations before updating provides significant practical advantages over UCB approaches that traditionally require per-round updates.

For contextual settings, **Linear Thompson Sampling** (Agrawal & Goyal, 2013) maintains Gaussian posteriors over regression weights, sampling θ̂ ~ N(μ_t, v²B_t^{-1}) where B_t accumulates outer products of context vectors. **Neural Thompson Sampling** (Zhang et al., 2020) extends this to deep networks by using neural tangent features to construct variance estimates around network predictions, achieving O(√T) regret matching other contextual bandit algorithms.

Prior specification strategies critically impact early-stage performance. **Informative priors** from historical data—for example, Beta(1, 100) fitted to historical question-answer distributions—can substantially accelerate learning. For dialogue domains, priors might encode curriculum difficulty ratings, expected user engagement patterns, or expert estimates of question diagnosticity. Russo and Van Roy's Stanford tutorial demonstrates that thoughtfully elicited priors can reduce regret by orders of magnitude in practical applications.

Empirical comparisons consistently favor Thompson Sampling over UCB in high-dimensional settings. Chapelle and Li (2011) found TS approaching the Lai-Robbins lower bound in practice, while cascading bandit experiments show TS significantly outperforming UCB with K=1000 items due to UCB's suboptimal hyper-rectangular confidence sets versus TS's natural ellipsoidal exploration.

---

## Information-theoretic measures provide principled question selection criteria

**Expected Information Gain (EIG)**, formalized by Lindley in 1956, measures the expected reduction in entropy about parameters of interest when observing an answer: EIG(ξ) = E_p(y|ξ)[H[p(θ)] - H[p(θ|y,ξ)]]. This criterion naturally connects to the 20 Questions intuition that optimal questions should eliminate roughly half of remaining possibilities. For adaptive interviews, EIG provides a theoretically grounded objective for question selection that directly quantifies learning value.

**Bayesian Active Learning by Disagreement (BALD)**, introduced by Houlsby et al. (2011), decomposes EIG into predictive entropies: BALD(x) = H[E_θ[p(y|x,θ)]] - E_θ[H[p(y|x,θ)]]. The first term measures total predictive uncertainty; the second measures expected aleatoric (irreducible) uncertainty; their difference captures **epistemic uncertainty**—uncertainty reducible through observation. This formulation enables practical computation via Monte Carlo sampling from the parameter posterior, with extensions like **BatchBALD** addressing batch acquisition for interviewing multiple topics simultaneously.

**Deep Adaptive Design (DAD)**, developed by Foster et al. (2021), addresses computational tractability for real-time deployment. Rather than computing EIG at decision time, DAD trains a policy network π_φ(h_t) → ξ_{t+1} that maps interaction history to optimal next question. This amortization reduces per-decision latency to milliseconds while maintaining near-optimal information acquisition. For interview systems requiring responsive interactions, DAD provides the only currently viable path to full Bayesian optimal experimental design.

Connections between information theory and bandit approaches run deep. Information-Directed Sampling (Russo & Van Roy) explicitly balances information gain against regret, while Kirsch et al. (2022) showed that gradient-based and Fisher information methods can be understood as EIG approximations. The 20 Questions problem demonstrates the link explicitly: optimal questioning corresponds to Huffman codes, achieving average question counts of H(Π) + 1 where Π is the distribution over targets.

---

## Production systems demonstrate practical viability at scale

**Amazon** deploys contextual bandits across multiple products using both UCB and Thompson Sampling. Amazon Music uses bandits for song ranking with position bias modeling, while SageMaker provides production-ready contextual bandit containers using Vowpal Wabbit with doubly-robust policy evaluation. The architecture supports continuous retraining loops with ~1ms latency per prediction/update.

**Duolingo's** Recovering Sleeping Bandit algorithm (KDD 2020) optimizes push notifications for learner re-engagement, handling the novel constraint that not all message templates are available each round ("sleeping arms") and that recently-used templates suffer a recency penalty. This system contributed to **350% user retention improvement** based on 200 million notifications collected over 34 days.

**Microsoft's** Customer Support Bot uses contextual bandits for disambiguation intent selection, trained via Vowpal Wabbit with careful delayed reward attribution. The system demonstrates practical integration of bandits with dialogue management in high-stakes customer-facing applications.

Integration with LLMs follows three patterns emerging from recent research (KDD 2024 Tutorial). First, **prompt optimization via bandits** uses fixed-budget best arm identification to select among prompt variants—the TRIPLE framework applies successive halving for efficient prompt selection under compute constraints. Second, **LLM-informed bandits** use language models as reward predictors, with decaying temperature schedules to transition from exploration to exploitation. Third, **dueling bandits with LLM evaluation** leverage pairwise comparisons to reduce noisy point-wise scoring impacts when LLMs evaluate response quality.

Cold-start solutions for new users or topics include transfer learning approaches like **T-LinUCB**, which initializes arm parameters from prior recommendation domains; warm-start contextual bandits using active learning to explore high-information items that also satisfy user preferences; and LLM jump-starting (EMNLP 2024), which uses language models to rank arm pairs and initialize bandit priors before online learning begins.

Sparse reward handling—critical for dialogue where success signals may only appear at conversation end—employs potential-based reward shaping (PBRS) to provide dense signals while guaranteeing identical optimal policy convergence, graph-based reward shaping using spectral clustering to propagate rewards at turn-level, and semi-supervised approaches learning trajectory representations from zero-reward transitions.

---

## Open-source frameworks enable rapid implementation

**Vowpal Wabbit** remains the industry standard for contextual bandits, powering Microsoft Azure Personalizer with extensive exploration algorithms (SquareCB, Online Cover, Epsilon-Greedy, Bagging, RND Explorer). The Python API supports action-dependent features enabling dynamic arm addition:

```python
import vowpalwabbit
vw = vowpalwabbit.Workspace("--cb_explore_adf --quiet --squarecb")
vw.learn("1:0.5:0.25 | user_feature1 item_feature2")
probs = vw.predict("| user_feature1")
```

**MABWiser** from Fidelity provides a scikit-learn compatible API with parallel execution support, implementing LinUCB, LinTS, Thompson Sampling, UCB1, and neighborhood policies for contextual bandits. The companion **Mab2Rec** library adds fairness evaluation for recommendation applications.

**learn_to_pick** simplifies contextual bandit integration with LLMs, supporting Vowpal Wabbit or PyTorch backends with automatic scoring, delayed reward handling, and sentence transformer featurization for semantic contexts.

---

## Knowledge graph construction requires phased interview strategies

Adaptive questioning for knowledge elicitation maps naturally to bandit formulations, with coverage-depth tradeoffs mirroring exploration-exploitation tensions. Seven types of knowledge graph completeness—schema, property, population, interlinking, currency, ontology, and coverage—provide multiple optimization objectives that phased interview strategies can target sequentially.

**Active Knowledge Graph Completion** using Open Path (OPRL) rules can generate queries even when correct answers are missing entities not yet in the graph, achieving **precision up to 98%** with 62% recall. The **ASRC framework** combines active learning with semantic recognition, iteratively recommending entity pairs to experts for relation labeling. **KAEL** assembles error detection algorithms into an ensemble updated adaptively based on expert responses.

A three-phase framework emerges from synthesizing this research. The **coverage phase** prioritizes broad questioning to discover entities and relations, using exploration-focused policies with high uncertainty tolerance and active learning to prioritize high-information queries. The **healing phase** targets inconsistencies and missing relations, leveraging knowledge graph completion techniques with moderate exploration. The **expansion phase** deepens understanding of existing entities through exploitation-focused questioning, employing reflective elicitation techniques for tacit knowledge.

**Bandit-based phase transitions** can govern movement between phases: Thompson Sampling or UCB over phase "arms" where rewards encode phase-appropriate objectives (coverage improvements, error corrections, depth increases). The **PAI framework** (Planning-Assessment-Interaction) from recent goal-oriented ITS research uses graph-based reinforcement learning with cognitive structure representations to learn optimal transitions between exercise and assessment activities—directly analogous to interview phase sequencing.

**BanditCAT** (2024) casts computerized adaptive testing in a contextual bandit setting, using Thompson Sampling for test administration. Combined with AutoIRT for item parameter estimation from foundation model embeddings, this approach addresses exploration-exploitation in diagnostic question selection—precisely the capability needed for knowledge graph construction interviews.

---

## Conclusion: Integrated approaches for adaptive interviewing

The optimal approach for adaptive interview sequencing combines complementary strengths across algorithm families. Thompson Sampling should serve as the default selection algorithm due to natural uncertainty quantification, batch update capability, and superior empirical performance in high-dimensional settings—critical advantages for dialogue systems with delayed feedback. LinUCB provides a strong alternative when interpretable feature importance weights are needed for explaining question selection decisions.

Information-theoretic criteria (EIG/BALD) offer principled objectives for question selection when computational budget permits, with Deep Adaptive Design enabling real-time deployment through amortized inference. For knowledge graph construction specifically, phased strategies with bandit-governed transitions—discovery, healing, expansion—provide a structured approach to balancing coverage breadth against depth on existing entities.

The gap between research and practice has narrowed substantially. Production frameworks like Vowpal Wabbit provide millisecond-latency contextual bandits, LLM integration patterns are crystallizing around prompt optimization and reward prediction, and cold-start solutions enable reasonable performance from first interactions. The remaining challenges center on reward specification (defining what constitutes successful knowledge elicitation), multi-objective optimization across coverage/accuracy/engagement, and scaling to knowledge graphs with millions of potential entities and relations.