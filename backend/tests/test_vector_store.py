"""
Test suite for vector store
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from app.core.retrieval.vector_store import VectorStore, Document, SearchResult


pytestmark = pytest.mark.slow


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def vector_store(temp_dir):
    """Create vector store for testing"""
    return VectorStore(
        persist_directory=temp_dir,
        collection_name="test_collection",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2"
    )


def test_vector_store_initialization(vector_store):
    """Test vector store initialization"""
    assert vector_store is not None
    assert vector_store.count() == 0


def test_add_document(vector_store):
    """Test adding a document"""
    doc_id = vector_store.add_document(
        content="Test document content",
        metadata={"title": "Test Document"}
    )
    assert doc_id is not None
    assert vector_store.count() == 1


def test_add_multiple_documents(vector_store):
    """Test adding multiple documents"""
    docs = [
        Document(
            id=f"doc_{i}",
            content=f"Document {i} content",
            metadata={"title": f"Document {i}"}
        )
        for i in range(5)
    ]
    doc_ids = vector_store.add_documents(docs)
    assert len(doc_ids) == 5
    assert vector_store.count() == 5


def test_search(vector_store):
    """Test document search"""
    # Add test documents
    docs = [
        Document(
            id="doc1",
            content="Machine learning and artificial intelligence",
            metadata={"title": "AI Paper"}
        ),
        Document(
            id="doc2",
            content="Deep learning and neural networks",
            metadata={"title": "DL Paper"}
        )
    ]
    vector_store.add_documents(docs)
    
    # Search
    results = vector_store.search("machine learning", top_k=2)
    assert len(results) > 0
    assert isinstance(results[0], SearchResult)
    assert results[0].score > 0


def test_get_document(vector_store):
    """Test retrieving a document"""
    doc_id = vector_store.add_document(
        content="Test content",
        metadata={"title": "Test"}
    )
    
    retrieved = vector_store.get_document(doc_id)
    assert retrieved is not None
    assert retrieved.id == doc_id
    assert "Test content" in retrieved.content


def test_delete_document(vector_store):
    """Test deleting a document"""
    doc_id = vector_store.add_document(
        content="To be deleted",
        metadata={}
    )
    
    assert vector_store.count() == 1
    success = vector_store.delete_document(doc_id)
    assert success
    assert vector_store.count() == 0


def test_similarity(vector_store):
    """Test text similarity calculation"""
    similarity = vector_store.similarity(
        "machine learning",
        "artificial intelligence"
    )
    assert 0 <= similarity <= 1


def test_get_stats(vector_store):
    """Test getting statistics"""
    stats = vector_store.get_stats()
    assert "collection_name" in stats
    assert "total_documents" in stats
    assert "embedding_dimension" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
