# PERNYATAAN KEBARUAN PENELITIAN (NOVELTY STATEMENT)

## Neuro-Symbolic Agentic System untuk Deteksi Indikator Synthesis Gap

---

## 1. Konteks: Keterbatasan Pendekatan Saat Ini

### 1.1 Latar Belakang

Dalam beberapa tahun terakhir, pendekatan berbasis Retrieval-Augmented Generation (RAG) yang dikombinasikan dengan Large Language Model (LLM) telah menjadi arsitektur dominan dalam sistem otomatis untuk analisis literatur ilmiah. Pendekatan ini pada umumnya mengikuti pola pipeline linear: *retrieve-then-generate* — yaitu mengambil dokumen relevan dari basis data vektor, kemudian menghasilkan output melalui model bahasa generatif.

Meskipun pipeline RAG+LLM telah menunjukkan kemampuan dalam tugas-tugas seperti *question answering*, perangkuman, dan ekstraksi informasi, terdapat sejumlah keterbatasan fundamental ketika pendekatan ini diterapkan pada tugas yang lebih kompleks seperti deteksi *synthesis gap* dalam literatur ilmiah.

### 1.2 Keterbatasan Pipeline Linear RAG+LLM

| No. | Keterbatasan | Penjelasan |
|-----|-------------|------------|
| 1 | **Arsitektur linear tanpa penalaran bertahap** | Pipeline RAG+LLM berjalan secara sekuensial: *Retrieve → Generate → selesai*. Tidak terdapat mekanisme untuk mengevaluasi ulang, merevisi, atau memperdalam analisis secara iteratif — berbeda dengan proses kognitif seorang peneliti yang melakukan penalaran bertahap (*multi-step reasoning*). |
| 2 | **Tidak memiliki mekanisme validasi logis** | Output yang dihasilkan oleh LLM tidak melewati tahap pemeriksaan konsistensi logis. Rekomendasi yang secara logika tidak layak (misalnya, menyarankan metode berkomputasi tinggi untuk perangkat *edge*) tetap diteruskan ke pengguna tanpa penyaringan. |
| 3 | **Tidak mampu membedakan asosiasi semantik dari hubungan kausal** | Sistem berbasis *embedding* mendeteksi kesamaan semantik antar konsep (co-occurrence), namun tidak mampu membedakan apakah dua konsep memiliki hubungan kausal yang sesungguhnya ataukah sekadar sering muncul bersama dalam korpus. Sebagai contoh, "Python" dan "machine learning" memiliki kemiripan semantik tinggi, tetapi tidak memiliki hubungan kausal. |
| 4 | **Tidak terdapat mekanisme verifikasi mandiri (*self-verification*)** | Pipeline linear tidak memiliki kemampuan untuk memeriksa ulang klaim-klaim yang dihasilkannya sendiri. Dalam konteks deteksi *synthesis gap*, hal ini berarti output yang tidak akurat atau tidak konsisten tetap disajikan tanpa koreksi. |
| 5 | **Knowledge Graph hanya digunakan sebagai alat visualisasi** | Pada sistem-sistem yang telah mengintegrasikan Knowledge Graph, graf pengetahuan umumnya digunakan sebatas untuk visualisasi hubungan antar entitas — bukan sebagai basis fakta (*fact base*) yang dapat dimanfaatkan untuk penalaran formal. |

### 1.3 Contoh Sistem Serupa yang Telah Ada

Sejumlah penelitian terdahulu telah menggunakan pipeline RAG+LLM untuk tugas analisis literatur:

- Sistem berbasis RAG untuk *scientific question answering* yang mengikuti pola *retrieve-then-generate* tanpa validasi logis (Lewis et al., 2020).
- Pendekatan perangkuman ilmiah otomatis berbasis LLM yang tidak memiliki mekanisme pembeda antara hubungan semantik dan kausal.
- Sistem deteksi *research gap* yang hanya mengandalkan kemiripan semantik (*cosine similarity*) tanpa melakukan verifikasi faktual terhadap Knowledge Graph.
- Platform analisis literatur yang menggunakan Knowledge Graph semata untuk visualisasi, bukan untuk penalaran berbasis aturan.

Kesamaan dari semua pendekatan tersebut adalah ketergantungan pada paradigma *black box* LLM tanpa lapisan penalaran simbolik yang eksplisit — suatu keterbatasan fundamental yang menjadi motivasi utama penelitian ini.

---

## 2. Kebaruan Penelitian: Neuro-Symbolic Agentic System

### 2.1 Ringkasan Kebaruan

Penelitian ini mengusulkan pendekatan **Neuro-Symbolic Agentic System** yang mengintegrasikan penalaran neural (LLM agent) dengan penalaran simbolik (rule engine + fact table) untuk domain spesifik deteksi indikator *synthesis gap*. Kebaruan bukan terletak pada komponen RAG atau LLM secara individual (yang sudah *established*), melainkan pada **arsitektur integrasi** yang memungkinkan penalaran yang lebih mendekati proses kognitif peneliti manusia.

### 2.2 Empat Pilar Kebaruan

#### Pilar 1: Arsitektur Agentic Multi-Step Reasoning

Berbeda dengan pipeline linear, sistem ini mengadopsi arsitektur agentic yang mengimplementasikan siklus penalaran bertahap:

```
Plan → Act → Observe → Reflect → Repeat/Stop
```

Agent orchestrator secara iteratif merencanakan langkah berikutnya (*planning*), menjalankan aksi melalui pemanggilan *tools* yang modular (*acting*), mengamati hasil (*observing*), mengevaluasi kecukupan dan kualitas hasil (*evaluating*), serta memutuskan apakah diperlukan iterasi tambahan atau proses dapat dihentikan. Pendekatan ini lebih mendekati proses kognitif bertahap seorang peneliti dibandingkan pendekatan linear *one-shot*.

**Tools yang tersedia bagi agent:**
| Tool | Fungsi |
|------|--------|
| RAG Retriever | Pengambilan dokumen relevan dari basis data vektor |
| Paper Analyzer | Ekstraksi temuan, metode, dan klaim dari paper |
| NLI Contradiction Checker | Deteksi kontradiksi antar temuan menggunakan Natural Language Inference |
| KG Querier (Fact Table) | Kueri terhadap tabel fakta di Knowledge Graph |
| Rule Engine (Logical Validator) | Validasi konsistensi logis output |
| Self-Critic | Evaluasi mandiri terhadap klaim yang dihasilkan |

#### Pilar 2: Rule-Based Validation Layer untuk Konsistensi Logis

Sistem ini menambahkan lapisan validasi berbasis aturan (*Rule-Based Validation Layer*) yang berfungsi sebagai penyaring logis terhadap output yang dihasilkan oleh komponen neural (LLM). Lapisan ini terdiri atas tiga kategori aturan:

| Kategori | ID Aturan | Deskripsi | Contoh |
|----------|-----------|-----------|--------|
| **Kelayakan (*Feasibility*)** | F1–F3 | Memeriksa kompatibilitas sumber daya, data, dan skala | Menolak rekomendasi metode berkomputasi tinggi untuk perangkat *edge* |
| **Kausalitas (*Causality*)** | C1–C3 | Memvalidasi klaim hubungan sebab-akibat | Men-*downgrade* klaim kausal yang hanya didukung satu sumber bukti menjadi korelasi |
| **Konsistensi (*Consistency*)** | K1–K3 | Memeriksa konsistensi internal dan kesesuaian dengan fakta KG | Menandai output yang bertentangan dengan fakta yang tercatat di Knowledge Graph |

Setiap output dievaluasi terhadap aturan-aturan tersebut dan menerima salah satu dari tiga *verdict*:

| Verdict | Arti | Aksi |
|---------|------|------|
| ✅ **PASS** | Output lolos semua aturan | Disajikan kepada pengguna dengan *confidence score* |
| ⚠️ **FLAG** | Output melanggar aturan non-kritis | Disajikan dengan peringatan "memerlukan validasi manusia" |
| ❌ **REJECT** | Output melanggar aturan kritis | Tidak disajikan kepada pengguna; disertai alasan penolakan |

#### Pilar 3: Mekanisme Pembeda Asosiasi Semantik vs Hubungan Kausal/Kontradiktif

Sistem ini mengimplementasikan mekanisme tiga lapis (*three-layer mechanism*) untuk membedakan jenis hubungan antar konsep:

**Lapis 1 — Semantic Filtering:**
Kandidat hubungan disaring berdasarkan kemiripan semantik (*cosine similarity*). Pasangan konsep dengan skor di bawah ambang batas dieliminasi.

**Lapis 2 — Evidence Extraction (LLM Agent):**
Untuk pasangan yang lolos saringan semantik, agent mencari bukti linguistik eksplisit dalam teks sumber:
- **Penanda kausal:** "causes", "leads to", "results in", "because", "therefore", "contributes to", "enables", "prevents"
- **Penanda kontradiksi:** "however", "contradicts", "in contrast", "whereas", "inconsistent with", "conflicts with", "contrary to"
- **Tanpa penanda** → diklasifikasikan sebagai *co-occurrence only*

**Lapis 3 — Rule-Based Validation:**
Hubungan yang teridentifikasi divalidasi terhadap aturan logika di Fact Base (Knowledge Graph). Hubungan yang lolos dinyatakan valid; yang tidak lolos ditolak disertai alasan.

#### Pilar 4: Knowledge Graph sebagai Fact Base (Bukan Hanya Visualisasi)

Berbeda dengan pendekatan konvensional yang menggunakan Knowledge Graph sebatas untuk visualisasi hubungan, sistem ini mentransformasi teks jurnal yang tidak terstruktur menjadi **Tabel Fakta** berupa tripel Subject–Predicate–Object (SPO) yang berfungsi sebagai basis fakta untuk penalaran formal.

**Ontologi entitas** mencakup 8 tipe: METHOD, CONCEPT, DOMAIN, FINDING, DATASET, METRIC, PAPER, dan CONSTRAINT.

**Ontologi relasi** mencakup 12 predikat: USES_METHOD, PROPOSES, APPLIES_TO, ACHIEVES, REQUIRES_RESOURCE, REQUIRES_DATA, IMPROVES, CONTRADICTS, EXTENDS, EVALUATED_ON, HAS_CONSTRAINT, dan DISCUSSES.

**Proses transformasi teks ke tabel fakta:**
1. **Entity Extraction** (SciSpaCy + LLM) — mengidentifikasi entitas ilmiah dalam teks
2. **Relation Extraction** (LLM + Pattern Matching) — mengidentifikasi hubungan antar entitas
3. **Triple Construction & Validation** — membentuk tripel SPO dan memvalidasi terhadap aturan

Tabel fakta ini kemudian digunakan oleh Rule Engine untuk melakukan penalaran deduktif — termasuk menghasilkan *inferred facts* (fakta turunan) yang tidak tercantum secara eksplisit dalam teks asli.

---

## 3. Perbandingan dengan Penelitian Terdahulu

Tabel berikut menyajikan perbandingan sistematis antara pendekatan pipeline RAG+LLM konvensional dengan sistem yang diusulkan dalam penelitian ini:

| Aspek | Pipeline RAG+LLM (Konvensional) | Sistem Ini (Neuro-Symbolic Agentic) |
|-------|--------------------------------|--------------------------------------|
| **Arsitektur** | Linear: *Retrieve → Generate → selesai*. Proses berjalan sekuensial tanpa iterasi. | Agentic: *Plan → Act → Observe → Reflect → Repeat/Stop*. Proses berjalan iteratif dengan evaluasi di setiap langkah. |
| **Penalaran (*Reasoning*)** | *One-shot generation* — LLM menghasilkan output dalam satu langkah tanpa refleksi. | *Multi-step reasoning* — agent melakukan penalaran bertahap, memanggil *tools* yang berbeda untuk sub-tugas yang berbeda. |
| **Validasi Logis** | ❌ Tidak ada. Output LLM diteruskan langsung ke pengguna tanpa pemeriksaan konsistensi logis. | ✅ Rule-Based Validation Layer dengan 9 aturan (F1–F3, C1–C3, K1–K3) dan tiga kemungkinan *verdict* (PASS/FLAG/REJECT). |
| **Pembeda Semantik vs Logis** | ❌ Tidak ada. Semua hubungan diperlakukan setara berdasarkan kemiripan semantik (*embedding similarity*). | ✅ Mekanisme tiga lapis: Semantic Filtering → Evidence Extraction → Rule-Based Validation. Membedakan *co-occurrence*, kausalitas, dan kontradiksi. |
| **Penggunaan Knowledge Graph** | Sebagai alat visualisasi atau *retrieval* tambahan. Tidak digunakan untuk penalaran formal. | Sebagai **Fact Base** berupa tabel SPO yang digunakan oleh Rule Engine untuk penalaran deduktif dan menghasilkan fakta turunan (*inferred facts*). |
| **Verifikasi Mandiri (*Self-verification*)** | ❌ Tidak ada. Sistem tidak memeriksa ulang klaim-klaim yang dihasilkannya. | ✅ Agent memiliki *tool* Self-Critic yang mengevaluasi validitas klaim dan menyesuaikan *confidence score*. |
| **Pendekatan Deteksi Gap** | Berbasis kemiripan semantik dan generasi teks — mengandalkan *pattern matching* statistik. | Berbasis integrasi penalaran neural (LLM) dan simbolik (Rule Engine + Fact Table) — menggabungkan fleksibilitas bahasa alami dengan rigor logika formal. |
| **Kebaruan** | ❌ Sudah banyak implementasi serupa; tidak terdapat kebaruan mendasar. | ⚠️ Agent untuk *synthesis gap detection* yang divalidasi oleh rule engine belum ada dalam literatur. |

---

## 4. Klaim Penelitian dan Batasan Epistemologis

### 4.1 Apa yang Diklaim oleh Penelitian Ini

| No. | Klaim | Penjelasan |
|-----|-------|------------|
| 1 | Sistem mampu mendeteksi **indikator** *synthesis gap*, bukan *synthesis gap* yang definitif | Output sistem berupa kandidat indikator yang memerlukan validasi oleh peneliti manusia. Sistem tidak mengklaim menemukan gap yang pasti valid. |
| 2 | Sistem berfungsi sebagai **alat bantu keputusan (*decision support*)**, bukan pengganti penalaran manusia | Sistem mempercepat proses identifikasi awal, namun keputusan akhir tentang validitas dan signifikansi gap tetap berada di tangan peneliti. |
| 3 | Sistem mengintegrasikan **penalaran neural dan simbolik** untuk meningkatkan kualitas output | Komponen neural (LLM) memberikan fleksibilitas bahasa alami, sementara komponen simbolik (Rule Engine + Fact Table) memberikan konsistensi logis yang dapat diaudit. |
| 4 | Sistem mampu **menolak rekomendasi yang cacat logika** melalui Rule Engine | Aturan-aturan validasi eksplisit (F1–F3, C1–C3, K1–K3) memungkinkan sistem mendeteksi dan menolak output yang tidak konsisten secara logis. |
| 5 | Sistem mampu menyajikan **indikator yang mempercepat proses identifikasi** oleh peneliti manusia | Indikator yang dihasilkan disertai *confidence score*, *reasoning trace*, dan status validasi (PASS/FLAG/REJECT). |

### 4.2 Apa yang TIDAK Diklaim oleh Penelitian Ini

| No. | Klaim yang Tidak Dibuat | Alasan |
|-----|------------------------|--------|
| 1 | ❌ Sistem TIDAK mengklaim mampu **menalar secara induktif** | Penalaran induktif — yaitu menarik kesimpulan umum dari observasi spesifik — memerlukan kapabilitas kognitif yang melampaui kemampuan LLM (yang bersifat probabilistik) maupun Rule Engine (yang bersifat deduktif). |
| 2 | ❌ Sistem TIDAK mengklaim menemukan gap yang **pasti valid** | Validitas suatu *synthesis gap* pada akhirnya memerlukan *scientific judgment* yang hanya dimiliki oleh peneliti berpengalaman dalam bidang terkait. |
| 3 | ❌ Sistem TIDAK mengklaim **menggantikan proses review manusia** | Sistem menghasilkan indikator awal; proses validasi, interpretasi, dan penilaian signifikansi tetap memerlukan keterlibatan manusia. |
| 4 | ❌ Sistem TIDAK mengklaim mampu **memahami konteks eksperimental secara mendalam** | Sistem dapat mendeteksi kontradiksi antar temuan, namun tidak mampu menjelaskan *mengapa* temuan tersebut bertentangan (misalnya, perbedaan populasi sampel, desain eksperimen, atau variabel kontekstual). |
| 5 | ❌ Sistem TIDAK mengklaim bahwa pemeringkatan gap bersifat **absolut** | Pemeringkatan indikator berdasarkan *confidence score* bersifat heuristik dan bergantung pada kualitas input serta cakupan basis fakta. |

### 4.3 Kemampuan dan Batasan Sistem

**Apa yang BISA dilakukan sistem (Level Semantik + Rule Engine):**

| Kemampuan | Metode | Tingkat Keyakinan |
|-----------|--------|-------------------|
| Mendeteksi kesamaan topik antar paper | Semantic similarity (embedding) | Tinggi |
| Mendeteksi terminologi berbeda untuk konsep sama | Clustering semantik | Tinggi |
| Mendeteksi klaim yang saling bertentangan | NLI + Rule Engine | Sedang–Tinggi |
| Mengidentifikasi aspek absen dari paper tertentu | Coverage gap analysis | Sedang |
| Memvalidasi kelayakan logis suatu rekomendasi | Rule-Based Validation | Tinggi |
| Mengelompokkan paper berdasarkan pendekatan | Topic clustering | Tinggi |

**Apa yang TIDAK BISA dilakukan sistem:**

| Keterbatasan | Alasan |
|-------------|--------|
| Menilai apakah suatu kombinasi ide logis secara mendalam | Membutuhkan penalaran kausal yang melampaui rule engine sederhana |
| Memahami mengapa temuan saling bertentangan | Membutuhkan pemahaman konteks eksperimental mendalam |
| Menentukan apakah gap bermakna untuk dijadikan riset | Membutuhkan *scientific judgment* |
| Melakukan penalaran induktif sejati | LLM bersifat probabilistik, Rule Engine bersifat deduktif — keduanya bukan induktif |

---

## 5. Posisi dalam Literatur

### 5.1 Spektrum Pendekatan

Sistem yang diusulkan dalam penelitian ini menempati posisi di antara dua ujung spektrum pendekatan kecerdasan buatan untuk analisis literatur ilmiah:

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  Sistem LLM Murni              SISTEM INI              Expert      │
│  (Pure Neural)            (Neuro-Symbolic)            Systems      │
│                                                   (Pure Symbolic)   │
│       ◄────────────────────────●──────────────────────►             │
│                                                                     │
│  • Fleksibel tapi            • Fleksibel DAN          • Rigid tapi │
│    tidak terverifikasi         terverifikasi             presisi   │
│  • Tidak ada jaminan         • Validasi eksplisit     • Sulit      │
│    konsistensi logis           via rule engine           diskalakan │
│  • Black box                 • Transparan &           • Butuh      │
│                                dapat diaudit             knowledge  │
│                                                          engineer  │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Pendekatan Neuro-Symbolic sebagai Jalan Tengah

Pendekatan neuro-symbolic yang diadopsi dalam penelitian ini merepresentasikan **jalan tengah** yang menggabungkan kelebihan dari kedua ujung spektrum:

**Dari komponen neural (LLM Agent):**
- Fleksibilitas dalam memproses bahasa alami yang kompleks dan beragam
- Kemampuan generalisasi terhadap terminologi dan pola ekspresi baru
- Skalabilitas dalam menangani volume literatur yang besar

**Dari komponen simbolik (Rule Engine + Fact Table):**
- Konsistensi logis yang dapat dijamin melalui aturan eksplisit
- Transparansi dan auditabilitas — setiap keputusan dapat ditelusuri ke aturan dan fakta spesifik
- Kemampuan menolak output yang tidak memenuhi standar logika formal

Integrasi kedua komponen ini memungkinkan sistem untuk memanfaatkan kekuatan LLM dalam pemrosesan bahasa alami sambil tetap menjaga standar rigor logika melalui lapisan validasi simbolik — sebuah pendekatan yang konsisten dengan visi *Neuro-Symbolic AI* sebagaimana diadvokasi oleh Garcez et al. (2019) dan Marcus (2020).

### 5.3 Kontribusi terhadap Bidang

Dalam konteks literatur yang ada, penelitian ini memberikan kontribusi pada tiga area:

1. **Bidang *automated literature analysis*:** Mengusulkan arsitektur agentic yang melampaui paradigma pipeline linear yang dominan saat ini.
2. **Bidang *neuro-symbolic AI*:** Menyediakan studi kasus penerapan integrasi neural-simbolik pada domain spesifik analisis literatur ilmiah.
3. **Bidang *research gap identification*:** Memperkenalkan mekanisme pembeda antara asosiasi semantik dan hubungan kausal/kontradiktif yang belum ada dalam sistem-sistem sebelumnya.

---

## Referensi Utama

1. Cooper, H. (1998). *Synthesizing Research: A Guide for Literature Reviews* (3rd ed.). Sage Publications.
2. Booth, A., Sutton, A., & Papaioannou, D. (2012). *Systematic Approaches to a Successful Literature Review*. Sage.
3. Garcez, A., et al. (2019). Neural-Symbolic Computing: An Effective Methodology for Principled Integration of Machine Learning and Reasoning. *Journal of Applied Logics*.
4. Marcus, G. (2020). The Next Decade in AI: Four Steps Towards Robust Artificial Intelligence. *arXiv:2002.06177*.
5. Marcus, G., & Davis, E. (2020). *Rebooting AI: Building Artificial Intelligence We Can Trust*. Vintage.
6. Bender, E. M., & Koller, A. (2020). Climbing towards NLU: On Meaning, Form, and Understanding in the Age of Data. *ACL 2020*.
7. Ji, S., et al. (2021). A Survey on Knowledge Graphs: Representation, Acquisition, and Applications. *IEEE TNNLS*.
8. Buchanan, B. G., & Shortliffe, E. H. (1984). *Rule-Based Expert Systems*. Addison-Wesley.
9. Muller-Bloch, C., & Kranz, J. (2015). A Framework for Rigorously Identifying Research Gaps in Qualitative Literature Reviews. *ICIS 2015 Proceedings*.
10. Lewis, P., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *NeurIPS 2020*.
