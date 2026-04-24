---
name: interview-export
description: Export all artifacts from a simulated interview into a single timestamped folder under reports/interviews/. Generates transcript, causal chains, graph visualization, scoring CSV + summary, latency folder, and log copy. Produces a structured export ready for review.
---

# Interview Export

Export all artifacts from a single simulated interview into a unified folder.

## What it produces

`reports/interviews/<timestamp>/` containing:

| File | Description |
|------|-------------|
| `00_meta.yaml` | Interview metadata (concept, methodology, persona, turns) |
| `01_transcript.md` | Structured Q&A with focus nodes and extracted concepts |
| `02_causal_chains.md` | Methodology-conforming causal chain analysis |
| `03_graph.mmd` | Mermaid graph source (left-to-right turn columns) |
| `03_graph.png` | Rendered graph diagram |
| `04_scoring.csv` | Raw per-signal-per-candidate scoring decomposition |
| `04_scoring_summary.md` | Aggregated tables (firing rates, dead signals, budget, gates) |
| `05_latency/` | Latency audit summary + per-stage CSV + LLM call CSV |
| `06_insights.md` | Placeholder — populated by `/interview-review` |
| `99_session.log` | Copied session log (for latency analysis and debugging) |

## Usage

**Most recent simulation:**
```bash
uv run python scripts/reporting/export_interview.py
```

**Specific simulation:**
```bash
uv run python scripts/reporting/export_interview.py synthetic_interviews/<filename>.json
```

**Custom output directory:**
```bash
uv run python scripts/reporting/export_interview.py <json> --output-dir /tmp/my_export
```

## Procedure

1. Identify the source JSON:
   - If the user specified a file, use that path
   - If not, find the most recent: `ls -t synthetic_interviews/*.json | head -1`

2. Run the export script:
   ```bash
   uv run python scripts/reporting/export_interview.py <path-to-json>
   ```

3. Report the export folder path: `reports/interviews/<timestamp>/`

4. List the generated files with sizes:
   ```bash
   ls -lh reports/interviews/<timestamp>/
   ```

5. If the user wants to proceed to review, suggest:
   ```
   /interview-review reports/interviews/<timestamp>/
   ```

## Notes

- **PNG rendering** requires Chrome/Chromium. If not available (e.g. WSL without Chrome), the `.mmd` file is still generated and can be rendered manually with `npx @mermaid-js/mermaid-cli -i file.mmd -o file.png`.
- **Log copying** requires the JSON to have `metadata.log_file` set. Simulations saved after the logging fix include this. Older simulations will have an empty `log_file` in `00_meta.yaml`.
- **Causal chains** (`02_causal_chains.md`) is initially a placeholder. Run the `extract-causal-chains` logic on the source JSON to populate it, or use the skill `/interview-review` which reads the raw graph data directly.
- The export is **idempotent** — re-running overwrites files in the same folder.
