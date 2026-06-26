"""
Cross-Encoder Reranker for two-stage retrieval.

The bi-encoder (all-MiniLM-L6-v2) used by the vector store is fast but scores
the query and each passage *independently*. A cross-encoder instead scores the
(query, passage) pair jointly, which is markedly more accurate at ordering the
top candidates. The standard pattern is two-stage retrieval:

    1. bi-encoder retrieves a broad candidate set (high recall),
    2. cross-encoder re-scores those candidates (high precision).

This module wraps a pretrained cross-encoder (sentence-transformers, already a
project dependency). It degrades gracefully to ``available = False`` when the
model weights cannot be loaded (e.g. offline), so callers can fall back to the
heuristic reranker without failing.
"""

from typing import List, Optional, Tuple

from loguru import logger

# A small, fast, well-tested reranker trained on MS MARCO passage ranking.
DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class CrossEncoderReranker:
    """Thin wrapper around a sentence-transformers CrossEncoder reranker."""

    def __init__(self, model_name: str = DEFAULT_RERANKER_MODEL, device: Optional[str] = None):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._loaded = False

    @property
    def available(self) -> bool:
        """Lazily attempt to load the model; report whether it is usable."""
        if not self._loaded:
            self._loaded = True
            self._try_load()
        return self._model is not None

    def _try_load(self) -> bool:
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading reranker model: {self.model_name}")
            self._model = CrossEncoder(self.model_name, device=self.device)
            return True
        except Exception as e:
            logger.warning(f"Reranker model unavailable ({self.model_name}): {e}")
            self._model = None
            return False

    def score(self, query: str, passages: List[str]) -> Optional[List[float]]:
        """
        Score each passage against the query. Higher is more relevant.

        Returns None when the model is unavailable so callers can fall back.
        """
        if not self.available or not passages:
            return None
        try:
            pairs = [(query[:512], (p or "")[:512]) for p in passages]
            scores = self._model.predict(pairs)
            return [float(s) for s in scores]
        except Exception as e:
            logger.error(f"Reranker scoring failed: {e}")
            return None

    def rerank(
        self,
        query: str,
        passages: List[str],
        top_k: Optional[int] = None,
    ) -> Optional[List[Tuple[int, float]]]:
        """
        Rerank passages for a query.

        Returns a list of ``(original_index, score)`` sorted by descending
        relevance, or None when the model is unavailable.
        """
        scores = self.score(query, passages)
        if scores is None:
            return None
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k] if top_k else ranked
