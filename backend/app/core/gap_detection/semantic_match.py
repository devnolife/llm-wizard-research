"""
Semantic matching helpers (LeapSpace P8).

`_detect_incompleteness` originally decided whether an expected aspect was
covered with an exact lowercase string comparison, so "reproducibility" and
"replication of results" counted as two different aspects and the second was
reported as an uncovered gap. That is a pure false-positive generator.

This module provides embedding-backed matching with a deterministic lexical
fallback, so the pipeline keeps working offline and on machines without the
sentence-transformers model warmed up.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from loguru import logger

# Cosine/lexical similarity above which an expected aspect counts as covered.
# Deliberately conservative: a missed match only costs recall on one aspect,
# whereas a spurious "uncovered aspect" becomes a claimed research gap.
ASPECT_MATCH_THRESHOLD = 0.62

# Similarity above which a lexical (non-embedding) match is accepted. Higher
# than the embedding threshold because token overlap is a coarser signal.
LEXICAL_MATCH_THRESHOLD = 0.55

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "in", "on", "to", "with",
    "by", "from", "vs", "versus", "such", "as", "its", "their", "this",
    "that", "these", "those", "considerations", "consideration", "issues",
    "aspects", "aspect", "analysis", "study", "research",
}

# Morphological suffixes stripped before lexical comparison so that
# "reproducibility" and "reproducible" collapse to the same stem.
_SUFFIXES = (
    "ability", "ibility", "ization", "isation", "iveness", "fulness",
    "ations", "ation", "ities", "ility", "ments", "ment", "ness", "ible",
    "able", "ing", "ies", "ed", "es", "s",
)

# Minimum stem length for prefix-based fuzzy matching ("reproduc" ~
# "reproducib"), which catches morphological variants the suffix table misses.
_PREFIX_MATCH_MIN = 5


def _stems_match(a: str, b: str) -> bool:
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    return len(shorter) >= _PREFIX_MATCH_MIN and longer.startswith(shorter)


def _stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def normalize_phrase(text: str) -> List[str]:
    """Content stems of a phrase, stopwords removed."""
    words = re.findall(r"[a-z][a-z\-]{2,}", (text or "").lower())
    return [_stem(w) for w in words if w not in _STOPWORDS]


def lexical_similarity(a: str, b: str) -> float:
    """Stem-level overlap with prefix-fuzzy matching and a containment bonus.

    Containment matters because expected aspects are short phrases that are
    often fully contained in a longer covered phrase ("cost" vs
    "implementation cost analysis").
    """
    stems_a, stems_b = set(normalize_phrase(a)), set(normalize_phrase(b))
    if not stems_a or not stems_b:
        return 0.0
    matched = sum(1 for sa in stems_a if any(_stems_match(sa, sb) for sb in stems_b))
    if not matched:
        return 0.0
    union = len(stems_a) + len(stems_b) - matched
    jaccard = matched / max(1, union)
    containment = matched / min(len(stems_a), len(stems_b))
    return max(jaccard, 0.85 * containment)


@dataclass
class AspectMatch:
    """Why a given expected aspect was (or was not) considered covered."""

    aspect: str
    covered: bool
    best_match: str = ""
    score: float = 0.0
    method: str = "lexical"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aspect": self.aspect,
            "covered": self.covered,
            "best_match": self.best_match,
            "score": round(self.score, 3),
            "method": self.method,
        }


class SemanticMatcher:
    """Similarity between short phrases, embedding-backed when possible.

    The embedder is whatever `SentenceTransformer` instance the vector store
    already loaded — no second model is pulled into memory.
    """

    def __init__(self, embedder=None, threshold: float = ASPECT_MATCH_THRESHOLD):
        self.embedder = embedder
        self.threshold = threshold
        self._cache: Dict[str, Any] = {}
        self._embedding_failed = False

    @classmethod
    def from_vector_store(cls, vector_store=None, **kwargs) -> "SemanticMatcher":
        embedder = getattr(vector_store, "embedding_model", None) if vector_store else None
        return cls(embedder=embedder, **kwargs)

    @property
    def uses_embeddings(self) -> bool:
        return self.embedder is not None and not self._embedding_failed

    def _encode(self, texts: Sequence[str]) -> Optional[List[Any]]:
        if not self.uses_embeddings:
            return None
        missing = [t for t in texts if t not in self._cache]
        if missing:
            try:
                vectors = self.embedder.encode(missing, normalize_embeddings=True)
                for text, vector in zip(missing, vectors):
                    self._cache[text] = vector
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"Aspect embedding failed, falling back to lexical: {exc}")
                self._embedding_failed = True
                return None
        return [self._cache[t] for t in texts]

    def similarity(self, a: str, b: str) -> Tuple[float, str]:
        """Return (score, method) for two phrases."""
        lexical = lexical_similarity(a, b)
        vectors = self._encode([a, b])
        if vectors is None:
            return lexical, "lexical"
        cosine = float(sum(x * y for x, y in zip(vectors[0], vectors[1])))
        cosine = max(0.0, min(1.0, cosine))
        # Keep whichever signal is stronger: embeddings catch paraphrase,
        # lexical overlap catches domain jargon the model has not seen.
        if lexical >= cosine:
            return lexical, "lexical"
        return cosine, "embedding"

    def best_match(
        self, aspect: str, candidates: Sequence[str]
    ) -> AspectMatch:
        """Find the covered phrase closest to an expected aspect."""
        if not candidates:
            return AspectMatch(aspect=aspect, covered=False)
        best_score, best_text, best_method = 0.0, "", "lexical"
        for candidate in candidates:
            score, method = self.similarity(aspect, candidate)
            if score > best_score:
                best_score, best_text, best_method = score, candidate, method
        threshold = (
            self.threshold if best_method == "embedding" else LEXICAL_MATCH_THRESHOLD
        )
        return AspectMatch(
            aspect=aspect,
            covered=best_score >= threshold,
            best_match=best_text,
            score=best_score,
            method=best_method,
        )

    def split_covered(
        self, expected: Sequence[str], covered: Sequence[str]
    ) -> Tuple[List[AspectMatch], List[AspectMatch]]:
        """Partition expected aspects into (covered, uncovered) matches."""
        matches = [self.best_match(a, covered) for a in expected]
        return (
            [m for m in matches if m.covered],
            [m for m in matches if not m.covered],
        )
