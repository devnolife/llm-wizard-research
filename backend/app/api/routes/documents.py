"""
Document ingestion and management endpoints
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from loguru import logger
import os
import uuid
from typing import Optional
from pathlib import Path

from ...models.requests import QueryRequest
from ...models.responses import IngestResponse
from ...core.retrieval.vector_store import Document
from ..dependencies import (
    get_vector_store,
    get_retriever,
    get_document_processor
)
from ...utils.config_loader import get_config
from ...utils.upload_validation import sanitize_filename, write_validated_pdf_upload

router = APIRouter()


@router.post("/search")
async def search(request: QueryRequest):
    """Search for relevant papers"""
    try:
        retriever = get_retriever()
        results = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            filter_metadata=request.filters
        )
        
        return {
            "query": request.query,
            "total_results": len(results),
            "results": [
                {
                    "rank": r.rank,
                    "title": r.document.metadata.get("title", "Unknown"),
                    "content": r.document.content[:500],
                    "score": r.score,
                    "metadata": r.document.metadata
                }
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = None,
    authors: Optional[str] = None,
    year: Optional[int] = None
):
    """Ingest a research paper"""
    tmp_path = None
    try:
        config = get_config()
        allowed_types = {str(t).lower().lstrip(".") for t in config.data.allowed_file_types}
        if "pdf" not in allowed_types:
            raise HTTPException(status_code=415, detail="PDF uploads are not enabled")
        safe_name = sanitize_filename(file.filename)
        tmp_path = Path(config.data.raw_path) / f"{uuid.uuid4()}_{safe_name}"
        await write_validated_pdf_upload(file, tmp_path, config.data.max_file_size_mb)
        
        # Process document
        processor = get_document_processor()
        processed_doc = processor.process_pdf(str(tmp_path))
        
        # Add metadata
        if title:
            processed_doc.metadata["title"] = title
        if authors:
            processed_doc.metadata["authors"] = authors
        if year:
            processed_doc.metadata["year"] = int(year)
        
        # Add to vector store
        vector_store = get_vector_store()
        
        # Convert chunks to documents with ChromaDB-compatible metadata
        docs_to_add = []
        for chunk in processed_doc.chunks:
            # Clean metadata to ensure ChromaDB compatibility
            clean_metadata = {}
            for key, value in chunk.metadata.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    clean_metadata[key] = value
                elif isinstance(value, list):
                    clean_metadata[key] = ", ".join(str(v) for v in value)
                else:
                    clean_metadata[key] = str(value)
            
            docs_to_add.append(Document(
                id=chunk.chunk_id,
                content=chunk.content,
                metadata=clean_metadata
            ))
        
        doc_ids = vector_store.add_documents(docs_to_add)
        
        return IngestResponse(
            success=True,
            doc_id=processed_doc.doc_id,
            message=f"Successfully ingested: {processed_doc.title}",
            chunks_created=len(doc_ids)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass


@router.get("/stats")
async def get_statistics():
    """Get system statistics"""
    try:
        vector_store = get_vector_store()
        vs_stats = vector_store.get_stats()
        total_docs = vector_store.count()
        
        return {
            "vector_store": vs_stats,
            "total_documents": total_docs,
            "document_count": total_docs,
            "total_chunks": vs_stats.get("total_chunks", vs_stats.get("count", total_docs)),
        }
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document"""
    try:
        vector_store = get_vector_store()
        success = vector_store.delete_document(doc_id)
        
        if success:
            return {"message": f"Document {doc_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        logger.error(f"Document deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
