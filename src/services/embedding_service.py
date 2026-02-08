"""
Text embedding service using sentence-transformers.

Computes embeddings for canonical slot similarity matching in the
dual-graph architecture. Uses all-MiniLM-L6-v2 (384-dim, float32)
for semantic cosine similarity comparisons.

Also provides access to the spaCy nlp model for lemmatization
(used by CanonicalSlotService._lemmatize_name).

Bead: lmyr (Phase 2: Dual-Graph Architecture)
Bead: gjb5 (switched from spaCy word vectors to sentence-transformers)
"""

from typing import Any, Dict, Optional

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
SPACY_MODEL = "en_core_web_md"


class EmbeddingService:
    """
    Text embedding via sentence-transformers + spaCy for lemmatization.

    Embeddings:
        Uses all-MiniLM-L6-v2 (384-dim float32) for semantic similarity.
        This is a transformer model trained specifically for sentence similarity,
        significantly better than spaCy word vectors for catching semantic
        overlaps like "digestive_comfort" vs "reduced_bloating".

    Lemmatization:
        Exposes spaCy en_core_web_md via the `nlp` property for lemmatization
        in CanonicalSlotService._lemmatize_name(). Not used for embeddings.

    Lazy Loading:
        Both models are loaded on first access via properties, avoiding
        startup penalty for sessions that don't need them.

    Cache:
        In-memory dict cache prevents redundant computation. Encoding the
        same text twice = one model call. Cache lives for the service
        instance lifetime (sessions are bounded: ~10 turns, ~50-100 unique texts).

    Thread Safety:
        NOT required. The turn pipeline is async but single-threaded per session.
        (AMBIGUITY RESOLUTION 2026-02-07)
    """

    def __init__(
        self,
        nlp: Optional[Any] = None,
    ):
        """
        Initialize embedding service.

        Args:
            nlp: Optional shared spaCy Language instance (e.g., from SRLService)
                 If provided, reuses the loaded model instead of loading a new one.

        REFERENCE: Phase 2 (Dual-Graph Architecture), bead lmyr
        """
        self._nlp: Optional[Any] = nlp
        self._model: Optional[Any] = None  # SentenceTransformer (lazy)
        self._cache: Dict[str, np.ndarray] = {}

    @property
    def nlp(self) -> Any:
        """
        Lazy-load spaCy model on first access.

        Used for lemmatization only (not for embeddings).

        Returns:
            spaCy Language object (en_core_web_md)

        Raises:
            OSError: If spaCy model is not installed (fail-fast per ADR-009)
        """
        if self._nlp is None:
            import spacy

            logger.info("loading_spacy_model", model=SPACY_MODEL)
            self._nlp = spacy.load(SPACY_MODEL)
            logger.info("spacy_model_loaded", model=SPACY_MODEL)
        return self._nlp

    @property
    def model(self) -> Any:
        """
        Lazy-load sentence-transformers model on first access.

        Returns:
            SentenceTransformer model (all-MiniLM-L6-v2)
        """
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("loading_embedding_model", model=EMBEDDING_MODEL)
            self._model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("embedding_model_loaded", model=EMBEDDING_MODEL)
        return self._model

    async def encode(self, text: str) -> np.ndarray:
        """
        Encode text to embedding vector using sentence-transformers.

        Checks cache first to avoid redundant computation.

        Args:
            text: Input text to encode

        Returns:
            numpy float32 array (384 dimensions for all-MiniLM-L6-v2)

        Example:
            >>> service = EmbeddingService()
            >>> embedding = await service.encode("gut_health :: digestive function")
            >>> embedding.shape
            (384,)
        """
        if text in self._cache:
            logger.debug("embedding_cache_hit", text_length=len(text))
            return self._cache[text]

        embedding = self.model.encode(text)

        self._cache[text] = embedding

        logger.debug(
            "embedding_computed",
            text_length=len(text),
            embedding_shape=embedding.shape,
        )

        return embedding

    def clear_cache(self) -> None:
        """
        Clear the embedding cache.

        Optional method - cache lives for the service instance lifetime.
        Call at session boundaries if memory is a concern (unlikely for POC).
        """
        cleared_count = len(self._cache)
        self._cache.clear()
        logger.info("embedding_cache_cleared", count=cleared_count)
