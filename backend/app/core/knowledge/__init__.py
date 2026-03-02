"""
Knowledge module - Fact Table and Fact Extraction

Implements the SPO (Subject-Predicate-Object) triple system
for structured knowledge representation from research papers.

Reference: revisi.md Section 9 - Skema Fakta Knowledge Graph (Tabel SPO)
"""

from .fact_table import (
    EntityType,
    PredicateType,
    Entity,
    Fact,
    FactTable,
    Verdict,
)
from .fact_extractor import FactExtractor

__all__ = [
    "EntityType",
    "PredicateType",
    "Entity",
    "Fact",
    "FactTable",
    "FactExtractor",
    "Verdict",
]
