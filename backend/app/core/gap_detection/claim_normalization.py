"""
Claim normalization & variable alignment (LeapSpace P7).

Raw pairwise NLI over paper snippets is *insufficient* for scientific
contradiction detection: two papers that study different populations,
interventions or outcomes can produce opposite-looking statements without
actually contradicting each other. The literature therefore prescribes a
fixed pipeline order:

    normalize claims -> align variables (PICO) -> extract effect direction
    -> NLI -> adjudicate heterogeneity -> label

This module implements the first two stages. It is deliberately dependency-free
(pure Python + optional embedding model) so it can run offline and be unit
tested without a live LLM.

References:
    - LeapSpace P7 report (`leapspace/*prompt-7*.txt`): "This is why pairwise
      NLI alone is insufficient"; "relaxed matching is common when structure
      is incomplete".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from loguru import logger

# Alignment gate reported by the P7 literature review: below this score two
# claims are not considered to be talking about the same thing, so any NLI
# "contradiction" between them is non-comparable rather than contradictory.
ALIGNMENT_GATE = 0.65

# PICO-style fields the aligner tries to match. `purpose` and `setting` are
# included because non-clinical (CS/engineering) corpora rarely carry a clean
# population/intervention split.
PICO_FIELDS = (
    "population",
    "intervention",
    "comparator",
    "outcome",
    "setting",
    "purpose",
)

# Field weights — outcome and intervention carry the most meaning when
# deciding whether two claims are comparable at all.
_FIELD_WEIGHTS = {
    "population": 1.0,
    "intervention": 1.5,
    "comparator": 0.5,
    "outcome": 1.5,
    "setting": 0.75,
    "purpose": 0.75,
}

_INCREASE_PATTERNS = (
    r"\bincreas\w*", r"\bimprov\w*", r"\benhanc\w*", r"\bhigher\b", r"\bgreater\b",
    r"\boutperform\w*", r"\bboost\w*", r"\bgain\w*", r"\bpositive(?:ly)? (?:effect|impact|correlat\w*)",
    r"\bmeningkat\w*", r"\blebih tinggi\b", r"\bunggul\b",
)
_DECREASE_PATTERNS = (
    r"\bdecreas\w*", r"\breduc\w*", r"\bdeclin\w*", r"\blower\b", r"\bworse\b",
    r"\bdegrad\w*", r"\bunderperform\w*", r"\bharm\w*", r"\bloss\b",
    r"\bnegative(?:ly)? (?:effect|impact|correlat\w*)",
    r"\bmenurun\w*", r"\blebih rendah\b",
)
_NULL_PATTERNS = (
    r"\bno (?:significant )?(?:effect|difference|impact|association|correlation)\b",
    r"\bnot (?:significant|associated|correlated)\b",
    r"\bnonsignificant\b", r"\bno change\b",
    r"\btidak (?:ada )?(?:pengaruh|perbedaan|signifikan)\b",
)
_NEGATION_PATTERNS = (
    r"\bnot\b", r"\bno\b", r"\bnever\b", r"\bfail(?:s|ed)? to\b",
    r"\bcannot\b", r"\bwithout\b", r"\btidak\b", r"\bbukan\b", r"\btanpa\b",
)

# Numeric quantity + unit, e.g. "12.5 %", "3 ms", "0.84 F1".
_QUANTITY_RE = re.compile(
    r"(?P<value>[-+]?\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>%|percent|percentage points?|ms|s\b|sec\w*|minutes?|hours?|"
    r"mg|kg|db|fps|points?|f1|auc|accuracy|bleu|rouge)",
    re.IGNORECASE,
)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

# Claim-bearing sentences: only sentences that assert a finding are worth
# normalizing. Background/method sentences add noise to the NLI stage.
_CLAIM_CUES = (
    "we find", "we found", "results show", "results indicate", "our results",
    "findings suggest", "findings show", "demonstrates that", "shows that",
    "indicates that", "reveals that", "we observe", "experiments show",
    "significantly", "compared to", "outperforms", "achieves",
    "hasil menunjukkan", "temuan", "penelitian ini menemukan",
)

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "in", "on", "to", "with", "by",
    "from", "that", "this", "these", "those", "is", "are", "was", "were", "be",
    "been", "we", "our", "their", "its", "it", "as", "at", "than", "then",
    "which", "who", "when", "while", "can", "may", "also", "such", "using",
    "used", "use", "show", "shows", "shown", "study", "paper", "results",
    "yang", "dan", "atau", "dengan", "pada", "untuk", "dari", "ini", "itu",
}

_ABBREVIATION_RE = re.compile(r"\b([A-Z][A-Za-z\- ]{4,60}?)\s*\((\b[A-Z][A-Z0-9\-]{1,9})\)")


@dataclass
class NormalizedClaim:
    """A single finding decomposed into a comparable proposition.

    The tuple (subject, relation, object, direction, polarity, unit) is what
    the adjudicator compares; `pico` carries the context needed to decide
    whether two claims are about the same thing at all.
    """

    paper_ref: str
    text: str
    subject: str = ""
    relation: str = ""
    object: str = ""
    direction: str = "unknown"          # increase | decrease | no_effect | unknown
    polarity: str = "affirm"            # affirm | negate
    unit: str = ""
    value: Optional[float] = None
    pico: Dict[str, str] = field(default_factory=dict)
    terms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_ref": self.paper_ref,
            "text": self.text,
            "subject": self.subject,
            "relation": self.relation,
            "object": self.object,
            "direction": self.direction,
            "polarity": self.polarity,
            "unit": self.unit,
            "value": self.value,
            "pico": dict(self.pico),
        }

    @property
    def signed_direction(self) -> str:
        """Direction after applying negation polarity.

        "does not increase" is treated as a null/decrease-leaning claim rather
        than an increase claim, which is precisely the case raw NLI gets wrong.
        """
        if self.polarity == "negate":
            if self.direction == "increase":
                return "not_increase"
            if self.direction == "decrease":
                return "not_decrease"
        return self.direction


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _expand_abbreviations(text: str) -> str:
    """Replace `Long Form (LF)` acronyms with the long form throughout.

    Two papers using "LLM" and "large language model" for the same concept
    must not be treated as different variables.
    """
    expansions: Dict[str, str] = {}
    for long_form, short_form in _ABBREVIATION_RE.findall(text):
        expansions[short_form] = long_form.strip()
    if not expansions:
        return text
    out = text
    for short_form, long_form in expansions.items():
        out = re.sub(rf"\b{re.escape(short_form)}\b", long_form, out)
    return out


def _match_any(patterns: Sequence[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def extract_direction(text: str) -> str:
    """Classify the effect direction asserted by a sentence."""
    if _match_any(_NULL_PATTERNS, text):
        return "no_effect"
    up = _match_any(_INCREASE_PATTERNS, text)
    down = _match_any(_DECREASE_PATTERNS, text)
    if up and not down:
        return "increase"
    if down and not up:
        return "decrease"
    return "unknown"


def extract_polarity(text: str) -> str:
    """Detect sentence-level negation (after null-effect phrases are excluded)."""
    if _match_any(_NULL_PATTERNS, text):
        # "no significant effect" is a direction, not a negated claim.
        return "affirm"
    return "negate" if _match_any(_NEGATION_PATTERNS, text) else "affirm"


def extract_quantity(text: str) -> Tuple[Optional[float], str]:
    """Pull the first numeric magnitude + unit out of a claim sentence."""
    match = _QUANTITY_RE.search(text)
    if not match:
        return None, ""
    raw = match.group("value").replace(",", ".")
    try:
        value = float(raw)
    except ValueError:
        return None, ""
    unit = match.group("unit").lower()
    unit = {"percent": "%", "percentage point": "%", "percentage points": "%"}.get(unit, unit)
    return value, unit


def content_terms(text: str, min_len: int = 4) -> List[str]:
    """Lowercased content words, stopwords removed — used for lexical overlap."""
    words = re.findall(r"[A-Za-z][A-Za-z\-]{1,}", text.lower())
    return [w for w in words if len(w) >= min_len and w not in _STOPWORDS]


def _split_spo(sentence: str) -> Tuple[str, str, str]:
    """Very light subject/relation/object split around the effect verb.

    Not a parser — just enough structure to compare "X increases Y" against
    "X decreases Y" without relying on the LLM.
    """
    for patterns, _label in ((_INCREASE_PATTERNS, "increase"),
                             (_DECREASE_PATTERNS, "decrease"),
                             (_NULL_PATTERNS, "no_effect")):
        for pattern in patterns:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                subject = sentence[: match.start()].strip(" ,;:")
                relation = match.group(0).strip()
                obj = sentence[match.end():].strip(" ,;:")
                return subject[:160], relation.lower(), obj[:160]
    return sentence[:160], "", ""


def _pico_from_metadata(paper: Dict[str, Any]) -> Dict[str, str]:
    """Read PICO fields the extraction stage may have produced.

    Accepts both a nested `pico` dict and flat metadata keys, so the pipeline
    keeps working on legacy jobs that have neither (relaxed matching).
    """
    meta = paper.get("metadata") or {}
    sources: List[Dict[str, Any]] = []
    for holder in (paper, meta):
        nested = holder.get("pico")
        if isinstance(nested, dict):
            sources.append(nested)
    sources.extend([paper, meta])

    pico: Dict[str, str] = {}
    for field_name in PICO_FIELDS:
        for src in sources:
            raw = src.get(field_name)
            if isinstance(raw, (list, tuple)):
                raw = ", ".join(str(x) for x in raw)
            if raw and str(raw).strip():
                pico[field_name] = " ".join(str(raw).split())[:200]
                break
    return pico


def is_claim_sentence(sentence: str) -> bool:
    """Keep only sentences that actually assert a finding."""
    low = sentence.lower()
    if len(sentence.split()) < 5:
        return False
    if any(cue in low for cue in _CLAIM_CUES):
        return True
    # A direction word plus a comparative structure is claim-like enough.
    return extract_direction(sentence) != "unknown"


def normalize_claims(
    paper: Dict[str, Any],
    paper_ref: str,
    max_claims: int = 5,
    max_chars: int = 4000,
) -> List[NormalizedClaim]:
    """Decompose a paper's text into comparable normalized claims.

    Returns at most `max_claims` claims, preferring sentences that carry an
    explicit effect direction (those are the ones a contradiction check can
    actually reason about).
    """
    content = (paper.get("content") or "")[:max_chars]
    if not content.strip():
        return []
    content = _expand_abbreviations(content)
    pico = _pico_from_metadata(paper)

    candidates = [s.strip() for s in _SENTENCE_SPLIT_RE.split(content) if s.strip()]
    claims: List[NormalizedClaim] = []
    for sentence in candidates:
        if not is_claim_sentence(sentence):
            continue
        direction = extract_direction(sentence)
        subject, relation, obj = _split_spo(sentence)
        value, unit = extract_quantity(sentence)
        claims.append(NormalizedClaim(
            paper_ref=paper_ref,
            text=sentence[:400],
            subject=subject,
            relation=relation,
            object=obj,
            direction=direction,
            polarity=extract_polarity(sentence),
            unit=unit,
            value=value,
            pico=dict(pico),
            terms=content_terms(sentence),
        ))

    # Directional claims first — they are the comparable ones.
    claims.sort(key=lambda c: (c.direction == "unknown", -len(c.terms)))
    return claims[:max_claims]


# ---------------------------------------------------------------------------
# Variable alignment
# ---------------------------------------------------------------------------

@dataclass
class AlignmentResult:
    """Outcome of comparing two claims' study context."""

    score: float
    matched_fields: List[str] = field(default_factory=list)
    mismatched_fields: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    relaxed: bool = False
    lexical_overlap: float = 0.0

    @property
    def comparable(self) -> bool:
        return self.score >= ALIGNMENT_GATE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 3),
            "matched_fields": list(self.matched_fields),
            "mismatched_fields": list(self.mismatched_fields),
            "missing_fields": list(self.missing_fields),
            "relaxed": self.relaxed,
            "lexical_overlap": round(self.lexical_overlap, 3),
            "comparable": self.comparable,
        }


def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    set_a, set_b = set(a), set(b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _text_similarity(a: str, b: str, embedder=None) -> float:
    """Lexical Jaccard, upgraded to cosine similarity when an embedder exists."""
    lexical = _jaccard(content_terms(a), content_terms(b))
    if embedder is None:
        return lexical
    try:
        vectors = embedder.encode([a, b], normalize_embeddings=True)
        cosine = float(sum(x * y for x, y in zip(vectors[0], vectors[1])))
        return max(lexical, max(0.0, min(1.0, cosine)))
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug(f"Embedding similarity failed, using lexical: {exc}")
        return lexical


def align_claims(
    claim_a: NormalizedClaim,
    claim_b: NormalizedClaim,
    embedder=None,
) -> AlignmentResult:
    """Score how comparable two claims are (PICO alignment).

    When PICO fields are absent — the common case for CS corpora — the score
    falls back to lexical/semantic overlap of the claim text itself and is
    marked `relaxed`, per the P7 note that "relaxed matching is common when
    structure is incomplete". Relaxed scores are capped so that a missing
    context can never masquerade as a confirmed match.
    """
    matched: List[str] = []
    mismatched: List[str] = []
    missing: List[str] = []
    weighted_sum = 0.0
    weight_total = 0.0

    for field_name in PICO_FIELDS:
        value_a = claim_a.pico.get(field_name, "")
        value_b = claim_b.pico.get(field_name, "")
        if not value_a or not value_b:
            missing.append(field_name)
            continue
        weight = _FIELD_WEIGHTS[field_name]
        similarity = _text_similarity(value_a, value_b, embedder)
        weighted_sum += weight * similarity
        weight_total += weight
        (matched if similarity >= 0.5 else mismatched).append(field_name)

    lexical_overlap = _text_similarity(claim_a.text, claim_b.text, embedder)

    if weight_total == 0.0:
        # No structured context on either side: relaxed matching only.
        return AlignmentResult(
            score=round(min(0.85, lexical_overlap), 3),
            missing_fields=missing,
            relaxed=True,
            lexical_overlap=lexical_overlap,
        )

    structured = weighted_sum / weight_total
    coverage = weight_total / sum(_FIELD_WEIGHTS.values())
    # Partial structure => blend structured score with text overlap, weighted
    # by how much of the PICO frame was actually available.
    score = coverage * structured + (1.0 - coverage) * lexical_overlap
    return AlignmentResult(
        score=round(max(0.0, min(1.0, score)), 3),
        matched_fields=matched,
        mismatched_fields=mismatched,
        missing_fields=missing,
        relaxed=bool(missing),
        lexical_overlap=lexical_overlap,
    )
