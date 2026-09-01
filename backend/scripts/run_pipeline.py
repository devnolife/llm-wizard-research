"""CLI: run the upgraded pipeline over a folder of PDFs -> chunks_<jobid>.jsonl.

Usage (from the ``backend`` directory):

    python -m scripts.run_pipeline --input ../data/raw/analysis_jobs/<jobid> \
        --out ../data/processed/chunks_<n>jurnal_<jobid>.jsonl

    # legacy baseline (old DocumentProcessor char-window chunking) for before/after:
    python -m scripts.run_pipeline --input <dir> --out old.jsonl --legacy

This is the reproducible "re-run on the same 35 PDFs" entry point (TAHAP 1
kriteria selesai #1). It shares the core pipeline with the FastAPI ingestion.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from loguru import logger

from dotenv import load_dotenv

load_dotenv()  # pick up CROSSREF_EMAIL / GROBID_URL etc. for the CLI process

from app.core.pipeline.corpus_relevance import build_probe, check_corpus_relevance
from app.core.pipeline.io import write_chunks_jsonl, write_jsonl
from app.core.pipeline.pipeline import process_pdf


def _source_name(pdf_path: Path) -> str:
    """Inputs are stored as ``{index}_{original-name}`` in job dirs."""
    return pdf_path.name.split("_", 1)[-1] if "_" in pdf_path.name else pdf_path.name


def _load_embedder():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", device="cpu"
        )
    except Exception:
        return None


def _report_relevance(results):
    """Warn about journals that do not belong to the same research area."""
    probes = {
        r.meta.source: build_probe(
            r.meta.paper_title,
            [{"text": c.text, "is_reference": c.is_reference,
              "chunk_index": c.chunk_index} for c in r.chunks],
        )
        for r in results
    }
    reports = check_corpus_relevance(probes, embedder=_load_embedder())
    flagged = [rep for rep in reports if rep.flagged]
    if not flagged:
        logger.info(f"Corpus coherence OK: {len(reports)} journals, none flagged")
        return
    logger.warning(
        f"{len(flagged)}/{len(reports)} journal(s) look unrelated to this batch "
        f"(review manually — this is a warning, not a rejection):"
    )
    for rep in flagged:
        logger.warning(f"   {rep.score:.3f}  {rep.source}  (terdekat: {rep.nearest})")


def _run_new(pdfs, out_path: str, job_id: str):
    results = []
    t0 = time.time()
    for i, pdf in enumerate(pdfs, 1):
        src = _source_name(pdf)
        logger.info(f"[{i}/{len(pdfs)}] {src}")
        try:
            results.append(process_pdf(str(pdf), source=src))
        except Exception as e:
            logger.error(f"Failed on {src}: {e}")
    summary = write_chunks_jsonl(out_path, results, job_id=job_id)
    logger.info(
        f"Wrote {summary['chunk']} chunks from {summary['jurnal']} journals "
        f"to {summary['path']} in {time.time() - t0:.1f}s"
    )
    if len(results) > 1:
        _report_relevance(results)
    return summary


def _run_legacy(pdfs, out_path: str, job_id: str):
    """Baseline using the legacy DocumentProcessor (char-window chunking)."""
    from app.utils.document_processor import DocumentProcessor

    dp = DocumentProcessor(chunk_size=512, chunk_overlap=50, chunk_strategy="sections")
    records = [{
        "record": "meta", "job_id": job_id, "skema": "legacy",
        "catatan": "Baseline: DocumentProcessor lama (fixed-window).",
    }]
    n_chunks = 0
    for i, pdf in enumerate(pdfs, 1):
        src = _source_name(pdf)
        logger.info(f"[legacy {i}/{len(pdfs)}] {src}")
        try:
            doc = dp.process_pdf(str(pdf))
        except Exception as e:
            logger.error(f"Legacy failed on {src}: {e}")
            continue
        for c in doc.chunks:
            m = c.metadata or {}
            records.append({
                "record": "chunk", "source": src,
                "title": doc.title, "year": doc.metadata.get("year"),
                "section": m.get("section"), "chunk_index": c.chunk_index,
                "chars": len(c.content or ""), "text": c.content,
            })
            n_chunks += 1
    write_jsonl(out_path, records)
    logger.info(f"Wrote {n_chunks} legacy chunks to {out_path}")
    return {"chunk": n_chunks, "path": out_path}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the upgraded chunking pipeline.")
    ap.add_argument("--input", required=True, help="Directory of PDFs.")
    ap.add_argument("--out", required=True, help="Output JSONL path.")
    ap.add_argument("--job-id", default=None, help="Job id (default: input dir name).")
    ap.add_argument("--legacy", action="store_true",
                    help="Produce a legacy-format baseline instead of the new schema.")
    ap.add_argument("--limit", type=int, default=0, help="Process only the first N PDFs.")
    args = ap.parse_args(argv)

    input_dir = Path(args.input)
    if not input_dir.is_dir():
        logger.error(f"Not a directory: {input_dir}")
        return 2
    pdfs = sorted(input_dir.glob("*.pdf"))
    if args.limit:
        pdfs = pdfs[: args.limit]
    if not pdfs:
        logger.error(f"No PDFs in {input_dir}")
        return 2
    job_id = args.job_id or input_dir.name

    if args.legacy:
        _run_legacy(pdfs, args.out, job_id)
    else:
        _run_new(pdfs, args.out, job_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
