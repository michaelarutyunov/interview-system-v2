"""Text similarity utilities for Tier 1 scorers.

Implements TF-IDF cosine similarity to detect redundant questions.
"""

from collections import Counter
from typing import List, Tuple, Optional, Dict, Any
import math

import structlog

logger = structlog.get_logger(__name__)


class TFIDFCosineSimilarity:
    """
    Computes TF-IDF cosine similarity between text documents.

    Used to detect when a proposed question is too similar to recent questions,
    which would make the interview feel repetitive.

    Formula:
    - TF(t, d) = count of term t in doc d / total terms in d
    - IDF(t) = log(1 + N / (1 + DF(t))) where N = total docs
    - TF-IDF = TF * IDF
    - Cosine similarity = (A · B) / (||A|| * ||B||)
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        min_ngram: int = 2,
        max_ngram: int = 3,
    ):
        """
        Initialize TF-IDF cosine similarity calculator.

        Args:
            similarity_threshold: Threshold above which texts are considered similar
            min_ngram: Minimum n-gram size (default: 2 for word pairs)
            max_ngram: Maximum n-gram size (default: 3 for word triples)
        """
        self.similarity_threshold = similarity_threshold
        self.min_ngram = min_ngram
        self.max_ngram = max_ngram

    def compute_similarity(
        self,
        text1: str,
        text2: str,
        history: Optional[List[str]] = None,
    ) -> float:
        """
        Compute cosine similarity between two texts using TF-IDF.

        Args:
            text1: First text (e.g., proposed question)
            text2: Second text (e.g., recent question)
            history: Optional list of additional texts to include in IDF calculation

        Returns:
            Cosine similarity in range [0, 1] where:
            - 0.0 = no similarity
            - 1.0 = identical
        """
        if not text1 or not text2:
            return 0.0

        # Build document collection
        documents = [text1, text2]
        if history:
            documents.extend(history)

        # Tokenize and create n-grams
        tokenized_docs = [self._tokenize(doc) for doc in documents]

        # Calculate TF-IDF vectors
        vector1 = self._tfidf_vector(tokenized_docs[0], tokenized_docs)
        vector2 = self._tfidf_vector(tokenized_docs[1], tokenized_docs)

        # Compute cosine similarity
        similarity = self._cosine_similarity(vector1, vector2)

        return similarity

    def is_too_similar(
        self,
        proposed_question: str,
        recent_questions: List[str],
    ) -> Tuple[bool, float]:
        """
        Check if proposed question is too similar to any recent question.

        Args:
            proposed_question: The question we want to ask
            recent_questions: List of recent questions to compare against

        Returns:
            (is_similar, similarity_score) where is_similar is True if similarity > threshold
        """
        max_similarity = 0.0
        most_similar = ""

        for recent_q in recent_questions:
            similarity = self.compute_similarity(
                proposed_question,
                recent_q,
                history=None,  # Only compare the two questions
            )

            if similarity > max_similarity:
                max_similarity = similarity
                most_similar = recent_q[:50] + "..."  # First 50 chars

        is_too_similar = max_similarity >= self.similarity_threshold

        if is_too_similar:
            logger.debug(
                "Question too similar to recent",
                similarity=max_similarity,
                threshold=self.similarity_threshold,
                recent_question=most_similar,
            )

        return is_too_similar, max_similarity

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into character n-grams.

        Uses character n-grams to be robust to word boundaries and typos.

        Args:
            text: Text to tokenize

        Returns:
            List of n-gram tokens
        """
        text = text.lower()
        tokens = []

        for n in range(self.min_ngram, self.max_ngram + 1):
            for i in range(len(text) - n + 1):
                ngram = text[i:i+n]
                tokens.append(ngram)

        return tokens

    def _tfidf_vector(
        self,
        doc_tokens: List[str],
        all_doc_tokens: List[List[str]],
    ) -> dict:
        """
        Compute TF-IDF vector for a document.

        Args:
            doc_tokens: Tokenized document
            all_doc_tokens: All tokenized documents

        Returns:
            Dictionary mapping term -> TF-IDF score
        """
        # Calculate term frequency
        tf = Counter(doc_tokens)
        total_terms = sum(tf.values())

        # Calculate document frequency
        df = Counter()
        for tokens in all_doc_tokens:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                df[token] += 1

        total_docs = len(all_doc_tokens)

        # Calculate TF-IDF
        tfidf = {}
        for term, count in tf.items():
            # Normalized TF
            tf_norm = count / total_terms
            # IDF with smoothing
            idf = math.log(1 + total_docs / (1 + df[term]))
            tfidf[term] = tf_norm * idf

        return tfidf

    def _cosine_similarity(self, vec1: dict, vec2: dict) -> float:
        """
        Compute cosine similarity between two TF-IDF vectors.

        Args:
            vec1: First TF-IDF vector
            vec2: Second TF-IDF vector

        Returns:
            Cosine similarity in range [0, 1]
        """
        # Get common terms
        all_terms = set(vec1.keys()) | set(vec2.keys())

        if not all_terms:
            return 0.0

        # Calculate dot product
        dot_product = sum(
            vec1.get(term, 0) * vec2.get(term, 0)
            for term in all_terms
        )

        # Calculate magnitudes
        mag1 = math.sqrt(sum(v**2 for v in vec1.values()))
        mag2 = math.sqrt(sum(v**2 for v in vec2.values()))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        # Cosine similarity
        similarity = dot_product / (mag1 * mag2)

        return similarity


def create_similarity_calculator(config: Optional[Dict[str, Any]] = None) -> TFIDFCosineSimilarity:
    """Factory function to create TF-IDF cosine similarity calculator."""
    config = config or {}

    return TFIDFCosineSimilarity(
        similarity_threshold=config.get("similarity_threshold", 0.85),
        min_ngram=config.get("min_ngram", 2),
        max_ngram=config.get("max_ngram", 3),
    )
