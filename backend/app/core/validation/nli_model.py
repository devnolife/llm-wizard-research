"""
Dedicated NLI Model — independent contradiction/entailment signal.

Addresses the circularity concern in the 3-layer mechanism: Layer 2
previously relied on the SAME generative LLM used elsewhere in the
pipeline. A dedicated cross-encoder NLI model (trained on SNLI/MNLI)
provides an independent, discriminative signal.

Uses sentence-transformers CrossEncoder (already a project dependency).
Model is lazy-loaded on first use and entirely optional — when the model
cannot be loaded (offline, no weights), callers fall back to marker/LLM
evidence as before.

References:
    - Bowman et al. (2015) — SNLI
    - Williams et al. (2018) — MultiNLI
"""

from typing import Dict, Optional

from loguru import logger

DEFAULT_NLI_MODEL = "cross-encoder/nli-deberta-v3-xsmall"

# Standard NLI label order for cross-encoder/nli-* models
NLI_LABELS = ["contradiction", "entailment", "neutral"]


class NLIModel:
    """
    Thin wrapper around a sentence-transformers CrossEncoder NLI model.

    predict(premise, hypothesis) → {"label": str, "scores": {label: prob}}
    """

    def __init__(self, model_name: str = DEFAULT_NLI_MODEL, device: Optional[str] = None):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._load_failed = False

    @property
    def available(self) -> bool:
        """True when the model is loaded or loadable."""
        if self._load_failed:
            return False
        if self._model is not None:
            return True
        return self._try_load()

    def _try_load(self) -> bool:
        try:
            from sentence_transformers import CrossEncoder

            logger.info(f"Loading NLI model: {self.model_name}")
            self._model = CrossEncoder(self.model_name, device=self.device)
            logger.info("NLI model ready")
            return True
        except Exception as e:
            logger.warning(f"NLI model unavailable ({e}); falling back to marker/LLM evidence")
            self._load_failed = True
            return False

    def predict(self, premise: str, hypothesis: str) -> Optional[Dict]:
        """
        Run NLI on a (premise, hypothesis) pair.

        Returns:
            {"label": "contradiction|entailment|neutral",
             "scores": {label: probability}}
            or None when the model is unavailable.
        """
        if not self.available:
            return None

        try:
            import numpy as np

            logits = self._model.predict([(premise[:512], hypothesis[:512])])[0]
            # Softmax over the three NLI classes
            exp = np.exp(logits - np.max(logits))
            probs = exp / exp.sum()
            scores = {label: float(p) for label, p in zip(NLI_LABELS, probs)}
            label = max(scores, key=scores.get)
            return {"label": label, "scores": scores}
        except Exception as e:
            logger.error(f"NLI prediction failed: {e}")
            return None

    def check_contradiction(
        self, claim_a: str, claim_b: str, threshold: float = 0.5
    ) -> Optional[Dict]:
        """
        Bidirectional contradiction check (NLI is order-sensitive).

        Returns:
            {"is_contradiction": bool, "confidence": float, "direction": str}
            or None when the model is unavailable.
        """
        forward = self.predict(claim_a, claim_b)
        if forward is None:
            return None
        backward = self.predict(claim_b, claim_a)

        f_score = forward["scores"].get("contradiction", 0.0)
        b_score = backward["scores"].get("contradiction", 0.0) if backward else 0.0
        best = max(f_score, b_score)

        return {
            "is_contradiction": best >= threshold,
            "confidence": best,
            "direction": "forward" if f_score >= b_score else "backward",
            "forward_scores": forward["scores"],
            "backward_scores": backward["scores"] if backward else None,
        }
