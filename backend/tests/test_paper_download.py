"""Contract tests for legal OA paper download + analyze queueing (no network)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.routes import papers
from app.main import app
from app.services.paper_apis.unpaywall import UnpaywallAPI
from app.utils import job_store


@pytest.fixture(autouse=True)
def isolated_job_store(tmp_path):
    job_store.load_jobs(tmp_path / "analysis_jobs.sqlite3")
    yield


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def isolated_raw_path(tmp_path, monkeypatch):
    """Keep downloaded files inside tmp and avoid touching the real config."""
    fake_config = SimpleNamespace(
        data=SimpleNamespace(max_file_size_mb=50, raw_path=str(tmp_path / "raw")),
        queue=SimpleNamespace(max_attempts=2),
    )
    monkeypatch.setattr(papers, "get_config", lambda: fake_config)
    yield


# ── Unpaywall client ─────────────────────────────────────────────────────────

def test_unpaywall_extract_pdf_url_prefers_best_location():
    record = {
        "is_oa": True,
        "best_oa_location": {"url_for_pdf": "https://repo.example/best.pdf"},
        "oa_locations": [{"url_for_pdf": "https://repo.example/other.pdf"}],
    }
    assert UnpaywallAPI.extract_pdf_url(record) == "https://repo.example/best.pdf"


def test_unpaywall_extract_pdf_url_falls_back_to_pdf_page_url():
    record = {
        "is_oa": True,
        "best_oa_location": {"url_for_pdf": None, "url": "https://repo.example/page"},
        "oa_locations": [{"url_for_pdf": None, "url": "https://repo.example/copy.PDF"}],
    }
    assert UnpaywallAPI.extract_pdf_url(record) == "https://repo.example/copy.PDF"


@pytest.mark.asyncio
async def test_unpaywall_resolve_pdf_requires_oa(monkeypatch):
    api = UnpaywallAPI(email="test@unhas.ac.id")

    async def fake_lookup(doi):
        return {"is_oa": False, "best_oa_location": {"url_for_pdf": "https://x/y.pdf"}}

    monkeypatch.setattr(api, "lookup", fake_lookup)
    assert await api.resolve_pdf("10.1/x") is None


# ── download-and-analyze endpoint ────────────────────────────────────────────

def _fake_download(content: bytes = b"%PDF-1.4 fake"):
    async def fake(session, url, destination, max_mb):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    return fake


@pytest.mark.api
def test_download_and_analyze_queues_job_and_skips_non_oa(client, monkeypatch, tmp_path):
    monkeypatch.setattr(papers, "_download_pdf", _fake_download())

    response = client.post("/api/papers/download-and-analyze", json={
        "papers": [
            {"title": "Paper OA Langsung", "pdf_url": "https://arxiv.org/pdf/1234.pdf",
             "source_api": "arxiv"},
            {"title": "Paper Berbayar", "doi": None, "pdf_url": None,
             "source_api": "sciencedirect"},
        ]
    })

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["downloaded"]) == 1
    assert body["downloaded"][0]["via"] == "pdf_url"
    assert len(body["skipped"]) == 1
    assert "unduh manual" in body["skipped"][0]["reason"].lower()

    job = job_store.get_job(body["job_id"])
    assert job is not None and job["status"] == "queued"
    pdf_paths = job["payload"]["pdf_paths"]
    assert len(pdf_paths) == 1
    assert pdf_paths[0].startswith(str(tmp_path / "raw"))
    with open(pdf_paths[0], "rb") as fh:
        assert fh.read(5) == b"%PDF-"


@pytest.mark.api
def test_download_and_analyze_resolves_doi_via_unpaywall(client, monkeypatch):
    monkeypatch.setattr(papers, "_download_pdf", _fake_download())

    async def fake_resolve(self, doi):
        assert doi == "10.5555/oa-copy"
        return "https://repository.example/oa-copy.pdf"

    monkeypatch.setattr(papers.UnpaywallAPI, "resolve_pdf", fake_resolve)

    response = client.post("/api/papers/download-and-analyze", json={
        "papers": [{"title": "Paper Lewat Unpaywall", "doi": "10.5555/oa-copy"}]
    })

    body = response.json()
    assert body["success"] is True
    assert body["downloaded"][0]["via"] == "unpaywall"


@pytest.mark.api
def test_download_and_analyze_without_any_pdf_creates_no_job(client, monkeypatch):
    async def fake_resolve(self, doi):
        return None

    monkeypatch.setattr(papers.UnpaywallAPI, "resolve_pdf", fake_resolve)

    response = client.post("/api/papers/download-and-analyze", json={
        "papers": [{"title": "Semua Berbayar", "doi": "10.9/paywalled"}]
    })

    body = response.json()
    assert body["success"] is False
    assert body["job_id"] is None
    assert len(body["skipped"]) == 1
    assert job_store.list_jobs() == []


@pytest.mark.api
def test_download_and_analyze_failed_download_is_skipped(client, monkeypatch):
    async def failing(session, url, destination, max_mb):
        raise ValueError("bukan file PDF")

    monkeypatch.setattr(papers, "_download_pdf", failing)

    response = client.post("/api/papers/download-and-analyze", json={
        "papers": [{"title": "Rusak", "pdf_url": "https://x.example/broken.pdf"}]
    })

    body = response.json()
    assert body["success"] is False
    assert "Unduhan gagal" in body["skipped"][0]["reason"]


# ── idea-to-query endpoint ───────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def no_copilotd(monkeypatch):
    """Default: copilotd dianggap mati agar test deterministik (fallback GLM)."""
    monkeypatch.setattr(papers.copilot_client, "generate", lambda *a, **k: None)
    yield


@pytest.mark.api
def test_idea_to_query_prefers_copilot_when_available(client, monkeypatch):
    def fake_copilot(prompt, system="", json_mode=False, **kwargs):
        assert json_mode is True
        assert "struk" in prompt
        return ('{"query": "receipt OCR expense tracking", "keywords": ["receipt OCR"]}',
                "copilot:claude-sonnet-5")

    monkeypatch.setattr(papers.copilot_client, "generate", fake_copilot)

    def no_glm():
        raise AssertionError("GLM lokal tidak boleh dipanggil saat Copilot tersedia")

    monkeypatch.setattr(papers, "get_glm_interface", no_glm)

    response = client.post("/api/papers/idea-to-query", json={
        "idea": "Ekstraksi struk belanja otomatis dengan OCR"
    })

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "receipt OCR expense tracking"
    assert body["engine"] == "GitHub Copilot (claude-sonnet-5)"


@pytest.mark.api
def test_idea_to_query_converts_idea(client, monkeypatch):
    class FakeGLM:
        def generate(self, prompt, **kwargs):
            assert "struk belanja" in prompt
            return ('{"query": "receipt OCR (information AND extraction)", '
                    '"keywords": ["receipt OCR", "information extraction"]}')

    monkeypatch.setattr(papers, "get_glm_interface", lambda: FakeGLM())

    response = client.post("/api/papers/idea-to-query", json={
        "idea": "Sistem ekstraksi struk belanja otomatis dengan OCR dan LLM"
    })

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    # Boolean operators & tanda kurung dibersihkan
    assert body["query"] == "receipt OCR information extraction"
    assert body["keywords"] == ["receipt OCR", "information extraction"]


@pytest.mark.api
def test_idea_to_query_llm_down_returns_503(client, monkeypatch):
    def broken():
        raise RuntimeError("ollama down")

    monkeypatch.setattr(papers, "get_glm_interface", broken)

    response = client.post("/api/papers/idea-to-query", json={
        "idea": "Analisis sentimen ulasan aplikasi dompet digital Indonesia"
    })

    assert response.status_code == 503
    assert "kata kunci" in response.json()["detail"]


# ── fetch-pdf endpoint ───────────────────────────────────────────────────────

@pytest.mark.api
def test_fetch_pdf_returns_pdf_attachment(client, monkeypatch):
    monkeypatch.setattr(papers, "_download_pdf", _fake_download(b"%PDF-1.7 satu dokumen"))

    response = client.post("/api/papers/fetch-pdf", json={
        "title": "Paper Unduhan Tunggal", "pdf_url": "https://arxiv.org/pdf/9.pdf"
    })

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'filename="' in response.headers["content-disposition"]
    assert response.headers["x-download-via"] == "pdf_url"
    assert response.content.startswith(b"%PDF-")


@pytest.mark.api
def test_fetch_pdf_via_unpaywall_doi(client, monkeypatch):
    monkeypatch.setattr(papers, "_download_pdf", _fake_download())

    async def fake_resolve(self, doi):
        return "https://repo.example/oa.pdf"

    monkeypatch.setattr(papers.UnpaywallAPI, "resolve_pdf", fake_resolve)

    response = client.post("/api/papers/fetch-pdf", json={
        "title": "Lewat DOI", "doi": "10.1109/x"
    })

    assert response.status_code == 200
    assert response.headers["x-download-via"] == "unpaywall"


@pytest.mark.api
def test_fetch_pdf_no_oa_returns_404(client, monkeypatch):
    async def fake_resolve(self, doi):
        return None

    monkeypatch.setattr(papers.UnpaywallAPI, "resolve_pdf", fake_resolve)

    response = client.post("/api/papers/fetch-pdf", json={
        "title": "Berbayar", "doi": "10.9/paywalled"
    })

    assert response.status_code == 404
    assert "unduh manual" in response.json()["detail"].lower()
