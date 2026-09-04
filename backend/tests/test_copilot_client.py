"""Tes copilot_client di atas Copilot SDK, dengan SDK palsu (tanpa CLI nyata).

Yang dijaga: kontrak publik (None saat gagal, tuple saat sukses), paritas
perilaku copilotd (instruksi JSON, sesi tanpa tool, system message 'replace'),
serta jembatan sinkron→asyncio dari banyak thread.
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from app.services import copilot_client as cc


class _FakeSession:
    def __init__(self, reply, log):
        self._reply = reply
        self._log = log
        self.destroyed = False

    async def send_and_wait(self, options, timeout=None):
        self._log.append(("send", options["prompt"], timeout))
        if isinstance(self._reply, Exception):
            raise self._reply
        if self._reply is None:
            return None
        return SimpleNamespace(data=SimpleNamespace(content=self._reply))

    async def destroy(self):
        self.destroyed = True
        self._log.append(("destroy",))


class _FakeClient:
    """Meniru copilot.CopilotClient sejauh yang dipakai klien kita."""

    instances = []

    def __init__(self, options):
        self.options = options
        self.started = False
        self.stopped = False
        self.sessions = []
        self.log = []
        self.reply = "jawaban"
        _FakeClient.instances.append(self)

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True
        return []

    async def get_auth_status(self):
        return SimpleNamespace(isAuthenticated=True, authType="user",
                               login="andiagung0", host="https://github.com")

    async def create_session(self, config):
        self.log.append(("create_session", config))
        session = _FakeSession(self.reply, self.log)
        self.sessions.append(session)
        return session


@pytest.fixture
def fake_sdk(monkeypatch, tmp_path):
    """Pasang SDK palsu dan runtime baru untuk tiap tes."""
    _FakeClient.instances.clear()
    monkeypatch.setattr(cc, "CopilotClient", _FakeClient)
    monkeypatch.setattr(cc, "_runtime", cc._Runtime())
    monkeypatch.setenv("COPILOT_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.delenv("COPILOT_DISABLED", raising=False)
    monkeypatch.delenv("COPILOT_MODEL", raising=False)
    monkeypatch.delenv("COPILOT_MAX_CONCURRENCY", raising=False)
    yield _FakeClient
    cc._runtime.stop()


def _client():
    return _FakeClient.instances[-1]


class TestConfiguration:
    def test_disabled_by_env_returns_none_without_starting_cli(self, fake_sdk, monkeypatch):
        monkeypatch.setenv("COPILOT_DISABLED", "1")
        assert cc.is_configured() is False
        assert cc.generate("halo") is None
        assert cc.status() is None
        assert fake_sdk.instances == []

    def test_missing_sdk_is_not_configured(self, fake_sdk, monkeypatch):
        monkeypatch.setattr(cc, "CopilotClient", None)
        assert cc.is_configured() is False
        assert cc.generate("halo") is None

    def test_cli_started_with_separate_config_dir(self, fake_sdk, tmp_path):
        cc.generate("halo")
        opts = _client().options
        assert opts["cli_args"] == ["--config-dir", str(tmp_path / "cfg")]
        assert opts["use_logged_in_user"] is True
        assert (tmp_path / "cfg").is_dir()

    def test_cli_path_env_is_forwarded(self, fake_sdk, monkeypatch):
        monkeypatch.setenv("COPILOT_CLI_PATH", "/opt/copilot")
        cc.generate("halo")
        assert _client().options["cli_path"] == "/opt/copilot"


class TestGenerate:
    def test_returns_text_and_prefixed_model_id(self, fake_sdk):
        assert cc.generate("halo") == ("jawaban", f"copilot:{cc.DEFAULT_MODEL}")

    def test_explicit_model_and_env_default(self, fake_sdk, monkeypatch):
        monkeypatch.setenv("COPILOT_MODEL", "claude-sonnet-5")
        assert cc.generate("halo")[1] == "copilot:claude-sonnet-5"
        assert cc.generate("halo", model="gpt-5")[1] == "copilot:gpt-5"
        configs = [e[1] for e in _client().log if e[0] == "create_session"]
        assert [c["model"] for c in configs] == ["claude-sonnet-5", "gpt-5"]

    def test_session_has_no_tools_and_replaces_system_prompt(self, fake_sdk):
        cc.generate("halo", system="Kamu asisten.")
        config = _client().log[0][1]
        assert config["available_tools"] == cc.NO_TOOLS
        assert config["system_message"] == {"mode": "replace", "content": "Kamu asisten."}
        assert config["on_permission_request"](None, None)["kind"].startswith("denied")

    def test_no_system_prompt_keeps_cli_default(self, fake_sdk):
        cc.generate("halo")
        assert "system_message" not in _client().log[0][1]

    def test_json_mode_appends_same_instruction_as_copilotd(self, fake_sdk):
        cc.generate("halo", system="Sistem.", json_mode=True)
        cc.generate("halo", json_mode=True)
        configs = [e[1] for e in _client().log if e[0] == "create_session"]
        assert configs[0]["system_message"]["content"] == f"Sistem.\n\n{cc.JSON_INSTRUCTION}"
        assert configs[1]["system_message"]["content"] == cc.JSON_INSTRUCTION

    def test_timeout_is_passed_to_sdk(self, fake_sdk):
        cc.generate("halo", timeout=42.0)
        assert _client().log[1] == ("send", "halo", 42.0)

    def test_session_destroyed_after_success(self, fake_sdk):
        cc.generate("halo")
        assert _client().sessions[0].destroyed is True

    def test_session_destroyed_after_failure(self, fake_sdk):
        cc.generate("halo")
        _client().reply = RuntimeError("Session error: Failed to get token")
        assert cc.generate("halo") is None
        assert all(s.destroyed for s in _client().sessions)

    def test_empty_or_missing_reply_returns_none(self, fake_sdk):
        cc.generate("halo")
        _client().reply = None
        assert cc.generate("halo") is None
        _client().reply = "   "
        assert cc.generate("halo") is None

    def test_asyncio_timeout_returns_none(self, fake_sdk):
        cc.generate("halo")
        _client().reply = asyncio.TimeoutError("Timeout after 5s")
        assert cc.generate("halo", timeout=5) is None

    def test_cli_start_failure_returns_none_and_allows_retry(self, fake_sdk, monkeypatch):
        async def boom(self):
            raise RuntimeError("Copilot CLI not found")
        original = fake_sdk.start
        monkeypatch.setattr(fake_sdk, "start", boom)
        assert cc.generate("halo") is None
        monkeypatch.setattr(fake_sdk, "start", original)
        assert cc.generate("halo") == ("jawaban", f"copilot:{cc.DEFAULT_MODEL}")

    def test_temperature_and_tier_accepted_but_not_sent(self, fake_sdk):
        """Copilot tidak mengekspos temperature; parameter hanya kompatibilitas."""
        cc.generate("halo", temperature=0, tier="cheap")
        config = _client().log[0][1]
        assert "temperature" not in config and "tier" not in config


class TestRuntime:
    def test_single_cli_shared_across_threads(self, fake_sdk):
        with ThreadPoolExecutor(6) as pool:
            results = list(pool.map(lambda i: cc.generate(f"p{i}"), range(12)))
        assert all(r == ("jawaban", f"copilot:{cc.DEFAULT_MODEL}") for r in results)
        assert len(fake_sdk.instances) == 1
        assert len(_client().sessions) == 12

    def test_concurrency_is_bounded_by_env(self, fake_sdk, monkeypatch):
        monkeypatch.setenv("COPILOT_MAX_CONCURRENCY", "2")
        peak = {"now": 0, "max": 0}
        gate = threading.Lock()
        original = _FakeSession.send_and_wait

        async def slow(self, options, timeout=None):
            with gate:
                peak["now"] += 1
                peak["max"] = max(peak["max"], peak["now"])
            await asyncio.sleep(0.05)
            with gate:
                peak["now"] -= 1
            return await original(self, options, timeout)

        monkeypatch.setattr(_FakeSession, "send_and_wait", slow)
        with ThreadPoolExecutor(6) as pool:
            list(pool.map(lambda i: cc.generate(f"p{i}"), range(6)))
        assert peak["max"] == 2

    def test_status_reports_auth_and_config(self, fake_sdk, tmp_path):
        st = cc.status()
        assert st["ok"] is True and st["login"] == "andiagung0"
        assert st["backend"] == "copilot-sdk"
        assert st["config_dir"] == str(tmp_path / "cfg")

    def test_stop_shuts_cli_down_and_is_idempotent(self, fake_sdk):
        cc.generate("halo")
        cc.stop()
        assert _client().stopped is True
        cc.stop()  # tidak boleh melempar
        # Setelah stop, panggilan berikutnya menyalakan CLI baru.
        assert cc.generate("halo") is not None
        assert len(fake_sdk.instances) == 2
