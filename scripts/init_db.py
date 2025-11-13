"""
Database Initialization Script

Initializes ChromaDB and creates necessary collections.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.retrieval.vector_store import VectorStore, Document
from src.utils.config_loader import get_config


def init_vector_database():
    """Initialize vector database"""
    logger.info("Initializing vector database...")
    
    # Load config
    config = get_config()
    
    # Create vector store
    vector_store = VectorStore(
        persist_directory=config.vector_db.persist_directory,
        collection_name=config.vector_db.collection_name,
        embedding_model=config.vector_db.embedding_model
    )
    
    logger.info(f"Vector store initialized with {vector_store.count()} documents")
    
    # Add sample documents if empty
    if vector_store.count() == 0:
        logger.info("Adding sample documents...")
        
        sample_docs = [
            Document(
                id="sample_1",
                content="Transformers have revolutionized natural language processing through self-attention mechanisms. The attention mechanism allows the model to weigh the importance of different parts of the input sequence.",
                metadata={
                    "title": "Attention is All You Need",
                    "year": 2017,
                    "authors": ["Vaswani et al."],
                    "keywords": ["transformer", "attention", "NLP"],
                    "type": "research_paper"
                }
            ),
            Document(
                id="sample_2",
                content="BERT introduces bidirectional training of transformers for language understanding. By pretraining on unlabeled data and fine-tuning on specific tasks, BERT achieves state-of-the-art results.",
                metadata={
                    "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                    "year": 2018,
                    "authors": ["Devlin et al."],
                    "keywords": ["BERT", "transformer", "pretraining"],
                    "type": "research_paper"
                }
            ),
            Document(
                id="sample_3",
                content="GPT-3 demonstrates remarkable few-shot learning capabilities with 175 billion parameters. The model can perform various NLP tasks without task-specific fine-tuning.",
                metadata={
                    "title": "Language Models are Few-Shot Learners",
                    "year": 2020,
                    "authors": ["Brown et al."],
                    "keywords": ["GPT-3", "few-shot learning", "large language model"],
                    "type": "research_paper"
                }
            ),
            Document(
                id="sample_4",
                content="Graph Neural Networks (GNNs) extend deep learning to graph-structured data. They learn node representations by aggregating information from neighboring nodes.",
                metadata={
                    "title": "Graph Neural Networks: A Review",
                    "year": 2019,
                    "authors": ["Wu et al."],
                    "keywords": ["GNN", "graph learning", "neural networks"],
                    "type": "research_paper"
                }
            ),
            Document(
                id="sample_5",
                content="Reinforcement Learning from Human Feedback (RLHF) aligns language models with human preferences. This technique has been crucial for creating helpful and harmless AI assistants.",
                metadata={
                    "title": "Training Language Models with Human Feedback",
                    "year": 2022,
                    "authors": ["Ouyang et al."],
                    "keywords": ["RLHF", "alignment", "preference learning"],
                    "type": "research_paper"
                }
            )
        ]
        
        vector_store.add_documents(sample_docs)
        logger.info(f"Added {len(sample_docs)} sample documents")
    
    # Print statistics
    stats = vector_store.get_stats()
    logger.info(f"Database statistics: {stats}")
    
    return vector_store


def test_database():
    """Test database functionality"""
    logger.info("Testing database...")
    
    config = get_config()
    vector_store = VectorStore(
        persist_directory=config.vector_db.persist_directory,
        collection_name=config.vector_db.collection_name,
        embedding_model=config.vector_db.embedding_model
    )
    
    # Test search
    results = vector_store.search("transformer attention mechanism", top_k=3)
    
    logger.info(f"Test search returned {len(results)} results")
    for result in results:
        logger.info(f"  - {result.document.metadata.get('title')} (score: {result.score:.3f})")
    
    logger.info("Database test completed successfully")


if __name__ == "__main__":
    # Setup logging
    logger.add("logs/init_db.log", rotation="10 MB")
    
    try:
        # Initialize database
        vector_store = init_vector_database()
        
        # Test database
        test_database()
        
        logger.info("✅ Database initialization completed successfully")
        print("\n✅ Database initialized successfully!")
        print(f"📊 Total documents: {vector_store.count()}")
        print(f"📁 Location: {vector_store.persist_directory}")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)
