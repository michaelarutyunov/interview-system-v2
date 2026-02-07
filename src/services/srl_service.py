"""
Semantic Role Labeling (SRL) service for linguistic structure extraction.

This service uses spaCy to extract:
- Discourse relations (causal, temporal markers via dependency parsing)
- SRL frames (predicate-argument structures)

The output is used to enhance extraction prompts with structural hints.
"""

from typing import Dict, List, Optional, Set, Any
import structlog

logger = structlog.get_logger(__name__)


class SRLService:
    """
    Extract linguistic structure using spaCy dependency parsing.

    Uses language-agnostic dependency labels (Universal Dependencies)
    rather than hardcoded keyword matching.
    """

    DEFAULT_NOISE_PREDICATES = {
        "mean",
        "know",
        "think",
        "guess",
        "say",
        "tell",
        "ask",
        "like",
        "want",
        "need",
    }

    def __init__(
        self,
        model_name: str = "en_core_web_md",
        noise_predicates: Optional[Set[str]] = None,
    ):
        """
        Initialize SRL service with lazy loading.

        Args:
            model_name: spaCy model name (default: en_core_web_md)
            noise_predicates: Set of predicates to filter out (default: English meta-talk verbs)
        """
        self._model_name = model_name
        self._noise_predicates = (
            noise_predicates if noise_predicates is not None else self.DEFAULT_NOISE_PREDICATES
        )
        self._nlp = None

    @property
    def nlp(self):
        """Lazy-load spaCy model on first access."""
        if self._nlp is None:
            import spacy

            logger.info("loading_spacy_model", model=self._model_name)
            self._nlp = spacy.load(self._model_name)
            logger.info("spacy_model_loaded", model=self._model_name)
        return self._nlp

    def analyze(
        self, user_utterance: str, interviewer_question: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze user utterance for discourse relations and SRL frames.

        Args:
            user_utterance: The user's response text
            interviewer_question: Optional interviewer question for context (not currently used)

        Returns:
            Dictionary with:
                - discourse_relations: List[Dict] with {marker, antecedent, consequent}
                - srl_frames: List[Dict] with {predicate, arguments}
        """
        # Handle edge cases
        if not user_utterance or not user_utterance.strip():
            logger.debug("srl_analysis_skipped", reason="empty_input")
            return {"discourse_relations": [], "srl_frames": []}

        try:
            doc = self.nlp(user_utterance)

            discourse_relations = self._extract_discourse_relations(doc)
            srl_frames = self._extract_srl_frames(doc)

            logger.info(
                "srl_analysis_complete",
                discourse_count=len(discourse_relations),
                frame_count=len(srl_frames),
            )

            return {
                "discourse_relations": discourse_relations,
                "srl_frames": srl_frames,
            }

        except Exception as e:
            logger.error("srl_analysis_error", error=str(e), error_type=type(e).__name__)
            # Graceful degradation - return empty structures
            return {"discourse_relations": [], "srl_frames": []}

    def _extract_discourse_relations(self, doc) -> List[Dict[str, str]]:
        """
        Extract discourse relations using dependency labels.

        Uses Universal Dependencies:
        - MARK: subordinating conjunctions (because, since, when, if)
        - ADVCL: adverbial clauses (often causal/temporal)

        Returns:
            List of discourse relations with marker, antecedent, consequent
        """
        relations = []

        for token in doc:
            # MARK = subordinating conjunctions
            if token.dep_ == "mark":
                head = token.head
                # Antecedent: clause introduced by marker
                antecedent_tokens = [t.text for t in head.subtree]
                antecedent = " ".join(antecedent_tokens)

                # Consequent: main clause (head's head)
                if head.head:
                    consequent_tokens = [
                        t.text for t in head.head.subtree if t not in head.subtree
                    ]
                    consequent = " ".join(consequent_tokens) if consequent_tokens else ""
                else:
                    consequent = ""

                relations.append(
                    {
                        "marker": token.text,
                        "antecedent": antecedent[:100],  # Limit length
                        "consequent": consequent[:100],
                    }
                )

            # ADVCL = adverbial clause (often causal/temporal)
            elif token.dep_ == "advcl":
                # Extract clause and main clause
                clause_tokens = [t.text for t in token.subtree]
                clause = " ".join(clause_tokens)

                main_tokens = [t.text for t in token.head.subtree if t not in token.subtree]
                main_clause = " ".join(main_tokens) if main_tokens else ""

                relations.append(
                    {
                        "marker": "implicit",
                        "antecedent": clause[:100],
                        "consequent": main_clause[:100],
                    }
                )

        return relations

    def _extract_srl_frames(self, doc) -> List[Dict[str, Any]]:
        """
        Extract predicate-argument structures from dependency tree.

        Maps dependency labels to semantic roles:
        - nsubj -> ARG0 (agent/subject)
        - dobj -> ARG1 (patient/object)
        - prep -> ARGM-<prep> (modifiers)

        Returns:
            List of SRL frames with predicate and arguments dict
        """
        frames = []

        for token in doc:
            # Only process verbs
            if token.pos_ != "VERB":
                continue

            # Filter noise predicates
            if token.lemma_.lower() in self._noise_predicates:
                continue

            arguments = {}

            for child in token.children:
                # ARG0: agent/subject
                if child.dep_ == "nsubj":
                    arguments["nsubj"] = child.text

                # ARG1: patient/object
                elif child.dep_ == "dobj":
                    arguments["dobj"] = child.text

                # ARGM: prepositional modifiers
                elif child.dep_ == "prep":
                    # Find prepositional object
                    prep_obj = [w.text for w in child.children if w.dep_ == "pobj"]
                    if prep_obj:
                        arguments[f"prep_{child.text}"] = prep_obj[0]

            # Only include frames with at least one argument
            if arguments:
                frames.append({"predicate": token.text, "arguments": arguments})

        return frames
