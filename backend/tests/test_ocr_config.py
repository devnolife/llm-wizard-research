"""Tests for the ocrd-first document extraction flow and the OcrdClient."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.utils import document_processor as dp_module
from app.utils.document_processor import DocumentProcessor
from app.utils.ocr_client import OcrdClient, OcrdResult


class _FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class _FakePdfReader:
    def __init__(self, _path):
        self.pages = [_FakePage("native pypdf text " * 10)]


# --------------------------------------------------------------- pipeline

def test_ocrd_result_is_used_first_when_service_ready():
    processor = DocumentProcessor(ocr_enabled=True)
    client = MagicMock()
    client.is_available.return_value = True
    client.read_document.return_value = OcrdResult(
        text="# BAB I\n\nteks hasil OCR", from_text_layer=False
    )
    processor._ocr_client = client

    text, method = processor._extract_text_from_pdf("dummy.pdf")

    assert method == "ocr"
    assert "teks hasil OCR" in text
    client.read_document.assert_called_once_with("dummy.pdf")


def test_text_layer_pdf_is_labeled_ocrd_text_layer():
    processor = DocumentProcessor(ocr_enabled=True)
    client = MagicMock()
    client.is_available.return_value = True
    client.read_document.return_value = OcrdResult(
        text="teks dari layer PDF", from_text_layer=True
    )
    processor._ocr_client = client

    text, method = processor._extract_text_from_pdf("dummy.pdf")

    assert method == "ocrd_text_layer"
    assert text == "teks dari layer PDF"


def test_falls_back_to_pypdf_when_service_not_ready(monkeypatch):
    monkeypatch.setattr(dp_module, "PdfReader", _FakePdfReader)
    processor = DocumentProcessor(ocr_enabled=True)
    client = MagicMock()
    client.is_available.return_value = False
    processor._ocr_client = client

    text, method = processor._extract_text_from_pdf("dummy.pdf")

    assert method == "pypdf"
    assert "native pypdf text" in text
    client.read_document.assert_not_called()


def test_falls_back_to_pypdf_when_ocrd_request_fails(monkeypatch):
    monkeypatch.setattr(dp_module, "PdfReader", _FakePdfReader)
    processor = DocumentProcessor(ocr_enabled=True)
    client = MagicMock()
    client.is_available.return_value = True
    client.read_document.return_value = None  # ocrd failed / empty output
    processor._ocr_client = client

    text, method = processor._extract_text_from_pdf("dummy.pdf")

    assert method == "pypdf"
    assert "native pypdf text" in text


def test_ocr_disabled_goes_straight_to_pypdf(monkeypatch):
    monkeypatch.setattr(dp_module, "PdfReader", _FakePdfReader)
    processor = DocumentProcessor(ocr_enabled=False)

    text, method = processor._extract_text_from_pdf("dummy.pdf")

    assert method == "pypdf"
    assert processor.ocr_client is None


# ----------------------------------------------------------------- client

def _response(status_code=200, payload=None, text=""):
    resp = SimpleNamespace(status_code=status_code, text=text)
    if payload is not None:
        resp.json = lambda: payload
    else:
        def _raise():
            raise ValueError("no json")
        resp.json = _raise
    return resp


def test_is_available_requires_model_ready():
    client = OcrdClient(service_url="http://ocr.test")
    client._session = MagicMock()
    client._session.get.return_value = _response(
        payload={"ok": True, "model_ready": False}
    )

    assert client.is_available(force=True) is False


def test_is_available_true_when_model_ready():
    client = OcrdClient(service_url="http://ocr.test")
    client._session = MagicMock()
    client._session.get.return_value = _response(
        payload={"ok": True, "model_ready": True}
    )

    assert client.is_available(force=True) is True


def test_read_document_parses_success_payload(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    client = OcrdClient(service_url="http://ocr.test", api_key="secret")
    client._session = MagicMock()
    client._session.post.return_value = _response(
        payload={
            "text": "BAB V\n\nPENUTUP",
            "from_text_layer": True,
            "page_count": 6,
            "duration_ms": 12,
            "engine": "Unlimited-OCR",
            "image_mode": "gundam",
            "pages": [],
        }
    )

    result = client.read_document(str(pdf))

    assert result is not None
    assert result.text.startswith("BAB V")
    assert result.from_text_layer is True
    assert result.page_count == 6
    kwargs = client._session.post.call_args.kwargs
    assert kwargs["headers"] == {"X-API-Key": "secret"}
    assert kwargs["data"]["prefer_text_layer"] == "true"


def test_read_document_returns_none_on_http_error(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    client = OcrdClient(service_url="http://ocr.test")
    client._session = MagicMock()
    client._session.post.return_value = _response(
        status_code=503, payload={"detail": "model not ready"}
    )

    assert client.read_document(str(pdf)) is None


def test_read_document_returns_none_on_empty_text(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    client = OcrdClient(service_url="http://ocr.test")
    client._session = MagicMock()
    client._session.post.return_value = _response(payload={"text": "   "})

    assert client.read_document(str(pdf)) is None
