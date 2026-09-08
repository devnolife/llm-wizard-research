"""
Unit tests — GapAnalyzer (3-indicator Cooper/Booth model).

Covers each indicator's detection logic plus Rule Engine integration:
    1. FRAGMENTATION   — topic clustering on divergent keyword sets
    2. INCONSISTENCY   — FactTable CONTRADICTS facts + LLM NLI detection
    3. INCOMPLETENESS  — uncovered aspects + methodology homogeneity
    4. Rule Engine     — REJECT filtering, verdict & confidence propagation
    5. Epistemological boundary — every indicator requires human validation

All tests run offline — no Ollama, no ChromaDB.
"""

import pytest
from unittest.mock import MagicMock

from app.core.gap_detection.analyzer import GapAnalyzer, GapIndicator
from app.core.knowledge.fact_table import (
    Entity,
    EntityType,
    Fact,
    FactTable,
    PredicateType,
)
from app.models.responses import IndicatorType, RuleVerdictType


# ===================================================================
# Fixtures
# ===================================================================

def make_paper(doc_id, content, keywords=None, title=None):
    return {
        "doc_id": doc_id,
        "content": content,
        "metadata": {
            "title": title or doc_id,
            "keywords": keywords or [],
        },
    }


@pytest.fixture
def divergent_papers():
    """Three papers with no keyword overlap → distinct clusters."""
    return [
        make_paper("p1", "We run a randomized experiment with statistical tests.",
                   keywords=["experiment", "statistics"]),
        make_paper("p2", "A qualitative case study based on interviews.",
                   keywords=["case study", "interviews"]),
        make_paper("p3", "Deep learning simulation of network traffic.",
                   keywords=["deep learning", "simulation"]),
    ]


@pytest.fixture
def homogeneous_papers():
    """Three papers all using the same single methodology."""
    return [
        make_paper("h1", "We use deep learning for detection.", keywords=["deep learning"]),
        make_paper("h2", "Our deep learning approach improves accuracy.", keywords=["deep learning"]),
        make_paper("h3", "A deep learning pipeline for segmentation.", keywords=["deep learning"]),
    ]


@pytest.fixture
def contradicting_fact_table():
    ft = FactTable()
    fa = Entity("find_a", EntityType.FINDING, "Dropout improves accuracy")
    fb = Entity("find_b", EntityType.FINDING, "Dropout reduces accuracy")
    ft.add_entity(fa)
    ft.add_entity(fb)
    ft.add_fact(Fact(
        fact_id="c1", subject_id="find_a",
        predicate=PredicateType.CONTRADICTS, object_id="find_b",
        source="Section 4", source_paper="paper_x", confidence=0.8,
    ))
    return ft


# ===================================================================
# Indicator 1: FRAGMENTATION
# ===================================================================

class TestFragmentation:
    def test_detected_with_distinct_clusters(self, divergent_papers):
        ga = GapAnalyzer()  # no LLM, no KG — pure clustering
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="quick")

        frag = [i for i in indicators if i.indicator_type == IndicatorType.FRAGMENTATION]
        assert len(frag) >= 1
        assert frag[0].detection_method == "topic_clustering"
        # Confidence is calibrated from measured cluster separation: fully
        # disjoint approach-sets (as in this fixture) score near the top of the
        # defensible band rather than a fixed heuristic value.
        assert 0.6 <= frag[0].confidence <= 0.9
        assert frag[0].sub_indicators  # cluster traceability

    def test_not_detected_with_single_paper(self):
        ga = GapAnalyzer()
        indicators = ga.analyze_gaps(
            "test topic", [make_paper("only", "content", ["kw"])], depth="quick"
        )
        frag = [i for i in indicators if i.indicator_type == IndicatorType.FRAGMENTATION]
        assert frag == []


# ===================================================================
# Indicator 2: INCONSISTENCY
# ===================================================================

class TestInconsistency:
    def test_detected_from_fact_table(self, contradicting_fact_table, divergent_papers):
        ga = GapAnalyzer(fact_table=contradicting_fact_table)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="standard")

        inc = [i for i in indicators if i.indicator_type == IndicatorType.INCONSISTENCY]
        assert len(inc) >= 1
        ft_based = [i for i in inc if i.detection_method == "fact_table_contradicts"]
        assert len(ft_based) == 1
        assert "Dropout improves accuracy" in ft_based[0].description
        # Without a RelationClassifier the contradiction is unverified, so
        # its confidence is capped at 0.5 (was raw fact confidence 0.8).
        assert ft_based[0].confidence == pytest.approx(0.5)

    def test_llm_detected_contradiction(self, divergent_papers):
        llm = MagicMock()
        llm.generate.return_value = (
            "Paper A claims dropout helps; Paper B claims it hurts. "
            "These findings are contradictory and unresolved."
        )
        ga = GapAnalyzer(llm_interface=llm)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="standard")

        llm_inc = [i for i in indicators if i.detection_method == "llm_nli"]
        assert len(llm_inc) == 1
        # LLM-only contradictions get LOW confidence (epistemological caution):
        # lower than the dedicated NLI cross-encoder signal, which is preferred.
        assert llm_inc[0].confidence == pytest.approx(0.4)

    def test_llm_no_contradiction_found(self, divergent_papers):
        llm = MagicMock()
        llm.generate.return_value = "No contradictions detected."
        ga = GapAnalyzer(llm_interface=llm)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="standard")

        assert [i for i in indicators if i.detection_method == "llm_nli"] == []

    def test_skipped_at_quick_depth(self, contradicting_fact_table, divergent_papers):
        ga = GapAnalyzer(fact_table=contradicting_fact_table)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="quick")
        inc = [i for i in indicators if i.indicator_type == IndicatorType.INCONSISTENCY]
        assert inc == []


# ===================================================================
# Contradiction validation filter (false-positive guard)
# ===================================================================

class TestContradictionValidation:
    """CONTRADICTS facts must be validated before becoming indicators."""

    @staticmethod
    def _ft(subj_type, obj_type, subj_name, obj_name, confidence=0.7):
        ft = FactTable()
        ft.add_entity(Entity("e_a", subj_type, subj_name))
        ft.add_entity(Entity("e_b", obj_type, obj_name))
        ft.add_fact(Fact(
            fact_id="c1", subject_id="e_a",
            predicate=PredicateType.CONTRADICTS, object_id="e_b",
            source="However, results differ across studies.",
            source_paper="paper_x", confidence=confidence,
        ))
        return ft

    def test_method_vs_method_discarded(self, divergent_papers):
        """Two METHOD entities (e.g. 'Residual Networks' vs 'SSD') are not a
        scientific contradiction — extraction artifact must be discarded."""
        ft = self._ft(EntityType.METHOD, EntityType.METHOD,
                      "Residual Networks", "SSD")
        ga = GapAnalyzer(fact_table=ft)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="standard")
        assert [i for i in indicators
                if i.detection_method == "fact_table_contradicts"] == []

    def test_short_finding_names_discarded(self, divergent_papers):
        """FINDING entities whose names are bare labels (<3 words) are not
        comparable claim statements."""
        ft = self._ft(EntityType.FINDING, EntityType.FINDING, "ResNet", "SSD")
        ga = GapAnalyzer(fact_table=ft)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="standard")
        assert [i for i in indicators
                if i.detection_method == "fact_table_contradicts"] == []

    def test_classifier_confirmation_keeps_indicator(self, divergent_papers):
        """A classifier-confirmed contradiction keeps min(fact, classifier) conf."""
        from app.core.validation.relation_classifier import RelationType
        ft = self._ft(EntityType.FINDING, EntityType.FINDING,
                      "Dropout improves accuracy", "Dropout reduces accuracy",
                      confidence=0.8)
        classifier = MagicMock()
        classified = MagicMock()
        classified.relation_type = RelationType.CONTRADICTION
        classified.rule_validated = True
        classified.confidence = 0.75
        classifier.classify.return_value = classified
        ga = GapAnalyzer(fact_table=ft, relation_classifier=classifier)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="standard")
        ft_based = [i for i in indicators
                    if i.detection_method == "fact_table_contradicts"]
        assert len(ft_based) == 1
        assert ft_based[0].confidence == pytest.approx(0.75)

    def test_classifier_rejection_discards_indicator(self, divergent_papers):
        """If the 3-layer classifier says CO_OCCURRENCE, the fact is dropped."""
        from app.core.validation.relation_classifier import RelationType
        ft = self._ft(EntityType.FINDING, EntityType.FINDING,
                      "Dropout improves accuracy", "Dropout reduces accuracy")
        classifier = MagicMock()
        classified = MagicMock()
        classified.relation_type = RelationType.CO_OCCURRENCE
        classified.rule_validated = False
        classified.confidence = 0.3
        classifier.classify.return_value = classified
        ga = GapAnalyzer(fact_table=ft, relation_classifier=classifier)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="standard")
        assert [i for i in indicators
                if i.detection_method == "fact_table_contradicts"] == []


# ===================================================================
# Indicator 3: INCOMPLETENESS
# ===================================================================

class TestIncompleteness:
    def test_uncovered_aspects_detected(self, homogeneous_papers):
        llm = MagicMock()
        # First call: contradiction check; second: expected aspects.
        # Order: _detect_inconsistency (standard) runs before _detect_incompleteness.
        llm.generate.side_effect = [
            "No contradictions detected.",
            "1. Privacy\n2. Scalability\n3. Cost analysis\n4. Ethical review",
        ]
        ga = GapAnalyzer(llm_interface=llm)
        indicators = ga.analyze_gaps("test topic", homogeneous_papers, depth="standard")

        aspect = [i for i in indicators if i.detection_method == "aspect_coverage"]
        assert len(aspect) == 1
        assert aspect[0].indicator_type == IndicatorType.INCOMPLETENESS
        assert "critical aspect" in aspect[0].description

    def test_methodological_homogeneity_detected(self, homogeneous_papers):
        ga = GapAnalyzer()  # no LLM → only methodology check
        indicators = ga.analyze_gaps("test topic", homogeneous_papers, depth="quick")

        meth = [i for i in indicators if i.detection_method == "methodology_coverage"]
        assert len(meth) == 1
        # Confidence is calibrated by method dominance: 3 papers sharing one
        # method → 0.4 + 0.4 * (3/5) = 0.64. More papers → stronger signal.
        assert meth[0].confidence == pytest.approx(0.64)
        assert "deep learning" in meth[0].description

    def test_aspect_grounding_splits_parametric_aspects(self, homogeneous_papers):
        """Aspects absent from the corpus vocabulary are marked ungrounded
        (parametric LLM knowledge) and reduce indicator confidence."""
        ga = GapAnalyzer()
        grounded, ungrounded = ga._ground_aspects(
            ["detection accuracy analysis", "quantum cryptography ethics"],
            homogeneous_papers,  # contents mention detection/accuracy, not quantum
        )
        assert grounded == ["detection accuracy analysis"]
        assert ungrounded == ["quantum cryptography ethics"]


# ===================================================================
# Rule Engine integration
# ===================================================================

class TestRuleEngineIntegration:
    def _engine_returning(self, verdict, adjusted=0.4):
        engine = MagicMock()
        report = MagicMock()
        report.overall_verdict = verdict
        report.adjusted_confidence = adjusted
        engine.validate.return_value = report
        return engine

    def test_rejected_indicators_filtered_out(self, divergent_papers):
        ga = GapAnalyzer(rule_engine=self._engine_returning("REJECT", 0.1))
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="quick")
        assert indicators == []

    def test_verdict_and_confidence_propagated(self, divergent_papers):
        ga = GapAnalyzer(rule_engine=self._engine_returning("FLAG", 0.42))
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="quick")

        assert len(indicators) >= 1
        for ind in indicators:
            assert ind.rule_engine_verdict == RuleVerdictType.FLAG
            assert ind.adjusted_confidence == pytest.approx(0.42)
            assert ind.confidence == pytest.approx(0.42)

    def test_no_rule_engine_leaves_verdict_none(self, divergent_papers):
        """Ablation mode (H7): without rule engine, verdict stays None."""
        ga = GapAnalyzer(rule_engine=None)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="quick")
        assert len(indicators) >= 1
        for ind in indicators:
            assert ind.rule_engine_verdict is None


# ===================================================================
# Epistemological boundary (revisi.md §4 / BAB I §1.5)
# ===================================================================

class TestEpistemologicalBoundary:
    def test_all_indicators_require_human_validation(
        self, contradicting_fact_table, divergent_papers
    ):
        llm = MagicMock()
        llm.generate.side_effect = [
            "Papers contradict each other on dropout.",
            "1. Privacy\n2. Cost",
        ]
        ga = GapAnalyzer(llm_interface=llm, fact_table=contradicting_fact_table)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="standard")

        assert len(indicators) >= 2
        assert all(ind.requires_human_validation for ind in indicators)

    def test_indicators_sorted_by_confidence(self, divergent_papers):
        ga = GapAnalyzer()
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="quick")
        confidences = [i.confidence for i in indicators]
        assert confidences == sorted(confidences, reverse=True)


# ===================================================================
# Paper references in indicators (traceability for readers)
# ===================================================================

class TestPaperReferences:
    def test_paper_ref_prefers_source_then_title(self):
        from app.core.gap_detection.analyzer import _paper_ref

        assert _paper_ref({"title": "Judul A", "source": "a.pdf"}) == "a.pdf"
        assert _paper_ref({"title": "Judul A"}) == "Judul A"
        assert _paper_ref({"title": "Unknown", "metadata": {"title": "Judul Meta"}}) == "Judul Meta"
        assert _paper_ref({"doc_id": "d1"}) == "d1"
        assert _paper_ref({"title": "  spasi \n ganda  "}) == "spasi ganda"
        assert _paper_ref({}) == ""

    def test_paper_refs_dedupes_and_drops_empty(self):
        from app.core.gap_detection.analyzer import _paper_refs

        papers = [
            {"title": "Judul A"},
            {"title": "Judul A"},
            {},
            {"source": "b.pdf"},
        ]
        assert _paper_refs(papers) == ["Judul A", "b.pdf"]

    def test_fragmentation_related_papers_use_sources_for_rag_passages(self):
        """Passages from rag_tool carry title/source but no doc_id — indicators
        must still name the journals instead of emitting empty strings."""
        papers = [
            {"title": "Jurnal Eksperimen", "source": "01_exp.pdf",
             "content": "We run a randomized experiment with statistical tests.",
             "metadata": {"keywords": ["experiment", "statistics"]}},
            {"title": "Jurnal Kualitatif", "source": "02_case.pdf",
             "content": "A qualitative case study based on interviews.",
             "metadata": {"keywords": ["case study", "interviews"]}},
            {"title": "Unknown", "source": "03_dl.pdf",
             "content": "Deep learning simulation of network traffic.",
             "metadata": {"keywords": ["deep learning", "simulation"]}},
        ]
        ga = GapAnalyzer()
        indicators = ga.analyze_gaps("test topic", papers, depth="quick")

        assert indicators
        for ind in indicators:
            refs = ind.related_papers
            assert refs, f"{ind.detection_method} has no related_papers"
            assert all(r.strip() for r in refs), f"empty ref in {refs}"
        frag = [i for i in indicators if i.indicator_type == IndicatorType.FRAGMENTATION]
        assert frag
        joined = " ".join(frag[0].related_papers)
        assert "01_exp.pdf" in joined
        assert "03_dl.pdf" in joined


# ===================================================================
# Author-stated corroboration (per-journal side-channel)
# ===================================================================

class TestAuthorCorroboration:
    """Author limitations / future work are EVIDENCE for an indicator, never a gap."""

    PAPER_CONTENTS = [{"source": s, "title": s} for s in ("h1", "h2", "h3")]

    @staticmethod
    def _weakness(source, kind="tersurat"):
        point = {
            "poin": "Alternative methodological approaches are absent",
            "dasar": "Only deep learning is evaluated",
            "verification_status": "terverifikasi" if kind == "tersurat" else "inferensi",
            "confidence": 0.9,
        }
        if kind == "tersurat":
            point["kutipan"] = "we evaluated a single deep learning approach only"
        return {"title": source, "source": source,
                "tersurat": [point] if kind == "tersurat" else [],
                "tersirat": [point] if kind == "tersirat" else []}

    def _methodology_indicator(self, indicators):
        meth = [i for i in indicators if i.detection_method == "methodology_coverage"]
        assert len(meth) == 1
        return meth[0]

    def _corroboration(self, indicator):
        found = [s["author_corroboration"] for s in indicator.sub_indicators
                 if "author_corroboration" in s]
        return found[0] if found else None

    def test_explicit_statement_becomes_evidence_and_verbatim_quote(self, homogeneous_papers):
        from app.core.gap_detection.paper_profiles import build_profiles

        profiles = build_profiles(self.PAPER_CONTENTS, weaknesses=[self._weakness("h1")])
        ga = GapAnalyzer()
        before = self._methodology_indicator(
            ga.analyze_gaps("test topic", homogeneous_papers, depth="quick"))
        after = self._methodology_indicator(ga.analyze_gaps(
            "test topic", homogeneous_papers, depth="quick",
            paper_profiles={k: v.to_dict() for k, v in profiles.items()}))

        hits = self._corroboration(after)
        assert hits and hits[0]["source"] == "h1" and hits[0]["kind"] == "tersurat"
        quotes = [q for q in after.supporting_quotes if q.get("origin") == "author_stated"]
        assert len(quotes) == 1
        assert quotes[0]["quote"] == "we evaluated a single deep learning approach only"
        assert quotes[0]["source_paper"] == "h1" and quotes[0]["kind"] == "tersurat"
        assert any(e.startswith("Korroborasi penulis: 1 pernyataan dari 1 jurnal")
                   for e in after.evidence)
        # Evidence only: the score is exactly what the profile-less run produced.
        assert after.confidence == pytest.approx(before.confidence)
        assert after.description == before.description

    def test_implicit_statement_is_traceable_but_never_quoted(self, homogeneous_papers):
        from app.core.gap_detection.paper_profiles import build_profiles

        profiles = build_profiles(self.PAPER_CONTENTS,
                                  weaknesses=[self._weakness("h2", kind="tersirat")])
        ga = GapAnalyzer()
        ind = self._methodology_indicator(ga.analyze_gaps(
            "test topic", homogeneous_papers, depth="quick",
            paper_profiles={k: v.to_dict() for k, v in profiles.items()}))

        hits = self._corroboration(ind)
        assert hits and hits[0]["kind"] == "tersirat" and hits[0]["quote"] is None
        assert [q for q in ind.supporting_quotes if q.get("origin") == "author_stated"] == []

    def test_gap_mining_statement_is_quoted_with_its_kind(self, homogeneous_papers):
        from app.core.gap_detection.paper_profiles import build_profiles

        profiles = build_profiles(self.PAPER_CONTENTS, author_gaps=[{
            "source": "07_h3",  # job-dir prefix from the gap-mining run
            "statement": "Future work should apply alternative methodological approaches.",
            "paraphrase": "Perlu pendekatan metodologis alternatif.",
            "kind": "explicit_future_work",
            "chunk_id": "h3::4::abc",
            "grounding_score": 1.0,
        }])
        ga = GapAnalyzer()
        ind = self._methodology_indicator(ga.analyze_gaps(
            "test topic", homogeneous_papers, depth="quick",
            paper_profiles={k: v.to_dict() for k, v in profiles.items()}))

        quotes = [q for q in ind.supporting_quotes if q.get("origin") == "author_stated"]
        assert len(quotes) == 1 and quotes[0]["kind"] == "explicit_future_work"
        assert quotes[0]["quote"].startswith("Future work should apply")
        assert self._corroboration(ind)[0]["chunk_id"] == "h3::4::abc"

    def test_unrelated_journal_is_not_searched_when_related_ones_exist(self, homogeneous_papers):
        from app.core.gap_detection.paper_profiles import build_profiles

        profiles = build_profiles(
            self.PAPER_CONTENTS + [{"source": "zz", "title": "zz"}],
            weaknesses=[self._weakness("zz")],
        )
        ga = GapAnalyzer()
        ind = self._methodology_indicator(ga.analyze_gaps(
            "test topic", homogeneous_papers, depth="quick",
            paper_profiles={k: v.to_dict() for k, v in profiles.items()}))
        assert self._corroboration(ind) is None

    def test_falls_back_to_all_profiles_when_none_are_related(self, homogeneous_papers):
        from app.core.gap_detection.paper_profiles import build_profiles

        profiles = build_profiles([{"source": "zz", "title": "zz"}],
                                  weaknesses=[self._weakness("zz")])
        ga = GapAnalyzer()
        ind = self._methodology_indicator(ga.analyze_gaps(
            "test topic", homogeneous_papers, depth="quick",
            paper_profiles={k: v.to_dict() for k, v in profiles.items()}))
        assert self._corroboration(ind)[0]["source"] == "zz"

    def test_without_profiles_output_is_unchanged(self, homogeneous_papers):
        ga = GapAnalyzer()
        plain = [i.to_dict() for i in ga.analyze_gaps("test topic", homogeneous_papers, depth="quick")]
        empty = [i.to_dict() for i in ga.analyze_gaps(
            "test topic", homogeneous_papers, depth="quick", paper_profiles={})]
        assert plain == empty
        assert all("author_corroboration" not in s
                   for ind in plain for s in ind["sub_indicators"])
        assert all(q.get("origin") is None
                   for ind in plain for q in ind["supporting_quotes"])


# ===================================================================
# Workflow-stage mining (methodological incompleteness from pipelines)
# ===================================================================

class TestWorkflowStageMining:
    PAPER_CONTENTS = [{"source": s, "title": s} for s in ("h1", "h2", "h3")]

    @staticmethod
    def _stage(value, quote="", verified=False):
        return {"value": value, "kutipan": quote, "verified": verified,
                "match_score": 0.95 if verified else 0.0}

    def _profiles(self, workflows):
        from app.core.gap_detection.paper_profiles import build_profiles

        profiles = build_profiles(self.PAPER_CONTENTS, workflows=workflows)
        return {k: v.to_dict() for k, v in profiles.items()}

    def _homogeneous_workflows(self):
        return {
            "h1": {"method_model": self._stage("CNN"),
                   "evaluation_metrics": self._stage(
                       "accuracy", "we report accuracy on the test set", verified=True)},
            "h2": {"method_model": self._stage("SVM"),
                   "evaluation_metrics": self._stage(
                       "accuracy", "accuracy is the only metric", verified=True)},
            "h3": {"method_model": self._stage("random forest"),
                   "evaluation_metrics": self._stage(
                       "accuracy", "invented quote", verified=False)},
        }

    def test_homogeneous_stage_replaces_keyword_check(self, homogeneous_papers):
        ga = GapAnalyzer()
        indicators = ga.analyze_gaps(
            "test topic", homogeneous_papers, depth="quick",
            paper_profiles=self._profiles(self._homogeneous_workflows()))

        assert [i for i in indicators if i.detection_method == "methodology_coverage"] == []
        wf = [i for i in indicators if i.detection_method == "workflow_stage_mining"]
        assert len(wf) == 1
        ind = wf[0]
        assert ind.indicator_type == IndicatorType.INCOMPLETENESS
        assert "unidentified" not in ind.description
        assert "Metrik evaluasi: 3/3 journals rely on 'accuracy'" in ind.description
        # Same formula as the keyword check: 3 journals on one choice -> 0.64.
        assert ind.confidence == pytest.approx(0.64)
        assert sorted(ind.related_papers) == ["h1", "h2", "h3"]
        # Only verified stage quotes are presented as verbatim evidence.
        quotes = [q for q in ind.supporting_quotes if q.get("origin") == "workflow_stage"]
        assert [q["source_paper"] for q in quotes] == ["h1", "h2"]
        assert all(q["stage"] == "evaluation_metrics" for q in quotes)
        matrix = next(s["stage_matrix"] for s in ind.sub_indicators if "stage_matrix" in s)
        assert [h["stage"] for h in matrix["homogeneous"]] == ["evaluation_metrics"]
        assert matrix["verified_quotes"] == 2 and matrix["total_quotes"] == 3
        assert any(e.startswith("Tahap Metrik evaluasi: 1 varian") and "[HOMOGEN]" in e
                   for e in ind.evidence)

    def test_diverse_pipelines_yield_no_methodology_indicator(self, homogeneous_papers):
        workflows = {
            "h1": {"method_model": self._stage("CNN"), "evaluation_metrics": self._stage("accuracy")},
            "h2": {"method_model": self._stage("SVM"), "evaluation_metrics": self._stage("F1-score")},
            "h3": {"method_model": self._stage("random forest"),
                   "evaluation_metrics": self._stage("processing time")},
        }
        ga = GapAnalyzer()
        indicators = ga.analyze_gaps(
            "test topic", homogeneous_papers, depth="quick",
            paper_profiles=self._profiles(workflows))
        # The pipelines are authoritative: no fallback to the keyword guess
        # that would have called these three journals "similar methodology".
        assert [i for i in indicators
                if i.detection_method in ("workflow_stage_mining", "methodology_coverage")] == []

    def test_too_few_pipelines_keep_the_keyword_fallback(self, homogeneous_papers):
        workflows = {k: v for k, v in self._homogeneous_workflows().items() if k != "h3"}
        ga = GapAnalyzer()
        indicators = ga.analyze_gaps(
            "test topic", homogeneous_papers, depth="quick",
            paper_profiles=self._profiles(workflows))
        assert [i for i in indicators if i.detection_method == "workflow_stage_mining"] == []
        meth = [i for i in indicators if i.detection_method == "methodology_coverage"]
        assert len(meth) == 1 and meth[0].confidence == pytest.approx(0.64)

    def test_author_statement_corroborates_the_homogeneous_stage(self, homogeneous_papers):
        from app.core.gap_detection.paper_profiles import build_profiles

        weakness = {
            "title": "h2", "source": "h2", "tersirat": [],
            "tersurat": [{
                "poin": "The evaluation reports accuracy only",
                "dasar": "Other evaluation metrics are absent",
                "kutipan": "accuracy is the only metric",
                "verification_status": "terverifikasi", "confidence": 0.9,
            }],
        }
        profiles = build_profiles(self.PAPER_CONTENTS, weaknesses=[weakness],
                                  workflows=self._homogeneous_workflows())
        ga = GapAnalyzer()
        ind = next(i for i in ga.analyze_gaps(
            "test topic", homogeneous_papers, depth="quick",
            paper_profiles={k: v.to_dict() for k, v in profiles.items()})
            if i.detection_method == "workflow_stage_mining")
        hits = next(s["author_corroboration"] for s in ind.sub_indicators
                    if "author_corroboration" in s)
        assert hits[0]["source"] == "h2" and hits[0]["kind"] == "tersurat"
        origins = {q.get("origin") for q in ind.supporting_quotes}
        assert origins == {"workflow_stage", "author_stated"}
