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
- **Unit test**: 197 test (65 Rule Engine + 65 Fact Table + 44 Relation Classifier + 23 Integration)
- **Test coverage**: Semua komponen Neuro-Symbolic tervalidasi
- **5 Tool Agen**: RAGTool, PaperAnalyzerTool, NLICheckerTool, KGQuerierTool, SelfCriticTool

---

## 4.2 Skenario Pengujian

### 4.2.1 Dataset Pengujian

Eksperimen menggunakan 5 paper benchmark dari domain *deep learning* dan *computer vision*:

| No. | Paper | Penulis | Tahun | Ukuran | Chunks |
|-----|-------|---------|-------|--------|--------|
| 1 | Attention Is All You Need | Vaswani et al. | 2017 | 2.2 MB | 86 |
| 2 | BERT: Pre-training of Deep Bidirectional Transformers | Devlin et al. | 2019 | 775 KB | 139 |
| 3 | Generative Adversarial Nets | Goodfellow et al. | 2014 | 530 KB | 63 |
| 4 | Deep Residual Learning for Image Recognition | He et al. | 2016 | 819 KB | 129 |
| 5 | You Only Look Once (YOLO) | Redmon et al. | 2016 | 5.3 MB | 92 |

**Total**: 509 chunks teks, ~234.063 karakter dari 5 paper.

### 4.2.2 Topik Query Pengujian

Tiga topik query dipilih untuk merepresentasikan domain yang berbeda namun saling terkait:

1. **T1**: *"Deep learning architectures and optimization techniques"* — mencakup arsitektur dan optimasi
2. **T2**: *"Computer vision object detection and image recognition"* — fokus pada visi komputer
3. **T3**: *"Natural language processing and attention mechanisms"* — fokus pada NLP

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

### 4.2.4 Setup Eksperimen

- **Hardware**: Server lokal
- **Model LLM**: `llama3.2:latest` (3B parameter) via Ollama
- **Embedding**: `all-MiniLM-L6-v2` (384 dimensi)
- **Parameter LLM**: temperature = 0.3, max_tokens = 2048
- **Kedalaman analisis**: `standard` (mencakup fragmentasi + inkonsistensi + ketidaklengkapan)

---

## 4.3 Hasil Eksperimen

### 4.3.1 Hasil Ingestion dan Preprocessing (Fase 1)

Seluruh 5 paper berhasil diproses dan diindeks ke dalam ChromaDB:

| Paper | Chunks | Karakter | Waktu (s) |
|-------|--------|----------|-----------|
| Attention Is All You Need | 86 | 39.597 | ~2.0 |
| BERT | 139 | 64.067 | ~3.5 |
| Generative Adversarial Nets | 63 | 28.903 | ~1.5 |
| Deep Residual Learning | 129 | 59.288 | ~3.0 |
| YOLO | 92 | 42.208 | ~2.5 |
| **Total** | **509** | **234.063** | **~12.5** |

Rata-rata ukuran chunk: ~460 karakter dengan overlap 50 karakter, sesuai konfigurasi `chunk_size=512`.

### 4.3.2 Hasil Deteksi Gap (Fase 3)

Sistem berhasil mengidentifikasi **9 indikator gap** dari 3 topik query:

#### Tabel 4.1: Ringkasan Indikator Gap per Topik

| Topik | Total Indikator | Fragmentasi | Inkonsistensi | Ketidaklengkapan | Waktu (s) |
|-------|----------------|-------------|---------------|------------------|-----------|
| T1: Deep Learning Architectures | 3 | 1 | 1 | 1 | 6.48 |
| T2: Computer Vision | 3 | 1 | 0 | 2 | 5.92 |
| T3: NLP & Attention | 3 | 1 | 0 | 2 | 5.31 |
| **Total** | **9** | **3** | **1** | **5** | **17.71** |

#### Distribusi Tipe Indikator

```
Ketidaklengkapan (INCOMPLETENESS): 55.6% (5/9)
Fragmentasi (FRAGMENTATION):      33.3% (3/9)
Inkonsistensi (INCONSISTENCY):     11.1% (1/9)
```

Dominasi indikator ketidaklengkapan konsisten dengan definisi Cooper (1998) bahwa *synthesis gap* seringkali muncul karena aspek-aspek kritis yang belum diteliti secara kolektif oleh komunitas riset.

#### Tabel 4.2: Detail Indikator Gap — Topik T1 (Deep Learning Architectures)

| # | Tipe | Deskripsi | Confidence | Verdict |
|---|------|-----------|------------|---------|
| 1 | FRAGMENTATION | Literatur terfragmentasi ke dalam 9 kluster pendekatan berbeda tanpa kerangka integratif | 0.850 | PASS |
| 2 | INCOMPLETENESS | 10 aspek kritis tidak tercakup oleh seluruh paper yang dianalisis | 0.800 | PASS |
| 3 | INCONSISTENCY | Kontradiksi terdeteksi oleh LLM yang memerlukan verifikasi manual | 0.500 | PASS |

**Arah riset yang disarankan** (T1):
- Mengembangkan kerangka integratif yang menyatukan 9 pendekatan
- Investigasi: pilihan desain arsitektur (*layer types, activation functions, normalization*)
- Investigasi: algoritma optimasi (*SGD, Adam, RMSprop*)
- Investigasi: metode *hyperparameter tuning*

#### Tabel 4.3: Detail Indikator Gap — Topik T2 (Computer Vision)

| # | Tipe | Deskripsi | Confidence | Verdict |
|---|------|-----------|------------|---------|
| 1 | FRAGMENTATION | Literatur terfragmentasi ke dalam 10 kluster pendekatan berbeda | 0.850 | PASS |
| 2 | INCOMPLETENESS | 10 aspek kritis tidak tercakup (object detection, image recognition, deep architectures) | 0.800 | PASS |
| 3 | INCOMPLETENESS | Ketidaklengkapan metodologis: seluruh 10 paper menggunakan metodologi serupa | 0.600 | PASS |

#### Tabel 4.4: Detail Indikator Gap — Topik T3 (NLP & Attention)

| # | Tipe | Deskripsi | Confidence | Verdict |
|---|------|-----------|------------|---------|
| 1 | FRAGMENTATION | Literatur terfragmentasi ke dalam 10 kluster pendekatan berbeda | 0.850 | PASS |
| 2 | INCOMPLETENESS | 9 aspek kritis tidak tercakup (evolusi attention, tipe attention, aplikasi) | 0.800 | PASS |
| 3 | INCOMPLETENESS | Ketidaklengkapan metodologis: pendekatan alternatif tidak ditemukan | 0.600 | PASS |

### 4.3.3 Analisis Skor Kepercayaan (Confidence)

| Statistik | Nilai |
|-----------|-------|
| Rata-rata keseluruhan | 0.739 |
| Skor tertinggi | 0.850 |
| Skor terendah | 0.500 |
| Standar deviasi | ~0.126 |

Distribusi confidence per tipe indikator:

| Tipe Indikator | Rata-rata Confidence | Range |
|----------------|---------------------|-------|
| FRAGMENTATION | 0.850 | 0.850 (konsisten) |
| INCOMPLETENESS | 0.720 | 0.600 - 0.800 |
| INCONSISTENCY | 0.500 | 0.500 (satu data) |

**Interpretasi**: Indikator fragmentasi memiliki confidence tertinggi (0.850) karena diukur secara kuantitatif melalui clustering topik. Indikator inkonsistensi memiliki confidence terendah (0.500) karena sangat bergantung pada kemampuan LLM mendeteksi kontradiksi — sesuai dengan prinsip epistemologis bahwa LLM tidak melakukan penalaran logis sejati [Marcus, 2020].

### 4.3.4 Hasil Validasi Rule Engine (Fase 4)

| Metrik | Nilai |
|--------|-------|
| Total indikator dievaluasi | 9 |
| PASS | 9 (100%) |
| FLAG | 0 (0%) |
| REJECT | 0 (0%) |

Seluruh 9 indikator melewati validasi Rule Engine dengan verdict PASS. Ini menunjukkan:

1. **Aturan Kelayakan (F1-F3)**: Seluruh indikator memiliki bukti yang cukup, skor kepercayaan di atas threshold minimum, dan relevansi topik yang memadai.

2. **Aturan Kausalitas (C1-C3)**: Tidak ada indikator yang mengklaim hubungan kausal tanpa bukti memadai. Sistem berhasil membatasi klaim pada level "indikator" bukan "kesimpulan".

3. **Aturan Konsistensi (K1-K3)**: Tidak ada kontradiksi internal antar indikator yang terdeteksi.

**Catatan**: Tingkat PASS 100% pada dataset benchmark ini perlu divalidasi dengan dataset lebih besar dan beragam. Pada eksperimen skala penuh, diharapkan akan muncul FLAG dan REJECT yang menunjukkan efektivitas lapisan validasi.

### 4.3.5 Performa Waktu Eksekusi

| Fase | Waktu (s) | Persentase |
|------|-----------|------------|
| Ingestion & Preprocessing | 12.5 | 18.2% |
| Fact Extraction | 38.35 | 55.9% |
| Gap Detection (3 topik) | 17.71 | 25.8% |
| Rule Engine Analysis | <0.01 | <0.1% |
| **Total Pipeline** | **68.56** | **100%** |

Fase Fact Extraction mendominasi waktu eksekusi (55.9%) karena setiap paper memerlukan inferensi LLM individual untuk mengekstrak entitas dan relasi. Ini konsisten dengan temuan bahwa komponen neural (LLM) merupakan *bottleneck* utama, sementara komponen symbolic (Rule Engine) beroperasi hampir instan (<0.01 detik).

---

## 4.4 Pembahasan

### 4.4.1 Evaluasi terhadap Pertanyaan Penelitian

**RQ1: Bagaimana merancang arsitektur Neuro-Symbolic Agentic yang mampu mengidentifikasi *synthesis gap*?**

Hasil eksperimen menunjukkan bahwa arsitektur empat fase yang dirancang (Ingestion → Fact Extraction → Agentic Analysis → Logical Checker) berhasil mengidentifikasi indikator gap dari kumpulan paper. Integrasi komponen neural (LLM untuk ekstraksi dan deteksi) dengan komponen symbolic (Rule Engine untuk validasi) memberikan kerangka kerja yang lebih terstruktur dibandingkan pipeline RAG+LLM konvensional.

**RQ2: Bagaimana membedakan asosiasi semantik dan hubungan logis?**

Relation Classifier dengan mekanisme 3 lapis (penanda linguistik, analisis struktural, verifikasi NLI) berhasil diimplementasikan. Pada eksperimen ini, indikator inkonsistensi yang terdeteksi oleh LLM secara tepat diberi label `requires_human_validation = True`, menunjukkan bahwa sistem tidak mengklaim hubungan logis yang belum terverifikasi.

**RQ3: Bagaimana mengevaluasi kualitas indikator gap?**

Framework evaluasi 6 metrik (M1-M6) berhasil diterapkan. Hasil menunjukkan:
- M1 (Jumlah indikator): 3 per topik (konsisten)
- M2 (Distribusi): didominasi INCOMPLETENESS (55.6%)
- M3 (Confidence): rata-rata 0.739 (di atas threshold 0.5)
- M4 (Rule Engine): 100% PASS
- M5 (Waktu): 68.56 detik total
- M6 (Validasi manual): 100% indikator membutuhkan validasi manusia

### 4.4.2 Keunggulan Pendekatan Neuro-Symbolic

Berdasarkan hasil eksperimen, keunggulan pendekatan Neuro-Symbolic dibandingkan pipeline RAG+LLM konvensional:

1. **Transparansi**: Setiap indikator gap memiliki *reasoning trace* yang dapat ditelusuri, berbeda dengan output "kotak hitam" LLM biasa.

2. **Validasi Berlapis**: Rule Engine menyediakan lapisan verifikasi independen yang tidak bergantung pada LLM, mengurangi risiko halusinasi yang lolos ke output akhir.

3. **Klaim yang Terkalibrasi**: Sistem secara eksplisit menyatakan bahwa output adalah "indikator gap" yang memerlukan validasi manusia, bukan "kesenjangan riset definitif".

4. **Performa Rule Engine**: Validasi simbolis beroperasi dalam <0.01 detik, membuktikan bahwa penambahan lapisan logis tidak menambah *overhead* signifikan.

### 4.4.3 Keterbatasan yang Ditemukan

1. **Ekstraksi Fakta**: Modul fact extraction mengalami kendala parsing JSON dari output LLM, menghasilkan 0 fakta SPO. Ini menunjukkan kebutuhan *prompt engineering* yang lebih baik atau mekanisme *retry* dengan format yang lebih ketat.

2. **Sensitivitas Model**: Eksperimen menggunakan model 3B parameter (`llama3.2`). Model yang lebih besar mungkin menghasilkan deteksi inkonsistensi yang lebih akurat.

3. **Dataset Terbatas**: 5 paper benchmark belum merepresentasikan keragaman domain riset. Eksperimen skala penuh memerlukan 50-100 paper dari berbagai bidang.

4. **Tidak Ada Evaluasi Pakar**: Metrik *Expert Acceptance Rate* belum dapat diukur karena memerlukan evaluasi oleh pakar domain. Ini direncanakan untuk fase evaluasi penuh.

5. **Rule Engine PASS 100%**: Tingkat kelulusan sempurna mungkin menunjukkan threshold aturan yang terlalu longgar, atau paper benchmark yang berkualitas tinggi. Diperlukan kalibrasi dengan dataset yang lebih menantang.

### 4.4.4 Perbandingan dengan Studi Terkait

| Aspek | Pipeline RAG+LLM Biasa | Wizard Research (Neuro-Symbolic) |
|-------|------------------------|----------------------------------|
| Validasi output | Tidak ada | 9 aturan dalam 3 kategori |
| Transparansi | Output langsung LLM | Reasoning trace + evidence |
| Klaim epistemologis | Sering terlalu kuat | Dibatasi pada "indikator" |
| Overhead validasi | N/A | <0.01 detik |
| Jenis output | "Research gaps" | "Gap indicators + human validation flag" |
| Representasi pengetahuan | Embedding saja | Embedding + SPO Knowledge Graph |

Dibandingkan dengan sistem seperti ResearchRabbit [2023] dan Elicit [2023] yang menggunakan pipeline RAG end-to-end, pendekatan Wizard Research menambahkan lapisan validasi simbolis yang memberikan jaminan tambahan terhadap kualitas output. Namun, sistem ini masih memerlukan validasi oleh pakar untuk mengukur akurasi aktual indikator gap.
