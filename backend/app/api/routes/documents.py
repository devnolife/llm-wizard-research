"""
Document ingestion and management endpoints
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from loguru import logger
import tempfile
import os
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
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Save temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # Process document
        processor = get_document_processor()
        processed_doc = processor.process_pdf(tmp_path)
        
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
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        return IngestResponse(
            success=True,
            doc_id=processed_doc.doc_id,
            message=f"Successfully ingested: {processed_doc.title}",
            chunks_created=len(doc_ids)
        )
        
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
