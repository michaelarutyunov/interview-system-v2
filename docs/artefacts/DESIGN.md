---
name: Interview Engine Visual System
version: 1.0.0
author: Interview System v2

# ═══════════════════════════════════════════════
# Color Tokens
# ═══════════════════════════════════════════════
colors:
  # ── Neutrals ──
  bg: "#F2F1ED"
  panel: "#FFFFFF"
  ink: "#14171C"
  ink_2: "#41474F"
  ink_3: "#7A828D"
  rule: "#DDDCD4"
  rule_strong: "#C7C5BB"
  line: "#5B6471"

  # ── Pipeline Group Accents ──
  # Each group in the pipeline diagram gets a distinct hue for
  # the group header stripe and stage borders.
  group_intake: "#5B6471"     # Slate — input handling
  group_graph: "#4F6E8C"      # Steel blue — graph operations
  group_state: "#6B5C8A"      # Purple — state computation
  group_strategy: "#8A5C5C"   # Terracotta — strategy selection
  group_generation: "#5C7A5C" # Sage — question generation
  group_persist: "#7A6B4F"    # Olive — persistence

  # ── Call-Type Badges ──
  # Background/foreground pairs for pipeline stage badges.
  # Each badge signals what kind of work a stage performs.
  badge_llm_bg: "#ECECF7"
  badge_llm_fg: "#2E2A6B"
  badge_emb_bg: "#E1EFEA"
  badge_emb_fg: "#16574A"
  badge_pure_bg: "#F2EAD6"
  badge_pure_fg: "#5C4612"
  badge_async_bg: "#F8E8D5"
  badge_async_fg: "#874A0B"
  badge_edge_bg: "#E4E0F0"
  badge_edge_fg: "#3D2E6B"

  # ── Graph Relationship Types ──
  # Each relationship type in the conversation graph gets a
  # distinct color so edge meaning is readable at a glance.
  rel_triggers: "#874A0B"
  rel_drives: "#5C7A5C"
  rel_supports: "#16574A"
  rel_implies: "#4F6E8C"
  rel_achieves: "#6B5C8A"
  rel_conflicts: "#8A5C5C"
  rel_occurs_in: "#5B6471"

  # ── Focus States ──
  focus_bg: "#F2EAD6"
  focus_fg: "#5C4612"
  focus_border: "#5C4612"

# ═══════════════════════════════════════════════
# Typography Tokens
# ═══════════════════════════════════════════════
typography:
  families:
    body: '"Inter Tight", -apple-system, sans-serif'
    mono: '"JetBrains Mono", monospace'

  sizes:
    xs: "10px"      # Phase tags, group numbers
    sm: "11px"      # Stage numbers, badge text, labels
    md: "12px"      # Meta text, legend, footer
    base: "13px"    # Body text within stages, badge labels
    lg: "14px"      # Eyebrow, group names
    xl: "16px"      # Stage names, endpoint labels
    _2xl: "18px"    # Subtitle
    _3xl: "22px"    # Row names
    _4xl: "24px"    # Graph title
    _5xl: "44px"    # Slide title

  weights:
    normal: 400
    medium: 500
    semibold: 600
    bold: 700

  letter_spacing:
    tight: "-0.02em"    # Headlines
    normal: "0"
    wide: "0.04em"      # Mono labels
    wider: "0.08em"     # Stage numbers
    widest: "0.12em"    # Uppercase group names
    eyebrow: "0.18em"   # Eyebrow, phase tags

  line_heights:
    tight: 1.1
    snug: 1.15
    normal: 1.2
    relaxed: 1.35
    loose: 1.4
    subtitle: 1.4

# ═══════════════════════════════════════════════
# Spacing & Layout Tokens
# ═══════════════════════════════════════════════
spacing:
  # Base unit is 4px. All spacing derives from this.
  unit: "4px"
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "10px"
  xl: "12px"
  _2xl: "14px"
  _3xl: "16px"
  _4xl: "18px"
  _5xl: "28px"

layout:
  # Slide canvas — 1920×1080 presentation format
  slide_width: "1920px"
  slide_height: "1080px"
  slide_padding: "28px"
  slide_padding_top: "5px"

  # Pipeline grid
  pipeline_row_height: "400px"
  pipeline_gap: "16px"
  pipeline_row_gap: "8px"

  # 40px background grid for alignment
  grid_size: "40px"

  # Stage dimensions
  stage_padding: "10px"
  stage_gap: "4px"
  stage_border_radius: "10px"

  # Small stage variant
  stage_sm_padding: "6px"
  stage_sm_border_radius: "7px"

  # Parallel block
  parblock_padding: "14px"
  parblock_border_radius: "12px"

  # Group layout
  group_padding: "0 8px"

# ═══════════════════════════════════════════════
# Elevation & Depth Tokens
# ═══════════════════════════════════════════════
elevation:
  # The system is intentionally flat. Shadows are used sparingly
  # and only to lift interactive elements or indicate focus.
  flat: "none"
  subtle: "0 1px 0 rgba(20,23,28,0.04)"
  hover: "0 1px 0 rgba(20,23,28,0.06)"
  focus: "0 0 6px rgba(20,23,28,0.05)"
  emphasis: "0 0 14px rgba(20,23,28,0.1)"

# ═══════════════════════════════════════════════
# Shape Tokens
# ═══════════════════════════════════════════════
shapes:
  border_radius:
    xs: "4px"    # Badges
    sm: "6px"    # Graph nodes
    md: "7px"    # Small stages
    lg: "10px"   # Stages
    xl: "12px"   # Parallel blocks
    full: "50%"  # Endpoints (circles)

  border_width:
    thin: "1px"
    medium: "1.5px"

# ═══════════════════════════════════════════════
# Component Tokens
# ═══════════════════════════════════════════════
components:
  badge:
    padding: "3px 7px"
    border_radius: "{shapes.border_radius.xs}"
    font_size: "{typography.sizes.sm}"
    font_family: "{typography.families.mono}"
    font_weight: "{typography.weights.medium}"
    letter_spacing: "{typography.letter_spacing.wide}"

  endpoint:
    size: "84px"
    border_radius: "{shapes.border_radius.full}"
    border_width: "{shapes.border_width.medium}"
    font_size: "{typography.sizes.xl}"
    font_weight: "{typography.weights.semibold}"

  arrow:
    height: "2px"
    width: "24px"
    color: "{colors.line}"

  stage:
    border: "1px solid {colors.rule_strong}"
    border_radius: "{shapes.border_radius.lg}"
    padding: "{spacing.stage_padding}"
    background: "{colors.panel}"
    shadow: "{elevation.subtle}"

  tooltip:
    background: "{colors.ink}"
    border_color: "{colors.ink_2}"
    border_width: "1px"
    padding: "8px 12px"
    text_color: "{colors.bg}"
    font_size: "{typography.sizes.md}"

  legend:
    gap: "28px"
    font_size: "{typography.sizes.base}"
    color: "{colors.ink_2}"
    border_top: "1px solid {colors.rule_strong}"
    padding_top: "{spacing._2xl}"
---

# Interview Engine Visual System

> A design system for technical diagrams, pipeline visualizations, and interactive graph renderings used in the Interview System v2. Built for clarity under information density.

## Overview

The visual identity serves a single purpose: **make complex pipelines and knowledge graphs readable at a glance**. Every choice — color, spacing, type scale — is subservient to that goal.

Two primary surfaces exist:

1. **Pipeline slides** — static 1920×1080 diagrams showing the turn pipeline, data flow, and stage relationships. These are dense: 16+ stages, 6 pipeline groups, 5 call-type badges, all in one view.
2. **Interactive graphs** — force-directed network visualizations of conversation knowledge graphs, rendered in ECharts. These must convey node identity, turn provenance, relationship semantics, and focus state simultaneously.

The system therefore prioritizes:
- **Semantic color encoding** — group, call type, and relationship each get a distinct palette
- **Typography as hierarchy** — size and weight changes replace color changes where possible
- **Flat surfaces with minimal lift** — no gratuitous depth; shadows only signal interactivity or focus
- **Generous internal spacing** — stages breathe even when the grid is dense

## Colors

### Philosophy

The palette is built on a warm neutral base (`#F2F1ED`) that reduces eye strain during long viewing sessions. Against this, a near-black ink (`#14171C`) provides maximum contrast for text. Color is reserved for **meaning** — never decoration.

Three distinct color roles exist:

1. **Pipeline group colors** — tell you *where* you are in the pipeline (intake → graph → state → strategy → generation → persist)
2. **Call-type badge colors** — tell you *what kind of work* a stage performs (LLM, embeddings, pure computation, async, edge extraction)
3. **Relationship colors** — tell you *what connects* two concepts in the graph (triggers, drives, supports, implies, achieves, conflicts_with, occurs_in)

### Neutral Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `bg` | `#F2F1ED` | Slide background, warm off-white |
| `panel` | `#FFFFFF` | Card surfaces, stages, nodes |
| `ink` | `#14171C` | Primary text, borders, endpoints |
| `ink_2` | `#41474F` | Secondary text, subtitles |
| `ink_3` | `#7A828D` | Tertiary text, meta labels, inactive elements |
| `rule` | `#DDDCD4` | Light dividers |
| `rule_strong` | `#C7C5BB` | Card borders, group dividers |
| `line` | `#5B6471` | Connectors, arrows, graph edges |

### Pipeline Groups

Each pipeline group gets a desaturated, muted accent color used as a 3px stripe at the top of the group and a dashed left border on contained stages.

| Group | Token | Hex | Character |
|-------|-------|-----|-----------|
| Intake | `group_intake` | `#5B6471` | Slate — neutral, receiving |
| Graph | `group_graph` | `#4F6E8C` | Steel blue — structural, analytical |
| State | `group_state` | `#6B5C8A` | Purple — internal, computed |
| Strategy | `group_strategy` | `#8A5C5C` | Terracotta — decision, active |
| Generation | `group_generation` | `#5C7A5C` | Sage — creation, growth |
| Persist | `group_persist` | `#7A6B4F` | Olive — storage, archival |

### Call-Type Badges

Badges are pill-shaped labels on pipeline stages. Each call type has a background/foreground pair designed for WCAG-compliant contrast.

| Type | Background | Foreground | Meaning |
|------|------------|------------|---------|
| LLM | `#ECECF7` | `#2E2A6B` | Large language model call |
| Embeddings | `#E1EFEA` | `#16574A` | Vector similarity operation |
| Pure | `#F2EAD6` | `#5C4612` | Deterministic computation |
| Async | `#F8E8D5` | `#874A0B` | Background/overlapping task |
| Edge | `#E4E0F0` | `#3D2E6B` | Relationship extraction |

### Graph Relationships

In the interactive graph, edge color encodes relationship type. The palette is deliberately limited and reused from pipeline group colors where semantically appropriate (e.g., `drives` uses the same sage green as `group_generation`).

| Relationship | Color | Hex |
|--------------|-------|-----|
| triggers | Orange-brown | `#874A0B` |
| drives | Sage | `#5C7A5C` |
| supports | Teal | `#16574A` |
| implies | Steel blue | `#4F6E8C` |
| achieves | Purple | `#6B5C8A` |
| conflicts_with | Terracotta | `#8A5C5C` |
| occurs_in | Slate | `#5B6471` |

## Typography

### Philosophy

Two type families create a clear functional split:

- **Inter Tight** for all human-readable prose — headlines, stage names, subtitles. Its tight letter spacing and modern proportions feel technical without being cold.
- **JetBrains Mono** for all machine-readable labels — stage numbers, meta text, graph turn indicators, relationship labels. Monospace creates a "system" feeling and improves scannability for identifiers.

### Scale

The type scale is anchored at 13px (`base`), the size of stage body text. It expands upward in roughly 1.125×–1.25× increments and compresses downward for labels.

| Token | Size | Usage |
|-------|------|-------|
| `xs` | 10px | Phase tags, group numbers |
| `sm` | 11px | Stage numbers, badges, graph turn labels |
| `md` | 12px | Meta text, legend, footer, graph metadata |
| `base` | 13px | Stage descriptions, legend items |
| `lg` | 14px | Eyebrow labels, group names (uppercase) |
| `xl` | 16px | Stage names, endpoint labels |
| `_2xl` | 18px | Subtitles |
| `_3xl` | 22px | Row names ("Listen & gather") |
| `_4xl` | 24px | Graph titles |
| `_5xl` | 44px | Slide titles |

### Weights

| Token | Value | Usage |
|-------|-------|-------|
| `normal` | 400 | Body text, descriptions |
| `medium` | 500 | Meta text, labels, secondary headings |
| `semibold` | 600 | Stage names, row names, titles |
| `bold` | 700 | (Reserved, rarely used) |

## Layout

### Philosophy

The layout system is built for **fixed-dimension presentation surfaces** (1920×1080 slides) and **viewport-filling interactive graphs**. It uses CSS Grid for the pipeline diagram and a 40px background grid for visual alignment.

### Slide Canvas

- **Width:** 1920px
- **Height:** 1080px (auto for overflow)
- **Padding:** 5px top, 28px sides and bottom
- **Background grid:** 40px squares, 1px lines at 2.5% opacity of ink

### Spacing Scale

All spacing derives from a 4px base unit:

| Token | Value |
|-------|-------|
| `xs` | 4px |
| `sm` | 6px |
| `md` | 8px |
| `lg` | 10px |
| `xl` | 12px |
| `_2xl` | 14px |
| `_3xl` | 16px |
| `_4xl` | 18px |
| `_5xl` | 28px |

### Pipeline Grid

The pipeline uses a complex CSS Grid:
- **Columns:** 158px (row meta) + 84px (endpoint) + 24px (arrow) + 7 flexible groups + 24px + 84px
- **Rows:** Two 400px rows with 8px gap
- **Group dividers:** 1px dashed `rule_strong`

## Elevation & Depth

### Philosophy

The system is **intentionally flat**. Shadows are used sparingly and only for two purposes:

1. **Subtle lift** — separating a card from the background (`0 1px 0 rgba(20,23,28,0.04)`)
2. **Focus indication** — highlighting the currently focused node in a graph (`0 0 6px` blur)

No drop shadows with Y-offsets. No multiple shadow layers. The 1px-offset shadow on stages is technically a border substitute — it creates a hairline separation without consuming border real estate.

### Levels

| Token | Value | Usage |
|-------|-------|-------|
| `flat` | none | Default state |
| `subtle` | `0 1px 0 rgba(20,23,28,0.04)` | Stages, cards |
| `hover` | `0 1px 0 rgba(20,23,28,0.06)` | Slightly elevated on interaction |
| `focus` | `0 0 6px rgba(20,23,28,0.05)` | Focused graph nodes |
| `emphasis` | `0 0 14px rgba(20,23,28,0.1)` | Adjacent emphasis on graph hover |

## Shapes

### Philosophy

Border radius communicates **containment level**:

- Smaller radii (4–6px) for inline elements and dense components
- Medium radii (7–10px) for primary content cards
- Larger radii (12px) for grouped containers
- Full radius (50%) for terminal/endpoint elements

### Radius Scale

| Token | Value | Usage |
|-------|-------|-------|
| `xs` | 4px | Badges, legend items |
| `sm` | 6px | Graph nodes |
| `md` | 7px | Small stage variant |
| `lg` | 10px | Standard stages |
| `xl` | 12px | Parallel blocks, grouped containers |
| `full` | 50% | Endpoints (input/output circles) |

## Components

### Stage

The basic information unit in pipeline diagrams. A rounded rectangle containing a number, name, description, and optional badges.

```
Background:  {colors.panel}
Border:      1px solid {colors.rule_strong}
Radius:      {shapes.border_radius.lg}
Padding:     {spacing.stage_padding}
Shadow:      {elevation.subtle}
```

**Typography inside a stage:**
- Number: `{typography.sizes.sm}` mono, `{colors.ink_3}`, letter-spacing `{typography.letter_spacing.wider}`
- Name: `{typography.sizes.xl}` semibold, `{colors.ink}`
- Description: `{typography.sizes.base}` normal, `{colors.ink_2}`, line-height `{typography.line_heights.loose}`

### Badge

Pill-shaped call-type indicator. Appears at the bottom of stages.

```
Padding:       {components.badge.padding}
Radius:        {shapes.border_radius.xs}
Font:          {typography.families.mono} {typography.sizes.sm} {typography.weights.medium}
Letter-spacing: {typography.letter_spacing.wide}
```

Five color variants (see Colors → Call-Type Badges). Uppercase labels for call types; lowercase for model names ("LLM · Sonnet", "embed", "computation").

### Endpoint

Circular input/output nodes at the edges of the pipeline.

```
Size:          {components.endpoint.size}
Radius:        {shapes.border_radius.full}
Border:        {shapes.border_width.medium} solid {colors.ink}
Font:          {typography.sizes.xl} {typography.weights.semibold}
Text align:    center
```

**States:**
- Default: white background, ink text
- Output (filled): ink background, bg-colored text

### Arrow

Horizontal connector between endpoints and groups.

```
Height:     {components.arrow.height}
Width:      {components.arrow.width}
Color:      {colors.line}
Arrowhead:  8px wide, 5px tall, same color
```

**Bend variant:** Adds a circular dot at the left end to indicate a continuation from a previous row.

### Parallel Block

Dashed-border container for concurrent pipeline stages. Signals that enclosed stages run simultaneously or overlap.

```
Border:        1.5px dashed {badge_async_fg}
Radius:        {shapes.border_radius.xl}
Padding:       {spacing.parblock_padding}
Background:    rgba(248,232,213,0.22)  (subtle async tint)
```

**Label:** Positioned absolute, top -10px, left 12px, with bg-colored padding to create a "tab" effect. Text uses mono font at `{typography.sizes.sm}`, `{badge_async_fg}` color.

### Graph Node

Interactive force-directed graph node, rendered via ECharts.

```
Focused node:
  Background:   {colors.focus_bg}
  Border:       0.8px solid {colors.focus_border}
  Shadow:       {elevation.focus}
  Size:         48px

Unfocused node:
  Background:   {colors.panel}
  Border:       0.8px solid {colors.rule_strong}
  Shadow:       0 0 2px rgba(20,23,28,0.05)
  Size:         32px
```

**Label formatting:** Two-part rich text — turn number in mono (`{typography.sizes.md}`, `{colors.ink_3}`), then node name in mono (`{typography.sizes.sm}`, `{colors.ink}`). Focused nodes use `{colors.focus_fg}` for the turn number.

### Graph Edge

Curved connection between graph nodes.

```
Width:        1.4px (2.5px on emphasis)
Curveness:    0.15
Opacity:      0.5 (0.85 on emphasis)
Color:        Per relationship type (see Colors → Graph Relationships)
Arrow:        6px at target end
```

**Label:** Relationship name in mono, `{typography.sizes.sm}`, same color as edge, letter-spacing `{typography.letter_spacing.wide}`.

### Tooltip

Appears on graph node/edge hover.

```
Background:    {colors.ink}
Border:        1px solid {colors.ink_2}
Padding:       {components.tooltip.padding}
Text color:    {colors.bg}
Font:          {typography.families.body} {typography.sizes.md}
```

Content varies by data type:
- **Node:** Bold name + turn number + focus flag
- **Edge:** Relationship name only

### Legend

Appears at the bottom of pipeline slides and within graph visualizations.

**Pipeline legend:**
- Layout: flex row, gap `{spacing._5xl}`, items centered
- Top border: 1px solid `{colors.rule_strong}`
- Padding top: `{spacing._2xl}`
- Items: badge sample + description text at `{typography.sizes.base}` `{colors.ink_2}`

**Graph legend (ECharts):**
- Two rows: node categories (left) + relationship types (right)
- Bottom position: 4% from bottom
- Text: `{typography.sizes.md}` body for categories, `{typography.sizes.sm}` mono for relationships

## Do's and Don'ts

### Do

- **Do use the full type scale.** The scale is designed to create clear hierarchy without needing color changes. A stage number at 11px and a stage name at 16px is sufficient differentiation.
- **Do respect the 40px grid.** Align major elements to the background grid for visual coherence.
- **Do use badge colors consistently.** The five call-type colors are semantic — never repurpose them for decorative elements.
- **Do keep shadows minimal.** The `subtle` elevation (1px offset, 4% opacity) is the default for all cards. Only escalate to `focus` or `emphasis` for genuine interactive states.
- **Do use monospace for identifiers.** Stage numbers, turn indicators, relationship labels, and meta text should always use JetBrains Mono.

### Don't

- **Don't introduce new colors for pipeline groups.** The six group colors are fixed. Adding a seventh group requires careful consideration of colorblind accessibility and existing semantic mapping.
- **Don't use pure black or white.** `#000000` and `#FFFFFF` are not in the palette. The warm off-white (`#F2F1ED`) and near-black (`#14171C`) are chosen to reduce eye strain.
- **Don't add drop shadows with offsets.** The elevation system uses only 1px-offset or blur-only shadows. Large Y-offset shadows violate the flat aesthetic.
- **Don't use border radii outside the scale.** The six radius tokens cover all needs. Ad-hoc values (e.g., 8px or 14px) break visual consistency.
- **Don't mix relationship colors.** Each relationship type has a fixed color. Using `drives` color for a `triggers` edge creates semantic confusion.
