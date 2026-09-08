"""
Bibliographic coupling antar-jurnal unggahan (Fase 3) — sinyal fragmentasi bebas LLM.

Dua paper *terkopel bibliografis* bila mengutip karya yang sama (Kessler, 1963);
paper yang tidak berbagi satu pun referensi dan tidak saling mengutip berdiri di
untai literatur yang terpisah. Ini sinyal struktural yang independen dari LLM
maupun embedding, jadi melengkapi dua metode fragmentasi yang sudah ada
(klasterisasi pendekatan; isolasi entitas di knowledge graph).

Masukan: daftar pustaka terurai per jurnal (``pipeline.references``) yang
dibawa ``PaperProfile.references``. Keluaran ``CouplingResult`` memuat pasangan
dengan referensi bersama (Jaccard himpunan kunci), sitasi langsung antar-jurnal
unggahan, komponen terhubung, modularitas Newman pada graf kopling (fungsi yang
sama dengan ``graph_metrics``), dan interpretasinya.

Confidence indikator = ``disconnected_pairs / total_pairs`` — rumus yang sama
dengan skor isolasi Metode 2, tanpa bobot baru. Paper dengan daftar pustaka
terlalu pendek (< ``MIN_REFS_PER_PAPER``) tidak ikut dihitung dan dilaporkan
sebagai *dilewati*, bukan diperlakukan sebagai terputus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from ..pipeline.references import content_words
from .graph_metrics import Q_COHESIVE_MIN, Q_FRAGMENTED_MAX, compute_modularity, connected_components

# Di bawah ini daftar pustaka dianggap tidak terurai/terpotong, bukan "tidak mengutip apa pun".
MIN_REFS_PER_PAPER = 5
# Kopling butuh minimal tiga paper agar komponen/modularitas bermakna.
MIN_PAPERS = 3
# Satu referensi bersama sudah menjadi sisi graf kopling (Jaccard > 0).
EDGE_THRESHOLD = 1e-9
# Kata-isi judul minimum agar entri pustaka boleh dinyatakan mengutip paper unggahan.
_TITLE_MATCH_WORDS = 4


@dataclass
class CouplingResult:
    papers: List[str]
    eligible: List[str]
    skipped: Dict[str, str] = field(default_factory=dict)
    pairs: List[Dict[str, Any]] = field(default_factory=list)          # semua pasangan eligible
    direct_citations: List[Dict[str, Any]] = field(default_factory=list)
    components: List[List[str]] = field(default_factory=list)
    modularity: float = 0.0
    disconnected_pairs: int = 0
    total_pairs: int = 0
    top_shared: List[Dict[str, Any]] = field(default_factory=list)
    interpretation: str = "insufficient"
    skipped_reason: Optional[str] = None

    @property
    def fragmented(self) -> bool:
        return self.interpretation == "fragmented"

    @property
    def isolation_score(self) -> float:
        return round(self.disconnected_pairs / self.total_pairs, 3) if self.total_pairs else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "papers": list(self.papers),
            "eligible": list(self.eligible),
            "skipped": dict(self.skipped),
            "skipped_reason": self.skipped_reason,
            "pairs": [dict(p) for p in self.pairs],
            "direct_citations": [dict(d) for d in self.direct_citations],
            "components": [list(c) for c in self.components],
            "modularity": self.modularity,
            "disconnected_pairs": self.disconnected_pairs,
            "total_pairs": self.total_pairs,
            "isolation_score": self.isolation_score,
            "top_shared": [dict(t) for t in self.top_shared],
            "interpretation": self.interpretation,
            "thresholds": {"q_fragmented_max": Q_FRAGMENTED_MAX, "q_cohesive_min": Q_COHESIVE_MIN,
                           "min_refs_per_paper": MIN_REFS_PER_PAPER, "min_papers": MIN_PAPERS},
        }


def _profile_view(profile: Any) -> Tuple[str, str, str, List[Mapping[str, Any]]]:
    """(source, title, doi, entries) dari PaperProfile atau dict setara."""
    if isinstance(profile, Mapping):
        return (str(profile.get("source") or ""), str(profile.get("title") or ""),
                str(profile.get("doi") or ""), list(profile.get("references") or []))
    return (str(getattr(profile, "source", "") or ""), str(getattr(profile, "title", "") or ""),
            str(getattr(profile, "doi", "") or ""), list(getattr(profile, "references", []) or []))


def _direct_citation(entries: Iterable[Mapping[str, Any]], title: str, doi: str) -> Optional[str]:
    """Kunci entri yang mengutip paper unggahan: DOI sama, atau judul entri (>= 5 kata-isi)
    berbagi >= 60% kata-isi himpunan yang lebih pendek (minimal 4 kata) dengan judul paper.
    Kata domain umum ("forensic", "digital") saja tidak cukup — ambangnya proporsional."""
    doi = (doi or "").lower().strip()
    title_words = set(content_words(title, limit=12))
    for entry in entries:
        entry_doi = str(entry.get("doi") or "").lower()
        if doi and entry_doi and entry_doi == doi:
            return str(entry.get("key") or entry_doi)
        if len(title_words) < _TITLE_MATCH_WORDS:
            continue
        guess = set(content_words(str(entry.get("title_guess") or ""), limit=30))
        if len(guess) < _TITLE_MATCH_WORDS + 1:
            continue
        needed = max(_TITLE_MATCH_WORDS, -(-min(len(title_words), len(guess)) * 6 // 10))
        if len(title_words & guess) >= needed:
            return str(entry.get("key") or "")
    return None


def build_coupling_graph(
    profiles: Mapping[str, Any] | Sequence[Any],
    min_refs: int = MIN_REFS_PER_PAPER,
    min_papers: int = MIN_PAPERS,
) -> CouplingResult:
    """Graf kopling bibliografis dari daftar pustaka terurai per jurnal."""
    items = list(profiles.values()) if isinstance(profiles, Mapping) else list(profiles)
    views = [_profile_view(p) for p in items]
    papers = [v[0] for v in views if v[0]]
    result = CouplingResult(papers=papers, eligible=[])

    refsets: Dict[str, Set[str]] = {}
    raw_by_key: Dict[str, Dict[str, str]] = {}   # key -> {paper: raw entry}
    for source, _title, _doi, entries in views:
        if not source:
            continue
        keys = {str(e.get("key") or "").strip() for e in entries if str(e.get("key") or "").strip()}
        if len(keys) < min_refs:
            result.skipped[source] = (
                f"{len(keys)} referensi terurai (< {min_refs}); daftar pustaka tidak "
                "terdeteksi atau terpotong")
            continue
        refsets[source] = keys
        for e in entries:
            key = str(e.get("key") or "").strip()
            if key:
                raw_by_key.setdefault(key, {}).setdefault(source, str(e.get("raw") or ""))
    eligible = [v[0] for v in views if v[0] in refsets]
    result.eligible = eligible
    if len(eligible) < min_papers:
        result.skipped_reason = (
            f"hanya {len(eligible)} jurnal dengan >= {min_refs} referensi terurai "
            f"(butuh {min_papers}); kopling bibliografis dilewati")
        return result

    # Sitasi langsung antar jurnal unggahan (A mengutip B) — juga menyambungkan graf.
    meta = {v[0]: (v[1], v[2]) for v in views if v[0] in refsets}
    direct: Set[Tuple[str, str]] = set()
    for citing in eligible:
        entries = next(v[3] for v in views if v[0] == citing)
        for cited in eligible:
            if cited == citing:
                continue
            via = _direct_citation(entries, *meta[cited])
            if via:
                direct.add((citing, cited))
                result.direct_citations.append({"citing": citing, "cited": cited, "via": via})

    n = len(eligible)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            a, b = eligible[i], eligible[j]
            shared = refsets[a] & refsets[b]
            union = refsets[a] | refsets[b]
            jaccard = len(shared) / len(union) if union else 0.0
            linked = bool(shared) or (a, b) in direct or (b, a) in direct
            # Sitasi langsung tanpa referensi bersama tetap satu sisi (bobot minimal).
            matrix[i][j] = matrix[j][i] = jaccard if shared else (EDGE_THRESHOLD if linked else 0.0)
            result.pairs.append({
                "a": a, "b": b, "shared": len(shared), "jaccard": round(jaccard, 3),
                "direct": (a, b) in direct or (b, a) in direct,
                "shared_keys": sorted(shared)[:5],
            })
            result.total_pairs += 1
            if not linked:
                result.disconnected_pairs += 1

    clusters = connected_components(eligible, matrix, EDGE_THRESHOLD)
    result.components = [sorted(members) for members in clusters.values()]
    result.modularity = compute_modularity(eligible, matrix, clusters, EDGE_THRESHOLD)

    shared_counts: Dict[str, Set[str]] = {}
    for source, keys in refsets.items():
        for key in keys:
            shared_counts.setdefault(key, set()).add(source)
    result.top_shared = [
        {"key": key, "papers": sorted(srcs), "count": len(srcs),
         "example": next(iter(raw_by_key.get(key, {}).values()), "")[:300]}
        for key, srcs in sorted(shared_counts.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        if len(srcs) >= 2
    ][:8]

    # Aturan keputusan transparan: >= 2 komponen = ada kelompok jurnal yang tidak
    # berbagi satu pun referensi dan tidak saling mengutip. Modularitas dilaporkan
    # sebagai bukti (Q ~ 0 = satu komponen; makin tinggi makin terpisah), bukan
    # sebagai ambang keputusan.
    if len(result.components) >= 2:
        result.interpretation = "fragmented"
    elif result.disconnected_pairs == 0:
        result.interpretation = "cohesive"
    else:
        result.interpretation = "intermediate"
    return result
