# 🎯 Quick Start Guide - Upload & Search Papers

## Step-by-Step Guide

### 1️⃣ Start the Server

```bash
cd /home/devnolife/wizard-research
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Wait for: `✅ Vector store initialized` 

### 2️⃣ Open Web Interface

Open browser: **http://localhost:8000**

---

## 📤 Upload PDF Papers

### Method 1: Web Interface (Easiest)

1. **Click "📁 Select PDF Files"**
   - Select one or multiple PDF files
   - Supported: `.pdf` files only

2. **Review Selected Files**
   - See file name and size
   - Remove unwanted files with "✕" button

3. **Click "⬆️ Upload X File(s)"**
   - Files will upload automatically
   - See real-time progress for each file
   - ✅ Success: Shows chunks created
   - ❌ Error: Shows error message

4. **After Upload Success**
   - Click **"📊 View Database Stats"** to see total papers
   - Click **"🔍 Search Uploaded Papers"** to test search
   - Click **"⬆️ Upload More"** to add more files

### Method 2: Command Line

**Single file:**
```bash
curl -X POST \
  -F "file=@paper.pdf" \
  -F "title=My Research Paper" \
  -F "authors=John Doe, Jane Smith" \
  -F "year=2024" \
  http://localhost:8000/api/ingest
```

**Bulk upload (all PDFs in directory):**
```bash
./bulk_upload.sh /path/to/pdfs/
```

---

## 🔍 Search Papers

### Option 1: Search Uploaded Papers (Local)

After uploading:
1. Click **"🔍 Search Uploaded Papers"**
2. Enter search query (e.g., "machine learning")
3. See top results with relevance scores

### Option 2: Search External APIs

1. Enter query in search box
2. Select data sources (CORE, arXiv, etc.)
3. Click **"🔍 Search Papers"**
4. Results show papers from external APIs
5. Click **"✅ Ingest to DB"** to add paper to your database

---

## 📊 Check Database Status

### Web Interface:
- After upload, click **"📊 View Database Stats"**

### API Endpoint:
```bash
curl http://localhost:8000/api/stats | python3 -m json.tool
```

**Output:**
```json
{
  "vector_store": {
    "collection_name": "research_papers",
    "total_documents": 1435,
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
  }
}
```

---

## 🧪 Quick Test

### Test 1: Create Sample PDFs
```bash
cd /home/devnolife/wizard-research
python3 -c "
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

os.makedirs('test_pdfs', exist_ok=True)
c = canvas.Canvas('test_pdfs/test_paper.pdf', pagesize=letter)
c.setFont('Helvetica-Bold', 16)
c.drawString(100, 750, 'Deep Learning Research')
c.setFont('Helvetica', 12)
c.drawString(100, 720, 'Authors: John Doe')
c.drawString(100, 680, 'This is a test paper about deep learning.')
c.save()
print('✅ Created test_pdfs/test_paper.pdf')
"
```

### Test 2: Upload via Web
1. Open http://localhost:8000
2. Click "📁 Select PDF Files"
3. Choose `test_pdfs/test_paper.pdf`
4. Click "⬆️ Upload 1 File(s)"
5. Wait for ✅ Success message
6. Click "🔍 Search Uploaded Papers"
7. Search for "deep learning"

### Test 3: Upload via Command
```bash
curl -X POST \
  -F "file=@test_pdfs/test_paper.pdf" \
  http://localhost:8000/api/ingest
```

---

## ✅ Features Summary

| Feature | Status | Description |
|---------|--------|-------------|
| 📤 Multi-file Upload | ✅ | Select multiple PDFs at once |
| 🔄 Real-time Progress | ✅ | See upload status for each file |
| 📊 Database Stats | ✅ | View total papers and settings |
| 🔍 Local Search | ✅ | Search in uploaded papers |
| 🌐 External Search | ✅ | Search CORE, arXiv, etc. |
| ✅ Ingest External | ✅ | Add external papers to DB |
| 📝 Metadata Support | ✅ | Title, authors, year |
| ❌ Error Handling | ✅ | Clear error messages |
| 📦 Chunking | ✅ | Automatic text chunking |
| 🤖 Embeddings | ✅ | SentenceTransformer/Ollama |

---

## 🐛 Troubleshooting

### "Only PDF files are supported"
- Ensure file extension is `.pdf`
- Check file is not corrupted

### "Failed to upload"
- Check server is running: `curl http://localhost:8000/health`
- Check logs: `tail -f /tmp/wizard_server.log`
- Verify PDF is text-based (not scanned image)

### "No results found"
- Check database has papers: Click "📊 View Database Stats"
- Try different search query
- Wait a few seconds after upload for indexing

### Upload hangs/timeout
- File too large (>100MB)
- Server out of memory
- Network issue

---

## 🎯 Recommended Workflow

1. **Collect PDFs** in a folder (e.g., `my_papers/`)
2. **Bulk upload** via script: `./bulk_upload.sh my_papers/`
3. **Verify** upload: Click "📊 View Database Stats"
4. **Search** papers: Click "🔍 Search Uploaded Papers"
5. **Add more** as needed: Click "⬆️ Upload More"

---

## 📈 Current Status

**Database:** 1,435 documents indexed
**Model:** sentence-transformers/all-MiniLM-L6-v2
**Storage:** ChromaDB (./chroma_db)

✨ **Ready to use!**

---

**Last Updated:** November 17, 2025
