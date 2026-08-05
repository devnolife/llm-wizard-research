"""
Cross-Model Critic — komunikasi antar-LLM untuk mode eksperimen `cross-critic`.

Pola: Extractor–Critic debate (1 ronde kritik + 1 ronde pembelaan).
  1. LLM utama (mis. llama3.2) menghasilkan indikator gap seperti biasa.
  2. LLM critic  (mis. gpt-oss) mengkritik SETIAP indikator: apakah grounded
     pada bukti, spesifik-topik, dan bukan output templat → verdict KEEP/REJECT.
  3. Untuk indikator yang di-REJECT, LLM utama diberi kesempatan MEMBELA.
     Critic verdict + pembelaan menentukan keputusan akhir (defensible → keep).

Hipotesis H10: kritik lintas-model meningkatkan presisi/kalibrasi indikator
dibanding mode `nli` (kritik-diri satu model punya self-preference bias).

Juga menyediakan kritik fakta SPO batch per-paper (opsional, --critic-facts)
untuk memfilter entitas sampah hasil ekstraksi (mis. "Table 1" sebagai DATASET).
"""

import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger


def _parse_json_array(raw: str) -> list:
    """Parse a JSON array from LLM output (handles code fences / preamble)."""
    text = (raw or "").strip()
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    elif not text.startswith("["):
        m = re.search(r"(\[.*\])", text, re.DOTALL)
        if m:
            text = m.group(1)
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, ValueError):
        return []


CRITIQUE_PROMPT = """You are a rigorous scientific reviewer (Model B) auditing gap indicators \
produced by another AI system (Model A) for the topic: "{topic}".

A valid SYNTHESIS GAP describes a relationship BETWEEN papers — never a fact about a \
single paper, and never a generic statement that fits any topic:
- FRAGMENTATION: ≥2 papers/clusters study the same phenomenon without integrating findings
- INCONSISTENCY: findings of ≥2 DIFFERENT papers contradict each other
- INCOMPLETENESS: an important aspect is missing from ALL papers collectively

Papers analyzed:
{papers}

Established facts extracted from the papers (SPO triples):
{facts}

Model A's gap indicators:
{indicators}

Judge EACH indicator against ALL four criteria — you MUST give a concrete reason \
citing the criterion, even for KEEP:
1. INTER-PAPER: does it genuinely relate ≥2 papers (or the whole collection)?
   REJECT single-paper observations, or INCONSISTENCY claims where both findings
   come from the same paper.
2. GROUNDED: is it supported by the facts/papers above? REJECT claims about
   entities that appear nowhere in the facts.
3. SPECIFIC: would this exact indicator be false for a random other topic?
   REJECT copy-paste templates ("literature appears fragmented", no specifics).
4. CALIBRATED: is confidence plausible given evidence_count and related_papers_count?
   Use confidence_delta to correct overconfident indicators.

Be strict: a typical honest audit REJECTs 20-40% of machine-generated indicators.

Respond ONLY with a JSON array, one object per indicator, same order:
[
  {{"index": 0, "verdict": "KEEP", "reason": "inter-paper: contradicts across paper X and Y; grounded in fact (A, CONTRADICTS, B)", "confidence_delta": 0.0}},
  {{"index": 1, "verdict": "REJECT", "reason": "inter-paper violated: cites only one paper", "confidence_delta": -0.2}}
]
verdict: KEEP or REJECT. confidence_delta: float in [-0.3, 0.1].
JSON:"""


DEFENSE_PROMPT = """You are Model A. Another reviewer (Model B) rejected some of your gap \
indicators for topic "{topic}". For each rejection below, either DEFEND your indicator \
with concrete evidence from the excerpts, or ACCEPT the rejection.

Rejections:
{rejections}

Respond ONLY with a JSON array, same order:
[
  {{"index": 0, "decision": "DEFEND", "argument": "cite specific evidence"}},
  {{"index": 2, "decision": "ACCEPT", "argument": ""}}
]
decision: DEFEND or ACCEPT.
JSON:"""


FACT_CRITIQUE_PROMPT = """You are a strict knowledge-base auditor. Below are SPO facts \
extracted from the paper "{paper}". Flag facts that are extraction noise:
- entity is not a real research concept (e.g. "Table 1", section headers, author lists, venues as DOMAIN)
- relation is nonsensical for the entity types
- fact is unrelated to the paper's subject

Facts:
{facts}

Respond ONLY with a JSON array listing ONLY the BAD facts:
[
  {{"index": 3, "reason": "'Table 1' is not a dataset"}}
]
If all facts are fine, respond with [].
JSON:"""


class CrossCritic:
    """Debate 1-ronde antara LLM critic dan LLM utama (defender)."""

    # Catatan budget token: gpt-oss adalah reasoning model yang memakai token
    # untuk chain-of-thought SEBELUM JSON akhir. Budget 1200 terbukti terpotong
    # (respons berhenti tepat di max_tokens → JSON tak selesai → fail-open
    # membuat semua KEEP dengan reason kosong). 3500 memberi ruang aman.
    def __init__(self, critic_llm, defender_llm, max_tokens: int = 3500):
        self.critic = critic_llm
        self.defender = defender_llm
        self.max_tokens = max_tokens

    # ── Phase 3: debate atas indikator gap ──────────────────────────

    def debate_indicators(
        self,
        topic: str,
        indicators: List[Any],
        facts_summary: str = "",
        paper_titles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Jalankan kritik (critic) + pembelaan (defender) atas daftar indikator.

        `paper_titles` memberi critic konteks jurnal yang dianalisis sehingga
        klaim antar-paper (inti synthesis gap) dapat diverifikasi — indikator
        yang hanya merujuk satu paper bukan gap antar-jurnal yang valid.

        Returns dict berisi keputusan per indikator:
            {"decisions": [{"index", "keep", "critic_verdict", "critic_reason",
                            "defense", "confidence_delta"}],
             "kept": int, "rejected": int, "defended": int}
        Indeks mengacu ke posisi di `indicators`. Bila terjadi error parsing,
        default fail-open: semua indikator KEEP (tidak menghukum tanpa bukti).
        """
        payload = []
        for i, ind in enumerate(indicators):
            related = sorted({str(p) for p in getattr(ind, "related_papers", []) if str(p)})
            payload.append({
                "index": i,
                "type": str(getattr(ind, "indicator_type", getattr(ind, "gap_type", "?"))),
                "description": str(getattr(ind, "description", ""))[:300],
                "confidence": float(getattr(ind, "confidence", 0.0)),
                "evidence": [str(e)[:150] for e in list(getattr(ind, "evidence", []))[:4]],
                "evidence_count": len(getattr(ind, "evidence", [])),
                "related_papers_count": len(related),
                "related_papers": related[:8],
                "detection_method": str(getattr(ind, "detection_method", "") or ""),
            })

        decisions = [
            {"index": i, "keep": True, "critic_verdict": "KEEP",
             "critic_reason": "", "defense": None, "confidence_delta": 0.0}
            for i in range(len(indicators))
        ]
        result = {"decisions": decisions, "kept": len(indicators), "rejected": 0,
                  "defended": 0, "critic_parse_ok": False}
        if not indicators:
            result["critic_parse_ok"] = True
            return result

        # Ronde 1 — critic menilai
        try:
            raw = self.critic.generate(
                prompt=CRITIQUE_PROMPT.format(
                    topic=topic,
                    papers="\n".join(f"- {t}" for t in (paper_titles or [])) or "(paper list not provided)",
                    facts=facts_summary or "(no fact summary provided)",
                    indicators=json.dumps(payload, ensure_ascii=False, indent=1),
                ),
                temperature=0.2,
                max_tokens=self.max_tokens,
            )
            critiques = _parse_json_array(raw)
        except Exception as e:
            logger.warning(f"CrossCritic: critique round failed ({e}); keeping all indicators")
            return result

        if not critiques:
            # Fail-open TERLIHAT: respons ada tapi tidak bisa diparse (mis.
            # terpotong max_tokens). Jangan diam — catat agar tidak menyaru
            # sebagai "semua indikator valid".
            logger.warning(
                f"CrossCritic: critique response unparseable — keeping all "
                f"{len(indicators)} indicators. raw_len={len(raw or '')}, "
                f"tail={repr((raw or '')[-120:])}"
            )
            return result
        result["critic_parse_ok"] = True

        by_index = {}
        for c in critiques:
            if isinstance(c, dict) and isinstance(c.get("index"), int):
                by_index[c["index"]] = c

        rejected_items = []
        for d in decisions:
            c = by_index.get(d["index"])
            if not c:
                continue
            verdict = str(c.get("verdict", "KEEP")).strip().upper()
            d["critic_verdict"] = "REJECT" if verdict == "REJECT" else "KEEP"
            d["critic_reason"] = str(c.get("reason", ""))[:300]
            try:
                delta = float(c.get("confidence_delta", 0.0))
            except (TypeError, ValueError):
                delta = 0.0
            d["confidence_delta"] = max(-0.3, min(0.1, delta))
            if d["critic_verdict"] == "REJECT":
                rejected_items.append(d)

        # Ronde 2 — defender membela indikator yang di-REJECT
        if rejected_items:
            rejections_payload = [
                {"index": d["index"],
                 "indicator": payload[d["index"]],
                 "critic_reason": d["critic_reason"]}
                for d in rejected_items
            ]
            defenses = []
            try:
                raw = self.defender.generate(
                    prompt=DEFENSE_PROMPT.format(
                        topic=topic,
                        rejections=json.dumps(rejections_payload, ensure_ascii=False, indent=1),
                    ),
                    temperature=0.2,
                    max_tokens=self.max_tokens,
                )
                defenses = _parse_json_array(raw)
            except Exception as e:
                logger.warning(f"CrossCritic: defense round failed ({e}); rejections stand")

            defense_by_index = {
                d["index"]: d for d in defenses
                if isinstance(d, dict) and isinstance(d.get("index"), int)
            }
            for d in rejected_items:
                df = defense_by_index.get(d["index"])
                decision = str(df.get("decision", "ACCEPT")).strip().upper() if df else "ACCEPT"
                argument = str(df.get("argument", ""))[:300] if df else ""
                if decision == "DEFEND" and argument:
                    d["keep"] = True
                    d["defense"] = argument
                    result["defended"] += 1
                else:
                    d["keep"] = False
                    d["defense"] = argument or None

        result["rejected"] = sum(1 for d in decisions if not d["keep"])
        result["kept"] = len(decisions) - result["rejected"]
        logger.info(
            f"CrossCritic debate [{topic[:40]}…]: {result['kept']} keep, "
            f"{result['rejected']} reject, {result['defended']} defended"
        )
        return result

    # ── Phase 2 (opsional): kritik fakta SPO batch per paper ────────

    def critique_facts(self, paper_title: str, facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Satu panggilan batch: kembalikan daftar fakta BURUK
        [{"index": int, "reason": str}]. Fail-open: error → [] (tidak ada yang dibuang).
        """
        if not facts:
            return []
        payload = [
            {"index": i,
             "s": f.get("subject", "?"), "s_type": f.get("subject_type", "?"),
             "p": f.get("predicate", "?"),
             "o": f.get("object", "?"), "o_type": f.get("object_type", "?")}
            for i, f in enumerate(facts)
        ]
        try:
            raw = self.critic.generate(
                prompt=FACT_CRITIQUE_PROMPT.format(
                    paper=paper_title,
                    facts=json.dumps(payload, ensure_ascii=False, indent=1),
                ),
                temperature=0.2,
                max_tokens=self.max_tokens,
            )
            bad = _parse_json_array(raw)
        except Exception as e:
            logger.warning(f"CrossCritic: fact critique failed for {paper_title} ({e})")
            return []
        out = []
        for b in bad:
            if isinstance(b, dict) and isinstance(b.get("index"), int) and 0 <= b["index"] < len(facts):
                out.append({"index": b["index"], "reason": str(b.get("reason", ""))[:200]})
        return out
