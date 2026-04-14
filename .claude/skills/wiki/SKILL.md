---
name: wiki
description: Use when user requests to save, preserve, or document the current conversation for the interview-system-v2 project wiki. Triggered by /wiki or similar phrases like "save to wiki", "wiki this", "document this for the project", etc.
project: interview-system-v2
---

## Overview
Project-specific conversation preservation for interview-system-v2. Saves structured markdown to the project wiki at `interview-engine-wiki/raw/chat-exports/` in the Obsidian vault. Automatically detects conversation phases, generates appropriate template sections, and includes project-specific context.

## When to use this skill
When user requests to save a conversation to the project wiki. Typical triggers:
- `/wiki` - primary command
- "Save to wiki"
- "Wiki this conversation"
- "Document this for the project"
- "Add to project wiki"

## How to use this skill

### Quick Reference

**Target Location:**
- Path: `/mnt/g/My Drive/Obsidian_Vault/interview-engine-wiki/raw/chat-exports/`
- Format: `YYYY-MM-DD-{{topic-slug}}.md`
- Sync: Direct to Obsidian vault on Google Drive

**Project-Specific Context:**
- Always include `#project/interview-system-v2` tag
- Reference relevant architecture docs when applicable (SYSTEM_DESIGN.md, data_flow_paths.md, etc.)
- Include beads/issue IDs if work relates to specific tasks

**Tag Categories:**
| Category | Format | Examples |
|----------|--------|----------|
| Domain | `#pipeline/`, `#signals/`, `#graphs/`, `#strategies/` | `#pipeline/stage-6`, `#signals/graph.node.exhaustion` |
| Activity | `#debugging/`, `#implementation/`, `#architecture/`, `#refactoring/` | `#debugging/scoring`, `#implementation/node-signals` |
| Project | `#project/interview-system-v2` | Always included |

### Workflow Steps

### Step 1: Conversation Analysis
Analyze the current conversation to identify:

**Content identification:**
- Primary topics discussed (e.g., NodeStateTracker lifecycle, strategy scoring, SRL preprocessing)
- Key methodology decisions made
- Technical approaches explored
- Code patterns or implementations discussed
- Relevant beads/issue IDs if mentioned
- Architecture docs referenced (SYSTEM_DESIGN.md, data_flow_paths.md, etc.)

**Phase detection:**
Determine if conversation evolved through multiple phases:
- **Debugging**: Bug investigation, error tracing, troubleshooting
- **Implementation**: Code patterns, new features, concrete implementation
- **Architecture**: System design decisions, structural choices, tradeoffs
- **Refactoring**: Code improvement, cleanup, optimization

**Conversation type:**
- Single-phase: Stayed focused on one area
- Multi-phase: Evolved through multiple areas
- Bug-to-implementation: Started as debugging, moved to implementation

**Discovery path identification:**
For detailed Discovery Path capture, identify:
- **Hypotheses formed**: What did we initially believe was happening?
- **Evidence examined**: Which files, logs, signals, or docs were read to test hypotheses?
- **Dead ends & pivots**: What approaches were tried and abandoned? Why?
- **Mental model shifts**: How did understanding of the system change along the way?
- **Key questions**: What clarifying questions unlocked progress?
- **Aha trigger**: What exact observation, code line, or test result caused the breakthrough?
- **Context switches**: Which subsystems or docs had to be consulted before returning to the main thread?

### Step 2: Interactive Metadata Collection
Ask the user concisely in a single interaction:

**If multi-phase conversation detected:**
"Detected conversation flow: {{phases identified}}

1. Primary focus? [debugging/implementation/architecture/refactoring/mixed]
2. Phases: {{suggested phases}} - confirm or modify?
3. Tags suggested:
   - Domain: {{domain tags like #pipeline/stage-6}}
   - Activity: {{activity tags like #debugging/scoring}}
   - Project: #project/interview-system-v2
   Accept or modify?
4. Related beads/IDs? (if applicable)"

**If single-phase conversation:**
"1. Focus area: [implementation/debugging/architecture/refactoring/full]
2. Tags suggested: {{3-5 tags}} - accept or modify?
3. Related beads/IDs? (if applicable)"

**Tag Categories for interview-system-v2:**
- **Domain**: `#pipeline/`, `#signals/`, `#graphs/`, `#strategies/`, `#extraction/`, `#methodologies/`
- **Activity**: `#debugging/`, `#implementation/`, `#architecture/`, `#refactoring/`, `#testing/`
- **Project**: `#project/interview-system-v2` (always included)

### Step 3: Generate Structured Markdown

Create markdown file with this project-specific template:

```markdown
---
created: {{YYYY-MM-DD}}
conversation_type: {{single-phase|multi-phase|bug-to-implementation}}
phases: [{{list of phases}}]
primary_focus: {{implementation|debugging|architecture|refactoring|mixed}}
topics: [{{extracted topics as list}}]
tags: [{{user-confirmed tags}}]
project: interview-system-v2
beads: [{{related bead IDs if applicable}}]
type: wiki-export
conversation_date: {{YYYY-MM-DD}}
---

# {{Descriptive Title Based on Main Topic}}

## Context
{{Brief 2-3 sentence overview of what prompted this discussion and what was explored}}

{{If multi-phase conversation OR significant intellectual journey detected, include Discovery Path section}}
## Discovery Path
A detailed reconstruction of how understanding was built, hypothesis by hypothesis.

### Starting Frame
{{What was believed or assumed at the start of the conversation. Include the initial mental model of the problem.}}

### Hypotheses & Evidence Trail
{{For each major hypothesis tested, capture:}}
- **Hypothesis 1**: {{what we thought was happening}}
  - **Evidence checked**: {{files read, logs inspected, signals examined, docs referenced}}
  - **Verdict**: {{confirmed / partially true / falsified — and why}}
- **Hypothesis 2**: {{next best guess}}
  - **Evidence checked**: {{...}}
  - **Verdict**: {{...}}

### Dead Ends & Pivots
{{Approaches considered and abandoned, with reasons:}}
- **Attempted**: {{approach or fix tried}}
  - **Why it didn't fit**: {{contradictory evidence, scope mismatch, or side effects}}
  - **Pivot trigger**: {{what specifically caused the change in direction}}

### Context Switches
{{Subsystems, docs, or codebases consulted along the way:}}
- `{{file_or_doc}}`: {{why it had to be checked and what it revealed}}

### The Aha Moment
**Trigger**: {{exact observation — a line of code, a test result, a log entry, a doc clause}}

**Shift**: {{how the mental model changed in that moment}}

**Quote/consequence**: {{paste the key code snippet, log line, or reasoning chain that crystallized the insight}}

### Final Trajectory
{{How the corrected understanding led directly to the chosen solution or conclusion.}}

{{End of conditional Discovery Path section}}

{{If debugging was involved, include Bug Investigation section}}
## Bug Investigation
**Symptom**: {{what went wrong}}
**Root cause**: {{underlying issue}}
**Fix**: {{solution implemented}}
**Files affected**: {{files changed}}
**Learning**: {{what this revealed about the system}}

{{End of conditional Bug Investigation section}}

{{If architecture decision was made, include Architecture Decision section}}
## Architecture Decision
**Context**: {{what prompted this decision}}

**Options considered**:
- **Option A**: {{description}} - Tradeoffs: {{pros/cons}}
- **Option B**: {{description}} - Tradeoffs: {{pros/cons}}

**Decision**: {{chosen approach}}
**Rationale**: {{why this option was selected}}

{{End of conditional Architecture Decision section}}

## Implementation Details
{{Implementation specifics, code patterns, or technical nuances}}

### Files Modified
{{List files changed with brief descriptions}}
- `src/path/to/file.py`: {{what was changed and why}}

### Code Patterns
{{Key patterns or snippets}}
```{{language}}
{{representative code if applicable}}
```

### Configuration Changes
{{If YAML config or settings were changed}}
```yaml
{{relevant config changes}}
```

## System Integration
{{How this fits into the interview-system-v2 architecture}}

### Pipeline Stages Affected
{{Which pipeline stages (1-10) are impacted}}
- Stage X: {{impact description}}

### Related Services
{{Which services are involved}}
- `{{service_name}}`: {{role and impact}}

### Documentation References
{{Links to relevant project docs}}
- `docs/{{relevant_doc}}.md`: {{why relevant}}

## Key Insights & Learnings
{{Novel insights, aha moments, or important clarifications}}
1. {{Insight}}
2. {{Insight}}

## Related Beads/Issues
{{If beads or issue IDs were mentioned}}
- {{bead-ID}}: {{brief description}}

## Follow-up Work
{{Open questions or areas for future exploration}}
- {{Task or item}}

---
*Conversation preserved from Claude Code session {{session-date}}*
*Project: interview-system-v2*
```

### Step 4: Filename Generation
Create filename following pattern: `YYYY-MM-DD-{{topic-slug}}.md`
- Use date of conversation
- Create slug from main topic (lowercase, hyphens, no special chars)
- Example: `2026-04-06-node-exhaustion-backtracking.md`

### Step 5: Save to Project Wiki
Save file to: `/mnt/g/My Drive/Obsidian_Vault/interview-engine-wiki/raw/chat-exports/{{filename}}`

**Path handling:**
- Google Drive is mounted at `/mnt/g/` via WSL2 drvfs
- Auto-mount configured in `/etc/fstab`: `G: /mnt/g drvfs defaults 0 0`
- If G: drive is not mounted, run: `sudo mount -t drvfs 'G:' /mnt/g`

### Step 6: Confirmation
After saving, provide brief confirmation:
```
✓ Saved to: interview-engine-wiki/raw/chat-exports/{{filename}}
✓ Tags: {{tags used}}
✓ Beads: {{bead IDs if applicable}}
```

## Project-Specific Features

### Architecture Doc Integration
When relevant, reference specific docs:
- `docs/SYSTEM_DESIGN.md` - System architecture
- `docs/data_flow_paths.md` - 19 critical data flow diagrams
- `docs/pipeline_contracts.md` - Stage input/output contracts
- `docs/signals_and_strategies.md` - Signal Pools configuration
- `docs/extraction_and_graphs.md` - Extraction and Graphs configuration
- `docs/NodeStateTracker_mutation.md` - NodeStateTracker lifecycle

### Beads Integration
- Always ask if work relates to specific beads/issue IDs
- Include bead IDs in frontmatter as `beads: [{{ids}}]`
- Reference beads in Related Beads/Issues section

### Pipeline Stage References
When discussing pipeline changes:
- Reference specific stage numbers (1-10)
- Include stage file names (e.g., `context_loading_stage.py`)
- Note data flow path numbers from `docs/data_flow_paths.md`

## Common Mistakes

**1. Wrong Target Directory**
- **Symptom**: File saves to wrong location
- **Cause**: Using "Claude Insights" path instead of "interview-engine-wiki/raw/chat-exports/"
- **Fix**: Always use `/mnt/g/My Drive/Obsidian_Vault/interview-engine-wiki/raw/chat-exports/`

**2. Missing Project Tag**
- **Symptom**: Wiki entry not discoverable via project tags
- **Cause**: Forgetting to include `#project/interview-system-v2`
- **Fix**: Always include project tag in metadata

**3. Bead References Not Captured**
- **Symptom**: Work not linked to beads/issue tracking
- **Cause**: Not asking about related bead IDs
- **Fix**: Always ask "Related beads/IDs?" during metadata collection

**4. Architecture Context Missing**
- **Symptom**: Wiki entry lacks system integration context
- **Cause**: Not referencing relevant docs or pipeline stages
- **Fix**: Include System Integration section with doc references

## Error Handling
If unable to write to `/mnt/g/My Drive/Obsidian_Vault/interview-engine-wiki/raw/chat-exports/`:
1. Inform user clearly about the G: drive mount issue
2. Check if G: is mounted: `ls /mnt/g/`
3. If not mounted, run: `sudo mount -t drvfs 'G:' /mnt/g`
4. Provide the markdown content so user can manually save if needed
