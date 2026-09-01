"""GROBID client (optional) for high-quality paper metadata + IMRaD structure.

GROBID (https://github.com/kermitt2/grobid) turns a scholarly PDF into TEI XML
with a real title, authors, year, DOI, abstract, and section structure — far
better than header heuristics (spec TAHAP 1 bagian A).

It runs as a separate service. This client is a thin sync wrapper: set
``GROBID_URL`` (e.g. ``http://localhost:8070``) to enable it. When it is unset or
the service is unreachable, callers fall back to CrossRef/regex — so the pipeline
degrades gracefully in environments without a GROBID server.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from loguru import logger

try:
    from lxml import etree
except ImportError:  # pragma: no cover - lxml is in requirements
    etree = None

_TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def _grobid_url() -> str:
    return (os.getenv("GROBID_URL") or "").rstrip("/")


def is_configured() -> bool:
    return bool(_grobid_url())


class GrobidClient:
    """Sync client for GROBID's ``processFulltextDocument`` endpoint."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 120.0):
        self.base_url = (base_url or _grobid_url()).rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        if not self.base_url or etree is None:
            return False
        try:
            r = requests.get(f"{self.base_url}/api/isalive", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def process_fulltext(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """Return parsed metadata + sections, or None on any failure."""
        if not self.base_url or etree is None:
            return None
        try:
            with open(pdf_path, "rb") as fh:
                files = {"input": (Path(pdf_path).name, fh, "application/pdf")}
                data = {
                    "consolidateHeader": "1",
                    "consolidateCitations": "0",
                    "segmentSentences": "0",
                }
                r = requests.post(
                    f"{self.base_url}/api/processFulltextDocument",
                    files=files,
                    data=data,
                    timeout=self.timeout,
                )
            if r.status_code != 200:
                logger.warning(f"GROBID returned HTTP {r.status_code} for {pdf_path}")
                return None
            return self._parse_tei(r.content)
        except requests.RequestException as e:
            logger.warning(f"GROBID request failed for {pdf_path}: {e}")
            return None
        except Exception as e:  # malformed XML, IO error, ...
            logger.warning(f"GROBID processing failed for {pdf_path}: {e}")
            return None

    # ---- TEI parsing -------------------------------------------------

    def _parse_tei(self, xml_bytes: bytes) -> Dict[str, Any]:
        root = etree.fromstring(xml_bytes)

        title = self._xtext(root, ".//tei:titleStmt/tei:title[@type='main']") or \
            self._xtext(root, ".//tei:sourceDesc//tei:analytic/tei:title")
        doi = self._xtext(root, ".//tei:sourceDesc//tei:idno[@type='DOI']") or \
            self._xtext(root, ".//tei:idno[@type='DOI']")
        year = self._extract_year(root)
        authors = self._extract_authors(root)
        abstract = self._extract_abstract(root)
        sections = self._extract_sections(root)

        return {
            "title": (title or "").strip() or None,
            "doi": (doi or "").strip().lower() or None,
            "year": year,
            "authors": authors,
            "abstract": abstract,
            "sections": sections,
        }

    def _xtext(self, node, xpath: str) -> Optional[str]:
        found = node.xpath(xpath, namespaces=_TEI_NS)
        if not found:
            return None
        el = found[0]
        return "".join(el.itertext()).strip() if hasattr(el, "itertext") else str(el).strip()

    def _extract_year(self, root) -> Optional[int]:
        for xp in (
            ".//tei:publicationStmt/tei:date[@type='published']/@when",
            ".//tei:sourceDesc//tei:monogr//tei:imprint/tei:date/@when",
            ".//tei:sourceDesc//tei:monogr//tei:imprint/tei:date[@type='published']/@when",
        ):
            vals = root.xpath(xp, namespaces=_TEI_NS)
            for v in vals:
                m = re.search(r"(19|20)\d{2}", str(v))
                if m:
                    return int(m.group(0))
        return None

    def _extract_authors(self, root) -> List[str]:
        authors: List[str] = []
        persons = root.xpath(
            ".//tei:sourceDesc//tei:analytic/tei:author/tei:persName",
            namespaces=_TEI_NS,
        )
        for p in persons:
            forenames = p.xpath("tei:forename/text()", namespaces=_TEI_NS)
            surname = p.xpath("tei:surname/text()", namespaces=_TEI_NS)
            name = " ".join([*forenames, *surname]).strip()
            if name:
                authors.append(re.sub(r"\s+", " ", name))
        # de-dup preserving order
        seen = set()
        uniq = []
        for a in authors:
            if a.lower() not in seen:
                seen.add(a.lower())
                uniq.append(a)
        return uniq

    def _extract_abstract(self, root) -> Optional[str]:
        node = root.xpath(".//tei:profileDesc/tei:abstract", namespaces=_TEI_NS)
        if not node:
            return None
        text = " ".join(node[0].itertext())
        text = re.sub(r"\s+", " ", text).strip()
        return text or None

    def _extract_sections(self, root) -> List[Tuple[str, str]]:
        """Return ``(head, body)`` pairs from ``<body><div>`` elements."""
        sections: List[Tuple[str, str]] = []
        for div in root.xpath(".//tei:body/tei:div", namespaces=_TEI_NS):
            head = div.xpath("tei:head", namespaces=_TEI_NS)
            head_text = ("".join(head[0].itertext()).strip() if head else "").strip()
            paras = div.xpath("tei:p", namespaces=_TEI_NS)
            body_text = "\n".join(
                re.sub(r"\s+", " ", "".join(p.itertext())).strip() for p in paras
            ).strip()
            if body_text:
                sections.append((head_text or "", body_text))
        return sections


if __name__ == "__main__":  # pragma: no cover
    c = GrobidClient()
    print("configured:", is_configured(), "url:", c.base_url or "(none)")
    print("available:", c.is_available())
