"""Klien HTTP kecil untuk copilotd — service Go Copilot SDK milik user.

copilotd (github.com/devnolife/copilot-sdk-go) mengekspos langganan GitHub
Copilot (akun enterprise) sebagai HTTP API lokal. Backend ini hanya berbicara
HTTP; tidak ada dependensi SDK di sini.

Konfigurasi lewat env:
- ``COPILOTD_URL``      mis. http://127.0.0.1:8791 (kosong = fitur nonaktif)
- ``COPILOTD_API_KEY``  dikirim sebagai header ``X-API-Key`` bila diisi
- ``COPILOTD_MODEL``    model default (default: claude-opus-4.8-fast)
"""

import os
from typing import Optional, Tuple

import requests
from loguru import logger

DEFAULT_MODEL = "claude-opus-4.8-fast"


def _default_model() -> str:
    return (os.getenv("COPILOTD_MODEL") or DEFAULT_MODEL).strip()


def _base_url() -> str:
    return (os.getenv("COPILOTD_URL") or "").rstrip("/")


def _headers() -> dict:
    key = os.getenv("COPILOTD_API_KEY")
    return {"X-API-Key": key} if key else {}


def is_configured() -> bool:
    return bool(_base_url())


def status(timeout: float = 5.0) -> Optional[dict]:
    """Status copilotd (jumlah akun, model aktif) atau None bila mati."""
    if not is_configured():
        return None
    try:
        r = requests.get(f"{_base_url()}/v1/status", headers=_headers(), timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def generate(
    prompt: str,
    system: str = "",
    json_mode: bool = False,
    model: str = "",
    tier: str = "",
    timeout: float = 90.0,
    temperature: Optional[float] = None,
) -> Optional[Tuple[str, str]]:
    """Satu giliran generate via copilotd.

    ``temperature`` diteruskan hanya bila diisi; pemanggil yang butuh hasil
    reproducible (ekstraksi terstruktur) memakai 0.

    Returns:
        (text, model_id) — atau None bila copilotd tidak dikonfigurasi,
        mati, atau menjawab kosong (pemanggil diharapkan fallback ke LLM
        lokal).
    """
    if not is_configured():
        return None
    payload = {
        "prompt": prompt,
        "system": system,
        "json_mode": json_mode,
        "timeout_sec": timeout,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    chosen = model or _default_model()
    if chosen:
        payload["model"] = chosen
    if tier:
        payload["tier"] = tier
    try:
        r = requests.post(
            f"{_base_url()}/v1/generate",
            json=payload,
            headers=_headers(),
            timeout=timeout + 10,
        )
        r.raise_for_status()
        body = r.json()
        text = (body.get("text") or "").strip()
        if not text:
            logger.warning("copilotd mengembalikan teks kosong")
            return None
        return text, str(body.get("model") or "copilot")
    except requests.RequestException as e:
        logger.warning(f"copilotd tidak tersedia, fallback ke LLM lokal: {e}")
        return None
