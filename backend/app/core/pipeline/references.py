"""Parser daftar pustaka per paper (Fase 3, tanpa LLM).

TAHAP 1 sudah MENANDAI chunk daftar pustaka (``is_reference`` via
``section_normalizer.classify_reference``), tetapi tidak pernah MEMISAHKAN
entri-entrinya. Modul ini memecah teks daftar pustaka menjadi entri, lalu
menurunkan satu ``key`` per entri agar dua paper yang mengutip karya yang sama
bisa dicocokkan (*bibliographic coupling*, ``gap_detection.citation_coupling``):

* DOI bila ada (dinormalisasi lewat ``metadata_resolver.extract_doi_candidates``,
  yang lebih memilih DOI artikel daripada DOI jurnal/ISSN);
* bila tidak: ``penulis_pertama|tahun|enam kata isi judul``.

Pemisahan memakai penanda yang paling dominan di teks: ``[12]``, ``12.`` di awal
baris, atau batas "penulis, inisial" untuk gaya author-year. Tidak ada klaim
akurasi bibliografis penuh — cukup untuk mengenali kesamaan referensi; entri
yang tidak terurai tetap dibawa (``key`` dari teks mentahnya) agar hitungan
referensi per paper tidak menyusut diam-diam.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .metadata_resolver import extract_doi_candidates
from .section_normalizer import looks_like_references

# Entri lebih pendek dari ini hampir pasti pecahan (nomor halaman, sisa baris).
MIN_ENTRY_CHARS = 25
# Berhenti mengembalikan entri setelah ini: daftar pustaka > 300 entri adalah buku/handbook.
MAX_ENTRIES = 300
# Ekor dokumen yang dipindai bila tidak ada chunk berlabel daftar pustaka.
TAIL_FRACTION = 0.15

_HEADING_RE = re.compile(
    r"(?im)^\s*(?:\d+\.?\s*)?(references?|bibliography|daftar\s+pustaka|works\s+cited|"
    r"referensi|kepustakaan)\s*:?\s*$"
)
_BRACKET_RE = re.compile(r"\[\s*(\d{1,3})\s*\]")
_NUMBERED_LINE_RE = re.compile(r"(?m)^\s*(\d{1,3})[.)]\s+(?=[A-Z\"“])")
# "… . Surname, A." — batas entri gaya author-year pada teks yang barisnya menyatu.
_AUTHOR_YEAR_BOUNDARY_RE = re.compile(
    r"(?<=[.\d])\s+(?=[A-Z][A-Za-z'’\-]{1,30},\s+(?:[A-Z]\.|[A-Z][a-z]+))"
)
_YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-4]\d)[a-z]?\b")
_LEADING_MARKER_RE = re.compile(r"^\s*(?:\[\s*\d{1,3}\s*\]|\d{1,3}[.)])\s*")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "in", "on", "to", "with", "by",
    "from", "at", "as", "is", "are", "its", "into", "using", "based", "via",
    "dan", "atau", "yang", "dalam", "pada", "untuk", "dari", "dengan", "di",
    "ke", "terhadap", "sebagai", "melalui", "berbasis",
}


@dataclass
class ReferenceEntry:
    """Satu entri daftar pustaka beserta kunci pencocokannya."""

    raw: str
    key: str
    doi: Optional[str] = None
    year: Optional[int] = None
    first_author: str = ""
    title_guess: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "key": self.key,
            "doi": self.doi,
            "year": self.year,
            "first_author": self.first_author,
            "title_guess": self.title_guess,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReferenceEntry":
        return cls(
            raw=str(data.get("raw") or ""),
            key=str(data.get("key") or ""),
            doi=data.get("doi") or None,
            year=int(data["year"]) if data.get("year") else None,
            first_author=str(data.get("first_author") or ""),
            title_guess=str(data.get("title_guess") or ""),
        )


def _clean(text: str) -> str:
    return " ".join((text or "").replace("\u00ad", "").split())


def content_words(text: str, limit: int = 6) -> List[str]:
    """Kata-isi (>= 4 huruf, tanpa stopword) untuk kunci judul — juga dipakai
    ``citation_coupling`` mencocokkan judul paper unggahan ke entri pustaka."""
    words = [w for w in re.findall(r"[a-z][a-z\-]{3,}", (text or "").lower())
             if w not in _STOPWORDS]
    return words[:limit]


def split_reference_entries(text: str) -> List[str]:
    """Pecah teks daftar pustaka menjadi entri mentah, dari penanda yang dominan."""
    if not text or not text.strip():
        return []
    body = text
    heading = list(_HEADING_RE.finditer(body))
    if heading:
        body = body[heading[-1].end():]

    entries: List[str] = []
    brackets = list(_BRACKET_RE.finditer(body))
    numbered = list(_NUMBERED_LINE_RE.finditer(body))
    if len(brackets) >= 3:
        # "[n]" bisa muncul di tengah baris (PDF menyatukan baris); potong pada tiap penanda.
        starts = [m.start() for m in brackets]
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(body)
            entries.append(body[start:end])
    elif len(numbered) >= 3:
        starts = [m.start() for m in numbered]
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(body)
            entries.append(body[start:end])
    else:
        # Gaya author-year: satu entri per baris kosong / baris baru yang diawali nama,
        # dengan cadangan pemisah "…. Surname, A." untuk teks yang barisnya menyatu.
        paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
        if len(paragraphs) < 3:
            lines = [ln for ln in body.splitlines() if ln.strip()]
            paragraphs = lines if len(lines) >= 3 else [body]
        for para in paragraphs:
            pieces = _AUTHOR_YEAR_BOUNDARY_RE.split(para) if len(para) > 400 else [para]
            entries.extend(pieces)

    cleaned: List[str] = []
    seen = set()
    for entry in entries:
        item = _clean(entry)
        if len(item) < MIN_ENTRY_CHARS:
            continue
        # Kunci dedup tanpa nomor urut: "[2] X" dan "[3] X" adalah entri yang sama.
        low = _LEADING_MARKER_RE.sub("", item).lower()
        if low in seen:
            continue
        seen.add(low)
        cleaned.append(item)
        if len(cleaned) >= MAX_ENTRIES:
            break
    return cleaned


def _first_author(text: str) -> str:
    head = _LEADING_MARKER_RE.sub("", text)
    # "Surname, A. B." (APA) atau "A. Surname," (IEEE): ambil kata alfabet >= 2 huruf
    # pertama, melewati inisial berpisah titik.
    for match in re.finditer(r"([A-Z][A-Za-z'’\-]{1,40})", head[:80]):
        token = match.group(1)
        if len(token) < 2:
            continue
        surname = token.lower().replace("’", "'")
        if surname in {"in", "the", "a", "an", "proceedings", "ieee", "acm", "et"}:
            continue
        return surname
    return ""


def _title_guess(text: str, year_match: Optional[re.Match]) -> str:
    body = _LEADING_MARKER_RE.sub("", text)
    candidate = ""
    if year_match:
        after = body[year_match.end():] if year_match.end() <= len(body) else ""
        after = after.lstrip(" ).:,;-—–\"“”")
        segments = [s.strip() for s in re.split(r"(?<=[.?!])\s+|[.]\s*$", after) if s.strip()]
        candidate = segments[0] if segments else ""
    if len(content_words(candidate)) < 3:
        # Tanpa tahun (atau judul sebelum tahun): segmen terpanjang yang bukan nama.
        segments = [s.strip() for s in re.split(r"(?<=[.?!])\s+", body) if s.strip()]
        segments = [s for s in segments if len(content_words(s)) >= 3]
        candidate = max(segments, key=len) if segments else candidate
    return candidate[:200]


def parse_reference(raw: str) -> ReferenceEntry:
    """Turunkan DOI/tahun/penulis/judul dan kunci pencocokan dari satu entri."""
    text = _clean(raw)
    dois = extract_doi_candidates(text)
    doi = dois[0] if dois else None
    year_match = None
    for m in _YEAR_RE.finditer(text):
        year_match = m
        # Tahun dalam kurung adalah tahun terbit; tahun lain (volume/halaman) diabaikan.
        if m.start() > 0 and text[m.start() - 1] == "(":
            break
    year = int(year_match.group(1)) if year_match else None
    author = _first_author(text)
    title = _title_guess(text, year_match)
    if doi:
        key = doi
    else:
        words = content_words(title)
        if author or words:
            key = f"{author}|{year or ''}|{' '.join(words)}"
        else:
            key = f"raw|{re.sub(r'[^a-z0-9]+', ' ', text.lower())[:60].strip()}"
    return ReferenceEntry(raw=text, key=key, doi=doi, year=year,
                          first_author=author, title_guess=title)


def _chunk_fields(chunk: Any):
    if isinstance(chunk, Mapping):
        meta = chunk.get("metadata") or chunk
        text = chunk.get("text") or chunk.get("content") or ""
    else:
        meta = getattr(chunk, "metadata", None) or {}
        text = getattr(chunk, "content", "") or getattr(chunk, "text", "") or ""
    section = str(meta.get("section_normalized") or "").lower()
    return str(text), section, bool(meta.get("is_reference"))


def _has_entry_markers(text: str) -> bool:
    """>= 3 penanda entri bernomor — cukup untuk mempercayai ekor berjudul 'References'
    walau heuristik kepadatan sitasi TAHAP 1 tidak yakin (baris PDF yang menyatu)."""
    return len(_BRACKET_RE.findall(text)) >= 3 or len(_NUMBERED_LINE_RE.findall(text)) >= 3


def reference_text(chunks: Sequence[Any], full_text: str = "") -> str:
    """Teks daftar pustaka: chunk berlabel referensi; kalau tidak ada, ekor dokumen
    (dari judul 'References/Daftar Pustaka' terakhir, atau 15% terakhir bila tidak ada)."""
    picked = [text for text, section, is_ref in map(_chunk_fields, chunks or [])
              if (is_ref or section == "references") and text.strip()]
    if picked:
        return "\n".join(picked)
    if not full_text:
        return ""
    heading = list(_HEADING_RE.finditer(full_text))
    if heading:
        tail = full_text[heading[-1].start():]
        return tail if (looks_like_references(tail) or _has_entry_markers(tail)) else ""
    tail = full_text[int(len(full_text) * (1 - TAIL_FRACTION)):]
    return tail if looks_like_references(tail) else ""


def extract_references(chunks: Sequence[Any], full_text: str = "") -> List[ReferenceEntry]:
    """Daftar pustaka satu paper sebagai entri terurai (kosong bila tidak terdeteksi)."""
    return [parse_reference(e) for e in split_reference_entries(reference_text(chunks, full_text))]
