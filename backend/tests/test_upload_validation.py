import io

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.utils.upload_validation import sanitize_filename, validate_pdf_upload


def make_upload(filename, content):
    return UploadFile(file=io.BytesIO(content), filename=filename)


def test_sanitize_filename_removes_traversal_and_controls():
    assert sanitize_filename("../../evil\x00\n file.pdf") == "evil file.pdf"


def test_sanitize_filename_falls_back_when_empty():
    assert sanitize_filename("\x00\n\t") == "upload.pdf"


def test_sanitize_filename_caps_long_names():
    safe = sanitize_filename(f"{'a' * 150}.pdf")
    assert len(safe) == 100
    assert safe.endswith(".pdf")


def test_sanitize_filename_keeps_unicode_printable_name():
    assert sanitize_filename(" riset tesis 你好.pdf ") == "riset tesis 你好.pdf"


def test_validate_pdf_upload_accepts_pdf_magic_and_resets_stream():
    upload = make_upload("paper.pdf", b"%PDF-1.7\nbody")
    validate_pdf_upload(upload, max_mb=1)
    assert upload.file.tell() == 0


def test_validate_pdf_upload_rejects_bad_extension():
    upload = make_upload("paper.txt", b"%PDF-1.7\nbody")
    with pytest.raises(HTTPException) as exc:
        validate_pdf_upload(upload, max_mb=1)
    assert exc.value.status_code == 415


def test_validate_pdf_upload_rejects_bad_magic():
    upload = make_upload("paper.pdf", b"not a pdf")
    with pytest.raises(HTTPException) as exc:
        validate_pdf_upload(upload, max_mb=1)
    assert exc.value.status_code == 400


def test_validate_pdf_upload_rejects_oversize_file():
    upload = make_upload("paper.pdf", b"%PDF-1.7\nbody")
    with pytest.raises(HTTPException) as exc:
        validate_pdf_upload(upload, max_mb=0)
    assert exc.value.status_code == 413
