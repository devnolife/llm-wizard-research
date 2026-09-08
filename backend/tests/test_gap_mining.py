"""Unit tests for gap mining + novelty (TAHAP 2/3), no LLM/network.

The LLM and OpenAlex calls are injected as fakes so these are fast and
deterministic.
"""

from app.core.gap_mining.candidates import matched_phrases, select_candidates, with_context
from app.core.gap_mining.extractor import (
    _normalize_gap,
    _parse_json_array,
    extract_gaps_from_candidate,
)
from app.core.gap_mining.verify import is_grounded, verify_gaps
from app.core.gap_mining.novelty import build_keywords, classify_novelty


def _chunk(cid, src, idx, text, section="discussion", is_ref=False):
    return {
        "record": "chunk", "chunk_id": cid, "source": src, "chunk_index": idx,
        "text": text, "section_normalized": section, "is_reference": is_ref,
        "paper_title": "T", "year": 2022, "doi": None,
    }


class TestCandidates:
    def test_phrase_matching_multilingual(self):
        assert "future work" in matched_phrases("In future work we will explore X.")
        assert any("belum dilakukan" in p for p in matched_phrases("Hal ini belum dilakukan."))

    def test_select_by_section_and_phrase(self):
        chunks = [
            _chunk("a", "p.pdf", 0, "Some methodology text here that is long enough.", "methods"),
            _chunk("b", "p.pdf", 1, "In conclusion this is a discussion chunk of prose.", "discussion"),
            _chunk("c", "p.pdf", 2, "Future work should explore deep learning here soon.", "methods"),
            _chunk("d", "p.pdf", 3, "References list here", "references", is_ref=True),
        ]
        cands = select_candidates(chunks)
        ids = {c["chunk_id"] for c in cands}
        assert "b" in ids  # discussion section
        assert "c" in ids  # phrase match in a non-target section
        assert "a" not in ids  # methods, no phrase
        assert "d" not in ids  # reference excluded

    def test_with_context_includes_neighbors(self):
        chunks = [_chunk(str(i), "p.pdf", i, f"Sentence chunk number {i} here.") for i in range(3)]
        by_source = {"p.pdf": chunks}
        ctx = with_context(chunks[1], by_source)
        assert "number 0" in ctx and "number 1" in ctx and "number 2" in ctx


class TestExtractorParsing:
    def test_parse_json_array_with_fence(self):
        reply = '```json\n[{"gap_type":"stated_limitation","gap_statement":"x"}]\n```'
        out = _parse_json_array(reply)
        assert out and out[0]["gap_type"] == "stated_limitation"

    def test_parse_single_object(self):
        out = _parse_json_array('{"gap_statement":"y"}')
        assert len(out) == 1

    def test_normalize_rejects_short_and_defaults(self):
        cand = {"source": "p.pdf", "chunk_id": "a", "paper_title": "T", "year": 2022}
        assert _normalize_gap({"gap_statement": "too short"}, cand) is None
        norm = _normalize_gap(
            {"gap_statement": "A sufficiently long verbatim gap statement here.",
             "gap_type": "bogus", "topic": "bogus"}, cand)
        assert norm["gap_type"] == "implicit_gap"  # invalid -> default
        assert norm["topic"] == "other"
        assert norm["evidence_chunk_ids"] == ["a"]

    def test_extract_with_fake_llm(self):
        cand = {"source": "p.pdf", "chunk_id": "a", "paper_title": "T", "year": 2022,
                "text": "Future work should address scalability."}

        def fake_gen(prompt, system):
            return '[{"gap_type":"explicit_future_work","gap_statement":"Future work should address scalability.","gap_paraphrase":"Perlu penelitian skalabilitas.","topic":"tools"}]'

        gaps = extract_gaps_from_candidate(cand, cand["text"], generate_fn=fake_gen)
        assert len(gaps) == 1
        assert gaps[0]["topic"] == "tools"


class TestVerify:
    def test_grounded_true_for_verbatim(self):
        text = "The system was not evaluated on mobile devices in this study."
        assert is_grounded("not evaluated on mobile devices", text)

    def test_verify_drops_hallucination(self):
        by_source = {"p.pdf": [_chunk("a", "p.pdf", 0, "We studied images on desktops only.")]}
        gaps = [
            {"source": "p.pdf", "gap_statement": "We studied images on desktops only.",
             "evidence_chunk_ids": ["a"]},
            {"source": "p.pdf", "gap_statement": "A totally invented claim about quantum blockchains.",
             "evidence_chunk_ids": ["a"]},
        ]
        kept = verify_gaps(gaps, by_source)
        assert len(kept) == 1
        assert kept[0]["grounding_score"] >= 0.82


class TestNovelty:
    def test_build_keywords(self):
        gap = {"gap_statement": "mobile forensic tools lack validation on Android devices",
               "gap_paraphrase": "alat forensik mobile belum tervalidasi", "topic": "mobile_forensics"}
        kw = build_keywords(gap)
        assert "forensic" in kw or "mobile" in kw

    def test_classify_open_when_no_results(self):
        class FakeOA:
            def search_recent(self, q, from_date="2024-01-01", max_results=8):
                return []
        gap = {"gap_statement": "x forensic gap", "gap_paraphrase": "y", "topic": "tools"}
        out = classify_novelty(gap, openalex=FakeOA())
        assert out["novelty_status"] == "open"
        assert out["related_recent_papers"] == []
        assert out["checked_at"]

    def test_classify_addressed_when_strong_matches(self):
        class P:
            def __init__(self, t):
                self.title = t
                self.abstract = t
                self.year = 2025
                self.doi = "10.1/x"

        class FakeOA:
            def search_recent(self, q, from_date="2024-01-01", max_results=8):
                # three strong matches to the query terms
                return [P("mobile forensic tools android validation") for _ in range(3)]

        gap = {"gap_statement": "mobile forensic tools android validation needed",
               "gap_paraphrase": "validasi alat forensik android", "topic": "mobile_forensics"}
        out = classify_novelty(gap, openalex=FakeOA())
        assert out["novelty_status"] in ("addressed", "partially_addressed")
        assert len(out["related_recent_papers"]) >= 1

    def test_unavailable_source_is_unchecked_not_open(self):
        """Kuota/429/jaringan mati tidak boleh terbaca sebagai 'semua gap baru'."""
        class DownOA:
            BASE_URL = "https://api.openalex.org/works"

            def search_recent(self, q, from_date="2024-01-01", max_results=8):
                return None

        gap = {"gap_statement": "x forensic gap statement here", "topic": "tools"}
        out = classify_novelty(gap, openalex=DownOA())
        assert out["novelty_status"] == "unchecked"
        assert out["novelty_error"] and out["related_recent_papers"] == []

    def test_annotate_limit_marks_the_rest_unchecked(self):
        from app.core.gap_mining.novelty import annotate_gaps

        class NoHits:
            BASE_URL = "https://api.openalex.org/works"
            calls = 0

            def search_recent(self, q, from_date="2024-01-01", max_results=8):
                NoHits.calls += 1
                return []

        gaps = [{"gap_statement": f"gap statement number {i} forensic"} for i in range(5)]
        out = annotate_gaps(gaps, openalex=NoHits(), limit=2)
        assert [g["novelty_status"] for g in out] == ["open", "open"] + ["unchecked"] * 3
        assert all(g["novelty_error"] == "di luar batas cek" for g in out[2:])
        assert NoHits.calls == 2, "gap di luar batas tidak boleh menghabiskan kuota"

    def test_openalex_disabled_marks_all_unchecked_without_network(self, monkeypatch):
        from app.core.gap_mining import novelty

        monkeypatch.setenv(novelty.ENV_DISABLED, "1")

        class Boom:
            def search_recent(self, *a, **k):
                raise AssertionError("tidak boleh ada permintaan jaringan saat dimatikan")

        monkeypatch.setattr(novelty, "OpenAlexAPI",
                            lambda *a, **k: (_ for _ in ()).throw(AssertionError("konstruksi klien")))
        gaps = [{"gap_statement": f"gap statement number {i} forensic"} for i in range(3)]
        out = novelty.annotate_gaps(gaps, openalex=Boom())
        assert [g["novelty_status"] for g in out] == ["unchecked"] * 3
        assert all(g["novelty_error"] == novelty.DISABLED_REASON for g in out)
        assert all(g["novelty_query"] and g["related_recent_papers"] == [] for g in out)

    def test_openalex_disabled_flag_parsing(self, monkeypatch):
        from app.core.gap_mining.novelty import ENV_DISABLED, novelty_disabled

        for raw, expected in (("1", True), ("true", True), ("YES", True),
                              ("0", False), ("", False), ("false", False)):
            monkeypatch.setenv(ENV_DISABLED, raw)
            assert novelty_disabled() is expected, raw
        monkeypatch.delenv(ENV_DISABLED)
        assert novelty_disabled() is False


class TestHttpCacheQuotaCooldown:
    """OpenAlex menjawab kuota habis dengan 429 + Retry-After ~13 jam."""

    def setup_method(self):
        from app.services.paper_apis import http_cache
        http_cache.clear_cooldowns()

    def test_long_retry_after_sets_cooldown_and_skips_retries(self, monkeypatch, tmp_path):
        from app.services.paper_apis import http_cache

        class Resp:
            status_code = 429
            headers = {"Retry-After": "46748"}

        calls = []
        monkeypatch.setattr(http_cache.requests, "get", lambda *a, **k: calls.append(a) or Resp())
        monkeypatch.setattr(http_cache.time, "sleep", lambda s: None)

        url = "https://api.openalex.org/works"
        assert http_cache.get_json(url, {"search": "a"}, cache_dir=tmp_path, min_interval=0) is None
        assert len(calls) == 1, "tidak boleh retry pada kuota habis"
        cooldown = http_cache.host_cooldown(url)
        assert cooldown and cooldown["seconds_left"] > 46000 and "kuota" in cooldown["reason"]

        # permintaan berikutnya ke host yang sama tidak menyentuh jaringan
        assert http_cache.get_json(url, {"search": "b"}, cache_dir=tmp_path, min_interval=0) is None
        assert len(calls) == 1

    def test_short_429_still_retries_with_backoff(self, monkeypatch, tmp_path):
        from app.services.paper_apis import http_cache

        class Resp:
            status_code = 429
            headers = {"Retry-After": "2"}

        calls = []
        monkeypatch.setattr(http_cache.requests, "get", lambda *a, **k: calls.append(a) or Resp())
        monkeypatch.setattr(http_cache.time, "sleep", lambda s: None)

        assert http_cache.get_json("https://api.openalex.org/works", {"search": "a"},
                                   cache_dir=tmp_path, min_interval=0, max_retries=2) is None
        assert len(calls) == 3
        assert http_cache.host_cooldown("api.openalex.org") is None
