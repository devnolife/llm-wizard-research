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
