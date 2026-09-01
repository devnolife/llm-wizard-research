"""Rekomendasi topik penelitian dari gap 'open' — memakai RUMUS RESMI project.

Ranking TIDAK memakai heuristik ad-hoc: ia memanggil
``app.core.recommendation.novelty.rank_proposals`` (skor komposit resmi project:
0.5·gap_confidence + 0.3·novelty + 0.2·actionability, plus band kebaruan &
actionability cues). Peran tiap lapis:

  * Filter   : hanya gap ``novelty_status == "open"`` (verifikasi eksternal
               OpenAlex/2024+ dari TAHAP 3).
  * Proposal : tiap gap open jadi proposal {title, description, gap_type} —
               judul = parafrase, deskripsi = kutipan verbatim.
  * Ranking  : rank_proposals() menilai novelty vs korpus 35 paper + actionability
               + gap_confidence (pakai grounding_score sebagai confidence).
  * LLM      : OPSIONAL, hanya untuk menuliskan narasi judul; tidak memengaruhi
               peringkat (dimatikan dengan --no-llm).

Pakai (dari backend):
    python -m experiments.recommend_topics \
        --gaps ../data/processed/gaps_d4eb6a1d_novelty.jsonl \
        --chunks ../data/processed/chunks_new.jsonl \
        --out ../data/processed/rekomendasi_penelitian.md
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()

from app.core.pipeline.io import read_jsonl
from app.core.recommendation.novelty import rank_proposals
from app.services import copilot_client


def _proposals_from_gaps(gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ubah tiap gap open jadi proposal untuk dinilai rumus project.

    ``title``/``description`` memakai parafrase + kutipan verbatim; ``how`` diisi
    dari kutipan agar sinyal actionability (dataset/eksperimen/framework) terbaca.
    """
    proposals = []
    for g in gaps:
        para = (g.get("gap_paraphrase") or "").strip()
        stmt = (g.get("gap_statement") or "").strip()
        if not (para or stmt):
            continue
        proposals.append({
            "title": para or stmt[:120],
            "description": stmt,
            "how": stmt,
            "gap_type": g.get("gap_type") or "implicit_gap",
            "topic": g.get("topic") or "other",
            "source": g.get("source"),
            "year": g.get("year"),
            "grounding_score": g.get("grounding_score"),
            "related_recent_papers": g.get("related_recent_papers") or [],
        })
    return proposals


def _corpus_from_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Agregasi chunk jadi 1 entri per paper untuk basis novelty-vs-korpus."""
    by_src: Dict[str, List[str]] = defaultdict(list)
    title_by_src: Dict[str, str] = {}
    for c in chunks:
        src = c.get("source")
        by_src[src].append(c.get("text") or "")
        title_by_src.setdefault(src, c.get("paper_title") or src)
    papers = []
    for src, texts in by_src.items():
        papers.append({
            "source": src,
            "title": title_by_src.get(src, src),
            "content": " ".join(texts)[:1500],
        })
    return papers


def _gap_confidences(gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Confidence per tipe gap (pakai grounding_score) untuk rank_proposals."""
    return [{"type": g.get("gap_type"), "confidence": g.get("grounding_score") or 0.0}
            for g in gaps]


def _load_embedder(disabled: bool):
    """Embedder multilingual (sama dg vector store project) di CPU.

    Membuat komponen novelty rumus project bekerja lintas-bahasa (parafrase ID
    vs korpus EN). Dikembalikan None (fallback leksikal) bila dimatikan/gagal.
    """
    if disabled:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", device="cpu"
        )
    except Exception:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Rekomendasi topik (rumus resmi project).")
    ap.add_argument("--gaps", required=True)
    ap.add_argument("--chunks", required=True, help="chunks JSONL sebagai korpus novelty.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", type=int, default=15, help="Jumlah proposal teratas ditampilkan.")
    ap.add_argument("--per-topic", type=int, default=3)
    ap.add_argument("--no-embedder", action="store_true",
                    help="Pakai similarity leksikal (bukan embedding multilingual).")
    ap.add_argument("--no-llm", action="store_true", help="Tanpa narasi LLM.")
    args = ap.parse_args(argv)

    gaps = [g for g in read_jsonl(args.gaps) if g.get("record") != "meta"]
    chunks = [c for c in read_jsonl(args.chunks) if c.get("record") == "chunk"]
    open_gaps = [g for g in gaps if g.get("novelty_status") == "open"]

    proposals = _proposals_from_gaps(open_gaps)
    corpus = _corpus_from_chunks(chunks)
    gap_conf = _gap_confidences(open_gaps)

    # ---- RANKING PAKAI RUMUS RESMI PROJECT (embedder multilingual) ----
    embedder = _load_embedder(args.no_embedder)
    ranked = rank_proposals(proposals, corpus, gaps=gap_conf, embedder=embedder)

    total_open = len(open_gaps)
    lines = [
        "# Rekomendasi Topik Penelitian",
        "",
        "> Peringkat dihitung dengan **rumus resmi project** "
        "`app.core.recommendation.novelty.rank_proposals` "
        "(skor prioritas = 0.5·gap_confidence + 0.3·novelty + 0.2·actionability; "
        "novelty = ketidakmiripan terhadap korpus 35 paper). "
        "Gap difilter ke status **open** (TAHAP 3 OpenAlex 2024+). "
        "LLM hanya untuk narasi, tidak memengaruhi peringkat.",
        "",
        f"Basis: {len(gaps)} gap terverifikasi, {total_open} **open**, "
        f"{len(proposals)} proposal dinilai.",
        "",
    ]

    lines += ["## ⭐ Peringkat Global (skor prioritas project)", ""]
    for i, p in enumerate(ranked[:args.top], 1):
        nov = p.get("novelty", {})
        cites = p.get("related_recent_papers") or []
        cite = ("; ".join(f"{c.get('title', '')[:40]} ({c.get('year')})" for c in cites[:2])
                or "tak ada match 2024+")
        lines.append(
            f"{i}. **[{p.get('priority', '?').upper()} · skor {nov.get('priority_score')}]** "
            f"{p.get('title')}"
        )
        lines.append(
            f"   - topik={p.get('topic')} · novelty={nov.get('novelty')} "
            f"({nov.get('band')}) · actionability={nov.get('actionability')} "
            f"· gap_conf={nov.get('gap_confidence')}"
        )
        lines.append(f"   - sumber: _{p.get('source')}_ ({p.get('year')}) · literatur 2024+: {cite}")
        if nov.get("notes"):
            lines.append(f"   - catatan: {nov['notes'][0]}")
        lines.append("")

    by_topic: Dict[str, List[Dict]] = defaultdict(list)
    for p in ranked:
        by_topic[p.get("topic")].append(p)
    lines += ["## Peringkat per Topik", ""]
    for topic in sorted(by_topic, key=lambda t: -len(by_topic[t])):
        lines.append(f"### {topic} ({len(by_topic[topic])} proposal open)")
        for p in by_topic[topic][:args.per_topic]:
            nov = p.get("novelty", {})
            lines.append(f"- **[{nov.get('priority_score')}]** {p.get('title')} "
                         f"— _{p.get('source', '')[:34]}_ ({p.get('year')})")
        lines.append("")

    if not args.no_llm and copilot_client.is_configured():
        lines += ["## Judul siap-pakai (narasi LLM dari 5 proposal teratas)", ""]
        top5 = ranked[:5]
        bullet = "\n".join(f"- ({p['topic']}) {p['title']}" for p in top5)
        res = copilot_client.generate(
            "Ubah tiap poin berikut menjadi 1 judul penelitian Bahasa Indonesia yang "
            "spesifik dan layak skripsi/tesis (pertahankan urutan, beri penomoran):\n\n" + bullet,
            system="Anda pakar metodologi penelitian forensik digital.",
        )
        lines += [res[0] if res else "(tidak tersedia)", ""]

    report = "\n".join(lines)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(report[:2500])
    print(f"\n[ditulis ke {args.out}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
