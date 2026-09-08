"""Workflow-stage mining — methodological homogeneity from per-paper pipelines.

The legacy methodology check (``GapAnalyzer._extract_methods``) matched ten
keywords ("survey", "deep learning", ...) against the paper text and, when
nothing matched, reported "all N papers use similar methodology (unidentified)"
— a non-finding. The LeapSpace P5 review lists *workflow-stage mining* (Zhang &
Zhang 2025) as the method family for exactly this case: reconstruct each
paper's methodological pipeline as a fixed set of stages, then look for stages
that are never varied across the corpus.

Design (mirrors the weakness review so the thesis has ONE grounding rule):

* one LLM call per paper returns, for each of eight stages, a short value plus
  a 5-20 word verbatim quote; a stage the paper does not state is left empty
  and the prompt forbids inventing one;
* every quote is re-verified against the paper text with the same fuzzy
  threshold used for author-stated weaknesses (``QUOTE_MATCH_THRESHOLD``);
* cross-paper comparison clusters stage values with the ``SemanticMatcher``
  already used for aspect coverage (embedding 0.62 / lexical 0.55) — no new
  thresholds are introduced;
* a stage is *homogeneous* when every paper that states it falls into ONE
  variant and at least ``MIN_PAPERS_FOR_HOMOGENEITY`` papers state it (the
  same ">= 3 papers" floor as the legacy check). Papers that do not state a
  stage are reported, never counted as agreeing.

Everything here is evidence for the INCOMPLETENESS indicator; the analyzer
keeps the legacy confidence formula.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .quote_grounding import QUOTE_MATCH_THRESHOLD, fuzzy_contains
from .semantic_match import SemanticMatcher

# (key, Indonesian label, what the LLM should look for)
STAGES = (
    ("data_source", "Sumber data",
     "sumber data/dataset (nama dataset, jenis data, asal data)"),
    ("data_collection", "Pengumpulan data",
     "cara pengumpulan/akuisisi data (jumlah sampel, alat akuisisi, periode)"),
    ("preprocessing", "Prapemrosesan",
     "prapemrosesan: pembersihan, normalisasi, segmentasi, augmentasi"),
    ("representation_features", "Representasi/fitur",
     "representasi data atau ekstraksi fitur"),
    ("method_model", "Metode/model",
     "metode, algoritma, atau model utama"),
    ("evaluation_metrics", "Metrik evaluasi",
     "metrik evaluasi (akurasi, F1, waktu, presisi, dll.)"),
    ("validation_design", "Desain validasi",
     "desain validasi: pembagian data, cross-validation, uji statistik, baseline pembanding"),
    ("tools_environment", "Alat/lingkungan",
     "perangkat lunak, kerangka kerja, atau perangkat keras yang dipakai"),
)
STAGE_KEYS = tuple(key for key, _, _ in STAGES)
STAGE_LABELS = {key: label for key, label, _ in STAGES}

# Same floor as the legacy methodology check ("len(papers) >= 3").
MIN_PAPERS_FOR_HOMOGENEITY = 3

# Chunk sections that describe how the study was done, in priority order.
METHOD_SECTIONS = ("methods", "results")
WORKFLOW_CONTEXT_CHARS = 3000
# Below this the section chunks are too thin to reconstruct a pipeline from.
_MIN_SECTION_CHARS = 600

_STAGE_ALIASES = {
    "dataset": "data_source", "data": "data_source", "sumber_data": "data_source",
    "collection": "data_collection", "pengumpulan_data": "data_collection",
    "preprocess": "preprocessing", "prapemrosesan": "preprocessing",
    "features": "representation_features", "representation": "representation_features",
    "fitur": "representation_features",
    "method": "method_model", "model": "method_model", "metode": "method_model",
    "evaluation": "evaluation_metrics", "metrics": "evaluation_metrics",
    "evaluasi": "evaluation_metrics",
    "validation": "validation_design", "validasi": "validation_design",
    "tools": "tools_environment", "environment": "tools_environment",
    "alat": "tools_environment",
}


def build_workflow_prompt(title: str, context_text: str) -> str:
    """Prompt for ONE paper; same grounding contract as the weakness review."""
    stage_lines = "\n".join(f"- {key}: {what}" for key, _, what in STAGES)
    return (
        "Anda adalah reviewer metodologi jurnal ilmiah. Rekonstruksi TAHAPAN METODE dari SATU "
        "jurnal berikut berdasarkan isinya (bukan tebakan umum).\n\n"
        "Untuk SETIAP tahap isi dua hal:\n"
        "- \"value\": frasa singkat (2-8 kata, bahasa asli teks) yang menyebut apa yang dipakai "
        "pada tahap itu;\n"
        "- \"kutipan\": potongan kalimat 5-20 kata yang DISALIN PERSIS (verbatim) dari teks tempat "
        "tahap itu dinyatakan.\n"
        "Jika teks TIDAK menyatakan suatu tahap, isi KEDUANYA dengan string kosong \"\". JANGAN "
        "mengarang nilai atau kutipan; kutipan yang tidak ada di teks lebih buruk daripada kosong.\n\n"
        f"Tahap:\n{stage_lines}\n\n"
        f"Judul: {title}\n"
        f"[TEKS METODE/EKSPERIMEN]\n{context_text}\n\n"
        "Kembalikan HANYA JSON (tanpa teks lain) dengan tepat 8 kunci tahap di atas, misalnya: "
        '{"data_source": {"value": "...", "kutipan": "..."}, "data_collection": {...}, ...}'
    )


def select_workflow_context(
    chunks: Sequence[Any],
    fallback_text: str,
    max_chars: int = WORKFLOW_CONTEXT_CHARS,
) -> str:
    """Method/result section chunks first; the document head when sections are thin.

    Accepts the ingestion chunk objects (``.content``/``.metadata``) as well as
    pipeline chunk dicts (``text`` + ``section_normalized``).
    """
    picked: List[str] = []
    for wanted in METHOD_SECTIONS:
        for chunk in chunks or []:
            text, section, is_reference = _chunk_view(chunk)
            if is_reference or section != wanted or not text.strip():
                continue
            picked.append(text.strip())
    joined = "\n".join(picked)
    if len(joined) < _MIN_SECTION_CHARS:
        joined = (joined + "\n" + (fallback_text or "")).strip()
    return joined[:max_chars]


def _chunk_view(chunk: Any):
    if isinstance(chunk, Mapping):
        meta = chunk.get("metadata") or chunk
        text = chunk.get("text") or chunk.get("content") or ""
    else:
        meta = getattr(chunk, "metadata", None) or {}
        text = getattr(chunk, "content", "") or getattr(chunk, "text", "") or ""
    section = str(meta.get("section_normalized") or "").lower()
    return str(text), section, bool(meta.get("is_reference"))


def parse_workflow_json(raw: str) -> Dict[str, Dict[str, str]]:
    """``{stage: {"value", "kutipan"}}`` for every stage the LLM filled in.

    Tolerates fenced JSON, prose around the object, alias keys and legacy
    string-only values. Stages with an empty value are dropped: an empty
    stage means "not stated", which the comparison must not treat as a value.
    """
    text = (raw or "").strip()
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    elif not text.startswith("{"):
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            text = match.group(1)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(data, Mapping):
        return {}

    stages: Dict[str, Dict[str, str]] = {}
    for raw_key, item in data.items():
        key = _canonical_stage(raw_key)
        if key is None or key in stages:
            continue
        if isinstance(item, Mapping):
            value = str(item.get("value") or item.get("nilai") or "").strip()
            quote = str(
                item.get("kutipan") or item.get("quote") or item.get("kutipan_verbatim") or ""
            ).strip().strip('"').strip()
        else:
            value, quote = str(item or "").strip(), ""
        value = value.strip("-•* ").strip()
        if not value or value.lower() in {"-", "n/a", "tidak dinyatakan", "none", "null"}:
            continue
        stages[key] = {"value": value[:160], "kutipan": quote[:400]}
    return stages


def _canonical_stage(raw_key: Any) -> Optional[str]:
    key = re.sub(r"[^a-z_]", "_", str(raw_key or "").strip().lower()).strip("_")
    if key in STAGE_KEYS:
        return key
    return _STAGE_ALIASES.get(key)


def verify_workflow(
    stages: Mapping[str, Mapping[str, Any]],
    full_text: str,
) -> Dict[str, Dict[str, Any]]:
    """Attach ``verified``/``match_score`` to each stage quote.

    Values without a verifiable quote are kept (they still describe the
    pipeline) but only verified quotes may later be shown as verbatim evidence.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for key in STAGE_KEYS:
        item = stages.get(key)
        if not item or not str(item.get("value") or "").strip():
            continue
        quote = str(item.get("kutipan") or "").strip()
        score = fuzzy_contains(quote, full_text or "") if quote else 0.0
        out[key] = {
            "value": str(item["value"]).strip(),
            "kutipan": quote,
            "verified": bool(quote) and score >= QUOTE_MATCH_THRESHOLD,
            "match_score": round(float(score), 3),
        }
    return out


@dataclass
class StageVariant:
    """One distinct choice at a stage and the papers that made it."""

    value: str
    papers: List[str] = field(default_factory=list)
    # Verified verbatim quotes only: [{"source", "quote", "match_score"}]
    quotes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"value": self.value, "papers": list(self.papers), "quotes": list(self.quotes)}


@dataclass
class StageSummary:
    stage: str
    label: str
    variants: List[StageVariant] = field(default_factory=list)
    stated_papers: List[str] = field(default_factory=list)
    unstated_papers: List[str] = field(default_factory=list)
    homogeneous: bool = False

    @property
    def dominant(self) -> Optional[StageVariant]:
        return self.variants[0] if self.variants else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "label": self.label,
            "variants": [v.to_dict() for v in self.variants],
            "stated_papers": list(self.stated_papers),
            "unstated_papers": list(self.unstated_papers),
            "homogeneous": self.homogeneous,
        }


@dataclass
class StageMatrix:
    """Stage x paper view of the corpus' methodological pipelines."""

    papers: List[str]
    stages: List[StageSummary]
    min_papers: int = MIN_PAPERS_FOR_HOMOGENEITY
    matcher_method: str = "lexical"
    verified_quotes: int = 0
    total_quotes: int = 0

    @property
    def homogeneous(self) -> List[StageSummary]:
        return [s for s in self.stages if s.homogeneous]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "papers": list(self.papers),
            "n_papers": len(self.papers),
            "min_papers": self.min_papers,
            "matcher": self.matcher_method,
            "verified_quotes": self.verified_quotes,
            "total_quotes": self.total_quotes,
            "stages": [s.to_dict() for s in self.stages],
            # Shape read by GapAnalyzer._indicator_needles (label/stage/value).
            "homogeneous": [
                {
                    "stage": s.stage,
                    "label": s.label,
                    "value": s.dominant.value if s.dominant else "",
                    "papers": list(s.dominant.papers) if s.dominant else [],
                    "unstated": list(s.unstated_papers),
                    "quotes": list(s.dominant.quotes) if s.dominant else [],
                }
                for s in self.homogeneous
            ],
        }


def compare_workflows(
    workflows: Mapping[str, Mapping[str, Mapping[str, Any]]],
    matcher: Optional[SemanticMatcher] = None,
    min_papers: int = MIN_PAPERS_FOR_HOMOGENEITY,
) -> StageMatrix:
    """Cluster each stage's values across papers and flag homogeneous stages.

    ``workflows`` maps paper source -> ``verify_workflow`` output. Values are
    grouped greedily: a value joins the first existing variant the matcher
    considers equivalent, otherwise it opens a new variant. Variants are
    ordered by support so ``variants[0]`` is the dominant choice.
    """
    matcher = matcher or SemanticMatcher()
    papers = [str(src) for src in workflows.keys()]
    summaries: List[StageSummary] = []
    verified = total = 0

    for key in STAGE_KEYS:
        summary = StageSummary(stage=key, label=STAGE_LABELS[key])
        for source in papers:
            item = (workflows.get(source) or {}).get(key) or {}
            value = str(item.get("value") or "").strip()
            if not value:
                summary.unstated_papers.append(source)
                continue
            summary.stated_papers.append(source)
            variant = _find_variant(value, summary.variants, matcher)
            if variant is None:
                variant = StageVariant(value=value)
                summary.variants.append(variant)
            variant.papers.append(source)
            quote = str(item.get("kutipan") or "").strip()
            if quote:
                total += 1
                if item.get("verified"):
                    verified += 1
                    variant.quotes.append({
                        "source": source,
                        "quote": quote,
                        "match_score": float(item.get("match_score") or 0.0),
                    })
        summary.variants.sort(key=lambda v: len(v.papers), reverse=True)
        summary.homogeneous = (
            len(summary.variants) == 1 and len(summary.stated_papers) >= min_papers
        )
        summaries.append(summary)

    return StageMatrix(
        papers=papers,
        stages=summaries,
        min_papers=min_papers,
        matcher_method="embedding" if matcher.uses_embeddings else "lexical",
        verified_quotes=verified,
        total_quotes=total,
    )


def _find_variant(
    value: str, variants: List[StageVariant], matcher: SemanticMatcher
) -> Optional[StageVariant]:
    if not variants:
        return None
    match = matcher.best_match(value, [v.value for v in variants])
    if not match.covered:
        return None
    for variant in variants:
        if variant.value == match.best_match:
            return variant
    return None
