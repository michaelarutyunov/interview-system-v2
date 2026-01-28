"""
Shared questioning techniques - the "how" of asking questions.

Techniques are reusable modules that generate questions using specific
questioning patterns. Unlike strategies (which decide WHEN to use a technique),
techniques define HOW to generate questions.

Example techniques:
- LadderingTechnique: Probe deeper with "why is that important?"
- ElaborationTechnique: Expand with "tell me more about..."
- ProbingTechnique: Explore alternatives with "what else..."
- ValidationTechnique: Confirm outcomes with "so you want..."
"""

from src.methodologies.techniques.common import Technique
from src.methodologies.techniques.laddering import LadderingTechnique
from src.methodologies.techniques.elaboration import ElaborationTechnique
from src.methodologies.techniques.probing import ProbingTechnique
from src.methodologies.techniques.validation import ValidationTechnique

__all__ = [
    "Technique",
    "LadderingTechnique",
    "ElaborationTechnique",
    "ProbingTechnique",
    "ValidationTechnique",
]
