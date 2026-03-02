"""
Validation module - Rule Engine and Relation Classifier

Implements the Neuro-Symbolic validation layer:
- Rule Engine: 9 rules (F1-F3, C1-C3, K1-K3) with PASS/FLAG/REJECT verdicts
- Relation Classifier: 3-layer semantic→evidence→rule-based validation

Reference: revisi.md Sections 6 and 7
"""

from .rule_engine import RuleEngine, Rule, RuleCategory, RuleResult, ValidationReport
from .relation_classifier import RelationClassifier, RelationType, ClassifiedRelation

__all__ = [
    "RuleEngine",
    "Rule",
    "RuleCategory",
    "RuleResult",
    "ValidationReport",
    "RelationClassifier",
    "RelationType",
    "ClassifiedRelation",
]
