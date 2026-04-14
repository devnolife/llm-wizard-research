# BAB III — METODOLOGI PENELITIAN

---

## 3.1 Desain Penelitian

Penelitian ini mengadopsi pendekatan *mixed methods* yang mengintegrasikan tiga komponen utama: (1) pengembangan sistem (*system development*), (2) evaluasi eksperimental (*experimental evaluation*), dan (3) penilaian pakar (*expert review*). Kombinasi ketiga pendekatan ini dipilih karena penelitian tentang *synthesis gap detection* tidak cukup hanya diukur secara kuantitatif melalui metrik otomatis, melainkan juga memerlukan validasi kualitatif dari pakar domain untuk menilai kebermaknaan (*meaningfulness*) indikator yang dihasilkan [Cooper, 1998; Booth et al., 2012].

### 3.1.1 Komponen Pengembangan Sistem

Pengembangan sistem mengikuti paradigma *design science research* [Hevner et al., 2004], di mana artefak yang dibangun — yaitu *Neuro-Symbolic Agentic System* — merupakan kontribusi utama penelitian. Sistem dirancang berdasarkan prinsip integrasi penalaran neural (LLM *agent*) dan penalaran simbolik (*rule engine* + *fact table*) sebagaimana diusulkan dalam kerangka *Neuro-Symbolic AI* [Garcez et al., 2019].

### 3.1.2 Komponen Evaluasi Eksperimental

Evaluasi eksperimental dilakukan melalui perbandingan beberapa konfigurasi sistem:

- **Konfigurasi 1:** *Pipeline* linear RAG+LLM (sebagai *baseline*)
- **Konfigurasi 2:** Arsitektur *agentic* tanpa *Rule Engine*
- **Konfigurasi 3:** Arsitektur *agentic* dengan *Rule Engine* (sistem penuh)

Perbandingan ini bertujuan mengisolasi kontribusi masing-masing komponen terhadap kualitas deteksi indikator *synthesis gap*.

### 3.1.3 Komponen Penilaian Pakar

Penilaian pakar (*expert review*) dilakukan untuk memvalidasi bahwa indikator yang dihasilkan sistem bersifat *genuine*, bukan sekadar artefak statistik atau korelasi semu. Pakar memberikan label terhadap setiap indikator: *genuine gap*, *trivial*, *illogical*, atau *already addressed* [Robinson et al., 2011].

### 3.1.4 Gambaran Umum Pendekatan Penelitian

```
┌──────────────────────────────────────────────────────────────┐
│                   DESAIN PENELITIAN                          │
│              (Mixed Methods — 3 Komponen)                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐  │
│  │  PENGEMBANGAN   │  │    EVALUASI      │  │  PENILAIAN │  │
│  │     SISTEM      │  │  EKSPERIMENTAL   │  │    PAKAR   │  │
│  │                 │  │                  │  │            │  │
│  │ Artefak:        │  │ Perbandingan:    │  │ Validasi:  │  │
│  │ Neuro-Symbolic  │  │ Pipeline vs      │  │ Expert     │  │
│  │ Agentic System  │  │ Agentic vs       │  │ labeling   │  │
│  │                 │  │ Agentic+Rules    │  │ per output │  │
│  └────────┬────────┘  └────────┬─────────┘  └─────┬──────┘  │
│           │                    │                   │         │
│           └────────────┬───────┘                   │         │
│                        │                           │         │
│                        ▼                           │         │
│              ┌─────────────────────┐               │         │
│              │  TRIANGULASI HASIL  │◄──────────────┘         │
│              │  Kuantitatif +      │                         │
│              │  Kualitatif         │                         │
│              └─────────────────────┘                         │
└──────────────────────────────────────────────────────────────┘
```

---

## 3.2 Arsitektur Sistem

Arsitektur sistem yang diusulkan terdiri dari empat fase yang dieksekusi secara sekuensial. Desain ini merupakan revisi fundamental dari arsitektur *pipeline* linear RAG+LLM yang ditolak pada seminar proposal sebelumnya. Perbedaan mendasar terletak pada penambahan mekanisme penalaran bertahap (*multi-step reasoning*) melalui arsitektur *agentic* dan lapisan validasi logika formal (*Logical Consistency Checker*) yang menjamin konsistensi output [Garcez et al., 2019; Marcus, 2020].

```
┌─────────────────────────────────────────────────────────────────┐
│            ARSITEKTUR SISTEM — 4 FASE                           │
│         Neuro-Symbolic Agentic System                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   FASE 1          FASE 2           FASE 3          FASE 4      │
│  ┌─────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐  │
│  │INGESTION│──▶│   FACT    │──▶│  AGENTIC  │──▶│ LOGICAL   │  │
│  │         │   │EXTRACTION │   │ ANALYSIS  │   │CONSISTENCY│  │
│  │ PDF →   │   │ Entity →  │   │ Plan →    │   │ CHECKER   │  │
│  │ Chunk → │   │ Triple →  │   │ Act →     │   │           │  │
│  │ Embed → │   │ KG        │   │ Observe → │   │ Rules →   │  │
│  │ Store   │   │           │   │ Reflect   │   │ Verdict   │  │
│  └─────────┘   └───────────┘   └───────────┘   └───────────┘  │
│                                                    ▲            │
│                                               KOMPONEN BARU    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2.1 Fase 1: Ingestion

Fase pertama bertanggung jawab untuk mengonversi dokumen PDF ilmiah menjadi representasi vektor yang dapat diproses oleh komponen-komponen berikutnya. Sistem dirancang untuk menerima input 3–10 paper ilmiah yang relevan dengan topik tertentu.

**Alur Proses Fase 1:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 1: INGESTION                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────────┐  │
│  │  Input   │──▶│   PDF    │──▶│ Section  │──▶│  Chunk &   │  │
│  │  Papers  │   │  Parser  │   │ Splitter │   │   Embed    │  │
│  │  (3-10)  │   │          │   │          │   │ (SciBERT)  │  │
│  └──────────┘   └──────────┘   └──────────┘   └─────┬──────┘  │
│                                                      │         │
│                                                      ▼         │
│                                                ┌──────────┐    │
│                                                │  Vector  │    │
│                                                │  Store   │    │
│                                                │ (ChromaDB)│    │
│                                                └──────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

Komponen-komponen pada Fase 1:

1. **PDF Parser:** Mengekstrak teks dari dokumen PDF menggunakan *library* seperti PyMuPDF atau GROBID. Parser ini menangani variasi format jurnal ilmiah termasuk *two-column layout*, tabel, dan caption gambar.

2. **Section Splitter:** Membagi teks yang telah diekstrak ke dalam seksi-seksi standar paper ilmiah (Abstract, Introduction, Related Work, Methodology, Results, Discussion, Conclusion). Pemisahan seksi diperlukan karena informasi di setiap seksi memiliki fungsi epistemik yang berbeda — misalnya, temuan empiris dominan di Results sedangkan posisi teoretis dominan di Introduction [Pare et al., 2015].

3. **Chunk & Embed:** Teks dari setiap seksi dipecah menjadi *chunk* berukuran 512 token dengan *overlap* 64 token. Setiap *chunk* kemudian diubah menjadi vektor menggunakan model *embedding* SciBERT [Beltagy et al., 2019], yang secara khusus dilatih pada korpus ilmiah sehingga menghasilkan representasi semantik yang lebih akurat untuk teks akademik dibandingkan model *embedding* umum.

4. **Vector Store (ChromaDB):** Vektor-vektor yang dihasilkan disimpan dalam basis data vektor ChromaDB bersama metadata (sumber paper, seksi, nomor halaman) untuk mendukung proses *retrieval* pada fase selanjutnya.

### 3.2.2 Fase 2: Fact Extraction

Fase kedua mengonversi teks tidak terstruktur menjadi representasi terstruktur berupa *Knowledge Graph* (KG) yang terdiri dari *triple* Subjek-Predikat-Objek (SPO). KG ini berfungsi sebagai *Fact Base* — bukan sekadar alat visualisasi, melainkan basis pengetahuan untuk penalaran deduktif [Ji et al., 2021].

**Alur Proses Fase 2:**

```
┌─────────────────────────────────────────────────────────────────┐
│                FASE 2: FACT EXTRACTION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │ Entity Extractor │───▶│  Fact Table      │                   │
│  │ (SciSpaCy + LLM) │    │  Constructor     │                   │
│  │                  │    │                  │                   │
│  │ 8 Tipe Entitas:  │    │ Generate SPO:    │                   │
│  │ • METHOD         │    │ (S, P, O)        │                   │
│  │ • CONCEPT        │    │ triples          │                   │
│  │ • DOMAIN         │    │                  │                   │
│  │ • FINDING        │    │ 12+ Predikat:    │                   │
│  │ • DATASET        │    │ USES_METHOD,     │                   │
│  │ • METRIC         │    │ PROPOSES,        │                   │
│  │ • PAPER          │    │ APPLIES_TO, ...  │                   │
│  │ • CONSTRAINT     │    │                  │                   │
│  └──────────────────┘    └────────┬─────────┘                   │
│                                   ▼                             │
│                          ┌──────────────────┐                   │
│                          │ KNOWLEDGE GRAPH  │                   │
│                          │ (Fact Base)      │                   │
│                          │ Nodes: entities  │                   │
│                          │ Edges: relations │                   │
│                          └──────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

Komponen-komponen pada Fase 2:

1. **Entity Extractor (SciSpaCy + LLM):** Ekstraksi entitas menggunakan pendekatan *hybrid*. SciSpaCy [Neumann et al., 2019] digunakan untuk mengenali entitas ilmiah berbasis *Named Entity Recognition* (NER) yang telah dilatih pada korpus biomedis dan ilmiah. LLM digunakan sebagai pelengkap untuk menangkap entitas yang bersifat kontekstual dan tidak tercakup oleh model NER — misalnya, temuan (*finding*) yang berupa kalimat deskriptif. Sistem mengenali 8 tipe entitas: **METHOD**, **CONCEPT**, **DOMAIN**, **FINDING**, **DATASET**, **METRIC**, **PAPER**, dan **CONSTRAINT** (lihat Subbab 3.5 untuk definisi lengkap).

2. **Fact Table Constructor:** Setelah entitas diekstrak, komponen ini mengidentifikasi relasi antar entitas dan membentuk *triple* SPO. Identifikasi relasi dilakukan melalui kombinasi *pattern matching* linguistik dan LLM *prompting*. Sistem mendukung 12+ tipe predikat: **USES_METHOD**, **PROPOSES**, **APPLIES_TO**, **ACHIEVES**, **REQUIRES_RESOURCE**, **REQUIRES_DATA**, **IMPROVES**, **CONTRADICTS**, **EXTENDS**, **EVALUATED_ON**, **HAS_CONSTRAINT**, dan **DISCUSSES** (lihat Subbab 3.5 untuk spesifikasi lengkap).

3. **Knowledge Graph (KG):** *Triple* SPO yang dihasilkan disimpan dalam *Knowledge Graph* menggunakan Neo4j atau NetworkX. KG ini berfungsi sebagai *Fact Base* yang menjadi input bagi *Rule Engine* di Fase 4, serta dapat di-*query* oleh *KG Querier tool* pada Fase 3.

### 3.2.3 Fase 3: Agentic Analysis

Fase ketiga merupakan inti dari arsitektur yang membedakan sistem ini dari *pipeline* linear. Alih-alih satu kali *retrieve-then-generate*, sistem menggunakan *Agent Orchestrator* berbasis LangGraph [LangChain, 2024] yang melakukan penalaran bertahap melalui siklus **Plan → Act → Observe → Reflect → Repeat/Stop**.

**Alur Proses Fase 3:**

```
┌─────────────────────────────────────────────────────────────────┐
│              FASE 3: AGENTIC ANALYSIS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                AGENT ORCHESTRATOR (LangGraph)            │   │
│  │                                                          │   │
│  │   ┌──────┐   ┌──────┐   ┌─────────┐   ┌─────────┐      │   │
│  │   │ PLAN │──▶│ ACT  │──▶│ OBSERVE │──▶│ REFLECT │      │   │
│  │   └──────┘   └──┬───┘   └─────────┘   └────┬────┘      │   │
│  │      ▲          │                           │           │   │
│  │      └──────────┼───────────────────────────┘           │   │
│  │                 │         REPEAT / STOP                  │   │
│  │                 ▼                                        │   │
│  │   ┌──────────────────────────────────────────────────┐   │   │
│  │   │              5 TOOLS                             │   │   │
│  │   │                                                  │   │   │
│  │   │  ┌───────────┐  ┌───────────┐  ┌──────────────┐ │   │   │
│  │   │  │    RAG    │  │   Paper   │  │     NLI      │ │   │   │
│  │   │  │ Retriever │  │ Analyzer  │  │   Checker    │ │   │   │
│  │   │  └───────────┘  └───────────┘  └──────────────┘ │   │   │
│  │   │                                                  │   │   │
│  │   │  ┌───────────┐  ┌───────────┐                    │   │   │
│  │   │  │    KG     │  │   Self-   │                    │   │   │
│  │   │  │  Querier  │  │   Critic  │                    │   │   │
│  │   │  └───────────┘  └───────────┘                    │   │   │
│  │   └──────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  Output: candidate gap indicators + evidence + reasoning │   │
│  └─────────────────────────┬────────────────────────────────┘   │
│                             │                                   │
│                  ┌──────────▼──────────┐                        │
│                  │   RAW LLM OUTPUT   │                        │
│                  │  (belum divalidasi) │                        │
│                  └────────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

**Deskripsi 5 *Tools*:**

| No | *Tool* | Fungsi | Input | Output |
|----|--------|--------|-------|--------|
| 1 | **RAG Retriever** | Mengambil *chunk* teks yang relevan dari *Vector Store* berdasarkan *query* semantik | *Query* teks | *Ranked chunks* + skor similaritas |
| 2 | **Paper Analyzer** | Mengekstrak temuan utama, metode, dan kesimpulan dari paper tertentu | ID paper | Ringkasan terstruktur per paper |
| 3 | **NLI Checker** | Mendeteksi relasi *entailment*, *contradiction*, atau *neutral* antara dua klaim | Pasangan klaim | Label NLI + skor *confidence* |
| 4 | **KG Querier** | Menjalankan *query* terhadap *Knowledge Graph* (Fact Base) untuk memverifikasi fakta | *Query* SPARQL/Cypher | *Triple* SPO yang relevan |
| 5 | **Self-Critic** | Mengevaluasi kualitas dan kelayakan output *agent* sebelum diteruskan | Kandidat output | Evaluasi + saran perbaikan |

Mekanisme *agentic* ini memungkinkan sistem untuk secara adaptif menentukan langkah analisis berikutnya berdasarkan observasi dari langkah sebelumnya — kemampuan yang tidak dimiliki oleh *pipeline* linear. Sebagai contoh, jika *NLI Checker* mendeteksi kontradiksi, *agent* dapat secara otonom memutuskan untuk memanggil *RAG Retriever* guna mencari apakah kontradiksi tersebut sudah direkonsiliasi dalam literatur lain.

Output dari Fase 3 berupa **kandidat indikator** *synthesis gap* yang dilengkapi **bukti** (*evidence*) dan **jejak penalaran** (*reasoning trace*). Output ini belum divalidasi secara logis dan akan diteruskan ke Fase 4.

### 3.2.4 Fase 4: Logical Consistency Checker (KOMPONEN BARU)

Fase keempat merupakan komponen baru yang menjadi pembeda utama arsitektur ini dari pendekatan RAG+LLM konvensional. *Logical Consistency Checker* berfungsi sebagai lapisan validasi logika formal yang memastikan bahwa output LLM dari Fase 3 konsisten secara logis sebelum disajikan kepada pengguna [Buchanan & Shortliffe, 1984; Giarratano & Riley, 2005].

**Alur Proses Fase 4:**

```
┌─────────────────────────────────────────────────────────────────┐
│       FASE 4: LOGICAL CONSISTENCY CHECKER  <-- KOMPONEN BARU   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    RULE ENGINE                           │   │
│  │                                                          │   │
│  │  Fact Base (dari KG) ────┐                               │   │
│  │                          ▼                               │   │
│  │  Rule Base ──────▶ INFERENCE ENGINE                      │   │
│  │  • F1-F3: Feasibility    │                               │   │
│  │  • C1-C3: Causality      │                               │   │
│  │  • K1-K3: Consistency    ▼                               │   │
│  │                   ┌──────────────┐                       │   │
│  │                   │   VERDICT    │                       │   │
│  │                   │              │                       │   │
│  │                   │  PASS        │                       │   │
│  │                   │  FLAG        │                       │   │
│  │                   │  REJECT      │                       │   │
│  │                   └──────┬───────┘                       │   │
│  └──────────────────────────┼───────────────────────────────┘   │
│                             │                                   │
│           ┌─────────────────┼────────────────┐                  │
│           ▼                 ▼                ▼                  │
│      ┌─────────┐     ┌──────────┐    ┌───────────┐             │
│      │ PASSED  │     │ FLAGGED  │    │ REJECTED  │             │
│      │ Output  │     │ Needs    │    │ Logically │             │
│      │ ke user │     │ human    │    │ incoherent│             │
│      │         │     │ review   │    │ + reason  │             │
│      └────┬────┘     └────┬─────┘    └───────────┘             │
│           │               │                                     │
│           ▼               ▼                                     │
│      ┌──────────────────────────┐                               │
│      │   OUTPUT KE PENGGUNA    │                               │
│      │  • Validated indicators  │                               │
│      │  • Flagged (perlu review)│                               │
│      │  • Confidence scores     │                               │
│      │  • Reasoning trace       │                               │
│      └──────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

*Rule Engine* menggunakan mekanisme *forward chaining*: fakta-fakta dari KG (*Fact Base*) dicocokkan dengan kumpulan aturan (*Rule Base*), dan *Inference Engine* menghasilkan salah satu dari tiga *verdict*:

| *Verdict* | Arti | Aksi |
|-----------|------|------|
| **PASS** | Output lolos semua aturan logika | Tampilkan ke pengguna dengan *confidence score* |
| **FLAG** | Output melanggar aturan non-kritis | Tampilkan ke pengguna dengan peringatan "perlu review manusia" |
| **REJECT** | Output melanggar aturan kritis | Jangan tampilkan ke pengguna; berikan alasan penolakan |

Keberadaan Fase 4 merupakan respons langsung terhadap kritik bahwa sistem semantik murni tidak mampu membedakan asosiasi statistik dari hubungan logis yang sesungguhnya [Marcus & Davis, 2020; Bender & Koller, 2020]. Detail aturan-aturan logika yang digunakan dibahas pada Subbab 3.4.

---

## 3.3 Mekanisme Pembeda Asosiasi Semantik vs Hubungan Logis

Salah satu kritik fundamental terhadap pendekatan RAG+LLM adalah ketidakmampuannya membedakan antara konsep yang sekadar "sering muncul bersama" (*co-occurrence*/asosiasi semantik) dengan konsep yang memiliki hubungan logis yang sesungguhnya (kausalitas atau kontradiksi). Subbab ini menjelaskan mekanisme tiga lapis (*three-layer mechanism*) yang dirancang untuk mengatasi keterbatasan tersebut.

### 3.3.1 Tiga Jenis Hubungan yang Didefinisikan

Sistem mendefinisikan tiga jenis hubungan antar konsep dalam literatur ilmiah:

| Jenis Hubungan | Definisi | Contoh | Terdeteksi via Semantik? |
|----------------|----------|--------|--------------------------|
| **Co-occurrence** | Dua konsep sering muncul bersama dalam teks tanpa hubungan kausal | "Python" dan "*machine learning*" | Ya — terdeteksi, tetapi BUKAN hubungan logis |
| **Kausalitas** | Konsep A secara logis memengaruhi atau menyebabkan Konsep B | "*Overfitting* → kebutuhan *regularization*" | Tidak — tidak dapat dideteksi dari *embedding* saja |
| **Kontradiksi** | Temuan tentang A bertentangan dengan temuan tentang B | "Method X meningkatkan akurasi" vs "Method X menurunkan akurasi" | Parsial — dapat dideteksi sebagian via NLI |

Pembedaan ketiga jenis hubungan ini bersifat kritis karena *synthesis gap* yang bermakna hanya dapat diidentifikasi melalui hubungan kausal dan kontradiktif — bukan dari sekadar *co-occurrence* [Cooper, 1998].

### 3.3.2 Mekanisme Pembeda Tiga Lapis

```
Kandidat hubungan (dari semantic similarity)
    │
    ▼
┌────────────────────────────────────────────────────┐
│ [Lapis 1] SEMANTIC FILTERING                       │
│   Similarity > threshold (0.75)?                   │
│   Ya --> lanjut         Tidak --> buang             │
└───────────────────────┬────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────┐
│ [Lapis 2] EVIDENCE EXTRACTION (LLM Agent)          │
│   Cari bukti eksplisit dalam teks:                 │
│   • Penanda kausal?       --> label KAUSAL         │
│   • Penanda kontradiksi?  --> label KONTRADIKSI    │
│   • Tidak ada penanda?    --> label CO-OCCURRENCE   │
│   Ada bukti?                                       │
│   Ya --> lanjut         Tidak --> "co-occurrence"   │
└───────────────────────┬────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────┐
│ [Lapis 3] RULE-BASED VALIDATION                    │
│   Cek terhadap aturan logika di Fact Base (KG)     │
│   Lolos?                                           │
│   Ya --> VALID RELATION   Tidak --> REJECTED+alasan │
└────────────────────────────────────────────────────┘
```

**Lapis 1 — Semantic Filtering:**

Lapis pertama berfungsi sebagai *gate* awal yang menyaring kandidat hubungan berdasarkan kedekatan semantik. Pasangan konsep yang memiliki skor *cosine similarity* di bawah *threshold* (ditentukan melalui eksperimen, nilai awal 0,75) dieliminasi. Lapis ini menangkap kandidat hubungan secara luas — termasuk *co-occurrence* — yang kemudian akan divalidasi oleh lapis-lapis berikutnya.

**Lapis 2 — Evidence Extraction (LLM Agent):**

Lapis kedua menggunakan LLM *agent* untuk mencari bukti eksplisit dalam teks asli yang mendukung jenis hubungan tertentu. *Agent* diarahkan untuk mengidentifikasi penanda linguistik (*linguistic markers*) yang mengindikasikan kausalitas atau kontradiksi.

**Penanda Linguistik Kausal:**
```
"causes", "leads to", "results in", "because", "therefore",
"consequently", "due to", "effect of", "contributes to",
"enables", "prevents", "inhibits"
```

**Penanda Linguistik Kontradiksi:**
```
"however", "contradicts", "in contrast", "whereas",
"on the other hand", "inconsistent with", "conflicts with",
"contrary to", "disputes", "challenges"
```

Jika tidak ditemukan penanda linguistik kausal maupun kontradiksi, hubungan dilabeli sebagai **co-occurrence only** dan tidak digunakan untuk deteksi *synthesis gap*. Mekanisme ini mencegah sistem menghasilkan *spurious correlation* yang secara statistik terlihat kuat tetapi tidak memiliki dasar logis [Bender & Koller, 2020].

**Lapis 3 — Rule-Based Validation:**

Lapis ketiga memverifikasi hubungan yang telah teridentifikasi terhadap aturan-aturan logika dalam *Rule Engine* (lihat Subbab 3.4). Sebagai contoh, jika lapis kedua mengidentifikasi hubungan kausal "A menyebabkan B," lapis ketiga akan memeriksa apakah hubungan tersebut konsisten dengan fakta-fakta yang sudah ada di *Knowledge Graph* dan apakah arah kausalitas logis secara temporal.

---

## 3.4 Rule-Based Validation Layer

### 3.4.1 Arsitektur Rule Engine

*Rule Engine* dibangun berdasarkan prinsip *expert systems* klasik [Buchanan & Shortliffe, 1984] yang diadaptasi untuk domain deteksi *synthesis gap*. Arsitektur terdiri dari tiga komponen:

```
                ┌──────────────────────────┐
                │       RULE ENGINE        │
                │                          │
                │  ┌────────────────────┐  │
                │  │    FACT BASE       │  │
                │  │  (dari Knowledge   │  │
                │  │   Graph - SPO      │  │
                │  │   Triples)         │  │
                │  └────────┬───────────┘  │
                │           │              │
                │  ┌────────▼───────────┐  │
                │  │    RULE BASE       │  │
                │  │                    │  │
                │  │  R1: Feasibility   │  │
                │  │  R2: Causality     │  │
                │  │  R3: Consistency   │  │
                │  └────────┬───────────┘  │
                │           │              │
                │  ┌────────▼───────────┐  │
                │  │ INFERENCE ENGINE   │  │
                │  │                    │  │
                │  │ Forward chaining:  │  │
                │  │ Facts + Rules -->  │  │
                │  │ Accept/Flag/Reject │  │
                │  └────────────────────┘  │
                └──────────────────────────┘
```

1. **Fact Base:** Basis fakta yang berasal dari *Knowledge Graph* (Fase 2). Setiap fakta direpresentasikan sebagai *triple* SPO beserta metadata (sumber paper, *confidence*, halaman). Fact Base bersifat dinamis — fakta turunan (*inferred facts*) dapat ditambahkan oleh *Inference Engine*.

2. **Rule Base:** Kumpulan aturan logika formal yang dikategorikan ke dalam tiga kelompok: *Feasibility*, *Causality*, dan *Consistency*. Aturan diformalisasi dalam bentuk klausa IF-THEN.

3. **Inference Engine:** Mesin inferensi yang menggunakan mekanisme *forward chaining* untuk mencocokkan fakta dengan aturan dan menghasilkan *verdict*.

### 3.4.2 Tiga Kategori Aturan Logika (9 Aturan)

#### Kategori 1: Aturan Kelayakan (*Feasibility Rules*)

Aturan kelayakan memastikan bahwa rekomendasi atau indikator yang dihasilkan LLM bersifat layak secara teknis dan praktis.

| ID | Aturan | Formalisasi | Contoh |
|----|--------|-------------|--------|
| **F1** | Kompatibilitas sumber daya | `IF method.resource_req = "high" AND problem.constraint = "low_resource" THEN REJECT` | LLM menyarankan "GPT-4 untuk *edge device*" → **DITOLAK** |
| **F2** | Kompatibilitas data | `IF method.data_req = "large_labeled" AND domain.data = "scarce" THEN FLAG` | "*Supervised DL* untuk *rare disease*" → **FLAG** |
| **F3** | Kompatibilitas skala | `IF method.scalability = "single_machine" AND problem.scale = "distributed" THEN REJECT` | "*In-memory processing* untuk *big data*" → **DITOLAK** |

#### Kategori 2: Aturan Kausalitas (*Causality Rules*)

Aturan kausalitas memverifikasi bahwa hubungan kausal yang diklaim oleh LLM memiliki dasar yang memadai.

| ID | Aturan | Formalisasi | Contoh |
|----|--------|-------------|--------|
| **C1** | Bukti kausal minimal | `IF relation.type = "CAUSAL" AND evidence_count < 2 THEN DOWNGRADE to "CORRELATION"` | Hanya 1 paper menyebut hubungan → *downgrade* ke korelasi |
| **C2** | Arah kausalitas | `IF cause.temporal_order > effect.temporal_order THEN REJECT` | "Hasil eksperimen menyebabkan hipotesis" → **DITOLAK** |
| **C3** | *Confounding check* | `IF relation.type = "CAUSAL" AND exists(confounding_var) THEN FLAG` | A→B tetapi ada C yang mungkin menyebabkan keduanya → **FLAG** |

#### Kategori 3: Aturan Konsistensi (*Consistency Rules*)

Aturan konsistensi memastikan bahwa output sistem tidak saling bertentangan secara internal maupun dengan basis fakta yang telah dibangun.

| ID | Aturan | Formalisasi | Contoh |
|----|--------|-------------|--------|
| **K1** | Non-kontradiksi internal | `IF output.claim_A CONTRADICTS output.claim_B THEN FLAG` | Sistem merekomendasikan X di poin 1 tetapi menolak X di poin 3 → **FLAG** |
| **K2** | Konsistensi dengan fakta KG | `IF output.claim NOT_SUPPORTED_BY kg.facts THEN DOWNGRADE confidence` | Klaim tidak didukung fakta KG → *confidence* diturunkan |
| **K3** | Transitivitas | `IF A→B AND B→C BUT output says A—/→C THEN FLAG` | "A *improves* B" + "B *improves* C" tetapi output menyatakan "A *worsens* C" → **FLAG** |

### 3.4.3 Tiga Kemungkinan *Verdict*

| *Verdict* | Arti | Aksi | Ditampilkan ke Pengguna? |
|-----------|------|------|--------------------------|
| **PASS** | Output lolos semua aturan | Tampilkan dengan *confidence score* | Ya |
| **FLAG** | Output melanggar aturan non-kritis | Tampilkan dengan peringatan "perlu *review* manusia" | Ya, dengan peringatan |
| **REJECT** | Output melanggar aturan kritis | Jangan tampilkan; berikan alasan penolakan | Tidak (hanya log) |

### 3.4.4 Contoh Skenario Lengkap

Berikut adalah contoh skenario end-to-end yang menunjukkan bagaimana *Rule Engine* mengevaluasi output LLM:

```
SKENARIO:
LLM Agent menyarankan: "CNN_Segmentation bisa di-deploy di
mobile health app untuk diagnosis real-time"

RULE ENGINE EVALUATION:

  Fact #5:  (CNN_Segmentation, REQUIRES_RESOURCE, GPU_16GB+)
  Fact #6:  (Medical_Image_Seg, HAS_CONSTRAINT, Edge_Device_Limitation)
  Fact #9:  (CNN_Segmentation, REQUIRES_RESOURCE, High_Compute)
  Fact #10: (CNN_Segmentation, INFEASIBLE_FOR, Edge_Deployment) [inferred]

  Rule F1: IF method.REQUIRES_RESOURCE = "High_Compute"
           AND target.HAS_CONSTRAINT = "Edge_Device_Limitation"
           THEN REJECT

  VERDICT: REJECT
  REASON: "CNN_Segmentation requires GPU_16GB+ (Fact #5)
           but mobile health app has edge device limitation
           (Fact #6). Recommendation is infeasible."
```

Pada skenario di atas, meskipun LLM secara semantik menghasilkan rekomendasi yang terdengar masuk akal, *Rule Engine* mampu menolaknya berdasarkan ketidaksesuaian antara kebutuhan sumber daya metode dengan *constraint* domain target. Mekanisme ini secara langsung menjawab kekhawatiran bahwa sistem semantik murni tidak mampu mendeteksi inkoherensi logis [Garcez et al., 2019].

---

## 3.5 Skema Fakta Knowledge Graph (Tabel SPO)

### 3.5.1 Ontologi

*Knowledge Graph* dalam penelitian ini dibangun berdasarkan ontologi yang mendefinisikan tipe-tipe entitas (*node*) dan tipe-tipe relasi (*edge*/predikat) secara eksplisit. Ontologi ini dirancang khusus untuk domain analisis literatur ilmiah.

#### Tipe Entitas (Node)

| Tipe | Deskripsi | Contoh | *Properties* |
|------|-----------|--------|--------------|
| **METHOD** | Metode, algoritma, atau teknik | "CNN", "Random Forest", "BERT" | `resource_requirement`, `scalability`, `data_requirement` |
| **CONCEPT** | Konsep, teori, atau *framework* | "*Transfer Learning*", "*Attention*" | `abstraction_level` |
| **DOMAIN** | Domain atau bidang penerapan | "*Medical Imaging*", "NLP" | `data_availability`, `constraint` |
| **FINDING** | Temuan empiris | "CNN achieves 95% accuracy" | `paper_source`, `confidence`, `sample_size` |
| **DATASET** | *Dataset* yang digunakan | "ImageNet", "CIFAR-10" | `size`, `type`, `availability` |
| **METRIC** | Metrik evaluasi | "Accuracy", "F1-Score" | — |
| **PAPER** | Paper sumber | "ResNet [He et al., 2016]" | `year`, `venue`, `citation_count` |
| **CONSTRAINT** | Keterbatasan atau syarat | "*High compute*", "*Low resource*" | — |

#### Tipe Relasi (Edge/Predikat)

| Predikat | Deskripsi | *Domain* → *Range* | Contoh |
|----------|-----------|---------------------|--------|
| **USES_METHOD** | Paper menggunakan metode | PAPER → METHOD | (Paper_A, USES_METHOD, CNN) |
| **PROPOSES** | Paper mengusulkan sesuatu baru | PAPER → METHOD/CONCEPT | (Paper_A, PROPOSES, ResNet) |
| **APPLIES_TO** | Metode diterapkan pada domain | METHOD → DOMAIN | (CNN, APPLIES_TO, Medical_Imaging) |
| **ACHIEVES** | Metode mencapai hasil | METHOD → FINDING | (ResNet, ACHIEVES, "95% accuracy") |
| **REQUIRES_RESOURCE** | Metode membutuhkan sumber daya | METHOD → CONSTRAINT | (GPT-4, REQUIRES_RESOURCE, high_compute) |
| **REQUIRES_DATA** | Metode membutuhkan jenis data | METHOD → CONSTRAINT | (Supervised_DL, REQUIRES_DATA, large_labeled) |
| **IMPROVES** | Metode A meningkatkan metode B | METHOD → METHOD | (ResNet, IMPROVES, VGG) |
| **CONTRADICTS** | Temuan A bertentangan dengan B | FINDING → FINDING | (Finding_1, CONTRADICTS, Finding_2) |
| **EXTENDS** | Konsep A memperluas konsep B | CONCEPT → CONCEPT | (Transformer, EXTENDS, Attention) |
| **EVALUATED_ON** | Metode dievaluasi pada *dataset* | METHOD → DATASET | (BERT, EVALUATED_ON, GLUE) |
| **HAS_CONSTRAINT** | Domain memiliki keterbatasan | DOMAIN → CONSTRAINT | (Mobile_App, HAS_CONSTRAINT, low_resource) |
| **DISCUSSES** | Paper membahas konsep | PAPER → CONCEPT | (Paper_B, DISCUSSES, Federated_Learning) |

### 3.5.2 Proses Transformasi Teks ke Tabel Fakta

Transformasi dari teks tidak terstruktur ke tabel fakta SPO dilakukan melalui tiga tahap:

```
Teks Asli (tidak terstruktur)
    │
    ▼
[Tahap 1] Entity Extraction (SciSpaCy + LLM)
    │  Identifikasi entitas: metode, konsep,
    │  dataset, temuan, constraint
    │
    ▼
[Tahap 2] Relation Extraction (LLM + Pattern Matching)
    │  Identifikasi hubungan antar entitas
    │
    ▼
[Tahap 3] Triple Construction & Validation
    │  Bentuk (S, P, O) + validasi terhadap aturan
    │
    ▼
Tabel Fakta (terstruktur) --> masuk ke Knowledge Graph
```

### 3.5.3 Contoh Lengkap: Transformasi Teks ke Tabel Fakta

#### Input (Teks Asli dari Paper):

> *"We propose a novel approach using Convolutional Neural Networks (CNN) for medical image segmentation. Our method achieves 92.3% Dice coefficient on the BraTS dataset. However, the model requires significant GPU memory (>16GB), which limits its deployment on edge devices. In contrast to Smith et al. (2023) who reported 88.1% using traditional U-Net, our approach shows improvement but at higher computational cost."*

#### Tahap 1 — Entity Extraction:

| Entitas | Tipe | Sumber Teks |
|---------|------|-------------|
| CNN (Convolutional Neural Networks) | METHOD | "using Convolutional Neural Networks (CNN)" |
| Medical Image Segmentation | DOMAIN | "for medical image segmentation" |
| Dice 92.3% | FINDING | "achieves 92.3% Dice coefficient" |
| BraTS | DATASET | "on the BraTS dataset" |
| GPU 16GB+ | CONSTRAINT | "requires significant GPU memory (>16GB)" |
| Edge Device Limitation | CONSTRAINT | "limits its deployment on edge devices" |
| Smith et al. (2023) | PAPER | "Smith et al. (2023)" |
| U-Net | METHOD | "using traditional U-Net" |
| Dice 88.1% | FINDING | "reported 88.1%" |
| High Compute | CONSTRAINT | "higher computational cost" |

#### Tahap 2 — Relation Extraction:

Penanda linguistik yang terdeteksi:
- "*propose*" → relasi PROPOSES
- "*achieves*" → relasi ACHIEVES
- "*requires*" → relasi REQUIRES_RESOURCE
- "*limits*" → relasi HAS_CONSTRAINT
- "*in contrast to*" → penanda kontradiksi/perbandingan
- "*improvement*" → relasi IMPROVES

#### Tahap 3 — Triple Construction (Output Tabel Fakta SPO):

| # | Subject | Predicate | Object | Source | Confidence |
|---|---------|-----------|--------|--------|------------|
| 1 | Paper_Current | PROPOSES | CNN_Segmentation | Sec. 3, p.5 | 1.0 |
| 2 | CNN_Segmentation | APPLIES_TO | Medical_Image_Segmentation | Sec. 1, p.1 | 1.0 |
| 3 | CNN_Segmentation | ACHIEVES | Dice_92.3% | Sec. 4, p.8 | 0.95 |
| 4 | CNN_Segmentation | EVALUATED_ON | BraTS_Dataset | Sec. 4, p.7 | 1.0 |
| 5 | CNN_Segmentation | REQUIRES_RESOURCE | GPU_16GB+ | Sec. 5, p.10 | 0.9 |
| 6 | Medical_Image_Seg | HAS_CONSTRAINT | Edge_Device_Limitation | Sec. 5, p.10 | 0.85 |
| 7 | Smith_UNet | ACHIEVES | Dice_88.1% | Sec. 2, p.3 | 0.9 |
| 8 | CNN_Segmentation | IMPROVES | Smith_UNet | Sec. 4, p.9 | 0.85 |
| 9 | CNN_Segmentation | REQUIRES_RESOURCE | High_Compute | Sec. 5, p.10 | 0.9 |

### 3.5.4 Fakta Turunan (*Inferred Facts*) via Rule Engine

Berdasarkan fakta-fakta eksplisit yang diekstrak, *Rule Engine* dapat menurunkan fakta baru melalui inferensi:

| # | Subject | Predicate | Object | *Inferred By Rule* |
|---|---------|-----------|--------|---------------------|
| 10 | CNN_Segmentation | INFEASIBLE_FOR | Edge_Deployment | F1: IF REQUIRES_RESOURCE(high_compute) AND HAS_CONSTRAINT(edge_device) THEN INFEASIBLE |

Fakta turunan (#10) tidak ditemukan secara eksplisit dalam teks, melainkan disimpulkan oleh *Rule Engine* berdasarkan kombinasi Fact #5, #6, dan #9 dengan Rule F1. Kemampuan ini menunjukkan bagaimana *Knowledge Graph* berfungsi sebagai *Fact Base* untuk penalaran — bukan sekadar alat visualisasi.

### 3.5.5 Contoh Penalaran Rule Engine Menggunakan Tabel Fakta

```
SKENARIO:
LLM Agent menyarankan: "CNN_Segmentation bisa di-deploy di
mobile health app untuk diagnosis real-time"

RULE ENGINE EVALUATION:

  Langkah 1 — Kumpulkan fakta relevan:
    Fact #5:  (CNN_Segmentation, REQUIRES_RESOURCE, GPU_16GB+)
    Fact #6:  (Medical_Image_Seg, HAS_CONSTRAINT, Edge_Device_Limitation)
    Fact #9:  (CNN_Segmentation, REQUIRES_RESOURCE, High_Compute)

  Langkah 2 — Inferensi fakta turunan:
    Fact #10: (CNN_Segmentation, INFEASIBLE_FOR, Edge_Deployment)
              [inferred from F1: resource_req=high AND constraint=low_resource]

  Langkah 3 — Evaluasi terhadap Rule Base:
    Rule F1: IF method.REQUIRES_RESOURCE = "High_Compute"
             AND target.HAS_CONSTRAINT = "Edge_Device_Limitation"
             THEN REJECT

  Langkah 4 — Verdict:
    VERDICT: REJECT
    REASON:  "CNN_Segmentation requires GPU_16GB+ (Fact #5)
              but mobile health app has edge device limitation
              (Fact #6). Recommendation is infeasible."
    ACTION:  Rekomendasi TIDAK ditampilkan ke pengguna.
```

---

## 3.6 Deteksi Indikator Synthesis Gap

### 3.6.1 Tiga Indikator Synthesis Gap

Merujuk pada kerangka Cooper [1998] dan Booth, Sutton & Papaioannou [2012], sistem mendeteksi tiga indikator utama *synthesis gap*:

| # | Indikator | Definisi | Contoh |
|---|-----------|----------|--------|
| 1 | **Fragmentasi** | Paper-paper membahas fenomena yang sama dari sudut berbeda tetapi tidak saling mengintegrasikan | 10 studi tentang *dropout* di *online learning*, masing-masing menggunakan teori berbeda, tidak ada yang menyatukan |
| 2 | **Inkonsistensi** (yang belum direkonsiliasi) | Temuan empiris saling bertentangan dan belum ada yang menyelesaikan | Paper A: *gamification* meningkatkan motivasi. Paper B: *gamification* menurunkan motivasi. Belum ada penjelasan mengapa |
| 3 | **Ketidaklengkapan** (kolektif) | Aspek-aspek kritis dari fenomena belum dicakup secara bersama oleh literatur yang ada | Banyak studi tentang efektivitas *blended learning*, tetapi tidak ada yang membahas aspek *equity*/aksesibilitas |

Penting untuk ditegaskan bahwa *synthesis gap* **bukan**: (a) kombinasi metode-domain yang belum pernah ada ("belum diterapkan" bukan berarti *gap*), (b) topik yang belum diteliti sama sekali (*knowledge gap*, bukan *synthesis gap*), atau (c) saran *future work* di akhir paper (*explicit gap*) [Muller-Bloch & Kranz, 2015].

### 3.6.2 Metode Deteksi per Indikator

#### Deteksi Fragmentasi

Fragmentasi dideteksi melalui analisis *coverage* dan *clustering* tematik:

1. **Topic Clustering:** Paper-paper dikelompokkan berdasarkan kedekatan semantik menggunakan *embedding* SciBERT. Klaster yang terfragmentasi ditandai dengan adanya sub-klaster yang memiliki *overlap* rendah (*silhouette score* < *threshold*).

2. **Cross-Citation Analysis:** Sistem memeriksa apakah paper-paper dalam klaster yang sama saling merujuk. Fragmentasi ditandai oleh rendahnya tingkat *cross-citation* di antara paper yang membahas topik serupa.

3. **KG Query — Shared Entities:** *KG Querier* memeriksa apakah paper-paper yang membahas fenomena sama menggunakan entitas (*method*, *concept*) yang sama atau berbeda. Keragaman tinggi tanpa integrasi eksplisit mengindikasikan fragmentasi.

#### Deteksi Inkonsistensi

Inkonsistensi dideteksi melalui kombinasi *NLI Checker* dan *KG Query*:

1. **Pairwise NLI:** Setiap pasangan temuan (*finding*) dari paper berbeda dievaluasi menggunakan *NLI Checker* untuk mendeteksi relasi *contradiction*. Pasangan dengan skor kontradiksi > 0,7 ditandai sebagai kandidat.

2. **Reconciliation Search:** Untuk setiap kandidat kontradiksi, *RAG Retriever* digunakan untuk mencari apakah kontradiksi tersebut sudah direkonsiliasi dalam literatur. Jika tidak ditemukan rekonsiliasi, kontradiksi dilabeli sebagai "*unresolved inconsistency*."

3. **Rule Validation (K1, K3):** *Rule Engine* memverifikasi bahwa kontradiksi yang terdeteksi bersifat genuine (bukan artefak *parsing* atau perbedaan konteks).

#### Deteksi Ketidaklengkapan

Ketidaklengkapan dideteksi melalui analisis *coverage gap*:

1. **Aspect Extraction:** Sistem mengekstrak aspek-aspek yang dibahas setiap paper menggunakan *Paper Analyzer*.

2. **Coverage Matrix:** Matriks *paper* × *aspek* dibangun untuk mengidentifikasi aspek-aspek yang tidak dicakup atau kurang dicakup oleh literatur yang ada.

3. **Significance Assessment:** *Self-Critic tool* mengevaluasi apakah aspek yang tidak tercakup bersifat signifikan (*critical gap*) atau marginal.

### 3.6.3 Contoh Agentic Workflow Trace

Berikut adalah contoh lengkap *trace* dari *Agent Orchestrator* saat mendeteksi indikator *synthesis gap* pada sekumpulan paper tentang "*gamification in education*":

```
INPUT: 5 papers tentang "gamification in education"

AGENT TRACE:
┌───────────────────────────────────────────────────────┐
│ Step 1 [PLAN]                                         │
│ "Saya perlu mengekstrak temuan dari setiap paper"     │
│ --> Call: PaperAnalyzer(paper_1..5)                    │
├───────────────────────────────────────────────────────┤
│ Step 2 [OBSERVE]                                      │
│ Paper 1: "Gamification increases engagement"          │
│ Paper 3: "Gamification has no significant effect"     │
│ "Dua temuan ini tampak bertentangan."                 │
├───────────────────────────────────────────────────────┤
│ Step 3 [ACT]                                          │
│ --> Call: NLI_Detector(finding_1, finding_3)           │
│ --> Result: CONTRADICTION (confidence: 0.87)           │
├───────────────────────────────────────────────────────┤
│ Step 4 [ACT]                                          │
│ "Apakah kontradiksi ini sudah di-address?"            │
│ --> Call: RAG_Retriever("reconciliation gamification   │
│          engagement contradictory findings")           │
│ --> Result: Tidak ditemukan rekonsiliasi               │
├───────────────────────────────────────────────────────┤
│ Step 5 [ACT]                                          │
│ --> Call: RuleEngine.validate(gap_indicator)            │
│ --> Rule K2: Cek konsistensi dengan KG facts           │
│ --> Result: PASSED (kontradiksi valid, didukung fakta) │
├───────────────────────────────────────────────────────┤
│ Step 6 [REFLECT]                                      │
│ --> Call: SelfCritic("Apakah ini valid?")              │
│ --> "Valid, tapi Paper 1 = K-12, Paper 3 = universitas.│
│    Kontradiksi mungkin context-dependent."             │
│ --> Confidence adjusted: 0.72                          │
├───────────────────────────────────────────────────────┤
│ Step 7 [OUTPUT]                                       │
│ INDICATOR: Unresolved Inconsistency                   │
│ TYPE: Inkonsistensi                                   │
│ Papers: 1, 3                                          │
│ Confidence: 0.72                                      │
│ Evidence: "Paper 1 claims gamification increases       │
│   engagement (K-12 context). Paper 3 finds no          │
│   significant effect (university context). No          │
│   reconciliation found in the literature."             │
│ Requires Human Validation: TRUE                       │
│ Rule Engine Verdict: PASS                             │
└───────────────────────────────────────────────────────┘
```

Perlu dicatat bahwa pada Step 6, *Self-Critic* mengidentifikasi bahwa kontradiksi mungkin bersifat *context-dependent* (K-12 vs universitas), sehingga *confidence* diturunkan dari 0,87 menjadi 0,72. Ini menunjukkan kemampuan *agentic system* untuk melakukan *self-correction* — kemampuan yang tidak dimiliki oleh *pipeline* linear [Marcus, 2020].

---

## 3.7 Framework Evaluasi

### 3.7.1 Metrik Evaluasi

Evaluasi sistem menggunakan 7 metrik yang dirancang untuk mengukur tidak hanya akurasi teknis tetapi juga kebermaknaan (*meaningfulness*) indikator yang dihasilkan:

| # | Metrik | Deskripsi | Cara Mengukur |
|---|--------|-----------|---------------|
| 1 | **Expert Acceptance Rate (EAR)** | Persentase indikator yang dinilai pakar sebagai *genuine synthesis gap* | Pakar me-*review* setiap indikator → *accept*/*reject* |
| 2 | **Logical Coherence Score (LCS)** | Apakah indikator logis dan masuk akal | Pakar memberikan skor 1–5 per indikator |
| 3 | **Actionability Score (AS)** | Apakah indikator cukup spesifik untuk ditindaklanjuti menjadi riset | Pakar memberikan skor 1–5 |
| 4 | **False Discovery Rate (FDR)** | Persentase indikator yang ternyata bukan *gap* | FDR = 1 − EAR |
| 5 | **Semantic vs Human Gap (SHG)** | Seberapa jauh hasil deteksi semantik dari penilaian manusia | Korelasi Spearman antara *ranking* sistem vs *ranking* pakar |
| 6 | **Rule Engine Rejection Rate (RERR)** | Persentase output LLM yang ditolak *Rule Engine* | RERR = jumlah *rejected* / total output |
| 7 | **Rule Engine Precision (REP)** | Dari yang ditolak, berapa persen yang memang pantas ditolak | Pakar me-*review* item yang di-*reject* |

### 3.7.2 Hipotesis Penelitian

#### Hipotesis Dasar (H1–H3):

- **H1:** Sistem dengan RAG menghasilkan *acceptance rate* lebih tinggi dibandingkan LLM *standalone* (mengurangi halusinasi).
- **H2:** Analisis komparatif (*multi-paper*) menghasilkan indikator yang lebih bermakna dibandingkan analisis *single-paper*.
- **H3:** Sistem dengan *Knowledge Graph* menghasilkan indikator yang lebih didukung bukti dibandingkan tanpa KG.

#### Hipotesis Baru (H4–H8):

- **H4:** *Expert acceptance rate* ≥ 50% — lebih dari separuh indikator yang dihasilkan dinilai *genuine* oleh pakar.
- **H5:** *Logical coherence score* ≥ 3,5/5 — indikator yang dihasilkan masuk akal secara logis.
- **H6:** Arsitektur *agentic* menghasilkan *acceptance rate* lebih tinggi dibandingkan *pipeline* linear RAG+LLM.
- **H7:** Sistem dengan *Rule Engine* menghasilkan *false discovery rate* lebih rendah dibandingkan tanpa *Rule Engine*.
- **H8:** Sistem mengurangi waktu identifikasi *gap* dibandingkan proses manual (*user study*).

### 3.7.3 Metodologi Ground Truth

Pendekatan *ground truth* dalam penelitian ini melampaui sekadar pencocokan *precision*/*recall* biner. Pakar domain diminta untuk memberikan label terhadap setiap indikator yang dihasilkan sistem:

| Label | Definisi | Implikasi |
|-------|----------|-----------|
| **Genuine Gap** | Indikator merepresentasikan *synthesis gap* yang bermakna dan layak diteliti | Dihitung sebagai *true positive* |
| **Trivial** | Indikator secara teknis benar tetapi terlalu dangkal atau *obvious* | Dihitung sebagai *false positive* (tipe 1) |
| **Illogical** | Indikator mengandung kesalahan logika atau inkonsistensi | Dihitung sebagai *false positive* (tipe 2) |
| **Already Addressed** | Indikator menunjukkan *gap* yang sudah dijawab oleh literatur yang ada | Dihitung sebagai *false positive* (tipe 3) |

Kategorisasi *false positive* ke dalam tiga tipe (trivial, illogical, already addressed) memungkinkan analisis yang lebih mendalam tentang **jenis** kesalahan yang dibuat sistem, bukan sekadar frekuensi kesalahan [Robinson et al., 2011].

### 3.7.4 Desain Eksperimental

#### Perbandingan Konfigurasi Sistem

Evaluasi dilakukan pada tiga konfigurasi untuk mengisolasi kontribusi setiap komponen:

| Konfigurasi | Deskripsi | Menguji Hipotesis |
|-------------|-----------|-------------------|
| **Baseline** | *Pipeline* linear RAG+LLM (tanpa *agent*, tanpa *rule engine*) | H1, H2, H3 |
| **Agentic Only** | Arsitektur *agentic* tanpa *Rule Engine* | H6 |
| **Full System** | Arsitektur *agentic* + *Rule Engine* (sistem penuh) | H4, H5, H6, H7 |

```
┌────────────────────────────────────────────────────────────┐
│            DESAIN EKSPERIMENTAL                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Konfigurasi 1       Konfigurasi 2       Konfigurasi 3    │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │   BASELINE   │   │ AGENTIC ONLY │   │ FULL SYSTEM  │   │
│  │              │   │              │   │              │   │
│  │  RAG + LLM   │   │  Agent +     │   │  Agent +     │   │
│  │  (pipeline)  │   │  Tools       │   │  Tools +     │   │
│  │              │   │  (no rules)  │   │  Rule Engine │   │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   │
│         │                  │                   │           │
│         ▼                  ▼                   ▼           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              EVALUASI BERSAMA                       │   │
│  │  • Dataset yang sama (3 topik x 5-10 paper)        │   │
│  │  • Pakar yang sama                                 │   │
│  │  • Metrik yang sama (EAR, LCS, AS, FDR, dll.)      │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

#### Desain User Study (H8)

Untuk menguji H8, dilakukan *user study* dengan desain *within-subject*:

1. **Partisipan:** 10–15 mahasiswa S2/S3 atau peneliti yang aktif melakukan *literature review*.
2. **Tugas:** Identifikasi *synthesis gap* dari sekumpulan 5–10 paper pada topik tertentu.
3. **Kondisi:**
   - **Kondisi A (Manual):** Partisipan mengidentifikasi *gap* tanpa bantuan sistem.
   - **Kondisi B (Dengan Sistem):** Partisipan menggunakan sistem sebagai alat bantu.
4. **Pengukuran:** Waktu yang dibutuhkan, jumlah *gap* yang teridentifikasi, kualitas *gap* (dinilai oleh pakar independen).
5. **Kontrol:** Urutan kondisi diimbangi (*counterbalanced*) untuk menghindari efek *learning*.

### 3.7.5 Kriteria Keberhasilan

Berdasarkan hipotesis yang diajukan, penelitian ini mendefinisikan kriteria keberhasilan minimum:

| Kriteria | *Threshold* | Justifikasi |
|----------|-------------|-------------|
| *Expert Acceptance Rate* | ≥ 50% | Lebih dari separuh indikator harus dinilai bermakna |
| *Logical Coherence Score* | ≥ 3,5/5 | Indikator harus masuk akal secara logis |
| *False Discovery Rate* penurunan | ≥ 20% | *Rule Engine* harus mengurangi FDR minimal 20% dibandingkan tanpa *Rule Engine* |
| *Rule Engine Precision* | ≥ 70% | Dari yang ditolak *Rule Engine*, minimal 70% memang pantas ditolak |

---

## 3.8 Novelty Statement

Penelitian terdahulu tentang *automated research gap detection* menggunakan pendekatan *pipeline* linear (*retrieve-then-generate*) yang memiliki tiga kelemahan fundamental: (a) tidak merepresentasikan proses kognitif bertahap yang dilakukan peneliti manusia, (b) tidak memiliki mekanisme validasi logis terhadap output yang dihasilkan, dan (c) tidak mampu membedakan asosiasi semantik dari hubungan kausal yang sesungguhnya [Bender & Koller, 2020; Marcus & Davis, 2020].

Penelitian ini mengusulkan pendekatan **Neuro-Symbolic Agentic System** yang mengintegrasikan empat komponen kebaruan:

1. **Arsitektur agentic multi-step reasoning** — menggunakan siklus *Plan → Act → Observe → Reflect → Repeat/Stop* yang secara struktural lebih mendekati proses kognitif peneliti dibandingkan *pipeline* linear.

2. **Rule-Based Validation Layer** — lapisan validasi logika formal berisi 9 aturan dalam 3 kategori (*Feasibility*, *Causality*, *Consistency*) yang menjamin konsistensi logis output.

3. **Mekanisme pembeda asosiasi semantik vs hubungan logis** — mekanisme tiga lapis (*Semantic Filtering → Evidence Extraction → Rule-Based Validation*) yang mencegah *spurious correlation*.

4. **Knowledge Graph sebagai Fact Base** — KG dengan ontologi eksplisit (8 tipe entitas, 12+ predikat) yang berfungsi sebagai basis penalaran deduktif, bukan sekadar alat visualisasi.

Kebaruan penelitian ini **bukan** terletak pada RAG atau LLM — yang sudah merupakan teknologi *established* — melainkan pada integrasi penalaran simbolik (*rule engine* + *fact table*) dengan penalaran neural (LLM *agent*) untuk domain spesifik *synthesis gap detection* [Garcez et al., 2019]. Pendekatan *neuro-symbolic* ini memungkinkan sistem untuk:

- Menghasilkan indikator yang tidak hanya relevan secara semantik tetapi juga konsisten secara logis.
- Menolak rekomendasi yang cacat logika sebelum sampai ke pengguna.
- Membedakan temuan yang saling berkorelasi dari temuan yang saling berkontradiksi.
- Melakukan penalaran bertahap dengan kemampuan *self-correction*.

Posisi sistem sebagai **alat bantu** (*decision support*) — bukan pengganti penalaran manusia — juga merupakan pembeda penting. Sistem tidak mengklaim mampu menalar secara induktif; sistem mengklaim mampu menyajikan **indikator** yang telah divalidasi secara logis untuk mempercepat proses identifikasi *synthesis gap* oleh peneliti manusia [Cooper, 1998].

---

### Daftar Referensi yang Dirujuk dalam BAB III

1. Beltagy, I., Lo, K., & Cohan, A. (2019). SciBERT: A Pretrained Language Model for Scientific Text. *EMNLP 2019*.
2. Bender, E. M., & Koller, A. (2020). Climbing towards NLU: On Meaning, Form, and Understanding in the Age of Data. *ACL 2020*.
3. Booth, A., Sutton, A., & Papaioannou, D. (2012). *Systematic Approaches to a Successful Literature Review*. Sage.
4. Bosselut, A., et al. (2019). COMET: Commonsense Transformers for Automatic Knowledge Graph Construction. *ACL 2019*.
5. Bowman, S., et al. (2015). A Large Annotated Corpus for Learning Natural Language Inference. *EMNLP 2015*.
6. Buchanan, B. G., & Shortliffe, E. H. (1984). *Rule-Based Expert Systems*. Addison-Wesley.
7. Cooper, H. (1998). *Synthesizing Research: A Guide for Literature Reviews* (3rd ed.). Sage Publications.
8. Garcez, A., et al. (2019). Neural-Symbolic Computing: An Effective Methodology for Principled Integration of Machine Learning and Reasoning. *Journal of Applied Logics*.
9. Giarratano, J. C., & Riley, G. D. (2005). *Expert Systems: Principles and Programming* (4th ed.). Thomson.
10. Hevner, A. R., et al. (2004). Design Science in Information Systems Research. *MIS Quarterly*, 28(1), 75-105.
11. Ji, S., et al. (2021). A Survey on Knowledge Graphs: Representation, Acquisition, and Applications. *IEEE TNNLS*.
12. LangChain. (2024). LangGraph: Building Stateful, Multi-Actor Applications with LLMs. *Documentation*.
13. Marcus, G. (2020). The Next Decade in AI: Four Steps Towards Robust Artificial Intelligence. *arXiv:2002.06177*.
14. Marcus, G., & Davis, E. (2020). *Rebooting AI: Building Artificial Intelligence We Can Trust*. Vintage.
15. Muller-Bloch, C., & Kranz, J. (2015). A Framework for Rigorously Identifying Research Gaps in Qualitative Literature Reviews. *ICIS 2015 Proceedings*.
16. Neumann, M., et al. (2019). ScispaCy: Fast and Robust Models for Biomedical Natural Language Processing. *BioNLP 2019*.
17. Pare, G., et al. (2015). Synthesizing Information Systems Knowledge: A Typology of Literature Reviews. *Information & Management*, 52(2), 183-199.
18. Robinson, K. A., Saldanha, I. J., & McKoy, N. A. (2011). Development of a Framework to Identify Research Gaps from Systematic Reviews. *Journal of Clinical Epidemiology*.
19. Williams, A., et al. (2018). A Broad-Coverage Challenge Corpus for Sentence Understanding through Inference. *NAACL 2018*.
