#!/usr/bin/env python3
"""
Build a (semi-automatic) gold-standard gap benchmark from the corpus.

Defensible, reproducible ground truth: a synthesis gap that the *authors
themselves* state — in Limitations / Future Work / Conclusion sections — is a
real, citable gap. This tool extracts those sections (reusing the section
extractor from the weakness-grounding work), optionally rephrases each as a
concise one-sentence gap statement with the LLM, auto-suggests a topic via
embedding similarity, and writes a curatable XLSX + JSON. A human then sets
`verified = yes` for the genuine gaps (curation step) before scoring.

Usage (from backend/):
    # Full (LLM-phrased) — needs Ollama:
    python experiments/build_gap_benchmark.py --papers-dir research_papers --max-per-paper 3
    # No-LLM (dump raw section snippets as candidates — author gaps by hand):
    python experiments/build_gap_benchmark.py --no-llm
"""

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.utils.document_processor import DocumentProcessor  # noqa: E402
from app.utils.config_loader import get_config  # noqa: E402

DEFAULT_TOPICS = {
    "T1": "deep learning architectures and optimization techniques",
    "T2": "computer vision object detection and image recognition",
    "T3": "natural language processing and attention mechanisms",
}

GAP_PROMPT = (
    "You are building a research-gap benchmark. From the following "
    "Limitations / Future Work / Conclusion text of ONE paper, extract up to "
    "{n} concise research-gap statements that the authors explicitly state or "
    "clearly imply as unsolved / future work. Each statement: one sentence, "
    "specific, phrased as a gap (e.g. 'lack of evaluation on low-resource "
    "languages'). Do NOT invent gaps not supported by the text.\n\n"
    "TEXT:\n{text}\n\n"
    'Return ONLY JSON: {{"gaps": ["...", "..."]}}'
)


def _parse_gaps(raw: str):
    import re
    text = (raw or "").strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)
    try:
        data = json.loads(text)
        gaps = data.get("gaps", []) if isinstance(data, dict) else []
        return [str(g).strip() for g in gaps if str(g).strip()]
    except (json.JSONDecodeError, ValueError):
        return []


def assign_topic(statement: str, topic_emb, embed_one):
    """Best-matching topic key by embedding cosine; returns (key, score)."""
    from gap_matching import cosine
    sys.path.insert(0, str(BACKEND_DIR / "experiments"))
    v = embed_one(statement)
    best_k, best_s = None, -1.0
    for k, te in topic_emb.items():
        s = cosine(v, te)
        if s > best_s:
            best_k, best_s = k, s
    return best_k, round(best_s, 3)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a gold gap benchmark from corpus future-work sections.")
    parser.add_argument("--papers-dir", default="research_papers")
    parser.add_argument("--max-per-paper", type=int, default=3)
    parser.add_argument("--model", default=None, help="Ollama model for phrasing (default: config)")
    parser.add_argument("--no-llm", action="store_true",
                        help="Skip LLM phrasing; dump raw section snippets as candidates")
    parser.add_argument("--output", default="experiments/gap_benchmark.json")
    args = parser.parse_args()

    cfg = get_config()
    papers_dir = Path(args.papers_dir)
    if not papers_dir.is_absolute():
        papers_dir = BACKEND_DIR.parent / args.papers_dir
    pdfs = sorted(papers_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs in {papers_dir}")
        return 1

    dp = DocumentProcessor(chunk_strategy="sections")

    # Embedder for topic assignment
    sys.path.insert(0, str(BACKEND_DIR / "experiments"))
    from sentence_transformers import SentenceTransformer
    embed_model = SentenceTransformer(cfg.vector_db.embedding_model)
    embed_one = lambda t: embed_model.encode(t, show_progress_bar=False).tolist()
    topic_emb = {k: embed_one(v) for k, v in DEFAULT_TOPICS.items()}

    llm = None
    if not args.no_llm:
        os.environ.setdefault("OLLAMA_MODEL", args.model or cfg.llm.model_name)
        from app.services.llm_service import GLMInterface, ModelConfig
        llm = GLMInterface(ModelConfig(
            model_name=args.model or cfg.llm.model_name,
            base_url=cfg.llm.base_url, temperature=0.2, max_tokens=400,
        ))

    gold_gaps = []
    gid = 0
    for pdf in pdfs:
        try:
            doc = dp.process_pdf(str(pdf))
        except Exception as e:
            print(f"  ! {pdf.name}: {e}")
            continue
        ctx = dp.extract_weakness_sections(doc.content)
        if not ctx:
            continue

        if llm is not None:
            raw = llm.generate(GAP_PROMPT.format(n=args.max_per_paper, text=ctx[:2500]), max_tokens=400)
            statements = _parse_gaps(raw if isinstance(raw, str) else str(raw))[:args.max_per_paper]
        else:
            # No-LLM: split the section into sentence-ish candidates.
            import re
            statements = [s.strip() for s in re.split(r"(?<=[.;])\s+", ctx) if len(s.strip()) > 40][:args.max_per_paper]

        for st in statements:
            tkey, tscore = assign_topic(st, topic_emb, embed_one)
            gid += 1
            gold_gaps.append({
                "id": f"g{gid}",
                "statement": st,
                "source_paper": pdf.name,
                "topic_key": tkey,
                "topic_score": tscore,
                "verified": None,  # human sets true/false during curation
            })
        print(f"  {pdf.name}: +{len(statements)} candidates")

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = BACKEND_DIR / args.output
    out_path.write_text(json.dumps({
        "meta": {
            "source": "authors' stated future-work/limitations",
            "papers": len(pdfs), "candidates": len(gold_gaps),
            "phrasing": "no-llm" if args.no_llm else (args.model or cfg.llm.model_name),
            "note": "Set verified=true for genuine gaps before scoring with evaluate_gaps.py",
        },
        "gold_gaps": gold_gaps,
    }, indent=2))

    # Curatable XLSX
    try:
        from openpyxl import Workbook
        from openpyxl.worksheet.datavalidation import DataValidation
        wb = Workbook(); ws = wb.active; ws.title = "GoldGaps"
        ws.append(["id", "statement", "source_paper", "topic_key", "topic_score", "verified(yes/no)"])
        for g in gold_gaps:
            ws.append([g["id"], g["statement"], g["source_paper"], g["topic_key"], g["topic_score"], ""])
        dv = DataValidation(type="list", formula1='"yes,no"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"F2:F{len(gold_gaps) + 1}")
        ws.column_dimensions["B"].width = 70
        xlsx = out_path.with_suffix(".xlsx")
        wb.save(xlsx)
        print(f"\nForm kurasi: {xlsx}")
    except ImportError:
        print("  (openpyxl unavailable — JSON only)")

    print(f"Benchmark JSON: {out_path}  ({len(gold_gaps)} kandidat)")
    print("Tandai verified=true untuk gap asli, lalu jalankan evaluate_gaps.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
