"""Pengayaan daftar pustaka lewat OpenAlex ``referenced_works`` — OPSIONAL, bawaan MATI.

Keputusan proposal (7 Sep 2026): pencarian literatur luar bukan bagian klaim
tesis, dan kuota OpenAlex gratis berbasis kredit (~100 pencarian/hari). Karena
itu kopling bibliografis (``citation_coupling``) bekerja OFFLINE dari daftar
pustaka yang diurai dari PDF; modul ini hanya pelengkap bila diaktifkan lewat
env ``BIBLIO_OPENALEX_ENRICH=true``.

Batasan yang disengaja: ``referenced_works`` adalah ID OpenAlex (``W…``), bukan
DOI, sehingga entri hasil pengayaan hanya terkopel dengan paper lain yang JUGA
diperkaya. Paper yang daftar pustakanya sudah terurai memadai tidak dipanggil ke
jaringan (hemat kredit); yang gagal (kuota/offline) dibiarkan apa adanya.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence

from loguru import logger

from ..core.gap_detection.citation_coupling import MIN_REFS_PER_PAPER
from .paper_apis.openalex import OpenAlexAPI

ENV_FLAG = "BIBLIO_OPENALEX_ENRICH"


def enrichment_enabled() -> bool:
    return os.getenv(ENV_FLAG, "").strip().lower() in ("1", "true", "yes", "on")


def referenced_work_entries(work: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Entri pustaka sintetis dari ``referenced_works`` satu karya OpenAlex."""
    if not work:
        return []
    entries: List[Dict[str, Any]] = []
    for ref in work.get("referenced_works") or []:
        wid = str(ref or "").rsplit("/", 1)[-1].strip()
        if not wid:
            continue
        entries.append({"raw": f"OpenAlex {wid}", "key": f"openalex:{wid}", "doi": None,
                        "year": None, "first_author": "", "title_guess": "",
                        "origin": "openalex"})
    return entries


def enrich_paper_references(
    paper_contents: Sequence[Dict[str, Any]],
    api: Optional[OpenAlexAPI] = None,
    min_refs: int = MIN_REFS_PER_PAPER,
    enabled: Optional[bool] = None,
) -> Dict[str, int]:
    """Tambahkan entri OpenAlex ke ``reference_entries`` paper ber-DOI yang daftar
    pustakanya pendek. Mengembalikan ``{source: jumlah entri ditambahkan}``.
    """
    if not (enrichment_enabled() if enabled is None else enabled):
        return {}
    api = api or OpenAlexAPI()
    added: Dict[str, int] = {}
    for paper in paper_contents:
        doi = str(paper.get("doi") or "").strip()
        entries = list(paper.get("reference_entries") or [])
        if not doi or len(entries) >= min_refs:
            continue
        try:
            work = api.get_work_by_doi(doi)
        except Exception as exc:  # jaringan/kuota: biarkan daftar pustaka apa adanya
            logger.warning(f"Pengayaan OpenAlex gagal untuk {paper.get('source')}: {exc}")
            continue
        new_entries = referenced_work_entries(work)
        if not new_entries:
            continue
        seen = {e.get("key") for e in entries}
        fresh: List[Dict[str, Any]] = []
        for entry in new_entries:
            if entry["key"] in seen:
                continue
            seen.add(entry["key"])
            fresh.append(entry)
        if not fresh:
            continue
        paper["reference_entries"] = entries + fresh
        added[str(paper.get("source") or "")] = len(fresh)
    return added
