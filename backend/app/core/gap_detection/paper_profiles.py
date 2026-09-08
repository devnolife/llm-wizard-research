"""Per-journal side-channel for the synthesis-gap analyzer.

``GapAnalyzer.analyze_gaps`` receives RAG *passages* (top-k chunks that carry
only ``source``/``title``), not the uploaded journals themselves. Anything the
8-stage job computes per journal — author-stated weaknesses, gap-mining records,
workflow stages, reference lists — therefore had no path to the indicators.

A :class:`PaperProfile` is that path: one record per uploaded journal, keyed by
:func:`normalize_source` so passages, weakness records and gap-mining records
join even though each spells the source a little differently
(``"07_x.pdf"`` in the job dir, ``"x.pdf"`` in the chunk JSONL, ``"X.pdf"`` in a
title fallback).

Profiles are *evidence carriers only*: nothing here scores anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from ..pipeline.io import source_name

# Gap-mining record kinds (see core/gap_mining/extractor.GAP_TYPES); listed here
# so the UI can tell author-mined statements from weakness-review statements.
AUTHOR_GAP_KINDS = ("explicit_future_work", "stated_limitation", "implicit_gap")
WEAKNESS_KINDS = ("tersurat", "tersirat")


def normalize_source(name: Any) -> str:
    """Join key shared by every per-journal data source.

    Basename only, job-dir index prefix (``07_``) removed, whitespace collapsed,
    lower-cased. Returns ``""`` for empty/None input so callers can skip it.
    """
    text = str(name or "").strip()
    if not text or text.lower() == "unknown":
        return ""
    # Windows-style separators appear in filenames uploaded from laptops.
    text = text.replace("\\", "/")
    return " ".join(source_name(text).split()).lower()


@dataclass
class PaperProfile:
    """Everything the job knows about ONE uploaded journal, beyond its text."""

    source: str
    title: str = ""
    # {"tersurat": [{poin, dasar, kutipan, verification_status, confidence}],
    #  "tersirat": [{poin, dasar, verification_status, confidence}]}
    weaknesses: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    # Gap-mining records for this journal (verbatim statements):
    # [{statement, paraphrase, kind, chunk_id, grounding_score, source}]
    author_gaps: List[Dict[str, Any]] = field(default_factory=list)
    # Workflow stages (Fase 2): {stage: {value, kutipan, verified}} or None
    workflow: Optional[Dict[str, Any]] = None
    # Parsed reference-list entries (Fase 3): [{raw, key, doi, year, ...}]
    references: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def key(self) -> str:
        return normalize_source(self.source)

    def statements(self) -> List[Dict[str, Any]]:
        """Author-stated statements usable as corroborating evidence.

        Every item has ``kind``, ``text`` (display form), ``texts`` (alternative
        phrasings to match against — a point and its basis, or a verbatim
        statement and its paraphrase, kept separate so a paraphrase in another
        language cannot dilute the match), ``source`` and ``score``; ``quote``
        is set ONLY when the text is verbatim from the paper (explicit
        weaknesses with a verified quote, gap-mining statements), because only
        verbatim text may enter ``supporting_quotes``.
        """
        out: List[Dict[str, Any]] = []
        for item in self.weaknesses.get("tersurat") or []:
            texts = _nonempty(item.get("poin"), item.get("dasar"))
            if not texts:
                continue
            quote = str(item.get("kutipan") or "").strip()
            out.append({
                "kind": "tersurat",
                "text": " ".join(texts),
                "texts": texts,
                "quote": quote or None,
                "source": self.source,
                "score": _as_float(item.get("confidence")),
                "verification_status": item.get("verification_status"),
            })
        for item in self.weaknesses.get("tersirat") or []:
            texts = _nonempty(item.get("poin"), item.get("dasar"))
            if not texts:
                continue
            out.append({
                "kind": "tersirat",
                "text": " ".join(texts),
                "texts": texts,
                "quote": None,
                "source": self.source,
                "score": _as_float(item.get("confidence")),
                "verification_status": item.get("verification_status"),
            })
        for gap in self.author_gaps:
            statement = str(gap.get("statement") or "").strip()
            if not statement:
                continue
            kind = gap.get("kind") if gap.get("kind") in AUTHOR_GAP_KINDS else "implicit_gap"
            out.append({
                "kind": kind,
                "text": statement,
                "texts": _nonempty(statement, gap.get("paraphrase")),
                "quote": statement,
                "source": self.source,
                "score": _as_float(gap.get("grounding_score")),
                "chunk_id": gap.get("chunk_id"),
            })
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "key": self.key,
            "title": self.title,
            "weaknesses": {
                "tersurat": list(self.weaknesses.get("tersurat") or []),
                "tersirat": list(self.weaknesses.get("tersirat") or []),
            },
            "author_gaps": list(self.author_gaps),
            "workflow": self.workflow,
            "references": list(self.references),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PaperProfile":
        weaknesses = data.get("weaknesses") or {}
        return cls(
            source=str(data.get("source") or ""),
            title=str(data.get("title") or ""),
            weaknesses={
                "tersurat": list(weaknesses.get("tersurat") or []),
                "tersirat": list(weaknesses.get("tersirat") or []),
            },
            author_gaps=list(data.get("author_gaps") or []),
            workflow=data.get("workflow"),
            references=list(data.get("references") or []),
        )


def build_profiles(
    paper_contents: Sequence[Mapping[str, Any]],
    weaknesses: Optional[Iterable[Mapping[str, Any]]] = None,
    author_gaps: Optional[Iterable[Mapping[str, Any]]] = None,
    workflows: Optional[Mapping[str, Any]] = None,
    references: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
) -> Dict[str, PaperProfile]:
    """One profile per journal in ``paper_contents``, keyed by :func:`normalize_source`.

    ``weaknesses`` are the ``paper_weaknesses`` records of the job
    (``{title, source, tersurat, tersirat}``); ``author_gaps`` are gap-mining
    records already reduced to ``{source, statement, ...}``; ``workflows`` and
    ``references`` are mappings ``source -> data``. Records whose source is not
    an uploaded journal are ignored rather than creating phantom profiles.
    """
    profiles: Dict[str, PaperProfile] = {}
    for paper in paper_contents:
        source = str(paper.get("source") or "").strip()
        key = normalize_source(source)
        if not key or key in profiles:
            continue
        profiles[key] = PaperProfile(source=source, title=str(paper.get("title") or source))

    for record in weaknesses or []:
        profile = profiles.get(normalize_source(record.get("source")))
        if profile is None:
            continue
        profile.weaknesses = {
            "tersurat": list(record.get("tersurat") or []),
            "tersirat": list(record.get("tersirat") or []),
        }

    for gap in author_gaps or []:
        profile = profiles.get(normalize_source(gap.get("source")))
        if profile is None or not str(gap.get("statement") or "").strip():
            continue
        profile.author_gaps.append(dict(gap))

    for source, workflow in (workflows or {}).items():
        profile = profiles.get(normalize_source(source))
        if profile is not None and workflow:
            profile.workflow = dict(workflow)

    for source, entries in (references or {}).items():
        profile = profiles.get(normalize_source(source))
        if profile is not None:
            profile.references = [dict(e) for e in entries or []]

    return profiles


def profiles_from_context(raw: Any) -> Dict[str, PaperProfile]:
    """Rehydrate profiles passed through the agent context (dicts or objects)."""
    out: Dict[str, PaperProfile] = {}
    if not isinstance(raw, Mapping):
        return out
    for key, value in raw.items():
        if isinstance(value, PaperProfile):
            profile = value
        elif isinstance(value, Mapping):
            profile = PaperProfile.from_dict(value)
        else:
            continue
        out[normalize_source(key) or profile.key] = profile
    return out


def profile_for(
    paper: Mapping[str, Any],
    profiles: Mapping[str, PaperProfile],
) -> Optional[PaperProfile]:
    """Profile of the journal a passage/paper dict belongs to, if any.

    Same candidate order as ``resolve_paper_id`` (doc_id/id/source/title),
    then the ``metadata`` block RAG passages carry, so both job paper dicts
    and retrieval results resolve to the same profile.
    """
    if not profiles:
        return None
    meta = paper.get("metadata") or {}
    for candidate in (
        paper.get("doc_id"),
        paper.get("id"),
        paper.get("source"),
        meta.get("source"),
        paper.get("title"),
        meta.get("title"),
    ):
        key = normalize_source(candidate)
        if key and key in profiles:
            return profiles[key]
    return None


def _nonempty(*parts: Any) -> List[str]:
    return [str(p).strip() for p in parts if p and str(p).strip()]


def _as_float(value: Any) -> Optional[float]:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None
