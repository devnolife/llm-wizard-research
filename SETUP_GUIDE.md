# 🚀 Complete Setup & Usage Guide

## RAG-LLM Research Recommendation System with GLM-4.6

### Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the System](#running-the-system)
5. [Usage Examples](#usage-examples)
6. [API Documentation](#api-documentation)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Topics](#advanced-topics)

---

## Prerequisites

### System Requirements
- **OS**: Linux, macOS, or Windows (WSL2 recommended)
- **RAM**: 16GB minimum, 32GB recommended
- **Storage**: 20GB free space
- **GPU**: Optional (NVIDIA CUDA-compatible for faster inference)
- **Python**: 3.10 or higher

### Required Software
1. **Python 3.10+**
   ```bash
   python3 --version  # Should be 3.10 or higher
   ```

2. **Ollama** (for GLM-4.6)
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Verify installation
   ollama --version
   ```

3. **Git**
   ```bash
   git --version
   ```

4. **Neo4j** (Optional - for advanced knowledge graph features)
   ```bash
   # Via Docker (recommended)
   docker pull neo4j:5.14
   
   # Or install directly from neo4j.com
   ```

---

## Installation

### Option 1: Automated Setup (Recommended)

```bash
# 1. Navigate to project directory
cd /home/devnolife/wizard-research

# 2. Make setup script executable
chmod +x scripts/setup.sh

# 3. Run setup script
./scripts/setup.sh
```

The script will:
- ✅ Check Python version
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Create necessary directories
- ✅ Initialize database
- ✅ Run tests

### Option 2: Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Upgrade pip
pip install --upgrade pip setuptools wheel

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create directories
mkdir -p data/raw data/processed logs chroma_db

# 5. Setup environment
cp .env.example .env
# Edit .env with your settings

# 6. Initialize database
python scripts/init_db.py
```

### Option 3: Docker Setup

```bash
# 1. Build and start services
docker-compose up -d

# 2. Pull GLM-4.6 model in Ollama container
docker exec -it ollama-glm ollama pull glm-4.6:cloud

# 3. Check status
docker-compose ps
```

---

## Configuration

### 1. Environment Variables (.env)

```bash
# Edit .env file
nano .env

# Key settings:
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=glm-4.6:cloud
CHROMA_PERSIST_DIRECTORY=./chroma_db
API_PORT=8000
LOG_LEVEL=INFO
```

### 2. Configuration File (configs/config.yaml)

```yaml
# Model settings
llm:
  temperature: 0.7
  max_tokens: 2048

# Retrieval settings
retrieval:
  top_k: 5
  min_relevance_score: 0.7

# Recommendation strategy
recommendation:
  strategy: hybrid  # content, graph, gap_aware, hybrid
  max_recommendations: 10
```

### 3. Install and Configure GLM-4.6

```bash
# Pull GLM-4.6 model
ollama pull glm-4.6:cloud

# Test the model
ollama run glm-4.6:cloud

# In the Ollama chat:
>>> What is machine learning?
# (Should get a response)
>>> /bye
```

---

## Running the System

### Start Ollama Server

```bash
# Terminal 1: Start Ollama
ollama serve
```

### Start API Server

```bash
# Terminal 2: Activate environment and start API
cd /home/devnolife/wizard-research
source venv/bin/activate
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Verify System is Running

```bash
# Check health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "components": {
    "glm": true,
    "vector_store": true
  },
  "version": "0.1.0"
}
```

### Access API Documentation

Open in browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Usage Examples

### 1. Search for Papers

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "transformer attention mechanisms",
    "top_k": 5
  }'
```

### 2. Get Recommendations

```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "recent advances in graph neural networks",
    "max_results": 10,
    "strategy": "hybrid"
  }'
```

### 3. Detect Research Gaps

```bash
curl -X POST http://localhost:8000/api/gaps \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "reinforcement learning",
    "depth": "comprehensive"
  }'
```

### 4. Ingest Research Paper

```bash
curl -X POST http://localhost:8000/api/ingest \
  -F "file=@paper.pdf" \
  -F "title=Example Paper" \
  -F "authors=John Doe, Jane Smith" \
  -F "year=2024"
```

### 5. Chat with Research Assistant

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain transformer architecture",
    "use_history": true
  }'
```

### Python Examples

```python
# See examples/usage_examples.py for comprehensive examples
python examples/usage_examples.py
```

---

## API Documentation

### Main Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/api/search` | POST | Search for papers |
| `/api/recommend` | POST | Get recommendations |
| `/api/gaps` | POST | Detect research gaps |
| `/api/chat` | POST | Chat with assistant |
| `/api/ingest` | POST | Upload paper |
| `/api/stats` | GET | System statistics |

### Request/Response Examples

See interactive API docs at: http://localhost:8000/docs

---

## Troubleshooting

### Common Issues

#### 1. Ollama Connection Error

```bash
# Problem: Cannot connect to Ollama
# Solution:
ollama serve  # Start Ollama server

# Check if Ollama is running:
curl http://localhost:11434/api/tags
```

#### 2. GLM-4.6 Model Not Found

```bash
# Problem: Model not available
# Solution:
ollama pull glm-4.6:cloud

# List available models:
ollama list
```

#### 3. ChromaDB Persistence Issues

```bash
# Problem: Database not persisting
# Solution:
# 1. Check permissions
chmod -R 755 ./chroma_db

# 2. Reinitialize database
python scripts/init_db.py
```

#### 4. Memory Issues

```python
# Problem: Out of memory errors
# Solution: Reduce batch sizes in config.yaml

retrieval:
  top_k: 3  # Reduce from 5
  
vector_db:
  batch_size: 50  # Reduce from 100
```

#### 5. Import Errors

```bash
# Problem: Module not found
# Solution:
pip install -r requirements.txt --upgrade

# Or reinstall specific package:
pip install --force-reinstall chromadb
```

### Logging

Check logs for detailed error information:

```bash
# Application logs
tail -f logs/app.log

# Test logs
tail -f logs/test.log

# Init logs
tail -f logs/init_db.log
```

---

## Advanced Topics

### 1. Custom Embedding Models

```python
# Edit src/retrieval/vector_store.py
vector_store = VectorStore(
    embedding_model="sentence-transformers/all-mpnet-base-v2"  # Better quality
)
```

### 2. Neo4j Integration

```bash
# Start Neo4j
docker-compose up neo4j

# Enable in config.yaml
neo4j:
  enabled: true
  uri: bolt://localhost:7687
  user: neo4j
  password: research123
```

### 3. Batch Paper Ingestion

```python
# Process directory of papers
from src.utils.document_processor import DocumentProcessor

processor = DocumentProcessor()
docs = processor.process_directory("./data/raw", recursive=True)

# Add to vector store
from src.retrieval.vector_store import VectorStore
store = VectorStore()
store.add_documents([
    Document(id=doc.doc_id, content=doc.content, metadata=doc.metadata)
    for doc in docs
])
```

### 4. Custom Agents

```python
# Create custom agent
from src.agents.coordinator import CoordinatorAgent

class CustomAgent:
    def analyze(self, query, context):
        # Your custom logic
        return results

# Register with coordinator
coordinator = CoordinatorAgent(custom_agent=CustomAgent())
```

### 5. Performance Optimization

```yaml
# config.yaml
performance:
  enable_caching: true
  parallel_processing: true
  max_workers: 8  # Adjust based on CPU cores
```

---

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_vector_store.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Code Formatting

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Check style
flake8 src/ tests/
```

### Adding New Features

1. Create feature branch
2. Implement feature with tests
3. Update documentation
4. Submit pull request

---

## Production Deployment

### Using Docker

```bash
# Build production image
docker build -t rag-research:latest .

# Run production stack
docker-compose -f docker-compose.prod.yml up -d

# Scale workers
docker-compose up --scale api=4
```

### Environment Variables for Production

```bash
# Production .env
API_WORKERS=8
LOG_LEVEL=WARNING
ENABLE_CACHING=true
CORS_ORIGINS=https://your-domain.com
```

---

## Support & Resources

- **Documentation**: See `/docs` endpoint
- **Issues**: GitHub Issues
- **Examples**: `examples/` directory
- **Tests**: `tests/` directory

---

## License

MIT License - See LICENSE file

---

**Built with ❤️ for Research Community**

Last Updated: November 13, 2025
