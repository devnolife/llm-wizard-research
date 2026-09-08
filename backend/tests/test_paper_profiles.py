"""Unit tests — PaperProfile side-channel (per-journal evidence carrier).

Offline: no LLM, no vector store. Exercises the join key that lets weakness
records, gap-mining records and RAG passages resolve to the same journal.
"""

import json

from app.core.gap_detection.paper_profiles import (
    PaperProfile,
    build_profiles,
    normalize_source,
    profile_for,
    profiles_from_context,
)


PAPERS = [
    {"source": "bert_paper.pdf", "title": "BERT: Pre-training", "content": "..."},
    {"source": "yolo_paper.pdf", "title": "YOLO", "content": "..."},
]

WEAKNESSES = [
    {
        "title": "BERT: Pre-training",
        "source": "bert_paper.pdf",
        "tersurat": [{
            "poin": "Hanya diuji pada bahasa Inggris",
            "dasar": "Penulis menyebut evaluasi terbatas pada GLUE",
            "kutipan": "we only evaluate on English benchmarks",
            "verification_status": "terverifikasi",
            "confidence": 0.91,
        }],
        "tersirat": [{
            "poin": "Tidak ada uji statistik",
            "dasar": "Tabel hasil tanpa interval kepercayaan",
            "verification_status": "inferensi",
            "confidence": 0.4,
        }],
    },
    # A weakness record for a journal that is NOT in this job must not create a
    # phantom profile.
    {"title": "Stray", "source": "stray.pdf", "tersurat": [], "tersirat": []},
]

AUTHOR_GAPS = [
    {
        "source": "07_bert_paper.pdf",  # job-dir prefix from another run
        "statement": "Future work should evaluate multilingual settings.",
        "paraphrase": "Perlu evaluasi multibahasa.",
        "kind": "explicit_future_work",
        "chunk_id": "bert::12::abc",
        "grounding_score": 1.0,
    },
    {"source": "yolo_paper.pdf", "statement": "", "kind": "implicit_gap"},  # empty → skipped
]


class TestNormalizeSource:
    def test_prefix_and_case_are_ignored(self):
        assert normalize_source("07_Bert_Paper.pdf") == normalize_source("bert_paper.pdf")
        assert normalize_source("bert_paper.pdf") == "bert_paper.pdf"

    def test_basename_only(self):
        assert normalize_source("/data/raw/analysis_jobs/x/03_a b.pdf") == "a b.pdf"
        assert normalize_source("C:\\Users\\me\\03_a.pdf") == "a.pdf"

    def test_underscore_inside_name_is_kept(self):
        # bert_paper.pdf and yolo_paper.pdf must NOT collapse into "paper.pdf"
        assert normalize_source("bert_paper.pdf") != normalize_source("yolo_paper.pdf")

    def test_empty_and_unknown(self):
        assert normalize_source(None) == ""
        assert normalize_source("  ") == ""
        assert normalize_source("Unknown") == ""


class TestBuildProfiles:
    def test_profiles_keyed_by_normalised_source(self):
        profiles = build_profiles(PAPERS, weaknesses=WEAKNESSES, author_gaps=AUTHOR_GAPS)
        assert set(profiles) == {"bert_paper.pdf", "yolo_paper.pdf"}
        bert = profiles["bert_paper.pdf"]
        assert bert.title == "BERT: Pre-training"
        assert len(bert.weaknesses["tersurat"]) == 1
        assert len(bert.author_gaps) == 1  # joined despite the "07_" prefix
        assert profiles["yolo_paper.pdf"].author_gaps == []

    def test_statements_only_quote_verbatim_text(self):
        profiles = build_profiles(PAPERS, weaknesses=WEAKNESSES, author_gaps=AUTHOR_GAPS)
        statements = profiles["bert_paper.pdf"].statements()
        kinds = {s["kind"]: s for s in statements}
        assert set(kinds) == {"tersurat", "tersirat", "explicit_future_work"}
        assert kinds["tersurat"]["quote"] == "we only evaluate on English benchmarks"
        assert kinds["tersirat"]["quote"] is None
        assert kinds["explicit_future_work"]["quote"].startswith("Future work should")
        assert kinds["explicit_future_work"]["chunk_id"] == "bert::12::abc"
        assert all(s["source"] == "bert_paper.pdf" for s in statements)

    def test_workflow_and_references_attach_by_source(self):
        profiles = build_profiles(
            PAPERS,
            workflows={"07_bert_paper.pdf": {"evaluation_metrics": {"value": "accuracy"}}},
            references={"yolo_paper.pdf": [{"raw": "[1] A. B. Title. 2020.", "key": "b|2020|title"}]},
        )
        assert profiles["bert_paper.pdf"].workflow == {"evaluation_metrics": {"value": "accuracy"}}
        assert profiles["yolo_paper.pdf"].references[0]["key"] == "b|2020|title"
        assert profiles["yolo_paper.pdf"].workflow is None

    def test_to_dict_is_json_serialisable_and_round_trips(self):
        profiles = build_profiles(PAPERS, weaknesses=WEAKNESSES, author_gaps=AUTHOR_GAPS)
        payload = {k: v.to_dict() for k, v in profiles.items()}
        json.dumps(payload)  # must not raise
        back = profiles_from_context(payload)
        assert set(back) == set(profiles)
        assert back["bert_paper.pdf"].statements() == profiles["bert_paper.pdf"].statements()

    def test_profiles_from_context_ignores_garbage(self):
        assert profiles_from_context(None) == {}
        assert profiles_from_context({"x": 42}) == {}


class TestProfileFor:
    def test_rag_passage_resolves_via_metadata(self):
        profiles = build_profiles(PAPERS)
        passage = {"content": "...", "metadata": {"source": "07_bert_paper.pdf", "title": "Unknown"}}
        assert profile_for(passage, profiles) is profiles["bert_paper.pdf"]

    def test_job_paper_dict_resolves_via_source(self):
        profiles = build_profiles(PAPERS)
        assert profile_for({"source": "yolo_paper.pdf"}, profiles) is profiles["yolo_paper.pdf"]

    def test_title_fallback(self):
        profiles = {"bert: pre-training": PaperProfile(source="BERT: Pre-training")}
        assert profile_for({"title": "BERT: Pre-training"}, profiles) is not None

    def test_missing_profile_is_none(self):
        profiles = build_profiles(PAPERS)
        assert profile_for({"source": "nope.pdf", "title": "Unknown"}, profiles) is None
        assert profile_for({"source": "nope.pdf"}, {}) is None
