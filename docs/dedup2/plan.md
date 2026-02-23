#  Plan (with KIMI + Chunked Interview Emulation)

## High-level behavior

You will simulate a 10-turn interview by:

1. Randomly splitting 67 surface nodes into **unequal chunks**
2. Processing chunks sequentially as “turns”
3. On each turn:

   * Call KIMI to propose slot hypotheses for that chunk
   * Merge new slot hypotheses with all prior slots
   * Update evidence and promotion state
4. Canonical slots evolve over time


---

## New / Modified Components

## STEP 0 — Environment & API

Agent must:

* Read `KIMI_API_KEY` from COLAB secrets
* Implement:

```python
def call_kimi(prompt: str) -> dict:
    """
    Calls KIMI API and returns parsed JSON.
    Must raise on invalid JSON.
    """
```

The prompt must explicitly request **strict JSON output**.

---

## STEP 1 — Chunking / Turn Simulation

Add a function:

```python
def split_into_unequal_chunks(nodes, n_turns=10, seed=42):
    """
    Returns list of lists (chunks), uneven sizes, sum = len(nodes)
    """
```

Implementation approach:

* Generate random weights
* Normalize to total nodes
* Round
* Adjust last chunk to fix off-by-one

This is deterministic and testable.

---

## STEP 2 — Per-turn Slot Proposal (REAL LLM)

Replace stub with real LLM call:

```python
def propose_slots_with_kimi(surface_nodes: list[SurfaceNode]) -> list[dict]:
```

### Prompt contract (critical)

Prompt must say:

* You are extracting latent variables / concept slots
* Each slot must include:

  * slot_name (snake_case)
  * description
  * supporting_surface_ids (subset of provided ids)
* Do NOT invent slots without evidence
* Return STRICT JSON list

Example schema enforced in prompt:

```json
[
  {
    "slot_name": "processing_level",
    "description": "degree of processing / clean label",
    "supporting_surface_ids": ["id1", "id2"]
  }
]
```

---

## STEP 3 — Slot Embeddings (unchanged)

Embed:

```
slot_name + " :: " + description
```

Store embedding.

---

## STEP 4 — Cumulative Slot Clustering (IMPORTANT CHANGE)

Now clustering is always done against:

```
ALL existing SlotHypotheses
```

not just current turn.

Algorithm:

For each proposed slot (this turn):

1. Compute similarity vs every existing slot
2. If max_sim >= SLOT_MERGE_THRESHOLD:

   * Merge into best match
3. Else:

   * Create new SlotHypothesis

This ensures **cross-turn convergence.**

---

## STEP 5 — Evidence + Turn Tracking (unchanged but critical)

Each slot must track:

```python
slot.supported_surface_ids
slot.turns_seen
```

On merge:

* Union surface ids
* Add current_turn to turns_seen

---

## STEP 6 — Promotion Rules (unchanged)

Promote to CanonicalSlot if:

```python
len(slot.supported_surface_ids) >= MIN_SUPPORT_NODES
AND len(slot.turns_seen) >= MIN_TURNS
```

---

## STEP 7 — Logging (for sanity)

On each turn, print:

* Turn number
* New slot proposals
* Slot merges
* Newly promoted canonicals
* Total active canonicals so far

This is important to debug drift.

---

# Key Risks (honest assessment)

These are real and you should expect them:

### 1. KIMI will invent near-duplicate slots

Even with instructions, you’ll see:

* processing_level
* clean_label
* ingredient_quality

Your clustering layer MUST be solid, or you’ll just move the problem up.

---

### 2. Early turns will be noisy

First 1–2 chunks may produce bad or overly general slots.
That’s fine — promotion rules + later evidence will stabilize.

---

### 3. Chunk composition matters

Random uneven chunks will stress-test your system.
Good — but expect some instability in early runs.

---

# Why this design is correct for your goal

This architecture:

✅ Mirrors real streaming interview conditions
✅ Forces canonical concepts to emerge gradually
✅ Preserves traceability to surface nodes
✅ Lets you measure convergence quality over turns

This is much closer to state-of-the-art practice than batch dedup.

---

# One important extra constraint to add to your KIMI prompt

Tell KIMI:

> Prefer reusing existing latent variables if they fit, rather than inventing new ones.

You can include existing slot names in the prompt context each turn.

This materially improves convergence.

---

