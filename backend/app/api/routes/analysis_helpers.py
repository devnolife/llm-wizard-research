"""Parsing, grounding, and verification helpers for the analysis routes.

Pure functions extracted from ``analysis.py`` (LLM output parsing for gaps,
recommendations, roadmap, paper groups, marked-paper selection, and per-paper
weakness verification). No FastAPI or router dependencies.
"""

from loguru import logger


def _parse_selection_json(raw: str) -> dict:
    """Parse grounded JSON output for the marked-papers analysis."""
    import json as _json
    import re as _re
    text = raw.strip()
    match = _re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, _re.DOTALL)
    if match:
        text = match.group(1)
    elif not text.startswith('{'):
        match = _re.search(r'(\{.*\})', text, _re.DOTALL)
        if match:
            text = match.group(1)
    try:
        data = _json.loads(text)
        if isinstance(data, dict):
            sugg = []
            for s in data.get("suggestions", []):
                if isinstance(s, dict):
                    raw_sources = s.get("source_papers", s.get("supporting_papers", s.get("papers", [])))
                    if isinstance(raw_sources, str):
                        raw_sources = [raw_sources]
                    sugg.append({
                        "title": str(s.get("title", s.get("judul", ""))).strip(),
                        "rationale": str(s.get("rationale", s.get("alasan", ""))).strip(),
                        "basis": str(s.get("basis", s.get("evidence", s.get("bukti", "")))).strip(),
                        "source_papers": [str(p).strip() for p in raw_sources if str(p).strip()][:5] if isinstance(raw_sources, list) else [],
                        "gap_type": str(s.get("gap_type", "")).strip().upper(),
                    })
                elif isinstance(s, str):
                    sugg.append({"title": s, "rationale": "", "basis": "", "source_papers": [], "gap_type": ""})
            return {
                "common_keywords": [str(k) for k in data.get("common_keywords", data.get("kata_kunci", []))],
                "shared_themes": [str(t) for t in data.get("shared_themes", data.get("tema", []))],
                "suggestions": sugg,
                "summary": data.get("summary", data.get("ringkasan", "")),
            }
    except (_json.JSONDecodeError, ValueError):
        pass
    return {"common_keywords": [], "shared_themes": [], "suggestions": [], "summary": text[:500]}


def _ground_selection_suggestions(suggestions: list, papers: list[dict]) -> list[dict]:
    """Keep only research directions tied to at least two marked papers.

    The marked-paper flow receives abstracts rather than full text.  Requiring
    cited titles prevents generic algorithm/domain combinations from being
    presented as evidence-backed synthesis opportunities.
    """
    known_titles = [str(p.get("title", "")).strip() for p in papers if p.get("title")]

    def _normalise(title: str) -> str:
        import re
        return re.sub(r"\s+", " ", title.lower()).strip()

    def _match_title(candidate: str) -> str | None:
        candidate_norm = _normalise(candidate)
        if not candidate_norm:
            return None
        for title in known_titles:
            title_norm = _normalise(title)
            if candidate_norm == title_norm or candidate_norm in title_norm or title_norm in candidate_norm:
                return title
        return None

    grounded = []
    for suggestion in suggestions:
        if not isinstance(suggestion, dict) or not suggestion.get("title"):
            continue
        sources = []
        for source in suggestion.get("source_papers", []):
            matched = _match_title(str(source))
            if matched and matched not in sources:
                sources.append(matched)
        if len(sources) < 2:
            continue
        suggestion["source_papers"] = sources
        suggestion["basis"] = str(suggestion.get("basis", "")).strip()
        grounded.append(suggestion)
    return grounded[:3]


def _parse_weaknesses_json(raw: str) -> dict:
    """Parse LLM JSON output for per-paper weaknesses (tersurat & tersirat)."""
    import json as _json
    import re as _re
    text = (raw or "").strip()
    match = _re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, _re.DOTALL)
    if match:
        text = match.group(1)
    elif not text.startswith('{'):
        match = _re.search(r'(\{.*\})', text, _re.DOTALL)
        if match:
            text = match.group(1)

    def _clean(items):
        """Normalise weakness items to {poin, dasar, kutipan} (handles legacy strings)."""
        out = []
        for it in items if isinstance(items, list) else []:
            if isinstance(it, dict):
                poin = str(
                    it.get("poin", it.get("point", it.get("kelemahan", it.get("kekurangan", ""))))
                ).strip().lstrip('-•* ').strip()
                dasar = str(
                    it.get("dasar", it.get("basis", it.get("alasan", it.get("bukti", ""))))
                ).strip()
                kutipan = str(
                    it.get("kutipan", it.get("quote", it.get("kutipan_verbatim", "")))
                ).strip().strip('"').strip()
                if poin:
                    out.append({"poin": poin, "dasar": dasar, "kutipan": kutipan})
            else:
                s = str(it).strip().lstrip('-•* ').strip()
                if s:
                    out.append({"poin": s, "dasar": "", "kutipan": ""})
        return out[:3]

    try:
        data = _json.loads(text)
        if isinstance(data, dict):
            return {
                "tersurat": _clean(data.get("tersurat", data.get("explicit", []))),
                "tersirat": _clean(data.get("tersirat", data.get("implicit", []))),
            }
    except (_json.JSONDecodeError, ValueError):
        pass
    return {"tersurat": [], "tersirat": []}


def _normalize_text(s: str) -> str:
    """Lowercase + collapse whitespace for robust substring matching."""
    from ...core.gap_detection.quote_grounding import normalize_text
    return normalize_text(s)


def _fuzzy_contains(needle: str, haystack: str, threshold: float = 0.82) -> float:
    """
    Return best similarity (0-1) of `needle` against any same-length window of
    `haystack`. Delegates to the shared quote-grounding util (single algorithm
    for both weakness verification and gap-indicator quote grounding).
    """
    from ...core.gap_detection.quote_grounding import fuzzy_contains
    return fuzzy_contains(needle, haystack)


def _content_word_overlap(claim: str, full_norm: str) -> float:
    """Fraction of meaningful words in `claim` that also appear in the paper."""
    import re as _re
    stop = {
        "yang", "dan", "atau", "tidak", "ada", "pada", "ini", "itu", "untuk",
        "dengan", "dari", "ke", "di", "the", "a", "an", "of", "to", "in", "is",
        "are", "and", "or", "not", "no", "this", "that", "study", "paper",
        "jurnal", "penelitian", "hanya", "secara", "sebuah", "adalah",
    }
    words = [w for w in _re.findall(r"[a-zA-Z]{4,}", claim.lower()) if w not in stop]
    if not words:
        return 0.0
    hits = sum(1 for w in set(words) if w in full_norm)
    return hits / len(set(words))


def _verify_paper_weaknesses(
    parsed,
    full_content,
    source_name="",
    vector_store=None,
    analysis_job_id="",
):
    """
    Verify each weakness point against the paper text so the output is grounded,
    not guessed.

    - tersurat (explicit): the 'kutipan'/'dasar' MUST be locatable in the paper
      (substring or fuzzy match). Unverifiable points are DROPPED — they are
      likely hallucinations. Verified points get verification_status='terverifikasi'.
    - tersirat (implicit, by definition not written): grounded against the paper
      via the project's own vector store (embedding similarity, filtered to this
      source) with a content-word overlap fallback. Points with no grounding at
      all are dropped; the rest carry verification_status + confidence.
    """
    full_norm = _normalize_text(full_content)

    def _ground_score(text: str) -> float:
        # Primary: reuse the project's embeddings via the vector store.
        if vector_store is not None and source_name and text:
            try:
                source_filter = {"source": source_name}
                if analysis_job_id:
                    source_filter = {
                        "$and": [
                            {"analysis_job_id": analysis_job_id},
                            source_filter,
                        ]
                    }
                results = vector_store.search(query=text, top_k=1, filter_metadata=source_filter)
                if results:
                    return max(0.0, float(results[0].score))
            except Exception as e:
                logger.debug(f"Weakness grounding search failed: {e}")
        # Fallback: lexical overlap with the paper text.
        return _content_word_overlap(text, full_norm)

    verified_tersurat = []
    for item in parsed.get("tersurat", []):
        quote = item.get("kutipan") or item.get("dasar") or item.get("poin")
        match = _fuzzy_contains(quote, full_content)
        if match >= 0.82:
            item["verification_status"] = "terverifikasi"
            item["confidence"] = round(match, 2)
            verified_tersurat.append(item)
        # else: explicit claim we cannot find in the text → drop (hallucination)

    verified_tersirat = []
    for item in parsed.get("tersirat", []):
        basis = item.get("dasar") or item.get("poin")
        score = _ground_score(basis)
        if score < 0.2:
            continue  # ungrounded inference → drop
        item["verification_status"] = "terbukti" if score >= 0.5 else "inferensi"
        item["confidence"] = round(score, 2)
        verified_tersirat.append(item)

    return {"tersurat": verified_tersurat, "tersirat": verified_tersirat}


def _parse_gap_json(raw: str) -> list:
    """Parse LLM JSON output for gaps. Falls back to text parsing."""
    import json as _json
    import re as _re
    text = raw.strip()
    # Try to extract JSON array from markdown code blocks
    match = _re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, _re.DOTALL)
    if match:
        text = match.group(1)
    elif not text.startswith('['):
        # Try to find a JSON array anywhere in the text
        match = _re.search(r'(\[.*\])', text, _re.DOTALL)
        if match:
            text = match.group(1)
    try:
        items = _json.loads(text)
        if isinstance(items, list):
            result = []
            for item in items:
                if isinstance(item, dict):
                    result.append({
                        "title": item.get("title", item.get("gap", "Untitled")),
                        "description": item.get("description", ""),
                        "type": item.get("type", "general"),
                        "confidence": item.get("confidence", 0.5),
                        "evidence": item.get("evidence", []),
                        "suggested_directions": item.get("suggested_directions", []),
                    })
            return result
    except (_json.JSONDecodeError, ValueError):
        pass
    # Fallback: parse numbered list text
    return _parse_gap_text(text)


def _parse_gap_text(text: str) -> list:
    """Parse plain text gaps (numbered list) into structured dicts."""
    import re as _re
    gaps = []
    # Split by numbered items like "1." or "- "
    items = _re.split(r'\n\s*(?:\d+[\.\)]\s*|-\s+)', text)
    for item in items:
        item = item.strip()
        if not item or len(item) < 10:
            continue
        title = item.split('\n')[0].strip().rstrip(':')
        desc = '\n'.join(item.split('\n')[1:]).strip() or title
        gaps.append({
            "title": title[:200],
            "description": desc,
            "type": "general",
            "confidence": 0.5,
            "evidence": [],
            "suggested_directions": [],
        })
    return gaps


def _coerce_rec_dict(item: dict, idx: int) -> dict:
    """Normalise one LLM dict into a recommendation record (or {} if degenerate)."""
    title = _clean_rec_field(str(item.get("title", "")))
    description = _clean_rec_field(str(item.get("description", "")))
    if _is_degenerate_text(title) and _is_degenerate_text(description):
        return {}
    default_priority = "high" if idx < 2 else "medium" if idx < 4 else "low"
    return {
        "title": title or "Usulan penelitian",
        "description": description,
        "gap_type": str(item.get("gap_type", item.get("type", ""))).upper(),
        "why": _clean_rec_field(str(item.get("why", ""))),
        "how": _clean_rec_field(str(item.get("how", ""))),
        "priority": item.get("priority", default_priority),
    }


def _parse_recommendations_json(raw: str) -> list:
    """
    Parse LLM JSON output for recommendations. Robust to:
    - a JSON array  [ {...}, {...} ]
    - a SINGLE JSON object  {...}  (small models often drop the array wrapper)
    - several bare objects  {...}\n{...}  not wrapped in an array
    - markdown code fences around any of the above
    Never lets raw JSON leak into a recommendation field.
    """
    import json as _json
    import re as _re
    text = (raw or "").strip()

    # Unwrap a ```json ... ``` fence if present.
    fence = _re.search(r'```(?:json)?\s*(.+?)\s*```', text, _re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    parsed = None
    # 1) Try the whole payload as-is (handles both array and single object).
    try:
        parsed = _json.loads(text)
    except (_json.JSONDecodeError, ValueError):
        parsed = None

    # 2) If that failed, try to isolate a top-level array.
    if parsed is None:
        m = _re.search(r'\[.*\]', text, _re.DOTALL)
        if m:
            try:
                parsed = _json.loads(m.group())
            except (_json.JSONDecodeError, ValueError):
                parsed = None

    # 3) Still nothing → collect every individual {...} object and parse each.
    if parsed is None:
        objs = []
        for m in _re.finditer(r'\{[^{}]*\}', text, _re.DOTALL):
            try:
                objs.append(_json.loads(m.group()))
            except (_json.JSONDecodeError, ValueError):
                continue
        if objs:
            parsed = objs

    # Normalise the shape to a list of dicts.
    if isinstance(parsed, dict):
        parsed = [parsed]
    if isinstance(parsed, list):
        result = []
        for idx, item in enumerate(parsed):
            if isinstance(item, dict):
                rec = _coerce_rec_dict(item, idx)
                if rec:
                    result.append(rec)
        if result:
            return result

    # Last resort: plain-text parsing (guards against raw JSON leakage).
    return _parse_recommendations_text(text)


def _parse_recommendations_text(text: str) -> list:
    """Parse plain text recommendations into structured dicts."""
    import re as _re
    # Safety: if the text still looks like JSON, do NOT dump it into a card.
    stripped = (text or "").strip()
    if stripped.startswith('{') or stripped.startswith('['):
        return []
    recs = []
    items = _re.split(r'\n\s*(?:\d+[\.\)]\s*|-\s+)', text)
    for item in items:
        item = item.strip()
        if not item or len(item) < 10:
            continue
        # Skip any fragment that is (or starts as) raw JSON.
        if item.startswith('{') or item.startswith('['):
            continue
        title = item.split('\n')[0].strip().rstrip(':')
        desc = '\n'.join(item.split('\n')[1:]).strip() or title
        # Skip bare gap-type tags like "[INCOMPLETENESS]".
        if _is_degenerate_text(title) and _is_degenerate_text(desc):
            continue
        recs.append({
            "title": title[:200],
            "description": desc,
            "why": "",
            "how": "",
            "priority": "medium",
        })
    return recs


def _is_degenerate_text(s: str) -> bool:
    """True if a string is just a bare gap-type tag / placeholder (e.g. "[INCOMPLETENESS]")."""
    import re as _re
    t = (s or "").strip()
    if len(t) < 6:
        return True
    return bool(_re.match(
        r'^\[?\s*(FRAGMENTATION|INCONSISTENCY|INCOMPLETENESS|UNKNOWN|NULL|N/?A|NONE)\s*\]?$',
        t, _re.IGNORECASE,
    ))


def _clean_rec_field(s: str) -> str:
    """Strip a leading bare gap-type tag like "[INCOMPLETENESS] " from a field."""
    import re as _re
    return _re.sub(
        r'^\s*\[\s*(FRAGMENTATION|INCONSISTENCY|INCOMPLETENESS|UNKNOWN)\s*\]\s*',
        '', (s or ''), flags=_re.IGNORECASE,
    ).strip()


def _build_recommendations_from_gaps(gaps: list) -> list:
    """
    Deterministic fallback: synthesise gap-anchored research proposals directly
    from detected gap indicators. Used when the LLM proposal output is empty or
    degenerate (small models sometimes just echo "[INCOMPLETENESS]"). Keeps the
    output anchored to the Cooper/Booth indicators without another LLM round-trip.
    """
    type_meta = {
        "FRAGMENTATION": {
            "verb": "Mengintegrasikan",
            "why": "Menjawab indikator fragmentasi: jurnal membahas fenomena serupa dari sudut berbeda tetapi belum saling terintegrasi.",
        },
        "INCONSISTENCY": {
            "verb": "Merekonsiliasi",
            "why": "Menjawab indikator inkonsistensi: terdapat temuan antar-jurnal yang saling bertentangan dan belum direkonsiliasi.",
        },
        "INCOMPLETENESS": {
            "verb": "Melengkapi",
            "why": "Menjawab indikator ketidaklengkapan kolektif: ada aspek penting yang belum dicakup bersama oleh jurnal-jurnal yang dianalisis.",
        },
    }
    recs = []
    for idx, g in enumerate(gaps[:5]):
        gtype = str(g.get("type") or "INCOMPLETENESS").upper()
        meta = type_meta.get(gtype, type_meta["INCOMPLETENESS"])
        dirs = [
            str(d).replace("Investigate:", "").strip().rstrip(".")
            for d in (g.get("suggested_directions") or [])
            if str(d).strip()
        ]
        focus = dirs[0] if dirs else (g.get("title") or "")
        if focus:
            title = f"{meta['verb']} aspek: {focus}"[:200]
            desc = (
                f"Penelitian yang {meta['verb'].lower()} {focus[0].lower() + focus[1:] if focus else focus} "
                f"berdasarkan jurnal-jurnal yang dianalisis."
            )
        else:
            title = f"{meta['verb']} literatur pada topik ini"
            desc = g.get("description", "")
        how = ""
        if len(dirs) > 1:
            how = "Tinjau dan bandingkan secara sistematis: " + "; ".join(dirs[:3]) + "."
        recs.append({
            "title": title,
            "description": desc,
            "gap_type": gtype,
            "why": meta["why"],
            "how": how,
            "priority": "high" if idx < 2 else "medium" if idx < 4 else "low",
        })
    return recs


def _parse_paper_groups_json(raw: str) -> list:
    """Parse LLM JSON output classifying each paper by its basis/approach."""
    import json as _json
    import re as _re
    text = raw.strip()
    match = _re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, _re.DOTALL)
    if match:
        text = match.group(1)
    elif not text.startswith('['):
        match = _re.search(r'(\[.*\])', text, _re.DOTALL)
        if match:
            text = match.group(1)
    try:
        items = _json.loads(text)
        if isinstance(items, list):
            result = []
            for item in items:
                if isinstance(item, dict):
                    result.append({
                        "title": item.get("title", item.get("paper", "")),
                        "basis": item.get("basis", item.get("category", "Lainnya")),
                    })
            return result
    except (_json.JSONDecodeError, ValueError):
        pass
    return []


def _parse_roadmap_json(raw: str) -> list:
    """Parse LLM JSON output for roadmap phases."""
    import json as _json
    import re as _re
    text = raw.strip()
    match = _re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, _re.DOTALL)
    if match:
        text = match.group(1)
    elif not text.startswith('['):
        match = _re.search(r'(\[.*\])', text, _re.DOTALL)
        if match:
            text = match.group(1)
    try:
        items = _json.loads(text)
        if isinstance(items, list):
            result = []
            for item in items:
                if isinstance(item, dict):
                    result.append({
                        "phase": item.get("phase", f"Phase {len(result)+1}"),
                        "items": item.get("items", item.get("tasks", [])),
                    })
            return result
    except (_json.JSONDecodeError, ValueError):
        pass
    # Fallback: parse text roadmap
    return _parse_roadmap_text(text)


def _parse_roadmap_text(text: str) -> list:
    """Parse plain text roadmap into structured phases (robust fallback)."""
    import re as _re
    # Strip stray markdown bold/italic markers that LLMs often leave behind
    text = text.replace('**', '').replace('__', '')
    phases = []
    # Match phase headers AND capture the phase title after it:
    #   "Fase 1: Penelitian Teori", "Phase 2 - Build", "Tahap 3 Pengujian"
    pattern = _re.compile(
        r'(?:^|\n)\s*(?:#{1,3}\s*)?(?:Phase|Fase|Tahap)\s*\d+\s*[:\-.]?\s*([^\n]*)',
        _re.IGNORECASE,
    )
    matches = list(pattern.finditer(text))
    if matches:
        for i, m in enumerate(matches):
            title = m.group(1).strip().rstrip(':').strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end]
            items = []
            for line in body.split('\n'):
                line = line.strip().lstrip('-•* ').strip()
                line = _re.sub(r'^\d+[.)]\s*', '', line)
                if line and len(line) > 3:
                    items.append(line)
            label = title if title else f"Tahap {len(phases) + 1}"
            if items:
                phases.append({"phase": label, "items": items})
        if phases:
            return phases
    # No phase headers: treat as a flat numbered/bulleted list, dropping preamble
    items = []
    for line in text.split('\n'):
        line = line.strip().lstrip('-•* ').strip()
        line = _re.sub(r'^\d+[.)]\s*', '', line)
        low = line.lower()
        if line and len(line) > 3 and not low.startswith(('berikut', 'peta jalan', 'here', 'roadmap')):
            items.append(line)
    if items:
        return [{"phase": "Rencana Penelitian", "items": items}]
    return []
