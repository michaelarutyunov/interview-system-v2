"""Text embedding service using sentence-transformers for semantic similarity.

Computes embeddings for canonical slot similarity matching in the dual-graph
architecture. Uses all-MiniLM-L6-v2 (384-dim, float32) for semantic
cosine similarity comparisons to detect paraphrases and group surface nodes
into abstract canonical slots.

Also provides spaCy model access for lemmatization in CanonicalSlotService.
"""

from typing import Any, Dict, Optional

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
SPACY_MODEL = "en_core_web_md"


class EmbeddingService:
    """Text embedding service using sentence-transformers and spaCy for lemmatization.

    Provides semantic similarity computation for canonical slot matching to detect
    paraphrases and group surface nodes into abstract canonical slots in the
    dual-graph architecture.

    Embeddings:
        Uses all-MiniLM-L6-v2 (384-dim float32) for semantic similarity,
        a transformer model specifically trained for sentence similarity. This is
        significantly better than spaCy word vectors for catching semantic overlaps
        like "digestive_comfort" vs "reduced_bloating".

    Lemmatization:
        Exposes spaCy en_core_web_md via the `nlp` property for lemmatization
        in CanonicalSlotService._lemmatize_name().

    Lazy Loading:
        Both models are loaded on first access via properties to avoid startup
        penalty for sessions that don't need them.

    Cache:
        In-memory dict cache prevents redundant computation. Cache lives for the
        service instance lifetime (sessions are bounded: ~10 turns, ~50-100 unique texts).
    """

    def __init__(
        self,
        nlp: Optional[Any] = None,
    ):
        """Initialize embedding service with optional shared spaCy model.

        Args:
            nlp: Optional shared spaCy Language instance (e.g., from SRLService).
                 If provided, reuses the loaded model instead of loading a new one.
        """
        self._nlp: Optional[Any] = nlp
        self._model: Optional[Any] = None  # SentenceTransformer (lazy)
        self._cache: Dict[str, np.ndarray] = {}

    @property
    def nlp(self) -> Any:
        """Lazy-load spaCy model for lemmatization on first access.

        Used by CanonicalSlotService._lemmatize_name() for text normalization.

        Returns:
            spaCy Language object (en_core_web_md)

        Raises:
            OSError: If spaCy model is not installed (fail-fast)
        """
        if self._nlp is None:
            import spacy

            logger.info("loading_spacy_model", model=SPACY_MODEL)
            self._nlp = spacy.load(SPACY_MODEL)
            logger.info("spacy_model_loaded", model=SPACY_MODEL)
        return self._nlp

    @property
    def model(self) -> Any:
        """Lazy-load sentence-transformers model on first access.

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
        """Encode text to embedding vector using sentence-transformers.

        Checks cache first to avoid redundant computation for duplicate text.

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
        """Clear the embedding cache.

        Optional method - cache lives for the service instance lifetime.
        Call at session boundaries if memory is a concern.
        """
        cleared_count = len(self._cache)
        self._cache.clear()
        logger.info("embedding_cache_cleared", count=cleared_count)
