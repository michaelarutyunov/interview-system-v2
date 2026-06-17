You are to generate a single, Colab-ready Python script that implements a streaming canonical slot discovery system for interview-extracted nodes.

## Input Data

The script will contain a hardcoded list of surface nodes, each with:

```python
{"id": str, "label": str, "node_type": str}
```

get the data from /home/mikhailarutyunov/projects/interview-system-v2/docs/dedup2/data.txt

---

## Environment

* Read KIMI API key from COLAB secrets: `KIMI_API_KEY`
* Implement real API calls to KIMI for slot proposal
* Use `sentence-transformers` for embeddings
* Use cosine similarity
* No database, in-memory only

---

## Core Behavior

Simulate a 10-turn interview by randomly splitting surface nodes into unequal chunks and processing them sequentially.

### Chunking

Implement:

```python
def split_into_unequal_chunks(nodes, n_turns=10, seed=42)
```

* Uneven chunk sizes
* Deterministic with seed
* All nodes assigned exactly once

---

## Data Structures

Implement:

### SlotHypothesis

Fields:

* slot_id (uuid)
* slot_name (snake_case)
* description (str)
* supported_surface_ids (set[str])
* turns_seen (set[int])
* embedding (np.array)
* status ("candidate" or "active")

### CanonicalSlot

Fields:

* slot_id
* slot_name
* description
* surface_ids (set[str])
* turns_seen (set[int])

---

## KIMI Slot Proposal

Implement:

```python
def propose_slots_with_kimi(surface_nodes, existing_slot_names) -> list[dict]
```

### Prompt Requirements

The KIMI prompt MUST:

* Ask for latent variable / concept slot extraction
* Require STRICT JSON output
* Require fields:

  * slot_name (snake_case)
  * description
  * supporting_surface_ids (must be subset of provided ids)
* Instruct model to:

  * Prefer reusing existing slot_names if applicable
  * Not invent slots without evidence
* Include existing_slot_names in context

Expected JSON format:

```json
[
  {
    "slot_name": "processing_level",
    "description": "degree of processing / clean label",
    "supporting_surface_ids": ["id1", "id2"]
  }
]
```

The function must:

* Call KIMI API
* Parse JSON
* Raise on invalid JSON

---

## Embeddings

Implement:

```python
embed_text(text: str) -> np.ndarray
```

Using sentence-transformers (e.g. all-MiniLM-L6-v2)

Slot embedding text:

```
slot_name + " :: " + description
```

---

## Slot Clustering / Merge (CUMULATIVE)

Implement:

```python
def merge_or_create_slot(proposed_slot, current_turn)
```

Algorithm:

For each proposed slot:

1. Compute cosine similarity to ALL existing SlotHypotheses
2. If max similarity >= SLOT_MERGE_THRESHOLD:

   * Merge into best match:

     * Union supported_surface_ids
     * Add current_turn to turns_seen
3. Else:

   * Create new SlotHypothesis

Constants:

```python
SLOT_MERGE_THRESHOLD = 0.85
```

---

## Promotion to CanonicalSlot

After each turn, run:

```python
def promote_slots_if_ready()
```

Promotion rule:

Promote SlotHypothesis to CanonicalSlot if:

```python
len(slot.supported_surface_ids) >= MIN_SUPPORT_NODES
AND len(slot.turns_seen) >= MIN_TURNS
```

Constants:

```python
MIN_SUPPORT_NODES = 3
MIN_TURNS = 2
```

On promotion:

* Set status = "active"
* Create CanonicalSlot entry

---

## Surface → Slot Mapping

Maintain mapping:

```python
surface_to_slot = dict[surface_id -> slot_id]
```

Update whenever a surface supports a slot.

---

## Per-turn Processing

Implement:

```python
def process_turn(surface_chunk, turn_id)
```

Steps:

1. Call propose_slots_with_kimi
2. For each proposed slot:

   * merge_or_create_slot
3. promote_slots_if_ready
4. Print logs:

   * Turn number
   * Proposed slots
   * Merge decisions
   * Newly promoted canonicals
   * Total active canonicals

---

## Final Output

After all turns:

Print:

1. All CanonicalSlots with:

   * slot_name
   * description
   * number of surface_ids
2. Mapping of:
   surface label → canonical slot_name

---

## Non-goals (do NOT implement)

* No polarity modeling
* No MEC reasoning
* No graph DB
* No batch global reclustering
* No slot splitting logic

---

## Code Requirements

* Single Python file
* Colab-safe
* Clear logging
* Functions separated cleanly
* Errors on invalid JSON from KIMI

---

## Important

This is an experimental harness. Favor clarity, debuggability, and determinism over optimization.

Save the code in dedup2.py in the folder /docs/dedup2/
---
