"""
Vector Store with ChromaDB Integration

Manages document embeddings, storage, and semantic search using ChromaDB.
"""

import os
import uuid
from threading import RLock
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
import numpy as np

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
except ImportError:
    raise ImportError("chromadb not installed. Run: pip install chromadb")

from sentence_transformers import SentenceTransformer
from loguru import logger


@dataclass
class Document:
    """Represents a document with metadata"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Represents a search result"""
    document: Document
    score: float
    rank: int


class VectorStore:
    """
    Vector store using ChromaDB for document embeddings and similarity search
    
    Features:
    - Document embedding generation with sentence-transformers
    - Persistent storage with ChromaDB
    - Semantic search and similarity queries
    - Metadata filtering
    - Batch operations for efficiency
    """
    
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "research_papers",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        distance_metric: str = "cosine"
    ):
        """
        Initialize vector store
        
        Args:
            persist_directory: Directory for persistent storage
            collection_name: Name of the collection
            embedding_model: HuggingFace model for embeddings
            distance_metric: Distance metric (cosine, l2, ip)
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.distance_metric = distance_metric
        # Chroma's persistent local client is shared by the two analysis
        # workers. Serialize mutations while allowing concurrent reads.
        self._write_lock = RLock()
        
        # Create persist directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
        logger.info(f"Embedding dimension: {self.embedding_dimension}")
        
        # Get or create collection
        self.collection = self._get_or_create_collection()
        
        logger.info(f"VectorStore initialized with collection '{collection_name}'")
        logger.info(f"Current document count: {self.collection.count()}")
    
    def _get_or_create_collection(self):
        """Get existing collection or create new one"""
        try:
            # Try to get existing collection
            collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=self._create_embedding_function()
            )
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            # Create new collection
            collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self._create_embedding_function(),
                metadata={"hnsw:space": self.distance_metric}
            )
            logger.info(f"Created new collection: {self.collection_name}")
        
        return collection
    
    def _create_embedding_function(self):
        """Create custom embedding function for ChromaDB"""
        class CustomEmbeddingFunction(embedding_functions.EmbeddingFunction):
            def __init__(self, model):
                self.model = model
            
            def __call__(self, input: List[str]) -> List[List[float]]:
                embeddings = self.model.encode(input, show_progress_bar=False)
                return embeddings.tolist()
        
        return CustomEmbeddingFunction(self.embedding_model)
    
    def add_document(
        self,
        content: Union[str, 'Document'],
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> str:
        """
        Add a single document to the vector store
        
        Args:
            content: Document content (string) or Document object
            metadata: Optional metadata dictionary (ignored if Document object provided)
            doc_id: Optional document ID (auto-generated if not provided)
            
        Returns:
            Document ID
        """
        # Handle Document object
        if isinstance(content, Document):
            doc_id = content.id or str(uuid.uuid4())
            content_str = content.content
            metadata = content.metadata or {}
        else:
            doc_id = doc_id or str(uuid.uuid4())
            content_str = content
            metadata = metadata or {}
        
        # Ensure metadata values are simple types (ChromaDB requirement)
        clean_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (list, tuple)):
                # Convert lists to comma-separated strings
                clean_metadata[key] = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                # Convert dicts to JSON string
                clean_metadata[key] = str(value)
            elif isinstance(value, (str, int, float, bool)) or value is None:
                clean_metadata[key] = value
            else:
                clean_metadata[key] = str(value)
        
        # ChromaDB rejects empty metadata dicts — use None instead.
        # Local persistent Chroma is not safe for competing writes from
        # multiple analysis worker threads.
        with self._write_lock:
            self.collection.add(
                documents=[content_str],
                metadatas=[clean_metadata] if clean_metadata else None,
                ids=[doc_id]
            )
        
        logger.info(f"Added document: {doc_id}")
        return doc_id
    
    def add_documents(
        self,
        documents: List[Document],
        batch_size: int = 100
    ) -> List[str]:
        """
        Add multiple documents in batches
        
        Args:
            documents: List of Document objects
            batch_size: Batch size for processing
            
        Returns:
            List of document IDs
        """
        doc_ids = []
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            batch_ids = [doc.id for doc in batch]
            batch_contents = [doc.content for doc in batch]
            # ChromaDB rejects empty metadata dicts — substitute None per document
            batch_metadatas = [doc.metadata if doc.metadata else None for doc in batch]
            
            with self._write_lock:
                self.collection.add(
                    documents=batch_contents,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
            
            doc_ids.extend(batch_ids)
            logger.info(f"Added batch {i//batch_size + 1}: {len(batch)} documents")
        
        logger.info(f"Total documents added: {len(doc_ids)}")
        return doc_ids
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_score: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Search for similar documents
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filter
            min_score: Minimum similarity score threshold
            
        Returns:
            List of SearchResult objects
        """
        # Perform search
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=filter_metadata
        )
        
        # Parse results
        search_results = []
        
        if results['ids'] and len(results['ids'][0]) > 0:
            for rank, (doc_id, content, metadata, distance) in enumerate(zip(
                results['ids'][0],
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                # Convert distance to similarity score
                # For cosine distance: similarity = 1 - distance
                score = 1.0 - distance if self.distance_metric == "cosine" else distance
                
                # Apply minimum score filter
                if min_score and score < min_score:
                    continue
                
                document = Document(
                    id=doc_id,
                    content=content,
                    metadata=metadata
                )
                
                search_results.append(SearchResult(
                    document=document,
                    score=score,
                    rank=rank + 1
                ))
        
        logger.info(f"Search query: '{query[:50]}...' - Found {len(search_results)} results")
        return search_results
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """
        Get a document by ID
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document object or None if not found
        """
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
            
            if results['ids']:
                return Document(
                    id=results['ids'][0],
                    content=results['documents'][0],
                    metadata=results['metadatas'][0]
                )
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
        
        return None
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by ID
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._write_lock:
                self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
    
    def update_document(
        self,
        doc_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update a document
        
        Args:
            doc_id: Document ID
            content: New content (optional)
            metadata: New metadata (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_params = {"ids": [doc_id]}
            
            if content:
                update_params["documents"] = [content]
            if metadata:
                update_params["metadatas"] = [metadata]
            
            self.collection.update(**update_params)
            logger.info(f"Updated document: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False
    
    def count(self) -> int:
        """Get total number of documents in collection"""
        return self.collection.count()
    
    def count_by_source(self, source: str) -> int:
        """
        Count how many chunks are already stored for a given source filename.
        Used to detect duplicate uploads (paper already indexed).
        """
        try:
            results = self.collection.get(where={"source": source}, include=[])
            return len(results.get("ids", []))
        except Exception as e:
            logger.error(f"Failed to count by source '{source}': {e}")
            return 0

    def delete_by_metadata(self, filter_metadata: Dict[str, Any]) -> int:
        """Delete chunks matching a metadata filter and return their count.

        Analysis retries use ``analysis_job_id`` so they can clean only their
        own chunks rather than clearing the shared research corpus.
        """
        try:
            with self._write_lock:
                existing = self.collection.get(where=filter_metadata, include=[])
                ids = existing.get("ids", [])
                if ids:
                    self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents matching metadata filter")
            return len(ids)
        except Exception as e:
            logger.error(f"Failed to delete documents by metadata: {e}")
            return 0
    
    def get_all_documents(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Document]:
        """
        Get all documents from the collection
        
        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            
        Returns:
            List of Document objects
        """
        try:
            results = self.collection.get(
                limit=limit,
                offset=offset,
                include=["documents", "metadatas"]
            )
            
            documents = []
            for doc_id, content, metadata in zip(
                results['ids'],
                results['documents'],
                results['metadatas']
            ):
                documents.append(Document(
                    id=doc_id,
                    content=content,
                    metadata=metadata
                ))
            
            return documents
        except Exception as e:
            logger.error(f"Failed to get all documents: {e}")
            return []
    
    def clear_collection(self):
        """Delete all documents in the collection"""
        try:
            # Delete collection and recreate
            with self._write_lock:
                self.client.delete_collection(self.collection_name)
                self.collection = self._get_or_create_collection()
            logger.info(f"Cleared collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        embedding = self.embedding_model.encode(text, show_progress_bar=False)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        return embeddings.tolist()
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        emb1 = self.embedding_model.encode(text1, show_progress_bar=False)
        emb2 = self.embedding_model.encode(text2, show_progress_bar=False)
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        return {
            "collection_name": self.collection_name,
            "total_documents": self.count(),
            "embedding_model": self.embedding_model_name,
            "embedding_dimension": self.embedding_dimension,
            "distance_metric": self.distance_metric,
            "persist_directory": self.persist_directory
        }
    
    def __repr__(self) -> str:
        return f"VectorStore(collection='{self.collection_name}', docs={self.count()})"


# Example usage
if __name__ == "__main__":
    # Initialize vector store
    store = VectorStore(
        persist_directory="./test_chroma_db",
        collection_name="test_papers"
    )
    
    # Add sample documents
    sample_docs = [
        Document(
            id="paper1",
            content="Transformers have revolutionized natural language processing through self-attention mechanisms.",
            metadata={"title": "Attention is All You Need", "year": 2017}
        ),
        Document(
            id="paper2",
            content="BERT uses bidirectional training of transformers for language understanding.",
            metadata={"title": "BERT Paper", "year": 2018}
        ),
        Document(
            id="paper3",
            content="GPT-3 demonstrates few-shot learning capabilities with 175 billion parameters.",
            metadata={"title": "GPT-3 Paper", "year": 2020}
        )
    ]
    
    store.add_documents(sample_docs)
    
    # Search
    results = store.search("transformer attention mechanism", top_k=2)
    
    print("\n🔍 Search Results:")
    for result in results:
        print(f"  Rank {result.rank}: {result.document.metadata.get('title')} (Score: {result.score:.3f})")
        print(f"  Content: {result.document.content[:80]}...")
    
    # Stats
    print(f"\n📊 Stats: {store.get_stats()}")
