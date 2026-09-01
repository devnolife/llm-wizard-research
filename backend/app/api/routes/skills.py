"""Skill library endpoints — LLM berinteraksi dengan AI-Research-SKILLs.

Skill dari https://github.com/Orchestra-Research/AI-Research-SKILLs terpasang
di ``<repo>/.agents/skills/<nama>/SKILL.md`` (markdown + YAML frontmatter).
Endpoint di sini membuat LLM (GitHub Copilot via copilotd, fallback Ollama)
menjawab pertanyaan riset dengan SATU skill sebagai panduan/sistem prompt.
"""

import json
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from ...services import copilot_client
from ..dependencies import get_glm_interface

router = APIRouter()

# <repo>/backend/app/api/routes/skills.py → parents[4] = <repo>
SKILLS_DIR = Path(__file__).resolve().parents[4] / ".agents" / "skills"

MAX_SKILL_CHARS = 24_000  # jaga konteks LLM lokal tetap muat


class SkillAskRequest(BaseModel):
    skill: str = Field(..., min_length=1, max_length=100, description="Skill directory name")
    question: str = Field(..., min_length=5, max_length=4000, description="Research question for the skill-guided LLM")


class RecommendRequest(BaseModel):
    idea: str = Field(..., min_length=10, max_length=4000, description="Research idea/topic (Indonesian or English)")


def _parse_frontmatter(text: str) -> dict:
    """Ambil name/description dari YAML frontmatter SKILL.md (tanpa lib yaml)."""
    meta = {}
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return meta
    for key in ("name", "description"):
        m = re.search(rf"^{key}:\s*(.+?)(?=\n\S|\Z)", match.group(1), re.MULTILINE | re.DOTALL)
        if m:
            meta[key] = re.sub(r"\s+", " ", m.group(1)).strip().strip('"')
    return meta


def _safe_skill_path(name: str) -> Path:
    """Path SKILL.md yang tervalidasi (tolak traversal ../)."""
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise HTTPException(status_code=400, detail="Nama skill tidak valid")
    path = (SKILLS_DIR / name / "SKILL.md").resolve()
    if not str(path).startswith(str(SKILLS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Nama skill tidak valid")
    return path


@router.get("")
def list_skills():
    """Daftar semua skill terpasang (nama, deskripsi)."""
    if not SKILLS_DIR.is_dir():
        return {"skills": [], "total": 0, "skills_dir": str(SKILLS_DIR)}
    skills = []
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        try:
            meta = _parse_frontmatter(skill_md.read_text(encoding="utf-8", errors="replace")[:6000])
        except OSError:
            continue
        skills.append({
            "id": skill_md.parent.name,
            "name": meta.get("name") or skill_md.parent.name,
            "description": meta.get("description") or "",
        })
    return {"skills": skills, "total": len(skills), "skills_dir": str(SKILLS_DIR)}


def _llm_generate(prompt: str, system: str, json_mode: bool = False,
                  timeout: float = 120.0, max_tokens: int = 1500) -> tuple[str, str]:
    """Generate via Copilot (copilotd) dengan fallback Ollama.

    Returns:
        (text, engine_label). Raises HTTPException 503 bila keduanya mati.
    """
    copilot_result = copilot_client.generate(
        prompt, system=system, json_mode=json_mode, timeout=timeout
    )
    if copilot_result:
        text, model_id = copilot_result
        return text, f"GitHub Copilot ({model_id.removeprefix('copilot:')})"
    try:
        glm = get_glm_interface()
        text = glm.generate(
            prompt, system_prompt=system, temperature=0.3,
            max_tokens=max_tokens, format="json" if json_mode else None,
        )
        return str(text), "LLM lokal (Ollama)"
    except Exception as e:
        logger.error(f"LLM generate gagal (copilotd & Ollama): {e}")
        raise HTTPException(status_code=503, detail="Tidak ada LLM yang tersedia saat ini.")


def _strip_json_fences(raw: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())


@router.post("/ask")
def ask_with_skill(request: SkillAskRequest):
    """Jawab pertanyaan riset dengan satu skill sebagai panduan sistem.

    LLM = GitHub Copilot (copilotd) bila tersedia, fallback Ollama lokal.
    """
    path = _safe_skill_path(request.skill)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Skill '{request.skill}' tidak ditemukan")

    content = path.read_text(encoding="utf-8", errors="replace")[:MAX_SKILL_CHARS]
    meta = _parse_frontmatter(content)
    skill_name = meta.get("name") or request.skill

    system = (
        f"You are an expert research assistant equipped with the '{skill_name}' skill. "
        "Follow the skill document below as your primary guidance. Answer the user's "
        "question practically and concretely, citing specific techniques, commands, or "
        "code from the skill where relevant. Answer in Bahasa Indonesia (keep technical "
        "terms in English). Use markdown.\n\n"
        "===== SKILL DOCUMENT =====\n"
        f"{content}\n"
        "===== END SKILL DOCUMENT ====="
    )

    engine: Optional[str] = None
    answer: Optional[str] = None
    answer, engine = _llm_generate(request.question, system, timeout=120.0)

    if not answer or not str(answer).strip():
        raise HTTPException(status_code=502, detail="LLM mengembalikan jawaban kosong.")

    logger.info(f"skills/ask [{engine}] skill={request.skill} q='{request.question[:60]}…'")
    return {
        "success": True,
        "skill": request.skill,
        "skill_name": skill_name,
        "engine": engine,
        "answer": str(answer).strip(),
    }


# ── Rekomendasi penelitian lengkap (LLM memilih skill sendiri) ───────────────

_ROUTE_SYSTEM = (
    "You are a skill router for a research assistant. Given a research idea and a "
    "catalog of skills, pick the 2-3 MOST relevant skill ids for producing a full "
    "research recommendation (methodology, experiments, paper structure). Respond "
    'ONLY with JSON: {"skills": ["id1", "id2"], "reason": "<one short sentence in '
    'Bahasa Indonesia explaining why>"}. Use exact ids from the catalog.'
)

_RECOMMEND_SYSTEM_TEMPLATE = (
    "You are a senior AI research advisor. Using the skill documents below as your "
    "methodology guides, produce a COMPLETE research recommendation for the user's "
    "idea. Respond ONLY with JSON (all prose values in Bahasa Indonesia, technical "
    "terms in English):\n"
    "{\n"
    '  "title": "<judul penelitian akademik yang spesifik>",\n'
    '  "background": "<latar belakang & motivasi, 2-4 kalimat>",\n'
    '  "problem_statements": ["<rumusan masalah 1>", "..."],\n'
    '  "objectives": ["<tujuan penelitian 1>", "..."],\n'
    '  "methodology": [{"step": "<nama tahap singkat>", "description": "<apa yang dilakukan>", "tools": "<framework/library/dataset>"}, ...],\n'
    '  "experiments": [{"name": "<nama eksperimen>", "design": "<desain singkat>", "metrics": "<metrik evaluasi>"}, ...],\n'
    '  "contributions": ["<kontribusi ilmiah 1>", "..."],\n'
    '  "risks": ["<risiko/tantangan + mitigasi>", "..."],\n'
    '  "keywords": ["<kata kunci pencarian literatur EN>", "..."]\n'
    "}\n"
    "methodology harus 4-7 tahap berurutan membentuk pipeline. experiments 2-4 buah. "
    "Ground every section in the skill documents where applicable.\n\n"
    "{skill_docs}"
)

_PER_SKILL_CHARS = 9_000


def _catalog() -> list[dict]:
    return list_skills()["skills"]


def _route_skills(idea: str, catalog: list[dict]) -> tuple[list[str], str, str]:
    """LLM memilih 2-3 skill paling relevan dari katalog.

    Returns:
        (skill_ids, alasan, engine). Fallback heuristik keyword bila LLM
        gagal/format rusak.
    """
    listing = "\n".join(f"- {s['id']}: {s['description'][:160]}" for s in catalog)
    prompt = f'Research idea: "{idea}"\n\nSkill catalog:\n{listing}'
    valid = {s["id"] for s in catalog}
    try:
        raw, engine = _llm_generate(prompt, _ROUTE_SYSTEM, json_mode=True, timeout=90.0, max_tokens=300)
        data = json.loads(_strip_json_fences(raw))
        picked = [s for s in (data.get("skills") or []) if s in valid][:3]
        if picked:
            return picked, str(data.get("reason") or "").strip(), engine
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Routing skill via LLM gagal, pakai heuristik: {e}")

    # Heuristik: overlap kata ide × deskripsi skill; default brainstorming.
    words = {w for w in re.findall(r"[a-z]+", idea.lower()) if len(w) > 3}
    scored = sorted(
        catalog,
        key=lambda s: -len(words & set(re.findall(r"[a-z]+", (s["description"] or "").lower()))),
    )
    picked = [s["id"] for s in scored[:2]]
    for pref in ("brainstorming-research-ideas",):
        if pref in valid and pref not in picked:
            picked.insert(0, pref)
    return picked[:3], "dipilih dengan pencocokan kata kunci (LLM router tidak tersedia)", "heuristik"


@router.post("/recommend")
def recommend_research(request: RecommendRequest):
    """Rekomendasi penelitian LENGKAP dari sebuah ide.

    Alur: LLM memilih sendiri 2-3 skill relevan dari katalog → dokumen skill
    terpilih menjadi panduan → LLM menyusun rekomendasi terstruktur (judul,
    latar belakang, rumusan masalah, tujuan, metodologi bertahap untuk bagan,
    eksperimen, kontribusi, risiko, kata kunci).
    """
    idea = request.idea.strip()
    catalog = _catalog()
    if not catalog:
        raise HTTPException(status_code=503, detail="Tidak ada skill terpasang di .agents/skills.")

    skill_ids, reason, route_engine = _route_skills(idea, catalog)
    names = {s["id"]: s["name"] for s in catalog}

    docs = []
    for sid in skill_ids:
        p = _safe_skill_path(sid)
        if p.is_file():
            body = p.read_text(encoding="utf-8", errors="replace")[:_PER_SKILL_CHARS]
            docs.append(f"===== SKILL: {names.get(sid, sid)} =====\n{body}")
    if not docs:
        raise HTTPException(status_code=404, detail="Skill terpilih tidak ditemukan di disk.")

    system = _RECOMMEND_SYSTEM_TEMPLATE.replace("{skill_docs}", "\n\n".join(docs))
    raw, engine = _llm_generate(
        f'Research idea: "{idea}"', system, json_mode=True, timeout=180.0, max_tokens=3000
    )
    try:
        rec = json.loads(_strip_json_fences(raw))
    except json.JSONDecodeError:
        logger.error(f"recommend: JSON rusak dari {engine}: {raw[:200]}")
        raise HTTPException(status_code=502, detail="LLM mengembalikan format tidak valid — coba lagi.")

    logger.info(f"skills/recommend [{engine}] via {skill_ids}: '{idea[:60]}…'")
    return {
        "success": True,
        "engine": engine,
        "skills_used": [
            {"id": sid, "name": names.get(sid, sid)} for sid in skill_ids
        ],
        "routing_reason": reason,
        "routing_engine": route_engine,
        "recommendation": rec,
    }


# ── Rekomendasi penelitian lengkap (LLM memilih skill sendiri) ───────────────

_ROUTE_SYSTEM = (
    "You are a skill router for a research assistant. Given a research idea and a "
    "catalog of skills, pick the 2-3 MOST relevant skill ids for producing a full "
    "research recommendation (methodology, experiments, paper structure). Respond "
    'ONLY with JSON: {"skills": ["id1", "id2"], "reason": "<one short sentence in '
    'Bahasa Indonesia explaining why>"}. Use exact ids from the catalog.'
)

_RECOMMEND_SYSTEM_TEMPLATE = (
    "You are a senior AI research advisor. Using the skill documents below as your "
    "methodology guides, produce a COMPLETE research recommendation for the user's "
    "idea. Respond ONLY with JSON (all prose values in Bahasa Indonesia, technical "
    "terms in English):\n"
    "{\n"
    '  "title": "<judul penelitian akademik yang spesifik>",\n'
    '  "background": "<latar belakang & motivasi, 2-4 kalimat>",\n'
    '  "problem_statements": ["<rumusan masalah 1>", "..."],\n'
    '  "objectives": ["<tujuan penelitian 1>", "..."],\n'
    '  "methodology": [{"step": "<nama tahap singkat>", "description": "<apa yang dilakukan>", "tools": "<framework/library/dataset>"}, ...],\n'
    '  "experiments": [{"name": "<nama eksperimen>", "design": "<desain singkat>", "metrics": "<metrik evaluasi>"}, ...],\n'
    '  "contributions": ["<kontribusi ilmiah 1>", "..."],\n'
    '  "risks": ["<risiko/tantangan + mitigasi>", "..."],\n'
    '  "keywords": ["<kata kunci pencarian literatur EN>", "..."]\n'
    "}\n"
    "methodology harus 4-7 tahap berurutan membentuk pipeline. experiments 2-4 buah. "
    "Ground every section in the skill documents where applicable.\n\n"
    "{skill_docs}"
)

_PER_SKILL_CHARS = 9_000


def _catalog() -> list[dict]:
    return list_skills()["skills"]


def _route_skills(idea: str, catalog: list[dict]) -> tuple[list[str], str, str]:
    """LLM memilih 2-3 skill paling relevan dari katalog.

    Returns:
        (skill_ids, alasan, engine). Fallback heuristik keyword bila LLM
        gagal/format rusak.
    """
    listing = "\n".join(f"- {s['id']}: {s['description'][:160]}" for s in catalog)
    prompt = f'Research idea: "{idea}"\n\nSkill catalog:\n{listing}'
    valid = {s["id"] for s in catalog}
    try:
        raw, engine = _llm_generate(prompt, _ROUTE_SYSTEM, json_mode=True, timeout=90.0, max_tokens=300)
        data = json.loads(_strip_json_fences(raw))
        picked = [s for s in (data.get("skills") or []) if s in valid][:3]
        if picked:
            return picked, str(data.get("reason") or "").strip(), engine
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Routing skill via LLM gagal, pakai heuristik: {e}")

    # Heuristik: overlap kata ide × deskripsi skill; default brainstorming.
    words = {w for w in re.findall(r"[a-z]+", idea.lower()) if len(w) > 3}
    scored = sorted(
        catalog,
        key=lambda s: -len(words & set(re.findall(r"[a-z]+", (s["description"] or "").lower()))),
    )
    picked = [s["id"] for s in scored[:2]]
    for pref in ("brainstorming-research-ideas",):
        if pref in valid and pref not in picked:
            picked.insert(0, pref)
    return picked[:3], "dipilih dengan pencocokan kata kunci (LLM router tidak tersedia)", "heuristik"


@router.post("/recommend")
def recommend_research(request: RecommendRequest):
    """Rekomendasi penelitian LENGKAP dari sebuah ide.

    Alur: LLM memilih sendiri 2-3 skill relevan dari katalog → dokumen skill
    terpilih menjadi panduan → LLM menyusun rekomendasi terstruktur (judul,
    latar belakang, rumusan masalah, tujuan, metodologi bertahap untuk bagan,
    eksperimen, kontribusi, risiko, kata kunci).
    """
    idea = request.idea.strip()
    catalog = _catalog()
    if not catalog:
        raise HTTPException(status_code=503, detail="Tidak ada skill terpasang di .agents/skills.")

    skill_ids, reason, route_engine = _route_skills(idea, catalog)
    names = {s["id"]: s["name"] for s in catalog}

    docs = []
    for sid in skill_ids:
        p = _safe_skill_path(sid)
        if p.is_file():
            body = p.read_text(encoding="utf-8", errors="replace")[:_PER_SKILL_CHARS]
            docs.append(f"===== SKILL: {names.get(sid, sid)} =====\n{body}")
    if not docs:
        raise HTTPException(status_code=404, detail="Skill terpilih tidak ditemukan di disk.")

    system = _RECOMMEND_SYSTEM_TEMPLATE.replace("{skill_docs}", "\n\n".join(docs))
    raw, engine = _llm_generate(
        f'Research idea: "{idea}"', system, json_mode=True, timeout=180.0, max_tokens=3000
    )
    try:
        rec = json.loads(_strip_json_fences(raw))
    except json.JSONDecodeError:
        logger.error(f"recommend: JSON rusak dari {engine}: {raw[:200]}")
        raise HTTPException(status_code=502, detail="LLM mengembalikan format tidak valid — coba lagi.")

    logger.info(f"skills/recommend [{engine}] via {skill_ids}: '{idea[:60]}…'")
    return {
        "success": True,
        "engine": engine,
        "skills_used": [
            {"id": sid, "name": names.get(sid, sid)} for sid in skill_ids
        ],
        "routing_reason": reason,
        "routing_engine": route_engine,
        "recommendation": rec,
    }
