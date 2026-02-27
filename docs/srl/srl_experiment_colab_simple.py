"""
SRL + Discourse Analysis for Extraction Enhancement

Uses ONLY spaCy (no complex dependencies)
- Dependency-based discourse relations (language-agnostic, NO hardcoded markers)
- SRL via dependency parsing (predicate-argument structures)
- NO pronoun resolution (use original text)

INSTRUCTIONS FOR GOOGLE COLAB:
1. Create new notebook
2. Paste this entire file into ONE cell
3. Run
4. Download 2 output files

OUTPUT: Structural analysis to enhance extraction LLM prompts.
Use discourse relations and SRL frames as hints for relationship extraction.
"""

# ============================================
# STEP 1: Install
# ============================================
print("=" * 80)
print("INSTALLING...")
print("=" * 80)

import subprocess
import sys

print("Installing spaCy...")
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "spacy"])

print("Downloading spaCy model...")
subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])

print("\n" + "=" * 80)
print("✓ INSTALLED")
print("=" * 80 + "\n")

# ============================================
# STEP 2: Import and Load
# ============================================
print("=" * 80)
print("LOADING...")
print("=" * 80)

import json

try:
    from google.colab import files

    print("✓ Google Colab detected")
except ImportError:
    print("⚠ Not in Colab - files saved locally")

    class DummyFiles:
        def download(self, f):
            print(f"  Saved: {f}")

    files = DummyFiles()

import spacy

print("Loading spaCy model...")
nlp = spacy.load("en_core_web_sm")

print("\n" + "=" * 80)
print("✓ READY")
print("=" * 80)
print("Discourse: MARK/ADVCL dependencies (language-agnostic)")
print("SRL: Predicate-argument structures via dependencies")
print()

# ============================================
# STEP 3: Data
# ============================================

INTERVIEW_ANSWERS = {
    "turn_1": {
        "turn_number": 1,
        "question": "What else matters to you when you're choosing which oat milk to buy?",
        "response": "I always check the ingredient list - I want to make sure there's no added oils or gums if possible. And the sugar content is huge for me, like I try to stick to ones with under 5 grams per serving. Oh, and whether it's fortified with calcium and vitamin D, since I'm not getting those from regular dairy.",
    },
    "turn_2": {
        "turn_number": 2,
        "question": "Why does getting those nutrients matter to you?",
        "response": "I mean, I'm just trying to take care of my body, you know? I work out regularly and I want to make sure I'm actually fueling myself properly, not just drinking empty calories. Plus, I've noticed I have more energy throughout the day when I'm getting the right nutrients, so it's kind of become a priority for me.",
    },
    "turn_3": {
        "turn_number": 3,
        "question": "So taking care of your body through oat milk is about having energy and working out well - is that right?",
        "response": "Yeah, exactly. I mean, the energy part is huge for me - I noticed when I switched from regular milk, I didn't get that sluggish feeling after my morning coffee. And the fact that it's plant-based just feels cleaner for my system, you know? Less inflammation, easier to digest.",
    },
    "turn_4": {
        "turn_number": 4,
        "question": "So oat milk helps you feel less sluggish and cleaner - what does feeling that way give you?",
        "response": "I'd say it just helps me stay more consistent with my routine, you know? Like when I'm not dealing with that afternoon crash or feeling bloated, I can actually stick to my workout schedule and stay productive at work. It's really about maintaining that baseline energy throughout the day so I'm not constantly fighting against my body.",
    },
    "turn_5": {
        "turn_number": 5,
        "question": "What does not fighting against your body mean for you?",
        "response": "I think it means choosing foods that work with my system rather than against it. Like, I've noticed dairy can make me feel sluggish and bloated, so switching to oat milk just feels... easier on my digestion, you know? My body doesn't have to work as hard to process it. It's about listening to what makes me feel good and energized instead of pushing through discomfort just because that's what I'm used to.",
    },
    "turn_6": {
        "turn_number": 6,
        "question": "So choosing oat milk is part of listening to your body - why is that listening important to you?",
        "response": "I mean, I think it's just about respecting what my body's telling me, you know? Like, I used to ignore those signals - feeling bloated after dairy, or that afternoon crash - but now I actually pay attention. And when I listen and make changes, like switching to oat milk, I genuinely feel better. More energy, better digestion. It's kind of empowering to understand what works for me instead of just eating whatever.",
    },
    "turn_7": {
        "turn_number": 7,
        "question": "So understanding what works for you through choices like oat milk - what does that give you in your life?",
        "response": "You know, it gives me peace of mind, honestly. Like, I can go through my day knowing I'm fueling my body with something clean and not dealing with the inflammation or digestive issues I used to get from dairy. It's one less thing to worry about - I can just grab it for my smoothie or coffee and know I'm making a choice that supports my wellness goals instead of working against them.",
    },
    "turn_8": {
        "turn_number": 8,
        "question": "So oat milk helps support your wellness goals - what do those goals mean for how you want to live?",
        "response": "I want to feel good in my body, you know? Like, having sustained energy throughout the day without crashes, and just knowing I'm putting clean fuel into my system. It's about being able to keep up with my active lifestyle - whether that's morning workouts or just having the mental clarity to be productive at work. And honestly, it's also about longevity. I want to make choices now that help me stay healthy as I get older.",
    },
    "turn_9": {
        "turn_number": 9,
        "question": "Thank you for sharing your thoughts with me today. This has been very helpful.",
        "response": "You're welcome! I'm glad I could share my perspective on oat milk. It's definitely become a staple in my routine, so I'm always happy to talk about products that align with my health goals.",
    },
}

# ============================================
# STEP 4: Analysis Functions
# ============================================


def extract_discourse_relations(doc):
    """
    Language-agnostic discourse relation detection via dependencies.
    Uses MARK (subordinating conjunctions) and ADVCL (adverbial clauses).
    NO hardcoded marker lists!
    """
    relations = []

    for token in doc:
        # MARK = subordinating conjunctions (because, since, when, if, etc.)
        if token.dep_ == "mark":
            head = token.head
            clause = " ".join([t.text for t in head.subtree])
            relations.append(
                {"marker": token.text, "type": "subordination", "clause": clause[:80]}
            )

        # ADVCL = adverbial clause (often causal/temporal)
        elif token.dep_ == "advcl":
            relations.append(
                {"marker": "implicit", "type": "adverbial_clause", "verb": token.text}
            )

    return relations


def extract_srl_frames(doc):
    """
    Extract predicate-argument structures via dependencies.
    ARG0 = agent (subject), ARG1 = patient (object), ARGM-* = modifiers
    """
    frames = []

    for token in doc:
        if token.pos_ == "VERB":
            args = {}

            for child in token.children:
                if child.dep_ == "nsubj":
                    args["ARG0"] = child.text
                elif child.dep_ == "dobj":
                    args["ARG1"] = child.text
                elif child.dep_ == "prep":
                    prep_obj = [w.text for w in child.children if w.dep_ == "pobj"]
                    if prep_obj:
                        args[f"ARGM-{child.text.upper()}"] = prep_obj[0]

            if args:
                frames.append({"verb": token.text, "arguments": args})

    return frames


def analyze_turn(text, turn_id, question):
    """Analyze one interview turn."""
    print(f"  Analyzing {turn_id}...")

    doc = nlp(text)
    discourse = extract_discourse_relations(doc)
    srl = extract_srl_frames(doc)

    return {
        "turn_id": turn_id,
        "question": question,
        "text": text,
        "discourse": discourse,
        "srl": srl,
    }


# ============================================
# STEP 5: Run Analysis
# ============================================

print("\n" + "=" * 80)
print("RUNNING ANALYSIS...")
print("=" * 80)

results = {}
for turn_id, data in INTERVIEW_ANSWERS.items():
    results[turn_id] = analyze_turn(
        text=data["response"], turn_id=turn_id, question=data["question"]
    )

print("✓ Complete\n")

# ============================================
# STEP 6: Generate Report
# ============================================


def generate_report(results):
    """Generate analysis report."""
    lines = []
    lines.append("=" * 80)
    lines.append("DISCOURSE + SRL ANALYSIS")
    lines.append("=" * 80)
    lines.append("\nMETHOD: Dependency-based (language-agnostic)")
    lines.append("- Discourse: MARK/ADVCL dependencies (NO hardcoded markers)")
    lines.append("- SRL: Predicate-argument structures")
    lines.append("- NO pronoun resolution (use original text)\n")

    total_discourse = 0
    total_frames = 0

    for turn_id, data in results.items():
        lines.append(f"\n{'=' * 80}")
        lines.append(f"TURN {turn_id.split('_')[1]}")
        lines.append(f"{'=' * 80}")
        lines.append(f"Q: {data['question']}")
        lines.append(f"\nTEXT: {data['text'][:100]}...")

        lines.append(f"\n📌 DISCOURSE ({len(data['discourse'])}):")
        for rel in data["discourse"][:5]:
            lines.append(f"   {rel['marker']} ({rel['type']})")

        lines.append(f"\n🎯 SRL ({len(data['srl'])}):")
        for frame in data["srl"][:5]:
            args = ", ".join([f"{k}={v}" for k, v in frame["arguments"].items()])
            lines.append(f"   {frame['verb']}: {args}")

        total_discourse += len(data["discourse"])
        total_frames += len(data["srl"])

    lines.append(f"\n{'=' * 80}")
    lines.append("SUMMARY")
    lines.append("=" * 80)
    lines.append(f"Turns: {len(results)}")
    lines.append(
        f"Discourse relations: {total_discourse} (avg {total_discourse / len(results):.1f}/turn)"
    )
    lines.append(
        f"SRL frames: {total_frames} (avg {total_frames / len(results):.1f}/turn)"
    )

    return "\n".join(lines)


report = generate_report(results)
print(report)

# ============================================
# STEP 7: Save Files
# ============================================

print("\n" + "=" * 80)
print("SAVING FILES...")
print("=" * 80)

# 1. Analysis report
with open("srl_discourse_analysis.txt", "w") as f:
    f.write(report)

# 2. Extraction-ready context
extraction_contexts = {}
for turn_id, data in results.items():
    extraction_contexts[turn_id] = {
        "text": data["text"],
        "structural_analysis": {
            "discourse_relations": [
                {
                    "marker": r["marker"],
                    "type": r["type"],
                    "clause": r.get("clause", ""),
                }
                for r in data["discourse"]
            ],
            "srl_frames": [
                {"verb": f["verb"], "arguments": f["arguments"]} for f in data["srl"]
            ],
        },
    }

with open("extraction_context.json", "w") as f:
    json.dump(extraction_contexts, f, indent=2)

print("\n✅ FILES READY:")
print("1. srl_discourse_analysis.txt - Human-readable report")
print("2. extraction_context.json    - For extraction LLM integration")
print("\nDownloading...")

files.download("srl_discourse_analysis.txt")
files.download("extraction_context.json")

print("\n✅ DONE!")
print("\nUSAGE: Pass structural_analysis to extraction LLM as hints")
print("for identifying causal relationships and predicate-argument structures.")
