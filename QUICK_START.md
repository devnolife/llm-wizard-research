# 🚀 Panduan Setup Cepat - Menggunakan Ollama Server yang Sudah Ada

## Prasyarat
✅ Ollama sudah terinstall di server
✅ Python 3.10+ terinstall
✅ Model GLM sudah di-download di Ollama

## Setup Cepat

### 1. Pastikan Ollama Berjalan

```bash
# Cek status Ollama
ollama list

# Jika belum berjalan, start Ollama
ollama serve
```

### 2. Setup Project

```bash
# Masuk ke direktori project
cd /home/devnolife/wizard-research

# Jalankan setup otomatis
./scripts/setup.sh
```

Script akan otomatis:
- ✅ Membuat virtual environment
- ✅ Install dependencies
- ✅ Membuat direktori yang diperlukan
- ✅ Inisialisasi database
- ✅ Setup konfigurasi

### 3. Konfigurasi Environment

```bash
# File .env sudah dibuat otomatis, sesuaikan jika perlu
nano .env

# Pastikan settingan ini:
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=glm4:latest  # atau glm-4.6:cloud sesuai yang terinstall
```

### 4. Jalankan Aplikasi

#### Opsi A: Tanpa Docker (Langsung di Server)

```bash
# Aktifkan virtual environment
source venv/bin/activate

# Start API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Opsi B: Dengan Docker (API Only)

```bash
# Build dan jalankan
docker-compose -f docker-compose.simple.yml up -d

# Cek logs
docker logs -f rag-llm-api
```

### 5. Test Aplikasi

```bash
# Test health check
curl http://localhost:8000/health

# Test search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "top_k": 3}'
```

### 6. Akses API Documentation

Buka browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Verifikasi Ollama

```bash
# Cek model yang tersedia
ollama list

# Test Ollama langsung
ollama run glm4:latest "What is AI?"
# atau
ollama run glm-4.6:cloud "What is AI?"

# Cek Ollama API
curl http://localhost:11434/api/tags
```

## Troubleshooting

### Problem: API tidak bisa connect ke Ollama

```bash
# Solusi 1: Pastikan Ollama berjalan
ps aux | grep ollama

# Solusi 2: Start Ollama jika belum
ollama serve &

# Solusi 3: Test koneksi
curl http://localhost:11434/api/version
```

### Problem: Model tidak ditemukan

```bash
# Cek model yang ada
ollama list

# Pull model jika belum ada
ollama pull glm4:latest

# Atau untuk versi spesifik
ollama pull glm-4.6:cloud
```

### Problem: Permission denied pada setup.sh

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

## Struktur Project

```
wizard-research/
├── src/               # Source code
│   ├── api/          # FastAPI application
│   ├── llm/          # GLM interface
│   ├── retrieval/    # RAG & Vector store
│   ├── agents/       # Multi-agent system
│   └── ...
├── data/             # Data storage
│   ├── raw/          # PDF papers
│   └── processed/    # Processed data
├── chroma_db/        # Vector database
├── logs/             # Application logs
├── configs/          # Configuration files
├── scripts/          # Setup & utility scripts
└── tests/            # Test suites
```

## Quick Commands

```bash
# Aktivasi environment
source venv/bin/activate

# Start API (development)
uvicorn src.api.main:app --reload

# Start API (production)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Run tests
pytest tests/ -v

# Inisialisasi ulang database
python scripts/init_db.py

# Lihat logs
tail -f logs/app.log
```

## Next Steps

1. ✅ Upload PDF papers ke `data/raw/`
2. ✅ Ingest papers via API: `POST /api/ingest`
3. ✅ Cari papers: `POST /api/search`
4. ✅ Get recommendations: `POST /api/recommend`
5. ✅ Detect gaps: `POST /api/gaps`

## Contoh Penggunaan

```python
# Lihat contoh lengkap di:
python examples/usage_examples.py
```

---

**Catatan**: Karena Ollama sudah terinstall di server, tidak perlu Docker untuk Ollama. Cukup jalankan API service saja.
