"""Sumbu Evidence Gap Map sadar domain (coverage_axes): kurasi > LLM grounded > bawaan."""

from unittest.mock import MagicMock

import pytest

from app.core.gap_detection import coverage_axes as ca
from app.core.gap_detection.analyzer import GapAnalyzer
from app.core.gap_detection.coverage_map import (
    _DEFAULT_COLUMN_TERMS,
    _DEFAULT_ROW_TERMS,
    build_coverage_matrix,
)

FORENSIC_PAPERS = [
    {"source": "a.pdf", "content": "Akuisisi bukti dari perangkat forensik mobile; akurasi "
                                   "ekstraksi diukur dan integritas bukti dijaga dengan hash."},
    {"source": "b.pdf", "content": "Forensik citra untuk deteksi pemalsuan; akurasi model "
                                   "dievaluasi pada dataset publik."},
    {"source": "c.pdf", "content": "Chain of custody bukti digital dan admisibilitas di "
                                   "pengadilan; standar SOP dibahas."},
]

CURATED_YAML = """
match: [forensik, forensic]
rows: [akuisisi, forensik mobile, forensik citra, chain of custody]
columns: [akurasi, admisibilitas, integritas bukti]
important_columns: [admisibilitas, kolom-tak-dikenal]
aliases:
  akuisisi: [acquisition, imaging]
  akurasi: [accuracy]
note: uji
"""


@pytest.fixture
def ontology_dir(tmp_path):
    (tmp_path / "forensik_digital.yaml").write_text(CURATED_YAML, encoding="utf-8")
    return tmp_path


class TestCuratedAxes:
    def test_loads_by_match_keyword_and_parses_all_fields(self, ontology_dir):
        spec = ca.load_curated_axes("Analisis Forensic Digital", str(ontology_dir))
        assert spec is not None and spec.source == "curated"
        assert spec.slug == "forensik_digital"
        assert spec.rows[0] == "akuisisi" and "chain of custody" in spec.rows
        assert spec.columns == ["akurasi", "admisibilitas", "integritas bukti"]
        assert spec.important_columns == ["admisibilitas"], "kolom penting harus ada di columns"
        assert spec.aliases["akuisisi"] == ["acquisition", "imaging"]
        assert spec.notes == ["uji"]
        assert spec.to_dict()["source"] == "curated"

    def test_loads_by_slug_prefix_without_match_keyword(self, tmp_path):
        (tmp_path / "penjadwalan.yaml").write_text(
            "rows: [kuliah, ujian]\ncolumns: [waktu, biaya]\n", encoding="utf-8")
        assert ca.load_curated_axes("Penjadwalan Mata Kuliah", str(tmp_path)) is not None
        assert ca.load_curated_axes("Forensik", str(tmp_path)) is None

    def test_missing_dir_or_unrelated_topic_returns_none(self, ontology_dir, tmp_path):
        assert ca.load_curated_axes("forensik", str(tmp_path / "tidak-ada")) is None
        assert ca.load_curated_axes("Pembelajaran daring", str(ontology_dir)) is None

    def test_too_few_terms_or_broken_yaml_is_skipped(self, tmp_path):
        (tmp_path / "forensik.yaml").write_text("rows: [satu]\ncolumns: [x, y]\n", encoding="utf-8")
        (tmp_path / "forensik_b.yaml").write_text("rows: [a: b\n", encoding="utf-8")
        assert ca.load_curated_axes("forensik", str(tmp_path)) is None

    def test_env_var_points_to_directory(self, ontology_dir, monkeypatch):
        monkeypatch.setenv("COVERAGE_AXES_DIR", str(ontology_dir))
        assert ca.axes_dir() == ontology_dir
        assert ca.resolve_axes("forensik digital", FORENSIC_PAPERS).source == "curated"

    def test_shipped_forensik_digital_ontology_is_valid(self):
        spec = ca.load_curated_axes("Forensik digital bukti elektronik")
        assert spec is not None and spec.slug == "forensik_digital"
        assert len(spec.rows) >= 2 and len(spec.columns) >= 2
        assert set(spec.important_columns) <= set(spec.columns)


class TestGroundedProposal:
    def test_grounding_drops_terms_absent_from_corpus(self):
        corpus = ca._corpus_text(FORENSIC_PAPERS)
        kept, dropped = ca.grounded_terms(
            ["forensik mobile", "reproducibility", "akurasi", "quantum cryptography"], corpus)
        assert kept == ["forensik mobile", "akurasi"]
        assert dropped == ["reproducibility", "quantum cryptography"]

    def test_llm_json_is_parsed_grounded_and_deduped(self):
        llm = MagicMock()
        llm.generate.return_value = (
            'Berikut sumbunya:\n```json\n{"rows": ["Forensik mobile", "forensik citra", '
            '"Chain of custody", "quantum computing", "forensik mobile"], '
            '"columns": ["akurasi", "admisibilitas", "reproducibility", "akurasi"]}\n```')
        spec = ca.propose_axes("forensik digital", FORENSIC_PAPERS, llm)
        assert spec.source == "llm_grounded"
        assert spec.rows == ["forensik mobile", "forensik citra", "chain of custody"]
        assert spec.columns == ["akurasi", "admisibilitas"]
        assert spec.dropped_ungrounded == ["quantum computing", "reproducibility"]
        assert spec.notes and "2 istilah" in spec.notes[0]
        prompt = llm.generate.call_args.args[0]
        assert "forensik digital" in prompt and "Akuisisi bukti" in prompt, \
            "cuplikan korpus diperlihatkan agar LLM memakai kosakata korpus"

    def test_column_duplicating_a_row_is_removed(self):
        llm = MagicMock()
        llm.generate.return_value = '{"rows": ["akurasi", "forensik citra"], "columns": ["akurasi", "admisibilitas", "standar"]}'
        spec = ca.propose_axes("forensik", FORENSIC_PAPERS, llm)
        assert "akurasi" not in spec.columns and spec.columns == ["admisibilitas", "standar"]

    @pytest.mark.parametrize("reply", [
        "No contradictions detected.",                       # bukan JSON
        '{"rows": ["forensik mobile"], "columns": ["akurasi", "admisibilitas"]}',  # < 2 baris
        '{"rows": ["quantum", "blockchain"], "columns": ["akurasi", "admisibilitas"]}',  # tak grounded
    ])
    def test_falls_back_to_default_vocabulary(self, reply):
        llm = MagicMock()
        llm.generate.return_value = reply
        spec = ca.propose_axes("forensik", FORENSIC_PAPERS, llm)
        assert spec.source == "default"
        assert spec.rows == list(_DEFAULT_ROW_TERMS) and spec.columns == list(_DEFAULT_COLUMN_TERMS)
        assert spec.notes, "alasan fallback dicatat"

    def test_llm_failure_or_absence_is_default_not_an_error(self):
        assert ca.propose_axes("forensik", FORENSIC_PAPERS, None).source == "default"
        llm = MagicMock()
        llm.generate.side_effect = RuntimeError("putus")
        assert ca.propose_axes("forensik", FORENSIC_PAPERS, llm).source == "default"

    def test_curated_wins_over_llm(self, ontology_dir):
        llm = MagicMock()
        spec = ca.resolve_axes("forensik digital", FORENSIC_PAPERS, llm=llm, directory=str(ontology_dir))
        assert spec.source == "curated"
        llm.generate.assert_not_called()


class TestAliasesInCoverageMatrix:
    def test_alias_hit_counts_toward_canonical_term(self):
        papers = [
            {"source": "en.pdf", "content": "disk imaging and acquisition with high accuracy"},
            {"source": "id.pdf", "content": "akuisisi bukti dengan akurasi tinggi"},
            {"source": "x.pdf", "content": "chain of custody dan admisibilitas"},
        ]
        matrix = build_coverage_matrix(
            papers, row_terms=["akuisisi", "chain of custody"],
            column_terms=["akurasi", "admisibilitas"],
            aliases={"akuisisi": ["acquisition", "imaging"], "akurasi": ["accuracy"]},
            paper_ref=lambda p: p["source"],
        )
        assert matrix.cell("akuisisi", "akurasi").papers == ["en.pdf", "id.pdf"]
        assert matrix.cell("akuisisi", "admisibilitas").study_count == 0
        assert matrix.unmapped_papers == []


class TestAnalyzerUsesDomainAxes:
    """Blok Evidence Gap Map memakai sumbu hasil resolve_axes; asalnya tercatat."""

    PAPERS = [
        {"source": "a.pdf", "content": "Forensik mobile: akurasi ekstraksi diukur."},
        {"source": "b.pdf", "content": "Forensik citra: akurasi deteksi pemalsuan diukur."},
        {"source": "c.pdf", "content": "Chain of custody dan admisibilitas bukti di pengadilan."},
    ]

    def _egm(self, indicators):
        return [i for i in indicators if i.detection_method == "evidence_gap_map"]

    def test_curated_axes_shape_the_map(self, ontology_dir, monkeypatch):
        monkeypatch.setenv("COVERAGE_AXES_DIR", str(ontology_dir))
        ga = GapAnalyzer()
        egm = self._egm(ga.analyze_gaps("forensik digital", self.PAPERS, depth="quick"))
        assert len(egm) == 1
        axes = next(s["axes_spec"] for s in egm[0].sub_indicators if "axes_spec" in s)
        assert axes["source"] == "curated" and axes["slug"] == "forensik_digital"
        matrix = next(s["coverage_matrix"] for s in egm[0].sub_indicators if "coverage_matrix" in s)
        assert "forensik mobile" in matrix["rows"] and "admisibilitas" in matrix["columns"]
        assert any("Axes source: curated (forensik_digital.yaml)" in e for e in egm[0].evidence)
        # kolom penting dari kurasi ikut ke overlay signifikansi
        assert any(c["column"] == "admisibilitas" and c["important"]
                   for c in matrix["candidate_gaps"] if c["status"] == "empty")

    def test_llm_grounded_axes_when_no_curated_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("COVERAGE_AXES_DIR", str(tmp_path))
        llm = MagicMock()
        llm.generate.side_effect = [
            "1. Privasi\n2. Standar",  # expected aspects
            '{"rows": ["forensik mobile", "forensik citra", "chain of custody"], '
            '"columns": ["akurasi", "admisibilitas", "reproducibility"]}',
        ]
        ga = GapAnalyzer(llm_interface=llm)
        egm = self._egm(ga.analyze_gaps("forensik digital", self.PAPERS, depth="quick"))
        assert len(egm) == 1
        axes = next(s["axes_spec"] for s in egm[0].sub_indicators if "axes_spec" in s)
        assert axes["source"] == "llm_grounded"
        assert axes["dropped_ungrounded"] == ["reproducibility"]
        assert any("1 LLM-proposed term(s) dropped" in e for e in egm[0].evidence)

    def test_exhausted_or_absent_llm_falls_back_to_default_axes(self, tmp_path, monkeypatch):
        """Tes lama memberi LLM tiruan dengan daftar balasan terbatas; panggilan sumbu
        yang kehabisan balasan tidak boleh menggagalkan analisis."""
        monkeypatch.setenv("COVERAGE_AXES_DIR", str(tmp_path))
        llm = MagicMock()
        llm.generate.side_effect = ["1. Privasi\n2. Standar"]
        ga = GapAnalyzer(llm_interface=llm)
        papers = [
            {"source": "a.pdf", "content": "healthcare deployment with high accuracy"},
            {"source": "b.pdf", "content": "education setting evaluated for usability"},
            {"source": "c.pdf", "content": "finance pilot measured for cost"},
        ]
        egm = self._egm(ga.analyze_gaps("umum", papers, depth="quick"))
        assert len(egm) == 1
        axes = next(s["axes_spec"] for s in egm[0].sub_indicators if "axes_spec" in s)
        assert axes["source"] == "default"
