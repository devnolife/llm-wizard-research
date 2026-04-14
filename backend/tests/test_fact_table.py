"""
Unit tests for FactTable and related data models.

Covers Entity creation, Fact/triple CRUD, SPO queries, confidence filtering,
entity type validation, inferred facts, duplicate detection, and statistics.
"""

import pytest

from app.core.knowledge.fact_table import (
    Entity,
    EntityType,
    Fact,
    FactTable,
    PredicateType,
    Verdict,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ft():
    """Fresh, empty FactTable."""
    return FactTable()


@pytest.fixture
def sample_entities():
    """One entity per EntityType."""
    return [
        Entity("m1", EntityType.METHOD, "CNN"),
        Entity("c1", EntityType.CONCEPT, "Transfer Learning"),
        Entity("d1", EntityType.DOMAIN, "Medical Imaging"),
        Entity("f1", EntityType.FINDING, "92% accuracy"),
        Entity("ds1", EntityType.DATASET, "ImageNet"),
        Entity("mt1", EntityType.METRIC, "F1-score"),
        Entity("p1", EntityType.PAPER, "Smith et al. 2023"),
        Entity("cn1", EntityType.CONSTRAINT, "limited GPU"),
    ]


@pytest.fixture
def populated_ft(ft, sample_entities):
    """FactTable loaded with sample entities and a handful of facts."""
    for e in sample_entities:
        ft.add_entity(e)

    facts = [
        Fact(fact_id="fact1", subject_id="p1", predicate=PredicateType.USES_METHOD,
             object_id="m1", source="Sec.3", source_paper="paper_001", confidence=0.95),
        Fact(fact_id="fact2", subject_id="m1", predicate=PredicateType.APPLIES_TO,
             object_id="d1", source="Sec.4", source_paper="paper_001", confidence=0.88),
        Fact(fact_id="fact3", subject_id="m1", predicate=PredicateType.ACHIEVES,
             object_id="f1", source="Sec.5", source_paper="paper_001", confidence=0.92),
        Fact(fact_id="fact4", subject_id="m1", predicate=PredicateType.EVALUATED_ON,
             object_id="ds1", source="Sec.5", source_paper="paper_001", confidence=0.9),
        Fact(fact_id="fact5", subject_id="m1", predicate=PredicateType.REQUIRES_RESOURCE,
             object_id="cn1", source="Sec.6", source_paper="paper_001", confidence=0.7),
        Fact(fact_id="fact6", subject_id="p1", predicate=PredicateType.DISCUSSES,
             object_id="c1", source="Sec.2", source_paper="paper_001", confidence=0.85),
    ]
    for f in facts:
        ft.add_fact(f)

    return ft


# ---------------------------------------------------------------------------
# Entity tests
# ---------------------------------------------------------------------------

class TestEntityCreation:
    """Test Entity creation with all 8 EntityTypes."""

    @pytest.mark.parametrize("etype", list(EntityType))
    def test_create_entity_for_each_type(self, ft, etype):
        e = Entity(f"test_{etype.value}", etype, f"Name {etype.value}")
        eid = ft.add_entity(e)
        assert eid == e.entity_id
        assert ft.get_entity(eid) is e

    def test_all_eight_entity_types_exist(self):
        assert len(EntityType) == 8

    def test_entity_properties(self):
        e = Entity("x", EntityType.METHOD, "Method X",
                    properties={"lang": "python"}, source_paper="p1")
        assert e.properties["lang"] == "python"
        assert e.source_paper == "p1"

    def test_entity_equality_by_id(self):
        a = Entity("same_id", EntityType.METHOD, "A")
        b = Entity("same_id", EntityType.CONCEPT, "B")
        assert a == b  # equality based on entity_id

    def test_entity_inequality(self):
        a = Entity("id_a", EntityType.METHOD, "A")
        b = Entity("id_b", EntityType.METHOD, "A")
        assert a != b

    def test_entity_hash(self):
        a = Entity("id_a", EntityType.METHOD, "A")
        b = Entity("id_a", EntityType.CONCEPT, "B")
        assert hash(a) == hash(b)

    def test_get_nonexistent_entity(self, ft):
        assert ft.get_entity("nope") is None


class TestFindEntities:
    def test_find_by_type(self, populated_ft):
        methods = populated_ft.find_entities(entity_type=EntityType.METHOD)
        assert len(methods) == 1
        assert methods[0].entity_id == "m1"

    def test_find_by_name_contains(self, populated_ft):
        results = populated_ft.find_entities(name_contains="cnn")
        assert len(results) == 1

    def test_find_by_source_paper(self, ft):
        e = Entity("e1", EntityType.FINDING, "Result", source_paper="px")
        ft.add_entity(e)
        results = ft.find_entities(source_paper="px")
        assert len(results) == 1

    def test_find_no_match(self, populated_ft):
        assert populated_ft.find_entities(name_contains="zzzzz") == []


class TestGetOrCreateEntity:
    def test_creates_new_entity(self, ft):
        e = ft.get_or_create_entity("BERT", EntityType.METHOD)
        assert e.name == "BERT"
        assert e.entity_type == EntityType.METHOD

    def test_returns_existing_entity(self, ft):
        e1 = ft.get_or_create_entity("BERT", EntityType.METHOD)
        e2 = ft.get_or_create_entity("bert", EntityType.METHOD)
        assert e1.entity_id == e2.entity_id  # case-insensitive match

    def test_different_type_creates_new(self, ft):
        e1 = ft.get_or_create_entity("X", EntityType.METHOD)
        e2 = ft.get_or_create_entity("X", EntityType.CONCEPT)
        assert e1.entity_id != e2.entity_id


# ---------------------------------------------------------------------------
# Fact / Triple CRUD
# ---------------------------------------------------------------------------

class TestFactCreation:
    @pytest.mark.parametrize("pred", list(PredicateType))
    def test_create_fact_with_each_predicate(self, ft, pred):
        f = Fact(subject_id="s", predicate=pred, object_id="o", confidence=0.8)
        fid = ft.add_fact(f)
        assert ft.get_fact(fid) is f

    def test_fact_to_dict(self):
        f = Fact(fact_id="x1", subject_id="s", predicate=PredicateType.USES_METHOD,
                 object_id="o", confidence=0.9, is_inferred=True, inferred_by_rule="F1")
        d = f.to_dict()
        assert d["fact_id"] == "x1"
        assert d["predicate"] == "USES_METHOD"
        assert d["is_inferred"] is True
        assert d["inferred_by_rule"] == "F1"

    def test_remove_fact(self, populated_ft):
        assert populated_ft.get_fact("fact1") is not None
        assert populated_ft.remove_fact("fact1") is True
        assert populated_ft.get_fact("fact1") is None

    def test_remove_nonexistent_fact(self, ft):
        assert ft.remove_fact("nope") is False

    def test_get_nonexistent_fact(self, ft):
        assert ft.get_fact("nope") is None


# ---------------------------------------------------------------------------
# SPO Query
# ---------------------------------------------------------------------------

class TestSPOQuery:
    def test_query_by_subject(self, populated_ft):
        results = populated_ft.query(subject_id="m1")
        assert len(results) == 4  # APPLIES_TO, ACHIEVES, EVALUATED_ON, REQUIRES_RESOURCE

    def test_query_by_predicate(self, populated_ft):
        results = populated_ft.query(predicate=PredicateType.USES_METHOD)
        assert len(results) == 1
        assert results[0].subject_id == "p1"

    def test_query_by_object(self, populated_ft):
        results = populated_ft.query(object_id="d1")
        assert len(results) == 1
        assert results[0].predicate == PredicateType.APPLIES_TO

    def test_query_by_subject_and_predicate(self, populated_ft):
        results = populated_ft.query(
            subject_id="m1", predicate=PredicateType.ACHIEVES
        )
        assert len(results) == 1
        assert results[0].object_id == "f1"

    def test_query_by_source_paper(self, populated_ft):
        results = populated_ft.query(source_paper="paper_001")
        assert len(results) == 6

    def test_query_no_filters_returns_all(self, populated_ft):
        results = populated_ft.query()
        assert len(results) == 6

    def test_query_no_match(self, populated_ft):
        results = populated_ft.query(subject_id="nonexistent")
        assert results == []

    def test_query_triples(self, populated_ft):
        triples = populated_ft.query_triples(subject_id="p1")
        assert len(triples) == 2
        # Each triple is (subject, predicate_value, object)
        for s, p, o in triples:
            assert s == "p1"


# ---------------------------------------------------------------------------
# Confidence threshold filtering
# ---------------------------------------------------------------------------

class TestConfidenceFiltering:
    def test_min_confidence_filters(self, populated_ft):
        all_facts = populated_ft.query()
        high_conf = populated_ft.query(min_confidence=0.9)
        assert len(high_conf) < len(all_facts)
        for f in high_conf:
            assert f.confidence >= 0.9

    def test_min_confidence_zero_returns_all(self, populated_ft):
        assert len(populated_ft.query(min_confidence=0.0)) == 6

    def test_min_confidence_one_returns_few(self, populated_ft):
        results = populated_ft.query(min_confidence=1.0)
        # No fact has confidence=1.0 in our fixture
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Inferred facts
# ---------------------------------------------------------------------------

class TestInferredFacts:
    def test_inferred_fact_creation(self, ft):
        f = Fact(
            fact_id="inf1",
            subject_id="m1",
            predicate=PredicateType.INFEASIBLE_FOR,
            object_id="d1",
            confidence=0.7,
            is_inferred=True,
            inferred_by_rule="F1",
        )
        ft.add_fact(f)
        retrieved = ft.get_fact("inf1")
        assert retrieved.is_inferred is True
        assert retrieved.inferred_by_rule == "F1"

    def test_include_inferred_false_filters(self, ft):
        ft.add_fact(Fact(fact_id="norm", subject_id="a", predicate=PredicateType.USES_METHOD,
                         object_id="b", confidence=0.9, is_inferred=False))
        ft.add_fact(Fact(fact_id="inf", subject_id="a", predicate=PredicateType.INFEASIBLE_FOR,
                         object_id="b", confidence=0.7, is_inferred=True))

        with_inferred = ft.query(include_inferred=True)
        without_inferred = ft.query(include_inferred=False)
        assert len(with_inferred) == 2
        assert len(without_inferred) == 1
        assert without_inferred[0].fact_id == "norm"

    def test_statistics_count_inferred(self, ft):
        ft.add_fact(Fact(fact_id="a", subject_id="s", predicate=PredicateType.DISCUSSES,
                         object_id="o", is_inferred=False))
        ft.add_fact(Fact(fact_id="b", subject_id="s", predicate=PredicateType.INFEASIBLE_FOR,
                         object_id="o", is_inferred=True))
        stats = ft.get_statistics()
        assert stats["total_inferred_facts"] == 1
        assert stats["total_facts"] == 2


# ---------------------------------------------------------------------------
# Duplicate detection (get_or_create_entity)
# ---------------------------------------------------------------------------

class TestDuplicateDetection:
    def test_duplicate_entity_detected(self, ft):
        e1 = ft.get_or_create_entity("CNN", EntityType.METHOD)
        e2 = ft.get_or_create_entity("cnn", EntityType.METHOD)
        assert e1.entity_id == e2.entity_id
        assert len(ft.find_entities(entity_type=EntityType.METHOD)) == 1

    def test_same_name_different_type_not_duplicate(self, ft):
        e1 = ft.get_or_create_entity("CNN", EntityType.METHOD)
        e2 = ft.get_or_create_entity("CNN", EntityType.CONCEPT)
        assert e1.entity_id != e2.entity_id


# ---------------------------------------------------------------------------
# Contradiction detection
# ---------------------------------------------------------------------------

class TestContradictionDetection:
    def test_find_contradictions(self, ft):
        ft.add_fact(Fact(fact_id="fa", subject_id="f_a", predicate=PredicateType.ACHIEVES,
                         object_id="result_a", confidence=0.9))
        ft.add_fact(Fact(fact_id="fb", subject_id="f_b", predicate=PredicateType.ACHIEVES,
                         object_id="result_b", confidence=0.9))
        ft.add_fact(Fact(fact_id="contra", subject_id="f_a",
                         predicate=PredicateType.CONTRADICTS, object_id="f_b", confidence=0.85))

        pairs = ft.find_contradictions()
        assert len(pairs) == 1
        a_fact, b_fact = pairs[0]
        assert a_fact.subject_id == "f_a"
        assert b_fact.subject_id == "f_b"

    def test_no_contradictions(self, populated_ft):
        # populated_ft may or may not have CONTRADICTS; count actual
        contras = populated_ft.query(predicate=PredicateType.CONTRADICTS)
        pairs = populated_ft.find_contradictions()
        # If no CONTRADICTS predicate facts, pairs should be empty
        if not contras:
            assert pairs == []


# ---------------------------------------------------------------------------
# Bulk operations & statistics
# ---------------------------------------------------------------------------

class TestBulkAndStats:
    def test_add_facts_bulk(self, ft):
        facts = [
            Fact(fact_id=f"bf{i}", subject_id="s", predicate=PredicateType.DISCUSSES,
                 object_id=f"o{i}", confidence=0.8)
            for i in range(5)
        ]
        count = ft.add_facts_bulk(facts)
        assert count == 5
        assert len(ft.query()) == 5

    def test_clear(self, populated_ft):
        populated_ft.clear()
        assert len(populated_ft.query()) == 0
        assert populated_ft.get_entity("m1") is None

    def test_get_statistics(self, populated_ft):
        stats = populated_ft.get_statistics()
        assert stats["total_entities"] == 8
        assert stats["total_facts"] == 6
        assert stats["papers_indexed"] == 1
        assert "USES_METHOD" in stats["facts_by_predicate"]

    def test_get_all_facts_as_dicts(self, populated_ft):
        dicts = populated_ft.get_all_facts_as_dicts()
        assert len(dicts) == 6
        assert all(isinstance(d, dict) for d in dicts)

    def test_get_facts_for_paper(self, populated_ft):
        results = populated_ft.get_facts_for_paper("paper_001")
        assert len(results) == 6

    def test_repr(self, populated_ft):
        r = repr(populated_ft)
        assert "entities=8" in r
        assert "facts=6" in r


# ---------------------------------------------------------------------------
# Verdict enum
# ---------------------------------------------------------------------------

class TestVerdictEnum:
    def test_verdict_values(self):
        assert Verdict.PASS.value == "PASS"
        assert Verdict.FLAG.value == "FLAG"
        assert Verdict.REJECT.value == "REJECT"
