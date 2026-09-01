"""
External paper API endpoints
"""

import json
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path

import aiohttp
from fastapi import APIRouter, HTTPException, Response
from loguru import logger
from typing import List, Dict, Any

from ...models.requests import (
    IdeaToQueryRequest,
    PaperSearchRequest,
    PaperToDownload,
    DownloadAnalyzeRequest,
)
from ...models.responses import PaperSearchResponse
from ...core.retrieval.vector_store import Document
from ...services import copilot_client
from ...services.analysis_queue import get_analysis_queue
from ...services.paper_apis import UnpaywallAPI
from ...utils.config_loader import get_config
from ...utils.job_store import record_job_event, save_job
from ...utils.upload_validation import sanitize_filename
from ..dependencies import get_vector_store, get_paper_api, get_glm_interface

router = APIRouter()

PDF_MAGIC = b"%PDF-"
_DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) WizardResearch/1.0 (academic research)",
    "Accept": "application/pdf,*/*",
}


def _normalize_pdf_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if url.startswith("//"):
        url = f"https:{url}"
    if not url.startswith(("http://", "https://")):
        return None
    return url


async def _download_pdf(session: aiohttp.ClientSession, url: str, destination: Path, max_mb: int) -> None:
    """Stream a PDF to disk, enforcing the PDF magic header and a size limit."""
    limit = max_mb * 1024 * 1024
    async with session.get(url, allow_redirects=True) as response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")
        total = 0
        first = b""
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(destination, "wb") as out:
                async for chunk in response.content.iter_chunked(1024 * 256):
                    if len(first) < len(PDF_MAGIC):
                        first += chunk[: len(PDF_MAGIC) - len(first)]
                        if len(first) >= len(PDF_MAGIC) and first != PDF_MAGIC:
                            raise ValueError("bukan file PDF (kemungkinan halaman web)")
                    total += len(chunk)
                    if total > limit:
                        raise ValueError(f"melebihi batas {max_mb} MB")
                    out.write(chunk)
            if first != PDF_MAGIC:
                raise ValueError("bukan file PDF")
        except Exception:
            destination.unlink(missing_ok=True)
            raise


_IDEA_SYSTEM_PROMPT = (
    "You turn research ideas into academic literature search queries. "
    "The idea may be written in Indonesian or English. Respond ONLY with JSON: "
    '{"query": "<MAXIMUM 6 English keywords, space separated, no boolean operators, no filler words>", '
    '"keywords": ["kw1", "kw2", ...]}. '
    "Keywords must be short English technical terms used in paper titles "
    "(translate Indonesian terms). Example query: 'receipt OCR information extraction'. "
    "No explanations."
)


@router.post("/idea-to-query")
def idea_to_query(request: IdeaToQueryRequest):
    """Ubah ide penelitian (Bahasa Indonesia/Inggris) menjadi kata kunci pencarian akademik.

    Memakai LLM lokal (Ollama) dengan output JSON. Hasil ``query`` siap dipakai
    di ``POST /papers/search``.
    """
    idea = request.idea.strip()
    try:
        engine = None
        raw = None
        # Coba GitHub Copilot (copilotd, akun enterprise user) lebih dulu —
        # kualitas terjemahan ide → istilah teknis jauh lebih baik.
        copilot_result = copilot_client.generate(
            f'Research idea: "{idea}"',
            system=_IDEA_SYSTEM_PROMPT,
            json_mode=True,
        )
        if copilot_result:
            raw, model_id = copilot_result
            engine = f"GitHub Copilot ({model_id.removeprefix('copilot:')})"
        else:
            glm = get_glm_interface()
            raw = glm.generate(
                f'Research idea: "{idea}"',
                system_prompt=_IDEA_SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=200,
                format="json",
            )
            engine = "LLM lokal (Ollama)"
        # Buang pagar markdown bila model membungkus JSON dengan ```...```
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        data = json.loads(raw)
        query = str(data.get("query") or "").strip()
        keywords = [str(k).strip() for k in (data.get("keywords") or []) if str(k).strip()]
        if not query and keywords:
            query = " ".join(keywords[:6])
        # Keep it a plain keyword query (strip quotes/booleans the LLM may sneak in)
        query = re.sub(r'["()]|\b(AND|OR|NOT)\b', " ", query)
        query = re.sub(r"\s+", " ", query).strip()
        # LLM kadang mengembalikan kalimat panjang; query AND-semua-kata jadi
        # terlalu sempit. Pakai gabungan keyword bila lebih ringkas.
        if keywords and len(query.split()) > 7:
            joined = re.sub(r'["()]|\b(AND|OR|NOT)\b', " ", " ".join(keywords[:3]))
            joined = re.sub(r"\s+", " ", joined).strip()
            if joined and len(joined.split()) < len(query.split()):
                query = joined
        if not query:
            raise ValueError("LLM returned an empty query")
        logger.info(f"Idea→query [{engine}]: '{idea[:60]}…' → '{query}'")
        return {"success": True, "query": query, "keywords": keywords[:8], "engine": engine}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"idea-to-query failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="LLM tidak tersedia untuk mengubah ide menjadi kata kunci. "
                   "Coba lagi, atau ketik kata kunci Inggris secara manual.",
        )


@router.post("/fetch-pdf")
async def fetch_pdf(paper: PaperToDownload):
    """Unduh SATU PDF open-access legal untuk paper ini dan kirim sebagai file.

    Pakai ``pdf_url`` bila ada; kalau kosong tetapi ada DOI, resolve versi
    open-access via Unpaywall. 404 bila tidak ada PDF legal.
    """
    config = get_config()
    max_mb = config.data.max_file_size_mb

    pdf_url = _normalize_pdf_url(paper.pdf_url)
    via = "pdf_url"
    if not pdf_url and paper.doi:
        pdf_url = _normalize_pdf_url(await UnpaywallAPI().resolve_pdf(paper.doi))
        via = "unpaywall"
    if not pdf_url:
        raise HTTPException(
            status_code=404,
            detail="Tidak ditemukan PDF open-access legal untuk paper ini — "
                   "unduh manual dari halaman publisher dengan akses kampus Anda.",
        )

    tmp_path = Path(tempfile.mkstemp(suffix=".pdf")[1])
    timeout = aiohttp.ClientTimeout(total=90)
    try:
        async with aiohttp.ClientSession(headers=_DOWNLOAD_HEADERS, timeout=timeout) as session:
            await _download_pdf(session, pdf_url, tmp_path, max_mb)
        data = tmp_path.read_bytes()
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"fetch-pdf gagal ({pdf_url}): {e}")
        raise HTTPException(status_code=502, detail=f"Gagal mengunduh PDF: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    filename = f"{sanitize_filename(paper.title.strip()) or 'paper'}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Download-Via": via,
        },
    )


@router.post("/download-and-analyze")
async def download_and_analyze(request: DownloadAnalyzeRequest):
    """Unduh PDF open-access dari paper terpilih lalu antrekan job analisis.

    Untuk tiap paper: pakai ``pdf_url`` bila ada; kalau kosong tetapi ada DOI,
    coba resolve versi open-access legal via Unpaywall. Paper tanpa PDF legal
    masuk daftar ``skipped`` (unduh manual lewat publisher).
    """
    config = get_config()
    max_mb = config.data.max_file_size_mb
    job_id = str(uuid.uuid4())
    job_dir = Path(config.data.raw_path) / "analysis_jobs" / job_id

    unpaywall = UnpaywallAPI()
    downloaded: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    input_paths: list[Path] = []

    timeout = aiohttp.ClientTimeout(total=90)
    async with aiohttp.ClientSession(headers=_DOWNLOAD_HEADERS, timeout=timeout) as session:
        for index, paper in enumerate(request.papers):
            title = paper.title.strip()
            pdf_url = _normalize_pdf_url(paper.pdf_url)
            via = "pdf_url"
            if not pdf_url and paper.doi:
                pdf_url = _normalize_pdf_url(await unpaywall.resolve_pdf(paper.doi))
                via = "unpaywall"
            if not pdf_url:
                skipped.append({
                    "title": title,
                    "reason": "Tidak ada PDF open-access — unduh manual dari publisher",
                    "doi": paper.doi,
                })
                continue

            stem = sanitize_filename(title)[:80].removesuffix(".pdf") or "paper"
            destination = job_dir / f"{index:02d}_{stem}.pdf"
            try:
                await _download_pdf(session, pdf_url, destination, max_mb)
            except Exception as exc:
                logger.warning(f"Download gagal untuk '{title}' ({pdf_url}): {exc}")
                skipped.append({
                    "title": title,
                    "reason": f"Unduhan gagal: {exc}",
                    "doi": paper.doi,
                    "pdf_url": pdf_url,
                })
                continue
            input_paths.append(destination)
            downloaded.append({
                "title": title,
                "file": destination.name,
                "via": via,
                "source_api": paper.source_api,
            })

    if not input_paths:
        if job_dir.is_dir():
            shutil.rmtree(job_dir, ignore_errors=True)
        return {
            "success": False,
            "job_id": None,
            "downloaded": downloaded,
            "skipped": skipped,
            "message": "Tidak ada PDF yang bisa diunduh secara legal dari pilihan ini",
        }

    save_job(job_id, {
        "status": "queued",
        "progress": 0,
        "message": "Menunggu worker analisis...",
        "results": None,
        "error": None,
        "created_at": time.time(),
        "max_attempts": config.queue.max_attempts,
        "payload": {
            "pdf_paths": [str(path) for path in input_paths],
            "input_dir": str(job_dir),
            "files": [{"name": path.name} for path in input_paths],
        },
    })
    record_job_event(job_id, "job.created", status="queued", data={
        "file_count": len(input_paths),
        "origin": "papers.download",
    })
    get_analysis_queue().notify()

    return {
        "success": True,
        "job_id": job_id,
        "downloaded": downloaded,
        "skipped": skipped,
        "message": f"{len(downloaded)} PDF diunduh; analisis diantrekan.",
    }


def clean_paper_metadata(paper) -> Dict[str, Any]:
    """Clean paper metadata by removing None values for ChromaDB compatibility"""
    metadata = {
        "title": paper.title or "Unknown",
        "authors": ", ".join(paper.authors) if paper.authors else "Unknown",
        "source_api": paper.source_api or "unknown",
    }
    
    # Add optional fields only if they have values
    if paper.year is not None:
        metadata["year"] = int(paper.year)
    if paper.journal:
        metadata["journal"] = str(paper.journal)
    if paper.doi:
        metadata["doi"] = str(paper.doi)
    if paper.url:
        metadata["url"] = str(paper.url)
    if paper.keywords:
        metadata["keywords"] = ", ".join(paper.keywords)
    if paper.citation_count is not None:
        metadata["citation_count"] = int(paper.citation_count)
    
    return metadata


@router.post("/search", response_model=PaperSearchResponse)
async def search_external_papers(request: PaperSearchRequest):
    """
    Search for research papers across multiple external APIs
    
    Supported sources:
    - arxiv: arXiv papers (no API key needed)
    - semantic_scholar: Semantic Scholar (optional API key for higher limits)
    - crossref: CrossRef database (optional email for faster responses)
    - pubmed: PubMed/NCBI (optional API key for higher limits)
    - core: CORE open access (API key recommended, 10K requests/day free)
    - europe_pmc: Europe PMC (no API key needed)
    - sciencedirect: Elsevier ScienceDirect (ELSEVIER_API_KEY + campus IP/insttoken)
    - scopus: Elsevier Scopus, 90M+ records all publishers (ELSEVIER_API_KEY only)
    """
    try:
        paper_api = get_paper_api()
        
        # Search across specified sources
        sources = request.sources or ["arxiv", "core", "crossref"]
        logger.info(f"Searching papers: '{request.query}' across {sources}")
        
        results = await paper_api.search_all(
            query=request.query,
            max_results_per_source=request.max_results,
            sources=sources,
            year_from=request.year_from,
            year_to=request.year_to
        )
        
        # Deduplicate if requested
        if request.deduplicate:
            papers = paper_api.deduplicate_papers(results, query=request.query)
            logger.info(f"Deduplicated to {len(papers)} unique papers")
        else:
            # Flatten all results
            papers = []
            for source_papers in results.values():
                papers.extend(source_papers)
        
        # Convert to dict format
        papers_dict = [paper.to_dict() for paper in papers]
        
        return PaperSearchResponse(
            query=request.query,
            total_results=len(papers_dict),
            papers=papers_dict,
            sources_searched=sources,
            embedding_model=request.embedding_model
        )
    
    except Exception as e:
        logger.error(f"Paper search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Paper search failed: {str(e)}")


@router.post("/ingest-external")
async def ingest_external_paper(
    paper_id: str,
    source: str = "semantic_scholar",
):
    """
    Fetch and ingest a specific paper from external API into the vector store
    
    Args:
        paper_id: Paper ID (e.g., DOI, arXiv ID, PubMed ID)
        source: Source API (semantic_scholar, arxiv, etc.)
    """
    try:
        paper_api = get_paper_api()
        vector_store = get_vector_store()
        
        logger.info(f"Fetching paper {paper_id} from {source}")
        
        # Fetch paper details based on source
        paper = None
        if source == "semantic_scholar":
            paper = await paper_api.semantic_scholar.get_paper_details(paper_id)
        elif source == "arxiv":
            results = await paper_api.arxiv.search(f"id:{paper_id}", max_results=1)
            paper = results[0] if results else None
        elif source == "core":
            paper = await paper_api.core.get_paper_details(paper_id)
        elif source == "pubmed":
            results = await paper_api.pubmed.search(paper_id, max_results=1)
            paper = results[0] if results else None
        elif source == "crossref":
            results = await paper_api.crossref.search(paper_id, max_results=1)
            paper = results[0] if results else None
        elif source == "europe_pmc":
            results = await paper_api.europe_pmc.search(paper_id, max_results=1)
            paper = results[0] if results else None
        elif source == "sciencedirect":
            results = await paper_api.sciencedirect.search(paper_id, max_results=1)
            paper = results[0] if results else None
        else:
            raise HTTPException(status_code=400, detail=f"Source {source} not supported")
        
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")
        
        # Create document from paper metadata
        metadata = clean_paper_metadata(paper)
        
        doc = Document(
            id=paper.paper_id,
            content=f"{paper.title or 'Untitled'}\n\n{paper.abstract or 'No abstract available'}",
            metadata=metadata
        )
        
        # Add to vector store
        doc_id = vector_store.add_document(doc)
        logger.info(f"Added paper {paper_id} to vector store as {doc_id}")
        
        return {
            "success": True,
            "doc_id": doc_id,
            "paper_id": paper_id,
            "title": paper.title,
            "message": f"Successfully ingested paper from {source}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ingest external paper: {e}")
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)}")


@router.post("/batch-ingest")
async def batch_ingest_papers(
    query: str,
    max_results: int = 20,
    sources: List[str] = None,
):
    """
    Search for papers and automatically ingest them into the vector store
    """
    try:
        paper_api = get_paper_api()
        vector_store = get_vector_store()
        
        # Search for papers
        sources = sources or ["arxiv", "semantic_scholar"]
        logger.info(f"Batch ingest: Searching for '{query}' across {sources}")
        
        results = await paper_api.search_all(
            query=query,
            max_results_per_source=max_results // len(sources),
            sources=sources
        )
        
        # Deduplicate
        papers = paper_api.deduplicate_papers(results)
        logger.info(f"Found {len(papers)} unique papers to ingest")
        
        # Ingest all papers
        ingested_count = 0
        failed_count = 0
        ingested_ids = []
        
        for paper in papers[:max_results]:
            try:
                metadata = clean_paper_metadata(paper)
                
                doc = Document(
                    id=paper.paper_id,
                    content=f"{paper.title or 'Untitled'}\n\n{paper.abstract or 'No abstract available'}",
                    metadata=metadata
                )
                
                doc_id = vector_store.add_document(doc)
                ingested_ids.append(doc_id)
                ingested_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to ingest paper {paper.paper_id}: {e}")
                failed_count += 1
        
        return {
            "success": True,
            "query": query,
            "papers_found": len(papers),
            "papers_ingested": ingested_count,
            "papers_failed": failed_count,
            "ingested_ids": ingested_ids,
            "message": f"Successfully ingested {ingested_count} papers"
        }
    
    except Exception as e:
        logger.error(f"Batch ingest failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch ingest failed: {str(e)}")
