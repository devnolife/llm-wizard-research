"""
Client for the Unlimited-OCR SGLang service.

The OCR model runs as a *separate* GPU service (see ``ocr_service/``) exposing
an OpenAI-compatible API. This client only depends on ``requests`` and
``pymupdf`` (lazy-imported), so it never pulls SGLang/torch into the backend
environment.

It is used as a **fallback** inside the document pipeline: when ``pypdf`` fails
to extract meaningful text (i.e. scanned / image-only PDFs), the pages are
rasterized and sent to the OCR service, which returns structured Markdown.

Design goals:
- Never raise to the caller. Any failure (service down, timeout, missing deps)
  returns ``None`` so the pipeline can gracefully keep the ``pypdf`` result.
- Cheap availability checks with short-lived caching.
"""

from __future__ import annotations

import base64
import json
import os
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

import requests
from loguru import logger

# Unlimited-OCR emits layout-grounding spans of the form
#   <|det|>category [x1, y1, x2, y2]<|/det|>actual recognized text
# For RAG ingestion we strip the grounding spans and keep the text.
_DET_SPAN_RE = re.compile(r"<\|det\|>.*?<\|/det\|>", re.DOTALL)
_SPECIAL_TOKEN_RE = re.compile(r"<\|[^|>]*\|>")

# Default location of the serialized no-repeat-ngram processor string produced
# by ``ocr_service/gen_ngram_processor.py``. ocr_client.py lives at
# backend/app/utils/ -> parents[3] is the project root.
_DEFAULT_NGRAM_FILE = (
    Path(__file__).resolve().parents[3] / "ocr_service" / "ngram_processor.txt"
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class UnlimitedOCRClient:
    """Thin client for the Unlimited-OCR SGLang OpenAI-compatible endpoint."""

    def __init__(
        self,
        service_url: Optional[str] = None,
        image_mode: Optional[str] = None,
        dpi: Optional[int] = None,
        concurrency: Optional[int] = None,
        timeout: Optional[int] = None,
        ngram_size: Optional[int] = None,
        ngram_window: Optional[int] = None,
        prompt: Optional[str] = None,
        ngram_processor_file: Optional[str] = None,
        strip_layout_tags: Optional[bool] = None,
    ) -> None:
        self.service_url = (
            service_url or os.getenv("OCR_SERVICE_URL", "http://127.0.0.1:10000")
        ).rstrip("/")
        self.image_mode = (image_mode or os.getenv("OCR_IMAGE_MODE", "gundam")).strip()
        self.dpi = int(dpi if dpi is not None else os.getenv("OCR_DPI", 200))
        self.concurrency = int(
            concurrency if concurrency is not None else os.getenv("OCR_CONCURRENCY", 4)
        )
        self.timeout = int(timeout if timeout is not None else os.getenv("OCR_TIMEOUT", 1200))
        self.ngram_size = int(
            ngram_size if ngram_size is not None else os.getenv("OCR_NGRAM_SIZE", 35)
        )
        self.ngram_window = int(
            ngram_window if ngram_window is not None else os.getenv("OCR_NGRAM_WINDOW", 128)
        )
        self.prompt = prompt or os.getenv("OCR_PROMPT", "document parsing.")
        self.served_model_name = os.getenv("OCR_MODEL_NAME", "Unlimited-OCR")
        self.strip_layout_tags = (
            strip_layout_tags
            if strip_layout_tags is not None
            else _env_bool("OCR_STRIP_LAYOUT_TAGS", True)
        )

        self._ngram_processor_file = Path(
            ngram_processor_file
            or os.getenv("OCR_NGRAM_PROCESSOR_FILE", str(_DEFAULT_NGRAM_FILE))
        )
        self._ngram_processor_str: Optional[str] = None
        self._ngram_loaded = False

        # Short-lived availability cache to avoid hammering /health.
        self._available_cache: Optional[bool] = None
        self._available_checked_at: float = 0.0
        self._available_ttl = 15.0

        self._session = requests.Session()
        self._session.trust_env = False

    # ------------------------------------------------------------------ utils
    def _load_ngram_processor(self) -> Optional[str]:
        if self._ngram_loaded:
            return self._ngram_processor_str
        self._ngram_loaded = True
        try:
            if self._ngram_processor_file.is_file():
                text = self._ngram_processor_file.read_text(encoding="utf-8").strip()
                self._ngram_processor_str = text or None
                if self._ngram_processor_str:
                    logger.debug(
                        f"Loaded OCR ngram processor from {self._ngram_processor_file}"
                    )
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"Could not read OCR ngram processor file: {e}")
            self._ngram_processor_str = None
        return self._ngram_processor_str

    def is_available(self, force: bool = False) -> bool:
        """Return True if the OCR service answers /health (cached briefly)."""
        now = time.time()
        if (
            not force
            and self._available_cache is not None
            and (now - self._available_checked_at) < self._available_ttl
        ):
            return self._available_cache

        ok = False
        try:
            resp = self._session.get(f"{self.service_url}/health", timeout=5)
            ok = resp.status_code == 200
        except requests.RequestException as e:
            logger.debug(f"OCR service not reachable at {self.service_url}: {e}")
            ok = False

        self._available_cache = ok
        self._available_checked_at = now
        return ok

    @staticmethod
    def _encode_image(image_path: str) -> dict:
        ext = os.path.splitext(image_path)[1].lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext.lstrip('.')}"
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}

    def _build_payload(self, image_path: str) -> dict:
        payload = {
            "model": self.served_model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},
                        self._encode_image(image_path),
                    ],
                }
            ],
            "temperature": 0,
            "skip_special_tokens": False,
            "stream": True,
            "images_config": {"image_mode": self.image_mode},
        }
        ngram = self._load_ngram_processor()
        if ngram and self.ngram_size > 0 and self.ngram_window > 0:
            payload["custom_logit_processor"] = ngram
            payload["custom_params"] = {
                "ngram_size": self.ngram_size,
                "window_size": self.ngram_window,
            }
        return payload

    def _collect_stream(self, resp: requests.Response) -> str:
        chunks: List[str] = []
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
                delta = event["choices"][0]["delta"].get("content", "")
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
            if delta:
                chunks.append(delta)
        return "".join(chunks)

    def _clean_output(self, text: Optional[str]) -> Optional[str]:
        """Strip layout-grounding spans / special tokens and tidy whitespace."""
        if not text:
            return text
        if self.strip_layout_tags:
            text = _DET_SPAN_RE.sub("", text)
        text = _SPECIAL_TOKEN_RE.sub("", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # --------------------------------------------------------------- requests
    def ocr_image(self, image_path: str) -> Optional[str]:
        """OCR a single image file. Returns Markdown text, or None on failure."""
        try:
            resp = self._session.post(
                f"{self.service_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                data=json.dumps(self._build_payload(image_path)),
                timeout=self.timeout,
                stream=True,
            )
            resp.raise_for_status()
            return self._clean_output(self._collect_stream(resp))
        except Exception as e:
            logger.warning(f"OCR request failed for {os.path.basename(image_path)}: {e}")
            return None

    def _pdf_to_images(self, pdf_path: str) -> List[str]:
        import fitz  # PyMuPDF, lazy import

        doc = fitz.open(pdf_path)
        tmp_dir = tempfile.mkdtemp(prefix="ocr_pdf_")
        mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
        image_paths: List[str] = []
        try:
            for i, page in enumerate(doc):
                out_path = os.path.join(tmp_dir, f"page_{i + 1:04d}.png")
                page.get_pixmap(matrix=mat).save(out_path)
                image_paths.append(out_path)
        finally:
            doc.close()
        return image_paths

    def ocr_pdf(self, pdf_path: str) -> Optional[str]:
        """
        OCR every page of a PDF concurrently and return the pages joined as a
        single Markdown string (page order preserved). Returns None on failure.
        """
        try:
            image_paths = self._pdf_to_images(pdf_path)
        except ImportError:
            logger.warning(
                "pymupdf (fitz) not installed; cannot rasterize PDF for OCR. "
                "Install with: pip install pymupdf"
            )
            return None
        except Exception as e:
            logger.warning(f"Failed to rasterize PDF for OCR ({pdf_path}): {e}")
            return None

        if not image_paths:
            return None

        results: List[Optional[str]] = [None] * len(image_paths)
        try:
            with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                futures = {
                    executor.submit(self.ocr_image, path): idx
                    for idx, path in enumerate(image_paths)
                }
                for future in as_completed(futures):
                    idx = futures[future]
                    results[idx] = future.result()
        finally:
            for path in image_paths:
                try:
                    os.remove(path)
                except OSError:
                    pass

        pages = [r for r in results if r]
        if not pages:
            return None

        joined = "\n\n".join(
            f"<!-- page {i + 1} -->\n{text}" for i, text in enumerate(results) if text
        )
        return joined or None
