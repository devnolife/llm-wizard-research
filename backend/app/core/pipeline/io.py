"""Shared JSONL/JSON writers for pipeline artifacts (chunks + gaps).

Kept separate from the FastAPI export so the CLI and the API produce byte-for-byte
the same new-schema records.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .schema import PipelineChunk


def write_chunks_jsonl(
    path: str,
    results: List[Any],
    job_id: str,
    note: str = "Teks verbatim hasil ekstraksi PDF, belum diringkas LLM.",
) -> Dict[str, Any]:
    """Write a ``chunks_*.jsonl`` file (meta line + one line per chunk).

    ``results`` is any list of objects exposing ``.meta`` (PaperMeta) and
    ``.chunks`` (List[PipelineChunk]). Returns a small summary dict.
    """
    all_chunks: List[PipelineChunk] = []
    for res in results:
        all_chunks.extend(res.chunks)

    meta_line = {
        "record": "meta",
        "job_id": job_id,
        "diekspor_pada": datetime.now().isoformat(timespec="seconds"),
        "jumlah_jurnal": len(results),
        "jumlah_chunk": len(all_chunks),
        "skema": "v2",
        "catatan": note,
    }

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(meta_line, ensure_ascii=False) + "\n")
        for chunk in all_chunks:
            fh.write(json.dumps(chunk.to_json_record(), ensure_ascii=False) + "\n")

    return {"jurnal": len(results), "chunk": len(all_chunks), "path": str(out)}


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    """Read a JSONL file into a list of dicts (skips blank lines)."""
    records = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(path: str, records: Iterable[Dict[str, Any]]) -> int:
    """Write an iterable of dicts to JSONL; returns the count written."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n
