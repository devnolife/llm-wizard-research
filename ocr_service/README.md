# Unlimited-OCR Service

A standalone GPU microservice that runs [Baidu Unlimited-OCR](https://github.com/baidu/Unlimited-OCR)
behind an OpenAI-compatible [SGLang](https://github.com/sgl-project/sglang) API.
The backend uses it as a **fallback** to parse scanned / image-only PDFs that
`pypdf` cannot extract text from.

> **Why a separate service?** Unlimited-OCR / SGLang require `torch ~2.9–2.10`
> and a vendored SGLang wheel, which conflict with the backend's `torch 2.4.1`.
> This service lives in its own `uv` virtualenv so the two never mix. The backend
> only talks to it over HTTP (needs just `requests` + `pymupdf`).

## 1. Setup (one-time)

```bash
bash ocr_service/setup.sh
```

This will:
- create an isolated `.venv` (Python 3.12),
- download + install the vendored SGLang wheel, `kernels==0.11.7`, `pymupdf`,
- download the model `baidu/Unlimited-OCR` (~6.7 GB) into `models/Unlimited-OCR`,
- generate `ngram_processor.txt` (the anti-repetition logit processor string the
  backend forwards on each request).

## 2. Start the server

```bash
bash ocr_service/run_server.sh
```

Defaults: GPU `1`, port `10000`, served model name `Unlimited-OCR`.
Override via env, e.g. `OCR_GPU=0 OCR_PORT=10000 bash ocr_service/run_server.sh`.

Health check:
```bash
curl http://127.0.0.1:10000/health
```

## 3. Enable the fallback in the backend

In `.env` (project root):
```
OCR_ENABLED=true
OCR_SERVICE_URL=http://127.0.0.1:10000
```
Restart the backend. From now on, when an ingested PDF yields fewer than
`OCR_MIN_CHARS_PER_PAGE` characters per page on average, it is rasterized and
parsed by this service instead. Ingested chunks carry `ocr_used=true` /
`extraction_method="ocr"` metadata.

## Environment variables

| Var | Default | Meaning |
|-----|---------|---------|
| `OCR_ENABLED` | `false` | Turn the backend fallback on/off |
| `OCR_SERVICE_URL` | `http://127.0.0.1:10000` | Server base URL |
| `OCR_IMAGE_MODE` | `gundam` | `gundam` (dense single page) or `base` |
| `OCR_DPI` | `200` | PDF page rasterization DPI |
| `OCR_CONCURRENCY` | `4` | Parallel page requests |
| `OCR_TIMEOUT` | `1200` | Per-request timeout (s) |
| `OCR_MIN_CHARS_PER_PAGE` | `50` | Below this avg → treat as scanned |
| `OCR_NGRAM_SIZE` / `OCR_NGRAM_WINDOW` | `35` / `128` | Anti-repetition params |
| `OCR_GPU` | `1` | `CUDA_VISIBLE_DEVICES` for the server |
| `OCR_PORT` | `10000` | Server port |
| `OCR_MODEL_DIR` | `ocr_service/models/Unlimited-OCR` | Model path |

## Files

| File | Purpose |
|------|---------|
| `setup.sh` | Create venv, install deps, download model, gen ngram string |
| `run_server.sh` | Launch the SGLang OpenAI-compatible server |
| `gen_ngram_processor.py` | Produce `ngram_processor.txt` (runs in this venv) |
| `models/` | Downloaded model weights (git-ignored) |
| `.venv/` | Isolated environment (git-ignored) |

## Notes
- The backend degrades gracefully: if the service is down or OCR fails, ingestion
  silently keeps the `pypdf` result — it never breaks.
- The model is ~6.7 GB and needs an NVIDIA GPU (bf16). One L40S is plenty.
