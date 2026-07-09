"""
Shared upload validation helpers.
"""

import os
import re
import unicodedata
from pathlib import Path

from fastapi import HTTPException, UploadFile


PDF_MAGIC = b"%PDF-"
CHUNK_SIZE = 1024 * 1024


def sanitize_filename(name: str | None) -> str:
    """Return a safe, short filename suitable for local temporary storage."""
    filename = os.path.basename((name or "").replace("\\", "/"))
    filename = filename.replace("\x00", "")
    filename = "".join(ch for ch in filename if ch.isprintable())
    filename = unicodedata.normalize("NFKC", filename)
    filename = re.sub(r"\s+", " ", filename).strip()
    filename = filename.lstrip(".")

    if not filename:
        return "upload.pdf"

    if len(filename) > 100:
        path = Path(filename)
        suffix = path.suffix[:20]
        stem_limit = max(1, 100 - len(suffix))
        filename = f"{path.stem[:stem_limit]}{suffix}"

    return filename or "upload.pdf"


def _max_bytes(max_mb: int) -> int:
    return int(max_mb) * 1024 * 1024


def validate_pdf_upload(file: UploadFile, max_mb: int) -> None:
    """Validate extension, PDF header, and size for an UploadFile."""
    safe_name = sanitize_filename(file.filename)
    if not safe_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail=f"File {safe_name} is not a supported PDF")

    stream = file.file
    try:
        stream.seek(0)
        header = stream.read(len(PDF_MAGIC))
        if header != PDF_MAGIC:
            raise HTTPException(status_code=400, detail=f"File {safe_name} is not a valid PDF")

        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        if size > _max_bytes(max_mb):
            raise HTTPException(status_code=413, detail=f"File {safe_name} exceeds {max_mb} MB limit")
    finally:
        stream.seek(0)


async def write_validated_pdf_upload(file: UploadFile, destination: Path, max_mb: int) -> None:
    """Validate and stream an uploaded PDF to destination with size enforcement."""
    validate_pdf_upload(file, max_mb)

    limit = _max_bytes(max_mb)
    total = 0
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(destination, "wb") as out:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File {sanitize_filename(file.filename)} exceeds {max_mb} MB limit",
                    )
                out.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.seek(0)
