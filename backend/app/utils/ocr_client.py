"""
Client for the ocrd document OCR service.

ocrd (installed at ``~/ocr-service``) is a standalone HTTP service wrapping
the Unlimited-OCR VLM. Unlike the previous
raw-SGLang integration, all heavy lifting happens server-side: PDF rendering,
per-page concurrency, text-layer detection, and output cleanup. This client
is therefore a thin ``multipart/form-data`` wrapper around ``POST /v1/ocr``.

It is used **first** in the document pipeline: PDFs are sent to ocrd with
``prefer_text_layer=true`` so digital PDFs are answered in milliseconds from
their text layer while scanned PDFs go through GPU OCR. ``pypdf`` remains the
fallback when the service is unreachable.

Design goals:
- Never raise to the caller. Any failure (service down, timeout, HTTP error)
  returns ``None`` so the pipeline can gracefully fall back to ``pypdf``.
- Cheap availability checks (``/health`` + ``model_ready``) with short-lived
  caching.
"""

from __future__ import annotations

import mimetypes
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from loguru import logger


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class OcrdResult:
    """Parsed response of ``POST /v1/ocr``."""

    text: str
    from_text_layer: bool = False
    page_count: int = 0
    duration_ms: int = 0
    engine: str = ""
    image_mode: str = ""
    pages: List[Dict[str, Any]] = field(default_factory=list)


class OcrdClient:
    """Thin HTTP client for the ocrd OCR service (``POST /v1/ocr``)."""

    def __init__(
        self,
        service_url: Optional[str] = None,
        api_key: Optional[str] = None,
        image_mode: Optional[str] = None,
        dpi: Optional[int] = None,
        timeout: Optional[int] = None,
        prefer_text_layer: Optional[bool] = None,
    ) -> None:
        self.service_url = (
            service_url or os.getenv("OCR_SERVICE_URL", "http://127.0.0.1:8792")
        ).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("OCR_API_KEY", "")
        self.image_mode = (image_mode or os.getenv("OCR_IMAGE_MODE", "gundam")).strip()
        # dpi=0 defers to the server's own OCRD_PDF_DPI setting.
        self.dpi = int(dpi if dpi is not None else os.getenv("OCR_DPI", 0))
        # Generous default: a 150-page thesis takes ~3 minutes; leave headroom.
        self.timeout = int(timeout if timeout is not None else os.getenv("OCR_TIMEOUT", 1800))
        self.prefer_text_layer = (
            prefer_text_layer
            if prefer_text_layer is not None
            else _env_bool("OCR_PREFER_TEXT_LAYER", True)
        )

        # Short-lived availability cache to avoid hammering /health.
        self._available_cache: Optional[bool] = None
        self._available_checked_at: float = 0.0
        self._available_ttl = 15.0

        self._session = requests.Session()
        self._session.trust_env = False

    # ------------------------------------------------------------------ utils
    def _headers(self) -> Dict[str, str]:
        return {"X-API-Key": self.api_key} if self.api_key else {}

    def is_available(self, force: bool = False) -> bool:
        """True when ocrd answers ``/health`` **and** reports ``model_ready``.

        The service responds to ``/health`` as soon as it boots, but the model
        takes ~2 minutes to load; ``model_ready`` is the flag that matters.
        The result is cached briefly.
        """
        now = time.time()
        if (
            not force
            and self._available_cache is not None
            and (now - self._available_checked_at) < self._available_ttl
        ):
            return self._available_cache

        ok = False
        try:
            resp = self._session.get(
                f"{self.service_url}/health", headers=self._headers(), timeout=5
            )
            if resp.status_code == 200:
                payload = resp.json()
                ok = bool(payload.get("ok")) and bool(payload.get("model_ready"))
                if not ok:
                    logger.debug(f"ocrd reachable but not ready: {payload}")
        except (requests.RequestException, ValueError) as e:
            logger.debug(f"ocrd service not reachable at {self.service_url}: {e}")
            ok = False

        self._available_cache = ok
        self._available_checked_at = now
        return ok

    # --------------------------------------------------------------- requests
    def read_document(self, file_path: str) -> Optional[OcrdResult]:
        """OCR a PDF or image via ``POST /v1/ocr``.

        Returns an :class:`OcrdResult` (Markdown text plus metadata such as
        ``from_text_layer``), or ``None`` on any failure.
        """
        path = Path(file_path)
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = {
            "image_mode": self.image_mode,
            "dpi": str(self.dpi),
            "prefer_text_layer": "true" if self.prefer_text_layer else "false",
        }
        try:
            with open(path, "rb") as f:
                resp = self._session.post(
                    f"{self.service_url}/v1/ocr",
                    files={"file": (path.name, f, mime)},
                    data=data,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
        except OSError as e:
            logger.warning(f"Could not read {path.name} for OCR: {e}")
            return None
        except requests.RequestException as e:
            logger.warning(f"ocrd request failed for {path.name}: {e}")
            return None

        if resp.status_code != 200:
            detail = ""
            try:
                detail = resp.json().get("detail", "")
            except ValueError:
                detail = resp.text[:200]
            hints = {
                401: "check OCR_API_KEY",
                413: "file exceeds the service's OCRD_MAX_UPLOAD_MB",
                422: "empty/corrupt file or too many pages (OCRD_MAX_PAGES)",
                503: "model not ready or runtime down",
            }
            hint = hints.get(resp.status_code, "")
            logger.warning(
                f"ocrd returned {resp.status_code} for {path.name}: {detail}"
                + (f" ({hint})" if hint else "")
            )
            return None

        try:
            payload = resp.json()
            text = payload.get("text", "")
        except ValueError as e:
            logger.warning(f"ocrd returned invalid JSON for {path.name}: {e}")
            return None

        if not text or not text.strip():
            logger.warning(f"ocrd returned empty text for {path.name}")
            return None

        result = OcrdResult(
            text=text,
            from_text_layer=bool(payload.get("from_text_layer", False)),
            page_count=int(payload.get("page_count", 0)),
            duration_ms=int(payload.get("duration_ms", 0)),
            engine=str(payload.get("engine", "")),
            image_mode=str(payload.get("image_mode", "")),
            pages=payload.get("pages") or [],
        )
        logger.info(
            f"ocrd processed {path.name}: {len(result.text)} chars, "
            f"{result.page_count} pages in {result.duration_ms} ms "
            f"(from_text_layer={result.from_text_layer})"
        )
        return result

    def ocr_pdf(self, pdf_path: str) -> Optional[str]:
        """Convenience wrapper returning only the extracted text."""
        result = self.read_document(pdf_path)
        return result.text if result else None
