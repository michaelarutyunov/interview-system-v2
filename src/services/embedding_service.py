"""
Text embedding service using spaCy word vectors.

Computes embeddings for canonical slot name similarity matching in the
dual-graph architecture. Uses spaCy en_core_web_md word vectors
(300-dim, float32) for cosine similarity comparisons.

Bead: lmyr (Phase 2: Dual-Graph Architecture)
"""

from typing import Any, Dict, Optional
import structlog

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """
    Text embedding via spaCy word vectors.

    Computes 300-dimensional float32 embeddings using spaCy's en_core_web_md
    model. Embeddings are used for canonical slot similarity matching.

    Lazy Loading:
        The spaCy model is loaded on first access via the `nlp` property,
        avoiding startup penalty for sessions that don't need embeddings.

    Cache:
        In-memory dict cache prevents redundant computation. Encoding the
        same text twice = one spaCy call. Cache lives for the service
        instance lifetime (sessions are bounded: ~10 turns, ~50-100 unique texts).

    Thread Safety:
        NOT required. The turn pipeline is async but single-threaded per session.
        (AMBIGUITY RESOLUTION 2026-02-07)
    """

    def __init__(
        self,
        model_name: str = "en_core_web_md",
        nlp: Optional[Any] = None,
    ):
        """
        Initialize embedding service.

        Args:
            model_name: spaCy model name (default: en_core_web_md)
            nlp: Optional shared spaCy Language instance (e.g., from SRLService)
                 If provided, reuses the loaded model instead of loading a new one.

        REFERENCE: Phase 2 (Dual-Graph Architecture), bead lmyr
        """
        self.model_name = model_name
        self._nlp: Optional[Any] = nlp  # Reuse if provided (shared with SRLService)
        self._cache: Dict[str, Any] = {}  # text -> numpy embedding cache

    @property
    def nlp(self) -> Any:
        """
        Lazy-load spaCy model on first access.

        Returns:
            spaCy Language object (en_core_web_md)

        Raises:
            OSError: If spaCy model is not installed (fail-fast per ADR-009)
        """
        if self._nlp is None:
            import spacy

            logger.info("loading_spacy_model", model=self.model_name)
            self._nlp = spacy.load(self.model_name)
            logger.info("spacy_model_loaded", model=self.model_name)
        return self._nlp

    async def encode(self, text: str) -> Any:
        """
        Encode text to embedding vector.

        Checks cache first to avoid redundant spaCy computation.
        Empty string returns the model's zero vector (spaCy's natural behavior).

        Args:
            text: Input text to encode

        Returns:
            numpy float32 array (300 dimensions for en_core_web_md)

        Example:
            >>> service = EmbeddingService()
            >>> embedding = await service.encode("energy stability")
            >>> embedding.shape
            (300,)
        """
        # Check cache first
        if text in self._cache:
            logger.debug("embedding_cache_hit", text_length=len(text))
            return self._cache[text]

        # Compute embedding via spaCy
        doc = self.nlp(text)
        embedding = doc.vector  # 300-dim float32 numpy array

        # Cache result
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

        REFERENCE: Phase 2 (Dual-Graph Architecture), bead lmyr
        """
        cleared_count = len(self._cache)
        self._cache.clear()
        logger.info("embedding_cache_cleared", count=cleared_count)
