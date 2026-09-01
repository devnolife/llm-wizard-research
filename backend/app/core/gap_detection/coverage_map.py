"""
Evidence Gap Map / coverage matrix (LeapSpace P8).

The P8 review describes the standard construction precisely:

    Rows:        interventions, domains, settings, or categories
    Columns:     outcomes or question dimensions
    Cell values: typically counts or percentages, NOT weighted evidence scores
    Mapping:     many-to-many (one study can occupy several cells)

It is equally explicit about what the literature does *not* provide:

    "What the literature largely does not provide is a prespecified rule like
     'a cell is a significant gap if study count < k and quality < q'."

So this module deliberately stops short of emitting a single gap score per
cell. It produces a human-readable matrix, marks empty and thin cells as
*candidates*, and ranks those candidates only by an explicit, inspectable
importance overlay — never by a fabricated threshold.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .semantic_match import SemanticMatcher

# A cell holding fewer studies than this is "thin" rather than empty. This is a
# presentation band, not a gap rule — see the module docstring.
THIN_CELL_MAX = 2

# Row/column axis vocabularies used when the extraction stage supplies nothing
# structured. Kept small and generic so the matrix stays readable.
_DEFAULT_ROW_TERMS = (
    "healthcare", "education", "industry", "finance", "transportation",
    "agriculture", "security", "manufacturing", "public sector",
    "laboratory", "field deployment", "simulation environment",
)
_DEFAULT_COLUMN_TERMS = (
    "accuracy", "effectiveness", "efficiency", "scalability", "usability",
    "reliability", "cost", "privacy", "security", "equity", "accessibility",
    "sustainability", "reproducibility", "generalizability",
)


@dataclass
class CoverageCell:
    """One row x column intersection of the evidence gap map."""

    row: str
    column: str
    study_count: int = 0
    papers: List[str] = field(default_factory=list)
    important: bool = False

    @property
    def status(self) -> str:
        if self.study_count == 0:
            return "empty"
        if self.study_count <= THIN_CELL_MAX:
            return "thin"
        return "covered"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row": self.row,
            "column": self.column,
            "study_count": self.study_count,
            "papers": self.papers[:8],
            "status": self.status,
            "important": self.important,
        }


@dataclass
class CoverageMatrix:
    """Evidence gap map with counts, never weighted scores."""

    rows: List[str]
    columns: List[str]
    cells: Dict[Tuple[str, str], CoverageCell]
    total_papers: int = 0
    unmapped_papers: List[str] = field(default_factory=list)

    def cell(self, row: str, column: str) -> CoverageCell:
        return self.cells.get((row, column), CoverageCell(row=row, column=column))

    @property
    def empty_cells(self) -> List[CoverageCell]:
        return [c for c in self.cells.values() if c.status == "empty"]

    @property
    def thin_cells(self) -> List[CoverageCell]:
        return [c for c in self.cells.values() if c.status == "thin"]

    @property
    def density(self) -> float:
        """Fraction of cells holding at least one study."""
        if not self.cells:
            return 0.0
        covered = sum(1 for c in self.cells.values() if c.study_count > 0)
        return round(covered / len(self.cells), 3)

    def candidate_gaps(self, limit: int = 12) -> List[CoverageCell]:
        """Empty/thin cells ranked by the importance overlay.

        These are *candidates*, not gaps: the report is explicit that no
        prespecified count/quality rule is established in the literature, so
        the final judgement is left to the reviewer.
        """
        candidates = self.empty_cells + self.thin_cells
        candidates.sort(key=lambda c: (not c.important, c.study_count, c.row, c.column))
        return candidates[:limit]

    def to_grid(self) -> List[Dict[str, Any]]:
        """Row-major grid suitable for rendering as a table."""
        return [
            {
                "row": row,
                **{column: self.cell(row, column).study_count for column in self.columns},
            }
            for row in self.rows
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rows": list(self.rows),
            "columns": list(self.columns),
            "grid": self.to_grid(),
            "density": self.density,
            "total_papers": self.total_papers,
            "unmapped_papers": self.unmapped_papers[:10],
            "empty_cells": len(self.empty_cells),
            "thin_cells": len(self.thin_cells),
            "candidate_gaps": [c.to_dict() for c in self.candidate_gaps()],
            "note": (
                "Cells hold study counts, not weighted evidence scores. "
                "Empty cells are gap CANDIDATES: the literature establishes no "
                "prespecified rule such as 'count < k and quality < q'."
            ),
        }


def _axis_values(
    paper: Dict[str, Any], keys: Sequence[str]
) -> List[str]:
    """Read a structured axis value from a paper, if the extractor supplied one."""
    meta = paper.get("metadata") or {}
    values: List[str] = []
    for holder in (paper, meta):
        for key in keys:
            raw = holder.get(key)
            if isinstance(raw, (list, tuple, set)):
                values.extend(str(x).strip() for x in raw if str(x).strip())
            elif raw and str(raw).strip():
                values.append(str(raw).strip())
    seen: Set[str] = set()
    unique: List[str] = []
    for value in values:
        low = value.lower()
        if low not in seen:
            seen.add(low)
            unique.append(value)
    return unique


def _terms_present(text: str, terms: Sequence[str]) -> List[str]:
    low = text.lower()
    return [t for t in terms if t in low]


def build_coverage_matrix(
    papers: Sequence[Dict[str, Any]],
    row_terms: Optional[Sequence[str]] = None,
    column_terms: Optional[Sequence[str]] = None,
    important_columns: Optional[Iterable[str]] = None,
    paper_ref=None,
    matcher: Optional[SemanticMatcher] = None,
) -> CoverageMatrix:
    """Construct the evidence gap map from the analyzed corpus.

    Axis values are taken from structured extraction fields when present
    (`domain`, `setting`, `population`, `intervention` for rows; `outcome`,
    `metric` for columns) and fall back to vocabulary matching over the paper
    text otherwise, so legacy jobs still produce a usable matrix.

    A single paper may occupy several cells — the mapping is many-to-many, as
    the report prescribes.
    """
    paper_ref = paper_ref or (
        lambda p: (p.get("source") or (p.get("metadata") or {}).get("title") or p.get("doc_id") or "")
    )
    row_terms = list(row_terms or _DEFAULT_ROW_TERMS)
    column_terms = list(column_terms or _DEFAULT_COLUMN_TERMS)
    important = {c.lower() for c in (important_columns or [])}

    row_hits: Dict[str, Set[str]] = {}
    column_hits: Dict[str, Set[str]] = {}
    pair_hits: Dict[Tuple[str, str], List[str]] = {}
    unmapped: List[str] = []

    for paper in papers:
        ref = paper_ref(paper) or "(unnamed)"
        text = paper.get("content", "") or ""

        rows = _axis_values(paper, ("domain", "setting", "population", "intervention"))
        if not rows:
            rows = _terms_present(text, row_terms)
        columns = _axis_values(paper, ("outcome", "metric", "outcomes"))
        if not columns:
            columns = _terms_present(text, column_terms)

        if not rows or not columns:
            unmapped.append(ref)
            continue

        for row in rows:
            row_hits.setdefault(row, set()).add(ref)
        for column in columns:
            column_hits.setdefault(column, set()).add(ref)
        # Many-to-many: every row x column combination this paper covers.
        for row in rows:
            for column in columns:
                pair_hits.setdefault((row, column), []).append(ref)

    rows_sorted = sorted(row_hits, key=lambda r: (-len(row_hits[r]), r))
    columns_sorted = sorted(column_hits, key=lambda c: (-len(column_hits[c]), c))

    cells: Dict[Tuple[str, str], CoverageCell] = {}
    for row in rows_sorted:
        for column in columns_sorted:
            refs = pair_hits.get((row, column), [])
            cells[(row, column)] = CoverageCell(
                row=row,
                column=column,
                study_count=len(set(refs)),
                papers=sorted(set(refs)),
                important=column.lower() in important,
            )

    return CoverageMatrix(
        rows=rows_sorted,
        columns=columns_sorted,
        cells=cells,
        total_papers=len(papers),
        unmapped_papers=unmapped,
    )


def mark_important_columns(
    matrix: CoverageMatrix,
    critical_aspects: Sequence[str],
    matcher: Optional[SemanticMatcher] = None,
) -> CoverageMatrix:
    """Overlay decision-relevance onto the matrix columns.

    A cell is only promoted as a *significant* candidate when its column is
    one the reviewer (or the expected-aspect step) flagged as critical. This is
    the explicit, inspectable substitute for the count/quality threshold the
    literature does not provide.
    """
    if not critical_aspects:
        return matrix
    matcher = matcher or SemanticMatcher()
    important_columns: Set[str] = set()
    for column in matrix.columns:
        match = matcher.best_match(column, list(critical_aspects))
        if match.covered:
            important_columns.add(column)
    for cell in matrix.cells.values():
        cell.important = cell.column in important_columns
    return matrix
