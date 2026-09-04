"""Klien LLM di atas GitHub Copilot SDK resmi (paket ``github-copilot-sdk``).

Sebelumnya backend berbicara HTTP ke copilotd — daemon Go milik proyek
studio-revisi yang dipakai bersama. Daemon itu bisa kehilangan token OAuth
diam-diam sementara ``/health`` tetap 200, sehingga pipeline menghasilkan
0 gap tanpa satu pun peringatan (insiden 4 Sep 2026). Kini CLI Copilot
dijalankan sebagai subproses milik proses ini sendiri lewat SDK resmi, dan
autentikasi memakai login Copilot yang tersimpan (``copilot login``).

Kontrak publik dipertahankan agar pemanggil tidak berubah:
``is_configured()``, ``status()``, ``generate()`` → ``(text, model_id) | None``.

SDK bersifat asyncio; pemanggil kita sinkron dan berjalan dari banyak thread
(ThreadPoolExecutor di ekstraksi gap, worker antrean). Karena itu satu event
loop dijalankan di thread latar dan setiap ``generate()`` menitipkan coroutine
ke sana. Satu CLI dipakai bersama seluruh proses; sesi dibuat per permintaan.

Env:
- ``COPILOT_DISABLED=1``        matikan jalur Copilot (pemanggil fallback ke Ollama)
- ``COPILOT_MODEL``             model default (default: claude-opus-4.8-fast)
- ``COPILOT_CLI_PATH``          path CLI; kosong = binari yang dibundel SDK
- ``COPILOT_CONFIG_DIR``        direktori config CLI (default: <repo>/.copilot-sdk)
- ``COPILOT_MAX_CONCURRENCY``   permintaan serentak (default 2, sama dengan copilotd)

Direktori config sengaja dipisah dari ``~/.copilot`` yang dipakai CLI npm milik
copilotd: binari bundel SDK tidak bisa membaca entri login CLI npm di keyring,
jadi ia login sendiri (``copilot --config-dir <dir> login``, sekali) dan menyimpan
tokennya sebagai entri keyring terpisah. Dua instalasi, satu akun GitHub.
"""

from __future__ import annotations

import asyncio
import atexit
import os
import threading
from concurrent.futures import Future
from pathlib import Path
from typing import Any, Optional, Tuple

from loguru import logger

try:
    from copilot import CopilotClient
except ImportError:  # pragma: no cover - lingkungan tanpa SDK
    CopilotClient = None  # type: ignore[assignment,misc]

DEFAULT_MODEL = "claude-opus-4.8-fast"
DEFAULT_MAX_CONCURRENCY = 2
# Sama persis dengan instruksi copilotd agar perilaku json_mode tidak bergeser.
JSON_INSTRUCTION = "Balas HANYA dengan JSON valid, tanpa teks lain dan tanpa pagar kode."
# Nama tool yang tidak pernah ada → sesi berjalan tanpa tool sama sekali.
# (Daftar kosong berarti "tidak ditentukan", bukan "tidak ada".)
NO_TOOLS = ["__none__"]
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _default_model() -> str:
    return (os.getenv("COPILOT_MODEL") or DEFAULT_MODEL).strip()


def config_dir() -> Path:
    return Path(os.getenv("COPILOT_CONFIG_DIR") or _REPO_ROOT / ".copilot-sdk").expanduser()


def _max_concurrency() -> int:
    try:
        return max(1, int(os.getenv("COPILOT_MAX_CONCURRENCY") or DEFAULT_MAX_CONCURRENCY))
    except ValueError:
        return DEFAULT_MAX_CONCURRENCY


def is_configured() -> bool:
    """True bila SDK terpasang dan jalur Copilot tidak dimatikan lewat env."""
    return CopilotClient is not None and os.getenv("COPILOT_DISABLED", "").strip().lower() not in (
        "1", "true", "yes")


def _deny(_request: Any, _invocation: Any) -> dict:
    return {"kind": "denied-by-rules"}


class _Runtime:
    """Satu CLI Copilot per proses, dilayani event loop di thread latar."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._client: Any = None
        self._slots: Optional[threading.BoundedSemaphore] = None

    # ── siklus hidup ──────────────────────────────────────────────────────

    def _ensure_started(self) -> Any:
        with self._lock:
            if self._client is not None:
                return self._client
            loop = asyncio.new_event_loop()
            thread = threading.Thread(target=loop.run_forever, name="copilot-sdk",
                                      daemon=True)
            thread.start()
            cfg = config_dir()
            cfg.mkdir(parents=True, exist_ok=True)
            options: dict = {"log_level": "error", "auto_start": True,
                             "auto_restart": True, "use_logged_in_user": True,
                             "cli_args": ["--config-dir", str(cfg)]}
            if cli_path := os.getenv("COPILOT_CLI_PATH", "").strip():
                options["cli_path"] = cli_path
            client = CopilotClient(options)
            try:
                asyncio.run_coroutine_threadsafe(client.start(), loop).result(timeout=60)
            except Exception:
                loop.call_soon_threadsafe(loop.stop)
                thread.join(timeout=5)
                raise
            self._loop, self._thread, self._client = loop, thread, client
            self._slots = threading.BoundedSemaphore(_max_concurrency())
            logger.info(f"Copilot SDK siap (model default {_default_model()}, "
                        f"konkurensi {_max_concurrency()})")
            return client

    def _submit(self, coro) -> Future:
        assert self._loop is not None
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def stop(self, timeout: float = 10.0) -> None:
        with self._lock:
            client, loop, thread = self._client, self._loop, self._thread
            self._client = self._loop = self._thread = None
        if client is None or loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(client.stop(), loop).result(timeout=timeout)
        except Exception as exc:  # pragma: no cover - hanya saat shutdown
            logger.warning(f"Copilot SDK tidak berhenti bersih: {exc}")
        loop.call_soon_threadsafe(loop.stop)
        if thread is not None:
            thread.join(timeout=5)

    # ── operasi ───────────────────────────────────────────────────────────

    def auth_status(self) -> dict:
        client = self._ensure_started()
        resp = self._submit(client.get_auth_status()).result(timeout=30)
        # Respons SDK memakai camelCase (isAuthenticated), bukan snake_case.
        return {"authenticated": bool(getattr(resp, "isAuthenticated", False)),
                "auth_type": getattr(resp, "authType", None),
                "login": getattr(resp, "login", None),
                "host": getattr(resp, "host", None)}

    def generate(self, prompt: str, system: str, model: str, timeout: float) -> Optional[str]:
        client = self._ensure_started()
        assert self._slots is not None
        with self._slots:
            return self._submit(
                self._generate_async(client, prompt, system, model, timeout)
            ).result(timeout=timeout + 15)

    @staticmethod
    async def _generate_async(client: Any, prompt: str, system: str, model: str,
                              timeout: float) -> Optional[str]:
        config: dict = {"model": model, "available_tools": NO_TOOLS,
                        "on_permission_request": _deny, "streaming": False}
        if system:
            # "replace" persis seperti copilotd: prompt sistem kita menggantikan
            # instruksi bawaan CLI yang ditulis untuk agen pengkodean.
            config["system_message"] = {"mode": "replace", "content": system}
        session = await client.create_session(config)
        try:
            event = await session.send_and_wait({"prompt": prompt}, timeout=timeout)
            content = getattr(getattr(event, "data", None), "content", None) if event else None
            return content if isinstance(content, str) else None
        finally:
            try:
                await session.destroy()
            except Exception as exc:  # pragma: no cover
                logger.debug(f"sesi Copilot tidak bisa dihancurkan: {exc}")


_runtime = _Runtime()
atexit.register(_runtime.stop)


def stop() -> None:
    """Hentikan CLI Copilot; dipanggil dari shutdown aplikasi."""
    _runtime.stop()


def status(timeout: float = 30.0) -> Optional[dict]:
    """Status autentikasi & model default, atau None bila SDK/CLI tidak jalan."""
    if not is_configured():
        return None
    try:
        info = _runtime.auth_status()
    except Exception as exc:
        logger.warning(f"Copilot SDK tidak tersedia: {exc}")
        return None
    info.update({"ok": info["authenticated"], "model": _default_model(),
                 "config_dir": str(config_dir()),
                 "max_concurrency": _max_concurrency(), "backend": "copilot-sdk"})
    return info


def generate(
    prompt: str,
    system: str = "",
    json_mode: bool = False,
    model: str = "",
    tier: str = "",
    timeout: float = 90.0,
    temperature: Optional[float] = None,
) -> Optional[Tuple[str, str]]:
    """Satu giliran generate lewat Copilot SDK.

    ``temperature`` dan ``tier`` diterima hanya demi kompatibilitas tanda tangan.
    Copilot CLI tidak mengekspos temperature, dan copilotd sebelumnya pun
    membuang field itu tanpa pernah meneruskannya — jadi tidak ada perilaku
    yang berubah, hanya kini dinyatakan terbuka.

    Returns:
        (text, model_id) — atau None bila Copilot dimatikan, CLI gagal jalan,
        belum login, kehabisan waktu, atau menjawab kosong. Pemanggil diharapkan
        fallback ke LLM lokal.
    """
    if not is_configured():
        return None
    if json_mode:
        system = f"{system}\n\n{JSON_INSTRUCTION}" if system else JSON_INSTRUCTION
    chosen = model or _default_model()
    try:
        text = _runtime.generate(prompt, system, chosen, timeout)
    except Exception as exc:
        logger.warning(f"Copilot SDK gagal, fallback ke LLM lokal: {exc}")
        return None
    text = (text or "").strip()
    if not text:
        logger.warning("Copilot SDK mengembalikan teks kosong")
        return None
    return text, f"copilot:{chosen}"
