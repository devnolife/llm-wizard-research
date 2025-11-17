# Wizard Research

**AI-Powered Research Paper Recommendation System with Automatic Gap Detection**

A full-stack RAG-LLM application that helps researchers discover relevant papers, detect research gaps, and get personalized recommendations using advanced AI agents.

## 🌟 Features

- **📄 PDF Upload & Processing** - Automatic text extraction and chunking
- **🔍 Semantic Search** - Vector-based similarity search across research papers
- **🤖 Multi-Agent Analysis** - Coordinator, Analyzer, Gap Detector, and Recommender agents
- **🌐 External Paper APIs** - Integration with arXiv, Semantic Scholar, CORE, PubMed, CrossRef
- **🎯 Auto-Analysis** - Upload PDFs and get instant topic extraction, gap detection, and recommendations
- **💬 Research Assistant Chat** - Interactive Q&A about your research corpus
- **🔗 Knowledge Graph** - Citation network visualization (optional Neo4j integration)

## 🏗️ Project Structure

```
wizard-research/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── api/               # API routes (modular)
│   │   ├── core/              # Business logic (agents, RAG, graphs)
│   │   ├── services/          # External services (LLM, APIs)
│   │   ├── models/            # Pydantic models
│   │   └── main.py            # FastAPI entry point
│   ├── tests/                 # Unit, integration, e2e tests
│   ├── config.yaml            # Configuration
│   └── requirements.txt
│
├── frontend/                   # React + Vite frontend
│   ├── src/
│   │   ├── components/        # pages/, layout/, common/
│   │   ├── services/          # API clients
│   │   └── App.jsx
│   └── package.json
│
├── data/                       # Raw PDFs, processed data, backups
├── chroma_db/                 # Vector database (ChromaDB)
├── research_papers/           # Sample papers
└── Makefile                   # Common commands
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Ollama (for LLM inference)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/devnolife/wizard-research.git
cd wizard-research
```

2. **Setup (installs all dependencies)**
```bash
make setup
```

3. **Configure environment variables**
```bash
# Edit backend/.env and frontend/.env with your settings
# See .env.example files for reference
```

4. **Start Ollama (in a separate terminal)**
```bash
ollama serve
ollama pull glm-4-flash  # or your preferred model
```

5. **Run development servers**
```bash
make dev
```

This will start:
- Backend API: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

## 📖 Usage

### Upload & Auto-Analyze Papers

1. Navigate to http://localhost:5173
2. Drag & drop PDF papers or click to browse
3. Click "Upload & Auto-Analyze"
4. View extracted topics, research gaps, and recommendations

### Search External Papers

```bash
curl -X POST "http://localhost:8000/api/papers/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "transformer neural networks", "sources": ["arxiv", "semantic_scholar"]}'
```

### Chat with Research Assistant

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the main research directions in NLP?"}'
```

## 🛠️ Development

### Backend Commands

```bash
make backend          # Run backend server
make install-backend  # Install backend deps
make test            # Run all tests
make test-unit       # Run unit tests only
```

### Frontend Commands

```bash
make frontend         # Run frontend dev server
make install-frontend # Install frontend deps
```

### Docker

```bash
make docker-up       # Start all services
make docker-down     # Stop all services
make docker-logs     # View logs
```

## 🔌 API Endpoints

### Documents
- `POST /api/ingest` - Upload PDF
- `POST /api/search` - Search documents
- `GET /api/stats` - Get statistics
- `DELETE /api/documents/{id}` - Delete document

### External Papers
- `POST /api/papers/search` - Search external APIs
- `POST /api/papers/batch-ingest` - Bulk ingest papers
- `POST /api/papers/ingest-external` - Ingest specific paper

### Analysis
- `POST /api/upload-and-analyze` - Auto-analyze PDFs
- `GET /api/analysis-status/{job_id}` - Check analysis status
- `POST /api/recommend` - Get recommendations
- `POST /api/gaps` - Detect research gaps
- `POST /api/chat` - Chat with assistant

### System
- `GET /health` - Health check
- `GET /api/sources/status` - Check API keys

## 🔑 External API Keys (Optional)

Add these to `backend/.env` for enhanced functionality:

```bash
SEMANTIC_SCHOLAR_API_KEY=your_key
CORE_API_KEY=your_key
PUBMED_API_KEY=your_key
CROSSREF_EMAIL=your_email
```

## 📚 Documentation

See API documentation at http://localhost:8000/docs after starting the server.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Built with FastAPI, React, ChromaDB, and Ollama
- Integrates arXiv, Semantic Scholar, CORE, PubMed, and CrossRef APIs
- Powered by GLM-4 and other open-source LLMs

---

Made with ❤️ by [devnolife](https://github.com/devnolife)
