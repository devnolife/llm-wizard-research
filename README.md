# RAG-LLM Research Recommendation System 🔬

A sophisticated Research Assistant powered by **GLM-4.6**, **ChromaDB**, and **Multi-Agent Architecture** for intelligent research paper recommendations, gap detection, and knowledge discovery.

## 🌟 Features

- **🤖 GLM-4.6 Integration**: Leverages Ollama's GLM-4.6 model for advanced language understanding
- **📚 RAG Pipeline**: Semantic search and retrieval using ChromaDB vector database
- **🧠 Multi-Agent Framework**: Coordinated agents for research analysis, gap detection, and recommendations
- **🕸️ Knowledge Graph**: Citation networks and topic clustering with NetworkX/Neo4j
- **🔍 Gap Detection**: Automatic identification of research gaps using semantic analysis
- **⚡ FastAPI Backend**: High-performance REST API for real-time recommendations
- **📄 Document Processing**: Support for PDF research papers with intelligent chunking

## 📋 Prerequisites

- **Python**: 3.10 or higher
- **RAM**: 16GB+ recommended
- **GPU**: Optional (CUDA-compatible for faster inference)
- **Ollama**: For running GLM-4.6 model locally
- **Neo4j**: Optional (for advanced knowledge graph features)

## 🚀 Quick Start

### 1. Clone and Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install and Setup Ollama with GLM-4.6

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull GLM-4.6 model
ollama pull glm-4.6:cloud

# Test the model
ollama run glm-4.6:cloud
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 4. Initialize Vector Database

```bash
# Run initialization script
python scripts/init_db.py
```

### 5. Start the API Server

```bash
# Development mode
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📁 Project Structure

```
rag-llm-research-recommender/
├── data/
│   ├── raw/              # Raw research papers (PDF)
│   └── processed/        # Processed and embedded documents
├── src/
│   ├── agents/           # Multi-agent framework
│   │   ├── coordinator.py
│   │   ├── research_analyzer.py
│   │   ├── gap_detector.py
│   │   └── recommender.py
│   ├── retrieval/        # RAG pipeline
│   │   ├── vector_store.py
│   │   └── rag_retriever.py
│   ├── knowledge_graph/  # Graph construction
│   │   └── graph_builder.py
│   ├── gap_detection/    # Gap analysis
│   │   └── analyzer.py
│   ├── recommendation/   # Recommendation engine
│   │   └── engine.py
│   ├── llm/             # GLM-4.6 interface
│   │   └── glm_interface.py
│   ├── utils/           # Utilities
│   │   ├── document_processor.py
│   │   └── config_loader.py
│   └── api/             # FastAPI application
│       └── main.py
├── configs/             # Configuration files
│   └── config.yaml
├── tests/              # Test suites
├── scripts/            # Setup and utility scripts
├── requirements.txt    # Python dependencies
├── .env.example       # Environment template
└── README.md
```

## 🔧 Configuration

Edit `configs/config.yaml` to customize:

- **Model Settings**: Temperature, max tokens, context window
- **Vector DB**: Collection names, embedding dimensions
- **Data Sources**: Paper repositories, update schedules
- **Evaluation Metrics**: Relevance thresholds, ranking parameters

## 📖 API Usage

### Get Research Recommendations

```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "recent advances in transformer architectures",
    "max_results": 5
  }'
```

### Ingest Research Papers

```bash
curl -X POST http://localhost:8000/api/ingest \
  -F "file=@paper.pdf" \
  -F "metadata={\"title\":\"Paper Title\",\"authors\":[\"Author Name\"]}"
```

### Detect Research Gaps

```bash
curl -X POST http://localhost:8000/api/gaps \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "graph neural networks",
    "depth": "comprehensive"
  }'
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test module
pytest tests/test_retrieval.py -v
```

## 🐳 Docker Deployment (Optional)

```bash
# Build image
docker build -t rag-research-recommender .

# Run container
docker-compose up -d
```

## 📊 Performance Optimization

- **GPU Acceleration**: Set `CUDA_VISIBLE_DEVICES` for GPU inference
- **Batch Processing**: Adjust `BATCH_SIZE` in config for parallel processing
- **Caching**: Enable Redis for query result caching
- **Indexing**: Use HNSW index in ChromaDB for faster similarity search

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- **GLM-4**: Zhipu AI for the GLM-4.6 model
- **ChromaDB**: For vector database capabilities
- **LangChain**: For agent orchestration framework
- **Ollama**: For local LLM deployment

## 📞 Support

- **Issues**: GitHub Issues
- **Documentation**: [Wiki](https://github.com/your-repo/wiki)
- **Email**: support@example.com

---

**Built with ❤️ for the Research Community**
