"""
Indicator 4 — Ketiadaan Dukungan Bukti (evidence-support gap).

Grounded in the LeapSpace P5/P9 reviews, which frame *retrieval failure* as a
first-class gap signal: a claim that a retrieval-augmented system cannot ground
in a primary source is evidence about the literature, not merely a failure of
the retriever.

This is deliberately distinct from the three existing indicators:

    INCOMPLETENESS   an aspect is never discussed
    SUPPORT_GAP      an aspect IS discussed and asserted, yet no primary
                     evidence for it can be retrieved from the corpus

The distinction matters because it separates "nobody looked" from "everybody
asserts, nobody demonstrates" — the second is the classic citation-echo failure
mode where a claim propagates through reviews without an empirical anchor.

Method
------
For every normalized claim, run leave-one-out retrieval over the rest of the
corpus and score the best available corroboration::

    support(c) = max_{p != source(c)} sim(c, passage p)

    unsupported        support(c) <  SUPPORT_FLOOR
    weakly supported   SUPPORT_FLOOR <= support(c) < SUPPORT_GATE
    supported          support(c) >= SUPPORT_GATE

Two amplifiers, both taken from the report's failure-mode discussion:

* **citation echo** — the claim recurs in >= ECHO_MIN_PAPERS papers while every
  occurrence sits in a secondary (review/survey) context, so repetition is
  mistaken for evidence.
* **unanchored hedge** — the claim is hedged ("may", "is believed to") and
  carries no quantity, so it never commits to a measurable result.

A claim is only reported when it is asserted with enough force to matter; a
purely speculative sentence is not a gap, it is a suggestion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from loguru import logger

from .claim_normalization import NormalizedClaim, content_terms, normalize_claims
from .semantic_match import SemanticMatcher

# Below this, no passage in the rest of the corpus resembles the claim.
SUPPORT_FLOOR = 0.45
# At or above this the claim is considered corroborated by another paper.
SUPPORT_GATE = 0.62
# Lexical similarity is systematically lower than embedding cosine, so the
# fallback path uses its own (looser) bands rather than silently declaring
# everything unsupported when no embedder is available.
SUPPORT_FLOOR_LEXICAL = 0.34
SUPPORT_GATE_LEXICAL = 0.50
# Two papers asserting the same thing: paraphrase-level similarity.
ECHO_THRESHOLD = 0.70
ECHO_THRESHOLD_LEXICAL = 0.55
# A claim must recur in at least this many papers to count as a citation echo.
ECHO_MIN_PAPERS = 2
# Minimum share of unsupported claims before the corpus-level indicator fires.
UNSUPPORTED_RATIO_MIN = 0.30
# Never report more than this many claims in one indicator.
MAX_REPORTED_CLAIMS = 6

_HEDGE_RE = re.compile(
    r"\b(may|might|could|possibly|potentially|likely|is believed|are believed|"
    r"suggests?\s+that|appears?\s+to|seems?\s+to|presumably|arguably)\b",
    re.IGNORECASE,
)

_SECONDARY_RE = re.compile(
    r"\b(review|survey|overview|systematic literature|state of the art|"
    r"taxonomy|bibliometric|meta-?analysis)\b",
    re.IGNORECASE,
)

_PRIMARY_EVIDENCE_RE = re.compile(
    r"\b(we (?:conduct|perform|evaluat|measur|implement|train|test)\w*|"
    r"experiment\w*|dataset|benchmark|participants?|our (?:results?|study|"
    r"evaluation|experiments?)|empirical|ablation|case study|field (?:study|"
    r"trial)|measured|sample size|n\s*=\s*\d+)\b",
    re.IGNORECASE,
)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class SupportAssessment:
    """Retrieval-grounding verdict for one claim."""

    claim: NormalizedClaim
    support_score: float
    status: str                       # unsupported | weakly_supported | supported
    gate: float = SUPPORT_GATE
    best_source: str = ""
    best_passage: str = ""
    echo_papers: List[str] = field(default_factory=list)
    hedged: bool = False
    source_is_secondary: bool = False
    reasons: List[str] = field(default_factory=list)

    @property
    def is_gap(self) -> bool:
        """Only unsupported or echo-amplified weak claims count as a gap."""
        if self.status == "unsupported":
            return True
        return self.status == "weakly_supported" and bool(self.echo_papers)

    @property
    def severity(self) -> float:
        """How badly the claim lacks grounding, in [0, 1]."""
        gate = self.gate or SUPPORT_GATE
        base = max(0.0, min(1.0, (gate - self.support_score) / gate))
        if self.echo_papers:
            base = min(1.0, base + 0.10 * len(self.echo_papers))
        if self.hedged:
            base = min(1.0, base + 0.05)
        if self.source_is_secondary:
            base = min(1.0, base + 0.05)
        return round(base, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim.text,
            "paper_ref": self.claim.paper_ref,
            "support_score": round(self.support_score, 4),
            "status": self.status,
            "severity": self.severity,
            "best_source": self.best_source,
            "best_passage": self.best_passage[:240],
            "echo_papers": self.echo_papers[:5],
            "hedged": self.hedged,
            "source_is_secondary": self.source_is_secondary,
            "reasons": self.reasons,
        }


@dataclass
class SupportReport:
    """Corpus-level summary of evidence support."""

    assessments: List[SupportAssessment] = field(default_factory=list)
    total_claims: int = 0
    unsupported: int = 0
    weakly_supported: int = 0
    supported: int = 0
    echo_claims: int = 0

    @property
    def unsupported_ratio(self) -> float:
        if not self.total_claims:
            return 0.0
        return round(self.unsupported / self.total_claims, 4)

    @property
    def gaps(self) -> List[SupportAssessment]:
        ranked = [a for a in self.assessments if a.is_gap]
        ranked.sort(key=lambda a: a.severity, reverse=True)
        return ranked

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_claims": self.total_claims,
            "unsupported": self.unsupported,
            "weakly_supported": self.weakly_supported,
            "supported": self.supported,
            "echo_claims": self.echo_claims,
            "unsupported_ratio": self.unsupported_ratio,
            "gaps": [a.to_dict() for a in self.gaps[:MAX_REPORTED_CLAIMS]],
        }


# ---------------------------------------------------------------------------
# Corpus indexing
# ---------------------------------------------------------------------------

def _paper_text(paper: Dict[str, Any], max_chars: int = 6000) -> str:
    for key in ("content", "abstract", "summary"):
        value = paper.get(key)
        if value:
            return str(value)[:max_chars]
    return ""


def is_secondary_source(paper: Dict[str, Any]) -> bool:
    """Detect review/survey papers, whose assertions are not primary evidence."""
    haystack = " ".join(
        str(paper.get(k, "")) for k in ("title", "publication_type", "doc_type")
    )
    if _SECONDARY_RE.search(haystack):
        return True
    text = _paper_text(paper, 800)
    return bool(_SECONDARY_RE.search(text[:400]))


def has_primary_evidence(passage: str) -> bool:
    """Whether a passage reads like reported primary evidence."""
    return bool(_PRIMARY_EVIDENCE_RE.search(passage))


def build_evidence_index(
    papers: Sequence[Dict[str, Any]],
    paper_ref: Any,
    max_sentences_per_paper: int = 40,
) -> List[Tuple[str, str, bool]]:
    """Index the corpus as (paper_ref, sentence, is_primary_evidence) triples.

    Only sentences that look like reported evidence are indexed: matching a
    claim against another paper's *introduction* would corroborate rhetoric
    with rhetoric, which is exactly the failure this indicator exists to catch.
    """
    index: List[Tuple[str, str, bool]] = []
    for paper in papers:
        ref = paper_ref(paper)
        if not ref:
            continue
        text = _paper_text(paper)
        if not text:
            continue
        sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
        kept = 0
        for sentence in sentences:
            if len(sentence.split()) < 6:
                continue
            primary = has_primary_evidence(sentence)
            if not primary:
                continue
            index.append((ref, sentence[:400], primary))
            kept += 1
            if kept >= max_sentences_per_paper:
                break
    return index


# ---------------------------------------------------------------------------
# Retrieval-failure scoring
# ---------------------------------------------------------------------------

def support_bands(matcher: SemanticMatcher) -> Tuple[float, float, float]:
    """(floor, gate, echo threshold) appropriate to the matcher's mode."""
    if matcher.uses_embeddings:
        return SUPPORT_FLOOR, SUPPORT_GATE, ECHO_THRESHOLD
    return SUPPORT_FLOOR_LEXICAL, SUPPORT_GATE_LEXICAL, ECHO_THRESHOLD_LEXICAL


def _echo_papers(
    claim: NormalizedClaim,
    claims_by_paper: Dict[str, List[NormalizedClaim]],
    matcher: SemanticMatcher,
    threshold: Optional[float] = None,
) -> List[str]:
    """Other papers asserting the same thing (repetition, not corroboration)."""
    if threshold is None:
        threshold = support_bands(matcher)[2]
    echoes: List[str] = []
    for ref, others in claims_by_paper.items():
        if ref == claim.paper_ref:
            continue
        for other in others:
            score, _ = matcher.similarity(claim.text, other.text)
            if score >= threshold:
                echoes.append(ref)
                break
    return echoes


def assess_support(
    claim: NormalizedClaim,
    evidence_index: Sequence[Tuple[str, str, bool]],
    matcher: SemanticMatcher,
    claims_by_paper: Optional[Dict[str, List[NormalizedClaim]]] = None,
    secondary_refs: Optional[Sequence[str]] = None,
) -> SupportAssessment:
    """Leave-one-out retrieval grounding for a single claim."""
    floor, gate, echo_threshold = support_bands(matcher)
    best_score = 0.0
    best_source = ""
    best_passage = ""
    claim_terms = set(claim.terms or content_terms(claim.text))

    for ref, sentence, _primary in evidence_index:
        if ref == claim.paper_ref:
            continue  # leave-one-out: a paper cannot corroborate itself
        # Cheap lexical prefilter before paying for an embedding comparison.
        if claim_terms and not (claim_terms & set(content_terms(sentence))):
            continue
        score, _ = matcher.similarity(claim.text, sentence)
        if score > best_score:
            best_score, best_source, best_passage = score, ref, sentence

    if best_score >= gate:
        status = "supported"
    elif best_score >= floor:
        status = "weakly_supported"
    else:
        status = "unsupported"

    echoes = (
        _echo_papers(claim, claims_by_paper, matcher, echo_threshold)
        if claims_by_paper else []
    )
    hedged = bool(_HEDGE_RE.search(claim.text)) and claim.value is None
    secondary = claim.paper_ref in set(secondary_refs or [])

    reasons: List[str] = []
    if status == "unsupported":
        reasons.append(
            f"tidak ada paragraf bukti primer di korpus yang mendukung klaim ini "
            f"(kemiripan terbaik {best_score:.2f} < {floor:.2f})"
        )
    elif status == "weakly_supported":
        reasons.append(
            f"dukungan lemah: kemiripan terbaik {best_score:.2f} "
            f"masih di bawah ambang {gate:.2f}"
        )
    if len(echoes) >= ECHO_MIN_PAPERS:
        reasons.append(
            f"klaim diulang {len(echoes)} jurnal lain tanpa bukti primer baru "
            f"(citation echo)"
        )
    elif echoes:
        reasons.append(f"klaim juga diasersikan {len(echoes)} jurnal lain")
    if hedged:
        reasons.append("klaim berpagar (hedged) dan tanpa angka terukur")
    if secondary:
        reasons.append("sumber klaim adalah review/survei, bukan studi primer")

    return SupportAssessment(
        claim=claim,
        support_score=round(best_score, 4),
        status=status,
        gate=gate,
        best_source=best_source,
        best_passage=best_passage,
        echo_papers=echoes,
        hedged=hedged,
        source_is_secondary=secondary,
        reasons=reasons,
    )


def analyze_support(
    papers: Sequence[Dict[str, Any]],
    paper_ref,
    matcher: Optional[SemanticMatcher] = None,
    max_claims_per_paper: int = 4,
) -> SupportReport:
    """Run evidence-support analysis over the whole corpus."""
    report = SupportReport()
    if len(papers) < 2:
        return report

    matcher = matcher or SemanticMatcher()
    evidence_index = build_evidence_index(papers, paper_ref)
    if not evidence_index:
        logger.debug("Support gap: no primary-evidence sentences indexed")

    claims_by_paper: Dict[str, List[NormalizedClaim]] = {}
    secondary_refs: List[str] = []
    for paper in papers:
        ref = paper_ref(paper)
        if not ref:
            continue
        claims = normalize_claims(paper, ref, max_claims=max_claims_per_paper)
        if claims:
            claims_by_paper[ref] = claims
        if is_secondary_source(paper):
            secondary_refs.append(ref)

    for claims in claims_by_paper.values():
        for claim in claims:
            assessment = assess_support(
                claim,
                evidence_index,
                matcher,
                claims_by_paper=claims_by_paper,
                secondary_refs=secondary_refs,
            )
            report.assessments.append(assessment)
            report.total_claims += 1
            if assessment.status == "unsupported":
                report.unsupported += 1
            elif assessment.status == "weakly_supported":
                report.weakly_supported += 1
            else:
                report.supported += 1
            if len(assessment.echo_papers) >= ECHO_MIN_PAPERS:
                report.echo_claims += 1

    return report


def support_confidence(report: SupportReport) -> float:
    """Confidence that the corpus really has an evidence-support gap.

    Driven by how widespread the failure is rather than by any single claim:
    one ungrounded sentence is noise, a third of the corpus's claims being
    ungrounded is a property of the literature.
    """
    if report.total_claims < 3:
        return 0.0
    ratio = report.unsupported_ratio
    if ratio < UNSUPPORTED_RATIO_MIN:
        return 0.0
    confidence = 0.45 + 0.40 * min(1.0, (ratio - UNSUPPORTED_RATIO_MIN) / 0.45)
    if report.echo_claims:
        confidence += min(0.10, 0.03 * report.echo_claims)
    # More claims examined means a more stable estimate.
    if report.total_claims < 8:
        confidence -= 0.08
    return round(max(0.0, min(0.92, confidence)), 4)
