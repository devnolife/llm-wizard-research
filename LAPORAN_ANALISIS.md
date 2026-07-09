# Laporan Analisis Menyeluruh — Wizard Research

> Tanggal analisis: 8 Juli 2026 · Baseline commit: `2925682` · Status perbaikan: diterapkan (uncommitted, lihat §8)
> Analisis arsitektur, kualitas kode, dan rekomendasi perbaikan.
> Project: *Neuro-Symbolic Agentic System for Synthesis Gap Detection* (tesis S2 Teknik Informatika UNHAS).
> Metode: 4 agent eksplorasi paralel (core, API, frontend, eksperimen) + eksekusi suite tes + verifikasi manual temuan kritis.

---

## 1. Ringkasan Eksekutif

| Aspek | Penilaian |
|---|---|
| Arsitektur | **Baik** — pemisahan 4 fase jelas, DI konsisten, pipeline eksperimen terstruktur |
| Kualitas kode inti | **Cukup** — solid tapi ada file raksasa, broad except, kontrak data longgar |
| Tes | **Sehat** — 304/304 pass (~50 dtk), tapi API/agents/tools nyaris tanpa coverage |
| Konfigurasi | **Bermasalah** — dua .env saling bertentangan dengan skema key berbeda |
| Dokumentasi | **Sangat lengkap tapi mulai basi** — port salah, model embedding lama, klaim loop agentic tidak persis |
| Kesiapan eksperimen tesis | **Hampir** — H6/H7 ada hasil; H9 (nli/no-nli) belum dijalankan; statistik perlu penguatan |

**Skor keseluruhan: solid untuk prototipe riset** — dengan 3 bug/masalah kritis yang layak diperbaiki sebelum sidang/publikasi.

---

## 2. Peta Arsitektur (hasil observasi kode, bukan README)

```
INGESTION            pypdf (+OCR fallback svc :10000) → section-aware chunking
                     → SentenceTransformer multilingual → ChromaDB (research_papers_ml)
FACT EXTRACTION      FactExtractor (LLM + recovery JSON berlapis + pattern fallback)
                     → SPO triples → FactTable (thread-safe RLock) → KG Builder (networkx)
AGENTIC ANALYSIS     LangGraph: observe → think → act → evaluate  (max 3 iterasi)
                     ├─ observe: RAG retrieval + fact extraction + KG rebuild
                     ├─ think:   GapAnalyzer (3 indikator Cooper) + NLI cross-check
                     ├─ act:     RuleEngine (9 aturan F/C/K) + rekomendasi
                     └─ evaluate: self-critic → needs_revision? loop : END
API                  FastAPI (:8001) — job async in-memory + SSE/polling status
FRONTEND             React 19 SPA (:5173, proxy /api → 8001), context-based state
EKSPERIMEN           5 fase, mode: full | no-rule-engine | linear-baseline | nli | no-nli
```

**Catatan arsitektural penting:** loop agentic yang diimplementasi adalah
*Observe→Think→Act→Evaluate* dengan tool **hard-wired per fase** — bukan
*Plan→Act→Observe→Reflect* dengan pemilihan tool dinamis seperti diklaim README/tesis
(`coordinator.py:88-183`). Selaraskan narasi tesis dengan implementasi.

---

## 3. Temuan Kritis (perbaiki dulu)

### K1. BUG: 3-Layer Discriminator tidak pernah aktif via NLI tool ⚠️ *terverifikasi manual*
`nli_checker_tool.py:68` membaca `classified.layers_used`, tapi dataclass
`ClassifiedRelation` (`relation_classifier.py:63-73`) **tidak punya field itu** →
`AttributeError` selalu terjadi → ditangkap `except` → hasil classifier 3-layer
**selalu dibuang** dan jatuh ke LLM fallback. Klaim "3-Layer Discriminator" pada jalur
NLI tool tidak pernah berjalan. Bug ini lolos karena `tools/` tidak punya unit test.
**Fix:** tambah field `layers_used` (atau derive dari `rule_validated`/`evidence_markers`) + unit test.

### K2. Konfigurasi .env ganda yang saling bertentangan ⚠️ *terverifikasi manual*
`load_dotenv()` menemukan `backend/.env` (bukan root `.env`). Masalahnya `backend/.env`
memakai **skema key mati** yang tidak dibaca `config_loader.py`: `LLM_MODEL_NAME` (loader baca
`OLLAMA_MODEL`), `VECTOR_DB_COLLECTION` (loader baca `CHROMA_COLLECTION_NAME`),
`RETRIEVAL_MIN_RELEVANCE_SCORE` (loader baca `MIN_RELEVANCE_SCORE`), plus `API_PORT=8000` vs root `8001`.
Akibat: root `.env` (berisi `OLLAMA_*`, `OCR_*`) **tidak pernah dimuat** — instruksi README
`echo "OCR_ENABLED=true" >> .env` tidak berefek; konfigurasi efektif = default YAML, bukan .env Anda.
**Fix:** satukan ke satu `.env` dengan key yang benar-benar dibaca loader; perbaiki `.env.example`; muat dotenv dengan path eksplisit.

### K3. Rule Engine default-PASS saat bukti tidak ada
Bila entity linking gagal (method/domain/finding tak terhubung di KG), banyak aturan
**lolos otomatis** (`rule_engine.py:397-399,455-456,509-510,549-554,589-590,655-656`).
Ini melemahkan klaim validasi simbolik — klaim tanpa bukti justru tidak tersaring.
**Fix:** default ke `FLAG`/`UNKNOWN`, bukan `PASS`; laporkan "insufficient evidence" eksplisit.

### K4. Hasil eksperimen H9 belum ada
Mode `nli`/`no-nli` ada di kode, tapi **tidak ada file hasil** di `experiments/results/`;
`compare_results.py:17-35` juga hard-filter mode sehingga tak bisa merangkum H9.
**Fix:** jalankan kedua mode + perluas compare_results — ini prasyarat klaim H9 di BAB IV.

### K5. Metodologi statistik rawan kritik penguji
`run_multi.py:128-163`: Mann-Whitney U **unpaired** pada confidence yang di-*pool* lintas
indikator (melanggar independensi — banyak indikator per run), tanpa koreksi multiple
comparison; run juga tidak di-seed (hanya temperature 0.3).
**Fix:** uji per-run (n=3+ per mode) atau hierarkis; koreksi Holm; seed eksplisit.

### K6. Job analisis hanya in-memory
`_analysis_jobs = {}` (`analysis.py:50-51`) — restart backend menghilangkan semua status;
frontend polling gagal tanpa penjelasan. **Fix:** persist ke SQLite/disk.

### K7. Upload tidak divalidasi memadai
Hanya cek suffix `.pdf`; tanpa MIME sniffing & size limit (config `max_file_size_mb: 50`
tidak ditegakkan); temp file memakai filename asli tanpa sanitasi (risiko path traversal);
cleanup tanpa `finally` (`analysis.py:527-537`; `documents.py:64-111`).

---

## 4. Temuan Penting

| # | Temuan | Lokasi |
|---|---|---|
| P1 | `AnalysisResults.jsx` **2.247 baris** — parsing+polling+ekspor+8 tab+2 mode dalam satu file | frontend/pages |
| P2 | Polling rekursif `setTimeout` tanpa clear timer; `useApi` tanpa AbortController → race/stale updates | AnalysisResults.jsx:220-248 |
| P3 | Akses API frontend tidak terpusat — `VITE_API_URL`+fetch diduplikasi padahal ada axios instance dgn error-normalization bagus | UploadPage, GraphPage vs api.js |
| P4 | LLM service: `timeout=120` di config **tidak diteruskan** ke `client.chat()`; tanpa retry; parser JSON tersebar | llm_service.py:261-362 |
| P5 | Config drift: fallback loader `all-MiniLM-L6-v2`/`research_papers`/port 8000 ≠ YAML multilingual/`research_papers_ml`/8001 | config_loader.py:221-258 |
| P6 | File inti raksasa: fact_extractor 975, analyzer 868, rule_engine 833, coordinator 814 baris (plus pipeline legacy mati di coordinator:693-760) | backend/app/core |
| P7 | Kontrak data longgar antar modul (dict/list campur) — sumber bug tipe K1 | coordinator, tools |
| P8 | Endpoint tak terpakai frontend: `/api/models*`, `/api/sources/status`, `/api/graph` vs `/api/kg/graph` (duplikat konsep); paper search kirim `embedding_model` yang di-ignore backend | routes/* |
| P9 | Tanpa coverage tes: seluruh API routes, coordinator, 4 agent, 4/5 tools, graph_builder | tests/ |
| P10 | requirements.txt semua `>=` tanpa lock — eksperimen tesis tidak reprodusibel bit-exact | backend/requirements.txt |
| P11 | Reproduksibilitas eksperimen: hardcoded paths; `--skip-ingest` bisa drift bila manifest ≠ korpus tersimpan | run_experiment.py:37-46,972-988 |
| P12 | docker-compose basi: port 8000, mount `./configs` tak ada, `network_mode: host`+ports (diabaikan), Neo4j wajib padahal `neo4j.enabled=false` | docker-compose.yml |

## 5. Temuan Minor (ringkas)

- README: port 8000 (asli 8001); masih menyebut `all-MiniLM-L6-v2`; komentar basi sama di `config.yaml`
- Makefile: `init-db` memanggil script yang tidak ada; `format` → `npm run format` tak terdefinisi; `lint` pakai pylint yang tidak di-requirements
- Broad `except Exception` menyebar (core, routes, experiments) — kegagalan jadi hasil parsial senyap
- Frontend: validasi upload hanya MIME client-side; ErrorBoundary cuma bungkus `<main>`; key list pakai index; aria-label kurang; campur bahasa ID/EN
- Magic numbers: `top_k`, `max_iterations=3`, year-cutoff `>=2014`, timeout/threshold frontend
- Log tercecer di root (`backend_run.log` 90KB, `server.log` 56KB) — gitignored tapi mengotori
- Neo4j password dev hardcoded di docker-compose (risiko rendah, service disabled)
- pytest butuh `PYTHONPATH=backend` manual (tanpa itu `ModuleNotFoundError: app`)
- Cohen's kappa hanya menghitung 2 rater pertama (`compute_metrics.py:252-260`)

## 6. Kekuatan yang Layak Dipertahankan

1. **Suite tes inti sehat**: 304/304 pass dalam ~50 dtk; rule_engine 67 tes, relation_classifier 57, fact_table 52
2. **Recovery JSON berlapis** di FactExtractor (fenced → bare → salvage truncated) + fallback pattern saat LLM mati
3. **DI konsisten** via constructor; FactTable thread-safe (RLock)
4. **Pipeline eksperimen 5 fase** dgn mode ablation jelas + tooling statistik/expert-eval/kalibrasi lengkap — di atas rata-rata prototipe tesis
5. **Config precedence jelas** (env > YAML > default); CORE API client punya backoff eksponensial; OCR fallback degradasi anggun
6. **Error normalization axios** di frontend rapi; SSE + fallback polling

## 7. Rekomendasi Berprioritas

**Segera (sebelum eksperimen final/sidang):**
1. Fix bug `layers_used` (K1) + unit test tools — klaim 3-layer discriminator bergantung ini
2. Satukan konfigurasi .env (K2) — saat ini eksperimen Anda mungkin berjalan dgn config yang berbeda dari yang Anda kira
3. Jalankan H9 `nli`/`no-nli` + perluas `compare_results.py` (K4)
4. Perkuat statistik: paired/per-run test + koreksi Holm + seed (K5)
5. Ubah default-PASS Rule Engine → FLAG (K3), lalu re-run eksperimen full

**Jangka pendek:**
6. `pip freeze > requirements.lock` untuk reproduksibilitas tesis (P10)
7. Persist job analisis + hardening upload (K6, K7)
8. Teruskan timeout ke Ollama client + retry + parser JSON terpusat (P4)
9. Tambah tes API routes (httpx) & tools (P9)

**Jangka menengah (kualitas hidup):**
10. Pecah `AnalysisResults.jsx` + kelola timer/AbortController (P1, P2)
11. Pecah 4 file inti raksasa; hapus pipeline legacy; typed models (Pydantic) antar modul (P6, P7)
12. Sinkronkan README/Makefile/docker-compose dgn realita (port 8001, model multilingual, target mati)
13. Selaraskan narasi tesis: loop = Observe-Think-Act-Evaluate, tool statis per fase

---
*Statistik: 36 temuan — 7 kritis, 13 penting, 16 minor. Verifikasi manual dilakukan utk K1 (bug nyata), K2 (shadowing .env), dan koreksi 2 dugaan agent yang salah (find_paths_between_entities ada; .env.example ada).*

---

## 8. Addendum — Perbaikan Diterapkan (fleet mode)

Semua diterapkan sebagai perubahan **uncommitted** di working tree (HEAD `2925682`), 22 file diubah + 5 file baru (+813/−258). Suite penuh: **325 pass, 6 skip** (baseline 304 → +21 tes baru), 0 gagal.

| Temuan | Perbaikan |
|---|---|
| K1 bug `layers_used` | Field `layers_used` ditambahkan ke `ClassifiedRelation` + diisi di kedua jalur classify; NLI tool kini benar-benar memakai 3-layer classifier; tes baru `test_nli_checker_tool.py` |
| K2 .env ganda | `load_project_env()`: root `.env` dimuat dulu, `backend/.env` sebagai override eksplisit; key mati dimigrasi (`LLM_MODEL_NAME`→`OLLAMA_MODEL`, `VECTOR_DB_*`→`CHROMA_*`, dll); port seragam 8001; `.env.example` diperbarui |
| K3 default-PASS | Config baru `rule_engine.defaults.on_missing_evidence: flag` (default) — missing evidence → FLAG −0.05; mode `pass` mengembalikan perilaku lama; kasus not-applicable tetap PASS |
| K5 statistik | `--seed` di run_experiment (random+numpy, tercatat di JSON); run_multi: uji per-run (bukan pooled) sebagai primary + Holm-Bonferroni; pooled dilabeli exploratory |
| K4 (kode) | compare_results.py kini mencakup nli/no-nli — cetak "not available" bila belum dijalankan |
| K6 job in-memory | `job_store.py`: persist JSON atomik; job RUNNING saat crash → "interrupted" saat reload |
| K7 upload | `upload_validation.py`: sanitasi filename, cek magic bytes %PDF, size cap dari config, cleanup try/finally |
| P4 LLM timeout | timeout config diteruskan ke `ollama.Client`; retry 2× backoff hanya utk error transien (ConnectError/5xx) |
| Minor docs | README port 8001 + model multilingual + loop "Observe→Think→Act→Evaluate"; Makefile (init-db dihapus, lint→flake8, format dibenahi); docker-compose ditandai template + disinkronkan |

**Belum dilakukan (butuh keputusan/waktu Anda):**
1. **Re-run eksperimen** — perubahan K3 mengubah hasil deteksi gap; jalankan ulang `full`/ablation utk angka final tesis (butuh model `llama3.2:latest` di Ollama; saat ini hanya `gemma4:latest` terpasang)
2. **Run H9**: `python experiments/run_experiment.py --mode nli --skip-ingest` + `--mode no-nli`
3. Refactor jangka menengah: pecah `AnalysisResults.jsx` (2.247 baris) & 4 file inti backend; `pip freeze > requirements.lock`
4. Commit perubahan setelah review: `git add -A && git commit`
