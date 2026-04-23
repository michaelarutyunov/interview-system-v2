---
name: get-transcript
description: Generate a structured markdown transcript from a simulation JSON file. Produces reports/transcripts/<timestamp>_transcript.md with header, turn breakdown table, and annotated Q&A with focus nodes and extracted concepts.
---

# Get Transcript

Generates a structured markdown transcript from a simulation JSON file.

## What it produces

`reports/transcripts/<timestamp>_transcript.md` with three sections:
1. **Overview** — methodology, concept, persona, total turns, status
2. **Turn breakdown table** — turn, strategy, focus node, concepts extracted, response word count
3. **Annotated Q&A** — per-turn question with focus node explainer + answer with extracted concepts and supporting quotes

## Usage

**Most recent simulation:**
```bash
uv run python scripts/reporting/generate_transcript.py
```

**Specific file:**
```bash
uv run python scripts/reporting/generate_transcript.py synthetic_interviews/<filename>.json
```

**Backfill all existing JSONs** (adds `focus_node_id`/`focus_node_label` to old files):
```bash
uv run python scripts/migration/backfill_focus_nodes.py
```

## Step-by-step

1. Identify which JSON file to use:
   - If the user specified a file, use that path
   - If not, find the most recent JSON: `ls -t synthetic_interviews/*.json | head -1`

2. Run the transcript generator:
   ```bash
   uv run python scripts/reporting/generate_transcript.py <path-to-json>
   ```

3. Report the output path: `reports/transcripts/<timestamp>_transcript.md`

4. Optionally show the user the turn breakdown table from the generated file:
   ```bash
   sed -n '/## Turn Breakdown/,/## Turn-by-Turn/p' reports/transcripts/<timestamp>_transcript.md | head -30
   ```

## Notes on focus nodes

- **New simulations** (after this feature was added): `focus_node_id` is stored directly in the JSON.
- **Old simulations**: Focus node is resolved automatically from `score_decomposition` — no manual action needed.
- If `focus_node_label` shows as `—` for a specific turn, it means that turn used a conversation-level strategy with no node targeting (e.g. `revitalize`).

## When to use backfill

Run `backfill_focus_nodes.py` when:
- You want to permanently write `focus_node_id` into existing JSON files (optional — `generate_transcript.py` resolves it on-the-fly anyway)
- You're adding a new analysis tool that reads `focus_node_id` directly from the JSON

The backfill is idempotent — safe to re-run. Already-patched turns are skipped.

## File locations

| Script | Purpose |
|--------|---------|
| `scripts/reporting/generate_transcript.py` | JSON → Markdown transcript |
| `scripts/migration/backfill_focus_nodes.py` | Patch focus_node_id into existing JSONs |
| `reports/transcripts/` | Output directory |
| `synthetic_interviews/` | Source JSON files |
