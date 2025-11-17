# 📤 Bulk PDF Upload Guide

## Overview
The Wizard Research system now supports **bulk PDF upload** functionality, allowing you to quickly populate your knowledge base with research papers.

## Features

✅ **Multi-file upload** - Select and upload multiple PDFs at once
✅ **Real-time progress** - Visual feedback for each file upload
✅ **Automatic processing** - PDFs are automatically extracted and chunked
✅ **Error handling** - Clear error messages for failed uploads
✅ **Summary statistics** - Success/failure counts after batch upload

## Usage

### 1. Web Interface (Recommended)

1. **Start the server:**
   ```bash
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Open browser:**
   ```
   http://localhost:8000
   ```

3. **Upload PDFs:**
   - Click "📁 Select PDF Files" button
   - Choose one or multiple PDF files
   - Review selected files (you can remove any)
   - Click "⬆️ Upload X File(s)" button
   - Wait for processing (progress shown in real-time)

### 2. API Endpoint

**Single file upload:**
```bash
curl -X POST \
  -F "file=@/path/to/paper.pdf" \
  -F "title=Paper Title" \
  -F "authors=Author Name" \
  -F "year=2024" \
  http://localhost:8000/api/ingest
```

**Response:**
```json
{
  "success": true,
  "doc_id": "abc123...",
  "message": "Successfully ingested: Paper Title",
  "chunks_created": 5
}
```

### 3. Batch Upload Script

```bash
# Upload all PDFs in a directory
for file in /path/to/pdfs/*.pdf; do
  echo "Uploading: $(basename $file)"
  curl -X POST \
    -F "file=@$file" \
    http://localhost:8000/api/ingest
  echo ""
done
```

## Test PDFs

Create test PDFs for development:

```bash
cd /home/devnolife/wizard-research
python3 -c "
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

test_dir = 'test_pdfs'
os.makedirs(test_dir, exist_ok=True)

papers = [
    ('Deep Learning', 'John Smith', 'Deep learning research paper...'),
    ('NLP with Transformers', 'Jane Doe', 'Transformer architectures...'),
]

for i, (title, authors, abstract) in enumerate(papers, 1):
    filename = f'{test_dir}/paper_{i}.pdf'
    c = canvas.Canvas(filename, pagesize=letter)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(100, 750, title)
    c.setFont('Helvetica', 12)
    c.drawString(100, 720, f'Authors: {authors}')
    c.drawString(100, 680, abstract)
    c.save()
"
```

## Supported File Types

- **Format:** PDF only (`.pdf`)
- **Size:** No hard limit (but consider server memory)
- **Content:** Text-based PDFs work best (OCR not included)

## Current Status

✅ **Working:**
- Web UI upload interface
- Multi-file selection
- Progress tracking
- API endpoint `/api/ingest`
- Automatic text extraction
- Vector store indexing

⚠️ **Limitations:**
- Image-only PDFs require OCR (not implemented)
- Very large files (>100MB) may timeout
- No duplicate detection (same file can be uploaded multiple times)

## Testing Results

```bash
# Test upload
curl -X POST -F "file=@test_pdfs/paper_1.pdf" \
  http://localhost:8000/api/ingest

# Check stats
curl http://localhost:8000/api/stats

# Search uploaded papers
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "deep learning", "top_k": 5}'
```

## Troubleshooting

### Upload fails with "Only PDF files are supported"
- Ensure file has `.pdf` extension
- Check file is not corrupted

### "Document ingestion failed"
- Check PDF is text-based (not scanned image)
- Verify server has enough memory
- Check logs: `tail -f logs/app.log`

### No results after upload
- Wait a few seconds for indexing
- Check document count: `curl http://localhost:8000/api/stats`
- Verify vector store is initialized

## Next Steps

🔄 **Planned Enhancements:**
- [ ] Duplicate detection (check DOI/title)
- [ ] OCR support for scanned PDFs
- [ ] Metadata extraction (citations, references)
- [ ] Bulk delete functionality
- [ ] Upload queue system for large batches
- [ ] Progress persistence (resume interrupted uploads)

## Architecture

```
Frontend (HTML/JS)
    ↓
    📤 Multi-file Upload
    ↓
FastAPI Endpoint (/api/ingest)
    ↓
Document Processor (PDF → Text)
    ↓
Text Chunking (configurable size)
    ↓
Embedding Generation (SentenceTransformer)
    ↓
Vector Store (ChromaDB)
    ✅ Searchable Knowledge Base
```

## Performance

**Typical upload times:**
- Small PDF (1-5 pages): ~2-3 seconds
- Medium PDF (10-20 pages): ~5-8 seconds
- Large PDF (50+ pages): ~15-30 seconds

**Batch upload (10 papers):**
- Sequential: ~30-60 seconds
- Recommended: Upload in batches of 5-10 files

## API Reference

### POST `/api/ingest`

**Request:**
- `file`: PDF file (multipart/form-data)
- `title`: Optional paper title
- `authors`: Optional comma-separated authors
- `year`: Optional publication year

**Response:**
```json
{
  "success": boolean,
  "doc_id": string,
  "message": string,
  "chunks_created": integer
}
```

### GET `/api/stats`

**Response:**
```json
{
  "vector_store": {
    "collection_name": string,
    "total_documents": integer,
    "embedding_model": string
  },
  "total_documents": integer
}
```

---

**Last Updated:** November 17, 2025
**Version:** 0.1.0
