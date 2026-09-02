"""Tests for the ocrd recovery path in the upgraded pipeline."""

import app.core.pipeline.pipeline as pipeline_mod
from app.core.pipeline.pipeline import _ocr_pages


class _FakeResult:
    def __init__(self, text="", pages=None, from_text_layer=False):
        self.text = text
        self.pages = pages or []
        self.from_text_layer = from_text_layer


class _FakeClient:
    """Stand-in for OcrdClient; records whether the service was actually called."""

    instances: list = []

    def __init__(self, available=True, result=None):
        self.available = available
        self.result = result
        self.read_calls = 0
        _FakeClient.instances.append(self)

    def is_available(self):
        return self.available

    def read_document(self, path):
        self.read_calls += 1
        return self.result


def _patch_client(monkeypatch, client):
    import app.utils.ocr_client as ocr_mod
    monkeypatch.setattr(ocr_mod, "OcrdClient", lambda *a, **k: client)


class TestOcrRecovery:
    def test_service_is_called_even_when_model_not_ready(self, monkeypatch):
        """ocrd memuat model saat permintaan pertama; is_available() akan
        memblokir pemulihan selamanya kalau dijadikan gerbang."""
        client = _FakeClient(available=False, result=_FakeResult(text="isi hasil ocr"))
        _patch_client(monkeypatch, client)
        pages, _ = _ocr_pages("/tmp/x.pdf")
        assert pages == ["isi hasil ocr"]
        assert client.read_calls == 1

    def test_disabled_by_env_skips_service_entirely(self, monkeypatch):
        monkeypatch.setenv("OCR_ENABLED", "false")
        client = _FakeClient(result=_FakeResult(text="halo"))
        _patch_client(monkeypatch, client)
        assert _ocr_pages("/tmp/x.pdf") is None
        assert client.read_calls == 0

    def test_uses_per_page_text_when_available(self, monkeypatch):
        client = _FakeClient(result=_FakeResult(
            text="gabungan",
            pages=[{"text": "halaman satu"}, {"text": "halaman dua"}],
        ))
        _patch_client(monkeypatch, client)
        pages, method = _ocr_pages("/tmp/x.pdf")
        assert pages == ["halaman satu", "halaman dua"]
        assert method == "ocrd_ocr"

    def test_falls_back_to_whole_text_when_pages_empty(self, monkeypatch):
        client = _FakeClient(result=_FakeResult(text="seluruh isi", pages=[{"text": ""}]))
        _patch_client(monkeypatch, client)
        pages, _ = _ocr_pages("/tmp/x.pdf")
        assert pages == ["seluruh isi"]

    def test_text_layer_hit_is_labelled_differently(self, monkeypatch):
        """Membedakan jalur cepat (lapisan teks) dari OCR GPU yang mahal."""
        client = _FakeClient(result=_FakeResult(text="isi", from_text_layer=True))
        _patch_client(monkeypatch, client)
        assert _ocr_pages("/tmp/x.pdf")[1] == "ocrd_text_layer"

    def test_none_result_is_propagated(self, monkeypatch):
        _patch_client(monkeypatch, _FakeClient(result=None))
        assert _ocr_pages("/tmp/x.pdf") is None


class TestGoodPdfNeverCallsOcr:
    def _sample_pdf(self):
        import glob
        pdfs = glob.glob(
            "../data/raw/analysis_jobs/d4eb6a1d-*/*.pdf") or glob.glob(
            "data/raw/analysis_jobs/d4eb6a1d-*/*.pdf")
        return sorted(pdfs)[0] if pdfs else None

    def test_healthy_pdf_skips_recovery(self, monkeypatch):
        """PDF digital harus tetap lewat pymupdf agar tidak ikut melambat."""
        pdf = self._sample_pdf()
        if not pdf:
            return
        calls = []
        monkeypatch.setattr(pipeline_mod, "_ocr_pages", lambda path: calls.append(path))
        monkeypatch.setattr(pipeline_mod, "assess_quality", lambda text: "good")
        pipeline_mod.process_pdf(pdf)
        assert calls == [], "PDF berkualitas baik tidak boleh memanggil ocrd"

    def test_poor_pdf_triggers_recovery_and_replaces_text(self, monkeypatch):
        pdf = self._sample_pdf()
        if not pdf:
            return
        seen = {}

        def _fake_ocr(path):
            seen["path"] = path
            return (["Teks hasil pemulihan OCR. " * 40], "ocrd_ocr")

        monkeypatch.setattr(pipeline_mod, "_ocr_pages", _fake_ocr)
        qualities = iter(["poor", "good"])
        monkeypatch.setattr(pipeline_mod, "assess_quality",
                            lambda text: next(qualities, "good"))

        result = pipeline_mod.process_pdf(pdf)
        assert seen.get("path") == pdf, "PDF buruk harus dikirim ke ocrd"
        assert result.extraction_method == "ocrd_ocr"
        assert "pemulihan OCR" in result.full_text
