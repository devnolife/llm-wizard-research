# RINGKASAN REVISI PROPOSAL TESIS

**Mahasiswa:** Andi Agung Dwi Arya B (D082251054)
**Program:** Magister Teknik Informatika — Universitas Hasanuddin
**Tanggal Kompilasi:** April 2026

---

## Daftar Isi

1. [Kronologi Revisi](#1-kronologi-revisi)
2. [Kritik Penguji & Respons](#2-kritik-penguji--respons)
3. [Perubahan Judul](#3-perubahan-judul)
4. [Revisi Rumusan Masalah](#4-revisi-rumusan-masalah)
5. [Revisi Definisi Synthesis Gap](#5-revisi-definisi-synthesis-gap)
6. [Perubahan Arsitektur](#6-perubahan-arsitektur)
7. [Komponen Baru: Rule-Based Validation Layer](#7-komponen-baru-rule-based-validation-layer)
8. [Komponen Baru: Knowledge Graph sebagai Fact Base](#8-komponen-baru-knowledge-graph-sebagai-fact-base)
9. [Komponen Baru: Mekanisme Pembeda Semantik vs Logis](#9-komponen-baru-mekanisme-pembeda-semantik-vs-logis)
10. [Batasan Epistemologis (Baru)](#10-batasan-epistemologis-baru)
11. [Revisi Framework Evaluasi](#11-revisi-framework-evaluasi)
12. [Revisi Tinjauan Pustaka](#12-revisi-tinjauan-pustaka)
13. [Ringkasan Perubahan per BAB](#13-ringkasan-perubahan-per-bab)
14. [Status Implementasi Sistem](#14-status-implementasi-sistem)

---

## 1. Kronologi Revisi

| Versi | Tanggal | File | Deskripsi |
|-------|---------|------|-----------|
| v0 | Des 2025 | `draf_proposal.pdf` | Draft proposal awal — pipeline linear RAG+LLM |
| v1.0 | 20 Des 2025 | `REVISI_PROPOSAL_OLD.md` | Revisi pertama — fokus Comparative Multi-Paper Analysis |
| v1.1 | 20 Des 2025 | `REVISI_PROPOSAL.md` | Koreksi fokus — bukan paper search, tapi analisis setelah papers ada |
| v2.0 | 2 Mar 2026 | `revisi.md` | **Master dokumen revisi** — respons menyeluruh terhadap 8 kritik FATAL penguji |
| v3.0 | 24 Mar 2026 | `drafts/PROPOSAL_REVISI_FINAL_v2.docx` | **Proposal final** — BAB I–V lengkap dengan seluruh revisi terintegrasi |

---

## 2. Kritik Penguji & Respons

Penguji menyampaikan **8 kritik FATAL** dalam 2 tahap:

### Tahap 1 — Fondasi Konseptual

| # | Kritik | Respons dalam Revisi |
|---|--------|---------------------|
| 1 | **Rumusan masalah bukan "masalah"** — hanya spesifikasi teknis berbentuk pertanyaan, bukan kesenjangan pengetahuan | Direvisi menggunakan pola FENOMENA → KESENJANGAN → PERTANYAAN. Kata kunci berubah dari "Bagaimana merancang..." menjadi "Sejauh mana..." |
| 2 | **Definisi synthesis gap tidak mainstream** — "Kombinasi Method A + Domain B" terlalu dangkal | Diganti dengan definisi Cooper (1998) & Booth (2012): fragmentasi, inkonsistensi, ketidaklengkapan kolektif |
| 3 | **Tidak dijelaskan bagaimana sistem semantik menarik research gap** — batas kemampuan LLM tidak diakui | Ditambahkan bagian Batasan Epistemologis yang eksplisit (BAB I §1.5) — sistem adalah *decision support tool*, bukan pengganti manusia |
| 4 | **RAG+LLM bukan sesuatu yang baru** — tidak ada kebaruan mendasar | Kebaruan digeser ke **Neuro-Symbolic Agentic System** — integrasi penalaran neural + simbolik, bukan sekadar pipeline |

### Tahap 2 — Arsitektur & Metodologi

| # | Kritik | Respons dalam Revisi |
|---|--------|---------------------|
| 5 | **Tidak bisa bedakan asosiasi semantik vs hubungan logis** | Ditambahkan mekanisme 3 lapis: Semantic Filtering → Evidence Extraction → Rule-Based Validation |
| 6 | **Perlu Rule-Based Validation Layer** | Ditambahkan Rule Engine dengan 9 aturan dalam 3 kategori (F1–F3, C1–C3, K1–K3) dan 3 verdict (PASS/FLAG/REJECT) |
| 7 | **Diagram alir terlalu linear & black box** | Direvisi menjadi 4 Fase: Ingestion → Fact Extraction → Agentic Analysis → Logical Consistency Checker |
| 8 | **Knowledge Graph tanpa Tabel Fakta SPO** | KG ditransformasi menjadi Fact Base dengan ontologi eksplisit: 8 tipe entitas, 12 predikat, tabel SPO |

### Pola Tuntutan Penguji

Penguji menuntut **3 hal fundamental:**

1. **KONSEPTUAL** — Perbaiki definisi synthesis gap dan akui batas kemampuan sistem
2. **KEBARUAN** — RAG+LLM pipeline biasa bukan kebaruan → perlu arsitektur berbeda (AI Agent + Rule Engine)
3. **PENALARAN** — Sistem tidak boleh hanya semantik → harus ada lapisan logika formal (Neuro-Symbolic)

---

## 3. Perubahan Judul

| Aspek | Lama | Baru |
|-------|------|------|
| **Judul** | "Intelligent Research Gap Analyzer: Sistem Otomatis Berbasis RAG dan LLM" | Pendekatan **Neuro-Symbolic Agentic** untuk Deteksi Indikator *Synthesis Gap* |
| **Paradigma** | Pipeline linear RAG+LLM | Arsitektur Agentic multi-step reasoning dengan validasi simbolik |
| **Posisi sistem** | "Sistem otomatis" | "Alat bantu keputusan (*decision support tool*)" |

---

## 4. Revisi Rumusan Masalah

### LAMA (Ditolak)

> "Bagaimana merancang arsitektur sistem berbasis RAG dan LLM yang mampu menganalisis beberapa jurnal untuk menemukan celah penelitian (synthesis gap) secara otomatis?"

**Mengapa ditolak:** Pertanyaan *engineer*, bukan pertanyaan *peneliti*. Tidak ada fenomena, tidak ada kesenjangan pengetahuan.

### BARU (Diterima)

Mengikuti pola **FENOMENA → KESENJANGAN → PERTANYAAN**:

**3 Pertanyaan Penelitian:**

1. **Sejauh mana** pendekatan *agentic multi-step reasoning* yang dilengkapi *rule-based validation* mampu mendeteksi indikator *synthesis gap* (fragmentasi, inkonsistensi, dan ketidaklengkapan kolektif) dalam literatur ilmiah?

2. **Bagaimana** mekanisme pembeda asosiasi semantik dan hubungan logis serta *rule-based validation* memengaruhi tingkat akurasi dan *false discovery rate* dalam deteksi indikator *synthesis gap*?

3. **Apa batasan-batasan epistemologis** pendekatan ini dibandingkan dengan penalaran logis-induktif yang dilakukan peneliti manusia?

---

## 5. Revisi Definisi Synthesis Gap

### LAMA (Ditolak)

```
Synthesis Gap — 3 Types:
  a. Unexplored Combinations (Method A + Domain B)
  b. Bridging Gaps (Concept X ↔ Concept Y)
  c. Resolution Gaps (Contradictions need resolution)
```

**Mengapa ditolak:** "Unexplored Combinations" = kawin silang dangkal — CNN + Medical Imaging bukan sintesis, itu hanya aplikasi. Definisi tidak ditemukan di literatur mainstream.

### BARU (Diterima)

Berdasarkan **Cooper (1998)** dan **Booth, Sutton & Papaioannou (2012)**:

> **Synthesis gap** = kondisi di mana literatur yang ada tentang suatu fenomena BELUM menghasilkan kesimpulan terpadu yang konklusif, baik karena fragmentasi, inkonsistensi, atau ketidaklengkapan kolektif.

**3 Indikator Terukur:**

| # | Indikator | Penjelasan | Contoh |
|---|-----------|------------|--------|
| 1 | **Fragmentasi** | Paper-paper membahas fenomena yang sama dari sudut berbeda tetapi tidak saling mengintegrasikan | 10 studi tentang dropout di online learning, masing-masing pakai teori berbeda, tidak ada yang menyatukan |
| 2 | **Inkonsistensi** | Temuan empiris saling bertentangan dan belum ada yang menyelesaikan | Paper A: gamification meningkatkan motivasi. Paper B: gamification menurunkan motivasi. Belum ada rekonsiliasi. |
| 3 | **Ketidaklengkapan Kolektif** | Aspek-aspek kritis dari fenomena belum dicakup secara bersama oleh literatur yang ada | Banyak studi efektivitas blended learning, tapi tidak ada yang membahas aspek equity/aksesibilitas |

**Yang BUKAN synthesis gap:**
- ❌ Kombinasi metode-domain yang belum pernah ada (itu hanya "belum diterapkan")
- ❌ Topik yang belum diteliti sama sekali (itu *knowledge gap*)
- ❌ Saran "future work" di akhir paper (itu *explicit gap*)

---

## 6. Perubahan Arsitektur

### LAMA — Pipeline Linear (Ditolak)

```
Input → PDF Parse → Chunk → Embed → RAG Retrieve → LLM Generate → Output
                                                      ↑
                                                (Black Box)
                                            Tidak ada validasi
```

### BARU — 4 Fase dengan Logical Consistency Checker

```
FASE 1: INGESTION
  Input Papers (3-10) → PDF Parser → Section Splitter → Chunk & Embed → Vector Store

FASE 2: FACT EXTRACTION
  Entity Extractor (SciSpaCy + LLM) → Fact Table Constructor → Knowledge Graph (Fact Base)

FASE 3: AGENTIC ANALYSIS  
  Agent Orchestrator (Plan → Act → Observe → Reflect → Repeat/Stop)
  Tools: RAG Retriever | Paper Analyzer | NLI Checker | KG Querier
  Output: Candidate gap indicators + evidence + reasoning (RAW — belum divalidasi)

FASE 4: LOGICAL CONSISTENCY CHECKER ← KOMPONEN BARU
  Rule Engine (Fact Base + Rule Base → Inference Engine)
  Verdict: ✅ PASS | ⚠️ FLAG | ❌ REJECT
  Output ke pengguna: Validated indicators + flagged items + confidence scores + reasoning trace
```

### Perbandingan Arsitektur

| Aspek | Pipeline Linear (Lama) | Agentic + Rule Engine (Baru) |
|-------|----------------------|----------------------------|
| **Proses** | Linear: Retrieve → Generate → selesai | Iteratif: Plan → Act → Observe → Reflect → Repeat |
| **Self-verification** | ❌ Tidak ada | ✅ Agent bisa cek ulang klaimnya sendiri |
| **Tool use** | Monolitik | Modular — panggil tool berbeda untuk sub-task berbeda |
| **Validasi logis** | ❌ Tidak ada | ✅ Rule Engine sebagai salah satu tool |
| **Kebaruan** | ❌ Sudah banyak implementasi | ✅ Agent + Rule Engine untuk synthesis gap = belum ada |

---

## 7. Komponen Baru: Rule-Based Validation Layer

Rule Engine bertugas menyaring output LLM sebelum disajikan ke pengguna.

### 3 Kategori × 3 Aturan = 9 Aturan Total

#### Kategori 1: Kelayakan (*Feasibility*) — F1, F2, F3

| ID | Aturan | Contoh |
|----|--------|--------|
| F1 | Kompatibilitas sumber daya | LLM sarankan "GPT-4 untuk edge device" → **DITOLAK** |
| F2 | Kompatibilitas data | "Supervised DL untuk rare disease" (data scarce) → **FLAG** |
| F3 | Kompatibilitas skala | "In-memory processing untuk big data" → **DITOLAK** |

#### Kategori 2: Kausalitas (*Causality*) — C1, C2, C3

| ID | Aturan | Contoh |
|----|--------|--------|
| C1 | Bukti kausal minimal (≥2 sumber) | Hanya 1 paper menyebut hubungan → **DOWNGRADE** ke korelasi |
| C2 | Arah kausalitas benar | "Hasil eksperimen menyebabkan hipotesis" → **DITOLAK** |
| C3 | Confounding check | A→B tapi ada C yang mungkin menyebabkan keduanya → **FLAG** |

#### Kategori 3: Konsistensi (*Consistency*) — K1, K2, K3

| ID | Aturan | Contoh |
|----|--------|--------|
| K1 | Non-kontradiksi internal | Sistem rekomendasikan X di poin 1 tapi tolak X di poin 3 → **FLAG** |
| K2 | Konsistensi dengan fakta KG | Klaim tidak didukung fakta KG → **DOWNGRADE** confidence |
| K3 | Transitivitas | "A improves B" + "B improves C" tapi output bilang "A worsens C" → **FLAG** |

### 3 Kemungkinan Verdict

| Verdict | Arti | Aksi |
|---------|------|------|
| ✅ **PASS** | Output lolos semua aturan | Tampilkan ke pengguna dengan confidence score |
| ⚠️ **FLAG** | Melanggar aturan non-kritis | Tampilkan dengan peringatan "perlu review manusia" |
| ❌ **REJECT** | Melanggar aturan kritis | JANGAN tampilkan + berikan alasan penolakan |

---

## 8. Komponen Baru: Knowledge Graph sebagai Fact Base

### Perubahan Paradigma

| Aspek | Lama | Baru |
|-------|------|------|
| **Fungsi KG** | Alat visualisasi hubungan | **Fact Base** untuk penalaran formal |
| **Struktur** | Sekadar nodes & edges | Tabel Fakta SPO (Subject–Predicate–Object) |
| **Pemanfaatan** | Tidak digunakan untuk reasoning | Digunakan oleh Rule Engine untuk penalaran deduktif |

### Ontologi Entitas — 8 Tipe

| Tipe | Contoh |
|------|--------|
| METHOD | CNN, Random Forest, BERT |
| CONCEPT | Transfer Learning, Attention |
| DOMAIN | Medical Imaging, NLP |
| FINDING | "CNN achieves 95% accuracy" |
| DATASET | ImageNet, CIFAR-10 |
| METRIC | Accuracy, F1-Score |
| PAPER | ResNet (He et al., 2016) |
| CONSTRAINT | High compute, Low resource |

### Ontologi Relasi — 12 Predikat

USES_METHOD, PROPOSES, APPLIES_TO, ACHIEVES, REQUIRES_RESOURCE, REQUIRES_DATA, IMPROVES, CONTRADICTS, EXTENDS, EVALUATED_ON, HAS_CONSTRAINT, DISCUSSES

### Proses Transformasi Teks → Tabel Fakta

1. **Entity Extraction** (SciSpaCy + LLM) — identifikasi entitas ilmiah
2. **Relation Extraction** (LLM + Pattern Matching) — identifikasi hubungan
3. **Triple Construction & Validation** — bentuk SPO dan validasi terhadap aturan

### Contoh Tabel Fakta

Dari teks: *"We propose CNN for medical image segmentation, achieves 92.3% Dice on BraTS, requires >16GB GPU..."*

| Subject | Predicate | Object |
|---------|-----------|--------|
| Paper_Current | PROPOSES | CNN_Segmentation |
| CNN_Segmentation | APPLIES_TO | Medical_Image_Segmentation |
| CNN_Segmentation | ACHIEVES | Dice_92.3% |
| CNN_Segmentation | EVALUATED_ON | BraTS_Dataset |
| CNN_Segmentation | REQUIRES_RESOURCE | GPU_16GB+ |

**Fakta Turunan (Inferred):** CNN_Segmentation → INFEASIBLE_FOR → Edge_Deployment (via Rule F1)

---

## 9. Komponen Baru: Mekanisme Pembeda Semantik vs Logis

Menyelesaikan masalah: sistem tidak bisa bedakan "sering muncul bersama" (*co-occurrence*) vs "benar-benar berhubungan secara logis."

### 3 Jenis Hubungan

| Jenis | Definisi | Contoh | Deteksi via Semantik? |
|-------|----------|--------|----------------------|
| **Co-occurrence** | Sering muncul bersama, tanpa hubungan kausal | "Python" dan "machine learning" | ✅ Terdeteksi, tapi BUKAN hubungan logis |
| **Kausalitas** | A secara logis memengaruhi B | "Overfitting → need regularization" | ❌ Tidak bisa dari embedding saja |
| **Kontradiksi** | Temuan A bertentangan dengan B | "Method X meningkatkan akurasi" vs "Method X menurunkan akurasi" | ⚠️ Parsial via NLI |

### Mekanisme 3 Lapis

```
Kandidat hubungan (dari semantic similarity)
    │
    ▼
[Lapis 1] SEMANTIC FILTERING
    │  Similarity > threshold? → Ya: lanjut / Tidak: buang
    ▼
[Lapis 2] EVIDENCE EXTRACTION (LLM Agent)
    │  Cari bukti eksplisit dalam teks:
    │  • Penanda kausal: "causes", "leads to", "results in", "because"
    │  • Penanda kontradiksi: "however", "contradicts", "in contrast"
    │  • Tidak ada penanda → label "co-occurrence only"
    ▼
[Lapis 3] RULE-BASED VALIDATION
    │  Cek terhadap aturan logika di Fact Base (KG)
    │  Lolos → VALID RELATION / Tidak → REJECTED + alasan
```

---

## 10. Batasan Epistemologis (Baru)

Bagian ini **sepenuhnya baru** — proposal lama tidak pernah membahas batasan epistemologis.

### Apa yang DAPAT Dilakukan Sistem

| Kemampuan | Metode | Keyakinan |
|-----------|--------|-----------|
| Mendeteksi kesamaan topik antar-paper | Semantic similarity (SciBERT) | Tinggi |
| Mendeteksi terminologi berbeda untuk konsep sama | Clustering semantik | Tinggi |
| Mendeteksi klaim yang saling bertentangan | NLI + Rule Engine | Sedang–Tinggi |
| Mengidentifikasi aspek absen dari paper tertentu | Coverage gap analysis | Sedang |
| Memvalidasi kelayakan logis rekomendasi | Rule-Based Validation | Tinggi |

### Apa yang TIDAK DAPAT Dilakukan Sistem

| Keterbatasan | Alasan |
|-------------|--------|
| Menilai apakah kombinasi ide logis secara mendalam | Butuh penalaran kausal melampaui rule engine |
| Memahami **mengapa** temuan saling bertentangan | Butuh pemahaman konteks eksperimental mendalam |
| Menentukan apakah gap **bermakna** untuk dijadikan riset | Butuh *scientific judgment* |
| Melakukan **penalaran induktif** sejati | LLM = probabilistik, Rule Engine = deduktif — keduanya bukan induktif |

### Klaim yang TIDAK Dibuat

1. ❌ Sistem TIDAK mengklaim mampu menalar secara induktif
2. ❌ Sistem TIDAK mengklaim menemukan gap yang pasti valid
3. ❌ Sistem TIDAK mengklaim menggantikan proses review manusia
4. ❌ Sistem TIDAK mengklaim bahwa pemeringkatan gap bersifat absolut

### Posisi Sistem

Sistem = **alat bantu keputusan** (*decision support tool*). Input: paper-paper. Output: **indikator** synthesis gap (bukan synthesis gap final). Peneliti manusia = pengambil keputusan akhir.

---

## 11. Revisi Framework Evaluasi

### LAMA
Hanya mengukur Precision/Recall — seolah gap bisa dinilai benar/salah secara biner.

### BARU — 7 Metrik Tambahan

| # | Metrik | Deskripsi |
|---|--------|-----------|
| 1 | **Expert Acceptance Rate (EAR)** | % indikator yang dinilai pakar sebagai *genuine synthesis gap* |
| 2 | **Logical Coherence Score (LCS)** | Skor 1-5 dari pakar: apakah indikator logis/masuk akal |
| 3 | **Actionability Score (AS)** | Skor 1-5: apakah indikator cukup spesifik untuk ditindaklanjuti |
| 4 | **False Discovery Rate (FDR)** | % indikator yang ternyata bukan gap |
| 5 | **Semantic vs Human Gap (SHG)** | Korelasi Spearman ranking sistem vs ranking pakar |
| 6 | **Rule Engine Rejection Rate (RERR)** | % output LLM yang ditolak rule engine |
| 7 | **Rule Engine Precision (REP)** | Dari yang ditolak, berapa % memang pantas ditolak |

### Hipotesis Baru — H4 s.d. H8

| Hipotesis | Klaim yang Diuji |
|-----------|-----------------|
| H4 | Expert acceptance rate ≥ 50% |
| H5 | Logical coherence score ≥ 3.5/5 |
| H6 | Agentic system > Pipeline linear RAG+LLM (pada metrik acceptance rate) |
| H7 | Dengan Rule Engine > Tanpa Rule Engine (mengurangi false discovery rate) |
| H8 | Sistem mengurangi waktu identifikasi gap vs proses manual (user study) |

### Perubahan Ground Truth

| Lama | Baru |
|------|------|
| Pakar menentukan "expected gaps" → sistem dicocokkan | Pakar **JUGA** menilai output sistem |

Label penilaian pakar per indikator:
- ✅ **Genuine gap** — indikator valid
- ⚠️ **Trivial** — terlalu dangkal
- ❌ **Illogical** — cacat logika
- ⏭️ **Already addressed** — sudah dijawab di literatur

---

## 12. Revisi Tinjauan Pustaka

### 16+ Referensi Baru

| Kategori | Referensi |
|----------|-----------|
| **Synthesis & Literature Review** | Cooper (1998), Booth et al. (2012), Pare et al. (2015) |
| **Research Gap Identification** | Muller-Bloch & Kranz (2015), Robinson et al. (2011) |
| **Neuro-Symbolic AI** | Garcez et al. (2019), Marcus (2020) |
| **Batas Kemampuan LLM** | Marcus & Davis (2020), Bender & Koller (2020) |
| **Knowledge Graph** | Ji et al. (2021), Bosselut et al. (2019) |
| **Rule-Based Systems** | Buchanan & Shortliffe (1984), Giarratano & Riley (2005) |
| **NLI / Contradiction Detection** | Bowman et al. (2015), Williams et al. (2018) |
| **AI Agent** | Yao et al. (2023) |
| **Lainnya** | Ammar et al. (2018), Marshall et al. (2019) |

### Sub-bab Baru di BAB II

- §2.4 Batasan Penalaran LLM
- §2.5 Neuro-Symbolic AI
- §2.6 Knowledge Graph sebagai Fact Base
- §2.7 Rule-Based Expert Systems
- §2.8 Natural Language Inference (NLI)
- §2.9 AI Agent & Multi-Step Reasoning
- §2.10 Posisi Penelitian dalam Literatur

---

## 13. Ringkasan Perubahan per BAB

### BAB I — Pendahuluan

| Bagian | Perubahan |
|--------|-----------|
| Latar Belakang | Ditambah: penjelasan proses kognitif peneliti (Cooper, 1998), keterbatasan pipeline linear, kebutuhan pendekatan Neuro-Symbolic Agentic |
| Rumusan Masalah | **DITULIS ULANG TOTAL** — dari "Bagaimana merancang..." ke pola fenomena→kesenjangan→pertanyaan dengan 3 RQ |
| Tujuan | Disesuaikan: mengukur kemampuan, menganalisis pengaruh komponen, mengidentifikasi batasan epistemologis |
| Manfaat | Diperluas: manfaat teoretis (batas Neuro-Symbolic, operasionalisasi synthesis gap) + praktis |
| §1.5 Batasan Epistemologis | **BARU SEPENUHNYA** — tabel BISA/TIDAK BISA, posisi sebagai decision support, klaim yang TIDAK dibuat |
| Batasan Masalah | Diperjelas: domain CS (2015-2025), 3-10 papers/sesi, lightweight KG, 3 kategori rules |

### BAB II — Tinjauan Pustaka

| Perubahan | Detail |
|-----------|--------|
| Definisi synthesis gap | **DITULIS ULANG** — dari definisi naif ke Cooper (1998) + Booth (2012) dengan 3 indikator |
| Sub-bab baru | 7 sub-bab baru ditambahkan (§2.4–§2.10) |
| Referensi | 16+ referensi baru ditambahkan |
| Posisi penelitian | Ditambah perbandingan dengan pendekatan existing |

### BAB III — Metodologi

| Perubahan | Detail |
|-----------|--------|
| Diagram alir | **DITULIS ULANG TOTAL** — dari 3 tahap linear ke 4 fase dengan Logical Consistency Checker |
| Arsitektur agentic | **BARU** — Agent Orchestrator dengan 6 tools |
| Mekanisme pembeda | **BARU** — 3 lapis (Semantic → Evidence → Rule-Based) |
| Rule Engine | **BARU** — 9 aturan (F1-F3, C1-C3, K1-K3) + 3 verdict |
| Skema Fakta KG | **BARU** — ontologi 8 entitas + 12 predikat + contoh SPO |
| Framework evaluasi | **DIREVISI** — 7 metrik baru, hipotesis H4-H8, ground truth baru |

### BAB IV — Hasil dan Pembahasan (Draf)

| Isi | Detail |
|-----|--------|
| Hasil deteksi indikator | Per-indikator (fragmentasi, inkonsistensi, ketidaklengkapan) |
| Pengaruh Rule Engine | Komparasi dengan/tanpa rule engine |
| Analisis batasan | Identifikasi kasus-kasus di mana sistem gagal |

### BAB V — Kesimpulan dan Saran (Draf)

| Isi | Detail |
|-----|--------|
| Kesimpulan | Jawaban per-RQ |
| Keterbatasan | Batasan epistemologis yang teridentifikasi |
| Saran | Arah pengembangan: ontologi formal, LLM lebih besar, multi-bahasa |

---

## 14. Status Implementasi Sistem

### Komponen yang Sudah Diimplementasikan di Kode

| Komponen | File | Status |
|----------|------|--------|
| Agent Orchestrator (LangGraph) | `backend/app/core/agents/coordinator.py` | ✅ Implementasi |
| RAG Pipeline | `backend/app/core/retrieval/` | ✅ Implementasi |
| Gap Analyzer (3 indikator) | `backend/app/core/gap_detection/analyzer.py` | ✅ Implementasi |
| Rule Engine | `backend/app/core/validation/rule_engine.py` | ✅ Implementasi |
| Fact Table | `backend/app/core/knowledge/fact_table.py` | ✅ Implementasi |
| Fact Extractor (SPO) | `backend/app/core/knowledge/fact_extractor.py` | ✅ Implementasi (JSON mode + retry) |
| Recommendation Engine | `backend/app/core/recommendation/engine.py` | ✅ Implementasi |
| ChromaDB Vector Store | `chroma_db/` | ✅ Implementasi |
| Frontend Dashboard | `frontend/src/components/pages/AnalysisResults.jsx` | ✅ Implementasi |
| Experiment Runner + Ablation | `backend/experiments/run_experiment.py` (mode full / no-rule-engine / linear-baseline) | ✅ Implementasi |
| Dataset Benchmark | `research_papers/` — 23 paper, 4 topik (manifest tersedia) | ✅ Implementasi |
| Tooling Evaluasi Pakar | `backend/experiments/expert_eval/` (form XLSX + kalkulator metrik) | ✅ Implementasi |

### Kesesuaian Implementasi dengan Proposal Revisi

| Aspek Proposal | Implementasi | Kesesuaian |
|----------------|-------------|------------|
| 3 indikator Cooper (FRAGMENTATION, INCONSISTENCY, INCOMPLETENESS) | `IndicatorType` enum di `responses.py` | ✅ Sesuai |
| Rule Engine dengan verdict PASS/FLAG/REJECT | `RuleEngineReportModel` di `responses.py` + validasi adversarial (6 kasus, akurasi 100%) | ✅ Sesuai |
| Arsitektur Agentic | LangGraph-based coordinator | ✅ Sesuai |
| RAG grounding | ChromaDB + embedding | ✅ Sesuai |
| Knowledge Graph sebagai Fact Base | `fact_table.py` + `FactTableStats` | ✅ Sesuai |
| Mekanisme pembeda semantik vs logis | NLI + Evidence Extraction | ⚠️ Parsial |
| Ablation study (H6: agentic vs linear; H7: dengan/tanpa rule engine) | mode `linear-baseline` & `no-rule-engine` di experiment runner | ✅ Tooling siap |
| Evaluasi 7 metrik (EAR, LCS, AS, FDR, SHG, RERR, REP) | RERR otomatis di runner; EAR/LCS/AS/FDR/SHG/REP via `expert_eval/compute_metrics.py` | ✅ Tooling siap — menunggu penilaian pakar |
| User study (H8) | Belum dilakukan | ❌ Belum |

---

## Tabel Ringkasan: Sebelum vs Sesudah Revisi

| # | Aspek | SEBELUM | SESUDAH |
|---|-------|---------|---------|
| 1 | Judul | RAG + LLM otomatis | Neuro-Symbolic Agentic |
| 2 | Rumusan masalah | "Bagaimana merancang..." | "Sejauh mana..." |
| 3 | Definisi synthesis gap | Kombinasi Method+Domain | Cooper (1998): fragmentasi, inkonsistensi, ketidaklengkapan |
| 4 | Batasan epistemologis | Tidak ada | Eksplisit (BISA/TIDAK BISA) |
| 5 | Arsitektur | Pipeline linear 3 tahap | 4 Fase + Agentic + Rule Engine |
| 6 | Validasi logis | Tidak ada | Rule Engine (9 aturan, 3 kategori) |
| 7 | Knowledge Graph | Visualisasi saja | Fact Base (SPO triples) |
| 8 | Pembeda semantik vs logis | Tidak ada | Mekanisme 3 lapis |
| 9 | Evaluasi | Precision/Recall saja | 7 metrik + 8 hipotesis + user study |
| 10 | Posisi sistem | "Sistem otomatis" | "Decision support tool" |
| 11 | Referensi | 25 teknis | 40+ (termasuk fondasi konseptual) |
| 12 | Kebaruan | RAG+LLM (sudah banyak) | Neuro-Symbolic untuk synthesis gap (belum ada) |

---

*Dokumen ini merangkum seluruh revisi yang dilakukan dari proposal awal hingga versi final (v3.0). Sumber: `revisi.md`, `REVISI_PROPOSAL.md`, `REVISI_PROPOSAL_OLD.md`, `drafts/PERBANDINGAN_REVISI.md`, `drafts/BAB_I_PENDAHULUAN.md`–`BAB_V_KESIMPULAN_DAN_SARAN.md`, `drafts/NOVELTY_STATEMENT.md`, `drafts/REVIEW_KONSISTENSI.md`.*
