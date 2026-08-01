# Laporan Verifikasi & Penyelesaian Audit — Wizard Research

**Tanggal:** 1 Agustus 2026
**Ruang lingkup:** Verifikasi seluruh temuan audit `LAPORAN_ANALISIS.md` (K1–K7, P1–P4) + agregasi statistik eksperimen H6/H7/H9
**Hasil akhir:** Semua temuan **resolved**; test suite **368 pass, 2 skip**

---

## 1. Ringkasan Eksekutif

| Aspek | Status |
|---|---|
| Temuan kritis K1–K7 | ✅ Semua resolved & terverifikasi |
| Temuan penting P1–P4 | ✅ Semua resolved (P4 diselesaikan pada sesi ini) |
| Eksperimen H6/H7/H9 | ✅ Lengkap — 5 run/mode (seeds 43–47), Holm-corrected |
| Test suite | ✅ 368 pass, 2 skip (naik dari 351 → +17 test tools baru) |
| Kesiapan sidang | ✅ Siap, dengan catatan framing H9 (lihat §4) |

---

## 2. Verifikasi Temuan Kritis (K1–K7)

| # | Temuan | Status | Bukti di kode |
|---|---|---|---|
| K1 | Bug `layers_used` → 3-layer discriminator tidak aktif | ✅ Fixed | Field `layers_used` ada di `ClassifiedRelation` (`backend/app/core/validation/relation_classifier.py:70`), di-assign di `classify()`; `nli_checker_tool.py` membacanya; test `test_nli_checker_tool.py` pass (verifikasi tanpa fallback LLM) |
| K2 | Konflik `.env` ganda | ✅ Fixed | `load_project_env()` memuat root `.env` dulu lalu `backend/.env` sebagai override eksplisit; `backend/.env` kini hanya 2 key override (`LLM_TEMPERATURE`, `LLM_MAX_TOKENS`); port seragam 8001 |
| K3 | Rule Engine default-PASS saat bukti hilang | ✅ Fixed | Default `rule_engine.defaults.on_missing_evidence: flag` (`backend/config.yaml`); entity linking gagal → FLAG + penalti confidence (−0.15 / −0.1) |
| K4 | Hasil H9 belum ada | ✅ Selesai | 5 run `nli` + 5 run `no-nli` dengan `llama3.2:latest` (seeds 43–47) + 3 run `gpt-oss:latest` di `backend/experiments/results/` |
| K5 | Metodologi statistik lemah | ✅ Fixed | `--seed` per-run di `run_multi.py`; `stats_utils.py`: Holm–Bonferroni, Cliff's δ, rank-biserial r, bootstrap CI (seed=42); uji primer per-run, pooled dilabeli eksploratori |
| K6 | Job analisis hanya in-memory | ✅ Fixed | `backend/app/utils/job_store.py` — **SQLite** (`analysis_jobs.sqlite3`): atomic claim, recovery restart ("Server di-restart saat analisis berjalan"), retry exponential backoff; `analysis_queue.py` durable via ThreadPoolExecutor |
| K7 | Validasi upload minim | ✅ Fixed | `backend/app/utils/upload_validation.py` — `sanitize_filename` (null byte, path traversal, batas panjang), cek magic header `%PDF-`, size limit di-enforce saat streaming (HTTP 413/415), cleanup `try/finally` |

## 3. Verifikasi Temuan Penting (P1–P4)

| # | Temuan | Status | Bukti |
|---|---|---|---|
| P1 | `AnalysisResults.jsx` 2.247 baris | ✅ Refactored | Tab diekstrak ke `frontend/src/components/pages/analysis-tabs/` — 10 komponen (OverviewTab, GapsTab, TopicsTab, RecommendationsTab, KnowledgeGraphTab, PipelineTab, ProposalTab, RoadmapTab, DeepAnalysisPanel, SimpleResultsView) + `constants.js`; file utama tinggal orchestrator |
| P2 | Job tidak persist | ✅ Fixed | Sama dengan K6 (SQLite job store) |
| P3 | Keamanan upload | ✅ Fixed | Sama dengan K7 |
| P4 | Tools tanpa unit test | ✅ **Diselesaikan sesi ini** | `backend/tests/test_agent_tools.py` baru — **17 tests** meng-cover `RAGTool`, `KGQuerierTool`, `PaperAnalyzerTool`, `SelfCriticTool` (happy path, error handling, batas 50 fakta, truncation 500 char, skoring self-critic) |

---

## 4. Hasil Statistik Eksperimen (llama3.2:latest, 5 run/mode, seeds 43–47)

Sumber: `backend/experiments/results/multirun_stats_llama3.2_latest.md`
(dihasilkan via `python experiments/run_multi.py --skip-runs --runs 5 --model llama3.2:latest`)

### Deskriptif per mode

| Mode | Indikator (mean±std) | Avg Conf | Fakta SPO | RERR % |
|---|---|---|---|---|
| full | 17.2 ± 3.2 | 0.730 ± 0.021 | 133 ± 9.3 | 3.8 ± 8.5 |
| no-rule-engine | 18.2 ± 5.5 | 0.728 ± 0.021 | 127 ± 3.2 | 0 |
| linear-baseline | 20 ± 0 | 0.709 ± 0.008 | 0 | 0 |
| nli | 25.0 ± 2.3 | 0.788 ± 0.013 | 128 ± 8.9 | 0 |
| no-nli | 15.2 ± 1.9 | 0.749 ± 0.025 | 137 ± 12 | 4.4 ± 9.9 |

### Uji signifikansi primer (per-run, Mann–Whitney U + Holm)

| Hipotesis | Perbandingan | Variabel | p | p Holm | Sig (α=0.05) | Effect size |
|---|---|---|---|---|---|---|
| H7 | full vs no-rule-engine | indikator/run | 0.9155 | 1.0000 | tidak | δ=−0.08 (negligible) |
| H7 | full vs no-rule-engine | mean conf/run | 1.0000 | 1.0000 | tidak | δ=−0.04 (negligible) |
| H6 | full vs linear-baseline | indikator/run | 0.1188 | 0.4752 | tidak | δ=−0.60 (large) |
| H6 | full vs linear-baseline | mean conf/run | 0.2073 | 0.6219 | tidak | δ=0.52 (large) |
| **H9** | **nli vs no-nli** | **indikator/run** | **0.0119** | **0.0716** | **tidak** | **δ=1.0 (large), Δmed=11 [6, 13]** |
| **H9** | **nli vs no-nli** | **mean conf/run** | **0.0119** | **0.0716** | **tidak** | **δ=1.0 (large), Δmed=0.026 [0.006, 0.07]** |

### Rekomendasi framing untuk tesis (H9)

Efek **besar dan konsisten** (Cliff's δ = 1.0; CI bootstrap median tidak melewati 0) tetapi **belum signifikan setelah koreksi Holm** karena jumlah run kecil (n=5/kelompok, power terbatas). Framing yang defensible di sidang:

> "Mode NLI menunjukkan efek besar dan konsisten pada jumlah indikator terdeteksi (Δmedian = 11, 95% CI [6, 13], δ = 1.0), namun dengan n = 5 run per kelompok, p terkoreksi Holm (0.0716) belum melewati α = 0.05 — merupakan bukti awal yang kuat, bukan konfirmasi definitif."

Alternatif: tambah jumlah run (mis. `--runs 10`) untuk meningkatkan power bila waktu memungkinkan.

---

## 5. Verifikasi Test Suite

| Tahap | Perintah | Hasil |
|---|---|---|
| Full suite (awal) | `pytest tests/` | 351 pass, 2 skip (~49s) |
| K1/K3 spesifik | `pytest tests/test_relation_classifier.py tests/test_rule_engine.py` | 112 pass |
| NLI tool | `pytest tests/test_nli_checker_tool.py` | 1 pass |
| Tools baru (P4) | `pytest tests/test_agent_tools.py` | 17 pass |
| **Full suite (akhir)** | `pytest tests/` | **368 pass, 2 skip (~45s)** |

---

## 6. Perubahan yang Dibuat pada Sesi Ini

| Commit | Isi |
|---|---|
| `0d32f23` | `docs(laporan)`: LAPORAN_ANALISIS.md — ringkasan eksekutif diperbarui (H9 lengkap), banner resolved di §3, Addendum §9 (tabel verifikasi + statistik H9 + framing tesis) |
| `73e25b8` | `test(tools)`: `backend/tests/test_agent_tools.py` (17 unit tests) + refresh `backend/requirements.lock` (511 paket) |

> Kedua commit masih **lokal** (2 commit di depan `origin/main`) — push dilakukan atas keputusan Anda.

---

## 7. Sisa Pekerjaan (opsional, tidak memblokir sidang)

1. `git push` setelah review.
2. Tambah run eksperimen (`--runs 10`) bila ingin H9 signifikan pasca-Holm.
3. Technical debt minor: pecah 4 file inti backend yang besar, typed models (Pydantic) antar modul, CORS origin whitelist, rate limiting API.
