# 📚 CORE API Service - Dokumentasi Lengkap

## 🎯 Overview

CORE API Service adalah wrapper Python untuk CORE API v3 yang memudahkan pencarian paper akademik. Service ini sudah terintegrasi dengan system authentication dan error handling.

---

## 🚀 Quick Start

### 1. Setup API Key

Dapatkan API key dari [CORE API](https://core.ac.uk/services/api):

```bash
# Tambahkan ke .env file
CORE_API_KEY=your_api_key_here
# atau
WIZARD_API_KEY=your_api_key_here
```

### 2. Install Dependencies

```bash
pip install requests python-dotenv
```

### 3. Contoh Penggunaan Dasar

```python
from core_api_service import CoreAPIService

# Initialize service
service = CoreAPIService()

# Search papers
results = service.search_outputs(
    keyword="machine learning",
    limit=10,
    year_from=2020,
    year_to=2024
)

print(f"Found {results['total_hits']} papers")
for paper in results['results']:
    print(f"- {paper['title']}")
```

---

## 📖 API Methods

### 1. `search_outputs()` - Pencarian Paper

Method utama untuk mencari paper dengan berbagai filter.

#### Parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `keyword` | str | ✅ Yes | - | Kata kunci pencarian |
| `limit` | int | ❌ No | 10 | Jumlah hasil (max 100) |
| `offset` | int | ❌ No | 0 | Pagination offset |
| `year_from` | int | ❌ No | None | Tahun mulai (inclusive) |
| `year_to` | int | ❌ No | None | Tahun akhir (inclusive) |
| `require_fulltext` | bool | ❌ No | False | Hanya paper dengan full text |
| `require_download` | bool | ❌ No | False | Hanya paper dengan download link |
| `document_types` | List[str] | ❌ No | None | Filter tipe dokumen |

#### Response Format:

```python
{
    "success": True,
    "total_hits": 1234,
    "results": [
        {
            "id": "12345",
            "title": "Paper Title",
            "abstract": "Abstract text...",
            "authors": ["Author 1", "Author 2"],
            "yearPublished": 2023,
            "downloadUrl": "https://...",
            "sourceFulltextUrls": ["https://..."],
            "documentType": "journal article"
        }
    ],
    "limit": 10,
    "offset": 0,
    "query": "generated query string"
}
```

#### Contoh Penggunaan:

```python
# Basic search
results = service.search_outputs(
    keyword="artificial intelligence"
)

# Advanced search dengan filters
results = service.search_outputs(
    keyword="deep learning computer vision",
    limit=50,
    year_from=2020,
    year_to=2024,
    require_fulltext=True,
    document_types=["journal article", "conference paper"]
)

# Pagination
results_page_2 = service.search_outputs(
    keyword="neural networks",
    limit=10,
    offset=10
)
```

---

### 2. `get_output_by_id()` - Detail Paper

Mendapatkan informasi lengkap paper berdasarkan ID.

#### Parameters:

- `output_id` (str): ID paper dari CORE

#### Response:

```python
{
    "id": "12345",
    "title": "Paper Title",
    "abstract": "Full abstract...",
    "authors": [...],
    "yearPublished": 2023,
    "downloadUrl": "https://...",
    "fullText": "Full paper text...",
    "citations": [],
    # ... data lengkap lainnya
}
```

#### Contoh:

```python
paper = service.get_output_by_id("12345")
if paper:
    print(f"Title: {paper['title']}")
    print(f"Authors: {', '.join(paper['authors'])}")
```

---

### 3. `download_output()` - Get Download URL

Mendapatkan link download untuk paper.

#### Parameters:

- `output_id` (str): ID paper dari CORE

#### Response:

```python
{
    "success": True,
    "download_url": "https://core.ac.uk/download/...",
    "title": "Paper Title",
    "output_id": "12345"
}
```

#### Contoh:

```python
download_info = service.download_output("12345")
if download_info['success']:
    print(f"Download: {download_info['download_url']}")
```

---

### 4. `search_works()` - Search Deduplicated Papers

Mencari "works" (paper yang sudah deduplikasi dari berbagai sumber).

#### Parameters:

- `keyword` (str): Kata kunci
- `limit` (int): Jumlah hasil (default: 10)
- `offset` (int): Pagination (default: 0)

#### Contoh:

```python
works = service.search_works(
    keyword="quantum computing",
    limit=20
)
```

---

## 💡 Use Cases & Examples

### Use Case 1: Cari Paper Terbaru dengan Full Text

```python
service = CoreAPIService()

results = service.search_outputs(
    keyword="reinforcement learning",
    limit=20,
    year_from=2024,
    require_fulltext=True,
    require_download=True
)

print(f"✅ Found {results['total_hits']} papers with full text")

for paper in results['results']:
    print(f"\n📄 {paper['title']}")
    print(f"   Year: {paper.get('yearPublished')}")
    print(f"   Download: {paper.get('downloadUrl', 'N/A')}")
```

### Use Case 2: Batch Download Papers

```python
service = CoreAPIService()

# Search papers
results = service.search_outputs(
    keyword="natural language processing",
    limit=10,
    require_download=True
)

# Download all
for paper in results['results']:
    output_id = paper['id']
    download_info = service.download_output(output_id)
    
    if download_info['success']:
        url = download_info['download_url']
        title = download_info['title']
        print(f"✅ {title}: {url}")
```

### Use Case 3: Pagination untuk Dataset Besar

```python
service = CoreAPIService()
keyword = "machine learning healthcare"
batch_size = 100
max_papers = 500

all_papers = []

for offset in range(0, max_papers, batch_size):
    results = service.search_outputs(
        keyword=keyword,
        limit=batch_size,
        offset=offset
    )
    
    all_papers.extend(results['results'])
    print(f"Fetched {len(all_papers)}/{results['total_hits']} papers")
    
    if offset + batch_size >= results['total_hits']:
        break

print(f"\n✅ Total collected: {len(all_papers)} papers")
```

### Use Case 4: Filter by Document Type

```python
service = CoreAPIService()

# Hanya journal articles
results = service.search_outputs(
    keyword="climate change",
    document_types=["journal article"],
    year_from=2020
)

print(f"Journal articles: {results['total_hits']}")

# Hanya conference papers
results = service.search_outputs(
    keyword="climate change",
    document_types=["conference paper"],
    year_from=2020
)

print(f"Conference papers: {results['total_hits']}")
```

---

## 🔧 Integration dengan Flask/FastAPI

### Flask Integration

```python
# app.py
from flask import Flask, request, jsonify
from core_api_service import CoreAPIService

app = Flask(__name__)

@app.route('/api/search', methods=['POST'])
def search_papers():
    data = request.get_json()
    
    service = CoreAPIService()
    results = service.search_outputs(
        keyword=data.get('keyword'),
        limit=data.get('limit', 10),
        year_from=data.get('year_from'),
        year_to=data.get('year_to')
    )
    
    return jsonify(results)

@app.route('/api/paper/<output_id>', methods=['GET'])
def get_paper(output_id):
    service = CoreAPIService()
    paper = service.get_output_by_id(output_id)
    
    if paper:
        return jsonify({"success": True, "paper": paper})
    else:
        return jsonify({"success": False, "error": "Not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
```

### FastAPI Integration

```python
# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from core_api_service import CoreAPIService

app = FastAPI()

class SearchRequest(BaseModel):
    keyword: str
    limit: int = 10
    year_from: int | None = None
    year_to: int | None = None

@app.post("/api/search")
async def search_papers(request: SearchRequest):
    service = CoreAPIService()
    results = service.search_outputs(
        keyword=request.keyword,
        limit=request.limit,
        year_from=request.year_from,
        year_to=request.year_to
    )
    return results

@app.get("/api/paper/{output_id}")
async def get_paper(output_id: str):
    service = CoreAPIService()
    paper = service.get_output_by_id(output_id)
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    return {"success": True, "paper": paper}
```

---

## 📦 Standalone Package Usage

### Cara Copy ke Project Baru:

1. **Copy file `core_api_service.py`**:
```bash
cp backend/app/services/core_api_service.py /path/to/new/project/
```

2. **Setup di project baru**:
```python
# your_script.py
import os
from dotenv import load_dotenv
from core_api_service import CoreAPIService

# Load environment
load_dotenv()

# Use the service
service = CoreAPIService()
results = service.search_outputs(keyword="AI")
```

3. **Requirements untuk project baru**:
```txt
requests>=2.31.0
python-dotenv>=1.0.0
```

---

## ⚠️ Error Handling

### Best Practices:

```python
from core_api_service import CoreAPIService

service = CoreAPIService()

try:
    results = service.search_outputs(keyword="test")
    
    if results['success']:
        print(f"✅ Found {results['total_hits']} papers")
        for paper in results['results']:
            print(f"- {paper['title']}")
    else:
        print(f"❌ Error: {results['error']}")
        
except ValueError as e:
    print(f"❌ Configuration error: {e}")
    print("Make sure CORE_API_KEY is set in .env")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
```

### Common Errors:

| Error | Cause | Solution |
|-------|-------|----------|
| `CORE_API_KEY not found` | API key tidak di-set | Tambahkan ke `.env` |
| `401 Unauthorized` | API key invalid | Periksa API key di CORE dashboard |
| `429 Too Many Requests` | Rate limit exceeded | Tunggu atau upgrade plan |
| `timeout` | Request terlalu lama | Kurangi limit atau coba lagi |

---

## 🎯 Advanced Tips

### 1. Rate Limiting

```python
import time

service = CoreAPIService()
papers = []

for query in ["AI", "ML", "DL"]:
    results = service.search_outputs(keyword=query, limit=10)
    papers.extend(results['results'])
    time.sleep(1)  # Avoid rate limit
```

### 2. Caching Results

```python
import json
from pathlib import Path

def search_with_cache(keyword, cache_dir="cache"):
    cache_file = Path(cache_dir) / f"{keyword}.json"
    
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)
    
    service = CoreAPIService()
    results = service.search_outputs(keyword=keyword)
    
    cache_file.parent.mkdir(exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(results, f)
    
    return results
```

### 3. Retry Logic

```python
import time

def search_with_retry(service, keyword, max_retries=3):
    for attempt in range(max_retries):
        results = service.search_outputs(keyword=keyword)
        
        if results['success']:
            return results
        
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Retry {attempt + 1} after {wait_time}s...")
            time.sleep(wait_time)
    
    return {"success": False, "error": "Max retries exceeded"}
```

---

## 📊 Response Examples

### Success Response:
```json
{
  "success": true,
  "total_hits": 42,
  "results": [
    {
      "id": "123456",
      "title": "Deep Learning for Computer Vision",
      "abstract": "This paper presents...",
      "authors": ["John Doe", "Jane Smith"],
      "yearPublished": 2023,
      "downloadUrl": "https://core.ac.uk/download/pdf/123456.pdf",
      "documentType": "journal article"
    }
  ],
  "limit": 10,
  "offset": 0
}
```

### Error Response:
```json
{
  "success": false,
  "error": "Connection timeout",
  "total_hits": 0,
  "results": []
}
```

---

## 🔗 Links & Resources

- **CORE API Documentation**: https://core.ac.uk/documentation/api
- **Get API Key**: https://core.ac.uk/services/api
- **CORE Dataset**: https://core.ac.uk/services/dataset

---

## 📞 Support

Jika ada pertanyaan atau masalah:

1. Check error message di response
2. Verifikasi API key valid
3. Periksa rate limits di CORE dashboard
4. Lihat CORE API status page

---

## ✅ Checklist Migrasi

Saat pindah ke project baru:

- [ ] Copy file `core_api_service.py`
- [ ] Install dependencies (`requests`, `python-dotenv`)
- [ ] Setup `.env` dengan `CORE_API_KEY`
- [ ] Test dengan simple search
- [ ] Implement error handling
- [ ] (Optional) Tambahkan caching
- [ ] (Optional) Setup rate limiting

---

**Last Updated**: November 2025
**Version**: 1.0.0
**Compatible with**: CORE API v3
