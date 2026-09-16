# Sumber GitHub & Hugging Face untuk Penelitian Wizard Research

> Survei terverifikasi per **16 September 2026** · 277 item lolos (171 repo kode/library, 70 dataset/benchmark, 17 model HF, 19 paper arXiv) · 67 item di bawah saringan (Lampiran A) · 2 tidak ditemukan (Lampiran B)

Dokumen ini menjawab pertanyaan **"apa saja di GitHub yang bisa membantu penelitian ini?"** untuk tesis *Pendekatan Neuro-Symbolic Agentic untuk Deteksi Indikator Synthesis Gap pada Literatur Ilmiah*. Setiap item dipetakan ke **modul Wizard Research** yang bisa memakainya dan diberi **kategori aksi**:

| Kategori | Arti |
|---|---|
| **Adopsi** | Library/model yang bisa langsung dipakai menggantikan atau melengkapi implementasi sendiri |
| **Baseline** | Sistem pembanding untuk evaluasi komparatif (BAB IV) |
| **Dataset evaluasi** | Data/benchmark untuk mengukur presisi/recall komponen |
| **Rujukan** | Metode/arsitektur sebagai acuan desain atau sitasi, tidak diintegrasikan langsung |

## 1. Metode & Saringan

- **Sumber penemuan (3 jalur):** (a) daftar seed kurasi manual dari rancangan survei (12 tema + metrik graf + retrieval); (b) GitHub Search API, 74 kueri untuk 14 tema (Lampiran C), 466 repo unik dipindai lalu dikurasi; (c) Hugging Face Hub API untuk model & dataset (320 hasil); ditambah agen riset pelengkap untuk celah yang belum tercakup (bagian 6).
- **Verifikasi mesin (anti-karangan):** setiap item harus punya metadata dari GitHub Search API (`stargazers_count`, `pushed_at`, `license`, `archived`), HF Hub API (`likes`, `downloads`, `lastModified`), atau arXiv API (judul). Repo yang berpindah nama diikuti ke nama barunya (5 kasus, mis. `kermitt2/grobid` → `grobidOrg/grobid`).
- **Saringan repo kode/library:** ⭐ ≥ 50 **dan** push terakhir ≥ 2024-09-16 **dan** tidak `archived`. **Dataset, benchmark, model, dan paper dikecualikan dari syarat ⭐/aktivitas** (cukup terverifikasi ada). Repo yang gagal saringan tetap dicatat di Lampiran A beserta alasannya karena beberapa (mis. MultiVerS, Logic-LM, SelfCheckGPT) penting sebagai rujukan.
- **Kolom tabel:** ⭐ = stars GitHub; ♥/⬇ = likes/downloads HF; *Aktivitas* = bulan push/modifikasi terakhir; *Lisensi* = SPDX dari API (`lainnya` = lisensi non-standar).

## 2. Ringkasan Eksekutif

- **277 sumber terverifikasi** tersebar di 14 tema; kategori: Adopsi 74, Baseline 13, Dataset evaluasi 65, Rujukan 106.
- **Peluang adopsi terbesar** ada pada komponen yang saat ini diimplementasikan sendiri padahal ada library matang: klien OpenAlex (`pyalex`), kalibrasi/conformal (`MAPIE`, `net:cal`), heterogenitas meta-analisis (`PyMARE`, `statsmodels`), agreement antar-penilai (`fast-krippendorff`), dan deteksi komunitas graf (`cdlib`, `leidenalg`).
- **Celah bahasa:** model NLI (`cross-encoder/nli-deberta-v3-xsmall`) dan reranker (`ms-marco-MiniLM`) yang dipakai hanya Inggris; tersedia pengganti multibahasa (`mDeBERTa-v3-xnli-multilingual`, `bge-reranker-v2-m3`, `bge-m3`) yang relevan untuk jurnal Indonesia.
- **Gold standard komponen** yang belum dipakai: SciFact/SciNLI (NLI ilmiah), Evidence Inference (arah efek), EBM-NLP (PICO), LimitGen (limitation), unarXive-IMRaD (klasifikasi seksi), Text2KGBench/SciERC (ekstraksi triple) — memungkinkan evaluasi per-komponen di BAB IV, bukan hanya end-to-end.
- **Baseline pembanding** yang paling sepadan: PaperQA2 (citation grounding + deteksi kontradiksi), OpenScholar (self-feedback), gpt-researcher (generik). Tidak ditemukan sistem terbuka yang secara eksplisit mendeteksi *synthesis gap* Cooper (fragmentation/inconsistency/incompleteness) dengan rule engine — mendukung klaim kebaruan tesis.
- **Parsing PDF** adalah area dengan alternatif paling matang (GROBID, docling, marker, MinerU); GROBID sudah opsional di pipeline dan paling murah untuk diperluas ke referensi.

## 3. Top-10 Prioritas Integrasi

Skor prioritas = relevansi ke modul inti × kematangan (⭐, aktivitas, lisensi) × kemudahan integrasi. Setiap butir menyebut **file yang diubah**, **dependensi baru**, dan **cara validasi**.

### 1. `pyalex` — klien OpenAlex resmi-komunitas · Adopsi · tema D
- **Modul:** `backend/app/services/paper_apis/openalex.py` (`OpenAlexAPI`), `core/gap_mining/novelty.py`, `core/gap_detection/citation_coupling.py`
- **Langkah:** (1) `pip install pyalex`, tambah ke `backend/requirements.txt`; (2) set `pyalex.config.email` dari env `OPENALEX_EMAIL` (polite pool → limit lebih longgar); (3) ganti pemanggilan HTTP manual di `OpenAlexAPI.search()` dengan `Works().search(q).filter(publication_year=">2023")`; (4) kopling bibliografis: `Works()[id]["referenced_works"]` → irisan himpunan referensi antar-jurnal; (5) pastikan saklar `OPENALEX_DISABLED` tetap dihormati.
- **Validasi:** tes unit yang ada untuk `openalex.py` + uji manual pada 5 gap korpus forensik (hasil novelty sama/lebih baik).
- **Risiko/lisensi:** kuota 100k permintaan/hari; MIT.

### 2. GROBID + `grobid-client-python` — seksi & referensi dari PDF · Adopsi · tema E
- **Modul:** `core/pipeline/metadata_resolver.py` (sudah memakai GROBID bila `GROBID_URL` aktif), `services/paper_apis/grobid.py` (`GrobidClient`), `core/pipeline/references.py`
- **Langkah:** (1) jalankan layanan: `docker run --rm -p 8070:8070 grobid/grobid:<tag terbaru>` dan set `GROBID_URL`; (2) perluas `GrobidClient` dengan `processReferences` → parse `biblStruct` (TEI) ke skema referensi `references.py`, menggantikan pemisahan heuristik; (3) pakai seksi TEI (`<div><head>`) sebagai sumber utama `section_normalizer.py`, heuristik hanya fallback; (4) pertimbangkan mengganti klien buatan sendiri dengan `grobid-client-python` (batch + concurrency).
- **Validasi:** `experiments/audit_chunks.py` pada korpus 35 PDF: % judul seksi benar, jumlah referensi terurai vs manual pada 5 PDF.
- **Risiko/lisensi:** layanan Java terpisah (RAM 2–4 GB); Apache-2.0.

### 3. `docling` — parser layout dokumen (IBM) · Adopsi/pembanding · tema E
- **Modul:** `core/pipeline/layout.py`, `text_cleaning.py`, `token_chunker.py`
- **Langkah:** (1) `pip install docling` (mengunduh model layout saat pertama kali); (2) tulis adaptor `core/pipeline/docling_adapter.py` yang mengeluarkan daftar `(section_title, text)` dengan kontrak yang sama seperti `layout.py`; (3) tambahkan pilihan `pipeline.parser: heuristic | docling | grobid` di `backend/config.yaml`; (4) pertahankan `pypdf` sebagai fallback.
- **Validasi:** A/B pada korpus yang sama dengan metrik cacat pipeline yang sudah ada (potong tengah kalimat 4,7 %, overlap, seksi salah, header/footer bocor).
- **Risiko/lisensi:** waktu proses lebih lama (CPU); MIT.

### 4. NLI multibahasa — `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` (+ `DeBERTa-v3-base-mnli-fever-anli`) · Adopsi · tema B
- **Modul:** `core/validation/nli_model.py` (`DEFAULT_NLI_MODEL = "cross-encoder/nli-deberta-v3-xsmall"`), `core/agents/tools/nli_checker_tool.py`
- **Langkah:** (1) pindahkan nama model ke `config.yaml: nli.model`; (2) **peta label** jangan dikodekan tetap — model MoritzLaurer memakai urutan (entailment, neutral, contradiction), berbeda dari keluarga `cross-encoder/nli-*`; baca `model.config.id2label`; (3) mDeBERTa untuk korpus berbahasa Indonesia, DeBERTa-v3-base untuk Inggris; (4) cache model di `models/` agar tidak diunduh ulang.
- **Validasi:** skrip baru `experiments/evaluate_nli.py`: akurasi & F1 kelas *contradiction* pada SciFact-dev dan SciNLI (*contrasting*) untuk xsmall vs base vs mDeBERTa; catat latensi CPU per pasangan.
- **Risiko/lisensi:** mDeBERTa 278M parameter (~3× lebih lambat dari xsmall); MIT.

### 5. SciFact + SciNLI + Evidence Inference — gold untuk NLI & arah efek · Dataset evaluasi · tema B
- **Modul:** `core/gap_detection/claim_normalization.py` (`_directions_oppose`), `adjudication.py`, `experiments/`
- **Langkah:** (1) `datasets.load_dataset("allenai/scifact")`, `"tasksource/scinli"`, `"bigbio/evidence_inference"`; (2) SciFact: pasangan (klaim, kalimat bukti) → uji NLI dan *alignment* klaim (`semantic_match.py`); (3) SciNLI: kelas *contrasting* sebagai proxy indikator *inconsistency* → precision/recall detektor; (4) Evidence Inference: label *significantly increased / decreased / no significant difference* → gold normalisasi **arah efek**; (5) laporkan sebagai evaluasi komponen di BAB IV (bukan end-to-end).
- **Validasi:** tabel akurasi per dataset + contoh kegagalan untuk `error_taxonomy.py`.
- **Risiko/lisensi:** domain biomedis/NLP ≠ forensik digital → posisikan sebagai uji generalisasi komponen; lisensi: SciFact CC-BY-NC, SciNLI & Evidence Inference lihat repo masing-masing.

### 6. LimitGen — benchmark identifikasi limitation · Dataset evaluasi · tema A
- **Modul:** `core/gap_mining/candidates.py`, `extractor.py`, `experiments/evaluate_gaps.py`
- **Langkah:** (1) `load_dataset("yale-nlp/LimitGen")` (subset *Syn* dengan limitation disuntikkan dan *Human* beranotasi); (2) jalankan gap mining pada paper LimitGen → cocokkan dengan gold (semantic match ≥ ambang) → recall/precision per aspek (metodologi, eksperimen, analisis); (3) bandingkan dengan skor LLM baseline yang dilaporkan di paper LimitGen; (4) jadikan benchmark kedua di samping Mendeley (`gap_benchmark_mendeley.py`).
- **Validasi:** kurva recall vs ambang similarity; sampel 30 kecocokan diperiksa manual.
- **Risiko/lisensi:** paper domain AI; lisensi dataset perlu dicek di kartu HF.

### 7. MAPIE + net:cal — conformal & kalibrasi tervalidasi · Adopsi · tema I
- **Modul:** `core/gap_detection/calibration.py` (`expected_calibration_error`, `fit_temperature`, `conformal_threshold`, `Calibrator`)
- **Langkah:** (1) `pip install mapie netcal`; (2) tes kesetaraan di `backend/tests/`: `netcal.metrics.ECE(bins=10)` vs `expected_calibration_error` pada data yang sama (toleransi 1e-6); (3) bila setara, ganti grid-search `fit_temperature` dengan `netcal.scaling.TemperatureScaling`; (4) `conformal_threshold` → `SplitConformalClassifier` (MAPIE v1; `MapieClassifier(cv="prefit")` di v0.x) untuk jaminan cakupan 1−α; laporkan cakupan empiris & ukuran himpunan prediksi; (5) reliability diagram via `netcal.presentation.ReliabilityDiagram` untuk gambar BAB IV.
- **Validasi:** tes unit kesetaraan + cakupan empiris pada data kalibrasi ≥ 1−α.
- **Risiko/lisensi:** dependensi tambahan (scikit-learn sudah ada); BSD-3 / Apache-2.0.

### 8. PyMARE + `statsmodels` — validasi Cochran Q, I², τ² · Adopsi · tema J
- **Modul:** `core/gap_detection/adjudication.py` (`cochran_q`, `i_squared`, `tau_squared`, `assess_heterogeneity`), `experiments/stats_utils.py`
- **Langkah:** (1) `pip install pymare statsmodels` (keduanya belum ada di `requirements.txt`); (2) tes kesetaraan terhadap `pymare.estimators.DerSimonianLaird` dan `statsmodels.stats.meta_analysis.combine_effects` memakai contoh angka acuan dari buku teks meta-analisis; (3) validasi p-value Q dengan `combine_effects(...).test_homogeneity()`; (4) pertimbangkan estimator REML (PyMARE) untuk k kecil, tetap laporkan pita I².
- **Validasi:** tes unit toleransi 1e-6 untuk Q, I², τ².
- **Risiko/lisensi:** kecil; MIT / BSD-3.

### 9. PaperQA2 (+ OpenScholar) — baseline pembanding · Baseline · tema G
- **Modul:** `experiments/compare_results.py`, protokol BAB IV
- **Langkah:** (1) `pip install paper-qa`; arahkan LLM ke Ollama/endpoint Copilot via LiteLLM dan embedding lokal; (2) indeks 35 PDF korpus yang sama; (3) ajukan pertanyaan per tema: "Apa kontradiksi/gap antar-studi tentang X?"; ekstrak klaim/gap dari jawaban; (4) bandingkan dengan keluaran Wizard Research pada gold ahli: precision/recall gap, grounding kutipan verbatim, waktu; (5) bahas perbedaan desain (PaperQA2 tanpa rule engine/KG; deteksi kontradiksi implisit).
- **Validasi:** tabel komparatif + uji signifikansi (bootstrap CI, Holm–Bonferroni yang sudah ada).
- **Risiko/lisensi:** biaya token; Apache-2.0.

### 10. `fast-krippendorff` + `judgy` — agreement ahli & CI untuk LLM-judge · Adopsi · tema K
- **Modul:** `experiments/expert_eval/compute_metrics.py` (`cohens_kappa`), `experiments/cross_critic.py`, `error_taxonomy.py`
- **Langkah:** (1) `pip install krippendorff judgy`; (2) tambah `krippendorff.alpha(reliability_data, level_of_measurement="ordinal")` untuk skala Likert dengan >2 penilai, di samping κ Cohen; (3) `judgy`: estimasi TPR/TNR judge LLM pada subset berlabel ahli → koreksi bias & interval kepercayaan untuk metrik judge pada seluruh data; (4) laporkan CI di tabel BAB IV.
- **Validasi:** α pada data ahli yang sudah ada; bandingkan α vs κ.
- **Risiko/lisensi:** `krippendorff` GPL-3.0 (dipakai hanya di skrip eksperimen, tidak didistribusikan bersama produk); `judgy` MIT.

### Prioritas berikutnya (11–20)
| # | Item | Tema | Manfaat singkat |
|---|---|---|---|
| 11 | `allenai/specter2_base` (HF) | F | Embedding paper sadar-sitasi untuk `semantic_match.py`, kopling & klaster fragmentasi |
| 12 | `MaartenGr/BERTopic` | M | Tema lintas-jurnal & label klaster untuk `recommendation/themes.py` |
| 13 | `allenai/scispacy` | F | Pra-ekstraksi entitas sebelum LLM di `fact_extractor.py` |
| 14 | `BAAI/bge-reranker-v2-m3` + `BAAI/bge-m3` (HF) | R | Retrieval & reranking multibahasa untuk `core/retrieval/` |
| 15 | `scallop-lang/scallop` / `ML-KULeuven/problog` | H | Rule engine probabilistik atas fakta SPO berbobot confidence |
| 16 | `saier/unarXive_imrad_clf` (HF) | E | Melatih/menguji pemetaan heading → IMRaD di `section_normalizer.py` |
| 17 | `IINemo/lm-polygraph` | I | Confidence pernyataan gap dari LLM sebelum kalibrasi |
| 18 | `SciSciCollective/pyscisci` | C | Metrik kopling bibliografis & lanskap riset terstandar untuk `citation_coupling.py` |
| 19 | `mb7419/egm` | C | Render Evidence Gap Map (Plotly) langsung dari matriks `coverage_map.py` |
| 20 | `IbrahimAlAzhar/FutureWorkGeneration` + dataset limitasi HF | A | Prompt penyaring *future work* & rubrik judge FutureGen; gold limitasi tambahan untuk `evaluate_gaps.py` |

## 4. Tabel per Tema

Urutan dalam tabel: Adopsi → Baseline → Dataset evaluasi → Rujukan, lalu ⭐ menurun.

### Tema A — Gap mining, generasi ide & kebaruan

Modul terkait: `core/gap_mining/`, `core/gap_detection/quote_grounding.py`, `core/recommendation/`

| Item | Tipe | Isi | ⭐ | Aktivitas | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|---|
| [HKUDS/AI-Researcher](https://github.com/HKUDS/AI-Researcher) | Repo | [NeurIPS2025] "AI-Researcher: Autonomous Scientific Innovation" -- A production-ready version: https://novix.s… | ⭐ 5.741 | 2025-10 | — | Baseline | Sistem end-to-end ide → eksperimen → paper; pembanding "AI researcher" untuk tahap rekomendasi di BAB IV → `core/recommendation/engine.py` |
| [DAMO-NLP-SG/CoI-Agent](https://github.com/DAMO-NLP-SG/CoI-Agent) | Repo | Official code for paper: Chain of Ideas: Revolutionizing Research via Novel Idea Development with LLM Agents | ⭐ 510 | 2025-01 | Apache-2.0 | Baseline | Chain-of-Ideas: agen ide riset dengan rantai literatur (ICLR 2025) → baseline generasi ide dari literatur → `core/recommendation/engine.py` |
| [cheerss/SciPIP](https://github.com/cheerss/SciPIP) | Repo | The official repository for the Scientific Paper Idea Proposer (SciPIP) | ⭐ 77 | 2025-02 | MIT | Baseline | Scientific Paper Idea Proposer → baseline pengusul ide → `core/recommendation/engine.py` |
| [princeton-nlp/LitSearch](https://github.com/princeton-nlp/LitSearch) | Benchmark | [EMNLP 2024] A Retrieval Benchmark for Scientific Literature Search | ⭐ 109 | 2024-12 | MIT | Dataset evaluasi | Benchmark retrieval literatur ilmiah (597 kueri realistis) → menguji pencarian "apakah gap sudah dijawab" dan `core/retrieval/` → `core/gap_mining/novelty.py` |
| [xingjian-zhang/massw](https://github.com/xingjian-zhang/massw) | Dataset | MASSW is a comprehensive text dataset on Multi-Aspect Summarization of Scientific Workflows. MASSW includes mo… | ⭐ 22 | 2025-05 | CC0-1.0 | Dataset evaluasi | MASSW: 152k paper dengan 5 aspek alur kerja (Context, Key Idea, Method, Outcome, Projected Impact) → *Projected Impact* ≈ future work skala besar → `core/gap_mining/extractor.py` |
| [sandeep82945/Future-Idea-Generation](https://github.com/sandeep82945/Future-Idea-Generation) | Dataset | — | ⭐ 14 | 2025-02 | MIT | Dataset evaluasi | Data/kode "Can LLMs unlock novel scientific research ideas?" → validasi rekomendasi arah riset dari *future work* → `core/recommendation/engine.py` |
| [yale-nlp/LimitGen](https://github.com/yale-nlp/LimitGen) | Benchmark | Data and Code for ACL 2025 Paper "Can LLMs Identify Critical Limitations within Scientific Research? A Systema… | ⭐ 9 | 2025-07 | — | Dataset evaluasi | Benchmark limitation paper AI beranotasi (LimitGen) → gold untuk mengukur recall gap mining tipe *limitation* dan pola prompt "identify limitations" → `experiments/evaluate_gaps.py` |
| [ethannlin/SchNovel](https://github.com/ethannlin/SchNovel) | Benchmark | This repository contains the code for the paper "Evaluating and Enhancing Large Language Models for Novelty As… | ⭐ 8 | 2024-10 | MIT | Dataset evaluasi | SchNovel: evaluasi LLM menilai kebaruan publikasi → rujukan protokol penilaian kebaruan → `core/recommendation/novelty.py` |
| [OpenNSWM-Lab/FAROS](https://github.com/OpenNSWM-Lab/FAROS) | Repo | A blueprint-driven AutoResearch runtime for orchestrating AI research workflows from idea generation and exper… | ⭐ 3.034 | 2026-09 | — | Rujukan | Runtime AutoResearch blueprint-driven → rujukan orkestrasi eksperimen otomatis (relevansi tak langsung) → `core/agents/coordinator.py` |
| [NoviScl/AI-Researcher](https://github.com/NoviScl/AI-Researcher) | Repo | — | ⭐ 407 | 2025-08 | MIT | Rujukan | Pipeline generasi + ranking ide (Si et al. 2024) dengan penilai kebaruan berbasis Semantic Scholar → rujukan skor novelty & dedup ide → `core/recommendation/novelty.py` |
| [CL-ML/open-collider](https://github.com/CL-ML/open-collider) | Repo | A semantic collision engine for non-trivial LLM idea generation. Operationalizes Koestler's bisociation theory… | ⭐ 343 | 2026-05 | MIT | Rujukan | Mesin "semantic collision" untuk ide LLM non-trivial → teknik rekombinasi tema lintas-jurnal → `core/recommendation/themes.py` |
| [ulab-uiuc/research-town](https://github.com/ulab-uiuc/research-town) | Repo | [ICML 2025] ResearchTown: Simulator of Human Research Community | ⭐ 211 | 2026-09 | Apache-2.0 | Rujukan | Simulasi komunitas riset multi-agen (ResearchTown) → rujukan evaluasi ide dengan agen "reviewer" → `core/recommendation/engine.py` |
| [allenai/marg-reviewer](https://github.com/allenai/marg-reviewer) | Repo | Code/data for MARG (multi-agent review generation) | ⭐ 64 | 2026-03 | Apache-2.0 | Rujukan | MARG: multi-agent review generation (kelemahan paper) → pola menemukan limitasi implisit yang tidak ditulis penulis → `core/agents/tools/self_critic_tool.py` |
| [JinheonBaek/ResearchAgent](https://github.com/JinheonBaek/ResearchAgent) | Repo | Official Code Repository for ResearchAgent (NAACL 2025) | ⭐ 59 | 2025-08 | — | Rujukan | ResearchAgent (NAACL 2025): identifikasi masalah → metode → desain eksperimen dengan agen peninjau iteratif → rujukan arsitektur rekomendasi → `core/recommendation/engine.py` |

**Model/dataset Hugging Face (tema A):**

| Item | Tipe | ♥ / ⬇ | Modifikasi | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|
| [InternScience/SGI-IdeaGeneration](https://huggingface.co/datasets/InternScience/SGI-IdeaGeneration) <sub>HF dataset</sub> | Dataset | ♥ 4 · ⬇ 68 | 2026-06 | mit | Dataset evaluasi | Dataset generasi ide ilmiah (2026) → evaluasi kualitas judul/ide siap-pakai → `core/recommendation/engine.py` |
| [yale-nlp/LimitGen](https://huggingface.co/datasets/yale-nlp/LimitGen) <sub>HF dataset</sub> | Benchmark | ♥ 0 · ⬇ 50 | 2025-07 | — | Dataset evaluasi | Versi HF LimitGen, langsung dimuat dengan `datasets` untuk skrip evaluasi → `experiments/evaluate_gaps.py` |
| [IbrahimAlAzhar/limitation-generation-dataset-bagels](https://huggingface.co/datasets/IbrahimAlAzhar/limitation-generation-dataset-bagels) <sub>HF dataset</sub> | Dataset | ♥ 0 · ⬇ 206 | 2025-09 | — | Dataset evaluasi | Dataset generasi *limitations* (paper ACL 2023, JSON per paper) → gold alternatif LimitGen untuk ekstraktor limitasi → `experiments/evaluate_gaps.py` |
| [iaadlab/LimAgents_limitation_data_scientific_papers_with_cited_papers](https://huggingface.co/datasets/iaadlab/LimAgents_limitation_data_scientific_papers_with_cited_papers) <sub>HF dataset</sub> | Dataset | ♥ 0 · ⬇ 675 | 2025-09 | cc-by-4.0 | Dataset evaluasi | Limitasi paper NeurIPS 2021–22 + ulasan OpenReview **beserta paper yang dikutip/mengutip** → menghubungkan gap dengan jaringan sitasi (fragmentasi) → `core/gap_detection/citation_coupling.py` |
| [datalab2/Limitation_generation_dataset](https://huggingface.co/datasets/datalab2/Limitation_generation_dataset) <sub>HF dataset</sub> | Dataset | ♥ 0 · ⬇ 54 | 2025-05 | — | Dataset evaluasi | Limitasi ACL 2023–24 & NeurIPS 2021–22 (kurasi manusia + LLM) → set uji kecil ekstraktor limitasi → `experiments/evaluate_gaps.py` |

### Tema B — Verifikasi klaim, NLI & kontradiksi (PICO)

Modul terkait: `core/validation/nli_model.py`, `agents/tools/nli_checker_tool.py`, `gap_detection/claim_normalization.py`, `adjudication.py`

| Item | Tipe | Isi | ⭐ | Aktivitas | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|---|
| [allenai/scifact](https://github.com/allenai/scifact) | Dataset | Data and models for the SciFact verification task. | ⭐ 272 | 2023-10 | lainnya | Dataset evaluasi | 1.409 klaim ilmiah + abstrak bukti berlabel SUPPORT/REFUTE → gold akurasi NLI cross-encoder & alignment klaim → `core/validation/nli_model.py` |
| [Franck-Dernoncourt/pubmed-rct](https://github.com/Franck-Dernoncourt/pubmed-rct) | Dataset | PubMed 200k RCT dataset: a large dataset for sequential sentence classification. | ⭐ 202 | 2023-10 | — | Dataset evaluasi | PubMed 200k RCT: 200k abstrak berlabel peran kalimat → melatih classifier peran kalimat/PICO → `core/gap_detection/claim_normalization.py` |
| [bepnye/EBM-NLP](https://github.com/bepnye/EBM-NLP) | Dataset | — | ⭐ 99 | 2019-08 | — | Dataset evaluasi | 5k abstrak RCT beranotasi span P/I/O → melatih/menguji ekstraktor PICO → `core/gap_detection/claim_normalization.py` |
| [jayded/evidence-inference](https://github.com/jayded/evidence-inference) | Dataset | Data and code from our "Inferring Which Medical Treatments Work from Reports of Clinical Trials", NAACL 2019. … | ⭐ 68 | 2021-08 | MIT | Dataset evaluasi | Evidence Inference: (intervensi, komparator, outcome) → arah efek naik/turun/tidak-signifikan dari RCT → gold normalisasi **arah efek** → `core/gap_detection/claim_normalization.py` |
| [asaakyan/covidfact](https://github.com/asaakyan/covidfact) | Dataset | Data and code for the paper COVID-Fact: Fact Extraction and Verification of Real-World Claims on COVID-19 Pand… | ⭐ 40 | 2025-02 | — | Dataset evaluasi | 4.086 klaim dengan bukti & *counter-claims* → uji robust deteksi kontradiksi → `core/gap_detection/adjudication.py` |
| [msadat3/SciNLI](https://github.com/msadat3/SciNLI) | Dataset | The dataset and code for ACL 2022 paper "SciNLI: A Corpus for Natural Language Inference on Scientific Text" a… | ⭐ 29 | 2023-10 | — | Dataset evaluasi | 107k pasangan kalimat NLI dari paper ACL; kelas *contrasting* = sinyal inconsistency → fine-tune/evaluasi NLI ilmiah → `core/validation/nli_model.py` |
| [dwadden/scifact-open](https://github.com/dwadden/scifact-open) | Dataset | Data and code for the SciFact-Open task | ⭐ 29 | 2023-11 | — | Dataset evaluasi | SciFact-Open: verifikasi klaim open-domain pada korpus besar → uji retrieval+NLI yang realistis → `core/retrieval/` |
| [XinyuanLu00/SciTab](https://github.com/XinyuanLu00/SciTab) | Benchmark | The project page for "SCITAB: A Challenging Benchmark for Compositional Reasoning and Claim Verification on Sc… | ⭐ 23 | 2023-12 | MIT | Dataset evaluasi | Klaim ilmiah yang butuh penalaran tabel (1,2k) → uji NLI pada klaim numerik → `core/validation/nli_model.py` |
| [sarrouti/HealthVer](https://github.com/sarrouti/HealthVer) | Dataset | — | ⭐ 22 | 2022-02 | — | Dataset evaluasi | Klaim kesehatan vs bukti (14k) → uji generalisasi NLI ke domain medis → `core/validation/nli_model.py` |
| [ddhruvkr/CONTRADOC](https://github.com/ddhruvkr/CONTRADOC) | Dataset | — | ⭐ 15 | 2025-02 | Apache-2.0 | Dataset evaluasi | ContraDoc: self-contradiction dalam dokumen panjang → protokol anotasi & evaluasi kontradiksi yang dapat diperluas antar-dokumen → `core/gap_detection/adjudication.py` |
| [posuer/Check-COVID](https://github.com/posuer/Check-COVID) | Dataset | A COVID-19 News Fact-checking Dataset. Verifying claims in news against evidence in scientific papers. | ⭐ 7 | 2023-05 | MIT | Dataset evaluasi | Check-COVID: klaim berita vs bukti paper ilmiah → data klaim↔bukti → `core/validation/nli_model.py` |
| [sandeep82945/Contradiction-in-Peer-Review](https://github.com/sandeep82945/Contradiction-in-Peer-Review) | Dataset | — | ⭐ 1 | 2024-03 | Apache-2.0 | Dataset evaluasi | ContraSciView ("When Reviewers Lock Horns"): ketidaksepakatan antar-reviewer → data kontradiksi bergaya ilmiah untuk fine-tune/uji NLI → `core/validation/nli_model.py` |
| [MicheleNuijten/statcheck](https://github.com/MicheleNuijten/statcheck) | Repo | A spellchecker for statistics | ⭐ 194 | 2026-07 | — | Rujukan | statcheck (R): ekstrak hasil NHST & hitung ulang p-value → klasifikasi signifikan/tidak dan inkonsistensi statistik internal → `core/gap_detection/claim_normalization.py` |
| [zhaochen0110/conflictbank](https://github.com/zhaochen0110/conflictbank) | Benchmark | Code and data for "ConflictBank: A Benchmark for Evaluating the Influence of Knowledge Conflicts in LLM" (Neur… | ⭐ 73 | 2025-05 | — | Rujukan | ConflictBank (NeurIPS 2024): taksonomi konflik pengetahuan pada LLM → rujukan kategori kontradiksi → `core/gap_detection/adjudication.py` |
| [HanNight/RAMDocs](https://github.com/HanNight/RAMDocs) | Dataset | Data and Code for COLM 2025 paper "Retrieval-Augmented Generation with Conflicting Evidence" | ⭐ 25 | 2025-04 | MIT | Rujukan | RAMDocs/MADAM-RAG (COLM 2025): RAG dengan bukti saling bertentangan → strategi agregasi multi-agen saat bukti konflik → `core/agents/coordinator.py` |

**Model/dataset Hugging Face (tema B):**

| Item | Tipe | ♥ / ⬇ | Modifikasi | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|
| [MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7) <sub>HF model</sub> | Model | ♥ 386 · ⬇ 855.997 | 2024-04 | mit | Adopsi | NLI **multibahasa** (100 bahasa, termasuk Indonesia) → menangani jurnal berbahasa Indonesia tanpa terjemahan → `core/validation/nli_model.py` |
| [MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli](https://huggingface.co/MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli) <sub>HF model</sub> | Model | ♥ 225 · ⬇ 544.263 | 2024-04 | mit | Adopsi | NLI 3-kelas kuat (MNLI+FEVER+ANLI, 184M) → pengganti `cross-encoder/nli-deberta-v3-xsmall`; perhatikan urutan label (entailment, neutral, contradiction) → `core/validation/nli_model.py` |
| [MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli](https://huggingface.co/MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli) <sub>HF model</sub> | Model | ♥ 131 · ⬇ 162.349 | 2024-04 | mit | Adopsi | Versi large (+LingNLI/WANLI) → akurasi adjudikasi kontradiksi lebih tinggi bila GPU tersedia → `core/validation/nli_model.py` |
| [cross-encoder/nli-deberta-v3-base](https://huggingface.co/cross-encoder/nli-deberta-v3-base) <sub>HF model</sub> | Model | ♥ 49 · ⬇ 713.443 | 2025-04 | apache-2.0 | Adopsi | Cross-encoder NLI keluarga yang sama dengan default proyek → upgrade drop-in xsmall → base tanpa ubah kode → `core/validation/nli_model.py` |
| [tasksource/deberta-base-long-nli](https://huggingface.co/tasksource/deberta-base-long-nli) <sub>HF model</sub> | Model | ♥ 27 · ⬇ 2.675 | 2024-10 | apache-2.0 | Adopsi | NLI konteks panjang (1.680 token) → membandingkan klaim dengan paragraf bukti utuh, bukan satu kalimat → `core/agents/tools/nli_checker_tool.py` |
| [allenai/scifact](https://huggingface.co/datasets/allenai/scifact) <sub>HF dataset</sub> | Dataset | ♥ 29 · ⬇ 2.868 | 2023-12 | cc-by-nc-2.0 | Dataset evaluasi | SciFact versi HF (`datasets`) untuk skrip evaluasi → `core/validation/nli_model.py` |
| [bigbio/evidence_inference](https://huggingface.co/datasets/bigbio/evidence_inference) <sub>HF dataset</sub> | Dataset | ♥ 6 · ⬇ 155 | 2022-12 | mit | Dataset evaluasi | Evidence Inference versi HF (BigBIO) → `core/gap_detection/claim_normalization.py` |
| [tasksource/scinli](https://huggingface.co/datasets/tasksource/scinli) <sub>HF dataset</sub> | Dataset | ♥ 5 · ⬇ 274 | 2023-01 | apache-2.0 | Dataset evaluasi | SciNLI versi HF → `core/validation/nli_model.py` |
| [allenai/scitail](https://huggingface.co/datasets/allenai/scitail) <sub>HF dataset</sub> | Dataset | ♥ 5 · ⬇ 95.376 | 2024-01 | — | Dataset evaluasi | SciTail: 27k pasangan NLI domain sains → data tambahan fine-tuning NLI → `core/validation/nli_model.py` |
| [allenai/csabstruct](https://huggingface.co/datasets/allenai/csabstruct) <sub>HF dataset</sub> | Dataset | ♥ 4 · ⬇ 161 | 2022-11 | apache-2.0 | Dataset evaluasi | CSAbstruct: peran kalimat abstrak (background/objective/method/result) → melabel kalimat sebelum ekstraksi klaim → `core/gap_detection/claim_normalization.py` |
| [bigbio/ebm_pico](https://huggingface.co/datasets/bigbio/ebm_pico) <sub>HF dataset</sub> | Dataset | ♥ 2 · ⬇ 36 | 2022-12 | — | Dataset evaluasi | EBM-NLP versi HF (BigBIO) → `core/gap_detection/claim_normalization.py` |
| [jedick/DeBERTa-v3-base-mnli-fever-anli-scifact-citint](https://huggingface.co/jedick/DeBERTa-v3-base-mnli-fever-anli-scifact-citint) <sub>HF model</sub> | Model | ♥ 0 · ⬇ 168 | 2025-05 | mit | Rujukan | Fine-tune SciFact + citation intent → varian domain ilmiah untuk dibandingkan dalam ablasi → `core/validation/nli_model.py` |

### Tema C — Systematic review & Evidence Gap Map

Modul terkait: `gap_detection/coverage_axes.py`, `coverage_map.py`, `support_gap.py`, `pipeline/corpus_relevance.py`

| Item | Tipe | Isi | ⭐ | Aktivitas | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|---|
| [SciSciCollective/pyscisci](https://github.com/SciSciCollective/pyscisci) | Repo | Science of Science | ⭐ 187 | 2026-08 | MIT | Adopsi | pySciSci: science-of-science (jaringan sitasi, kopling, metrik novelty/disruption) → metrik lanskap riset terstandar → `core/gap_detection/citation_coupling.py` |
| [ChaokunHong/MetaScreener](https://github.com/ChaokunHong/MetaScreener) | Repo | AI-powered tool for efficient abstract and PDF screening in systematic reviews. | ⭐ 1.332 | 2026-06 | Apache-2.0 | Rujukan | Skrining abstrak/PDF berbasis LLM dengan kriteria PICO → rujukan prompt ekstraksi PICO untuk sumbu Evidence Gap Map → `core/gap_detection/coverage_axes.py` |
| [asreview/asreview](https://github.com/asreview/asreview) | Repo | Active learning for systematic reviews | ⭐ 1.006 | 2026-09 | Apache-2.0 | Rujukan | Active learning untuk skrining systematic review → rujukan prioritisasi jurnal relevan & protokol simulasi evaluasi skrining → `core/pipeline/corpus_relevance.py` |
| [OpenKnowledgeMaps/Headstart](https://github.com/OpenKnowledgeMaps/Headstart) | Repo | A framework for creating web-based knowledge maps | ⭐ 220 | 2026-09 | MIT | Rujukan | Open Knowledge Maps: knowledge maps berbasis web → visualisasi lanskap riset → `core/gap_detection/coverage_map.py` |
| [nealhaddaway/citationchaser](https://github.com/nealhaddaway/citationchaser) | Repo | Perform forward and backward citation chasing as part of an evidence synthesis project | ⭐ 156 | 2025-03 | — | Rujukan | citationchaser (R): forward/backward citation chasing via Lens.org → rujukan perluasan korpus → `services/paper_apis/` |
| [jpruiz84/ScientoPy](https://github.com/jpruiz84/ScientoPy) | Repo | ScientoPy is a open-source Python based scientometric analysis tool | ⭐ 93 | 2026-08 | MIT | Rujukan | ScientoPy: analisis tren scientometrik (Scopus/WoS) → rujukan → `core/gap_detection/citation_coupling.py` |
| [mjwestgate/revtools](https://github.com/mjwestgate/revtools) | Repo | Tools to support research synthesis in R | ⭐ 59 | 2026-07 | — | Rujukan | Alat R untuk systematic review (dedup, topic model, skrining) → rujukan metode → `core/gap_detection/coverage_map.py` |

### Tema D — Bibliometrik & klien API literatur

Modul terkait: `gap_detection/citation_coupling.py`, `services/paper_apis/`, `services/reference_enrichment.py`

| Item | Tipe | Isi | ⭐ | Aktivitas | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|---|
| [lukasschwab/arxiv.py](https://github.com/lukasschwab/arxiv.py) | Repo | Python wrapper for the arXiv API | ⭐ 1.545 | 2026-09 | MIT | Adopsi | Klien arXiv API resmi-komunitas → pengganti parser Atom manual → `services/paper_apis/` |
| [jannisborn/paperscraper](https://github.com/jannisborn/paperscraper) | Repo | A bibliometrics tool for publication metadata (pubmed, arxiv, medrxiv, biorxiv, chemrxiv) and citation analyse… | ⭐ 541 | 2026-09 | MIT | Adopsi | Scraping metadata/PDF arXiv, PubMed, bio/med/chemRxiv → pengunduh korpus eksperimen → `experiments/download_papers.py` |
| [danielnsilva/semanticscholar](https://github.com/danielnsilva/semanticscholar) | Repo | Unofficial Python client library for Semantic Scholar APIs. | ⭐ 480 | 2026-08 | MIT | Adopsi | Klien S2 Graph API (references, citations, embedding SPECTER2) → sumber sitasi kedua untuk kopling bibliografis → `services/paper_apis/` |
| [J535D165/pyalex](https://github.com/J535D165/pyalex) | Repo | A Python library for OpenAlex (openalex.org) | ⭐ 410 | 2026-07 | MIT | Adopsi | Klien Python OpenAlex (works, `cited_by`, `referenced_works`, paginasi, polite pool) → pengganti pemanggilan HTTP manual di `OpenAlexAPI` & novelty check → `services/paper_apis/openalex.py` |
| [fabiobatalha/crossrefapi](https://github.com/fabiobatalha/crossrefapi) | Repo | A python library that implements the Crossref API. | ⭐ 348 | 2025-07 | BSD-2-Clause | Adopsi | Klien Crossref → resolusi DOI/metadata & pengayaan referensi → `core/pipeline/metadata_resolver.py` |
| [sckott/habanero](https://github.com/sckott/habanero) | Repo | Python client for Crossref search API | ⭐ 251 | 2026-09 | MIT | Adopsi | Klien Crossref alternatif (works, cn, counts) → pengayaan referensi → `services/reference_enrichment.py` |
| [allenai/scicite](https://github.com/allenai/scicite) | Dataset | Repository for NAACL 2019 paper on Citation Intent prediction | ⭐ 130 | 2019-12 | Apache-2.0 | Dataset evaluasi | SciCite (NAACL 2019): *citation intent* background/method/result → membobot kopling bibliografis (sitasi *result* > *background*) → `core/gap_detection/citation_coupling.py` |
| [allenai/multicite](https://github.com/allenai/multicite) | Dataset | MultiCite code and data. Models are available on Huggingface. | ⭐ 37 | 2022-05 | — | Dataset evaluasi | MultiCite: intent sitasi multi-kalimat & multi-label (model di HF) → konteks sitasi paper penuh → `core/gap_detection/citation_coupling.py` |
| [copenlu/cite-worth](https://github.com/copenlu/cite-worth) | Dataset | Data and code for the paper "CiteWorth: Cite-Worthiness Detection for Improved Scientific Document Understandi… | ⭐ 14 | 2022-09 | MIT | Dataset evaluasi | CiteWorth: deteksi kalimat yang layak sitasi → klaim tak bersitasi = indikator *incompleteness* → `core/gap_detection/support_gap.py` |
| [oacore/dynamic_citation_context](https://github.com/oacore/dynamic_citation_context) | Dataset | This repository contains dataset and | ⭐ 7 | 2023-10 | MIT | Dataset evaluasi | Konteks sitasi dinamis (CORE) → panjang konteks sitasi optimal → `core/gap_detection/citation_coupling.py` |
| [scholarly-python-package/scholarly](https://github.com/scholarly-python-package/scholarly) | Repo | Retrieve author and publication information from Google Scholar in a friendly, Pythonic way without having to … | ⭐ 1.880 | 2026-03 | Unlicense | Rujukan | Akses Google Scholar → fallback metadata (perhatikan rate limit/ToS) → `services/paper_apis/` |
| [massimoaria/bibliometrix](https://github.com/massimoaria/bibliometrix) | Repo | An R-tool for comprehensive science mapping analysis. A package for quantitative research in scientometrics an… | ⭐ 662 | 2026-09 | lainnya | Rujukan | Rujukan metode kopling bibliografis/co-citation & normalisasi Salton/Jaccard (R) → `core/gap_detection/citation_coupling.py` |
| [pybliometrics-dev/pybliometrics](https://github.com/pybliometrics-dev/pybliometrics) | Repo | Python-based API-Wrapper to access Scopus | ⭐ 499 | 2026-02 | lainnya | Rujukan | Klien Scopus API → sumber referensi tambahan bila institusi punya akses → `services/paper_apis/` |
| [NLeSC/litstudy](https://github.com/NLeSC/litstudy) | Repo | LitStudy: Using the power of Python to automate scientific literature analysis from the comfort of a Jupyter n… | ⭐ 221 | 2025-05 | Apache-2.0 | Rujukan | Analisis literatur (bibliometrik, jaringan sitasi, topik) dari OpenAlex/Scopus/S2 → rujukan kopling bibliografis & visualisasi → `core/gap_detection/citation_coupling.py` |
| [Valdecy/pyBibX](https://github.com/Valdecy/pybibx) | Repo | A Bibliometric and Scientometric Python Library Powered with Artificial Intelligence Tools | ⭐ 221 | 2026-06 | lainnya | Rujukan | Bibliometrik + AI (Scopus/WoS/PubMed) → rujukan analisis tren → `core/gap_detection/citation_coupling.py` |

**Model/dataset Hugging Face (tema D):**

| Item | Tipe | ♥ / ⬇ | Modifikasi | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|
| [allenai/scicite](https://huggingface.co/datasets/allenai/scicite) <sub>HF dataset</sub> | Dataset | ♥ 4 · ⬇ 660 | 2023-12 | — | Dataset evaluasi | SciCite versi HF → `core/gap_detection/citation_coupling.py` |

### Tema E — Parsing PDF ilmiah, seksi & referensi

Modul terkait: `core/pipeline/layout.py`, `section_normalizer.py`, `metadata_resolver.py`, `references.py`, `text_cleaning.py`

| Item | Tipe | Isi | ⭐ | Aktivitas | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|---|
| [docling-project/docling](https://github.com/docling-project/docling) | Repo | Get your documents ready for gen AI | ⭐ 66.464 | 2026-09 | MIT | Adopsi | Parser dokumen IBM (layout, heading, tabel, reading order → Markdown/JSON) → alternatif kuat untuk `layout.py` + `text_cleaning.py` → `core/pipeline/layout.py` |
| [datalab-to/marker](https://github.com/datalab-to/marker) | Repo | Convert PDF to markdown + JSON quickly with high accuracy | ⭐ 39.766 | 2026-09 | Apache-2.0 | Adopsi | PDF → Markdown dengan heading & tabel (OCR opsional) → alternatif cepat pipeline ingest → `core/pipeline/layout.py` |
| [datalab-to/surya](https://github.com/datalab-to/surya) | Repo | OCR, layout analysis, reading order, table recognition in 90+ languages | ⭐ 21.392 | 2026-09 | Apache-2.0 | Adopsi | OCR + layout + reading order multibahasa → pengganti ocrd untuk PDF hasil scan → `core/pipeline/pipeline.py` |
| [jsvine/pdfplumber](https://github.com/jsvine/pdfplumber) | Repo | Plumb a PDF for detailed information about each char, rectangle, line, et cetera — and easily extract text and… | ⭐ 10.744 | 2026-08 | MIT | Adopsi | Ekstraksi teks/tabel dengan geometri karakter → alternatif fallback pypdf → `core/pipeline/pipeline.py` |
| [pymupdf/PyMuPDF](https://github.com/pymupdf/PyMuPDF) | Repo | PyMuPDF is a high performance Python library for data extraction, analysis, conversion & manipulation of PDF (… | ⭐ 10.717 | 2026-09 | AGPL-3.0 | Adopsi | Sudah dependensi proyek; info font/bbox per span untuk deteksi heading sadar-font → `core/pipeline/layout.py` |
| [py-pdf/pypdf](https://github.com/py-pdf/pypdf) | Repo | A pure-python PDF library capable of splitting, merging, cropping, and transforming the pages of PDF files | ⭐ 10.204 | 2026-09 | lainnya | Adopsi | Sudah dipakai sebagai fallback ekstraksi teks → `core/pipeline/pipeline.py` |
| [grobidOrg/grobid](https://github.com/grobidOrg/grobid) | Repo | A machine learning software for extracting information from scholarly documents | ⭐ 5.130 | 2026-09 | Apache-2.0 | Adopsi | GROBID: header/metadata/seksi/referensi PDF ilmiah (TEI) — sudah opsional via `GROBID_URL`; perluas ke referensi (`processReferences`) menggantikan heuristik `references.py` → `core/pipeline/metadata_resolver.py` |
| [grobidOrg/grobid](https://github.com/grobidOrg/grobid) | Repo | A machine learning software for extracting information from scholarly documents | ⭐ 5.130 | 2026-09 | Apache-2.0 | Adopsi | GROBID: header/metadata/seksi/referensi PDF ilmiah (TEI) — sudah opsional via `GROBID_URL`; perluas ke referensi (`processReferences`) menggantikan heuristik `references.py` → `core/pipeline/metadata_resolver.py` |
| [pymupdf/pymupdf4llm](https://github.com/pymupdf/pymupdf4llm) | Repo | PyMuPDF4LLM | ⭐ 2.176 | 2026-09 | AGPL-3.0 | Adopsi | PDF → Markdown dengan heading dari ukuran font → pelengkap ringan deteksi heading → `core/pipeline/layout.py` |
| [pymupdf/pymupdf4llm](https://github.com/pymupdf/pymupdf4llm) | Repo | PyMuPDF4LLM | ⭐ 2.176 | 2026-09 | AGPL-3.0 | Adopsi | PDF → Markdown dengan heading dari ukuran font → pelengkap ringan deteksi heading → `core/pipeline/layout.py` |
| [inukshuk/anystyle](https://github.com/inukshuk/anystyle) | Repo | Fast citation reference parsing | ⭐ 1.289 | 2025-05 | lainnya | Adopsi | Parser string referensi berbasis CRF (Ruby CLI) → pembanding/pengganti pemisahan field referensi → `core/pipeline/references.py` |
| [grobidOrg/grobid-client-python](https://github.com/grobidOrg/grobid-client-python) | Repo | Python client for GROBID Web services | ⭐ 416 | 2026-08 | Apache-2.0 | Adopsi | Klien Python resmi GROBID (batch, concurrency) → pengganti `GrobidClient` buatan sendiri → `services/paper_apis/grobid.py` |
| [inspirehep/refextract](https://github.com/inspirehep/refextract) | Repo | Extract bibliographic references from (High-Energy Physics) articles. | ⭐ 143 | 2026-04 | GPL-2.0 | Adopsi | Ekstraksi referensi dari PDF/teks (INSPIRE-HEP) → adopsi langsung untuk daftar pustaka → `core/pipeline/references.py` |
| [OCR-D/core](https://github.com/OCR-D/core) | Repo | Collection of OCR-related python tools and wrappers from @OCR-D | ⭐ 136 | 2026-07 | Apache-2.0 | Adopsi | Sudah dipakai (layanan ocrd) untuk PDF hasil scan → `core/pipeline/pipeline.py` |
| [windx0303/CODA-19](https://github.com/windx0303/CODA-19) | Dataset | This is the Github repo of "CODA-19: Using a Non-Expert Crowd to Annotate Research Aspects on 10,000+ Abstract… | ⭐ 38 | 2021-10 | — | Dataset evaluasi | CODA-19: 10k abstrak beranotasi Background/Purpose/Method/Finding → data latih klasifikasi aspek riset → `core/gap_detection/claim_normalization.py` |
| [PKU-TANGENT/SciDTB](https://github.com/PKU-TANGENT/SciDTB) | Dataset | SciDTB: Discourse Dependency TreeBank for Scientific Abstracts | ⭐ 28 | 2018-07 | — | Dataset evaluasi | SciDTB: discourse dependency treebank abstrak ilmiah → struktur wacana abstrak → `core/gap_mining/candidates.py` |
| [boschresearch/mulms-az-codi2023](https://github.com/boschresearch/mulms-az-codi2023) | Dataset | Code and resources for our CODI paper "MuLMS-AZ: An Argumentative Zoning Dataset for the Materials Science Dom… | ⭐ 2 | 2024-11 | AGPL-3.0 | Dataset evaluasi | MuLMS-AZ: argumentative zoning domain material science (CODI 2023) → skema label AZ modern & contoh transfer domain → `core/pipeline/section_normalizer.py` |
| [opendatalab/MinerU](https://github.com/opendatalab/MinerU) | Repo | Transforms complex documents like PDFs and Office docs into LLM-ready markdown/JSON for your Agentic workflows… | ⭐ 79.987 | 2026-09 | lainnya | Rujukan | Ekstraksi dokumen → Markdown/JSON dengan layout model, rumus, tabel → pembanding docling → `core/pipeline/layout.py` |
| [opendataloader-project/opendataloader-pdf](https://github.com/opendataloader-project/opendataloader-pdf) | Repo | PDF Parser for AI-ready data. Automate PDF accessibility. Open-source. | ⭐ 29.250 | 2026-09 | Apache-2.0 | Rujukan | Parser PDF untuk data AI-ready (struktur, tabel) → `core/pipeline/layout.py` |
| [allenai/olmocr](https://github.com/allenai/olmocr) | Repo | Toolkit for linearizing PDFs for LLM datasets/training | ⭐ 19.596 | 2026-03 | Apache-2.0 | Rujukan | OCR PDF dengan VLM skala besar → OCR kualitas tinggi untuk PDF scan (butuh GPU) → `core/pipeline/pipeline.py` |
| [Unstructured-IO/unstructured](https://github.com/Unstructured-IO/unstructured) | Repo | Convert documents to structured data effortlessly. Unstructured is open-source ETL solution for transforming c… | ⭐ 15.435 | 2026-09 | Apache-2.0 | Rujukan | Partisi dokumen ke elemen (Title, NarrativeText, Table) → rujukan chunking sadar struktur → `core/pipeline/token_chunker.py` |
| [facebookresearch/nougat](https://github.com/facebookresearch/nougat) | Repo | Implementation of Nougat Neural Optical Understanding for Academic Documents | ⭐ 10.076 | 2025-02 | MIT | Rujukan | Nougat: OCR akademik visual → Markdown (rumus/tabel) → jalur khusus PDF ilmiah hasil scan → `core/pipeline/pipeline.py` |
| [lumina-ai-inc/chunkr](https://github.com/lumina-ai-inc/chunkr) | Repo | Vision infrastructure to turn complex documents into RAG/LLM-ready data | ⭐ 4.144 | 2026-09 | AGPL-3.0 | Rujukan | Layout analysis + chunking semantik untuk RAG → rujukan chunking sadar-layout → `core/pipeline/token_chunker.py` |
| [Dicklesworthstone/llm_aided_ocr](https://github.com/Dicklesworthstone/llm_aided_ocr) | Repo | Enhances Tesseract OCR output using LLMs (local or API) for error correction, smart chunking, and markdown for… | ⭐ 2.999 | 2026-08 | lainnya | Rujukan | Koreksi keluaran OCR dengan LLM → rujukan pembersihan teks OCR → `core/pipeline/text_cleaning.py` |
| [chatdoc-com/OCRFlux](https://github.com/chatdoc-com/OCRFlux) | Repo | OCRFlux is a lightweight yet powerful multimodal toolkit that significantly advances PDF-to-Markdown conversio… | ⭐ 2.530 | 2026-04 | Apache-2.0 | Rujukan | OCR multimodal ringan → alternatif OCR → `core/pipeline/pipeline.py` |
| [allenai/papermage](https://github.com/allenai/papermage) | Repo | library supporting NLP and CV research on scientific papers | ⭐ 803 | 2024-11 | Apache-2.0 | Rujukan | Representasi dokumen ilmiah berlapis (token/blok/seksi) + predictor layout → pembanding `layout.py` → `core/pipeline/layout.py` |

**Model/dataset Hugging Face (tema E):**

| Item | Tipe | ♥ / ⬇ | Modifikasi | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|
| [facebook/nougat-base](https://huggingface.co/facebook/nougat-base) <sub>HF model</sub> | Model | ♥ 189 · ⬇ 113.706 | 2023-11 | cc-by-nc-4.0 | Adopsi | Bobot Nougat siap pakai (transformers) → `core/pipeline/pipeline.py` |
| [saier/unarXive_imrad_clf](https://huggingface.co/datasets/saier/unarXive_imrad_clf) <sub>HF dataset</sub> | Dataset | ♥ 8 · ⬇ 155 | 2023-04 | cc-by-sa-4.0 | Dataset evaluasi | Klasifikasi seksi IMRaD dari unarXive → melatih/menguji pemetaan heading → IMRaD menggantikan regex `_SECTION_PATTERNS` → `core/pipeline/section_normalizer.py` |

### Tema F — Ekstraksi informasi → Knowledge Graph

Modul terkait: `core/knowledge/fact_extractor.py`, `fact_table.py`, `core/knowledge_graph/`, `gap_detection/semantic_match.py`

| Item | Tipe | Isi | ⭐ | Aktivitas | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|---|
| [stanfordnlp/stanza](https://github.com/stanfordnlp/stanza) | Repo | Stanford NLP Python library for tokenization, sentence segmentation, NER, and parsing of many human languages | ⭐ 7.876 | 2026-09 | lainnya | Adopsi | Pipeline NLP Python (Stanford) dengan klien CoreNLP → dependency parsing/OpenIE dari Python → `core/knowledge/fact_extractor.py` |
| [allenai/scispacy](https://github.com/allenai/scispacy) | Repo | A full spaCy pipeline and models for scientific/biomedical documents. | ⭐ 1.990 | 2025-12 | Apache-2.0 | Adopsi | spaCy untuk teks ilmiah/biomedis (NER, singkatan, entity linking) → pra-ekstraksi entitas sebelum LLM, mengurangi halusinasi SPO → `core/knowledge/fact_extractor.py` |
| [allenai/SPECTER2](https://github.com/allenai/SPECTER2) | Repo | — | ⭐ 143 | 2026-02 | Apache-2.0 | Adopsi | Kode & adapter SPECTER2 (proximity, adhoc query, classification) → `core/gap_detection/semantic_match.py` |
| [malteos/scincl](https://github.com/malteos/scincl) | Repo | Neighborhood Contrastive Learning for Scientific Document Representations with Citation Embeddings (EMNLP 2022… | ⭐ 80 | 2025-12 | MIT | Adopsi | SciNCL: embedding paper kontrastif berbasis tetangga sitasi → alternatif SPECTER2 → `core/gap_detection/semantic_match.py` |
| [stanfordnlp/CoreNLP](https://github.com/stanfordnlp/CoreNLP) | Repo | CoreNLP: A Java suite of core NLP tools for tokenization, sentence segmentation, NER, parsing, coreference, se… | ⭐ 10.114 | 2026-09 | GPL-3.0 | Baseline | Stanford OpenIE (Java) → baseline SPO non-LLM → `core/knowledge/fact_extractor.py` |
| [zjunlp/DeepKE](https://github.com/zjunlp/DeepKE) | Repo | [EMNLP 2022] An Open Toolkit for Knowledge Graph Extraction and Construction | ⭐ 4.479 | 2026-07 | MIT | Baseline | Toolkit NER/RE/AE (termasuk mode LLM) → baseline RE → `core/knowledge/fact_extractor.py` |
| [stair-lab/kg-gen](https://github.com/stair-lab/kg-gen) | Repo | [NeurIPS '25] Knowledge Graph Generation from Any Text | ⭐ 1.270 | 2026-03 | — | Baseline | Ekstraksi KG dari teks dengan LLM (DSPy) + clustering entitas → pembanding `fact_extractor.py` (MIT) → `core/knowledge/fact_extractor.py` |
| [dwadden/dygiepp](https://github.com/dwadden/dygiepp) | Repo | Span-based system for named entity, relation, and event extraction. | ⭐ 593 | 2026-07 | MIT | Baseline | DyGIE++: ekstraksi entitas/relasi/event (SciERC) → baseline non-LLM untuk triple SPO → `core/knowledge/fact_extractor.py` |
| [zjunlp/OneKE](https://github.com/zjunlp/OneKE) | Repo | [WWW 2025] A Dockerized Schema-Guided LLM Agent-based Knowledge Extraction System. | ⭐ 193 | 2025-07 | MIT | Baseline | Ekstraksi pengetahuan berbasis skema dengan LLM multi-agen → pembanding → `core/knowledge/fact_extractor.py` |
| [allenai/SciREX](https://github.com/allenai/SciREX) | Dataset | Data/Code Repository for https://api.semanticscholar.org/CorpusID:218470122 | ⭐ 141 | 2024-07 | Apache-2.0 | Dataset evaluasi | IE level dokumen (dataset, metode, tugas, metrik + relasi) → gold ekstraksi fakta dokumen-penuh → `core/knowledge/fact_extractor.py` |
| [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) | Repo | Turn any codebase, with its docs, SQL schemas, configs, and PDFs, into a queryable knowledge graph. A /graphif… | ⭐ 118.058 | 2026-09 | Apache-2.0 | Rujukan | Graf pengetahuan dari codebase/dokumen (skill `graphify` sudah ada di proyek) → rujukan → `core/knowledge_graph/` |
| [run-llama/llama_index](https://github.com/run-llama/llama_index) | Repo | LlamaIndex is the document processing platform for AI | ⭐ 52.177 | 2026-09 | MIT | Rujukan | PropertyGraphIndex/KnowledgeGraphIndex → kerangka KG-RAG siap pakai → `core/knowledge_graph/` |
| [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) | Repo | [EMNLP2025] LightRAG: Simple and Fast Retrieval-Augmented Generation | ⭐ 39.676 | 2026-09 | MIT | Rujukan | Graph RAG ringan (entitas-relasi dual-level) → alternatif implementasi KG-RAG → `core/agents/tools/kg_querier_tool.py` |
| [microsoft/graphrag](https://github.com/microsoft/graphrag) | Repo | A modular graph-based Retrieval-Augmented Generation (RAG) system | ⭐ 35.986 | 2026-09 | MIT | Rujukan | GraphRAG: ekstraksi entitas-relasi + komunitas Leiden + ringkasan komunitas → rujukan KG + deteksi fragmentasi (komunitas = klaster tema) → `core/knowledge_graph/` |
| [neo4j-labs/llm-graph-builder](https://github.com/neo4j-labs/llm-graph-builder) | Repo | Neo4j graph construction from unstructured data using LLMs | ⭐ 5.252 | 2026-09 | Apache-2.0 | Rujukan | Builder KG dari PDF dengan LLM (Neo4j) → rujukan pipeline & UI → `core/knowledge_graph/` |
| [OSU-NLP-Group/HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG) | Repo | [NeurIPS'24] HippoRAG is a novel RAG framework inspired by human long-term memory that enables LLMs to continu… | ⭐ 4.007 | 2026-09 | MIT | Rujukan | RAG berbasis KG + Personalized PageRank (NeurIPS 24) → retrieval multi-hop → `core/agents/tools/kg_querier_tool.py` |
| [gusye1234/nano-graphrag](https://github.com/gusye1234/nano-graphrag) | Repo | A simple, easy-to-hack GraphRAG implementation | ⭐ 3.988 | 2026-01 | MIT | Rujukan | GraphRAG ringkas (~1.100 baris) → mudah dipelajari/diadaptasi → `core/knowledge_graph/` |
| [yifanfeng97/Hyper-Extract](https://github.com/yifanfeng97/Hyper-Extract) | Repo | Hypergraph is more powerful. Transform unstructured text into structured knowledge with LLMs. Graphs, hypergra… | ⭐ 3.946 | 2026-09 | lainnya | Rujukan | Ekstraksi hypergraph (relasi n-ary) → rujukan untuk fakta kompleks di luar SPO → `core/knowledge/fact_table.py` |
| [pykeen/pykeen](https://github.com/pykeen/pykeen) | Repo | 🤖 A Python library for learning and evaluating knowledge graph embeddings | ⭐ 2.036 | 2026-09 | MIT | Rujukan | Embedding KG (TransE, RotatE…) untuk link prediction → memprediksi relasi hilang = sinyal *incompleteness* → `core/knowledge_graph/` |
| [AuvaLab/itext2kg](https://github.com/AuvaLab/itext2kg) | Repo | We build KGs the way nature builds matter | ⭐ 966 | 2026-09 | Apache-2.0 | Rujukan | Text2KG inkremental + resolusi entitas → pola KG bertahap per dokumen yang diunggah → `core/knowledge/fact_table.py` |
| [zjunlp/AutoKG](https://github.com/zjunlp/AutoKG) | Repo | [WWWJ 2024] LLMs for Knowledge Graph Construction and Reasoning: Recent Capabilities and Future Opportunities | ⭐ 473 | 2025-01 | MIT | Rujukan | LLM untuk konstruksi KG (survey + kode) → rujukan → `core/knowledge/fact_extractor.py` |
| [HICAI-ZJU/SciToolAgent](https://github.com/HICAI-ZJU/SciToolAgent) | Repo | SciToolAgent: A Knowledge Graph-Driven Scientific Agent for Multi-Tool Integration | ⭐ 423 | 2025-08 | MIT | Rujukan | Agen ilmiah berbasis KG alat → rujukan → `core/agents/coordinator.py` |
| [AI4WA/Docs2KG](https://github.com/AI4WA/Docs2KG) | Repo | Docs2KG: A Human-LLM Collaborative Approach to Unified Knowledge Graph Construction from Heterogeneous Documen… | ⭐ 372 | 2025-05 | Apache-2.0 | Rujukan | Dokumen heterogen → KG (human-LLM) → rujukan pipeline dokumen→KG → `core/knowledge_graph/` |
| [fusion-jena/automatic-KG-creation-with-LLM](https://github.com/fusion-jena/automatic-KG-creation-with-LLM) | Repo | Automatic Ontology and Knowledge Graph construction with LLM | ⭐ 363 | 2025-04 | Apache-2.0 | Rujukan | Konstruksi ontologi + KG otomatis dengan LLM → rujukan → `core/knowledge_graph/` |
| [zjunlp/SciAtlas](https://github.com/zjunlp/SciAtlas) | Repo | A Large-Scale Knowledge Graph for Automated Scientific Research | ⭐ 151 | 2026-09 | MIT | Rujukan | KG ilmiah skala besar (2026) → rujukan skema entitas/relasi ilmiah → `core/knowledge/fact_table.py` |

**Model/dataset Hugging Face (tema F):**

| Item | Tipe | ♥ / ⬇ | Modifikasi | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|
| [allenai/scibert_scivocab_uncased](https://huggingface.co/allenai/scibert_scivocab_uncased) <sub>HF model</sub> | Model | ♥ 176 · ⬇ 208.767 | 2022-10 | — | Adopsi | Encoder domain ilmiah → fine-tuning NER/RE ringan sebagai pembanding ekstraksi LLM → `core/knowledge/fact_extractor.py` |
| [allenai/specter2_base](https://huggingface.co/allenai/specter2_base) <sub>HF model</sub> | Model | ♥ 48 · ⬇ 1.064.365 | 2024-12 | apache-2.0 | Adopsi | Embedding dokumen ilmiah sadar-sitasi → similarity paper untuk kopling, `semantic_match.py`, dan klaster fragmentasi → `core/gap_detection/semantic_match.py` |
| [malteos/scincl](https://huggingface.co/malteos/scincl) <sub>HF model</sub> | Model | ♥ 35 · ⬇ 22.839 | 2024-06 | mit | Adopsi | Bobot SciNCL siap pakai → `core/gap_detection/semantic_match.py` |
| [nsusemiehl/SciERC](https://huggingface.co/datasets/nsusemiehl/SciERC) <sub>HF dataset</sub> | Dataset | ♥ 2 · ⬇ 197 | 2022-04 | — | Dataset evaluasi | SciERC (500 abstrak, entitas & relasi ilmiah) → evaluasi ekstraktor → `core/knowledge/fact_extractor.py` |

### Tema G — Agen riset literatur

Modul terkait: `core/agents/coordinator.py`, `agents/tools/self_critic_tool.py`, `core/recommendation/`

| Item | Tipe | Isi | ⭐ | Aktivitas | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|---|
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | Repo | Build resilient agents. | ⭐ 41.717 | 2026-09 | MIT | Adopsi | Sudah dipakai sebagai kerangka koordinator → `core/agents/coordinator.py` |
| [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher) | Repo | An autonomous agent that conducts deep research on any data using any LLM providers | ⭐ 29.472 | 2026-08 | Apache-2.0 | Baseline | Agen deep research dengan laporan bersitasi → baseline generik → `core/agents/coordinator.py` |
| [Future-House/paper-qa](https://github.com/Future-House/paper-qa) | Repo | High accuracy RAG for answering questions from scientific documents with citations | ⭐ 9.203 | 2026-09 | Apache-2.0 | Baseline | PaperQA2: agen RAG sintesis literatur dengan citation grounding & deteksi kontradiksi → **baseline utama BAB IV** dan rujukan pola Search→Gather→Answer → `core/agents/coordinator.py` |
| [AkariAsai/OpenScholar](https://github.com/AkariAsai/OpenScholar) | Repo | This repository includes the official implementation of OpenScholar: Synthesizing Scientific Literature with R… | ⭐ 1.595 | 2025-08 | Apache-2.0 | Baseline | RAG ilmiah dengan self-feedback loop & datastore 45M paper → baseline citation grounding → `core/agents/tools/self_critic_tool.py` |
| [Ayanami0730/deep_research_bench](https://github.com/Ayanami0730/deep_research_bench) | Benchmark | DeepResearch Bench: A Comprehensive Benchmark for Deep Research Agents | ⭐ 829 | 2026-05 | Apache-2.0 | Dataset evaluasi | Benchmark deep research → evaluasi agen → `experiments/` |
| [OSU-NLP-Group/ScienceAgentBench](https://github.com/OSU-NLP-Group/ScienceAgentBench) | Benchmark | [ICLR'25] ScienceAgentBench: Toward Rigorous Assessment of Language Agents for Data-Driven Scientific Discover… | ⭐ 171 | 2026-07 | MIT | Dataset evaluasi | ScienceAgentBench (ICLR 2025): evaluasi ketat agen untuk penemuan ilmiah → rujukan protokol evaluasi agen (rubrik, success rate) → `experiments/` |
| [AkariAsai/ScholarQABench](https://github.com/AkariAsai/ScholarQABench) | Benchmark | This repository contains ScholarQABench data and evaluation pipeline. | ⭐ 165 | 2025-08 | MIT | Dataset evaluasi | Benchmark QA literatur ilmiah bersitasi → evaluasi retrieval + sintesis → `experiments/evaluate_retrieval.py` |
| [allenai/discoverybench](https://github.com/allenai/discoverybench) | Benchmark | Discovering Data-driven Hypotheses in the Wild | ⭐ 161 | 2025-06 | lainnya | Dataset evaluasi | DiscoveryBench: penemuan berbasis data oleh LLM → rujukan → `experiments/` |
| [Future-House/LAB-Bench](https://github.com/Future-House/LAB-Bench) | Benchmark | Evaluation dataset for AI systems intended to benchmark capabilities foundational to scientific research in bi… | ⭐ 130 | 2025-09 | CC-BY-SA-4.0 | Dataset evaluasi | LAB-Bench (Future-House): termasuk tugas LitQA (QA literatur) → evaluasi retrieval literatur → `experiments/evaluate_retrieval.py` |
| [imlrz/DeepResearch-Bench-II](https://github.com/imlrz/DeepResearch-Bench-II) | Benchmark | DeepResearch Bench II (DRB2) is the follow-up to DeepResearch Bench, with a stronger focus on measuring the ga… | ⭐ 88 | 2026-09 | Apache-2.0 | Dataset evaluasi | DeepResearch Bench II → evaluasi agen → `experiments/` |
| [chchenhui/mlrbench](https://github.com/chchenhui/mlrbench) | Benchmark | [NeurIPS 2025 D&B Track] MLR-Bench: Evaluating AI Agents on Open-Ended Machine Learning Research | ⭐ 36 | 2026-09 | MIT | Dataset evaluasi | MLR-Bench (NeurIPS 2025): riset ML open-ended → rubrik LLM-judge untuk ide/limitasi → `experiments/cross_critic.py` |
| [x66ccff/liveideabench](https://github.com/x66ccff/liveideabench) | Benchmark | [𝐍𝐚𝐭𝐮𝐫𝐞 𝐂𝐨𝐦𝐦𝐮𝐧𝐢𝐜𝐚𝐭𝐢𝐨𝐧𝐬] 🤖💡 LiveIdeaBench: Evaluating LLMs' Scientific Creativity and Idea Generation with Mini… | ⭐ 35 | 2026-04 | MIT | Dataset evaluasi | LiveIdeaBench: kreativitas ilmiah LLM (novelty/feasibility) → metrik ide → `core/recommendation/novelty.py` |
| [RenzeLou/AAAR-1.0](https://github.com/RenzeLou/AAAR-1.0) | Benchmark | The source code for running LLMs on the AAAR-1.0 benchmark. | ⭐ 20 | 2025-04 | MIT | Dataset evaluasi | AAAR-1.0: tugas *paper weakness* & review critique → evaluasi langsung kemampuan menemukan limitasi → `experiments/evaluate_gaps.py` |
| [amir-hassan25/IdeaBench](https://github.com/amir-hassan25/IdeaBench) | Benchmark | — | ⭐ 13 | 2025-05 | — | Dataset evaluasi | IdeaBench: benchmark generasi ide riset → evaluasi rekomendasi → `core/recommendation/engine.py` |
| [ankitala/ResearchBench](https://github.com/ankitala/ResearchBench) | Benchmark | [ACL 2026] <ResearchBench: Benchmarking LLMs in Scientific Discovery via Inspiration-Based Task Decomposition> | ⭐ 9 | 2026-05 | MIT | Dataset evaluasi | ResearchBench (ACL 2026) → benchmark kemampuan riset LLM → `experiments/` |
| [bytedance/deer-flow](https://github.com/bytedance/deer-flow) | Repo | An open-source long-horizon SuperAgent harness that researches, codes, and creates. With the help of sandboxes… | ⭐ 82.503 | 2026-09 | MIT | Rujukan | Deep research LangGraph produksi (planner, researcher, reporter) → rujukan arsitektur → `core/agents/coordinator.py` |
| [stanford-oval/storm](https://github.com/stanford-oval/storm) | Repo | An LLM-powered knowledge curation system that researches a topic and generates a full-length report with citat… | ⭐ 31.400 | 2025-09 | MIT | Rujukan | STORM/Co-STORM: riset multi-perspektif → outline → artikel bersitasi → rujukan sintesis multi-sumber → `core/recommendation/engine.py` |
| [dzhng/deep-research](https://github.com/dzhng/deep-research) | Repo | An AI-powered research assistant that performs iterative, deep research on any topic by combining search engin… | ⭐ 19.678 | 2026-04 | MIT | Rujukan | Deep research iteratif (breadth/depth) → rujukan → `core/agents/coordinator.py` |
| [SakanaAI/AI-Scientist](https://github.com/SakanaAI/AI-Scientist) | Repo | The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery 🧑‍🔬 | ⭐ 14.560 | 2025-12 | lainnya | Rujukan | Pipeline riset otomatis (ide → eksperimen → paper → review) → rujukan self-review loop → `core/agents/tools/self_critic_tool.py` |
| [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) | Repo | The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via Agentic Tree Search | ⭐ 7.153 | 2025-12 | lainnya | Rujukan | Versi 2 dengan agentic tree search → rujukan eksplorasi bercabang → `core/agents/coordinator.py` |
| [SamuelSchmidgall/AgentLaboratory](https://github.com/SamuelSchmidgall/AgentLaboratory) | Repo | Agent Laboratory is an end-to-end autonomous research workflow meant to assist you as the human researcher tow… | ⭐ 5.849 | 2025-08 | MIT | Rujukan | Agen asisten riset (lit review → eksperimen → laporan) human-in-the-loop → rujukan → `core/agents/coordinator.py` |
| [noahshinn/reflexion](https://github.com/noahshinn/reflexion) | Repo | [NeurIPS 2023] Reflexion: Language Agents with Verbal Reinforcement Learning | ⭐ 3.267 | 2025-01 | MIT | Rujukan | Reflexion: refleksi verbal & memori episodik → rujukan self-critique → `core/agents/tools/self_critic_tool.py` |
| [openai/frontier-evals](https://github.com/openai/frontier-evals) | Benchmark | OpenAI Frontier Evals | ⭐ 1.300 | 2026-04 | MIT | Rujukan | PaperBench (di `project/paperbench/`): rubrik hierarkis penilaian replikasi paper → rujukan rubrik → `experiments/` |
| [IAAR-Shanghai/SurveyX](https://github.com/IAAR-Shanghai/SurveyX) | Repo | Academic Survey Paper Generation. | ⭐ 991 | 2026-01 | — | Rujukan | Generasi survey akademik → rujukan → `core/recommendation/themes.py` |
| [madaan/self-refine](https://github.com/madaan/self-refine) | Repo | LLMs can generate feedback on their work, use it to improve the output, and repeat this process iteratively. | ⭐ 820 | 2024-10 | Apache-2.0 | Rujukan | Self-Refine: feedback → refine iteratif → rujukan loop *evaluate* → `core/agents/tools/self_critic_tool.py` |
| [lamm-mit/SciAgentsDiscovery](https://github.com/lamm-mit/SciAgentsDiscovery) | Repo | — | ⭐ 639 | 2025-05 | Apache-2.0 | Rujukan | Multi-agen penemuan ilmiah berbasis KG ontologis → rujukan agen + KG → `core/agents/tools/kg_querier_tool.py` |
| [AutoSurveys/AutoSurvey](https://github.com/AutoSurveys/AutoSurvey) | Repo | — | ⭐ 476 | 2025-02 | — | Rujukan | Generasi survey otomatis → rujukan sintesis lintas-jurnal → `core/recommendation/themes.py` |
| [zhu-minjun/Researcher](https://github.com/zhu-minjun/Researcher) | Repo | CycleResearcher: Improving Automated Research via Automated Review | ⭐ 402 | 2026-03 | lainnya | Rujukan | CycleResearcher/CycleReviewer: model reviewer terbuka → judge lokal kualitas ide/gap → `experiments/cross_critic.py` |
| [snap-stanford/MLAgentBench](https://github.com/snap-stanford/MLAgentBench) | Benchmark | — | ⭐ 353 | 2024-06 | MIT | Rujukan | MLAgentBench → rujukan evaluasi agen → `experiments/` |
| [allenai/ai2-scholarqa-lib](https://github.com/allenai/ai2-scholarqa-lib) | Repo | Repo housing the open sourced code for the ai2 scholar qa app and also the corresponding library | ⭐ 280 | 2026-06 | Apache-2.0 | Rujukan | Ai2 ScholarQA: retrieval → quote extraction → clustering → sintesis → rujukan arsitektur multi-langkah → `core/agents/coordinator.py` |
| [tririver/arc](https://github.com/tririver/arc) | Repo | Agent Research Copilot (ARC) is a set of skills and tools (CLI) for theoretical physics literature review, ide… | ⭐ 87 | 2026-09 | MIT | Rujukan | Agent Research Copilot (skill riset) → rujukan → `core/agents/coordinator.py` |
| [JinchengGao-Infty/FWMA](https://github.com/JinchengGao-Infty/FWMA) | Repo | End-to-end AI literature review automation: crawl, screen, download, multi-agent review, and report generation | ⭐ 58 | 2026-03 | Apache-2.0 | Rujukan | Otomasi literature review end-to-end → rujukan → `core/recommendation/engine.py` |
| [LitLLM/litllm](https://github.com/LitLLM/LitLLM) | Repo | An AI-powered literature review assistant for researchers | ⭐ 52 | 2026-05 | Apache-2.0 | Rujukan | Toolkit literature review dengan LLM+RAG → rujukan → `core/recommendation/engine.py` |
| [xyzCS/SciReplicate-Bench](https://github.com/xyzCS/SciReplicate-Bench) | Benchmark | The dataset and code for paper "SciReplicate-Bench: Benchmarking LLMs in Agent-driven Algorithmic Reproduction… | ⭐ 13 | 2025-10 | — | Rujukan | SciReplicate-Bench → rujukan → `experiments/` |

### Tema H — Neuro-symbolic & rule engine

Modul terkait: `core/validation/rule_engine.py`, `relation_classifier.py`

| Item | Tipe | Isi | ⭐ | Aktivitas | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|---|
| [gorules/zen](https://github.com/gorules/zen) | Repo | Open-source Business Rules Engine for your Rust, NodeJS, Python, Go, Java, C#, Kotlin (JVM), Kotlin (Android) … | ⭐ 1.988 | 2026-08 | MIT | Adopsi | Business rules engine (decision table JDM, binding Python) → aturan yang dapat disunting non-programmer → `core/validation/rule_engine.py` |
| [jruizgit/rules](https://github.com/jruizgit/rules) | Repo | Durable Rules Engine | ⭐ 1.300 | 2025-07 | MIT | Adopsi | durable_rules: forward-chaining rule engine → alternatif implementasi aturan → `core/validation/rule_engine.py` |
| [potassco/clingo](https://github.com/potassco/clingo) | Repo | 🦉 A grounder and solver for logic programs. | ⭐ 831 | 2026-09 | MIT | Adopsi | ASP solver dengan API Python → 9 aturan sebagai program ASP; inkonsistensi = unsatisfiable core → `core/validation/rule_engine.py` |
| [zeroSteiner/rule-engine](https://github.com/zeroSteiner/rule-engine) | Repo | A lightweight, optionally typed expression language with a custom grammar for matching arbitrary Python object… | ⭐ 598 | 2026-08 | BSD-3-Clause | Adopsi | Bahasa ekspresi aturan bertipe → aturan yang dapat dikonfigurasi (YAML) tanpa mengubah kode → `core/validation/rule_engine.py` |
| [yuce/pyswip](https://github.com/yuce/pyswip) | Repo | PySwip is a Python-Prolog interface that enables querying SWI-Prolog in your Python programs. | ⭐ 548 | 2026-02 | MIT | Adopsi | SWI-Prolog dari Python → aturan kausalitas/konsistensi dalam Prolog → `core/validation/rule_engine.py` |
| [ML-KULeuven/problog](https://github.com/ML-KULeuven/problog) | Repo | ProbLog is a Probabilistic Logic Programming Language for logic programs with probabilities. | ⭐ 420 | 2026-09 | Apache-2.0 | Adopsi | ProbLog: logika probabilistik → menyatakan aturan F/C/K dengan probabilitas fakta dari LLM → `core/validation/rule_engine.py` |
| [lab-v2/pyreason](https://github.com/lab-v2/pyreason) | Repo | An explainable inference software supporting annotated, real valued, graph based and temporal logic | ⭐ 349 | 2026-09 | lainnya | Adopsi | PyReason: inferensi logika beranotasi (interval) atas graf dengan penjelasan → aturan atas KG dengan confidence interval → `core/validation/rule_engine.py` |
| [noxdafox/clipspy](https://github.com/noxdafox/clipspy) | Repo | Python CFFI bindings for the 'C' Language Integrated Production System CLIPS | ⭐ 203 | 2025-10 | BSD-3-Clause | Adopsi | Binding CLIPS untuk Python → rule engine matang → `core/validation/rule_engine.py` |
| [nilp0inter/experta](https://github.com/nilp0inter/experta) | Repo | Expert system framework for Python (fork of PyKnow, CLIPS-like rules) | ⭐ 196 | 2025-02 | LGPL-3.0 | Adopsi | Expert system CLIPS-like untuk Python (fork PyKnow) → aturan deklaratif → `core/validation/rule_engine.py` |
| [jiho283/FactKG](https://github.com/jiho283/FactKG) | Dataset | Official repository of FactKG | ⭐ 68 | 2025-04 | — | Dataset evaluasi | FactKG: 108k klaim verifikasi atas KG → uji rule engine pada klaim berbasis graf → `core/validation/rule_engine.py` |
| [ExtensityAI/symbolicai](https://github.com/ExtensityAI/symbolicai) | Repo | A neurosymbolic perspective on LLMs | ⭐ 1.761 | 2026-09 | BSD-3-Clause | Rujukan | Kerangka neurosymbolic untuk LLM (kontrak, operator simbolik) → rujukan → `core/validation/rule_engine.py` |
| [souffle-lang/souffle](https://github.com/souffle-lang/souffle) | Repo | Soufflé is a variant of Datalog for tool designers crafting analyses in Horn clauses. Soufflé synthesizes a na… | ⭐ 1.166 | 2026-07 | UPL-1.0 | Rujukan | Datalog cepat (C++) → skala besar → `core/validation/rule_engine.py` |
| [Libr-AI/OpenFactVerification](https://github.com/Libr-AI/OpenFactVerification) | Repo | Loki: Open-source solution designed to automate the process of verifying factuality | ⭐ 1.155 | 2024-10 | MIT | Rujukan | Loki: pipeline dekomposisi → pencarian → verifikasi faktual modular → rujukan → `core/agents/coordinator.py` |
| [scallop-lang/scallop](https://github.com/scallop-lang/scallop) | Repo | Framework and Language for Neurosymbolic Programming. | ⭐ 510 | 2026-06 | MIT | Rujukan | Datalog probabilistik + PyTorch → upgrade rule engine ke inferensi probabilistik atas fakta SPO berbobot confidence → `core/validation/rule_engine.py` |
| [logictensornetworks/logictensornetworks](https://github.com/logictensornetworks/logictensornetworks) | Repo | Deep Learning and Logical Reasoning from Data and Knowledge | ⭐ 375 | 2024-11 | MIT | Rujukan | Logic Tensor Networks: logika fuzzy diferensiabel → rujukan → `core/validation/rule_engine.py` |
| [ML-KULeuven/deepproblog](https://github.com/ML-KULeuven/deepproblog) | Repo | DeepProbLog is an extension of ProbLog that integrates Probabilistic Logic Programming with deep learning by i… | ⭐ 353 | 2026-09 | Apache-2.0 | Rujukan | DeepProbLog: ProbLog + jaringan saraf → rujukan → `core/validation/rule_engine.py` |
| [IBM/LNN](https://github.com/IBM/LNN) | Repo | A `Neural = Symbolic` framework for sound and complete weighted real-value logic | ⭐ 332 | 2026-09 | Apache-2.0 | Rujukan | Logical Neural Networks dengan penanganan kontradiksi eksplisit → rujukan aturan Consistency K1–K3 → `core/validation/rule_engine.py` |
| [pcarbonn/pyDatalog](https://github.com/pcarbonn/pyDatalog) | Repo | a datalog implementation in Python | ⭐ 321 | 2026-06 | LGPL-2.1 | Rujukan | Datalog dalam Python (tidak aktif) → `core/validation/rule_engine.py` |
| [Aiden0526/SymbCoT](https://github.com/Aiden0526/SymbCoT) | Repo | Codes and Data for ACL 2024 Paper "Faithful Logical Reasoning via Symbolic Chain-of-Thought". | ⭐ 207 | 2026-01 | MIT | Rujukan | Symbolic Chain-of-Thought → rujukan → `core/validation/relation_classifier.py` |
| [pyc-team/pytorch_concepts](https://github.com/pyc-team/pytorch_concepts) | Repo | PyC (Pytorch Concepts) is a PyTorch-based library for designing concept-based interpretable deep learning mode… | ⭐ 158 | 2026-09 | Apache-2.0 | Rujukan | Concept-based models PyTorch → rujukan → `core/validation/relation_classifier.py` |
| [gaorch85/Graph-of-States](https://github.com/gaorch85/Graph-of-States) | Repo | [ICML 2026] A neuro-symbolic framework for abductive reasoning that grounds multi-agent collaboration in struc… | ⭐ 139 | 2026-09 | MIT | Rujukan | Neuro-symbolic abductive reasoning (ICML 2026) → rujukan → `core/validation/rule_engine.py` |
| [AbductiveLearning/ABLkit](https://github.com/AbductiveLearning/ABLkit) | Repo | An efficient Python toolkit for Abductive Learning (ABL), a novel paradigm that integrates machine learning an… | ⭐ 100 | 2026-05 | lainnya | Rujukan | Abductive learning: ML + penalaran logis → rujukan koreksi label dengan basis pengetahuan → `core/validation/rule_engine.py` |
| [azreasoners/NeurASP](https://github.com/azreasoners/NeurASP) | Repo | — | ⭐ 57 | 2026-07 | — | Rujukan | ASP + jaringan saraf → rujukan → `core/validation/rule_engine.py` |

### Tema I — Kalibrasi, conformal prediction & abstention

Modul terkait: `core/gap_detection/calibration.py`, `core/gap_mining/extractor.py`

| Item | Tipe | Isi | ⭐ | Aktivitas | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|---|
| [scikit-learn-contrib/MAPIE](https://github.com/scikit-learn-contrib/MAPIE) | Repo | A scikit-learn-compatible library for estimating prediction intervals and controlling risks, based on conforma… | ⭐ 1.590 | 2026-09 | BSD-3-Clause | Adopsi | Conformal prediction scikit-learn → pengganti `conformal_threshold` buatan sendiri dengan jaminan cakupan → `core/gap_detection/calibration.py` |
| [henrikbostrom/crepes](https://github.com/henrikbostrom/crepes) | Repo | Python package for conformal prediction | ⭐ 582 | 2026-07 | BSD-3-Clause | Adopsi | Conformal classifiers/regressors (Mondrian) → alternatif ringan MAPIE → `core/gap_detection/calibration.py` |
| [IINemo/lm-polygraph](https://github.com/IINemo/lm-polygraph) | Repo | — | ⭐ 506 | 2026-09 | MIT | Adopsi | Estimasi ketidakpastian LLM (semantic entropy, p(true), dll.) → confidence pernyataan gap sebelum kalibrasi → `core/gap_mining/extractor.py` |
| [EFS-OpenSource/calibration-framework](https://github.com/EFS-OpenSource/calibration-framework) | Repo | The net:cal calibration framework is a Python 3 library for measuring and mitigating miscalibration of uncerta… | ⭐ 380 | 2026-04 | Apache-2.0 | Adopsi | net:cal — ECE/MCE, reliability diagram, temperature/Platt/beta → validasi silang `expected_calibration_error` & `fit_temperature` → `core/gap_detection/calibration.py` |
| [uncertainty-toolbox/uncertainty-toolbox](https://github.com/uncertainty-toolbox/uncertainty-toolbox) | Repo | Uncertainty Toolbox: a Python toolbox for predictive uncertainty quantification, calibration, metrics, and vis… | ⭐ 2.013 | 2025-03 | MIT | Rujukan | Metrik & visualisasi UQ → rujukan → `core/gap_detection/calibration.py` |
| [google/uncertainty-baselines](https://github.com/google/uncertainty-baselines) | Repo | High-quality implementations of standard and SOTA methods on a variety of tasks. | ⭐ 1.592 | 2026-09 | Apache-2.0 | Rujukan | Baseline UQ Google → rujukan → `core/gap_detection/calibration.py` |
| [valeman/awesome-conformal-prediction](https://github.com/valeman/awesome-conformal-prediction) | Repo | A professionally curated list of awesome Conformal Prediction videos, tutorials, books, papers, PhD and MSc th… | ⭐ 1.303 | 2026-08 | lainnya | Rujukan | Kurasi bahan conformal prediction → `core/gap_detection/calibration.py` |
| [gpleiss/temperature_scaling](https://github.com/gpleiss/temperature_scaling) | Repo | A simple way to calibrate your neural network. | ⭐ 1.175 | 2025-07 | MIT | Rujukan | Referensi temperature scaling (Guo et al. 2017) → `core/gap_detection/calibration.py` |
| [aangelopoulos/conformal-prediction](https://github.com/aangelopoulos/conformal-prediction) | Repo | Lightweight, useful implementation of conformal prediction on real data. | ⭐ 1.089 | 2025-11 | MIT | Rujukan | Notebook CP praktis (Angelopoulos & Bates) → tutorial → `core/gap_detection/calibration.py` |
| [torch-uncertainty/torch-uncertainty](https://github.com/torch-uncertainty/torch-uncertainty) | Repo | Open-source framework for uncertainty and deep learning models in PyTorch 🌱 | ⭐ 527 | 2026-09 | Apache-2.0 | Rujukan | Toolbox UQ PyTorch (ensembles, conformal, metrik kalibrasi) → `core/gap_detection/calibration.py` |
| [torch-uncertainty/torch-uncertainty](https://github.com/torch-uncertainty/torch-uncertainty) | Repo | Open-source framework for uncertainty and deep learning models in PyTorch 🌱 | ⭐ 527 | 2026-09 | Apache-2.0 | Rujukan | Toolbox UQ PyTorch (ensembles, conformal, metrik kalibrasi) → `core/gap_detection/calibration.py` |
| [ml-stat-Sustech/TorchCP](https://github.com/ml-stat-Sustech/TorchCP) | Repo | A Python toolbox for conformal prediction research on deep learning models, using PyTorch. | ⭐ 477 | 2026-08 | LGPL-3.0 | Rujukan | Toolbox CP PyTorch (klasifikasi, regresi, LLM) → `core/gap_detection/calibration.py` |
| [deel-ai/puncc](https://github.com/deel-ai/puncc) | Repo | 👋 Puncc is a python library for predictive uncertainty quantification using conformal prediction. | ⭐ 408 | 2026-09 | — | Rujukan | Conformal prediction (deel-ai) → alternatif → `core/gap_detection/calibration.py` |
| [ip200/venn-abers](https://github.com/ip200/venn-abers) | Repo | Python implementation of binary and multi-class Venn-ABERS calibration | ⭐ 208 | 2026-09 | MIT | Rujukan | Venn-ABERS: kalibrasi probabilistik dengan jaminan → rujukan → `core/gap_detection/calibration.py` |

### Tema J — Meta-analisis & heterogenitas

Modul terkait: `core/gap_detection/adjudication.py`, `experiments/stats_utils.py`

| Item | Tipe | Isi | ⭐ | Aktivitas | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|---|
| [statsmodels/statsmodels](https://github.com/statsmodels/statsmodels) | Repo | Statsmodels: statistical modeling and econometrics in Python | ⭐ 11.622 | 2026-09 | BSD-3-Clause | Adopsi | `stats.meta_analysis.combine_effects` (fixed/random, Q, I², τ² DL) → validasi angka heterogenitas → `experiments/stats_utils.py` |
| [neurostuff/PyMARE](https://github.com/neurostuff/PyMARE) | Repo | PyMARE: Python Meta-Analysis & Regression Engine | ⭐ 58 | 2026-08 | MIT | Adopsi | Meta-analisis Python (DerSimonian–Laird, REML) dengan Q/I²/τ² → validasi silang/pengganti `cochran_q`, `i_squared`, `tau_squared` → `core/gap_detection/adjudication.py` |
| [wviechtb/metafor](https://github.com/wviechtb/metafor) | Repo | A meta-analysis package for R | ⭐ 310 | 2026-09 | — | Rujukan | Referensi emas meta-analisis (R) → memverifikasi τ²/I² → `core/gap_detection/adjudication.py` |
| [htlin222/meta-pipe](https://github.com/htlin222/meta-pipe) | Repo | Claude Code-powered end-to-end meta-analysis automation: AI-assisted literature review, screening, extraction,… | ⭐ 125 | 2026-09 | lainnya | Rujukan | Meta-analisis otomatis end-to-end dengan LLM → rujukan ekstraksi effect size → `core/gap_detection/claim_normalization.py` |
| [guido-s/meta](https://github.com/guido-s/meta) | Repo | Official Git repository of R package meta | ⭐ 105 | 2026-09 | GPL-2.0 | Rujukan | Paket meta-analisis R → rujukan → `core/gap_detection/adjudication.py` |

### Tema K — Evaluasi, agreement, LLM-as-judge & anotasi

Modul terkait: `experiments/expert_eval/`, `error_taxonomy.py`, `cross_critic.py`, `evaluate_gaps.py`

| Item | Tipe | Isi | ⭐ | Aktivitas | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|---|
| [HumanSignal/label-studio](https://github.com/HumanSignal/label-studio) | Repo | Label Studio is a multi-type data labeling and annotation tool with standardized output format | ⭐ 28.268 | 2026-09 | Apache-2.0 | Adopsi | Alat anotasi multi-format → anotasi ahli → `experiments/expert_eval/` |
| [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | Repo | Test your prompts, agents, and RAGs. Red teaming/pentesting/vulnerability scanning for AI. Compare performance… | ⭐ 25.148 | 2026-09 | MIT | Adopsi | Pengujian prompt & LLM-as-judge (YAML) → regresi prompt gap mining → `core/gap_mining/extractor.py` |
| [confident-ai/deepeval](https://github.com/confident-ai/deepeval) | Repo | The LLM Evaluation Framework | ⭐ 18.283 | 2026-09 | Apache-2.0 | Adopsi | Framework evaluasi LLM (G-Eval, hallucination; pytest-style) → kerangka LLM-as-judge → `experiments/cross_critic.py` |
| [vibrantlabsai/ragas](https://github.com/vibrantlabsai/ragas) | Repo | Supercharge Your LLM Application Evaluations 🚀 | ⭐ 15.743 | 2026-02 | Apache-2.0 | Adopsi | Evaluasi RAG (faithfulness, context precision/recall) → menilai `rag_tool` & grounding kutipan → `experiments/evaluate_retrieval.py` |
| [vibrantlabsai/ragas](https://github.com/vibrantlabsai/ragas) | Repo | Supercharge Your LLM Application Evaluations 🚀 | ⭐ 15.743 | 2026-02 | Apache-2.0 | Adopsi | Evaluasi RAG (faithfulness, context precision/recall) → menilai `rag_tool` & grounding kutipan → `experiments/evaluate_retrieval.py` |
| [nltk/nltk](https://github.com/nltk/nltk) | Repo | NLTK Source | ⭐ 14.716 | 2026-09 | Apache-2.0 | Adopsi | `nltk.metrics.agreement` (κ, α, π) → validasi silang agreement → `experiments/expert_eval/compute_metrics.py` |
| [doccano/doccano](https://github.com/doccano/doccano) | Repo | Open source annotation tool for machine learning practitioners. | ⭐ 10.768 | 2026-04 | MIT | Adopsi | Alat anotasi teks → gold set & taksonomi error oleh penilai ahli → `experiments/expert_eval/` |
| [argilla-io/argilla](https://github.com/argilla-io/argilla) | Repo | Argilla is a collaboration tool for AI engineers and domain experts to build high-quality datasets | ⭐ 5.109 | 2026-09 | Apache-2.0 | Adopsi | Anotasi & feedback untuk data LLM → anotasi ahli → `experiments/expert_eval/` |
| [raphaelvallat/pingouin](https://github.com/raphaelvallat/pingouin) | Repo | Statistical package in Python based on Pandas | ⭐ 1.930 | 2026-09 | GPL-3.0 | Adopsi | Effect size, ICC, κ, power → statistik ringkas → `experiments/stats_utils.py` |
| [bashtage/arch](https://github.com/bashtage/arch) | Repo | ARCH models in Python | ⭐ 1.567 | 2026-09 | lainnya | Adopsi | Bootstrap (IID, stationary) → pengganti `bootstrap_ci_diff` → `experiments/stats_utils.py` |
| [prometheus-eval/prometheus-eval](https://github.com/prometheus-eval/prometheus-eval) | Repo | Evaluate your LLM's response with Prometheus and GPT4 💯 | ⭐ 1.116 | 2025-04 | Apache-2.0 | Adopsi | Model judge terbuka (Prometheus 2) → judge lokal via Ollama, mengurangi bias judge komersial → `experiments/cross_critic.py` |
| [davidjurgens/potato](https://github.com/davidjurgens/potato) | Repo | potato: the portable annotation tool | ⭐ 422 | 2026-09 | GPL-3.0 | Adopsi | Alat anotasi ringan (YAML) → survei penilai ahli → `experiments/expert_eval/` |
| [maximtrp/scikit-posthocs](https://github.com/maximtrp/scikit-posthocs) | Repo | Multiple Pairwise Comparisons (Post Hoc) Tests in Python | ⭐ 388 | 2026-09 | MIT | Adopsi | Uji post-hoc & koreksi multipel → pelengkap `holm_bonferroni` → `experiments/stats_utils.py` |
| [pln-fing-udelar/fast-krippendorff](https://github.com/pln-fing-udelar/fast-krippendorff) | Repo | Fast computation of Krippendorff's alpha agreement measure in Python. | ⭐ 161 | 2026-08 | GPL-3.0 | Adopsi | Krippendorff α (nominal/ordinal/interval, >2 penilai) → melengkapi `cohens_kappa` buatan sendiri → `experiments/expert_eval/compute_metrics.py` |
| [ai-evals-course/judgy](https://github.com/ai-evals-course/judgy) | Repo | Python package for estimating a CIs for metrics evaluated by LLM-as-Judges. | ⭐ 97 | 2025-05 | MIT | Adopsi | CI untuk metrik dari LLM-judge dengan koreksi bias (TPR/TNR) → melaporkan hasil judge dengan interval kepercayaan → `experiments/error_taxonomy.py` |
| [openai/evals](https://github.com/openai/evals) | Repo | Evals is a framework for evaluating LLMs and LLM systems, and an open-source registry of benchmarks. | ⭐ 19.463 | 2026-04 | lainnya | Rujukan | Kerangka eval OpenAI → rujukan → `experiments/` |
| [EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) | Repo | A framework for few-shot evaluation of language models. | ⭐ 13.995 | 2026-09 | MIT | Rujukan | Harness evaluasi LM standar → `experiments/` |
| [truera/trulens](https://github.com/truera/trulens) | Repo | Evaluation and Tracking for LLM Experiments and AI Agents | ⭐ 3.553 | 2026-09 | MIT | Rujukan | Feedback function & observabilitas aplikasi LLM → `experiments/cross_critic.py` |
| [modelscope/evalscope](https://github.com/modelscope/evalscope) | Repo | A streamlined and customizable framework for efficient large model (LLM, VLM, AIGC) evaluation and performance… | ⭐ 3.428 | 2026-09 | Apache-2.0 | Rujukan | Framework evaluasi model → rujukan → `experiments/` |
| [UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai) | Repo | Inspect: A framework for large language model evaluations | ⭐ 2.780 | 2026-09 | MIT | Rujukan | Framework evaluasi LLM AISI (scorer model-graded) → evaluasi terstruktur → `experiments/cross_critic.py` |
| [inception-project/inception](https://github.com/inception-project/inception) | Repo | INCEpTION provides a semantic annotation platform offering intelligent annotation assistance and knowledge man… | ⭐ 714 | 2026-09 | Apache-2.0 | Rujukan | Platform anotasi semantik → rujukan → `experiments/expert_eval/` |
| [CSHaitao/Awesome-LLMs-as-Judges](https://github.com/CSHaitao/Awesome-LLMs-as-Judges) | Repo | The official repo for paper, LLMs-as-Judges: A Comprehensive Survey on LLM-based Evaluation Methods. | ⭐ 611 | 2025-07 | — | Rujukan | Survey LLM-as-judge → rujukan bias & mitigasi → `experiments/cross_critic.py` |
| [IBM/eval-assist](https://github.com/IBM/eval-assist) | Repo | EvalAssist is an open-source project that simplifies using large language models as evaluators (LLM-as-a-Judge… | ⭐ 102 | 2026-04 | Apache-2.0 | Rujukan | Kriteria evaluasi LLM-judge (Unitxt) → rujukan → `experiments/cross_critic.py` |
| [UW-Madison-Lee-Lab/LLM-judge-reporting](https://github.com/UW-Madison-Lee-Lab/LLM-judge-reporting) | Repo | A simple plug-in framework that corrects bias and computes confidence intervals in reporting LLM-as-a-judge ev… | ⭐ 82 | 2025-11 | — | Rujukan | Koreksi bias & CI laporan LLM judge → rujukan → `experiments/cross_critic.py` |

### Tema L — Korpus & benchmark NLP ilmiah

Modul terkait: `experiments/build_gap_benchmark.py`, `download_papers.py`

| Item | Tipe | Isi | ⭐ | Aktivitas | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|---|
| [allenai/s2orc](https://github.com/allenai/s2orc) | Dataset | S2ORC: The Semantic Scholar Open Research Corpus:  https://www.aclweb.org/anthology/2020.acl-main.447/ | ⭐ 1.087 | 2024-04 | — | Dataset evaluasi | S2ORC: 81M paper teks-penuh terstruktur → korpus skala besar → `experiments/build_gap_benchmark.py` |
| [allenai/scitldr](https://github.com/allenai/scitldr) | Dataset | — | ⭐ 761 | 2023-05 | Apache-2.0 | Dataset evaluasi | SciTLDR: ringkasan ekstrem paper → rujukan → `core/gap_mining/extractor.py` |
| [allenai/PeerRead](https://github.com/allenai/PeerRead) | Dataset | Data and code for Kang et al., NAACL 2018's paper titled "A Dataset of Peer Reviews (PeerRead): Collection, In… | ⭐ 432 | 2025-12 | — | Dataset evaluasi | PeerRead: review & keputusan paper → melatih penilai kualitas/kebaruan → `core/recommendation/novelty.py` |
| [IllDepence/unarXive](https://github.com/IllDepence/unarXive) | Dataset | A data set based on all arXiv publications, pre-processed for NLP, including structured full-text and citation… | ⭐ 302 | 2024-09 | MIT | Dataset evaluasi | unarXive: 1,9M paper arXiv teks-penuh dengan konteks sitasi & label seksi IMRaD → `core/pipeline/section_normalizer.py` |
| [shauryr/ACL-anthology-corpus](https://github.com/shauryr/ACL-anthology-corpus) | Dataset | This repository provides details and links to the ACL anthology corpus/collection including .bib, .pdf and gro… | ⭐ 192 | 2023-10 | — | Dataset evaluasi | Korpus teks penuh ACL Anthology → korpus uji domain NLP → `experiments/build_gap_benchmark.py` |
| [allenai/scidocs](https://github.com/allenai/scidocs) | Benchmark | Dataset accompanying the SPECTER model | ⭐ 148 | 2022-12 | lainnya | Dataset evaluasi | SciDocs benchmark embedding dokumen ilmiah → `core/retrieval/` |
| [allenai/scirepeval](https://github.com/allenai/scirepeval) | Benchmark | SciRepEval benchmark training and evaluation scripts | ⭐ 91 | 2026-05 | Apache-2.0 | Dataset evaluasi | SciRepEval: 25 tugas representasi dokumen ilmiah → memilih embedder → `core/retrieval/` |
| [allenai/ms2](https://github.com/allenai/ms2) | Dataset | — | ⭐ 69 | 2022-10 | Apache-2.0 | Dataset evaluasi | MS²: ringkasan multi-dokumen studi medis → gold sintesis lintas-studi → `core/gap_detection/support_gap.py` |
| [yaolu/Multi-XScience](https://github.com/yaolu/Multi-XScience) | Dataset | Multi-XScience: A Large-scale Dataset for Extreme Multi-document Summarization of Scientific Articles | ⭐ 50 | 2024-06 | MIT | Dataset evaluasi | Multi-XScience: related-work multi-dokumen → evaluasi sintesis lintas-jurnal → `core/recommendation/themes.py` |
| [ai4s-research/awesome-ai-for-science](https://github.com/ai4s-research/awesome-ai-for-science) | Repo | A curated list of awesome AI tools, libraries, papers, datasets, and frameworks that accelerate scientific dis… | ⭐ 1.962 | 2026-09 | MIT | Rujukan | Kurasi AI for Science → rujukan → `experiments/` |
| [InternScience/Awesome-Scientific-Datasets-and-LLMs](https://github.com/InternScience/Awesome-Scientific-Datasets-and-LLMs) | Repo | A curated collection of papers, datasets, and resources on Scientific Datasets and Large Language Models (LLMs… | ⭐ 461 | 2025-10 | MIT | Rujukan | Kurasi dataset ilmiah & LLM → rujukan → `experiments/` |

**Model/dataset Hugging Face (tema L):**

| Item | Tipe | ♥ / ⬇ | Modifikasi | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|
| [allenai/peS2o](https://huggingface.co/datasets/allenai/peS2o) <sub>HF dataset</sub> | Dataset | ♥ 205 · ⬇ 20.969 | 2024-10 | odc-by | Dataset evaluasi | peS2o: 40M paper bersih dari S2ORC → korpus latih → `experiments/build_gap_benchmark.py` |
| [allenai/qasper](https://huggingface.co/datasets/allenai/qasper) <sub>HF dataset</sub> | Dataset | ♥ 114 · ⬇ 6.717 | 2022-10 | cc-by-4.0 | Dataset evaluasi | QASPER: QA atas paper NLP dengan bukti → evaluasi RAG level paper → `experiments/evaluate_retrieval.py` |
| [allenai/scirepeval](https://huggingface.co/datasets/allenai/scirepeval) <sub>HF dataset</sub> | Benchmark | ♥ 21 · ⬇ 6.621 | 2024-01 | — | Dataset evaluasi | SciRepEval versi HF → `core/retrieval/` |
| [allenai/peer_read](https://huggingface.co/datasets/allenai/peer_read) <sub>HF dataset</sub> | Dataset | ♥ 12 · ⬇ 470 | 2022-11 | — | Dataset evaluasi | PeerRead versi HF → `core/recommendation/novelty.py` |
| [saier/unarXive_citrec](https://huggingface.co/datasets/saier/unarXive_citrec) <sub>HF dataset</sub> | Dataset | ♥ 9 · ⬇ 206 | 2023-04 | cc-by-sa-4.0 | Dataset evaluasi | Rekomendasi sitasi dari unarXive → uji konteks sitasi → `core/gap_detection/citation_coupling.py` |

### Tema M — Metrik graf, komunitas & topik

Modul terkait: `core/gap_detection/graph_metrics.py`, `core/recommendation/themes.py`

| Item | Tipe | Isi | ⭐ | Aktivitas | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|---|
| [networkx/networkx](https://github.com/networkx/networkx) | Repo | Network Analysis in Python | ⭐ 17.259 | 2026-09 | lainnya | Adopsi | Sudah dipakai; `community.louvain_communities`, `modularity` bawaan → `core/gap_detection/graph_metrics.py` |
| [MaartenGr/BERTopic](https://github.com/MaartenGr/BERTopic) | Repo | Leveraging BERT and c-TF-IDF to create easily interpretable topics. | ⭐ 7.835 | 2026-09 | MIT | Adopsi | Topic modeling berbasis embedding (c-TF-IDF, hierarchical) → tema lintas-jurnal & label klaster fragmentasi → `core/recommendation/themes.py` |
| [igraph/python-igraph](https://github.com/igraph/python-igraph) | Repo | Python interface for igraph | ⭐ 1.462 | 2026-05 | GPL-2.0 | Adopsi | Lebih cepat untuk graf besar; Leiden/Infomap bawaan → `core/gap_detection/graph_metrics.py` |
| [vtraag/leidenalg](https://github.com/vtraag/leidenalg) | Repo | Implementation of the Leiden algorithm for various quality functions to be used with igraph in Python. | ⭐ 798 | 2026-09 | GPL-3.0 | Adopsi | Leiden (kualitas > Louvain) → klaster fragmentasi lebih stabil → `core/gap_detection/graph_metrics.py` |
| [GiulioRossetti/cdlib](https://github.com/GiulioRossetti/cdlib) | Repo | Community Discovery Library | ⭐ 429 | 2026-08 | BSD-2-Clause | Adopsi | Deteksi komunitas + evaluasi (modularity, NMI) → membandingkan algoritma pada graf fragmentasi → `core/gap_detection/graph_metrics.py` |
| [ddangelov/Top2Vec](https://github.com/ddangelov/Top2Vec) | Repo | Top2Vec learns jointly embedded topic, document and word vectors. | ⭐ 3.108 | 2024-11 | BSD-3-Clause | Rujukan | Topic modeling embedding → alternatif → `core/recommendation/themes.py` |
| [JasonKessler/scattertext](https://github.com/JasonKessler/scattertext) | Repo | Beautiful visualizations of how language differs among document types. | ⭐ 2.343 | 2026-07 | Apache-2.0 | Rujukan | Visualisasi perbedaan term antar-korpus → rujukan → `core/recommendation/themes.py` |
| [graspologic-org/graspologic](https://github.com/graspologic-org/graspologic) | Repo | Python package for graph statistics | ⭐ 1.010 | 2026-06 | MIT | Rujukan | Statistik graf (embedding, clustering) → rujukan → `core/gap_detection/graph_metrics.py` |
| [networkit/networkit](https://github.com/networkit/networkit) | Repo | NetworKit is a growing open-source toolkit for large-scale network analysis. | ⭐ 874 | 2026-09 | MIT | Rujukan | Analisis jaringan skala besar → rujukan → `core/gap_detection/graph_metrics.py` |

### Tema R — Retrieval & reranking multibahasa

Modul terkait: `core/retrieval/` (bi-encoder + cross-encoder reranker)

**Model/dataset Hugging Face (tema R):**

| Item | Tipe | ♥ / ⬇ | Modifikasi | Lisensi | Kategori | Manfaat untuk Wizard Research → modul |
|---|---|---|---|---|---|---|
| [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) <sub>HF model</sub> | Model | ♥ 3.561 · ⬇ 37.775.082 | 2024-07 | mit | Adopsi | Embedding multibahasa dense+sparse (8192 token) → pengganti `paraphrase-multilingual-MiniLM-L12-v2` → `core/retrieval/` |
| [intfloat/multilingual-e5-large](https://huggingface.co/intfloat/multilingual-e5-large) <sub>HF model</sub> | Model | ♥ 1.249 · ⬇ 6.897.865 | 2026-04 | mit | Adopsi | Embedding multibahasa E5 → alternatif → `core/retrieval/` |
| [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) <sub>HF model</sub> | Model | ♥ 1.196 · ⬇ 17.999.495 | 2024-06 | apache-2.0 | Adopsi | Reranker multibahasa kuat → pengganti `cross-encoder/ms-marco-MiniLM-L-6-v2` (Inggris) untuk jurnal Indonesia → `core/retrieval/` |
| [Alibaba-NLP/gte-multilingual-reranker-base](https://huggingface.co/Alibaba-NLP/gte-multilingual-reranker-base) <sub>HF model</sub> | Model | ♥ 190 · ⬇ 246.563 | 2025-07 | apache-2.0 | Adopsi | Reranker multibahasa Apache-2.0 → alternatif berlisensi permisif → `core/retrieval/` |
| [sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2) <sub>HF model</sub> | Model | ♥ 1.402 · ⬇ 45.507.894 | 2026-01 | apache-2.0 | Baseline | Embedder yang dipakai saat ini → baseline pembanding → `core/retrieval/` |
| [cross-encoder/ms-marco-MiniLM-L-6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2) <sub>HF model</sub> | Model | ♥ 340 · ⬇ 87.870.858 | 2026-08 | apache-2.0 | Baseline | Reranker yang dipakai saat ini → baseline pembanding → `core/retrieval/` |
| [jinaai/jina-reranker-v2-base-multilingual](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual) <sub>HF model</sub> | Model | ♥ 355 · ⬇ 1.079.850 | 2025-10 | cc-by-nc-4.0 | Rujukan | Reranker multibahasa alternatif (lisensi CC-BY-NC — non-komersial) → `core/retrieval/` |

## 5. Paper arXiv dengan Repo Terkait

| arXiv | Judul | Repo terkait | Relevansi |
|---|---|---|---|
| [2409.04109](https://arxiv.org/abs/2409.04109) | Can LLMs Generate Novel Research Ideas? A Large-Scale Human Study with 100+ NLP Researchers | [NoviScl/AI-Researcher](https://github.com/NoviScl/AI-Researcher) | Studi kebaruan ide LLM vs peneliti (A) |
| [2507.02694](https://arxiv.org/abs/2507.02694) | Can LLMs Identify Critical Limitations within Scientific Research? A Systematic Evaluation on AI Research Papers | [yale-nlp/LimitGen](https://github.com/yale-nlp/LimitGen) | Benchmark identifikasi limitation (A) |
| [2503.16561](https://arxiv.org/abs/2503.16561) | FutureGen: A RAG-based Approach to Generate the Future Work of Scientific Article | [IbrahimAlAzhar/FutureWorkGeneration](https://github.com/IbrahimAlAzhar/FutureWorkGeneration) | FutureGen: generasi future work RAG — kode resmi (A) |
| [2408.06292](https://arxiv.org/abs/2408.06292) | The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery | [SakanaAI/AI-Scientist](https://github.com/SakanaAI/AI-Scientist) | Riset otomatis end-to-end (G) |
| [2501.04227](https://arxiv.org/abs/2501.04227) | Agent Laboratory: Using LLM Agents as Research Assistants | [SamuelSchmidgall/AgentLaboratory](https://github.com/SamuelSchmidgall/AgentLaboratory) | Agen asisten riset (G) |
| [2409.13740](https://arxiv.org/abs/2409.13740) | Language agents achieve superhuman synthesis of scientific knowledge | [Future-House/paper-qa](https://github.com/Future-House/paper-qa) | PaperQA2 — baseline sintesis literatur (G) |
| [2402.14207](https://arxiv.org/abs/2402.14207) | Assisting in Writing Wikipedia-like Articles From Scratch with Large Language Models | [stanford-oval/storm](https://github.com/stanford-oval/storm) | STORM (G) |
| [2411.14199](https://arxiv.org/abs/2411.14199) | OpenScholar: Synthesizing Scientific Literature with Retrieval-augmented LMs | [AkariAsai/OpenScholar](https://github.com/AkariAsai/OpenScholar) | OpenScholar (G) |
| [2404.16130](https://arxiv.org/abs/2404.16130) | From Local to Global: A Graph RAG Approach to Query-Focused Summarization | [microsoft/graphrag](https://github.com/microsoft/graphrag) | GraphRAG (F) |
| [2410.05779](https://arxiv.org/abs/2410.05779) | LightRAG: Simple and Fast Retrieval-Augmented Generation | [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) | LightRAG (F) |
| [1909.03546](https://arxiv.org/abs/1909.03546) | Entity, Relation, and Event Extraction with Contextualized Span Representations | [dwadden/dygiepp](https://github.com/dwadden/dygiepp) | DyGIE++ (F) |
| [2004.07180](https://arxiv.org/abs/2004.07180) | SPECTER: Document-level Representation Learning using Citation-informed Transformers | [allenai/specter](https://github.com/allenai/specter) | SPECTER (F) |
| [2202.06671](https://arxiv.org/abs/2202.06671) | Neighborhood Contrastive Learning for Scientific Document Representations with Citation Embeddings | [malteos/scincl](https://github.com/malteos/scincl) | SciNCL (F) |
| [2004.14974](https://arxiv.org/abs/2004.14974) | Fact or Fiction: Verifying Scientific Claims | [allenai/scifact](https://github.com/allenai/scifact) | SciFact (B) |
| [2203.06728](https://arxiv.org/abs/2203.06728) | SciNLI: A Corpus for Natural Language Inference on Scientific Text | [msadat3/SciNLI](https://github.com/msadat3/SciNLI) | SciNLI (B) |
| [2112.01640](https://arxiv.org/abs/2112.01640) | MultiVerS: Improving scientific claim verification with weak supervision and full-document context | [dwadden/multivers](https://github.com/dwadden/multivers) | MultiVerS (B) |
| [2305.12295](https://arxiv.org/abs/2305.12295) | Logic-LM: Empowering Large Language Models with Symbolic Solvers for Faithful Logical Reasoning | [teacherpeterpan/Logic-LLM](https://github.com/teacherpeterpan/Logic-LLM) | Logic-LM (H) |
| [2303.08896](https://arxiv.org/abs/2303.08896) | SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models | [potsawee/selfcheckgpt](https://github.com/potsawee/selfcheckgpt) | SelfCheckGPT (I) |
| [2302.09664](https://arxiv.org/abs/2302.09664) | Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation | [lorenzkuhn/semantic_uncertainty](https://github.com/lorenzkuhn/semantic_uncertainty) | Semantic uncertainty (I) |

## 6. Temuan Agen Pelengkap (celah yang belum tercakup)

Setelah jalur seed + API, satu agen riset ditugaskan mencari **hanya** item yang belum ada, untuk tujuh celah. Semua 62 usulannya diverifikasi ulang secara independen lewat GitHub Search API / HF API (62/62 ada) dan sudah dilebur ke tabel tema di atas. Temuan yang paling bernilai:

| Celah | Temuan kunci | Catatan |
|---|---|---|
| 1. Future work / limitation | **`IbrahimAlAzhar/FutureWorkGeneration`** = kode resmi FutureGen (arXiv 2503.16561; ⭐ 0 tetapi dikonfirmasi lewat README & notebook); 3 dataset HF limitasi (ACL 2023, NeurIPS 2021–22 + sitasi); MASSW 152k paper | Melengkapi LimitGen; prompt penyaring & rubrik judge dapat diadaptasi |
| 2. Kontradiksi antar-dokumen | ContraSciView (`sandeep82945/Contradiction-in-Peer-Review`), ContraDoc, `dnsosa/covid_lit_contra_claims` (klaim kontradiktif antar-paper), SciFact-Open, RAMDocs, `statcheck` | Belum ada repo khusus klasifikasi **arah efek** pada abstrak selain statcheck (berbasis angka) |
| 3. Zoning seksi/argumentatif | ArguminSci, MuLMS-AZ, CODA-19, SSC lintas-domain (Brack), SciWING | Alternatif untuk memetakan IMRaD/AZ sebelum ekstraksi klaim |
| 4. Citation intent | SciCite, MultiCite, ACL-ARC `citation-function` (fungsi *CompareOrContrast*), CiteWorth | Membobot kopling bibliografis; klaim tak bersitasi = sinyal *incompleteness* |
| 5. Evidence gap map / lanskap | `mb7419/egm` (Python, Plotly), EviAtlas, **pySciSci**, novelpy, Open Knowledge Maps | `egm` bisa langsung dipakai untuk render EGM |
| 6. Neuro-symbolic verifikasi klaim | FOLK (FOL + LLM), LOREN, GraphCheck (KG → fact-check), Loki | Belum ada repo neuro-symbolic **khusus klaim ilmiah** 2024–2026 — mendukung klaim kebaruan tesis |
| 7. Benchmark agen riset | ScienceAgentBench, MLR-Bench, AAAR-1.0 (tugas *paper weakness*), PaperBench (`openai/frontier-evals`), LAB-Bench | Rujukan protokol evaluasi & rubrik |

Usulan agen yang **tidak** dapat diverifikasi (tidak dipakai): `voidful/IdeaBench` (404), `Fengrru/scientific-contradiction-detector` (404), repo GitHub untuk *AI-Idea-Bench-2025*, *Nova*, *SciCon/EvoNLI*, *WikiContradict*, *ManConCorpus*.

## Lampiran A — Ada, tetapi di bawah saringan

Repo berikut terverifikasi ada namun tidak memenuhi ⭐ ≥ 50 / aktivitas ≤ 2 tahun / non-archived. Tetap dicatat karena relevan sebagai rujukan atau baseline historis.

| Repo | ⭐ | Aktivitas | Alasan | Tetap relevan sebagai |
|---|---|---|---|---|
| [EagleW/Scientific-Inspiration-Machines-Optimized-for-Novelty](https://github.com/EagleW/Scientific-Inspiration-Machines-Optimized-for-Novelty) | 98 | 2024-04 | push terakhir 2024-04 (> 2 tahun) | Rujukan (tema A): SciMON: generasi ide berbasis literatur dengan optimasi kebaruan iteratif → rujukan loop "cek kebaruan → revisi" |
| [IbrahimAlAzhar/FutureWorkGeneration](https://github.com/IbrahimAlAzhar/FutureWorkGeneration) | 0 | 2025-08 | ⭐ 0 < 50 | Rujukan (tema A): Kode resmi **FutureGen** (arXiv 2503.16561): prompt penyaring kalimat *future work* + rubrik LLM-judge 1–5 → adaptasi langsung ke seleksi kandidat & evaluasi gap mining |
| [allenai/sequential_sentence_classification](https://github.com/allenai/sequential_sentence_classification) | 77 | 2022-11 | push terakhir 2022-11 (> 2 tahun) | Baseline (tema B): CSAbstruct + model klasifikasi kalimat sekuensial (SciBERT) → baseline peran kalimat abstrak |
| [dwadden/multivers](https://github.com/dwadden/multivers) | 54 | 2023-08 | push terakhir 2023-08 (> 2 tahun) | Baseline (tema B): MultiVerS: claim verification dokumen-penuh (LongFormer) dengan checkpoint → baseline NLI dokumen-penuh |
| [xiongsiheng/DeepVerify](https://github.com/xiongsiheng/DeepVerify) | 38 | 2026-07 | ⭐ 38 < 50 | Rujukan (tema B): Verifikasi klaim ilmiah berbasis bukti level pakar (2026) → rujukan alur verifikasi agentic |
| [dnsosa/covid_lit_contra_claims](https://github.com/dnsosa/covid_lit_contra_claims) | 2 | 2023-01 | ⭐ 2 < 50; push terakhir 2023-01 (> 2 tahun) | Rujukan (tema B): Deteksi klaim efikasi obat yang **kontradiktif antar-paper** (NLI + adaptasi domain, ManConCorpus) → paling dekat dengan indikator *inconsistency* |
| [MattiaToffolo/Scientific-Contradiction-Detector](https://github.com/MattiaToffolo/Scientific-Contradiction-Detector) | 1 | 2026-08 | ⭐ 1 < 50 | Rujukan (tema B): Proyek kecil klaim biomedis → laporan bukti mendukung/bertentangan → contoh end-to-end sederhana |
| [ijmarshall/robotreviewer](https://github.com/ijmarshall/robotreviewer) | 177 | 2022-07 | push terakhir 2022-07 (> 2 tahun) | Rujukan (tema C): RobotReviewer: ekstraksi PICO & risk-of-bias otomatis dari RCT → rujukan klasik ekstraksi PICO |
| [Kwirtz/novelpy](https://github.com/Kwirtz/novelpy) | 37 | 2024-06 | ⭐ 37 < 50; push terakhir 2024-06 (> 2 tahun) | Adopsi (tema C): novelpy: indikator kebaruan kombinatorial (Uzzi, Lee, Foster, Wang) → pelengkap cek kebaruan OpenAlex |
| [mjwestgate/synthesisr](https://github.com/mjwestgate/synthesisr) | 35 | 2026-03 | ⭐ 35 < 50 | Rujukan (tema C): Impor & dedup hasil pencarian bibliografis (R) → rujukan aturan dedup judul/DOI |
| [ESHackathon/eviatlas](https://github.com/ESHackathon/eviatlas) | 32 | 2025-02 | ⭐ 32 < 50 | Rujukan (tema C): EviAtlas (R Shiny): visualisasi peta sistematis/evidence map → rujukan format keluaran Evidence Gap Map |
| [evidencesynthesis-tools/awesome-evidence-synthesis](https://github.com/evidencesynthesis-tools/awesome-evidence-synthesis) | 27 | 2026-08 | ⭐ 27 < 50 | Rujukan (tema C): Kurasi alat evidence synthesis → rujukan |
| [ijmarshall/robotsearch](https://github.com/ijmarshall/robotsearch) | 23 | 2023-03 | ⭐ 23 < 50; push terakhir 2023-03 (> 2 tahun) | Rujukan (tema C): Classifier RCT vs non-RCT → rujukan filter desain studi |
| [ijmarshall/trialstreamer](https://github.com/ijmarshall/trialstreamer) | 23 | 2022-06 | ⭐ 23 < 50; push terakhir 2022-06 (> 2 tahun) | Rujukan (tema C): Basis data RCT terstruktur otomatis (PICO) → rujukan skema sel Evidence Gap Map |
| [mb7419/egm](https://github.com/mb7419/egm) | 5 | 2020-04 | ⭐ 5 < 50; push terakhir 2020-04 (> 2 tahun) | Adopsi (tema C): Paket Python untuk memplot Evidence Gap Map (Plotly) → render EGM dari matriks sumbu × sel langsung di backend |
| [mcallaghan/buscarpy](https://github.com/mcallaghan/buscarpy) | 3 | 2025-10 | ⭐ 3 < 50 | Rujukan (tema C): Stopping rules statistik untuk skrining → kriteria berhenti pencarian literatur tambahan |
| [nliulab/seeEvidenceGap](https://github.com/nliulab/seeEvidenceGap) | 1 | 2025-08 | ⭐ 1 < 50 | Rujukan (tema C): seeEvidenceGap → rujukan visualisasi celah bukti |
| [allenai/s2-folks](https://github.com/allenai/s2-folks) | 279 | 2025-01 | archived | Rujukan (tema D): Dokumentasi komunitas Semantic Scholar API (arsip) |
| [UWNETLAB/metaknowledge](https://github.com/UWNETLAB/metaknowledge) | 182 | 2022-06 | push terakhir 2022-06 (> 2 tahun) | Rujukan (tema D): Bibliometrik & jaringan sitasi Python (WoS/Scopus) → rujukan metrik kopling |
| [ourresearch/openalex-api-tutorials](https://github.com/ourresearch/openalex-api-tutorials) | 147 | 2024-04 | push terakhir 2024-04 (> 2 tahun) | Rujukan (tema D): Notebook resmi OpenAlex → contoh kueri sitasi/konsep |
| [diging/tethne](https://github.com/diging/tethne) | 88 | 2020-10 | push terakhir 2020-10 (> 2 tahun) | Rujukan (tema D): Analisis jaringan bibliografis (co-citation, coupling) → rujukan |
| [davidjurgens/citation-function](https://github.com/davidjurgens/citation-function) | 64 | 2018-10 | push terakhir 2018-10 (> 2 tahun) | Rujukan (tema D): ACL-ARC: 6 fungsi sitasi termasuk *CompareOrContrast* → sinyal langsung kontradiksi/fragmentasi antar-paper |
| [AvishekLahiri/CitePrompt](https://github.com/AvishekLahiri/CitePrompt) | 9 | 2023-04 | ⭐ 9 < 50; push terakhir 2023-04 (> 2 tahun) | Rujukan (tema D): Intent sitasi berbasis prompt (JCDL 2023) → intent via LLM |
| [Layout-Parser/layout-parser](https://github.com/Layout-Parser/layout-parser) | 5.779 | 2024-08 | push terakhir 2024-08 (> 2 tahun) | Rujukan (tema E): Deteksi layout dokumen berbasis deep learning (Detectron2) → rujukan |
| [allenai/pdffigures2](https://github.com/allenai/pdffigures2) | 759 | 2024-03 | push terakhir 2024-03 (> 2 tahun) | Rujukan (tema E): Ekstraksi gambar/tabel + caption dari PDF ilmiah |
| [allenai/science-parse](https://github.com/allenai/science-parse) | 706 | 2024-05 | push terakhir 2024-05 (> 2 tahun) | Rujukan (tema E): Parser PDF ilmiah klasik (judul, penulis, seksi, referensi) → pembanding |
| [CeON/CERMINE](https://github.com/CeON/CERMINE) | 512 | 2022-06 | push terakhir 2022-06 (> 2 tahun) | Rujukan (tema E): Ekstraksi metadata & referensi PDF (Java) → pembanding |
| [allenai/s2orc-doc2json](https://github.com/allenai/s2orc-doc2json) | 476 | 2024-04 | push terakhir 2024-04 (> 2 tahun) | Rujukan (tema E): Konversi GROBID TEI → JSON S2ORC → rujukan skema seksi/paragraf/sitasi |
| [titipata/scipdf_parser](https://github.com/titipata/scipdf_parser) | 456 | 2024-03 | push terakhir 2024-03 (> 2 tahun) | Rujukan (tema E): Wrapper GROBID → dict Python (seksi, referensi, gambar) |
| [WING-NUS/Neural-ParsCit](https://github.com/WING-NUS/Neural-ParsCit) | 81 | 2022-05 | push terakhir 2022-05 (> 2 tahun) | Rujukan (tema E): Parsing string sitasi BiLSTM-CRF → rujukan |
| [abhinavkashyap/sciwing](https://github.com/abhinavkashyap/sciwing) | 63 | 2023-05 | push terakhir 2023-05 (> 2 tahun) | Rujukan (tema E): SciWING: toolkit dokumen ilmiah (klasifikasi section header/logical structure, citation intent) → satu toolkit untuk normalisasi heading IMRaD |
| [jind11/HSLN-Joint-Sentence-Classification](https://github.com/jind11/HSLN-Joint-Sentence-Classification) | 34 | 2018-09 | ⭐ 34 < 50; push terakhir 2018-09 (> 2 tahun) | Rujukan (tema E): HSLN: klasifikasi kalimat berurutan (baseline klasik) |
| [anlausch/ArguminSci](https://github.com/anlausch/ArguminSci) | 20 | 2022-11 | ⭐ 20 < 50; push terakhir 2022-11 (> 2 tahun) | Rujukan (tema E): ArguminSci: argumentative zoning, discourse role, citation context → memisahkan klaim/temuan dari latar |
| [arthurbrack/sequential-sentence-classification](https://github.com/arthurbrack/sequential-sentence-classification) | 13 | 2022-06 | ⭐ 13 < 50; push terakhir 2022-06 (> 2 tahun) | Baseline (tema E): SSC lintas-domain multi-task (PubMed-RCT, CSAbstruct, Dr. Inventor) → zoning kalimat sebelum ekstraksi klaim |
| [CSU-NLP-Group/Sequential-Sentence-Classification](https://github.com/CSU-NLP-Group/Sequential-Sentence-Classification) | 1 | 2022-11 | ⭐ 1 < 50; push terakhir 2022-11 (> 2 tahun) | Rujukan (tema E): SSC alternatif → rujukan |
| [allenai/scibert](https://github.com/allenai/scibert) | 1.715 | 2022-02 | push terakhir 2022-02 (> 2 tahun) | Rujukan (tema F): Kode SciBERT & data fine-tuning (NER, RE, PICO) |
| [princeton-nlp/PURE](https://github.com/princeton-nlp/PURE) | 815 | 2022-07 | push terakhir 2022-07 (> 2 tahun) | Baseline (tema F): PURE: pipeline entitas → relasi sederhana & kuat → baseline |
| [allenai/specter](https://github.com/allenai/specter) | 593 | 2023-06 | push terakhir 2023-06 (> 2 tahun) | Rujukan (tema F): SPECTER v1 (kode & SciDocs) |
| [Babelscape/rebel](https://github.com/Babelscape/rebel) | 576 | 2023-11 | push terakhir 2023-11 (> 2 tahun) | Baseline (tema F): REBEL: seq2seq ekstraksi triple end-to-end → baseline |
| [thunlp/PL-Marker](https://github.com/thunlp/PL-Marker) | 274 | 2023-05 | push terakhir 2023-05 (> 2 tahun) | Baseline (tema F): PL-Marker: SOTA NER+RE SciERC → baseline |
| [cenguix/Text2KGBench](https://github.com/cenguix/Text2KGBench) | 92 | 2024-05 | push terakhir 2024-05 (> 2 tahun) | Dataset evaluasi (tema F): Benchmark ekstraksi KG berbasis ontologi (presisi/recall triple) → mengevaluasi ekstraktor fakta |
| [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) | 12.680 | 2026-08 | archived | Rujukan (tema G): Deep research LangGraph (arsip) → rujukan pola supervisor-researcher |
| [venmo/business-rules](https://github.com/venmo/business-rules) | 994 | 2024-08 | push terakhir 2024-08 (> 2 tahun) | Rujukan (tema H): Business rules Python → rujukan aturan yang dapat dikonfigurasi |
| [teacherpeterpan/Logic-LLM](https://github.com/teacherpeterpan/Logic-LLM) | 411 | 2024-06 | push terakhir 2024-06 (> 2 tahun) | Rujukan (tema H): Logic-LM: LLM → formulasi simbolik → solver (Prolog/SMT) → rujukan pola LLM+solver |
| [yuxiaw/Factcheck-GPT](https://github.com/yuxiaw/Factcheck-GPT) | 117 | 2024-01 | push terakhir 2024-01 (> 2 tahun) | Rujukan (tema H): Factcheck-GPT: verifikasi faktual keluaran LLM end-to-end → rujukan self-check |
| [benlipkin/linc](https://github.com/benlipkin/linc) | 85 | 2024-01 | push terakhir 2024-01 (> 2 tahun) | Rujukan (tema H): LINC: LLM sebagai semantic parser + theorem prover → rujukan |
| [jiho283/KG-GPT](https://github.com/jiho283/KG-GPT) | 74 | 2023-10 | push terakhir 2023-10 (> 2 tahun) | Rujukan (tema H): KG-GPT: penalaran atas KG dengan LLM → rujukan |
| [mbzuai-nlp/ProgramFC](https://github.com/mbzuai-nlp/ProgramFC) | 59 | 2023-07 | push terakhir 2023-07 (> 2 tahun) | Rujukan (tema H): ProgramFC: fact-checking klaim kompleks berpanduan program → rujukan dekomposisi klaim |
| [xiye17/SAT-LM](https://github.com/xiye17/SAT-LM) | 54 | 2024-07 | push terakhir 2024-07 (> 2 tahun) | Rujukan (tema H): SatLM: LLM + SAT solver → rujukan |
| [jiangjiechen/LOREN](https://github.com/jiangjiechen/LOREN) | 48 | 2022-12 | ⭐ 48 < 50; push terakhir 2022-12 (> 2 tahun) | Rujukan (tema H): LOREN (AAAI 2022): logic-regularized reasoning untuk fact verification interpretabel → neuro-symbolic agregasi klaim |
| [wang2226/FOLK](https://github.com/wang2226/FOLK) | 28 | 2023-12 | ⭐ 28 < 50; push terakhir 2023-12 (> 2 tahun) | Rujukan (tema H): FOLK (EMNLP 2023): verifikasi klaim via predikat first-order logic + LLM → pola LLM→FOL→verifikasi selaras rule engine |
| [Yingjian-Chen/GraphCheck](https://github.com/Yingjian-Chen/GraphCheck) | 21 | 2025-05 | ⭐ 21 < 50 | Rujukan (tema H): GraphCheck (ACL 2025): fact-checking teks panjang dengan KG hasil ekstraksi → sangat selaras alur SPO→KG→verifikasi |
| [krishnamrith12/ProoFVer](https://github.com/krishnamrith12/ProoFVer) | 14 | 2022-06 | ⭐ 14 < 50; push terakhir 2022-06 (> 2 tahun) | Rujukan (tema H): ProoFVer: proof system untuk fact verification → rujukan |
| [Raldir/QA-NatVer](https://github.com/Raldir/QA-NatVer) | 1 | 2025-04 | ⭐ 1 < 50 | Rujukan (tema H): QA-NatVer: natural logic verification → rujukan |
| [potsawee/selfcheckgpt](https://github.com/potsawee/selfcheckgpt) | 630 | 2024-06 | push terakhir 2024-06 (> 2 tahun) | Rujukan (tema I): SelfCheckGPT: konsistensi antar-sampel → rujukan konsensus k/n |
| [jlko/semantic_uncertainty](https://github.com/jlko/semantic_uncertainty) | 428 | 2024-04 | push terakhir 2024-04 (> 2 tahun) | Rujukan (tema I): Semantic entropy (Nature 24) → rujukan deteksi konfabulasi |
| [lorenzkuhn/semantic_uncertainty](https://github.com/lorenzkuhn/semantic_uncertainty) | 188 | 2024-06 | push terakhir 2024-06 (> 2 tahun) | Rujukan (tema I): Semantic uncertainty (ICLR 23) → rujukan |
| [hollance/reliability-diagrams](https://github.com/hollance/reliability-diagrams) | 170 | 2022-02 | push terakhir 2022-02 (> 2 tahun) | Rujukan (tema I): Kode reliability diagram → rujukan visual |
| [zlin7/UQ-NLG](https://github.com/zlin7/UQ-NLG) | 106 | 2024-06 | push terakhir 2024-06 (> 2 tahun) | Rujukan (tema I): UQ untuk NLG black-box → rujukan |
| [dirichletcal/dirichlet_python](https://github.com/dirichletcal/dirichlet_python) | 33 | 2025-06 | ⭐ 33 < 50 | Rujukan (tema I): Kalibrasi Dirichlet multi-kelas → rujukan |
| [facebookarchive/bootstrapped](https://github.com/facebookarchive/bootstrapped) | 637 | 2019-11 | archived | Rujukan (tema K): Bootstrap CI (arsip) → rujukan |
| [facebookarchive/bootstrapped](https://github.com/facebookarchive/bootstrapped) | 637 | 2019-11 | archived | Rujukan (tema K): Bootstrap CI (arsip) → rujukan |
| [benedekrozemberczki/karateclub](https://github.com/benedekrozemberczki/karateclub) | 2.286 | 2024-07 | push terakhir 2024-07 (> 2 tahun) | Rujukan (tema M): Embedding graf & komunitas unsupervised → rujukan |
| [taynaud/python-louvain](https://github.com/taynaud/python-louvain) | 1.046 | 2024-03 | push terakhir 2024-03 (> 2 tahun) | Rujukan (tema M): Louvain klasik → rujukan |
| [MaartenGr/BERTopic_evaluation](https://github.com/MaartenGr/BERTopic_evaluation) | 85 | 2023-12 | push terakhir 2023-12 (> 2 tahun) | Rujukan (tema M): Evaluasi BERTopic → rujukan |
| [csilab-ufop/pymocd](https://github.com/csilab-ufop/pymocd) | 22 | 2026-09 | ⭐ 22 < 50 | Rujukan (tema M): Deteksi komunitas multi-objektif → rujukan |
| [CodeSoul-co/THETA](https://github.com/CodeSoul-co/THETA) | 22 | 2026-09 | ⭐ 22 < 50 | Rujukan (tema M): Topic embedding adaptif LLM (2026) → rujukan |

## Lampiran B — Tidak terverifikasi

| Id | Catatan |
|---|---|
| `TIBHannover/orkg-pypi` | tidak ada di GitHub (ORKG di GitLab / dataset di HF) |
| `allenai/qasper` | tidak ada di GitHub (ORKG di GitLab / dataset di HF) |

## Lampiran C — Reproduksi

1. **Kueri GitHub Search API** (`sort=stars`, 10 hasil/kueri, jeda 7,5 s, backoff otomatis pada 403/429):

```text
A|research gap identification scientific literature LLM
A|future work extraction scientific papers
A|limitations extraction scientific papers dataset
A|research idea generation literature LLM agent
A|novelty assessment research ideas LLM
B|scientific claim verification SciFact
B|scientific NLI contradiction detection
B|contradiction detection scientific literature
B|PICO extraction clinical trials NLP
C|systematic review automation screening machine learning
C|evidence gap map
C|living systematic review LLM
D|openalex python client
D|bibliographic coupling citation network python
D|scientometrics bibliometric analysis python
E|GROBID python client
E|scientific PDF parsing structured sections
E|PDF to markdown document parsing deep learning
E|citation reference string parsing
F|scientific information extraction knowledge graph papers
F|SciERC relation extraction scientific
F|knowledge graph construction from papers LLM
F|graph RAG knowledge graph LLM
G|literature review agent LLM
G|AI scientist automated research
G|deep research agent langgraph
G|survey generation LLM papers
H|neuro-symbolic reasoning framework
H|rule engine python
H|logic programming neural network python
H|LLM symbolic solver reasoning
I|conformal prediction python library
I|calibration uncertainty neural network python
I|selective prediction abstention LLM uncertainty
J|meta-analysis heterogeneity python
K|inter-annotator agreement krippendorff python
K|LLM evaluation framework RAG
K|LLM as judge evaluation
K|text annotation tool open source
L|scientific NLP benchmark dataset papers
L|S2ORC corpus scientific papers
M|community detection python graph
M|topic modeling BERTopic
M|scientific document embeddings SPECTER
A|research gap LLM
A|future work extraction
A|limitations papers dataset
A|research idea generation
A|novelty research ideas
A|scientific idea generation agent
B|scientific NLI
B|scientific claim verification
B|contradiction detection
B|PICO extraction
C|systematic review screening
C|systematic review LLM
D|bibliographic coupling
D|citation network analysis
E|GROBID client
E|scientific PDF parser
E|PDF markdown OCR
E|reference parsing citation
F|scientific knowledge graph
F|SciERC
F|knowledge graph construction LLM
F|relation extraction scientific papers
I|neural network calibration
I|LLM uncertainty estimation
I|conformal prediction
L|scientific papers dataset
L|scholarly document processing
H|neurosymbolic
G|paper QA agent
G|literature review automation
```

2. **Verifikasi metadata:** kandidat dari agen/seed dicek dengan `GET /search/repositories?q=repo:a/b repo:c/d … fork:true` (batch ≤ 240 karakter, hanya endpoint *search* karena limit anonim *core* 60/jam), fallback `HEAD https://github.com/a/b` untuk mendeteksi rename (301); HF via `GET https://huggingface.co/api/{models|datasets}/<id>`; arXiv via `export.arxiv.org/api/query?id_list=<id>`.
3. **Istilah pencarian HF Hub:** model — scientific nli, scibert, specter, nli-deberta, mnli-fever-anli, scifact, scincl, multilingual reranker, bge-reranker, nougat; dataset — scifact, scinli, scitail, futuregen, limitgen, s2orc, ebm-nlp, pubmed rct, scierc, evidence inference, research gap, scirepeval, csabstruct, peer read, unarXive, qasper, idea generation, novelty.
4. **Saringan:** `lolos = exists ∧ ¬archived ∧ (⭐ ≥ 50 ∨ tipe ∈ {dataset, benchmark, model, paper}) ∧ pushed_at ≥ 2024-09-16` (syarat ⭐/aktivitas hanya untuk tipe repo).
5. Skrip pemindaian, hasil mentah (`results_github.tsv`, `results_hf.tsv`, `verified.csv`) dan kurasi disimpan di folder sesi Copilot, tidak di repositori.

---
*Dibuat dengan bantuan GitHub Copilot CLI · data diambil 16 September 2026 · angka ⭐/♥ berubah seiring waktu.*
