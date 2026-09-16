# BAB IV: HASIL DAN PEMBAHASAN

## 4.1 Implementasi Sistem

### 4.1.1 Arsitektur Sistem

Sistem Wizard Research diimplementasikan sebagai aplikasi web berbasis arsitektur *client-server* dengan pendekatan Neuro-Symbolic Agentic sesuai desain yang diuraikan pada BAB III. Arsitektur sistem terdiri dari empat lapisan utama:

1. **Lapisan Antarmuka**: Dibangun sebagai aplikasi Streamlit tunggal (`tools/process_monitor/`, 12 halaman) yang menangani unggah jurnal, pemantauan tiap tahap pipeline, tampilan indikator gap beserta rantai provenansnya, dan alur *Wizard* empat langkah hingga judul usulan siap pakai. Antarmuka React/Vite pada versi awal digantikan agar seluruh proses eksperimen dan demonstrasi berjalan pada satu aplikasi.

2. **Lapisan API (Backend)**: Dibangun menggunakan FastAPI (Python) dengan endpoint RESTful untuk ingestion dokumen, analisis gap, antrean pekerjaan (*job queue* persisten berbasis SQLite), dan rekomendasi penelitian.

3. **Lapisan Agen (Agentic Core)**: Implementasi LangGraph untuk orkestrator multi-agen dengan pola *Observe → Think → Act → Evaluate*. Terdiri dari CoordinatorAgent, ResearchAnalyzerAgent, GapDetectorAgent, dan RecommenderAgent.

4. **Lapisan Penyimpanan**: ChromaDB sebagai vector database untuk *retrieval* semantik. Eksperimen benchmark (Subbab 4.3.1–4.3.7, Juli 2026) memakai model embedding `all-MiniLM-L6-v2`; sejak pengujian korpus aplikatif (Subbab 4.3.8 dan seterusnya) indeks dibangun ulang dengan model multibahasa `paraphrase-multilingual-MiniLM-L12-v2` karena korpus memuat jurnal berbahasa Indonesia, ditambah *reranker cross-encoder* (`ms-marco-MiniLM-L-6-v2`) sebagai tahap kedua retrieval.

### 4.1.2 Komponen Neuro-Symbolic

Komponen inti yang membedakan sistem ini dari pipeline RAG+LLM konvensional:

| Komponen | Baris Kode | Deskripsi |
|----------|------------|-----------|
| Rule Engine (`rule_engine.py`) | 831 | Validasi logis dengan 9 aturan (F1-F3, C1-C3, K1-K3) |
| Fact Table (`fact_table.py`) | 430 | Penyimpanan fakta SPO (*Subject-Predicate-Object*) |
| Fact Extractor (`fact_extractor.py`) | 599 | Ekstraksi entitas dan relasi dari teks |
| Relation Classifier (`relation_classifier.py`) | 453 | Klasifikasi 3 jenis hubungan (kookurensi, kausal, kontradiksi) |
| Coordinator Agent (`coordinator.py`) | 737 | Orkestrator LangGraph dengan 5 tool agen |
| Gap Analyzer (`analyzer.py`) | 2.035 | Deteksi 4 indikator gap (fragmentasi, inkonsistensi, ketidaklengkapan, ketiadaan dukungan bukti) + korroborasi pernyataan penulis |
| Support Gap (`support_gap.py`) | 423 | Indikator ke-4: uji kegagalan retrieval bukti primer *leave-one-out* |
| Graph Metrics (`graph_metrics.py`) | 573 | Modularitas Newman, prediksi tautan Adamic-Adar, isolasi struktural |
| Coverage Map (`coverage_map.py`) | 287 | *Evidence gap map* (Snilstveit dkk., 2016) untuk indikator ketidaklengkapan; dukungan sinonim sumbu |
| Coverage Axes (`coverage_axes.py`) | 275 | Sumbu peta bukti sadar domain: ontologi kurasi (YAML) > usulan LLM ber-*grounding* korpus > bawaan |
| Paper Profiles (`paper_profiles.py`) | 266 | Kanal samping per jurnal (kekurangan penulis, gap eksplisit, tahap metode, daftar pustaka) menuju analyzer |
| Workflow Stages (`workflow_stages.py`) | 358 | Rekonstruksi 8 tahap metode per jurnal dengan kutipan terverifikasi; deteksi tahap homogen lintas jurnal (Zhang & Zhang, 2025) |
| References (`pipeline/references.py`) | 245 | Penguraian daftar pustaka menjadi entri berkunci DOI / penulis-tahun-judul (tanpa LLM) |
| Citation Coupling (`citation_coupling.py`) | 207 | *Bibliographic coupling* antar jurnal (Kessler, 1963): komponen, Jaccard referensi, sitasi langsung |
| Calibration (`calibration.py`) | 470 | ECE/Brier/AURC, *temperature scaling*, abstensi selektif, rantai provenans |
| Novelty (`novelty.py`) | 305 | Skor kebaruan semantik untuk pemeringkatan usulan (bukan indikator gap) |

**Total**: ~7.900 baris kode Python untuk komponen inti, dengan **894 unit test** (16 September 2026: 892 lulus, 2 dilewati karena dependensi opsional tidak terpasang; termasuk 4 uji regresi fusi verdict–kalibrasi pada Subbab 4.3.11).

### 4.1.3 Teknologi yang Digunakan

| Kategori | Teknologi | Versi | Fungsi |
|----------|-----------|-------|--------|
| Backend | Python + FastAPI | 3.10 / 0.109+ | API server, antrean pekerjaan, dan logika bisnis |
| Antarmuka | Streamlit | 1.3x | Dasbor unggah, pemantauan tahap, hasil, dan *Wizard* (`tools/process_monitor/`) |
| LLM (eksperimen benchmark & ablasi) | Ollama | 0.3+ | `llama3.2:latest` (3B) dan `gpt-oss:latest` (13B), inferensi lokal |
| LLM (korpus aplikatif) | GitHub Copilot SDK | — | `claude-opus-4.8-fast` untuk pipeline 35 jurnal (Subbab 4.3.8–4.3.11); Ollama sebagai *fallback* |
| Vector DB | ChromaDB | 0.4.22+ | Penyimpanan dan retrieval embedding |
| Embedding | Sentence-Transformers | 2.2.2+ | `all-MiniLM-L6-v2` (benchmark) → `paraphrase-multilingual-MiniLM-L12-v2` (korpus aplikatif) + *reranker* `ms-marco-MiniLM-L-6-v2` |
| NLI | Sentence-Transformers CrossEncoder | — | `cross-encoder/nli-deberta-v3-xsmall` sebagai sinyal kontradiksi independen (mode `nli`) |
| Orchestration | LangGraph | 0.2+ | Workflow agen multi-langkah |
| Graph | NetworkX | 3.2.1+ | Knowledge graph SPO, komponen kopling bibliografis |
| Validasi | Pydantic | 2.5+ | Validasi data dan response model |

### 4.1.4 Statistik Implementasi

- **Total modul Python**: 25+ modul dalam 8 paket
- **Unit test**: 894 test (Rule Engine, Fact Table, Relation Classifier, Fact Extractor, Gap Analyzer, pipeline ingest, gap mining & konsensus k/n, kopling bibliografis, kalibrasi/provenans, API, integrasi)
- **Test coverage**: Semua komponen Neuro-Symbolic tervalidasi, termasuk parsing JSON terstruktur (Ollama JSON mode + retry + salvage truncated array) dan 35 uji regresi berbentuk data produksi (Subbab 4.3.8)
- **5 Tool Agen**: RAGTool, PaperAnalyzerTool, NLICheckerTool, KGQuerierTool, SelfCriticTool
- **Mode eksperimen**: `full`, `no-rule-engine` (ablasi H7), `linear-baseline` (ablasi H6), `nli`/`no-nli` (ablasi H9), `cross-critic` (H10) + topik kontrol negatif

---

## 4.2 Skenario Pengujian

### 4.2.1 Dataset Pengujian

Eksperimen menggunakan **23 paper benchmark** dari domain *computer science*
(2014–2021) yang diunduh secara *reproducible* dari arXiv
(`backend/experiments/download_papers.py`), terorganisasi dalam 4 kelompok topik
(3–10 paper per kelompok, sesuai batasan masalah proposal):

| Topik | Fokus | Jumlah Paper | Contoh Paper |
|-------|-------|--------------|--------------|
| T1 | Arsitektur deep learning & optimasi | 6 | ResNet, DenseNet, Adam, BatchNorm, LayerNorm, GAN |
| T2 | Computer vision & object detection | 6 | YOLO, Faster R-CNN, SSD, Mask R-CNN, EfficientNet, ViT |
| T3 | NLP & attention mechanisms | 6 | Transformer, BERT, GPT-3, T5, RoBERTa, ELECTRA |
| T4 | Deployment efisien & kompresi model | 5 | MobileNet v1/v2, DistilBERT, Distillation, SqueezeNet |

Topik T4 sengaja dipilih karena karakteristik *resource constraint*-nya
mengaktifkan aturan kelayakan (F1–F3) Rule Engine. Metadata lengkap tersimpan
di `research_papers/papers_manifest.json`.

### 4.2.2 Topik Query Pengujian

Empat topik query sesuai kelompok dataset:

1. **T1**: *"Deep learning architectures and optimization techniques"*
2. **T2**: *"Computer vision object detection and image recognition"*
3. **T3**: *"Natural language processing and attention mechanisms"*
4. **T4**: *"Efficient deep learning deployment on resource-constrained edge devices"*

### 4.2.3 Metrik Evaluasi

Sesuai framework evaluasi pada BAB III, metrik yang diukur:

| Kode | Metrik | Deskripsi |
|------|--------|-----------|
| M1 | Jumlah Indikator Gap | Total indikator yang terdeteksi per topik |
| M2 | Distribusi Tipe Indikator | Proporsi Fragmentasi:Inkonsistensi:Ketidaklengkapan:Ketiadaan Dukungan Bukti |
| M3 | Skor Kepercayaan (Confidence) | Rata-rata, min, max confidence per indikator |
| M4 | Verdict Rule Engine | Distribusi PASS/FLAG/REJECT |
| M5 | Waktu Eksekusi | Durasi per fase pipeline |
| M6 | Kebutuhan Validasi Manusia | Proporsi indikator yang membutuhkan verifikasi |
| M7 | RERR (*Rule Engine Rejection Rate*) | Persentase output LLM yang tidak lolos bersih (FLAG+REJECT) |
| M8 | Akurasi Adversarial | Persentase kasus adversarial dengan verdict sesuai harapan |
| M9 | Kalibrasi (ECE, Brier, AURC) | Selisih keyakinan–akurasi, galat kuadrat, dan area risiko-cakupan |
| M10 | Laju Abstensi Selektif | Proporsi indikator ber-`needs_review` beserta alasan abstensi |
| M11 | Kelengkapan Provenans | Proporsi indikator dengan rantai klaim→jurnal→kutipan→validasi utuh |
| M12 | Kebaruan Usulan | Distribusi *band* kebaruan (derivative / sweet spot / off-topic) usulan |
| M13 | Stabilitas Lintas-Run (k/n) | Proporsi temuan bergantung-LLM yang muncul pada ≥ ⌈2n/3⌉ dari n *run* identik; Jaccard antar-run |
| M14 | Korroborasi Penulis | Proporsi indikator lintas-paper yang didukung ≥ 1 pernyataan keterbatasan/*future work* penulis di dalam korpus |

Metrik M9–M12 ditambahkan pada revisi metodologi (Subbab 3.6–3.7) sebagai
konsekuensi penambahan indikator keempat dan lapisan kalibrasi; M13–M14 menyusul
bersama pelaporan stabilitas lintas-run dan lapisan korroborasi penulis (Subbab
3.6.2 dan 3.7.4). M1–M8 tetap diukur agar hasil pra-revisi dan pasca-revisi dapat
dibandingkan langsung.

Metrik berbasis pakar (EAR, LCS, AS, FDR, SHG, REP — hipotesis H4–H5) diukur
terpisah melalui instrumen penilaian di `backend/experiments/expert_eval/`
setelah hasil eksperimen final.

### 4.2.4 Desain Eksperimen: Mode Ablasi & Validasi Adversarial

Untuk menguji hipotesis H6 dan H7, eksperimen dijalankan dalam **3 mode**:

| Mode | Komponen Aktif | Hipotesis |
|------|----------------|-----------|
| `full` | Pipeline lengkap: ingestion → fact extraction → gap detection → rule engine | — (baseline sistem) |
| `no-rule-engine` | Pipeline penuh TANPA lapisan validasi simbolis | H7: apakah Rule Engine mengurangi false discovery |
| `linear-baseline` | RAG + single-prompt LLM (tanpa agentic loop, tanpa fact base, tanpa rule engine) | H6: apakah sistem agentic mengungguli pipeline linear |

Selain itu, **fase validasi adversarial** menyuntikkan 6 klaim yang dirancang
melanggar aturan spesifik (F1, F2, F3, K1, C1 + 1 kontrol bersih) ke FactTable
terisolasi, untuk membuktikan Rule Engine benar-benar mendiskriminasi — bukan
sekadar meloloskan semua input.

### 4.2.5 Setup Eksperimen

Dua konfigurasi dipakai pada dua kelompok pengujian yang berbeda dan **tidak
dibandingkan silang** satu sama lain:

| Aspek | Eksperimen benchmark & ablasi (Subbab 4.3.1–4.3.7) | Pengujian korpus aplikatif (Subbab 4.3.8–4.3.11) |
|-------|------------------------------------------------------|---------------------------------------------------|
| Korpus | 23 paper *computer science* (T1–T4, bahasa Inggris) | 35 jurnal forensika digital (Indonesia & Inggris) |
| LLM | `llama3.2:latest` (3B) dan `gpt-oss:latest` (13B) via Ollama, lokal | `claude-opus-4.8-fast` via GitHub Copilot SDK; Ollama sebagai *fallback* |
| Embedding | `all-MiniLM-L6-v2` (384 dimensi) | `paraphrase-multilingual-MiniLM-L12-v2` + *reranker* `ms-marco-MiniLM-L-6-v2` |
| Parameter LLM | temperature = 0,3, max_tokens = 2048, JSON mode untuk ekstraksi fakta | bawaan penyedia; JSON mode + *salvage parser* untuk keluaran terstruktur |
| Chunking | `chunk_size=512` karakter, overlap 50 | sadar-kalimat & sadar-token (Subbab 3.2.1 revisi), overlap konsisten |
| Kedalaman analisis | `standard` (fragmentasi + inkonsistensi + ketidaklengkapan) | penuh (empat indikator + kalibrasi + provenans + korroborasi) |
| Hardware | Server lokal (GPU untuk Ollama) | Server lokal; inferensi LLM di penyedia |

Pemisahan ini disengaja: kelompok pertama menjawab hipotesis ablasi (H6, H7,
H9) dengan model lokal yang dapat di-*seed* dan diulang, sedangkan kelompok
kedua menguji perilaku sistem lengkap pada dokumen nyata dalam bahasa campuran.
Konsekuensi metodologisnya dibahas pada Subbab 4.4.3 (butir 8).

---

## 4.3 Hasil Eksperimen

Hasil yang dilaporkan pada bagian ini berasal dari eksperimen konfigurasi penuh
(*full mode*) dengan model `llama3.2` (3B) terhadap korpus benchmark 23 paper,
kecuali dinyatakan lain. Hasil ablasi dan komparasi model dibahas pada Subbab 4.3.6.

### 4.3.1 Hasil Ingestion dan Preprocessing (Fase 1)

Seluruh 23 paper benchmark berhasil diproses dan diindeks ke dalam ChromaDB:

| Metrik | Nilai |
|--------|-------|
| Paper diproses | 23 (4 topik: T1–T4) |
| Total chunks terindeks | 3.146 |
| Rata-rata chunks per paper | ~137 |
| Model embedding | all-MiniLM-L6-v2 (384 dimensi) |

Konfigurasi chunking menggunakan `chunk_size=512` dengan overlap 50 karakter.
Basis data vektor eksperimen (`chroma_db_experiment/`) diisolasi dari basis
data demo agar hasil tidak terkontaminasi dokumen lain.

### 4.3.2 Hasil Ekstraksi Fakta (Fase 2)

| Metrik | Nilai |
|--------|-------|
| Total fakta SPO terekstrak | 248 |
| Paper menghasilkan ≥1 fakta | 22 dari 23 (95,7%) |
| Rata-rata fakta per paper | 10,8 |
| Rentang fakta per paper | 0 – 30 |
| Waktu total ekstraksi | 1.735 detik (~28,9 menit) |

Ekstraksi fakta menggabungkan tiga metode: (a) ekstraksi LLM dengan
*structured output* JSON, (b) *pattern matching* penanda linguistik
(`outperforms`, `is based on`, dst.), dan (c) ko-okurensi entitas. Satu paper
menghasilkan 0 fakta karena konten terdominasi notasi matematis yang tidak
mengandung pola relasi SPO yang dikenali.

### 4.3.3 Hasil Deteksi Gap (Fase 3)

Hasil pada subbab ini berasal dari **pipeline pra-revisi (tiga indikator)** pada
korpus benchmark 23 paper, dan dipertahankan sebagai garis dasar pembanding.
Hasil pipeline empat indikator beserta lapisan kalibrasi dilaporkan terpisah di
Subbab 4.3.8.

Sistem mengidentifikasi **14 indikator gap** dari 4 topik query:

#### Tabel 4.1: Ringkasan Indikator Gap per Topik

| Topik | Total Indikator | Fragmentasi | Inkonsistensi | Ketidaklengkapan | Avg. Confidence | Waktu (s) |
|-------|----------------|-------------|---------------|------------------|-----------------|-----------|
| T1: Deep Learning Architectures | 3 | 1 | 1 | 1 | 0,717 | 4,62 |
| T2: Computer Vision | 4 | 1 | 1 | 2 | 0,688 | 6,62 |
| T3: NLP & Attention | 4 | 1 | 1 | 2 | 0,688 | 4,63 |
| T4: Efficient/Edge Deep Learning | 3 | 1 | 1 | 1 | 0,717 | 6,32 |
| **Total** | **14** | **4** | **4** | **6** | **0,700** | **22,19** |

Setiap topik menggunakan 10 chunk paling relevan hasil retrieval semantik.

#### Distribusi Tipe Indikator

```
Ketidaklengkapan (INCOMPLETENESS): 42,9% (6/14)
Fragmentasi (FRAGMENTATION):       28,6% (4/14)
Inkonsistensi (INCONSISTENCY):     28,6% (4/14)
```

Dominasi indikator ketidaklengkapan konsisten dengan definisi Cooper (1998)
bahwa *synthesis gap* sering muncul karena aspek-aspek kritis yang belum
diteliti secara kolektif oleh komunitas riset.

### 4.3.4 Analisis Skor Kepercayaan dan Validasi Rule Engine (Fase 4)

| Statistik Confidence | Nilai |
|----------------------|-------|
| Rata-rata keseluruhan | 0,700 |
| Skor tertinggi | 0,850 |
| Skor terendah | 0,500 |

Distribusi per tipe: indikator FRAGMENTATION konsisten pada 0,850 (diukur
kuantitatif via clustering topik), INCOMPLETENESS pada 0,600–0,800, dan
INCONSISTENCY pada 0,500 (terendah, karena bergantung pada deteksi kontradiksi
LLM yang tidak melakukan penalaran logis sejati [Marcus, 2020]). Seluruh
indikator INCONSISTENCY diberi label `requires_human_validation = True`.

Hasil validasi Rule Engine terhadap 14 indikator:

| Metrik | Nilai |
|--------|-------|
| Total indikator dievaluasi | 14 |
| PASS | 14 (100%) |
| FLAG | 0 (0%) |
| REJECT | 0 (0%) |
| RERR (Rule Engine Rejection Rate) | 0,0% |
| Waktu validasi | <0,01 detik |

Tingkat PASS 100% pada korpus benchmark **bukan** indikasi lapisan validasi
tidak bekerja, melainkan konsekuensi karakteristik input: indikator yang
dihasilkan dari paper berkualitas tinggi memang tidak melanggar aturan
kelayakan/kausalitas/konsistensi. Untuk membuktikan kemampuan diskriminatif
Rule Engine, dilakukan validasi adversarial (Subbab 4.3.5).

### 4.3.5 Hasil Validasi Adversarial

Enam klaim adversarial yang dirancang melanggar aturan spesifik disuntikkan ke
FactTable terisolasi. Rule Engine diharapkan menolak/menandai klaim bermasalah
dan meloloskan klaim kontrol:

#### Tabel 4.2: Hasil Validasi Adversarial (6 Kasus)

| Kasus | Aturan Diuji | Verdict Diharapkan | Verdict Aktual | Cocok | Confidence (sebelum → sesudah) |
|-------|--------------|--------------------|----------------|-------|-------------------------------|
| ADV-F1 | F1 (Resource Compatibility) | REJECT | REJECT | ✓ | 0,90 → 0,30 |
| ADV-F2 | F2 (Data Compatibility) | FLAG | FLAG | ✓ | 0,80 → 0,50 |
| ADV-F3 | F3 (Scale Compatibility) | REJECT | REJECT | ✓ | 0,85 → 0,25 |
| ADV-K1 | K1 (Internal Contradiction) | FLAG | FLAG | ✓ | 0,75 → 0,55 |
| ADV-C1 | C1 (Causal Evidence) | FLAG | FLAG | ✓ | 0,80 → 0,65 |
| ADV-PASS | Kontrol (tanpa pelanggaran) | PASS | PASS | ✓ | 0,70 → 0,70 |

**Akurasi adversarial: 6/6 (100%)**. Rule Engine secara tepat: (1) menolak
klaim yang tidak layak secara sumber daya dan skala, (2) menandai klaim dengan
data tidak kompatibel, kontradiksi internal, dan klaim kausal tanpa bukti,
serta (3) meloloskan klaim kontrol yang valid — membuktikan verdict PASS pada
Subbab 4.3.4 bukan karena Rule Engine meloloskan semua input.

Hasil ini menjawab kekhawatiran kalibrasi: penurunan confidence terbesar
terjadi pada pelanggaran kelayakan keras (F1: −0,60; F3: −0,60), sedangkan
pelanggaran yang memerlukan tinjauan manusia diturunkan moderat (C1: −0,15;
K1: −0,20).

### 4.3.6 Hasil Ablasi dan Komparasi

#### Mode Linear Baseline (RAG+LLM tanpa komponen symbolic)

| Metrik | Full Mode | Linear Baseline |
|--------|-----------|-----------------|
| Fakta SPO terekstrak | 248 | 0 (tidak ada FactTable) |
| Indikator gap | 14 | 20 |
| Validasi Rule Engine | 100% tervalidasi | Tidak ada |
| Reasoning trace | Ada (per indikator) | Tidak ada |
| Waktu pipeline | 1.757 s | 46 s |

Baseline linear menghasilkan *lebih banyak* indikator (20 vs 14) namun
**tanpa validasi apa pun**: tidak ada fakta terstruktur, tidak ada verdict,
dan tidak ada jejak penalaran. Pola output baseline juga seragam antar topik
(5 indikator dengan distribusi identik untuk semua topik), mengindikasikan
output templat LLM alih-alih analisis spesifik-topik. Ini mendukung H6:
komponen symbolic menambah akuntabilitas — *bukan* sekadar jumlah output.

#### Ablasi NLI (H9): Multi-Run dengan Uji Signifikansi

Untuk menguji kontribusi lapisan verifikasi NLI (H9), mode `nli` dan `no-nli`
dijalankan berulang dengan *seed* berbeda per run (7 run `nli`, seeds 43–49;
5 run `no-nli`, seeds 43–47 — desain tidak seimbang yang tetap valid untuk
uji Mann–Whitney U). Statistik dihitung pada ringkasan per-run (satu observasi
per run) untuk menghindari *pseudo-replication*:

| Mode | n run | Indikator/run (mean±std) | Confidence/run (mean±std) |
|------|-------|--------------------------|---------------------------|
| nli | 7 | **24,3 ± 2,3** | **0,791 ± 0,012** |
| no-nli | 5 | 15,2 ± 1,9 | 0,749 ± 0,025 |

Kedua variabel menunjukkan **pemisahan sempurna** antar kelompok — seluruh run
`nli` bernilai lebih tinggi dari seluruh run `no-nli` (indikator: min 22 vs
maks 18; confidence: min 0,779 vs maks 0,773) — sehingga U mencapai nilai
maksimum (35):

| Variabel | U | p | p Holm (keluarga 8 uji) | Signifikan (α=0,05) | Effect size |
|----------|---|---|--------------------------|----------------------|-------------|
| Indikator/run | 35 | 0,0055 | **0,0428** | **ya** | δ=1,0 (large); Δmed=8 [5, 13] |
| Confidence/run | 35 | 0,0057 | **0,0428** | **ya** | δ=1,0 (large); Δmed=0,038 [0,013, 0,082] |

Koreksi Holm–Bonferroni diterapkan atas keluarga **delapan** uji ablasi (H6,
H7, H9, H10 × dua variabel; Subbab 4.3.12 menambahkan H10 ke keluarga yang
sama, sehingga p Holm H9 naik dari 0,0331 pada laporan awal menjadi 0,0428 —
tetap signifikan). **H9 terkonfirmasi**: lapisan NLI meningkatkan jumlah
indikator kesenjangan terdeteksi (Δmedian = 8) sekaligus confidence-nya secara
signifikan. Sebaliknya, H6 dan H7 tidak mencapai signifikansi pada jumlah run
ini (p Holm ≥ 0,48) — efek Rule Engine bersifat kualitatif (akuntabilitas dan
kemampuan menolak klaim adversarial, Subbab 4.3.5), bukan kuantitas indikator.

Untuk melengkapi angka satu-run pada Subbab 4.3.3–4.3.4, ringkasan seluruh
mode pada protokol multi-run yang sama (`llama3.2`, seed 43–47/49; satu
observasi per *run*) adalah:

| Mode | n run | Indikator/run | Confidence/run | Fakta SPO/run | RERR % |
|------|------:|--------------:|---------------:|--------------:|-------:|
| `full` | 5 | 17,2 ± 3,2 | 0,730 ± 0,021 | 133 ± 9 | 3,8 ± 8,5 |
| `no-rule-engine` | 5 | 18,2 ± 5,5 | 0,728 ± 0,021 | 127 ± 3 | 0 (tidak ada validasi) |
| `linear-baseline` | 5 | 20 ± 0 | 0,709 ± 0,008 | 0 | 0 (tidak ada validasi) |
| `nli` | 7 | 24,3 ± 2,3 | 0,791 ± 0,012 | 130 ± 8 | 0 ± 0 |
| `no-nli` | 5 | 15,2 ± 1,9 | 0,749 ± 0,025 | 137 ± 12 | 4,4 ± 9,9 |
| `cross-critic` | 5 | 4,2 ± 4,1 | 0,884 ± 0,070 | 124 ± 7 | 0 ± 0 |

Dua pengamatan: (1) jumlah indikator `full` per *run* (17,2 ± 3,2) lebih
tinggi daripada eksekusi tunggal yang dirinci pada Tabel 4.1 (14) — perbedaan
yang berada dalam satu simpangan baku dan sekali lagi menegaskan bahwa angka
satu *run* adalah satu realisasi; (2) RERR `full` tidak selalu 0: pada satu dari
lima *run* Rule Engine menandai sebagian indikator (rerata 3,8%), sehingga
verdict PASS 100% pada Tabel 4.1 juga bukan sifat tetap sistem.

#### Komparasi Model (Sensitivitas Kapasitas Model)

Komparasi `llama3.2` (3B) dengan `gpt-oss` (13B, model *reasoning*)
mengungkap temuan teknis penting: model reasoning gagal menghasilkan output
ketika *structured output* JSON mode Ollama dipaksakan (respons kosong),
sehingga ekstraksi fakta turun drastis. Setelah mekanisme *fallback* (JSON
mode hanya pada percobaan pertama, percobaan ulang tanpa format constraint)
diterapkan, eksperimen diulang. Temuan ini menunjukkan pipeline ekstraksi
fakta sensitif terhadap perilaku decoding model — relevan sebagai catatan
implementasi untuk reproduksibilitas.

### 4.3.7 Performa Waktu Eksekusi

| Fase | Waktu (s) | Persentase |
|------|-----------|------------|
| Ingestion & Preprocessing | (pra-komputasi, ~3 menit) | — |
| Fact Extraction (23 paper) | 1.735,1 | 98,7% |
| Gap Detection (4 topik) | 22,2 | 1,3% |
| Rule Engine + Adversarial | <0,1 | <0,1% |
| **Total Pipeline** | **1.757,2** | **100%** |

Fase Fact Extraction mendominasi waktu eksekusi (98,7%) karena setiap paper
memerlukan beberapa inferensi LLM (ekstraksi entitas + relasi, dengan retry).
Ini konsisten dengan temuan bahwa komponen neural (LLM) merupakan *bottleneck*
utama, sementara komponen symbolic (Rule Engine) beroperasi hampir instan
(<0,1 detik untuk 14 indikator + 6 kasus adversarial) — penambahan lapisan
validasi logis praktis tanpa *overhead*.

### 4.3.8 Hasil Pipeline Empat Indikator dan Lapisan Kalibrasi

Setelah revisi metodologi (Subbab 3.6–3.7), pipeline diuji pada korpus aplikatif
**35 jurnal forensika digital** (3.095 chunk pada *chunker* versi Agustus 2026,
5 topik hasil klasterisasi, tanpa duplikat) memakai LLM `claude-opus-4.8-fast`
(GitHub Copilot SDK) dan *embedder* multibahasa (Subbab 4.2.5). Subbab ini
melaporkan metrik M9–M12 yang tidak dapat diukur pada pipeline pra-revisi;
hasil dari eksekusi ulang dengan versi akhir sistem (korroborasi penulis,
kopling bibliografis dalam pipeline, tahap metode) dilaporkan pada Subbab 4.3.11.

#### Tabel 4.3: Ringkasan Eksekusi Pipeline Empat Indikator

| Aspek | Nilai |
|-------|-------|
| Jurnal diproses | 35 (35 baru, 0 duplikat) |
| Chunk terindeks | 3.095 |
| Topik terdeteksi | 5 |
| Indikator lolos validasi | 2 (keduanya KETIDAKLENGKAPAN) |
| Verdict Rule Engine | 2 PASS, 0 FLAG, 0 REJECT (RERR 0,0%) |
| Waktu total pipeline | 308,1 detik (~5,1 menit) |

#### M9 — Kalibrasi

| Indikator | Confidence Mentah | Confidence Terkalibrasi | Temperature |
|-----------|-------------------|-------------------------|-------------|
| Ketidaklengkapan kolektif (10 aspek kritis tak tercakup) | 0,850 | 0,935 | 1,0 |
| Ketidaklengkapan metodologis (10 jurnal memakai *case study*) | 0,800 | 0,880 | 1,0 |

Temperature bernilai 1,0 karena himpunan label pakar masih kosong
(`calibration_labels = 0`, di bawah `MIN_CALIBRATION_LABELS = 4`), sehingga
kalibrator beroperasi sebagai pemetaan identitas dan kenaikan skor semata-mata
berasal dari pengali verdict `PASS` (×1,10). ECE, Brier, dan AURC karena itu
**belum dapat dilaporkan** dan akan diukur setelah instrumen penilaian pakar
(Subbab 4.2.3) terkumpul. Status ini ditampilkan apa adanya di antarmuka
("belum ada label pakar (identitas)") agar tidak disalahartikan sebagai
kalibrasi yang sudah tervalidasi — konsisten dengan prinsip bahwa keyakinan
model tidak boleh disajikan lebih meyakinkan daripada bukti pendukungnya.

#### M10 — Abstensi Selektif dan M11 — Kelengkapan Provenans

| Metrik | Sebelum Perbaikan | Sesudah Perbaikan |
|--------|-------------------|-------------------|
| Indikator ber-`needs_review` | 4/4 (100%) | 0/2 (0%) |
| Rantai provenans lengkap | 0/4 (0%) | 2/2 (100%) |
| Kutipan verbatim per indikator | 0 | 3 |

Pengujian pada korpus nyata mengungkap tiga cacat implementasi yang tidak
terlihat pada uji sintetis dan seluruhnya bersifat *silent* (tidak memunculkan
galat):

1. **Asimetri istilah grounding–kutipan.** Uji *grounding* menyatakan sebuah
   aspek "ada di korpus" bila salah satu kata-isinya muncul, sedangkan
   pengambil kutipan mencocokkan **frasa utuh**. Aspek berupa frasa panjang
   ("*Chain of custody* dan integritas bukti digital") karenanya selalu lolos
   grounding namun tidak pernah menghasilkan kutipan, sehingga rantai provenans
   permanen terputus dan **seluruh** indikator dipaksa `needs_review`. Perbaikan
   menyatukan kedua uji pada fungsi `aspect_terms()` yang sama.
2. **Indikator metodologis tanpa kutipan.** Klaim "semua jurnal memakai metode
   yang sama" tidak pernah menyertakan kutipan, padahal justru kalimat tempat
   metode itu disebut merupakan buktinya.
3. **Peta bukti degeneratif.** Matriks 1×1 dengan kerapatan 100% tetap
   memancarkan indikator berbunyi "0 dari 1 sel tidak memuat studi" — sebuah
   non-temuan. Gate diperketat menjadi minimal 2×2 **dan** wajib memiliki
   sedikitnya satu sel kosong, sesuai definisi *evidence gap map* (Snilstveit
   dkk., 2016) yang menempatkan sel kosong sebagai sinyal, bukan sel tipis.

Setelah perbaikan, abstensi menjadi **selektif**: kedua indikator memiliki
rantai klaim → 6 jurnal terkutip → 3 kutipan verbatim → verdict `PASS`
("9 aturan diuji, tidak ada pelanggaran") yang utuh, sehingga tidak lagi
ditandai butuh peninjauan. Ini adalah perilaku yang diinginkan: abstensi hanya
bermakna bila ia membedakan, bukan bila ia menyala untuk semua keluaran.

#### M12 — Kebaruan Usulan

| Usulan | Indikator Dijawab | Kebaruan | *Band* | Skor Prioritas |
|--------|-------------------|----------|--------|----------------|
| 1 | KETIDAKLENGKAPAN | 0,358 | *sweet spot* | 0,968 |
| 2 | KETIDAKLENGKAPAN | 0,361 | *sweet spot* | 0,968 |
| 3 | KETIDAKLENGKAPAN | 0,309 | *sweet spot* | 0,834 |
| 4 | KETIDAKLENGKAPAN | 0,412 | *sweet spot* | 0,834 |
| 5 | KETIADAAN DUKUNGAN BUKTI | 0,430 | *sweet spot* | 0,367 |

Seluruh usulan jatuh pada rentang *sweet spot* (0,25–0,65), yaitu cukup berbeda
dari korpus untuk tidak sekadar mengulang, namun masih cukup dekat untuk tetap
relevan. Usulan ke-5 memperoleh prioritas jauh lebih rendah (0,367) meskipun
kebaruannya tertinggi, karena indikator KETIADAAN DUKUNGAN BUKTI **tidak**
terdeteksi pada korpus ini sehingga bobot `gap_confidence`-nya nol. Perilaku ini
mengonfirmasi keputusan desain pada Subbab 3.6.2: kebaruan semantik hanya berfungsi
sebagai sinyal **pemeringkatan** dan tidak pernah dapat mengangkat usulan yang
tidak berjangkar pada indikator gap yang benar-benar terdeteksi.

#### Catatan Reproduksibilitas

Ketiga cacat di atas hanya terungkap ketika pipeline dijalankan pada dokumen
nyata; uji sintetis tidak menangkapnya karena memakai frasa pendek, *embedder*
tiruan, dan matriks yang selalu berukuran memadai. Karena itu ditambahkan 35
unit test regresi (`backend/tests/test_gap_upgrade.py`) yang secara eksplisit
menguji kondisi-kondisi tersebut — termasuk *embedder* yang mengembalikan
`Tensor`, korpus dengan `sample_chunks` bertipe dict, dan matriks degeneratif —
sehingga total pada saat itu menjadi 508 unit test yang seluruhnya lulus (894
pada versi akhir sistem, Subbab 4.1.2).

### 4.3.9 Sinyal Struktural Bebas-LLM: Kopling Bibliografis pada Korpus Forensik

Metode fragmentasi kelima (Subbab 3.6.2, kopling bibliografis) diuji pada
korpus 35 jurnal forensika digital yang sama, langsung dari daftar pustaka yang
diurai tanpa LLM.

#### Tabel 4.4: Penguraian Daftar Pustaka dan Kopling Bibliografis (35 jurnal)

| Aspek | Nilai |
|-------|-------|
| Jurnal dengan ≥ 5 entri pustaka terurai (memenuhi syarat) | 25 dari 35 |
| Jurnal dilewati (daftar pustaka tidak terdeteksi / < 5 entri) | 10 (termasuk 4 dengan 0 entri: editorial, bab buku, PDF Cyrillic) |
| Entri terurai pada jurnal terbanyak | 73 (46 ber-DOI) |
| Komponen graf kopling | 20 (ukuran 3, 3, 2, dan 17 jurnal tunggal) |
| Pasangan jurnal tanpa referensi bersama & tanpa sitasi langsung | 295 dari 300 (isolasi 0,98) |
| Sitasi langsung antar-jurnal korpus | 2 (keduanya terverifikasi benar: 1 via DOI, 1 via judul) |
| Karya rujukan yang dibagi ≥ 2 jurnal | 5 (antara lain Piva, 2013, *An Overview on Image Forensics*; Riadi dkk., analisis *image forensics*) |
| Modularitas Q partisi komponen | 0,58 |

Hasilnya memperkuat, dari arah yang sepenuhnya independen dari LLM dan
*embedding*, temuan fragmentasi pada Subbab 4.3.8 dan temuan bahwa sebagian
besar tema rekomendasi hanya didukung satu jurnal: 25 jurnal yang membahas
forensika digital hampir tidak berbagi basis rujukan (hanya 5 dari 300 pasangan
yang terkopel) dan hampir tidak saling mengutip. Dua pengamatan metodologis
penting dari pengujian ini: (1) pencocokan sitasi langsung berbasis kesamaan
judul dengan ambang tetap empat kata isi menghasilkan 12 kandidat, 10 di
antaranya positif palsu akibat kata domain umum ("*forensic*", "*digital*",
"*evidence*"); ambang proporsional (≥ 60% kata isi himpunan terpendek, entri
minimal lima kata isi) menyisakan tepat dua sitasi yang keduanya benar — ambang
inilah yang dipakai; (2) sepuluh jurnal yang dilewati **tidak** dihitung sebagai
terputus, sehingga angka isolasi 0,98 adalah properti dari 25 jurnal yang daftar
pustakanya benar-benar terbaca, bukan artefak kegagalan penguraian.

### 4.3.10 Stabilitas Lintas-Run Penambangan Gap (M13) dan Kualitas Ekstraksinya

Lapisan korroborasi penulis (Subbab 3.6.2) bersumber dari tahap penambangan
pernyataan gap per jurnal — kalimat *future work*, *limitation*, dan gap
implisit yang diekstrak LLM dari chunk kandidat dan diverifikasi verbatim
terhadap teks sumber. Karena tahap ini bergantung pada LLM, ia diukur dengan
protokol k/n (Subbab 3.7.4): tiga *run* independen pada masukan yang identik
(korpus 35 jurnal forensika digital, `claude-opus-4.8-fast`), digabungkan
dengan kunci yang sama dengan yang dipakai pipeline (`merge_gap_runs`).

#### Tabel 4.5: Stabilitas Lintas-Run Penambangan Gap (n = 3)

| Aspek | Nilai |
|-------|-------|
| Gap per *run* (verbatim-grounded 100%) | 388 · 307 · 336 (jurnal bergap: 27 · 23 · 24 dari 35) |
| Gabungan (union) gap unik | 528 dari 28 jurnal |
| Muncul pada 3/3 *run* | 196 (37,1%) |
| Muncul pada 2/3 *run* | 111 (21,0%) |
| Muncul pada 1/3 *run* saja | 221 (41,9%) |
| **Stabil** (k ≥ ⌈2n/3⌉ = 2) | **307 (58,1%)** — diteruskan ke tahap berikutnya |
| Tidak stabil (k = 1) | 221 (41,9%) — disimpan, ditampilkan, tidak diperingkat |
| Jaccard antar pasangan *run* | 0,445 · 0,475 · 0,645 (rerata 0,52) |

Stabilitas berbeda tajam menurut jenis pernyataan:

| Jenis pernyataan gap | Union | Stabil (k ≥ 2) | Proporsi stabil | k = 3 |
|----------------------|------:|---------------:|----------------:|------:|
| *Stated limitation* (keterbatasan yang dinyatakan penulis) | 315 | 197 | **62,5%** | 133 |
| *Explicit future work* | 116 | 70 | 60,3% | 40 |
| *Implicit gap* (disimpulkan LLM) | 97 | 40 | **41,2%** | 23 |

Dua implikasi langsung. Pertama, angka satu *run* memang hanya satu undian:
tumpang tindih antar dua *run* identik berkisar 0,45–0,65 (Jaccard), sehingga
"388 gap" pada laporan awal tidak dapat dipakai sebagai hasil tanpa anotasi
k/n — tepat seperti yang diantisipasi Subbab 3.7.4. Kedua, pernyataan yang
**tersurat** dalam teks (keterbatasan dan *future work* yang ditulis penulis)
jauh lebih dapat direproduksi daripada gap yang harus **disimpulkan** LLM
(41% vs 60–63%). Karena itu lapisan korroborasi (Subbab 4.3.11) sengaja hanya
memakai pernyataan stabil, dan kutipan tersurat diberi status bukti lebih kuat
daripada gap implisit.

#### Kualitas ekstraksi terhadap *gold standard* eksternal

Ketepatan isi pernyataan gap diuji pada *benchmark* independen: 30 paper sampel
acak dari dataset Mendeley "research gaps" (3.326 paper arXiv dengan kolom emas
*Limitation*/*Research Gap* hasil kurasi manusia), abstrak diambil dari arXiv
(30/30 berhasil).

| Metrik | Nilai |
|--------|-------|
| Paper yang menghasilkan ≥ 1 pernyataan gap | 20 dari 30 (66,7%) |
| Kemiripan semantik gap sistem vs gap emas (*embedder* multibahasa, skor terbaik antara pernyataan & parafrasa) | rerata **0,603**; ≥ 0,5 pada 14/20 |
| LLM-as-judge (skala 1–5, rubrik FutureGen) | rerata **2,75**; ≥ 3 pada 10/20 |

Dua catatan metodologis: (1) pengukuran awal memakai *embedder* Inggris-saja
terhadap parafrasa berbahasa Indonesia dan menghasilkan skor 0,176 yang
menyesatkan; angka 0,603 diperoleh setelah pembanding disamakan bahasanya —
contoh nyata bahwa metrik kemiripan lintas bahasa harus memakai model
multibahasa; (2) skor *judge* 2,75 menunjukkan ekstraksi menangkap **topik**
gap dengan baik tetapi sering kurang **spesifik** dibanding rumusan kurator
manusia — konsisten dengan temuan bahwa gap implisit paling tidak stabil.
Benchmark ini mengukur komponen penambangan gap, bukan indikator *synthesis
gap* lintas-jurnal; evaluasi indikator tetap memerlukan pakar (Subbab 4.4.5).

### 4.3.11 Eksekusi Ulang Versi Akhir Sistem pada Korpus 35 Jurnal (M14, Kopling dalam Pipeline)

Fitur yang ditambahkan setelah pengujian Agustus — korroborasi pernyataan
penulis (Subbab 3.6.2), kopling bibliografis sebagai metode fragmentasi di
dalam pipeline, sumbu peta bukti sadar domain, dan *chunker* sadar-kalimat —
belum pernah dijalankan bersama pada korpus tesis. Karena itu job 35 jurnal
yang sama dieksekusi ulang **dua kali** dengan versi akhir kode
(`analysis-jobs/{id}/reanalyze`, LLM `claude-opus-4.8-fast`, 16 September
2026). Dua eksekusi diperlukan: eksekusi pertama mengungkap satu cacat
konsistensi (dibahas di akhir subbab), eksekusi kedua adalah hasil yang
dilaporkan; keduanya sekaligus memberi dua realisasi untuk menilai stabilitas.

#### Tabel 4.6: Ringkasan Eksekusi Ulang Versi Akhir (n = 2)

| Aspek | Eksekusi 1 | Eksekusi 2 (dilaporkan) |
|-------|-----------:|------------------------:|
| Jurnal diproses / chunk terindeks | 35 / 877 | 35 / 877 |
| Topik hasil klasterisasi | 5 | 5 |
| Fakta SPO (entitas) dari paper representatif topik | 29 (33) | 25 (34) |
| Indikator lolos validasi | 3 | **4** |
| Verdict Rule Engine | 3 PASS, 0 FLAG, 0 REJECT | 4 PASS, 0 FLAG, 0 REJECT (RERR 0%) |
| Indikator ditahan untuk peninjauan (M10) | 1 dari 3 | **1 dari 4** (kutipan tidak terambil) |
| Rantai provenans lengkap (M11) | 2 dari 3 | 3 dari 4 (yang ke-4 ditahan) |
| Waktu total | 714 s | 705 s (~11,8 menit) |

Jumlah chunk turun dari 3.095 (Agustus) menjadi 877 karena *chunker* baru
memotong pada batas kalimat dengan overlap konsisten — bukan karena isi korpus
berubah (jurnal identik, 0 duplikat).

#### Tabel 4.7: Indikator pada Eksekusi 2 (topik 1, "Forensik Digital dan Ekstraksi Bukti Digital")

| # | Indikator | Metode deteksi | Confidence mentah → terkalibrasi | Verdict | Kutipan / jurnal terkutip | Korroborasi penulis | Status |
|---|-----------|----------------|----------------------------------|---------|---------------------------|---------------------|--------|
| 1 | Fragmentasi | Kopling bibliografis (bebas LLM) | 0,828 → 0,911 | PASS | 3 / 10 (26 jurnal terkait) | — (tidak berlaku) | Disajikan |
| 2 | Ketidaklengkapan kolektif | Peta cakupan aspek: 10/10 aspek kritis tidak dibahas 10 jurnal; 9 ber-*grounding* korpus, 1 ditandai parametrik | 0,750 → 0,825 | PASS | 3 / 7 | **1** pernyataan (tersirat, skor 0,69) | Disajikan |
| 3 | Fragmentasi | Isolasi struktural *embedding* (skor 0,82) | 0,720 → 0,792 | PASS | 0 / 7 | — | **Ditahan** (kutipan hilang) |
| 4 | Ketiadaan dukungan bukti | 3/3 klaim tanpa paragraf bukti primer di jurnal lain; 1 *citation echo* | 0,650 → 0,715 | PASS | 3 / 3 | **3** pernyataan (tersirat, skor 0,68–0,71) | Disajikan |

Tiga hal yang baru terlihat pada versi akhir:

1. **Indikator keempat akhirnya terdeteksi.** Ketiadaan dukungan bukti — yang
   pada Agustus tidak muncul sehingga usulan terkaitnya turun prioritas — kini
   terdeteksi dari tiga klaim pembuka ("penggunaan perangkat digital semakin
   meluas…") yang diasersikan lintas jurnal tanpa satu pun paragraf bukti
   primer di korpus (kemiripan terbaik 0,00 < 0,45), satu di antaranya berulang
   sebagai *citation echo*. Ini persis bentuk gap yang didefinisikan Subbab
   3.6.1: dibahas dan diklaim, tetapi tidak dibuktikan.
2. **Korroborasi penulis (M14) bekerja dan bersifat selektif.** Kanal samping
   memuat 31 kekurangan tersurat (16 jurnal) dan 84 kekurangan tersirat (32
   jurnal) hasil profil per jurnal. Dari dua indikator yang secara desain dapat
   dikorroborasi (ketidaklengkapan dan ketiadaan dukungan bukti; fragmentasi
   tidak memiliki "jarum" aspek), **keduanya (2/2)** memperoleh pernyataan
   penulis yang cocok — misalnya "jurnal tidak menampilkan metodologi empiris
   atau studi kasus konkret" menguatkan indikator ketiadaan dukungan bukti.
   Semua kecocokan berskor 0,68–0,71 (di atas ambang) dan seluruhnya berjenis
   *tersirat*; tidak ada kekurangan *tersurat* yang cocok, konsisten dengan
   Subbab 3.6.2 bahwa korroborasi adalah **bukti**, bukan skor — confidence
   indikator tidak berubah karenanya. Pada eksekusi 1, kedua indikator yang
   sama tidak memperoleh korroborasi (0/2): himpunan aspek yang dihasilkan LLM
   berbeda antar *run*, sehingga kecocokan dengan pernyataan penulis juga
   berubah — satu lagi alasan pelaporan k/n.
3. **Kopling bibliografis di dalam pipeline** mereplikasi hasil skrip
   terpisah pada Subbab 4.3.9 dengan penguraian yang sedikit lebih baik: 31
   jurnal memiliki daftar pustaka terurai, 26 memenuhi syarat (≥ 5 entri), 5
   dilewati; 19 komponen (terbesar 4 jurnal), 318 dari 325 pasangan terputus
   (isolasi 0,978), modularitas 0,70, 6 karya rujukan dibagi ≥ 2 jurnal, dan
   **3** sitasi langsung terverifikasi (1 via DOI, 2 via penulis-tahun-judul;
   bertambah satu dari Agustus karena pencocokan penulis-tahun). Indikator ini
   menjadi yang berkeyakinan tertinggi (0,911) dan sepenuhnya dapat diaudit
   tanpa LLM.

**Stabilitas dua realisasi.** Ketiga indikator eksekusi 1 muncul kembali pada
eksekusi 2 dengan metode deteksi dan besaran yang serupa (kopling: 0,878 vs
0,828; cakupan: 0,740 vs 0,750; isolasi: 0,711 vs 0,720), sedangkan indikator
ketiadaan dukungan bukti hanya muncul pada eksekusi 2 — sehingga 3 dari 4
temuan stabil pada 2/2 *run* dan 1 temuan berstatus 1/2. Kelima usulan judul pada eksekusi 2 berada pada *band sweet spot* (kebaruan
0,32–0,47); pada eksekusi 1, empat di antaranya *sweet spot* dan satu jatuh ke
*band derivative* (0,24), yang menunjukkan penyaring kebaruan memang membedakan.
Pada eksekusi 2 usulan yang berjangkar pada ketiadaan dukungan bukti naik ke
prioritas *high* karena indikatornya kini benar-benar terdeteksi.
Indikator ketidaklengkapan **metodologis** (tahap metode homogen, Subbab
3.6.2) tidak menyala pada kedua eksekusi — berbeda dari Agustus ("10 jurnal
memakai *case study*"): profil tahap metode per jurnal tidak disertakan pada
jalur analisis ini, sehingga pemeriksaan jatuh ke *fallback* kata kunci yang
menemukan lebih dari satu metode pada topik tersebut dan, sesuai gerbangnya,
tidak memancarkan indikator.

**Cacat yang terungkap eksekusi 1 dan perbaikannya.** Pada eksekusi 1, ketiga
indikator dilaporkan `PASS` namun keyakinan terkalibrasinya justru turun
(0,878 → 0,702; faktor ×0,80). Penelusuran menunjukkan Rule Engine berjalan dua
kali dengan pengait fakta yang berbeda: di dalam analyzer (verdict `FLAG` "bukti
tidak cukup" pada C3/K3, yang langsung difusikan ke kalibrasi) dan di
koordinator (verdict akhir `PASS` pada klaim yang diperkaya), tetapi verdict
akhir hanya menimpa label — bukan kalibrasi dan provenansnya. Rekaman keluaran
dengan demikian bertentangan dengan dirinya sendiri. Perbaikan: koordinator
kini **memfusikan ulang** verdict final ke kalibrasi, abstensi, dan rantai
provenans (dengan alasan abstensi berbasis provenans tetap dipertahankan),
disertai empat uji regresi (`tests/test_coordinator_calibration_refresh.py`).
Eksekusi 2 dijalankan setelah perbaikan ini; seluruh angka pada Tabel 4.7
berasal darinya. Cacat ini termasuk kelas yang sama dengan tiga cacat pada
Subbab 4.3.8: *silent*, tidak tertangkap uji sintetis, dan hanya terlihat pada
korpus nyata.

### 4.3.12 Mode *Cross-Critic* (H10) dan Topik Kontrol Negatif

Mode *cross-critic* (Subbab 3.7.4) menambahkan LLM kritikus dari model berbeda
(`gpt-oss` 13B) yang mengaudit setiap indikator keluaran model utama
(`llama3.2` 3B) terhadap empat kriteria — antar-paper, *grounded*, spesifik,
terkalibrasi — dan memberi model utama kesempatan membela indikator yang
ditolak dengan bukti konkret. Setelah tiga eksekusi pilot pada satu topik
(hasilnya tidak konsisten: 0/5, 0/5, dan 4/5 kandidat ditolak pada *seed* yang
sama), mode ini dijalankan dengan protokol multi-run penuh: **5 *run*** (seed
43–47) pada keempat topik benchmark **ditambah satu topik kontrol negatif**
(TC: *"quantum biology in marine ecosystems"*, sengaja tidak ada di korpus).

#### Tabel 4.8: Hasil Mode *Cross-Critic* per *Run* (5 *run*, 4 topik + TC)

| Seed | Kandidat indikator | Ditolak kritikus | Dibela & dipertahankan | Indikator akhir (T1–T4) | Indikator palsu pada TC | Confidence rerata | Waktu (s) |
|-----:|-------------------:|-----------------:|-----------------------:|------------------------:|------------------------:|------------------:|----------:|
| 43 | 30 | 26 (86,7%) | 3 | 4 | 0 | 0,918 | 668 |
| 44 | 31 | 30 (96,8%) | 1 | 1 | 0 | 0,991 | 645 |
| 45 | 30 | 19 (63,3%) | 3 | 11 | 0 | 0,829 | 734 |
| 46 | 31 | 29 (93,5%) | 2 | 0 | **1** (confidence 0,885) | 0,850 | 1.092 |
| 47 | 31 | 27 (87,1%) | 4 | 4 | 0 | 0,833 | 892 |
| **Total / rerata** | **153** | **131 (85,6%)** | **13** | **4,2 ± 4,1 per run** | **0,2 ± 0,45 per run** | **0,884 ± 0,070** | 806 |

#### Uji H10: `cross-critic` vs `nli`

| Variabel | U | p | p Holm (keluarga 8 uji) | Signifikan (α=0,05) | Effect size |
|----------|---|---|--------------------------|----------------------|-------------|
| Indikator/run | 0 | 0,0053 | **0,0428** | **ya** | δ=−1,0 (large); Δmed=−19 [−26, −12] |
| Confidence/run | 35 | 0,0057 | **0,0428** | **ya** | δ=1,0 (large); Δmed=0,059 [0,029, 0,200] |

**H10 terkonfirmasi dalam arah yang dihipotesiskan**: audit silang oleh model
berbeda memangkas jumlah indikator secara drastis (24,3 → 4,2 per *run*;
85,6% kandidat ditolak) dan yang bertahan berkeyakinan lebih tinggi (0,791 →
0,884). Dengan kata lain kritikus eksternal bertindak sebagai penyaring presisi
yang jauh lebih agresif daripada Rule Engine (RERR 0–4%). Apakah indikator yang
dibuang memang palsu — yaitu apakah pemangkasan ini menaikkan *precision* tanpa
mengorbankan *recall* — tidak dapat dijawab tanpa label pakar; yang dapat
dikatakan adalah kritikus mengubah keseimbangan ke arah "sedikit tetapi
yakin".

**Kontrol negatif.** Pada topik yang tidak ada di korpus, sistem berkalibrasi
seharusnya tidak menemukan apa pun. Pada 4 dari 5 *run* itulah yang terjadi
(0 indikator palsu); pada satu *run* (seed 46) satu indikator palsu **lolos
seluruh lapisan** — LLM utama, Rule Engine, dan kritikus — dengan confidence
0,885, lebih tinggi daripada rerata indikator sahih pada *run* yang sama.
*False-gap rate* mode ini 0,2 ± 0,45 per *run*. Satu kasus ini penting justru
karena keyakinannya tinggi: ia menunjukkan bahwa tanpa kutipan verbatim yang
dapat diverifikasi (yang tidak mungkin ada untuk topik fiktif) keyakinan model
tidak dapat dipercaya — dan menjadi argumen empiris paling kuat untuk syarat
rantai provenans pada Subbab 3.7.1. Kontrol negatif **hanya** dieksekusi pada
mode *cross-critic*; *false-gap rate* mode `full` dan `nli` belum diukur dan
dicatat sebagai keterbatasan (Subbab 4.4.3).

Variabilitas antar *run* tetap besar (1–11 indikator akhir; simpangan baku
hampir sebesar rerata). Ini konsisten dengan pilot: keputusan kritikus
*reasoning* itu sendiri stokastik, sehingga keluaran mode ini pun harus dibaca
dengan k/n dan tidak boleh dilaporkan dari satu eksekusi.

## 4.4 Pembahasan

### 4.4.1 Evaluasi terhadap Pertanyaan Penelitian

Bagian ini menjawab tiga pertanyaan penelitian sebagaimana dirumuskan pada
BAB I Subbab 1.2 (pola *fenomena → kesenjangan → pertanyaan*), dengan
membedakan secara tegas apa yang **terbukti** oleh eksperimen pada bab ini
dan apa yang **belum terukur**.

**RQ1 — Sejauh mana pendekatan *agentic multi-step reasoning* yang dilengkapi
*rule-based validation* mampu mendeteksi indikator *synthesis gap*?**

*Yang terbukti.* Keempat indikator dapat dioperasionalkan dan dideteksi pada
dokumen nyata dengan rantai bukti yang dapat ditelusuri. Pada korpus benchmark
(23 paper, 4 topik) sistem menghasilkan 14 indikator (Tabel 4.1; 42,9%
ketidaklengkapan, 28,6% fragmentasi, 28,6% inkonsistensi) dengan 248 fakta SPO
sebagai landasan penalaran. Pada korpus aplikatif 35 jurnal forensika digital,
versi akhir sistem menghasilkan tiga indikator yang lolos validasi — dua
fragmentasi dan satu ketidaklengkapan kolektif — yang **saling menguatkan dari
tiga sinyal independen**: kopling bibliografis bebas-LLM (26 jurnal terpecah
dalam 19 kelompok tanpa rujukan bersama; 318 dari 325 pasangan terputus),
isolasi struktural berbasis *embedding* (skor 0,81), dan peta cakupan aspek
(9 dari 10 aspek kritis tidak dibahas satu pun jurnal). Indikator ketiadaan
dukungan bukti tidak terdeteksi pada korpus ini, dan sistem **tidak**
memaksakan usulan yang berjangkar padanya (prioritas turun ke 0,367).
Kemampuan ini bertahan pada dua bahasa (Indonesia dan Inggris) setelah
*embedder* diganti ke model multibahasa.

*Batasnya.* Jumlah indikator per topik kecil (2–4) dan, untuk temuan yang
bergantung pada LLM, hanya 58% pernyataan gap muncul kembali pada ≥ 2 dari 3
*run* identik (M13) — sehingga "sejauh mana" harus dijawab dengan sebaran,
bukan satu angka. Indikator inkonsistensi adalah yang paling lemah (confidence
0,50 pada benchmark; tidak terdeteksi pada korpus aplikatif) karena kontradiksi
antar-temuan memerlukan klaim yang benar-benar sebanding, yang jarang ada pada
korpus heterogen. Ukuran akhir "sejauh mana" — *Precision/Recall/F1* terhadap
*gold standard* pakar (Subbab 3.7.1) — **belum dapat dilaporkan** karena sesi
penilaian pakar belum terlaksana (Subbab 4.4.5); yang dilaporkan bab ini adalah
kemampuan deteksi yang terverifikasi bukti, bukan akurasinya terhadap penilaian
manusia.

**RQ2 — Bagaimana mekanisme pembeda asosiasi semantik–hubungan logis dan
*rule-based validation* memengaruhi akurasi dan *false discovery rate*?**

*Yang terbukti.* (a) Lapisan pembeda tiga lapis bekerja sebagaimana dirancang:
sinyal NLI *cross-encoder* terdedikasi meningkatkan jumlah indikator terdeteksi
(Δmedian = 8 per *run*) dan confidence-nya secara signifikan (p Holm = 0,0428;
Cliff's δ = 1,0; H9), dan indikator yang bersumber dari asosiasi semantik
semata konsisten diberi `requires_human_validation = True`. (b) Lapisan
validasi simbolis terbukti **diskriminatif**: 6 dari 6 klaim adversarial
mendapat verdict sesuai harapan, dengan penurunan confidence terbesar pada
pelanggaran kelayakan keras (F1, F3: −0,60) dan moderat pada pelanggaran yang
memerlukan telaah manusia (C1: −0,15; K1: −0,20). (c) Fusi verdict ke dalam
keyakinan terkalibrasi dan abstensi selektif membuat penolakan tidak hanya
biner: pada korpus aplikatif 1 dari 3 indikator ditahan untuk peninjauan karena
kutipannya tidak terambil, meskipun verdict-nya PASS.

*Batasnya.* Pengaruh terhadap **FDR** — inti RQ2 — belum dapat dikuantifikasi:
FDR = 1 − EAR memerlukan label pakar. Proksi kuantitatif yang tersedia (jumlah
indikator dan confidence pada mode `no-rule-engine`) tidak berbeda signifikan
(p Holm ≥ 0,48; H7), karena pada paper berkualitas tinggi Rule Engine memang
jarang menolak (RERR 0%). Bukti yang ada menunjukkan Rule Engine **mampu**
menurunkan FDR (ia menolak klaim yang salah), bukan **seberapa besar** ia
menurunkannya pada distribusi klaim nyata. Penyaring presisi yang jauh lebih
agresif ternyata adalah kritikus LLM kedua (H10): 85,6% kandidat ditolak,
indikator per *run* turun dari 24,3 menjadi 4,2 dengan keyakinan lebih tinggi
(p Holm = 0,0428). Namun pada topik kontrol negatif satu indikator palsu tetap
lolos ketiga lapisan dengan confidence 0,885 (Subbab 4.3.12) — bukti bahwa
validasi neural (kritikus) dan simbolis (Rule Engine) sama-sama tidak dapat
menggantikan syarat kutipan verbatim; hanya rantai provenans yang secara
prinsip menolak klaim tentang topik yang tidak ada di korpus.

**RQ3 — Apa batasan epistemologis pendekatan ini dibandingkan penalaran
logis-induktif peneliti manusia?**

Eksperimen mengonfirmasi dan mempertajam batasan yang dinyatakan pada BAB I
Subbab 1.5, dengan lima temuan empiris:

1. *Sistem mendeteksi, tidak menilai kebermaknaan.* Dua indikator
   ketidaklengkapan pada korpus forensik (Tabel 4.3) benar secara struktural —
   aspek tersebut memang tidak dibahas — tetapi apakah ketiadaannya **bermakna**
   sebagai gap riset hanya dapat diputuskan pakar; sistem sengaja berhenti pada
   label "indikator".
2. *Penalaran deduktif bergantung pada apa yang berhasil diekstrak.* Rule Engine
   hanya menalar atas fakta SPO yang ada (248 fakta dari 23 paper; 29 fakta dari
   korpus forensik). Klaim yang tidak terhubung ke entitas KG lolos secara
   *default*, bukan karena dinyatakan benar — verdict PASS 100% pada data bersih
   adalah konsekuensi cakupan fakta, bukan bukti kebenaran klaim.
3. *Stokastisitas adalah sifat, bukan gangguan.* Dengan Jaccard antar-run
   0,45–0,65 dan gap implisit yang hanya 41% stabil, sistem tidak memiliki
   "jawaban" tunggal atas korpus yang sama — berbeda dari peneliti yang dapat
   mempertanggungjawabkan satu sintesis. Pelaporan k/n adalah pengakuan formal
   atas batas ini.
4. *Sinyal paling andal adalah yang paling sederhana.* Kopling bibliografis dan
   kutipan verbatim (bebas LLM) memberikan bukti fragmentasi yang tidak
   bergantung pada model dan dapat diaudit; sedangkan "gap implisit" hasil
   inferensi LLM adalah keluaran paling tidak stabil dan paling kurang spesifik
   (LLM-judge 2,75/5 terhadap kurator manusia).
5. *Tidak dapat menjelaskan "mengapa".* Sistem mendeteksi bahwa jurnal tidak
   saling mengutip, bukan mengapa komunitas riset terpecah; ia mendeteksi bahwa
   temuan bertentangan, bukan desain eksperimen mana yang menyebabkannya.
   Adjudikasi kontradiksi versus heterogenitas (Cochran Q, I²) hanya memisahkan
   kasus yang secara statistik dapat dipisahkan.

Posisi yang ditegaskan hasil ini sama dengan BAB I Subbab 1.5.3: sistem adalah
*decision support tool* yang mempersempit ruang pencarian dan menyediakan bukti
yang dapat diaudit, sementara penilaian induktif tetap pada peneliti.

**Ringkasan metrik.** Framework 14 metrik (M1–M14) berhasil diterapkan pada dua
korpus. Korpus benchmark (M1–M8): 14 indikator; distribusi 42,9/28,6/28,6%;
confidence rerata 0,700; PASS 100%, RERR 0%; 1.757 s (98,7% ekstraksi fakta);
100% indikator berlabel butuh validasi manusia; akurasi adversarial 6/6. Korpus
aplikatif (M9–M14, Subbab 4.3.8–4.3.11): kalibrator identitas (label pakar 0);
abstensi selektif 0/2 (Agustus) dan 1/3 (versi akhir); provenans lengkap 100%
untuk indikator yang disajikan; 5/5 usulan pada *band sweet spot*; stabilitas
k/n 58,1%; korroborasi penulis 2 dari 2 indikator yang dapat dikorroborasi
(4 pernyataan penulis, Subbab 4.3.11); eksekusi ulang versi akhir: 4 indikator
(semua tipe kecuali inkonsistensi), 1/4 ditahan untuk peninjauan. Metrik
berbasis pakar (EAR, LCS, AS, FDR, SHG, REP) belum terukur; statusnya dirinci
pada Subbab 4.4.5.

### 4.4.2 Keunggulan Pendekatan Neuro-Symbolic

Berdasarkan hasil eksperimen, keunggulan pendekatan Neuro-Symbolic dibandingkan pipeline RAG+LLM konvensional:

1. **Transparansi**: Setiap indikator gap memiliki *reasoning trace* yang dapat ditelusuri, berbeda dengan output "kotak hitam" LLM biasa.

2. **Validasi Berlapis**: Rule Engine menyediakan lapisan verifikasi independen yang tidak bergantung pada LLM, mengurangi risiko halusinasi yang lolos ke output akhir.

3. **Klaim yang Terkalibrasi**: Sistem secara eksplisit menyatakan bahwa output adalah "indikator gap" yang memerlukan validasi manusia, bukan "kesenjangan riset definitif".

4. **Performa Rule Engine**: Validasi simbolis beroperasi dalam <0.01 detik, membuktikan bahwa penambahan lapisan logis tidak menambah *overhead* signifikan.

5. **Sinyal Struktural Bebas-LLM**: Kopling bibliografis dan kutipan verbatim memberi bukti fragmentasi yang tidak bergantung pada model bahasa mana pun dan dapat diaudit langsung dari daftar pustaka — pada korpus forensik sinyal ini menjadi indikator dengan keyakinan tertinggi (Subbab 4.3.9 dan 4.3.11).

6. **Kejujuran Statistik**: Setiap temuan yang bergantung pada LLM dilaporkan bersama frekuensi kemunculannya k/n; pipeline RAG+LLM konvensional melaporkan satu eksekusi sebagai hasil.

### 4.4.3 Keterbatasan yang Ditemukan

1. **Kualitas Ekstraksi Fakta**: Kendala awal parsing JSON dari output LLM (yang
   sempat menghasilkan 0 fakta SPO) telah diatasi melalui tiga mekanisme:
   (a) *structured output* JSON mode Ollama, (b) *retry* dengan prompt lebih
   ketat, dan (c) *salvage parser* untuk respons terpotong akibat batas token.
   Namun demikian, *kebenaran* fakta yang terekstrak tetap perlu diukur —
   presisi ekstraksi dievaluasi melalui anotasi manual sampel acak
   (`experiments/annotate_facts.py`) dan dilaporkan terpisah.

2. **Sensitivitas Model**: Eksperimen utama menggunakan model 3B parameter
   (`llama3.2`). Komparasi dengan model 13B (`gpt-oss`) dilakukan untuk
   mengukur sensitivitas hasil terhadap kapasitas model.

3. **Cakupan Dataset**: 23 paper benchmark dalam 4 topik masih terbatas pada
   domain *computer science* (2014–2021). Generalisasi ke domain lain
   (kedokteran, sosial) memerlukan validasi tambahan.

4. **Evaluasi Pakar Tertunda**: Metrik berbasis pakar (EAR, LCS, AS, FDR, SHG,
   REP) belum diukur — instrumen penilaian (form XLSX + kalkulator metrik)
   telah disiapkan di `experiments/expert_eval/` dan menunggu sesi penilaian
   pakar terhadap output final sistem. Konsekuensi langsungnya, kalibrator
   temperature scaling masih beroperasi sebagai pemetaan identitas
   (`temperature = 1,0`) karena himpunan label pakar belum mencapai
   `MIN_CALIBRATION_LABELS = 4`, sehingga ECE, Brier, dan AURC (M9) belum dapat
   dilaporkan. Sistem menampilkan status ini secara eksplisit di antarmuka
   alih-alih menyajikan angka kalibrasi yang belum tervalidasi.

5. **Kalibrasi Verdict pada Data Bersih**: Pada indikator yang dihasilkan dari
   paper benchmark berkualitas tinggi, Rule Engine cenderung memberi verdict
   PASS. Untuk membuktikan lapisan validasi benar-benar mendiskriminasi (bukan
   meloloskan semua input), eksperimen dilengkapi **fase validasi adversarial**:
   6 klaim yang dirancang melanggar aturan spesifik disuntikkan ke FactTable
   terisolasi, dan verdict aktual dibandingkan dengan verdict yang diharapkan
   (lihat Subbab 4.3.4). Threshold penyesuaian confidence per aturan masih bersifat
   *rule-of-thumb* dan menjadi kandidat analisis sensitivitas pada penelitian
   lanjutan.

6. **Potensi Kontaminasi Pre-training**: Paper benchmark (Transformer, BERT,
   ResNet, dst.) adalah paper terkenal yang kemungkinan besar muncul dalam data
   pre-training LLM. Indikator gap yang dihasilkan dapat terpengaruh
   pengetahuan parametrik model, bukan murni dari korpus yang dianalisis. Ini
   merupakan ancaman validitas internal yang melekat pada semua sistem berbasis
   LLM dan dimitigasi sebagian oleh *grounding* RAG serta validasi simbolis.

7. **Cacat Terungkap Hanya pada Korpus Nyata**: Tiga cacat implementasi
   (asimetri istilah grounding–kutipan, indikator metodologis tanpa kutipan,
   dan peta bukti degeneratif — Subbab 4.3.8) tidak terdeteksi oleh uji sintetis dan
   seluruhnya bersifat *silent*. Temuan ini menunjukkan bahwa uji unit dengan
   data buatan tidak memadai untuk memvalidasi lapisan provenans: data buatan
   cenderung memakai frasa pendek dan matriks berukuran memadai, sehingga
   kondisi batas yang justru dominan pada dokumen nyata tidak pernah tersentuh.
   Mitigasinya adalah menambahkan uji regresi yang meniru bentuk data produksi
   secara spesifik, bukan sekadar bentuk yang valid.

8. **Heterogenitas LLM Antar-Kelompok Eksperimen**: Eksperimen benchmark dan
   ablasi memakai model lokal (`llama3.2` 3B, `gpt-oss` 13B), sedangkan korpus
   aplikatif memakai `claude-opus-4.8-fast` melalui GitHub Copilot SDK (Subbab
   4.2.5). Angka kedua kelompok karena itu **tidak boleh dibandingkan silang**;
   masing-masing hanya sahih di dalam kelompoknya. Pilihan ini diambil karena
   model lokal memungkinkan *seed* dan pengulangan untuk uji signifikansi,
   sementara model penyedia dibutuhkan agar dokumen berbahasa Indonesia
   terproses memadai. Penyedia eksternal juga tidak menjamin determinisme dan
   tidak mengekspos parameter *decoding*, sehingga stabilitas pada korpus
   aplikatif diukur secara empiris lewat k/n (Subbab 4.3.10), bukan dikendalikan.

9. **Kontrol Negatif Parsial dan *User Study* Tidak Dieksekusi**: Topik kontrol
   negatif (Subbab 3.7.4) hanya dieksekusi pada mode *cross-critic* (5 *run*,
   Subbab 4.3.12); *false-gap rate* mode `full` dan `nli` — konfigurasi yang
   sebenarnya dipakai pada korpus aplikatif — belum diukur, padahal satu
   indikator palsu berkeyakinan tinggi sudah terbukti dapat lolos. *User study*
   H8 (Subbab 3.7.4) tidak dilaksanakan. Keduanya bukan keterbatasan teknis —
   mode eksperimen sudah mendukung topik kontrol pada semua mode — melainkan
   keterbatasan waktu dan akses partisipan, dan dicatat sebagai pekerjaan
   lanjutan prioritas tinggi (BAB V).

10. **Angka Satu-Run Adalah Undian**: Stabilitas k/n (Subbab 4.3.10)
    menunjukkan hanya 58% pernyataan gap muncul kembali pada ≥ 2 dari 3 *run*
    identik. Seluruh angka pada bab ini yang berasal dari satu eksekusi LLM
    (termasuk jumlah indikator pada Tabel 4.1 dan Tabel 4.3) harus dibaca
    sebagai satu realisasi, bukan nilai harapan; hanya hasil multi-run (Subbab
    4.3.6 dan 4.3.10) yang membawa ukuran sebaran.

### 4.4.4 Perbandingan dengan Studi Terkait

| Aspek | Pipeline RAG+LLM Biasa | Wizard Research (Neuro-Symbolic) |
|-------|------------------------|----------------------------------|
| Validasi output | Tidak ada | 9 aturan dalam 3 kategori |
| Bukti validasi bekerja | N/A | Validasi adversarial 6 kasus (F1–F3, K1, C1 + kontrol) |
| Transparansi | Output langsung LLM | Reasoning trace + evidence |
| Klaim epistemologis | Sering terlalu kuat | Dibatasi pada "indikator" |
| Overhead validasi | N/A | <0.01 detik |
| Jenis output | "Research gaps" | "Gap indicators + human validation flag" |
| Representasi pengetahuan | Embedding saja | Embedding + SPO Knowledge Graph |
| Deteksi kontradiksi | LLM generatif (sirkuler) | Marker linguistik + NLI cross-encoder terdedikasi (opsional) + fakta KG |
| Keyakinan keluaran | Skor mentah LLM | Terkalibrasi + abstensi selektif + rantai provenans |
| Peringkat usulan | Urutan generasi LLM | Skor komposit gap × kebaruan × ketertindakan |

Dibandingkan dengan sistem seperti ResearchRabbit [2023] dan Elicit [2023] yang menggunakan pipeline RAG end-to-end, pendekatan Wizard Research menambahkan lapisan validasi simbolis yang memberikan jaminan tambahan terhadap kualitas output. Namun, sistem ini masih memerlukan validasi oleh pakar untuk mengukur akurasi aktual indikator gap.

### 4.4.5 Status Hipotesis dan Kriteria Keberhasilan

BAB III merumuskan sepuluh hipotesis (H1–H10), satu kontrol negatif, dan empat
kriteria keberhasilan (Subbab 3.7.5). Agar pembaca dapat menilai secara tepat
apa yang **sudah** dan **belum** dibuktikan, Tabel 4.9 memetakan setiap butir ke
bukti yang tersedia pada bab ini.

#### Tabel 4.9: Status Pengujian Hipotesis

| Hipotesis | Pengukur yang dijanjikan | Bukti pada BAB IV | Status |
|-----------|--------------------------|-------------------|--------|
| H1 — RAG mengurangi halusinasi vs LLM *standalone* | EAR pakar antar-konfigurasi | Tidak ada konfigurasi LLM *standalone* yang dijalankan; *grounding* verbatim 100% pada penambangan gap (4.3.10) dan provenans 100% (4.3.8) hanya bukti tidak langsung | **Tidak diuji** |
| H2 — analisis *multi-paper* lebih bermakna dari *single-paper* | EAR pakar | Sistem dirancang inheren *multi-paper*; tidak ada pembanding *single-paper* | **Tidak diuji** |
| H3 — KG menghasilkan indikator lebih didukung bukti | EAR/LCS pakar | Bukti kualitatif: 248 fakta SPO + *reasoning trace* per indikator vs 0 pada baseline (4.3.6); rantai provenans utuh 2/2 (4.3.8) dan 3/4 (4.3.11); korroborasi penulis 2/2 (4.3.11) | **Bukti kualitatif**, kuantifikasi menunggu pakar |
| H4 — EAR ≥ 50% | Penilaian pakar | Instrumen siap (`experiments/expert_eval/`), label belum terkumpul | **Tertunda** |
| H5 — LCS ≥ 3,5/5 | Penilaian pakar | Sama dengan H4 | **Tertunda** |
| H6 — *agentic* > *pipeline* linear | EAR pakar | Proksi kuantitatif (jumlah indikator & confidence, multi-run): tidak signifikan (p Holm ≥ 0,48); perbedaan kualitatif jelas — baseline tanpa fakta, verdict, dan jejak (4.3.6) | **Tidak signifikan pada proksi**; EAR tertunda |
| H7 — Rule Engine menurunkan FDR | FDR pakar (target turun ≥ 20%) | Kemampuan diskriminatif terbukti pada 6/6 kasus adversarial (4.3.5); RERR 0% pada data bersih; FDR aktual memerlukan label pakar | **Sebagian** (diskriminatif ya; FDR tertunda) |
| H8 — sistem mempercepat identifikasi gap | *User study within-subject* | Tidak dilaksanakan | **Tidak dilaksanakan** |
| H9 — lapisan NLI menambah kontradiksi terdeteksi | Multi-run + Mann–Whitney U | 7 vs 5 *run*, Δmedian = 8 indikator, p Holm = 0,0428, Cliff's δ = 1,0 (4.3.6) | **Terkonfirmasi** |
| H10 — *cross-critic* menurunkan indikator palsu | Multi-run *cross-critic* vs `nli` | 5 vs 7 *run*: 85,6% kandidat ditolak kritikus, indikator/run 24,3 → 4,2 (Δmed = −19, p Holm = 0,0428, δ = −1,0), confidence 0,791 → 0,884 (p Holm = 0,0428) — Subbab 4.3.12 | **Terkonfirmasi** (arah); apakah yang dibuang memang palsu menunggu pakar |
| Kontrol negatif — topik yang tidak ada di korpus | *False-gap rate* ≈ 0 | Mode *cross-critic*, 5 *run*: 0,2 ± 0,45 indikator palsu/run; 4/5 *run* bersih; 1 indikator palsu lolos dengan confidence 0,885 (4.3.12). Mode `full`/`nli` belum diukur | **Dieksekusi sebagian** (hanya *cross-critic*) |

Tiga hipotesis dasar (H1–H3) berasal dari proposal awal yang berorientasi pada
perbandingan konfigurasi; setelah revisi arsitektur, pertanyaan yang sama
dijawab lebih tajam oleh H6, H7, dan H9, sehingga H1–H2 tidak lagi memiliki
konfigurasi pembanding yang bermakna dalam sistem akhir. Hal ini dicatat sebagai
keterbatasan desain evaluasi, bukan dihapus dari catatan.

#### Tabel 4.10: Kriteria Keberhasilan (Subbab 3.7.5)

| Kriteria | Ambang | Hasil | Status |
|----------|--------|-------|--------|
| *Expert Acceptance Rate* | ≥ 50% | Belum diukur | Menunggu sesi pakar |
| *Logical Coherence Score* | ≥ 3,5/5 | Belum diukur | Menunggu sesi pakar |
| Penurunan FDR oleh Rule Engine | ≥ 20% | Belum diukur; diskriminasi adversarial 100% | Menunggu sesi pakar |
| *Rule Engine Precision* | ≥ 70% | Tidak ada REJECT pada data nyata (RERR 0%), sehingga REP tidak terdefinisi; 2/2 REJECT adversarial tepat | Tidak terdefinisi pada korpus ini |

Keempat kriteria bergantung pada label pakar yang belum terkumpul; **tidak satu
pun dapat dinyatakan terpenuhi atau gagal** pada tahap ini. Yang dapat
dinyatakan adalah bahwa seluruh prasyarat teknis untuk mengukurnya telah
tersedia dan diverifikasi: instrumen penilaian (formulir XLSX dengan rubrik
*genuine/trivial/illogical/already addressed*, LCS, AS, peringkat, dan
justifikasi REJECT), kalkulator metrik dengan Cohen's κ untuk ≥ 2 penilai, dan
kalibrator yang otomatis aktif setelah ≥ 4 label (Subbab 4.3.8). Kriteria
teknis yang tidak bergantung pada pakar seluruhnya terpenuhi: akurasi
adversarial 100%, kelengkapan provenans 100% untuk indikator yang disajikan,
abstensi selektif yang diskriminatif, kopling bibliografis bebas-LLM,
*false-gap rate* 0,2 per *run* pada topik kontrol (mode *cross-critic*), dan
pelaporan k/n untuk setiap temuan bergantung-LLM.
