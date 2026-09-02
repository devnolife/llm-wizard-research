# Laporan Analisis Menyeluruh — Wizard Research

> Tanggal analisis: 8 Juli 2026 · Baseline commit: `2925682` · Status perbaikan: diterapkan (uncommitted, lihat §8)
> **Audit ulang 3 September 2026** (baseline `66c5ab1`): lihat §10.
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
| Kesiapan eksperimen tesis | **Siap** — H6/H7/H9 lengkap (5 run/mode, seeded, Holm-corrected); lihat Addendum §9 |

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

> **Status per 1 Agustus 2026: seluruh K1–K7 sudah resolved** — lihat Addendum §8 (perbaikan) dan §9 (verifikasi ulang). Bagian ini dipertahankan sebagai catatan historis audit.

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

---

## 9. Addendum — Verifikasi Ulang (1 Agustus 2026)

Seluruh item "belum dilakukan" di §8 **sudah selesai** dan diverifikasi ulang terhadap kode aktual:

| Item | Status | Bukti |
|---|---|---|
| Re-run eksperimen + H9 | ✅ Selesai | 5 run/mode (seeds 43–47) untuk kelima mode dgn `llama3.2:latest` + 3 run `gpt-oss:latest`; hasil di `backend/experiments/results/` (`experiment_nli_*.run1-5.json`, dst) |
| Agregasi statistik | ✅ Selesai (diperbarui 5 Agu 2026) | `run_multi.py --skip-runs --runs 7` → `multirun_stats_llama3.2_latest.md`; H9 (nli n=7 vs no-nli n=5): indikator 24.3±2.3 vs 15.2±1.9, U=35 (pemisahan sempurna), p=0.0055, **p Holm=0.0331 — SIGNIFIKAN α=0.05**, Cliff's δ=1.0 (large), Δmed=8 [5,13]; mean conf/run juga signifikan (p Holm=0.0331, Δmed=0.038); H6/H7 tidak signifikan |
| Pecah `AnalysisResults.jsx` (P1) | ✅ Selesai | Tab diekstrak ke `frontend/src/components/pages/analysis-tabs/` (10 komponen + `constants.js`); `AnalysisResults.jsx` tinggal orchestrator |
| Job persistence (K6) | ✅ Ditingkatkan | `job_store.py` kini **SQLite** (`analysis_jobs.sqlite3`): atomic claim, recovery restart, retry backoff; `analysis_queue.py` durable dgn ThreadPoolExecutor |
| Test suite | ✅ Hijau | **351 pass, 2 skip** (naik dari 325); `test_relation_classifier.py` + `test_rule_engine.py` = 112 pass; `test_nli_checker_tool.py` pass |

**Catatan framing tesis (H9, diperbarui 5 Agu 2026):** dengan penambahan 2 run nli (seeds 48–49) desain menjadi n₁=7 vs n₂=5 dan kedua variabel menunjukkan pemisahan sempurna antar kelompok — **H9 terkonfirmasi signifikan pasca-Holm (p=0.0331 < 0.05, δ=1.0)**. Riwayat: pada n=5/5 (1 Agu) p Holm=0.0716, belum signifikan. Detail di `LAPORAN_VERIFIKASI.md` §4.

**Kesimpulan:** semua temuan kritis (K1–K7) dan P1 telah resolved di kode; laporan §3 dan §7 di atas dipertahankan sebagai catatan historis audit.

---

## 10. Addendum — Audit Ulang 3 September 2026

> Baseline: commit `66c5ab1` (*feat: satukan alur penelitian jadi satu halaman berpanduan*).
> Metode: eksekusi suite tes + lint + build sebagai baseline, 3 agent eksplorasi paralel (API/services, core, frontend + Streamlit) dengan dua putaran masing-masing, lalu **verifikasi manual/reproduksi** untuk setiap temuan yang ditindaklanjuti.
> Seluruh perubahan di bawah **belum di-commit** — tinjau dengan `git diff`, batalkan per item dengan perintah di §10.4.

### 10.1 Baseline (sebelum perubahan apa pun)

| Pemeriksaan | Hasil |
|---|---|
| `pytest tests/` (backend) | **626 pass, 2 skip** (~64 dtk) |
| `flake8 app` — gerbang CI `.github/workflows/quality.yml` | **exit 1** → CI *Quality Gate* **merah di `main`** (14 temuan F401/F841) |
| ESLint + `vite build` (frontend) | bersih |

### 10.2 Temuan yang ditindaklanjuti

| # | Tingkat | Temuan | Bukti |
|---|---|---|---|
| A1 | **Kritis** | `GET /api/analysis-status/{job_id}` **HTTP 500** — `_set_analysis_job(job_id, **job)` sedangkan `job` memuat kunci `job_id` → `TypeError: multiple values for argument 'job_id'`. Terpicu pada (a) job selesai yang belum punya `rule_engine_report`/`fact_table_stats`/`reasoning_trace`, dan (b) **setiap request `lang=id`** — bahasa bawaan UI React (`AnalysisResults.jsx: useState('id')`). Selain itu terjemahan (puluhan panggilan LLM sinkron) berjalan di dalam `async def` → memblokir event loop dan semua request lain. | Direproduksi langsung sebelum diubah; `analysis.py` (dulu) baris ~669 & ~717 |
| A2 | **Kritis** | Job pipeline penelitian (`POST /api/research/start`) **melewati antrean durable**: status langsung `running` + `threading.Thread` lepas. Akibat: tak dibatasi worker, **tak bisa dibatalkan**, dan setelah restart `load_jobs()` mengantrekan ulang lalu handler lama 8-tahap menjalankannya (komentar di kode mengakui hal ini pernah terjadi). `/reanalyze` pada job penelitian juga membuat salinan **tanpa** field `pipeline` → dijalankan sebagai analisis lama. | `research.py` (dulu) baris 170–200; `analysis.py` `reanalyze_job` |
| A3 | **Penting** | **Auto-retry tanpa batas**: `retry_job()` mereset `attempt=0`, sementara `AnalysisJobQueue._execute` mengandalkan `attempt < max_attempts`. Job yang selalu gagal (mis. PDF hilang) di-*requeue* tiap ~1 dtk selamanya. Bug lama, tetapi A2 membuat job penelitian ikut terpapar. | Direproduksi oleh tes `test_automatic_retry_stops_at_max_attempts` (gagal sebelum perbaikan: `assert 0 == 1`) |
| A4 | **Penting** | `flake8 app` gagal → CI merah (lihat §10.1). Termasuk 8 import helper mati di `analysis.py`, `AdjudicationResult`/`Calibrator` tak terpakai di `analyzer.py`, variabel `stopwords`/`index` tak terpakai. | keluaran flake8 |
| A5 | **Penting** | `_add_uploaded_paper_similarity()` dipanggil **di dalam** loop ingest per-PDF → seluruh paper di-*embed* ulang pada tiap iterasi (O(n²) encode) dan hasil antara ditimpa. | `analysis.py` `process_auto_analysis`, loop `for i, pdf_path` |
| A6 | Minor | `papers.py` `fetch_pdf`: `tempfile.mkstemp()` mengembalikan fd yang tidak pernah ditutup → kebocoran fd per unduhan. | `papers.py:177` |
| A7 | Minor | `config_loader.py` fallback `collection_name="research_papers"` ≠ `config.yaml` (`research_papers_ml`) — tanpa YAML aplikasi diam-diam memakai koleksi lain. | `config_loader.py:266` vs `config.yaml:21` |
| A8 | Minor | Frontend: `GraphPage.jsx` `setTimeout` tidak di-*clear* saat unmount; `UploadPage.jsx` nilai `<input type=file>` tak direset (memilih ulang file yang sama tidak memicu `onChange`) dan `key={index}` pada daftar file. | `GraphPage.jsx:84–90`, `UploadPage.jsx:34–39,147` |

### 10.3 Perubahan yang diterapkan (uncommitted)

| Item | Perubahan | File |
|---|---|---|
| A1 | Simpan hanya field yang berubah (`results=` / `results_id=`); logika terjemahan dipisah ke `_translate_results()`; **lock per job** agar poller paralel tidak menerjemahkan ganda; endpoint menjadi `def` sinkron (FastAPI menjalankannya di threadpool) agar LLM tidak memblokir event loop. **+2 tes regresi**. | `backend/app/api/routes/analysis.py`, `backend/tests/test_api.py` |
| A2 | `AnalysisJobQueue.register(pipeline, handler)` + `resolve_handler()` — *dispatch* berdasarkan `job["pipeline"]`, handler lama tetap *default*; job tanpa handler → `failed` eksplisit, bukan menggantung. `research_pipeline.run_research_job()` sebagai handler antrean (membaca `payload.pdf_paths`/`output_dir`). **Pembatalan kooperatif**: `ResearchCancelled` dicek antar tahap dan tiap 10 kandidat di ekstraksi gap; event baru `phase.cancelled`; status `cancelled` tidak memicu retry. `/api/research/start` kini `queued` + `max_attempts` + `notify()`. `/reanalyze` mempertahankan `pipeline` dan memberi `output_dir` baru. `main.py` mendaftarkan handler. **Tes**: `test_research_api.py` (disesuaikan), `test_research_pipeline.py` (+6: handler antrean, kegagalan per tahap, PDF hilang, pembatalan), `test_analysis_queue.py` (+3 dispatch), `test_api.py` (+1 reanalyze). | `analysis_queue.py`, `research_pipeline.py`, `routes/research.py`, `routes/analysis.py`, `main.py`, 4 file tes |
| A2′ | Streamlit mengikuti kontrak baru: `cancel_job()` + tombol ⏹️ di Dashboard dan wizard Analisis Penelitian; wizard menangani status `queued` (pesan “menunggu giliran worker”) dan `cancelled`; timeline mengenali `phase.cancelled`. README tool diperbarui. | `tools/process_monitor/{common,research_common,page_dashboard,page_research_wizard}.py`, `README.md` |
| A3 | `retry_job(..., reset_attempts=True)` — endpoint `/retry` manual tetap memberi kuota baru (perilaku lama, tes lama tetap lolos); auto-retry antrean memakai `reset_attempts=False` sehingga `max_attempts` benar-benar tercapai. **+1 tes**. | `job_store.py`, `analysis_queue.py`, `test_analysis_queue.py` |
| A4 | Hapus 14 import/variabel tak terpakai → `flake8 app` **exit 0**. | `analysis.py`, `analyzer.py`, `graph_metrics.py`, `corpus_relevance.py`, `themes.py` |
| A5 | Panggilan similarity dipindah ke **setelah** loop ingest (dihitung sekali). | `analysis.py` |
| A6 | `fd, name = mkstemp(); os.close(fd)`. | `papers.py` |
| A7 | Fallback `collection_name` → `research_papers_ml`. | `config_loader.py` |
| A8 | `clearTimeout` di cleanup effect; `e.target.value = ''` setelah membaca file; key stabil `name-size-lastModified`. | `GraphPage.jsx`, `UploadPage.jsx` |

**Verifikasi akhir**: `flake8 app` exit 0 · `pytest tests/` **639 pass, 2 skip** (+13 tes) · ESLint bersih · `vite build` sukses.

### 10.4 Cara meninjau & membatalkan per item

Semua perubahan ada di *working tree*. Tinjau dengan `git diff <file>`; batalkan dengan `git checkout -- <file...>`:

| Batalkan | Perintah |
|---|---|
| **Semua** | `git checkout -- . && git checkout -- LAPORAN_ANALISIS.md` |
| Hanya A2 + A2′ (refactor antrean; A1/A3/A4/A5 tetap) | tidak bisa per-file murni karena `analysis.py`/`test_api.py` juga memuat A1/A4/A5 — gunakan `git diff backend/app/api/routes/research.py backend/app/services/research_pipeline.py backend/app/main.py tools/process_monitor/` untuk menilai, lalu `git checkout -- backend/app/api/routes/research.py backend/app/services/research_pipeline.py backend/app/main.py backend/tests/test_research_api.py backend/tests/test_research_pipeline.py tools/process_monitor/` dan hapus `register()`/`resolve_handler()` di `analysis_queue.py` serta blok `pipeline=`/`output_dir` di `reanalyze_job` secara manual |
| Hanya frontend (A8) | `git checkout -- frontend/src/components/pages/GraphPage.jsx frontend/src/components/pages/UploadPage.jsx` |
| Hanya A6/A7 | `git checkout -- backend/app/api/routes/papers.py backend/app/utils/config_loader.py` |

Bila diterima: `git add -A && git commit` (disarankan dipecah: *fix(api)* A1, *feat(queue)* A2/A2′/A3, *chore(lint)* A4, *perf* A5, *fix* A6–A8).

### 10.5 Temuan yang **belum** ditindaklanjuti (butuh keputusan Anda)

Terverifikasi dari kode oleh agent (dikutip), tidak diubah karena menyentuh perilaku ilmiah/eksperimen atau di luar cakupan perbaikan aman:

| # | Prioritas | Temuan | Lokasi | Saran |
|---|---|---|---|---|
| B1 | **Tinggi** | `FactTable.add_fact()` **tidak mendedup** triple `(subject, predicate, object)`; `extract_from_text()` selalu menjalankan `_extract_pattern_relations()` di atas hasil LLM → fakta ganda menggembungkan hitungan SPO & metrik KG (mempengaruhi angka “Fakta SPO” di BAB IV). | `fact_table.py:234`, `fact_extractor.py:200–236` | Dedup pada insert dengan kunci `(subject_id, predicate, object_id, source_paper)`; **re-run eksperimen** bila diubah |
| B2 | **Tinggi** | Penanda kausal (“causes”, “leads to”, “reduces”, …) dipetakan ke `APPLIES_TO`; hanya `improves/enhances/increases` → `IMPROVES`. `PredicateType` **tidak punya** predikat CAUSES. Relasi kausal hilang dari KG dan uji konsistensi. | `fact_extractor.py:146,622` | Tambah `CAUSES` (atau pakai `CORRELATES_WITH` sesuai desain *downgrade*), selaraskan dengan revisi.md §6/§9 |
| B3 | Sedang | Jalur legacy `_run_sequential()` masih hidup sebagai fallback saat LangGraph tak terpasang/gagal — **tidak ada tes** yang menyentuhnya; dua model eksekusi harus dijaga setara. | `coordinator.py:20–23, 641, 699` | Hapus, atau tambah tes paritas + catat di tesis |
| B4 | Sedang | Cache embedding korpus berbasis **identitas objek** (`self._corpus_ref is not corpus`) di `semantic_match.py`, `recommendation/novelty.py`, `gap_mining/novelty.py` → list baru dengan isi sama di-*embed* ulang. | ketiga file | Kunci cache = hash tuple teks |
| B5 | Sedang | `CrossEncoderReranker`/`NLIModel`/`VectorStore` memuat model per-*instance* (tanpa cache modul) — aman di DI singleton, tapi CLI/eksperimen yang membuat beberapa instance memuat bobot berulang. | `reranker.py:26–47`, `nli_model.py:31–56`, `vector_store.py:92` | `lru_cache` per `(model_name, device)` |
| B6 | Sedang | `POST /api/papers/fetch-pdf` & `/download-and-analyze` mengunduh **URL sembarang** (SSRF). Dampak kecil karena single-user localhost, tapi layak dibatasi. | `papers.py:43–50,155–257` | Tolak host privat/loopback; atau hanya URL hasil resolusi Unpaywall/API |
| B7 | Sedang | Pembatalan di pipeline lama bisa **hilang** bila datang di antara `_ensure_job_active` terakhir dan penulisan `status="completed"`; job `cancelled` menyimpan `progress` terakhir (tampak “macet 95%”). | `analysis.py` ~1804–1874 | Cek ulang cancel tepat sebelum `completed`; set `progress` saat cancel |
| B8 | Rendah | `/api/kg/graph` (analysis.py) vs `/api/graph` (graph.py) — dua endpoint KG dengan bentuk respons berbeda. `/api/sources/status` dan `/health` tidak dipakai UI mana pun. | routes | Satukan / dokumentasikan sebagai API-only |
| B9 | Rendah | `POST /api/models/switch` mengubah `config.model_name` singleton tanpa lock saat job berjalan. | `health.py:70–79`, `llm_service.py:239–242` | Lock, atau model per-request |
| B10 | Rendah | `documents.py` menerima `BackgroundTasks` tapi tidak memakainya; `useAnalysisJob` fallback SSE→polling pada `onerror` pertama tanpa retry; `port_forward_3030.py` port hardcoded; helper unggah terduplikasi di `common.py`/`research_common.py`. | masing-masing | Rapikan bila ada waktu |

**Catatan proses**: audit ini mulai mengubah kode sebelum menyajikan temuan — seharusnya temuan dan rencana disajikan dulu untuk disetujui. Bagian §10.4 disusun agar setiap item dapat dinilai dan dibatalkan secara terpisah.
