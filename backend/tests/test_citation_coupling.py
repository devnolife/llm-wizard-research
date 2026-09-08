"""Bibliographic coupling antar-jurnal (citation_coupling) + integrasi analyzer."""

from unittest.mock import MagicMock

from app.core.gap_detection.analyzer import GapAnalyzer
from app.core.gap_detection.citation_coupling import (
    MIN_PAPERS,
    MIN_REFS_PER_PAPER,
    build_coupling_graph,
)
from app.core.gap_detection.paper_profiles import PaperProfile, build_profiles
from app.models.responses import IndicatorType
from app.services import reference_enrichment


def _refs(*keys, raw_prefix="Ref"):
    return [{"raw": f"{raw_prefix} {k} — judul karya yang dikutip dengan panjang memadai.",
             "key": k, "doi": k if k.startswith("10.") else None,
             "year": 2020, "first_author": "x", "title_guess": f"judul {k}"} for k in keys]


def _profile(source, keys, **kw):
    return PaperProfile(source=source, title=kw.get("title", source), doi=kw.get("doi", ""),
                        references=_refs(*keys))


class TestCouplingGraph:
    def test_two_groups_sharing_nothing_are_two_components(self):
        profiles = [
            _profile("a.pdf", ["r1", "r2", "r3", "r4", "r5"]),
            _profile("b.pdf", ["r1", "r2", "r3", "r6", "r7"]),
            _profile("c.pdf", ["s1", "s2", "s3", "s4", "s5"]),
            _profile("d.pdf", ["s1", "s2", "s9", "s8", "s7"]),
        ]
        res = build_coupling_graph(profiles)
        assert res.eligible == ["a.pdf", "b.pdf", "c.pdf", "d.pdf"] and not res.skipped
        assert res.components == [["a.pdf", "b.pdf"], ["c.pdf", "d.pdf"]]
        assert res.interpretation == "fragmented" and res.fragmented
        assert (res.disconnected_pairs, res.total_pairs, res.isolation_score) == (4, 6, 0.667)
        assert res.modularity > 0.3, "dua komponen terpisah = partisi modular"
        pair_ab = next(p for p in res.pairs if p["a"] == "a.pdf" and p["b"] == "b.pdf")
        assert pair_ab["shared"] == 3 and pair_ab["jaccard"] == round(3 / 7, 3)
        assert res.top_shared[0]["count"] == 3 or res.top_shared[0]["count"] == 2
        assert all(t["count"] >= 2 for t in res.top_shared)
        assert res.to_dict()["thresholds"]["min_refs_per_paper"] == MIN_REFS_PER_PAPER

    def test_one_shared_reference_links_the_groups(self):
        profiles = [
            _profile("a.pdf", ["r1", "r2", "r3", "r4", "bridge"]),
            _profile("b.pdf", ["r1", "r2", "r6", "r7", "r8"]),
            _profile("c.pdf", ["s1", "s2", "s3", "s4", "bridge"]),
        ]
        res = build_coupling_graph(profiles)
        assert len(res.components) == 1
        assert res.interpretation == "intermediate", "terhubung tetapi ada pasangan tanpa referensi bersama"
        assert res.disconnected_pairs == 1  # b–c
        assert res.modularity == 0.0, "satu komponen → Q partisi komponen = 0"

    def test_direct_citation_connects_papers_without_shared_references(self):
        cited = _profile("cited.pdf", ["x1", "x2", "x3", "x4", "x5"],
                         title="Deteksi pemalsuan citra dengan analisis kompresi ganda",
                         doi="10.1000/cited")
        citing = _profile("citing.pdf", ["y1", "y2", "y3", "y4", "y5"])
        citing.references.append({"raw": "Ref: 10.1000/cited", "key": "10.1000/cited",
                                  "doi": "10.1000/cited", "year": 2021, "first_author": "z",
                                  "title_guess": ""})
        by_title = _profile("bytitle.pdf", ["z1", "z2", "z3", "z4", "z5"])
        by_title.references.append({"raw": "Ref judul", "key": "q|2021|deteksi pemalsuan citra analisis",
                                    "doi": None, "year": 2021, "first_author": "q",
                                    "title_guess": "Deteksi pemalsuan citra dengan analisis kompresi ganda"})
        res = build_coupling_graph([cited, citing, by_title])
        assert {(d["citing"], d["cited"]) for d in res.direct_citations} == {
            ("citing.pdf", "cited.pdf"), ("bytitle.pdf", "cited.pdf")}
        assert len(res.components) == 1 and res.interpretation == "intermediate"

    def test_all_pairs_coupled_is_cohesive(self):
        profiles = [_profile(f"{i}.pdf", ["r1", "r2", f"u{i}", f"v{i}", f"w{i}"]) for i in range(3)]
        res = build_coupling_graph(profiles)
        assert res.interpretation == "cohesive" and res.disconnected_pairs == 0

    def test_short_reference_lists_are_skipped_not_treated_as_isolated(self):
        profiles = [
            _profile("a.pdf", ["r1", "r2", "r3", "r4", "r5"]),
            _profile("b.pdf", ["r1", "r2", "r3", "r4", "r6"]),
            _profile("short.pdf", ["r9"]),
            PaperProfile(source="none.pdf"),
        ]
        res = build_coupling_graph(profiles)
        assert "short.pdf" in res.skipped and "1 referensi" in res.skipped["short.pdf"]
        assert res.eligible == ["a.pdf", "b.pdf"]
        assert res.skipped_reason and f"butuh {MIN_PAPERS}" in res.skipped_reason
        assert res.interpretation == "insufficient" and not res.fragmented

    def test_accepts_profile_dicts_from_context(self):
        profiles = {p.key: p.to_dict() for p in [
            _profile("a.pdf", ["r1", "r2", "r3", "r4", "r5"]),
            _profile("b.pdf", ["r1", "r2", "r3", "r4", "r6"]),
            _profile("c.pdf", ["s1", "s2", "s3", "s4", "s5"]),
        ]}
        res = build_coupling_graph(profiles)
        assert len(res.components) == 2


class TestAnalyzerMethod3:
    PAPER_CONTENTS = [{"source": s, "title": s, "doi": "", "year": 2022} for s in ("a", "b", "c", "d")]
    PASSAGES = [
        {"source": "a", "content": "We run a randomized experiment with statistical tests.",
         "metadata": {"keywords": ["experiment"]}},
        {"source": "c", "content": "A qualitative case study based on interviews.",
         "metadata": {"keywords": ["case study"]}},
    ]

    def _profiles(self, split=True):
        refs = {
            "a": _refs("r1", "r2", "r3", "r4", "r5"),
            "b": _refs("r1", "r2", "r3", "r6", "r7"),
            "c": _refs("s1", "s2", "s3", "s4", "s5") if split else _refs("r1", "s2", "s3", "s4", "s5"),
            "d": _refs("s1", "s2", "s9", "s8", "s7") if split else _refs("r2", "s2", "s9", "s8", "s7"),
        }
        return {k: v.to_dict() for k, v in build_profiles(self.PAPER_CONTENTS, references=refs).items()}

    def test_fragmented_coupling_becomes_a_fragmentation_indicator(self):
        ga = GapAnalyzer()
        indicators = ga.analyze_gaps("forensik", self.PASSAGES, depth="quick",
                                     paper_profiles=self._profiles())
        bib = [i for i in indicators if i.detection_method == "bibliographic_coupling"]
        assert len(bib) == 1
        ind = bib[0]
        assert ind.indicator_type == IndicatorType.FRAGMENTATION
        assert ind.confidence == round(4 / 6, 3), "= disconnected_pairs / total_pairs (rumus Metode 2)"
        assert set(ind.related_papers) == {"a", "b", "c", "d"}, "semua jurnal unggahan, bukan hanya passage"
        assert "2 groups" in ind.description
        assert ind.supporting_quotes and all(q["origin"] == "reference_entry" and q["match_score"] == 1.0
                                             for q in ind.supporting_quotes)
        coupling = next(s["bibliographic_coupling"] for s in ind.sub_indicators)
        assert coupling["interpretation"] == "fragmented" and len(coupling["components"]) == 2
        # Tanpa Rule Engine mata rantai 'hasil validasi' selalu kosong; yang diuji di sini
        # adalah bahwa entri pustaka verbatim mengisi mata rantai kutipan.
        assert "kutipan terambil" not in ind.provenance.get("broken_links", [])

    def test_connected_coupling_is_attached_as_evidence_only(self):
        ga = GapAnalyzer()
        indicators = ga.analyze_gaps("forensik", self.PASSAGES, depth="quick",
                                     paper_profiles=self._profiles(split=False))
        assert [i for i in indicators if i.detection_method == "bibliographic_coupling"] == []
        frag = [i for i in indicators if i.indicator_type == IndicatorType.FRAGMENTATION]
        assert frag, "klasterisasi passage tetap menghasilkan indikator fragmentasi"
        attached = [s for s in frag[0].sub_indicators if "bibliographic_coupling" in s]
        assert attached and attached[0]["bibliographic_coupling"]["interpretation"] != "fragmented"

    def test_without_profiles_or_references_nothing_changes(self):
        ga = GapAnalyzer()
        base = ga.analyze_gaps("forensik", self.PASSAGES, depth="quick")
        empty_refs = {k: v.to_dict() for k, v in build_profiles(self.PAPER_CONTENTS).items()}
        with_profiles = ga.analyze_gaps("forensik", self.PASSAGES, depth="quick",
                                        paper_profiles=empty_refs)
        assert [i.detection_method for i in base] == [i.detection_method for i in with_profiles]
        assert not any("bibliographic_coupling" in s for i in with_profiles for s in i.sub_indicators)


class TestOpenAlexEnrichment:
    def _api(self, referenced):
        api = MagicMock()
        api.get_work_by_doi.return_value = {"referenced_works": referenced}
        return api

    def test_disabled_by_default_makes_no_network_call(self, monkeypatch):
        monkeypatch.delenv(reference_enrichment.ENV_FLAG, raising=False)
        api = self._api(["https://openalex.org/W1"])
        papers = [{"source": "a.pdf", "doi": "10.1/x", "reference_entries": []}]
        assert reference_enrichment.enrich_paper_references(papers, api=api) == {}
        api.get_work_by_doi.assert_not_called()

    def test_only_short_lists_with_doi_are_topped_up(self):
        api = self._api(["https://openalex.org/W1", "https://openalex.org/W2", "W2"])
        papers = [
            {"source": "short.pdf", "doi": "10.1/a", "reference_entries": [{"key": "openalex:W1"}]},
            {"source": "full.pdf", "doi": "10.1/b", "reference_entries": _refs("r1", "r2", "r3", "r4", "r5")},
            {"source": "nodoi.pdf", "doi": "", "reference_entries": []},
        ]
        added = reference_enrichment.enrich_paper_references(papers, api=api, enabled=True)
        assert added == {"short.pdf": 1}, "W1 sudah ada, W2 duplikat → 1 entri baru"
        assert [e["key"] for e in papers[0]["reference_entries"]] == ["openalex:W1", "openalex:W2"]
        assert api.get_work_by_doi.call_count == 1

    def test_network_failure_leaves_references_untouched(self):
        api = MagicMock()
        api.get_work_by_doi.side_effect = RuntimeError("429")
        papers = [{"source": "a.pdf", "doi": "10.1/a", "reference_entries": []}]
        assert reference_enrichment.enrich_paper_references(papers, api=api, enabled=True) == {}
        assert papers[0]["reference_entries"] == []
