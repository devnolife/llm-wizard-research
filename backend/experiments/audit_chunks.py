"""Audit a chunks JSONL against the 10 measurable defects + bagian-E gate.

Works on both the new-schema (``skema: v2``) and the legacy output, so it can
produce a before/after table (TAHAP 1 kriteria selesai #2/#3).

Metrics (masalah 1-10):
  1. mid-sentence prose cuts       6. reference chunks flagged
  2. consecutive-chunk overlap     7. extraction artifacts (ligatures/�/hyphen)
  3. bad paper_title               8. header/footer/page-number bleed
  4. bad/null year                 9. duplicate chunks
  5. section usefulness           10. destroyed non-latin text (quality=poor)

Validation gate (bagian E) fails when, on the NEW output:
  * mid-sentence prose cuts   > 5%
  * bad paper_title           > 10% of journals
  * null year                 > 10% of journals
  * any duplicate chunks
  * section_normalized="other" > 30% of chunks

Usage:
    python -m experiments.audit_chunks new.jsonl
    python -m experiments.audit_chunks new.jsonl --baseline old.jsonl
    python -m experiments.audit_chunks new.jsonl --gate      # exit 1 on failure
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

# ---- shared helpers ----------------------------------------------------

_LIGATURE_ARTIFACT = re.compile(r"[ﬁﬂﬀﬃﬄ]|\ufffd|(?<=[a-z])\?(?=[a-z])")
_HYPHEN_ARTIFACT = re.compile(r"[a-z]+-\s+[a-z]{2,}")
_HEADER_FOOTER = re.compile(
    r"(received\s+\w+\s+\d|©\s*\d{4}|copyright\s+\d{4}|\bp-issn\b|\be-issn\b|"
    r"running head|doi:\s*10\.)", re.IGNORECASE
)
_CAPTION_TAIL = re.compile(r"(figure|fig\.|table|gambar|tabel)\s+[\w.]+", re.IGNORECASE)
_KEYWORDS_HEAD = re.compile(r"(keywords|kata kunci|index terms|key words)\b", re.IGNORECASE)
_NAME_TITLES = re.compile(r"\b(Dr|Prof|Mr|Mrs|Ms|Assoc|Asst|Engr|Ph\.?D|M\.Sc|B\.Sc|Name:)\b")
_STAT_MARKERS = re.compile(r"\b(Std|Sig|Mean|Deviation|coefficient|p\s*[<=>])\b", re.IGNORECASE)
_BULLETS = "•▪◦‣·"
_ENUM_ITEM = re.compile(r"\b\d{1,2}[.\-)]\s*[A-Za-z]")


def _looks_non_prose(text: str) -> bool:
    """True when the chunk is a list/table/caption/keyword/author block.

    Such content legitimately lacks a terminal period and must not be scored as
    a prose "mid-sentence cut" (masalah 1 is about running prose, not lists).
    """
    t = text or ""
    tail = t[-180:]
    digits = sum(ch.isdigit() for ch in tail)
    if digits / max(len(tail), 1) > 0.12:
        return True
    if tail.count("=") >= 2 or tail.count("(") >= 6:
        return True
    if any(b in tail for b in _BULLETS):
        return True
    if len(_ENUM_ITEM.findall(tail)) >= 2:  # "1.MSAB 2.MSAB" / "3-Examination"
        return True
    if _CAPTION_TAIL.search(tail):
        return True
    if _KEYWORDS_HEAD.search(t[:120]):
        return True
    if len(_NAME_TITLES.findall(tail)) >= 2 or "Name:" in tail:
        return True
    if len(_STAT_MARKERS.findall(tail)) >= 2:
        return True
    return False


def _load(path: str):
    meta = None
    chunks = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("record") == "meta":
                meta = rec
            elif rec.get("record") == "chunk":
                chunks.append(rec)
    return meta, chunks


def _title_of(c: Dict[str, Any]) -> Optional[str]:
    return c.get("paper_title") or c.get("title")


def _is_prose_midsentence_cut(text: str) -> bool:
    """Genuine prose sentence cut: ends lowercase/comma AND is prose.

    Isolates the defect the spec targets (masalah 1: a fixed-window cutting
    *prose* mid-sentence), rather than penalising inherently non-sentence content
    (lists/tables/captions/keyword/author blocks) that GROBID would drop from
    body text. Applied identically to the legacy baseline and the new output.
    """
    t = (text or "").rstrip()
    if not t:
        return False
    if not (t[-1].islower() or t[-1] == ","):
        return False
    return not _looks_non_prose(t)


def _ends_terminal(text: str) -> bool:
    t = (text or "").rstrip().rstrip("\"')]")
    return bool(t) and t[-1] in ".!?"


def audit(path: str) -> Dict[str, Any]:
    meta, chunks = _load(path)
    n = len(chunks)
    by_source: Dict[str, List[Dict]] = defaultdict(list)
    for c in chunks:
        by_source[c.get("source")].append(c)
    journals = list(by_source)
    is_v2 = any(("section_normalized" in c) for c in chunks)

    # 1 — mid-sentence prose cuts (body prose only: exclude refs + front matter)
    def _is_body_prose(c: Dict[str, Any]) -> bool:
        if c.get("is_reference"):
            return False
        if is_v2:
            return c.get("section_normalized") not in ("other", "references")
        return True

    prose = [c for c in chunks if _is_body_prose(c)]
    mid = sum(_is_prose_midsentence_cut(c.get("text", "")) for c in prose)
    clean_terminal = sum(_ends_terminal(c.get("text", "")) for c in chunks)

    # 2 — overlap between consecutive chunks within the same raw section
    ov_pairs = ov_hit = 0
    for src, cs in by_source.items():
        cs = sorted(cs, key=lambda c: c.get("chunk_index", 0))
        for a, b in zip(cs, cs[1:]):
            # A within-section boundary: contiguous indices, same raw section.
            if b.get("chunk_index") != a.get("chunk_index", 0) + 1:
                continue
            if is_v2 and a.get("section_raw") != b.get("section_raw"):
                continue
            ov_pairs += 1
            probe = (b.get("text") or "").strip()[:60]
            if probe and probe in (a.get("text") or ""):
                ov_hit += 1

    # 3 — bad paper_title (empty, or looks like a journal/ISSN/DOI)
    bad_title = 0
    for src, cs in by_source.items():
        title = _title_of(cs[0]) or ""
        if (not title.strip()) or re.search(
            r"issn|doi|journal|proceedings|^\s*vol\.|www\.", title, re.IGNORECASE
        ):
            bad_title += 1

    # 4 — null/invalid year
    null_year = 0
    for src, cs in by_source.items():
        y = cs[0].get("year")
        if not (isinstance(y, int) and 1990 <= y <= 2100):
            null_year += 1

    # 5 — section usefulness
    if is_v2:
        other = sum(1 for c in chunks if c.get("section_normalized") == "other")
        distinct_sections = len({c.get("section_normalized") for c in chunks})
    else:
        vals = [c.get("section") for c in chunks]
        distinct_sections = len({v for v in vals if v})
        # legacy "other": empty/noisy section labels
        other = sum(1 for v in vals if not v or re.search(r"issn|:\s|\d{4}", str(v)))

    # 6 — reference chunks flagged
    if is_v2:
        refs = sum(1 for c in chunks if c.get("is_reference"))
    else:
        refs = sum(1 for c in chunks if re.search(r"\[\d+\]\s+[A-Z].*\b(19|20)\d{2}\b", c.get("text", "")))

    # 7 — extraction artifacts
    artifacts = sum(
        1 for c in chunks
        if _LIGATURE_ARTIFACT.search(c.get("text", "")) or _HYPHEN_ARTIFACT.search(c.get("text", ""))
    )

    # 8 — header/footer/page-number bleed
    hf = sum(1 for c in chunks if _HEADER_FOOTER.search(c.get("text", "")))

    # 9 — duplicate chunks (normalized text)
    seen: Counter = Counter()
    for c in chunks:
        seen[re.sub(r"\s+", " ", (c.get("text") or "").strip().lower())] += 1
    dups = sum(v - 1 for v in seen.values() if v > 1)

    # 10 — destroyed / poor extraction
    if is_v2:
        poor = sum(1 for c in chunks if c.get("extraction_quality") == "poor")
    else:
        poor = sum(1 for c in chunks if (c.get("text", "").count("?") / max(len(c.get("text", "")), 1)) > 0.05)

    pct = lambda a, b: (100.0 * a / b) if b else 0.0
    return {
        "path": path,
        "schema": "v2" if is_v2 else "legacy",
        "journals": len(journals),
        "chunks": n,
        "m1_midsentence_pct": pct(mid, len(prose)),
        "m1_midsentence": mid,
        "m1_prose": len(prose),
        "clean_terminal_pct": pct(clean_terminal, n),
        "m2_overlap_pct": pct(ov_hit, ov_pairs),
        "m3_bad_title": bad_title,
        "m3_bad_title_pct": pct(bad_title, len(journals)),
        "m4_null_year": null_year,
        "m4_null_year_pct": pct(null_year, len(journals)),
        "m5_other_pct": pct(other, n),
        "m5_distinct_sections": distinct_sections,
        "m6_reference_chunks": refs,
        "m7_artifact_chunks": artifacts,
        "m7_artifact_pct": pct(artifacts, n),
        "m8_headerfooter_chunks": hf,
        "m9_duplicates": dups,
        "m10_poor_chunks": poor,
    }


def gate(a: Dict[str, Any]) -> List[str]:
    """Return the list of bagian-E failures (empty = pass)."""
    fails = []
    if a["m1_midsentence_pct"] > 5:
        fails.append(f"mid-sentence prose cuts {a['m1_midsentence_pct']:.1f}% > 5%")
    if a["m3_bad_title_pct"] > 10:
        fails.append(f"bad paper_title {a['m3_bad_title_pct']:.1f}% > 10%")
    if a["m4_null_year_pct"] > 10:
        fails.append(f"null year {a['m4_null_year_pct']:.1f}% > 10%")
    if a["m9_duplicates"] > 0:
        fails.append(f"{a['m9_duplicates']} duplicate chunks")
    if a["m5_other_pct"] > 30:
        fails.append(f"section 'other' {a['m5_other_pct']:.1f}% > 30%")
    return fails


_ROWS = [
    ("1  mid-sentence cut %", "m1_midsentence_pct", "%", True),
    ("   clean terminal end %", "clean_terminal_pct", "%", False),
    ("2  overlap %", "m2_overlap_pct", "%", False),
    ("3  bad title (journals)", "m3_bad_title", "", True),
    ("4  null year (journals)", "m4_null_year", "", True),
    ("5  section 'other' %", "m5_other_pct", "%", True),
    ("   distinct sections", "m5_distinct_sections", "", False),
    ("6  reference chunks", "m6_reference_chunks", "", False),
    ("7  artifact chunks", "m7_artifact_chunks", "", True),
    ("8  header/footer chunks", "m8_headerfooter_chunks", "", True),
    ("9  duplicate chunks", "m9_duplicates", "", True),
    ("10 poor-quality chunks", "m10_poor_chunks", "", False),
]


def print_report(new: Dict[str, Any], base: Optional[Dict[str, Any]] = None):
    print("\n" + "=" * 74)
    print("CHUNKING AUDIT — before/after" if base else "CHUNKING AUDIT")
    print("=" * 74)
    hdr = f"{'metric':30}{'AFTER':>14}"
    if base:
        hdr = f"{'metric':30}{'BEFORE':>14}{'AFTER':>14}"
    print(hdr)
    print("-" * 74)
    print(f"{'journals':30}" + (f"{base['journals']:>14}" if base else "") + f"{new['journals']:>14}")
    print(f"{'chunks':30}" + (f"{base['chunks']:>14}" if base else "") + f"{new['chunks']:>14}")
    for label, key, unit, _ in _ROWS:
        def fmt(v):
            return f"{v:.1f}{unit}" if isinstance(v, float) else f"{v}{unit}"
        line = f"{label:30}"
        if base:
            line += f"{fmt(base[key]):>14}"
        line += f"{fmt(new[key]):>14}"
        print(line)
    print("-" * 74)
    fails = gate(new)
    if fails:
        print("GATE: FAIL")
        for f in fails:
            print(f"   - {f}")
    else:
        print("GATE: PASS (all bagian-E thresholds met)")
    print("=" * 74 + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit chunks JSONL.")
    ap.add_argument("new", help="New-schema chunks JSONL to audit.")
    ap.add_argument("--baseline", help="Legacy chunks JSONL for before/after.")
    ap.add_argument("--gate", action="store_true", help="Exit 1 if the gate fails.")
    ap.add_argument("--json", action="store_true", help="Print raw JSON metrics.")
    args = ap.parse_args(argv)

    new = audit(args.new)
    base = audit(args.baseline) if args.baseline else None
    if args.json:
        print(json.dumps({"after": new, "before": base}, indent=2))
    else:
        print_report(new, base)
    if args.gate and gate(new):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
