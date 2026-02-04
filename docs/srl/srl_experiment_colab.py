"""
SRL Experiment for Interview System
Copy and paste this entire code into a Google Colab notebook

This script:
1. Ingests interview answers
2. Runs Semantic Role Labeling (SRL) using spaCy
3. Extracts predicate-argument structures, causal clauses, coreferences
4. Outputs structured analysis for download
"""

# ============================================
# STEP 1: Install Dependencies
# ============================================
# Run this cell first
!pip install spacy
!python -m spacy download en_core_web_sm
!pip install allennlp allennlp-models

# ============================================
# STEP 2: Import Libraries
# ============================================
import spacy
import json
from collections import defaultdict
from google.colab import files

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# ============================================
# STEP 3: Paste INTERVIEW_ANSWERS here
# ============================================
# Copy the entire dictionary from srl_experiment_data.py

INTERVIEW_ANSWERS = {
  "turn_1": {
    "turn_number": 1,
    "question": "What else matters to you when you're choosing which oat milk to buy?",
    "response": "I always check the ingredient list - I want to make sure there's no added oils or gums if possible. And the sugar content is huge for me, like I try to stick to ones with under 5 grams per serving. Oh, and whether it's fortified with calcium and vitamin D, since I'm not getting those from regular dairy.",
    "persona": "Health-Conscious Millennial"
  },
  "turn_2": {
    "turn_number": 2,
    "question": "Why does getting those nutrients matter to you?",
    "response": "I mean, I'm just trying to take care of my body, you know? I work out regularly and I want to make sure I'm actually fueling myself properly, not just drinking empty calories. Plus, I've noticed I have more energy throughout the day when I'm getting the right nutrients, so it's kind of become a priority for me.",
    "persona": "Health-Conscious Millennial"
  },
  "turn_3": {
    "turn_number": 3,
    "question": "So taking care of your body through oat milk is about having energy and working out well - is that right?",
    "response": "Yeah, exactly. I mean, the energy part is huge for me - I noticed when I switched from regular milk, I didn't get that sluggish feeling after my morning coffee. And the fact that it's plant-based just feels cleaner for my system, you know? Less inflammation, easier to digest.",
    "persona": "Health-Conscious Millennial"
  },
  "turn_4": {
    "turn_number": 4,
    "question": "So oat milk helps you feel less sluggish and cleaner - what does feeling that way give you?",
    "response": "I'd say it just helps me stay more consistent with my routine, you know? Like when I'm not dealing with that afternoon crash or feeling bloated, I can actually stick to my workout schedule and stay productive at work. It's really about maintaining that baseline energy throughout the day so I'm not constantly fighting against my body.",
    "persona": "Health-Conscious Millennial"
  },
  "turn_5": {
    "turn_number": 5,
    "question": "What does not fighting against your body mean for you?",
    "response": "I think it means choosing foods that work with my system rather than against it. Like, I've noticed dairy can make me feel sluggish and bloated, so switching to oat milk just feels... easier on my digestion, you know? My body doesn't have to work as hard to process it. It's about listening to what makes me feel good and energized instead of pushing through discomfort just because that's what I'm used to.",
    "persona": "Health-Conscious Millennial"
  },
  "turn_6": {
    "turn_number": 6,
    "question": "So choosing oat milk is part of listening to your body - why is that listening important to you?",
    "response": "I mean, I think it's just about respecting what my body's telling me, you know? Like, I used to ignore those signals - feeling bloated after dairy, or that afternoon crash - but now I actually pay attention. And when I listen and make changes, like switching to oat milk, I genuinely feel better. More energy, better digestion. It's kind of empowering to understand what works for me instead of just eating whatever.",
    "persona": "Health-Conscious Millennial"
  },
  "turn_7": {
    "turn_number": 7,
    "question": "So understanding what works for you through choices like oat milk - what does that give you in your life?",
    "response": "You know, it gives me peace of mind, honestly. Like, I can go through my day knowing I'm fueling my body with something clean and not dealing with the inflammation or digestive issues I used to get from dairy. It's one less thing to worry about - I can just grab it for my smoothie or coffee and know I'm making a choice that supports my wellness goals instead of working against them.",
    "persona": "Health-Conscious Millennial"
  },
  "turn_8": {
    "turn_number": 8,
    "question": "So oat milk helps support your wellness goals - what do those goals mean for how you want to live?",
    "response": "I want to feel good in my body, you know? Like, having sustained energy throughout the day without crashes, and just knowing I'm putting clean fuel into my system. It's about being able to keep up with my active lifestyle - whether that's morning workouts or just having the mental clarity to be productive at work. And honestly, it's also about longevity. I want to make choices now that help me stay healthy as I get older.",
    "persona": "Health-Conscious Millennial"
  },
  "turn_9": {
    "turn_number": 9,
    "question": "Thank you for sharing your thoughts with me today. This has been very helpful.",
    "response": "You're welcome! I'm glad I could share my perspective on oat milk. It's definitely become a staple in my routine, so I'm always happy to talk about products that align with my health goals.",
    "persona": "Health-Conscious Millennial"
  }
}

# ============================================
# STEP 4: SRL Analysis Functions
# ============================================

def extract_causal_markers(doc):
    """Extract sentences with causal discourse markers."""
    causal_markers = ['because', 'so', 'since', 'therefore', 'thus', 'hence', 'as']
    causal_sentences = []

    for sent in doc.sents:
        sent_text = sent.text.lower()
        for marker in causal_markers:
            if marker in sent_text:
                causal_sentences.append({
                    'sentence': sent.text,
                    'marker': marker,
                    'start_char': sent.start_char,
                    'end_char': sent.end_char
                })
                break

    return causal_sentences

def extract_verb_frames(doc):
    """Extract predicate-argument structures (verb frames)."""
    verb_frames = []

    for token in doc:
        if token.pos_ == "VERB":
            frame = {
                'predicate': token.text,
                'lemma': token.lemma_,
                'arguments': {}
            }

            # Extract subjects, objects, and modifiers
            for child in token.children:
                if child.dep_ == "nsubj":  # Subject
                    frame['arguments']['agent'] = child.text
                elif child.dep_ == "dobj":  # Direct object
                    frame['arguments']['theme'] = child.text
                elif child.dep_ == "prep":  # Prepositional phrases
                    prep_obj = [w.text for w in child.children if w.dep_ == "pobj"]
                    if prep_obj:
                        frame['arguments'][f'prep_{child.text}'] = prep_obj[0]
                elif child.dep_ == "advmod":  # Adverbial modifiers
                    if 'modifiers' not in frame['arguments']:
                        frame['arguments']['modifiers'] = []
                    frame['arguments']['modifiers'].append(child.text)
                elif child.dep_ == "mark":  # Subordinating conjunctions (causal)
                    frame['arguments']['causal_marker'] = child.text

            if frame['arguments']:  # Only keep frames with arguments
                verb_frames.append(frame)

    return verb_frames

def extract_noun_phrases(doc):
    """Extract key noun phrases (potential concepts)."""
    noun_phrases = []

    for chunk in doc.noun_chunks:
        noun_phrases.append({
            'text': chunk.text,
            'root': chunk.root.text,
            'root_pos': chunk.root.pos_,
            'root_dep': chunk.root.dep_
        })

    return noun_phrases

def extract_dependencies(doc):
    """Extract dependency relationships (for relationship mining)."""
    dependencies = []

    for token in doc:
        if token.dep_ not in ['punct', 'det', 'aux']:  # Filter noise
            dependencies.append({
                'token': token.text,
                'lemma': token.lemma_,
                'pos': token.pos_,
                'dep': token.dep_,
                'head': token.head.text,
                'head_pos': token.head.pos_
            })

    return dependencies

def identify_coreferences(doc):
    """Simple coreference detection using pronouns."""
    # Note: This is basic. For production, use neuralcoref or similar
    pronouns = []

    for token in doc:
        if token.pos_ == "PRON":
            pronouns.append({
                'pronoun': token.text,
                'sentence': token.sent.text,
                'position': token.i
            })

    return pronouns

def analyze_utterance(text, turn_id):
    """Run full SRL analysis on an utterance."""
    doc = nlp(text)

    analysis = {
        'turn_id': turn_id,
        'text': text,
        'sentence_count': len(list(doc.sents)),
        'token_count': len(doc),
        'causal_markers': extract_causal_markers(doc),
        'verb_frames': extract_verb_frames(doc),
        'noun_phrases': extract_noun_phrases(doc),
        'dependencies': extract_dependencies(doc),
        'coreferences': identify_coreferences(doc)
    }

    return analysis

# ============================================
# STEP 5: Run Analysis on All Answers
# ============================================

results = {}

print("Running SRL analysis on interview answers...")
print("=" * 60)

for turn_id, turn_data in INTERVIEW_ANSWERS.items():
    print(f"\nAnalyzing {turn_id}...")

    response_text = turn_data['response']
    question_text = turn_data['question']

    # Analyze response
    response_analysis = analyze_utterance(response_text, turn_id)

    # Analyze question for Q->A relationship extraction
    question_analysis = analyze_utterance(question_text, f"{turn_id}_question")

    results[turn_id] = {
        'turn_number': turn_data['turn_number'],
        'question': question_text,
        'response': response_text,
        'question_analysis': question_analysis,
        'response_analysis': response_analysis
    }

print("\n" + "=" * 60)
print("Analysis complete!")

# ============================================
# STEP 6: Generate Summary Report
# ============================================

def generate_summary(results):
    """Generate human-readable summary."""
    summary = []
    summary.append("=" * 80)
    summary.append("SRL ANALYSIS SUMMARY")
    summary.append("=" * 80)

    for turn_id, data in results.items():
        analysis = data['response_analysis']

        summary.append(f"\n{'='*80}")
        summary.append(f"TURN {data['turn_number']}")
        summary.append(f"{'='*80}")
        summary.append(f"\nQUESTION: {data['question']}")
        summary.append(f"\nRESPONSE: {data['response']}")

        # Causal markers
        if analysis['causal_markers']:
            summary.append(f"\n📌 CAUSAL MARKERS DETECTED:")
            for marker in analysis['causal_markers']:
                summary.append(f"   - '{marker['marker']}': {marker['sentence']}")

        # Verb frames (predicate-argument structures)
        if analysis['verb_frames']:
            summary.append(f"\n🔗 PREDICATE-ARGUMENT STRUCTURES:")
            for frame in analysis['verb_frames']:
                summary.append(f"   - Predicate: '{frame['predicate']}'")
                for arg_type, arg_value in frame['arguments'].items():
                    summary.append(f"     • {arg_type}: {arg_value}")

        # Key noun phrases
        if analysis['noun_phrases']:
            summary.append(f"\n💡 KEY CONCEPTS (noun phrases):")
            concepts = [np['text'] for np in analysis['noun_phrases']]
            summary.append(f"   {', '.join(concepts[:10])}")  # Show first 10

        # Coreferences
        if analysis['coreferences']:
            summary.append(f"\n🔄 COREFERENCES (pronouns to resolve):")
            for coref in analysis['coreferences']:
                summary.append(f"   - '{coref['pronoun']}' in: {coref['sentence'][:60]}...")

        summary.append("\n")

    return "\n".join(summary)

# Print summary to console
summary_text = generate_summary(results)
print(summary_text)

# ============================================
# STEP 7: Save Results for Download
# ============================================

# Save full JSON
with open('srl_analysis_full.json', 'w') as f:
    json.dump(results, f, indent=2)

# Save summary text
with open('srl_analysis_summary.txt', 'w') as f:
    f.write(summary_text)

# Create extraction-ready format (for pipeline integration)
extraction_context = {}
for turn_id, data in results.items():
    analysis = data['response_analysis']

    # Format for extraction prompt
    extraction_context[turn_id] = {
        'response_text': data['response'],
        'structural_analysis': {
            'causal_links': [
                f"{m['marker']}: {m['sentence']}"
                for m in analysis['causal_markers']
            ],
            'predicate_frames': [
                f"{f['predicate']} ({', '.join([f'{k}={v}' for k,v in f['arguments'].items()])})"
                for f in analysis['verb_frames']
            ],
            'key_concepts': [np['text'] for np in analysis['noun_phrases']],
            'pronouns_to_resolve': [c['pronoun'] for c in analysis['coreferences']]
        }
    }

with open('extraction_context.json', 'w') as f:
    json.dump(extraction_context, f, indent=2)

print("\n" + "=" * 80)
print("FILES READY FOR DOWNLOAD:")
print("=" * 80)
print("1. srl_analysis_full.json       - Complete analysis (all data)")
print("2. srl_analysis_summary.txt     - Human-readable summary")
print("3. extraction_context.json      - Ready for extraction prompt integration")
print("\nDownloading files...")

# Download all files
files.download('srl_analysis_full.json')
files.download('srl_analysis_summary.txt')
files.download('extraction_context.json')

print("\n✅ Done! Check your downloads folder.")
