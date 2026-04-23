# ZeroFizz Bundle v1 — Cross-Concept Richness Audit

**Bundle:** `domain:zerofizz_beverage_v1`
**Status:** Immutable. Revisions become v2, not silent edits to v1.
**Source of truth:** `docs/concepts/zerofizz_beverage_v1/domain_brief.md`
**Machine-readable companion:** `audit.yaml` (same directory)

## Richness rubric

Each concept objective must satisfy:

1. **Word count** 120–180.
2. **Dimension coverage** — hints at ≥6 of the 9 dimensions (A–I) from the brief. Methodology-structural N/A is acceptable for H on MEC/RG and for I on JTBD/CIT/CJM.
3. **Methodology-native framing** — uses the methodology's ontological vocabulary.
4. **Specificity** — ≥2 concrete grounded details (rooftop bar, 2pm slump, TikTok call-out).
5. **Contrast set naming** — ≥2 comparison products in prose.
6. **No closed-vocabulary bias** — must not preclude unmentioned dimensions.

## Cross-concept coverage matrix

| Dim | MEC | JTBD | CIT | CJM | RG |
|---|---|---|---|---|---|
| A Functional attributes | ✓ attribute layer | ✓ desired outcomes + pains | partial, via incident detail | ✓ research stage | ✓ latent dimension |
| B Sensory | partial (carbonation) | partial (aftertaste pain) | ✓ moment reconstruction | ✓ first-taste stage | partial (jittery) |
| C Occasions | ✓ rooftop | ✓ 2pm, rooftop, Dry Jan | ✓ barbecue, rooftop, office | ✓ 2pm, post-workout, rooftop | ✓ rooftop vs gas station |
| D Emotional / identity | ✓ psychosocial layer | ✓ kind of person who | ✓ full emotion palette | partial (delight) | ✓ grown-up vs teenage |
| E Social meaning | ✓ belonging, signaling | ✓ peer alignment | ✓ with whom, told others | ✓ peer settings | ✓ show vs hide |
| F Contrast set | ✓ 3 named | ✓ 4 named | ✓ 3 named | ✓ 2 named | ✓ 7 named (densest) |
| G Tensions | ✓ not preachy | ✓ creator call-out | ✓ TikTok identity | ✓ marketing skepticism | ✓ four-way tension |
| H Experience arc | N/A structural | partial (switching pain) | ✓ canonical arc | ✓ canonical spine | N/A structural |
| I Values | ✓ values layer | implicit | implicit | implicit | ✓ values-aligned dim |

## Per-concept rubric compliance

| Check | MEC | JTBD | CIT | CJM | RG |
|---|---|---|---|---|---|
| Word count (120–180) | 129 | 138 | 140 | 132 | 126 |
| Dimensions covered (≥6 of addressable) | 8/8 | 8/8 | 9/9 | 8/8 | 8/8 |
| Methodology-native framing | ✓ | ✓ | ✓ | ✓ | ✓ |
| Specificity (≥2 concrete details) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Contrast set named (≥2) | ✓ (3) | ✓ (4) | ✓ (3) | ✓ (2) | ✓ (7) |
| Closed-vocabulary bias | none | none | none | none | none |

All 5 concepts pass the rubric.

## Structural asymmetries — expected, not defects

These are unavoidable consequences of methodology choice. An eval harness comparing across methodologies must know about these or it will misread structural asymmetry as richness asymmetry.

1. **H (experience arc).** MEC is a vertical ladder; RG is cross-sectional contrast. Neither models temporal sequence. CIT and CJM put arc at the center. JTBD touches it through switching pains. A scorer rewarding "captured the full adoption arc" will structurally favor CIT/CJM over MEC/RG.

2. **I (values).** MEC has a native values layer. RG surfaces values through construct abstraction. JTBD/CIT/CJM have no dedicated values node — values appear as implicit framing in emotional or identity cues. A scorer keying on "values depth" will structurally favor MEC/RG.

3. **F (contrast set density).** RG names 7 alternatives; others name 2–4. Triadic elicitation is impossible without an element set, so RG's input surface area is nominally larger by design. Do not interpret this as "RG is richer."

## Bundle manifest

```
config/concepts/zerofizz_beverage_mec.yaml     (means_end_chain_v2_strict)
config/concepts/zerofizz_beverage_jtbd.yaml    (jobs_to_be_done_v2)
config/concepts/zerofizz_beverage_cit.yaml     (critical_incident_v2)
config/concepts/zerofizz_beverage_cjm.yaml     (customer_journey_mapping_v2)
config/concepts/zerofizz_beverage_rg.yaml      (repertory_grid_v2)
docs/concepts/zerofizz_beverage_v1/domain_brief.md
docs/concepts/zerofizz_beverage_v1/audit.md
docs/concepts/zerofizz_beverage_v1/audit.yaml
```
