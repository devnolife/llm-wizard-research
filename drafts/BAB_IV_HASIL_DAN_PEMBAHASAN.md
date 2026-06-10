# BAB IV: HASIL DAN PEMBAHASAN

## 4.1 Implementasi Sistem

### 4.1.1 Arsitektur Sistem

Sistem Wizard Research diimplementasikan sebagai aplikasi web berbasis arsitektur *client-server* dengan pendekatan Neuro-Symbolic Agentic sesuai desain yang diuraikan pada BAB III. Arsitektur sistem terdiri dari empat lapisan utama:

1. **Lapisan Antarmuka (Frontend)**: Dibangun menggunakan React 19 dengan Vite sebagai *build tool* dan Tailwind CSS untuk styling. Terdiri dari 10 komponen React yang menangani upload paper, visualisasi hasil analisis, dan interaksi pengguna.

2. **Lapisan API (Backend)**: Dibangun menggunakan FastAPI (Python) dengan endpoint RESTful untuk ingestion dokumen, analisis gap, dan rekomendasi penelitian.

3. **Lapisan Agen (Agentic Core)**: Implementasi LangGraph untuk orkestrator multi-agen dengan pola *Observe → Think → Act → Evaluate*. Terdiri dari CoordinatorAgent, ResearchAnalyzerAgent, GapDetectorAgent, dan RecommenderAgent.

4. **Lapisan Penyimpanan**: ChromaDB sebagai vector database untuk *retrieval* semantik, dengan model embedding `all-MiniLM-L6-v2` dari Sentence-Transformers.

### 4.1.2 Komponen Neuro-Symbolic

Komponen inti yang membedakan sistem ini dari pipeline RAG+LLM konvensional:

| Komponen | Baris Kode | Deskripsi |
|----------|------------|-----------|
| Rule Engine (`rule_engine.py`) | 831 | Validasi logis dengan 9 aturan (F1-F3, C1-C3, K1-K3) |
| Fact Table (`fact_table.py`) | 430 | Penyimpanan fakta SPO (*Subject-Predicate-Object*) |
| Fact Extractor (`fact_extractor.py`) | 599 | Ekstraksi entitas dan relasi dari teks |
| Relation Classifier (`relation_classifier.py`) | 453 | Klasifikasi 3 jenis hubungan (kookurensi, kausal, kontradiksi) |
| Coordinator Agent (`coordinator.py`) | 737 | Orkestrator LangGraph dengan 5 tool agen |
| Gap Analyzer (`analyzer.py`) | ~400 | Deteksi 3 indikator gap (fragmentasi, inkonsistensi, ketidaklengkapan) |

**Total**: ~3.450 baris kode Python untuk komponen inti, dengan 197 unit test yang semuanya lulus.

### 4.1.3 Teknologi yang Digunakan

| Kategori | Teknologi | Versi | Fungsi |
|----------|-----------|-------|--------|
| Backend | Python + FastAPI | 3.10 / 0.109+ | API server dan logika bisnis |
| Frontend | React + Vite | 19.0 / 6.0 | Antarmuka pengguna |
| LLM | Ollama | 0.3+ | Inferensi model bahasa lokal |
| Vector DB | ChromaDB | 0.4.22+ | Penyimpanan dan retrieval embedding |
| Embedding | Sentence-Transformers | 2.2.2+ | Model `all-MiniLM-L6-v2` |
| Orchestration | LangGraph | 0.2+ | Workflow agen multi-langkah |
| Graph | NetworkX | 3.2.1+ | Knowledge graph SPO |
| Validasi | Pydantic | 2.5+ | Validasi data dan response model |

### 4.1.4 Statistik Implementasi

- **Total modul Python**: 25+ modul dalam 8 paket
- **Unit test**: 235+ test (Rule Engine, Fact Table, Relation Classifier, Fact Extractor, Gap Analyzer, Integration)
- **Test coverage**: Semua komponen Neuro-Symbolic tervalidasi, termasuk parsing JSON terstruktur (Ollama JSON mode + retry + salvage truncated array)
- **5 Tool Agen**: RAGTool, PaperAnalyzerTool, NLICheckerTool, KGQuerierTool, SelfCriticTool
- **Mode eksperimen**: `full`, `no-rule-engine` (ablasi H7), `linear-baseline` (ablasi H6)

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
| M2 | Distribusi Tipe Indikator | Proporsi Fragmentasi:Inkonsistensi:Ketidaklengkapan |
| M3 | Skor Kepercayaan (Confidence) | Rata-rata, min, max confidence per indikator |
| M4 | Verdict Rule Engine | Distribusi PASS/FLAG/REJECT |
| M5 | Waktu Eksekusi | Durasi per fase pipeline |
| M6 | Kebutuhan Validasi Manusia | Proporsi indikator yang membutuhkan verifikasi |
| M7 | RERR (*Rule Engine Rejection Rate*) | Persentase output LLM yang tidak lolos bersih (FLAG+REJECT) |
| M8 | Akurasi Adversarial | Persentase kasus adversarial dengan verdict sesuai harapan |

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

- **Hardware**: Server lokal
- **Model LLM**: `llama3.2:latest` (3B) dan `gpt-oss:latest` (13B) via Ollama — komparasi model
- **Embedding**: `all-MiniLM-L6-v2` (384 dimensi)
- **Parameter LLM**: temperature = 0.3, max_tokens = 2048, JSON mode (structured output) untuk ekstraksi fakta
- **Kedalaman analisis**: `standard` (fragmentasi + inkonsistensi + ketidaklengkapan)

---

## 4.3 Hasil Eksperimen

Hasil yang dilaporkan pada bagian ini berasal dari eksperimen konfigurasi penuh
(*full mode*) dengan model `llama3.2` (3B) terhadap korpus benchmark 23 paper,
kecuali dinyatakan lain. Hasil ablasi dan komparasi model dibahas pada §4.3.6.

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
Rule Engine, dilakukan validasi adversarial (§4.3.5).

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
§4.3.4 bukan karena Rule Engine meloloskan semua input.

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

---

## 4.4 Pembahasan

### 4.4.1 Evaluasi terhadap Pertanyaan Penelitian

**RQ1: Bagaimana merancang arsitektur Neuro-Symbolic Agentic yang mampu mengidentifikasi *synthesis gap*?**

Hasil eksperimen menunjukkan bahwa arsitektur empat fase yang dirancang (Ingestion → Fact Extraction → Agentic Analysis → Logical Checker) berhasil mengidentifikasi indikator gap dari kumpulan paper. Integrasi komponen neural (LLM untuk ekstraksi dan deteksi) dengan komponen symbolic (Rule Engine untuk validasi) memberikan kerangka kerja yang lebih terstruktur dibandingkan pipeline RAG+LLM konvensional.

**RQ2: Bagaimana membedakan asosiasi semantik dan hubungan logis?**

Relation Classifier dengan mekanisme 3 lapis (penanda linguistik, analisis struktural, verifikasi NLI) berhasil diimplementasikan. Pada eksperimen ini, indikator inkonsistensi yang terdeteksi oleh LLM secara tepat diberi label `requires_human_validation = True`, menunjukkan bahwa sistem tidak mengklaim hubungan logis yang belum terverifikasi.

**RQ3: Bagaimana mengevaluasi kualitas indikator gap?**

Framework evaluasi 8 metrik (M1-M8) berhasil diterapkan. Hasil menunjukkan:
- M1 (Jumlah indikator): 14 dari 4 topik (3–4 per topik)
- M2 (Distribusi): INCOMPLETENESS 42,9%, FRAGMENTATION 28,6%, INCONSISTENCY 28,6%
- M3 (Confidence): rata-rata 0,700 (di atas threshold 0,5)
- M4 (Rule Engine): 100% PASS pada data bersih; RERR 0,0%
- M5 (Waktu): 1.757 detik total (didominasi ekstraksi fakta 98,7%)
- M6 (Validasi manual): 100% indikator membutuhkan validasi manusia
- M7 (RERR baseline): baseline linear tidak memiliki mekanisme penolakan sama sekali
- M8 (Akurasi adversarial): 6/6 (100%) — Rule Engine terbukti diskriminatif

### 4.4.2 Keunggulan Pendekatan Neuro-Symbolic

Berdasarkan hasil eksperimen, keunggulan pendekatan Neuro-Symbolic dibandingkan pipeline RAG+LLM konvensional:

1. **Transparansi**: Setiap indikator gap memiliki *reasoning trace* yang dapat ditelusuri, berbeda dengan output "kotak hitam" LLM biasa.

2. **Validasi Berlapis**: Rule Engine menyediakan lapisan verifikasi independen yang tidak bergantung pada LLM, mengurangi risiko halusinasi yang lolos ke output akhir.

3. **Klaim yang Terkalibrasi**: Sistem secara eksplisit menyatakan bahwa output adalah "indikator gap" yang memerlukan validasi manusia, bukan "kesenjangan riset definitif".

4. **Performa Rule Engine**: Validasi simbolis beroperasi dalam <0.01 detik, membuktikan bahwa penambahan lapisan logis tidak menambah *overhead* signifikan.

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
   pakar terhadap output final sistem.

5. **Kalibrasi Verdict pada Data Bersih**: Pada indikator yang dihasilkan dari
   paper benchmark berkualitas tinggi, Rule Engine cenderung memberi verdict
   PASS. Untuk membuktikan lapisan validasi benar-benar mendiskriminasi (bukan
   meloloskan semua input), eksperimen dilengkapi **fase validasi adversarial**:
   6 klaim yang dirancang melanggar aturan spesifik disuntikkan ke FactTable
   terisolasi, dan verdict aktual dibandingkan dengan verdict yang diharapkan
   (lihat §4.3.4). Threshold penyesuaian confidence per aturan masih bersifat
   *rule-of-thumb* dan menjadi kandidat analisis sensitivitas pada penelitian
   lanjutan.

6. **Potensi Kontaminasi Pre-training**: Paper benchmark (Transformer, BERT,
   ResNet, dst.) adalah paper terkenal yang kemungkinan besar muncul dalam data
   pre-training LLM. Indikator gap yang dihasilkan dapat terpengaruh
   pengetahuan parametrik model, bukan murni dari korpus yang dianalisis. Ini
   merupakan ancaman validitas internal yang melekat pada semua sistem berbasis
   LLM dan dimitigasi sebagian oleh *grounding* RAG serta validasi simbolis.

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

Dibandingkan dengan sistem seperti ResearchRabbit [2023] dan Elicit [2023] yang menggunakan pipeline RAG end-to-end, pendekatan Wizard Research menambahkan lapisan validasi simbolis yang memberikan jaminan tambahan terhadap kualitas output. Namun, sistem ini masih memerlukan validasi oleh pakar untuk mengukur akurasi aktual indikator gap.
