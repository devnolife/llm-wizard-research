"""Panduan AI-Research-SKILLs untuk SEMUA panggilan LLM di pipeline analisis.

Setiap fase pipeline (topik, ringkasan, gap, usulan, peta jalan, dst.) dipetakan
ke 1-2 skill dari ``.agents/skills/`` (Orchestra-Research/AI-Research-SKILLs).
Cuplikan skill disisipkan sebagai panduan metodologi di awal prompt, sehingga
skill dipakai di seluruh alur — bukan hanya halaman Skill Riset / Cari Paper.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

from loguru import logger

SKILLS_DIR = Path(__file__).resolve().parents[3] / ".agents" / "skills"

# fase pipeline/endpoint → skill yang relevan (harus ada di SKILLS_DIR)
PHASE_SKILLS = {
    "topics": ["brainstorming-research-ideas"],
    "paper_analysis": ["ml-paper-writing"],
    "summary": ["ml-paper-writing"],
    "gaps": ["brainstorming-research-ideas", "creative-thinking-for-research"],
    "proposal": ["ml-paper-writing", "brainstorming-research-ideas"],
    "roadmap": ["brainstorming-research-ideas"],
    "selection": ["ml-paper-writing"],
    # dipakai GapAnalyzer internal (deteksi kontradiksi & aspek kritis)
    "contradictions": ["creative-thinking-for-research"],
    "aspects": ["brainstorming-research-ideas"],
}

_EXCERPT_SINGLE = 1200  # cukup memberi arah tanpa membengkakkan prompt
_EXCERPT_MULTI = 900

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


@lru_cache(maxsize=128)
def _excerpt(skill_id: str, budget: int) -> str:
    """Isi SKILL.md tanpa frontmatter, dipotong ke ``budget`` karakter."""
    path = SKILLS_DIR / skill_id / "SKILL.md"
    try:
        body = _FRONTMATTER_RE.sub("", path.read_text(encoding="utf-8", errors="replace"))
        return body.strip()[:budget]
    except OSError:
        logger.debug(f"Skill '{skill_id}' tidak ditemukan di {SKILLS_DIR}")
        return ""


def skills_for_phase(phase: str) -> List[str]:
    return PHASE_SKILLS.get(phase, [])


def wrap_prompt(phase: str, prompt: str) -> Tuple[str, List[str]]:
    """Sisipkan panduan skill fase ini di depan prompt.

    Returns:
        (prompt_baru, skill_ids_terpakai) — prompt asli utuh bila fase tidak
        punya mapping atau file skill tidak ada.
    """
    ids = skills_for_phase(phase)
    if not ids:
        return prompt, []
    budget = _EXCERPT_SINGLE if len(ids) == 1 else _EXCERPT_MULTI
    blocks, used = [], []
    for sid in ids:
        ex = _excerpt(sid, budget)
        if ex:
            blocks.append(f"===== RESEARCH SKILL: {sid} =====\n{ex}")
            used.append(sid)
    if not blocks:
        return prompt, []
    header = (
        "Gunakan panduan metodologi riset (AI-Research-SKILLs) berikut bila relevan. "
        "Tetap patuhi format output dan bahasa yang diminta pada tugas di bawah.\n\n"
    )
    return header + "\n\n".join(blocks) + "\n===== END SKILLS =====\n\n" + prompt, used
