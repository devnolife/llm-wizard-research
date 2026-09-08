"""
Sumbu Evidence Gap Map yang sadar domain (Fase 4).

``coverage_map.build_coverage_matrix`` memetakan tiap paper ke sel baris × kolom
dengan mencocokkan kosakata sumbu pada teks paper. Kosakata bawaannya generik
(``healthcare``, ``education`` … ``accuracy``, ``privacy``): pada korpus forensik
digital hampir semua paper jatuh ke sel yang sama atau tidak terpetakan, sehingga
peta bukti tidak berkata apa-apa tentang domain itu.

Modul ini menentukan sumbu dengan urutan prioritas yang bisa diperiksa:

1. **Kurasi** — berkas YAML di ``backend/data/ontology/<slug>.yaml`` (atau direktori
   ``COVERAGE_AXES_DIR``). Berkas dipilih bila nama-slug topik cocok, atau salah
   satu kata pada ``match:`` muncul di topik. Ini jalur untuk peneliti/pembimbing
   menetapkan ontologi domain secara eksplisit.
2. **LLM + grounding korpus** — LLM mengusulkan baris/kolom dalam istilah korpus;
   istilah yang kata-isinya tidak pernah muncul di korpus DIBUANG (logika yang
   sama dengan grounding aspek: pengetahuan parametrik bukan bukti tentang
   korpus ini). Bila tersisa < 2 baris atau < 2 kolom, jatuh ke (3).
3. **Bawaan** — kosakata generik ``coverage_map._DEFAULT_*``.

Hanya SUMBU yang berubah; rumus confidence sel kosong dan aturan "sel kosong =
kandidat, bukan gap" di ``coverage_map`` tidak disentuh.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from loguru import logger

from .coverage_map import _DEFAULT_COLUMN_TERMS, _DEFAULT_ROW_TERMS
from .semantic_match import normalize_phrase

# Batas jumlah istilah per sumbu agar matriks tetap terbaca (P8: peta, bukan tabel raksasa).
MAX_AXIS_TERMS = 12
# Di bawah ini peta tidak bisa membandingkan apa pun (lihat analyzer: butuh grid >= 2x2).
MIN_AXIS_TERMS = 2
# Cuplikan korpus yang diperlihatkan ke LLM agar istilah usulannya memakai kosakata korpus.
_SNIPPET_PAPERS = 6
_SNIPPET_CHARS = 300

AXES_SOURCES = ("curated", "llm_grounded", "default")

_AXES_PROMPT = """You are helping build an evidence gap map for a literature corpus on the topic \
"{topic}".

Corpus excerpts (use THEIR terminology and language):
{snippets}

Propose the two axes of the map:
- "rows": {n} short noun phrases (1-3 words) naming the domains / settings / objects / \
sub-areas that papers in THIS corpus study.
- "columns": {n} short noun phrases (1-3 words) naming the outcomes, quality dimensions \
or question dimensions papers in THIS corpus measure or discuss.

Rules: lowercase; words that literally appear in the excerpts; no generic terms such as \
"research", "method", "analysis"; no duplicates between rows and columns.
Return ONLY JSON: {{"rows": ["..."], "columns": ["..."]}}"""


@dataclass
class AxesSpec:
    """Sumbu peta bukti beserta asal-usulnya (dapat ditelusuri di sub_indicators)."""

    rows: List[str]
    columns: List[str]
    source: str = "default"                    # salah satu AXES_SOURCES
    slug: str = ""                             # berkas kurasi yang dipakai (bila ada)
    important_columns: List[str] = field(default_factory=list)
    aliases: Dict[str, List[str]] = field(default_factory=dict)
    dropped_ungrounded: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rows": list(self.rows),
            "columns": list(self.columns),
            "source": self.source,
            "slug": self.slug,
            "important_columns": list(self.important_columns),
            "aliases": {k: list(v) for k, v in self.aliases.items()},
            "dropped_ungrounded": list(self.dropped_ungrounded),
            "notes": list(self.notes),
        }


def default_axes(note: str = "") -> AxesSpec:
    spec = AxesSpec(rows=list(_DEFAULT_ROW_TERMS), columns=list(_DEFAULT_COLUMN_TERMS),
                    source="default")
    if note:
        spec.notes.append(note)
    return spec


def slugify(topic: str) -> str:
    """'Forensik Digital: Chain-of-Custody' -> 'forensik_digital_chain_of_custody'."""
    slug = re.sub(r"[^a-z0-9]+", "_", (topic or "").lower()).strip("_")
    return slug[:80]


def axes_dir(path: Optional[str] = None) -> Path:
    """Direktori YAML kurasi: argumen > env COVERAGE_AXES_DIR > backend/data/ontology."""
    if path:
        return Path(path)
    env = os.getenv("COVERAGE_AXES_DIR")
    if env:
        return Path(env)
    # coverage_axes.py ada di backend/app/core/gap_detection/ → 4 induk ke atas = backend/.
    return Path(__file__).resolve().parents[3] / "data" / "ontology"


def _clean_terms(values: Any, limit: int = MAX_AXIS_TERMS) -> List[str]:
    """Normalisasi daftar istilah: string, lowercase, tanpa duplikat, dibatasi."""
    if not isinstance(values, (list, tuple)):
        return []
    out: List[str] = []
    seen = set()
    for raw in values:
        term = " ".join(str(raw or "").lower().strip().strip(".,;:\"'").split())
        if len(term) < 3 or term in seen:
            continue
        seen.add(term)
        out.append(term)
        if len(out) >= limit:
            break
    return out


def _parse_yaml_spec(raw: Dict[str, Any], slug: str) -> Optional[AxesSpec]:
    rows = _clean_terms(raw.get("rows"))
    columns = _clean_terms(raw.get("columns"))
    if len(rows) < MIN_AXIS_TERMS or len(columns) < MIN_AXIS_TERMS:
        logger.warning(f"Ontologi {slug}: butuh >= {MIN_AXIS_TERMS} baris dan kolom; diabaikan")
        return None
    aliases_raw = raw.get("aliases") or {}
    aliases: Dict[str, List[str]] = {}
    if isinstance(aliases_raw, dict):
        for canonical, alts in aliases_raw.items():
            key = str(canonical).lower().strip()
            alts_clean = _clean_terms(alts, limit=20)
            if key and alts_clean:
                aliases[key] = alts_clean
    important = [c for c in _clean_terms(raw.get("important_columns")) if c in columns]
    return AxesSpec(rows=rows, columns=columns, source="curated", slug=slug,
                    important_columns=important, aliases=aliases,
                    notes=[str(raw.get("note")).strip()] if raw.get("note") else [])


def _matches_topic(raw: Dict[str, Any], stem: str, topic: str) -> bool:
    slug = slugify(topic)
    if stem == slug or (slug and stem and slug.startswith(stem)):
        return True
    topic_low = (topic or "").lower()
    for word in _clean_terms(raw.get("match"), limit=50):
        if word in topic_low:
            return True
    return False


def load_curated_axes(topic: str, directory: Optional[str] = None) -> Optional[AxesSpec]:
    """Berkas YAML pertama yang cocok dengan topik; None bila tidak ada/rusak."""
    folder = axes_dir(directory)
    if not folder.is_dir():
        return None
    try:
        import yaml
    except ImportError:  # pragma: no cover - yaml adalah dependensi config loader
        return None
    for path in sorted(folder.glob("*.y*ml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            logger.warning(f"Ontologi {path.name} tidak terbaca: {exc}")
            continue
        if not isinstance(raw, dict) or not _matches_topic(raw, path.stem, topic):
            continue
        spec = _parse_yaml_spec(raw, path.stem)
        if spec is not None:
            return spec
    return None


def _corpus_text(papers: Sequence[Dict[str, Any]]) -> str:
    return " ".join(str(p.get("content") or "") for p in papers).lower()


def grounded_terms(terms: Sequence[str], corpus_text: str) -> Tuple[List[str], List[str]]:
    """Pisahkan istilah yang kata-isinya muncul di korpus dari yang tidak.

    Sama semangatnya dengan ``GapAnalyzer._ground_aspects``: istilah usulan LLM yang
    tidak pernah muncul di korpus adalah pengetahuan parametrik, bukan bukti
    tentang korpus ini. Pencocokan memakai stem kata-isi (``normalize_phrase``)
    sebagai substring, sehingga "reproducibility" tetap tertaut ke "reproducible".
    """
    kept: List[str] = []
    dropped: List[str] = []
    for term in terms:
        stems = normalize_phrase(term) or [term.lower()]
        if any(stem and stem in corpus_text for stem in stems):
            kept.append(term)
        else:
            dropped.append(term)
    return kept, dropped


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Objek JSON pertama di dalam balasan LLM (boleh dibungkus teks/kode)."""
    if not text:
        return None
    match = re.search(r"\{.*\}", str(text), flags=re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _snippets(papers: Sequence[Dict[str, Any]]) -> str:
    lines = []
    for paper in list(papers)[:_SNIPPET_PAPERS]:
        text = " ".join(str(paper.get("content") or "").split())[:_SNIPPET_CHARS]
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines) or "- (no excerpts available)"


def propose_axes(topic: str, papers: Sequence[Dict[str, Any]], llm,
                 n_terms: int = 8) -> AxesSpec:
    """Sumbu usulan LLM yang sudah disaring grounding; bawaan bila tidak memadai."""
    if llm is None:
        return default_axes("LLM tidak tersedia; memakai kosakata sumbu bawaan.")
    prompt = _AXES_PROMPT.format(topic=topic, snippets=_snippets(papers),
                                 n=max(MIN_AXIS_TERMS, min(n_terms, MAX_AXIS_TERMS)))
    try:
        response = llm.generate(prompt, temperature=0.2, max_tokens=400)
    except Exception as exc:
        logger.warning(f"Usulan sumbu peta bukti gagal: {exc}")
        return default_axes("LLM gagal mengusulkan sumbu; memakai kosakata bawaan.")
    data = _extract_json_object(response if isinstance(response, str) else str(response))
    if not data:
        return default_axes("Balasan LLM untuk sumbu tidak berbentuk JSON; memakai kosakata bawaan.")

    rows = _clean_terms(data.get("rows"))
    columns = [c for c in _clean_terms(data.get("columns")) if c not in set(rows)]
    corpus = _corpus_text(papers)
    rows, dropped_rows = grounded_terms(rows, corpus)
    columns, dropped_cols = grounded_terms(columns, corpus)
    dropped = dropped_rows + dropped_cols
    if len(rows) < MIN_AXIS_TERMS or len(columns) < MIN_AXIS_TERMS:
        spec = default_axes(
            f"Usulan LLM tersisa {len(rows)} baris/{len(columns)} kolom setelah grounding "
            f"(< {MIN_AXIS_TERMS}); memakai kosakata bawaan.")
        spec.dropped_ungrounded = dropped
        return spec
    return AxesSpec(rows=rows, columns=columns, source="llm_grounded",
                    dropped_ungrounded=dropped,
                    notes=[f"{len(dropped)} istilah usulan LLM dibuang karena tidak muncul di korpus."]
                    if dropped else [])


def resolve_axes(topic: str, papers: Sequence[Dict[str, Any]], llm=None,
                 directory: Optional[str] = None) -> AxesSpec:
    """Kurasi YAML > LLM+grounding > bawaan. Selalu mengembalikan AxesSpec yang valid."""
    curated = load_curated_axes(topic, directory)
    if curated is not None:
        return curated
    return propose_axes(topic, papers, llm)
