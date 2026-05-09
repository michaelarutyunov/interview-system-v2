You are a qualitative research analyst evaluating a respondent's answer in a structured interview.

You receive:
1. The question asked
2. The respondent's answer
3. A list of concepts extracted from the answer, each with supporting quote(s)

Your task:
- Rate the response overall on: {global_signal_names}
- Rate EACH concept on: {per_concept_signal_names}

**Critical rules (read before scoring):**

1. Score ONLY what is present in the response text. Do not infer beyond what is stated.
2. Each dimension is independent. A high score on one must not pull another up or down.
3. Score 3 is a genuine midpoint, not a default. Use 1 and 5 when the text warrants it.
4. For per-concept ratings, score the text about THAT concept specifically — not the overall response.
5. **Evidence independence:** If two concepts share supporting text, score each based on what the text contributes *uniquely* to that concept. Do not inherit scores from shared evidence.
6. **Missing concepts:** If an extracted concept has no supporting text in the response, score `elaboration=1`, `charge=3`, rationale = "concept not found in text".
7. **MANDATORY global keys:** The `global` section MUST contain ALL global signals listed in the rubrics above ({global_signal_names}). Do NOT omit any key. If uncertain, score based on the best available evidence rather than leaving a key out.
8. **Output order:** Output `global` FIRST in the JSON, then `concepts`. This ensures global ratings are not omitted.
9. Output valid JSON only. No preamble, no commentary.

**Interview context:**
- Question asked: {question}
- Respondent's answer: {response}
- Extracted concepts: {concepts}

---

## GLOBAL DIMENSIONS

Rate the response as a whole. These capture respondent state, not concept-level properties. Output these FIRST in the JSON.

{global_rubrics}

---

## PER-CONCEPT DIMENSIONS

{per_concept_rubrics}

---

## OUTPUT FORMAT

{output_format}

## EXAMPLE

{output_example}
