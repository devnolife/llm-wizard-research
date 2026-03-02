# 📋 MASTER DOKUMEN REVISI PROPOSAL

**Mahasiswa:** Agung
**Program:** Magister (S2)
**Tanggal Kompilasi:** 2 Maret 2026
**Status:** 🔴 HARUS SEGERA DIKERJAKAN — JANGAN CODING SEBELUM KONSEP DISETUJUI PEMBIMBING

---

# DAFTAR ISI

1. [Ringkasan Seluruh Kritik Penguji](#1-ringkasan-seluruh-kritik-penguji)
2. [REVISI: Rumusan Masalah](#2-revisi-rumusan-masalah)
3. [REVISI: Definisi Synthesis Gap](#3-revisi-definisi-synthesis-gap)
4. [REVISI: Batasan Epistemologis Sistem](#4-revisi-batasan-epistemologis-sistem)
5. [REVISI: Perubahan ke Arsitektur Agent](#5-revisi-perubahan-ke-arsitektur-agent)
6. [REVISI: Pembeda Asosiasi Semantik vs Hubungan Logis](#6-revisi-pembeda-asosiasi-semantik-vs-hubungan-logis)
7. [REVISI: Rule-Based Validation Layer](#7-revisi-rule-based-validation-layer)
8. [REVISI: Diagram Alir Metodologi](#8-revisi-diagram-alir-metodologi)
9. [REVISI: Skema Fakta Knowledge Graph (Tabel SPO)](#9-revisi-skema-fakta-knowledge-graph-tabel-spo)
10. [REVISI: Framework Evaluasi](#10-revisi-framework-evaluasi)
11. [REVISI: Tinjauan Pustaka & Referensi Baru](#11-revisi-tinjauan-pustaka--referensi-baru)
12. [Perubahan File Kode](#12-perubahan-file-kode)
13. [Timeline Pengerjaan](#13-timeline-pengerjaan)
14. [Checklist Final](#14-checklist-final)

---

# 1. RINGKASAN SELURUH KRITIK PENGUJI

## Kritik Tahap 1 (Fondasi Konseptual)

| # | Kritik | Inti Masalah | Keparahan |
|---|--------|-------------|-----------|
| 1 | Rumusan masalah bukan "masalah" | Hanya spesifikasi teknis berbentuk pertanyaan — bukan kesenjangan pengetahuan | 🔴 FATAL |
| 2 | Definisi synthesis gap tidak mainstream | "Kombinasi Method A + Domain B" terlalu dangkal — bukan sintesis level S2 | 🔴 FATAL |
| 3 | Tidak ada penjelasan bagaimana sistem semantik menarik research gap | LLM/RAG bukan penalar induktif — batas kemampuan tidak diakui | 🔴 FATAL |
| 4 | RAG+LLM bukan sesuatu yang baru | Kombinasi RAG+LLM sudah banyak, tidak ada kebaruan mendasar | 🔴 FATAL |

## Kritik Tahap 2 (Arsitektur & Metodologi)

| # | Kritik | Inti Masalah | Keparahan |
|---|--------|-------------|-----------|
| 5 | Penalaran Induktif vs Asosiasi Semantik | Sistem tidak bisa bedakan "sering muncul bersama" vs "benar-benar berhubungan secara logis" | 🔴 FATAL |
| 6 | Perlu Rule-Based Validation Layer | Output LLM harus difilter aturan logika formal sebelum sampai ke pengguna | 🔴 FATAL |
| 7 | Diagram Alir terlalu Linear & Black Box | Harus ada blok "Logical Consistency Checker" setelah LLM reasoning | 🔴 FATAL |
| 8 | Skema Fakta Knowledge Graph tidak jelas | KG harus punya Tabel Fakta (Subjek-Predikat-Objek) yang eksplisit — bukan sekadar visualisasi | 🔴 FATAL |

## Pola yang Terlihat

Penguji menuntut **3 hal fundamental:**

```
1. KONSEPTUAL: Perbaiki pemahaman tentang apa itu synthesis gap 
               dan apa yang bisa/tidak bisa dilakukan sistem semantik.

2. KEBARUAN:   RAG+LLM pipeline biasa bukan kebaruan. 
               Perlu arsitektur yang berbeda (→ AI Agent + Rule Engine).

3. PENALARAN:  Sistem tidak boleh hanya semantik. 
               Harus ada lapisan logika formal (Neuro-Symbolic).
```

---

# 2. REVISI: RUMUSAN MASALAH

## ❌ Versi Lama (DITOLAK)

```
Bagaimana merancang arsitektur sistem berbasis RAG dan LLM yang mampu 
menganalisis beberapa jurnal untuk menemukan celah penelitian (synthesis gap) 
secara otomatis?
```

**Mengapa ditolak:**
- Ini pertanyaan **tukang/engineer**, bukan pertanyaan **peneliti**
- Tidak ada fenomena, tidak ada kesenjangan pengetahuan
- Pola "Bagaimana merancang X?" = spesifikasi proyek, bukan riset
- Tidak menunjukkan bahwa mahasiswa tahu di mana batas pengetahuan saat ini

## ✅ Versi Baru (YANG HARUS DITULIS)

Rumusan masalah harus mengikuti pola: **FENOMENA → CARA SAINS MENJELASKAN → KESENJANGAN → PERTANYAAN**

```markdown
## Rumusan Masalah

### Latar Belakang Masalah:

Identifikasi research gap merupakan tahap kritis dalam penelitian ilmiah 
yang membutuhkan kemampuan sintesis: peneliti membaca sejumlah literatur, 
membandingkan temuan-temuan, menalar secara induktif, dan menyimpulkan 
apa yang belum terjawab secara kolektif (Cooper, 1998; Booth et al., 2012).

Proses ini secara kognitif bersifat logis-induktif — peneliti tidak sekadar 
mencari "apa yang belum ada," melainkan mengevaluasi apakah temuan-temuan 
yang sudah ada secara kolektif sudah menghasilkan pemahaman yang utuh atau 
masih terfragmentasi dan inkonsisten.

Di sisi lain, pendekatan pipeline linear RAG+LLM (retrieve-then-generate) 
yang banyak digunakan saat ini beroperasi pada level representasi semantik 
— kesamaan vektor dan generasi probabilistik — tanpa mekanisme penalaran 
bertahap dan validasi logis. Pendekatan ini berisiko menghasilkan korelasi 
semu (spurious correlation) dan tidak mampu membedakan asosiasi semantik 
dari hubungan kausal yang sesungguhnya.

Paradigma AI Agent dengan kemampuan multi-step reasoning dan 
rule-based validation menawarkan pendekatan yang secara struktural lebih 
mendekati proses kognitif peneliti. Namun, belum diketahui secara memadai 
sejauh mana pendekatan agentic yang dilengkapi lapisan validasi logika 
formal mampu mendeteksi indikator-indikator synthesis gap, dan di mana 
batas kemampuannya dibandingkan penalaran manusia.

### Pertanyaan Penelitian:

1. Sejauh mana pendekatan agentic multi-step reasoning yang dilengkapi 
   rule-based validation mampu mendeteksi indikator synthesis gap 
   (fragmentasi, inkonsistensi, dan ketidaklengkapan kolektif) 
   dalam literatur ilmiah?

2. Bagaimana mekanisme pembeda asosiasi semantik dan hubungan logis 
   (kausalitas/kontradiksi) serta rule-based validation memengaruhi 
   tingkat akurasi dan false discovery rate dalam deteksi indikator 
   synthesis gap?

3. Apa batasan-batasan epistemologis pendekatan ini dibandingkan 
   dengan penalaran logis-induktif yang dilakukan peneliti manusia?
```

### Yang Harus Dilakukan:

- [ ] Tulis fenomena: bagaimana peneliti manusia mengidentifikasi gap
- [ ] Tulis cara sains menjelaskan: penalaran logis-induktif (Cooper, 1998)
- [ ] Tulis kesenjangan: pipeline linear RAG+LLM bersifat semantik & tanpa validasi logis
- [ ] Tulis pertanyaan yang menguji batas pengetahuan, BUKAN "bagaimana merancang"
- [ ] Gunakan kata "sejauh mana" atau "apa batasan" — bukan "bagaimana merancang"
- [ ] Tambahkan referensi: Cooper (1998), Booth et al. (2012)
- [ ] **Diskusikan draft dengan pembimbing sebelum finalisasi**

---

# 3. REVISI: DEFINISI SYNTHESIS GAP

## ❌ Versi Lama (DITOLAK)

```
Synthesis Gap — 3 Types:
  a. Unexplored Combinations (Method A + Domain B)
  b. Bridging Gaps (Concept X ↔ Concept Y)
  c. Resolution Gaps (Contradictions need resolution)
```

**Mengapa ditolak:**
- "Unexplored Combinations" = kawin silang dangkal — CNN + Medical Imaging bukan sintesis, itu hanya aplikasi
- Sintesis di level S2 = upaya logis **menyatukan literatur yang terpecah** menjadi kesimpulan konklusif
- Tidak ada jaminan bahwa kombinasi X+Y itu **logis** dan **bermakna**
- Definisi ini tidak ditemukan di literatur mainstream manapun

## ✅ Versi Baru (YANG HARUS DITULIS)

```markdown
## Definisi Synthesis Gap

### Definisi Berdasarkan Literatur:

Merujuk pada Cooper (1998) dan Booth, Sutton & Papaioannou (2012), 
synthesis gap didefinisikan sebagai:

> Kondisi di mana literatur yang ada tentang suatu fenomena BELUM 
> menghasilkan kesimpulan terpadu yang konklusif, baik karena 
> fragmentasi, inkonsistensi, atau ketidaklengkapan kolektif.

### Synthesis Gap BUKAN:
- ❌ Kombinasi metode-domain yang belum pernah ada (itu hanya "belum diterapkan")
- ❌ Topik yang belum diteliti sama sekali (itu knowledge gap)
- ❌ Saran "future work" di akhir paper (itu explicit gap)

### Synthesis Gap ADALAH:
- ✅ Literatur yang terpecah-pecah tanpa integrasi
- ✅ Temuan empiris yang saling bertentangan tanpa rekonsiliasi
- ✅ Banyak studi primer tetapi belum ada kerangka yang menyatukan
```

### Tiga Indikator Synthesis Gap:

| # | Indikator | Penjelasan | Contoh |
|---|-----------|------------|--------|
| 1 | **Fragmentasi** | Paper-paper membahas fenomena yang sama dari sudut berbeda tetapi tidak saling mengintegrasikan | 10 studi tentang dropout di online learning, masing-masing pakai teori berbeda, tidak ada yang menyatukan |
| 2 | **Inkonsistensi yang belum direkonsiliasi** | Temuan empiris saling bertentangan dan belum ada yang menyelesaikan | Paper A: gamification meningkatkan motivasi. Paper B: gamification menurunkan motivasi. Belum ada yang menjelaskan mengapa |
| 3 | **Ketidaklengkapan kolektif** | Aspek-aspek kritis dari fenomena belum dicakup secara bersama oleh literatur yang ada | Banyak studi tentang efektivitas blended learning, tapi tidak ada yang membahas aspek equity/aksesibilitas |

### Yang Harus Dilakukan:

- [ ] Buang definisi "Unexplored Combinations (Method A + Domain B)"
- [ ] Ganti dengan definisi mainstream dari Cooper (1998) dan Booth et al. (2012)
- [ ] Jelaskan apa yang BUKAN synthesis gap (beri kontras)
- [ ] Definisikan 3 indikator: fragmentasi, inkonsistensi, ketidaklengkapan
- [ ] Beri contoh nyata untuk setiap indikator
- [ ] Pastikan definisi konsisten di **seluruh** dokumen proposal

---

# 4. REVISI: BATASAN EPISTEMOLOGIS SISTEM

## ❌ Versi Lama

Proposal tidak pernah membahas batasan epistemologis. Klaim tersirat bahwa sistem **bisa** menemukan synthesis gap secara otomatis — seolah LLM+RAG bisa menalar seperti manusia.

## ✅ Yang Harus Ditambahkan

### Apa yang BISA Dilakukan Sistem (Level Semantik + Rule Engine):

| Kemampuan | Metode | Tingkat Keyakinan |
|-----------|--------|-------------------|
| Mendeteksi kesamaan topik antar paper | Semantic similarity (embedding) | ✅ Tinggi |
| Mendeteksi terminologi berbeda untuk konsep sama | Clustering semantik | ✅ Tinggi |
| Mendeteksi klaim yang saling bertentangan | NLI + Rule Engine | ⚠️ Sedang-Tinggi |
| Mengidentifikasi aspek absen dari paper tertentu | Coverage gap analysis | ⚠️ Sedang |
| Memvalidasi kelayakan logis suatu rekomendasi | Rule-Based Validation | ✅ Tinggi |
| Mengelompokkan paper berdasarkan pendekatan | Topic clustering | ✅ Tinggi |

### Apa yang TIDAK BISA Dilakukan Sistem:

| Keterbatasan | Alasan | Implikasi |
|-------------|--------|-----------|
| Menilai apakah suatu kombinasi ide **logis secara mendalam** | Membutuhkan penalaran kausal yang melampaui rule engine sederhana | Rule engine menangkap constraint eksplisit, bukan penilaian substantif |
| Memahami **mengapa** temuan saling bertentangan | Membutuhkan pemahaman konteks eksperimental mendalam | Sistem mendeteksi kontradiksi, bukan menjelaskan |
| Menentukan apakah gap **bermakna** untuk dijadikan riset | Membutuhkan scientific judgment | Pemeringkatan bersifat heuristik |
| Melakukan **penalaran induktif** sejati | LLM probabilistik, Rule Engine deduktif — keduanya bukan induktif | Sistem = alat bantu, bukan pengganti |

### Posisi Sistem:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   Peneliti Manusia                                      │
│   (penalaran induktif, penilaian substantif)            │
│                                                         │
│        ▲                                                │
│        │  menerima/menolak indikator                    │
│        │                                                │
│   ┌────┴─────────────────────────────┐                  │
│   │  SISTEM INI                      │                  │
│   │  (Agentic + Rule-Based)          │                  │
│   │                                  │                  │
│   │  Input: paper-paper              │                  │
│   │  Output: indikator synthesis gap │                  │
│   │  BUKAN: synthesis gap final      │                  │
│   └──────────────────────────────────┘                  │
│                                                         │
│   Sistem adalah ALAT BANTU (decision support)           │
│   BUKAN pengganti penalaran manusia                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Klaim yang TIDAK Dibuat:

1. ❌ Sistem TIDAK mengklaim mampu menalar secara induktif
2. ❌ Sistem TIDAK mengklaim menemukan gap yang pasti valid
3. ❌ Sistem TIDAK mengklaim menggantikan proses review manusia
4. ✅ Sistem mengklaim mampu menyajikan **indikator** yang mempercepat proses identifikasi oleh peneliti manusia
5. ✅ Sistem mengklaim mampu **menolak rekomendasi yang cacat logika** melalui rule engine

### Yang Harus Dilakukan:

- [ ] Tambahkan sesi "Batasan Epistemologis" di BAB I atau BAB III
- [ ] Jelaskan perbedaan: penalaran semantik vs induktif vs deduktif (rule-based)
- [ ] Buat tabel eksplisit: apa yang bisa vs tidak bisa
- [ ] Ubah klaim dari "mendeteksi gap" menjadi "mendeteksi **indikator** gap"
- [ ] Posisikan sistem sebagai **decision support**, bukan pengganti manusia
- [ ] Pastikan klaim ini konsisten di seluruh dokumen

---

# 5. REVISI: PERUBAHAN KE ARSITEKTUR AGENT

## Mengapa Harus Berubah ke Agent?

| Aspek | RAG+LLM Pipeline (Lama) | AI Agent (Baru) |
|-------|------------------------|-----------------|
| Kebaruan | ❌ Sudah banyak, tidak ada kebaruan mendasar | ⚠️ Agent untuk synthesis gap detection belum ada |
| Proses | Linear: Retrieve → Generate → selesai | Iteratif: Plan → Act → Observe → Reflect → Repeat |
| Self-verification | ❌ Tidak ada | ✅ Agent bisa cek ulang klaimnya sendiri |
| Tool use | ❌ Monolitik | ✅ Modular — panggil tool berbeda untuk sub-task berbeda |
| Validasi logis | ❌ Tidak ada | ✅ Rule Engine sebagai salah satu tool |
| Mendekati proses manusia | ❌ Tidak | ⚠️ Lebih mendekati (multi-step), tapi tetap bukan induktif |

## Arsitektur Agent yang Diusulkan

```
┌──────────┐    ┌──────────────────────────────────────┐
│  Query   │───▶│  AGENT ORCHESTRATOR                  │
│  (User)  │    │  (Planning, Reasoning, Decision)     │
└──────────┘    │                                      │
                │  Loop:                               │
                │    1. Observe (baca state)            │
                │    2. Think (plan langkah berikut)    │
                │    3. Act (panggil tool)              │
                │    4. Evaluate (cek hasil)            │
                │    5. Repeat atau Stop                │
                │                                      │
                │  Tools:                              │
                │    - RAG Retriever                    │
                │    - Paper Analyzer                   │
                │    - NLI Contradiction Checker        │
                │    - KG Querier (Fact Table)          │
                │    - Rule Engine (Logical Validator)  │
                │    - Self-Critic                      │
                └──────────────────────────────────────┘
```

## Contoh Agentic Workflow

```
INPUT: 5 papers tentang "gamification in education"

AGENT TRACE:
┌───────────────────────────────────────────────────────┐
│ Step 1 [PLAN]                                         │
│ "Saya perlu ekstrak temuan dari setiap paper"         │
│ → Call: PaperAnalyzer(paper_1..5)                     │
├───────────────────────────────────────────────────────┤
│ Step 2 [OBSERVE]                                      │
│ Paper 1: "Gamification increases engagement"          │
│ Paper 3: "Gamification has no significant effect"     │
│ "Dua temuan ini tampak bertentangan."                 │
├───────────────────────────────────────────────────────┤
│ Step 3 [ACT]                                          │
│ → Call: NLI_Detector(finding_1, finding_3)            │
│ → Result: CONTRADICTION (confidence: 0.87)            │
├───────────────────────────────────────────────────────┤
│ Step 4 [ACT]                                          │
│ "Apakah kontradiksi ini sudah diaddress?"             │
│ → Call: RAG_Retriever("reconciliation gamification    │
│          engagement contradictory findings")           │
│ → Result: Tidak ditemukan rekonsiliasi                │
├───────────────────────────────────────────────────────┤
│ Step 5 [ACT]                                          │
│ → Call: RuleEngine.validate(gap_indicator)             │
│ → Rule K2: Cek konsistensi dengan KG facts            │
│ → Result: PASSED (kontradiksi valid)                  │
├───────────────────────────────────────────────────────┤
│ Step 6 [EVALUATE]                                     │
│ → Call: SelfCritic("Apakah ini valid?")               │
│ → "Valid, tapi Paper 1 = K-12, Paper 3 = universitas. │
│    Kontradiksi mungkin context-dependent."             │
│ → Confidence adjusted: 0.72                           │
├───────────────────────────────────────────────────────┤
│ Step 7 [OUTPUT]                                       │
│ INDICATOR: Unresolved Inconsistency                   │
│ Papers: 1, 3                                          │
│ Confidence: 0.72                                      │
│ Requires Human Validation: TRUE                       │
└───────────────────────────────────────────────────────┘
```

## Novelty Statement (Jika Pakai Agent)

```
Penelitian terdahulu tentang automated research gap detection menggunakan 
pendekatan pipeline linear (retrieve-then-generate) yang:
(a) tidak merepresentasikan proses kognitif bertahap,
(b) tidak memiliki mekanisme validasi logis, dan
(c) tidak membedakan asosiasi semantik dari hubungan kausal.

Penelitian ini mengusulkan pendekatan Neuro-Symbolic Agentic System:
1. Arsitektur agentic multi-step reasoning (planning, acting, evaluating)
2. Rule-Based Validation Layer untuk menjamin konsistensi logis
3. Mekanisme pembeda asosiasi semantik vs hubungan kausal/kontradiktif
4. Knowledge Graph sebagai Fact Base (bukan hanya visualisasi)

Kebaruan bukan pada RAG atau LLM (yang sudah established), melainkan pada 
integrasi penalaran simbolik (rule engine + fact table) dengan penalaran 
neural (LLM agent) untuk domain spesifik synthesis gap detection.
```

## Risiko Beralih ke Agent

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| Scope membesar | 🔴 Tinggi | Batasi tools (maks 5-6), pakai framework existing (LangGraph) |
| Biaya API meningkat | 🟠 Sedang | Model lokal (Ollama) untuk dev, GPT-4 untuk final |
| Evaluasi lebih sulit | 🟠 Sedang | Tambahkan metrik reasoning quality |
| "Apa bedanya dengan ReAct/AutoGPT?" | 🟡 Rendah | Kebaruan = domain-specific + rule engine, bukan framework |
| Timeline mundur | 🟠 Sedang | Gunakan LangGraph (paling mature) |

### Yang Harus Dilakukan:

- [ ] Diskusikan perubahan ke Agent dengan pembimbing
- [ ] Pilih framework: LangGraph (rekomendasi) atau CrewAI
- [ ] Revisi arsitektur di BAB III — dari pipeline linear ke agentic
- [ ] Definisikan 5-6 tools yang akan digunakan agent
- [ ] Buat contoh agentic workflow trace minimal 1 skenario lengkap
- [ ] Tulis novelty statement yang jelas

---

# 6. REVISI: PEMBEDA ASOSIASI SEMANTIK vs HUBUNGAN LOGIS

## Masalah yang Diangkat Penguji

> "Bagaimana sistem membedakan antara konsep yang sekadar 'sering muncul bersama' (co-occurrence/asosiasi semantik) dengan konsep yang secara logis memiliki hubungan kausalitas atau kontradiksi?"

## Tiga Jenis Hubungan yang Harus Didefinisikan

| Jenis Hubungan | Definisi | Contoh | Detectable via Semantik? |
|----------------|----------|--------|--------------------------|
| **Co-occurrence** | Dua konsep sering muncul bersama tanpa hubungan kausal | "Python" dan "machine learning" | ✅ Terdeteksi, tapi BUKAN hubungan logis |
| **Kausalitas** | Konsep A secara logis memengaruhi Konsep B | "Overfitting → need for regularization" | ❌ Tidak bisa dari embedding saja |
| **Kontradiksi** | Temuan tentang A bertentangan dengan temuan tentang B | "Method X meningkatkan akurasi" vs "Method X menurunkan akurasi" | ⚠️ Parsial via NLI |

## Mekanisme Pembeda (Tiga Lapis)

```
Kandidat hubungan (dari semantic similarity)
    │
    ▼
[Lapis 1] SEMANTIC FILTERING
    │  Similarity > threshold? 
    │  Ya → lanjut     Tidak → buang
    ▼
[Lapis 2] EVIDENCE EXTRACTION (LLM Agent)
    │  Cari bukti eksplisit dalam teks:
    │  • Penanda kausal: "causes", "leads to", "results in", "because"
    │  • Penanda kontradiksi: "however", "contradicts", "in contrast"
    │  • Tidak ada penanda → CO-OCCURRENCE ONLY
    │  Ada bukti? 
    │  Ya → lanjut     Tidak → label "co-occurrence only"
    ▼
[Lapis 3] RULE-BASED VALIDATION
    │  Cek terhadap aturan logika di Fact Base (KG)
    │  Lolos?
    │  Ya → VALID RELATION     Tidak → REJECTED + alasan
```

### Penanda Linguistik yang Digunakan

**Penanda Kausal:**
```
"causes", "leads to", "results in", "because", "therefore", 
"consequently", "due to", "effect of", "contributes to", 
"enables", "prevents", "inhibits"
```

**Penanda Kontradiksi:**
```
"however", "contradicts", "in contrast", "whereas", 
"on the other hand", "inconsistent with", "conflicts with", 
"contrary to", "disputes", "challenges"
```

### Yang Harus Dilakukan:

- [ ] Tambahkan sub-bab "Mekanisme Pembeda Asosiasi Semantik vs Hubungan Logis" di BAB III
- [ ] Definisikan 3 jenis hubungan: co-occurrence, kausalitas, kontradiksi
- [ ] Jelaskan mekanisme 3 lapis (semantic → evidence → rule-based)
- [ ] Buat diagram alir pembeda
- [ ] Daftarkan penanda linguistik kausal dan kontradiksi
- [ ] Implementasikan `RelationClassifier` di kode
- [ ] Buat unit test: pastikan co-occurrence TIDAK diklasifikasikan sebagai kausal

---

# 7. REVISI: RULE-BASED VALIDATION LAYER

## Masalah yang Diangkat Penguji

> "Tambahkan komponen Rule-Based Validation (seperti prinsip pada Prolog atau Expert Systems) di atas output RAG."
>
> "Gunakan Knowledge Graph bukan hanya untuk pencarian (retrieval), tetapi sebagai Knowledge Base (Fakta)."
>
> Contoh: Jika Metode A butuh sumber daya besar, maka ia tidak logis disarankan untuk Masalah B yang berbasis perangkat mobile. Rule Engine harus mampu membatalkan rekomendasi tersebut.

## Arsitektur Rule Engine

```
                ┌──────────────────────────┐
                │    RULE ENGINE            │
                │                           │
                │  ┌─────────────────────┐  │
                │  │ FACT BASE            │  │
                │  │ (dari Knowledge      │  │
                │  │  Graph — SPO Triples) │  │
                │  └─────────┬───────────┘  │
                │            │               │
                │  ┌─────────▼───────────┐  │
                │  │ RULE BASE            │  │
                │  │                      │  │
                │  │ R1: Feasibility      │  │
                │  │ R2: Causality        │  │
                │  │ R3: Consistency      │  │
                │  └─────────┬───────────┘  │
                │            │               │
                │  ┌─────────▼───────────┐  │
                │  │ INFERENCE ENGINE     │  │
                │  │                      │  │
                │  │ Forward chaining:    │  │
                │  │ Facts + Rules →      │  │
                │  │ Accept/Reject        │  │
                │  └─────────────────────┘  │
                └──────────────────────────┘
```

## Tiga Kategori Aturan Logika

### Kategori 1: Aturan Kelayakan (Feasibility Rules)

| ID | Aturan | Formalisasi | Contoh |
|----|--------|-------------|--------|
| F1 | Kompatibilitas sumber daya | `IF method.resource_req = "high" AND problem.constraint = "low_resource" THEN REJECT` | LLM sarankan "GPT-4 untuk edge device" → DITOLAK |
| F2 | Kompatibilitas data | `IF method.data_req = "large_labeled" AND domain.data = "scarce" THEN FLAG` | "Supervised DL untuk rare disease" → FLAG |
| F3 | Kompatibilitas skala | `IF method.scalability = "single_machine" AND problem.scale = "distributed" THEN REJECT` | "In-memory processing untuk big data" → DITOLAK |

### Kategori 2: Aturan Kausalitas (Causality Rules)

| ID | Aturan | Formalisasi | Contoh |
|----|--------|-------------|--------|
| C1 | Bukti kausal minimal | `IF relation.type = "CAUSAL" AND evidence_count < 2 THEN DOWNGRADE to "CORRELATION"` | Hanya 1 paper menyebut hubungan → downgrade |
| C2 | Arah kausalitas | `IF cause.temporal_order > effect.temporal_order THEN REJECT` | "Hasil eksperimen menyebabkan hipotesis" → DITOLAK |
| C3 | Confounding check | `IF relation.type = "CAUSAL" AND exists(confounding_var) THEN FLAG` | A→B tapi ada C yang mungkin menyebabkan keduanya → FLAG |

### Kategori 3: Aturan Konsistensi (Consistency Rules)

| ID | Aturan | Formalisasi | Contoh |
|----|--------|-------------|--------|
| K1 | Non-kontradiksi internal | `IF output.claim_A CONTRADICTS output.claim_B THEN FLAG` | Sistem rekomendasikan X di poin 1 tapi tolak X di poin 3 → FLAG |
| K2 | Konsistensi dengan fakta KG | `IF output.claim NOT_SUPPORTED_BY kg.facts THEN DOWNGRADE confidence` | Klaim tidak didukung fakta KG → confidence turun |
| K3 | Transitivitas | `IF A→B AND B→C BUT output says A—/→C THEN FLAG` | "A improves B" + "B improves C" tapi output bilang "A worsens C" → FLAG |

### Tiga Kemungkinan Verdict

| Verdict | Arti | Aksi |
|---------|------|------|
| ✅ **PASS** | Output lolos semua aturan | Tampilkan ke pengguna dengan confidence score |
| ⚠️ **FLAG** | Output melanggar aturan non-kritis | Tampilkan ke pengguna dengan peringatan "perlu review manusia" |
| ❌ **REJECT** | Output melanggar aturan kritis | JANGAN tampilkan ke pengguna + berikan alasan penolakan |

### Yang Harus Dilakukan:

- [ ] Tambahkan sub-bab "Rule-Based Validation Layer" di BAB III
- [ ] Definisikan 3 kategori aturan: Feasibility, Causality, Consistency
- [ ] Buat tabel aturan lengkap (minimal 9 aturan: F1-F3, C1-C3, K1-K3)
- [ ] Jelaskan mekanisme: Facts (KG) + Rules → Inference → Accept/Reject/Flag
- [ ] Gambarkan diagram arsitektur Rule Engine
- [ ] Berikan contoh skenario lengkap (input → LLM output → rule check → verdict)
- [ ] Implementasikan `RuleEngine` class di kode
- [ ] Tambahkan referensi: Garcez et al. (2019) tentang Neuro-Symbolic AI

---

# 8. REVISI: DIAGRAM ALIR METODOLOGI

## ❌ Diagram Lama (DITOLAK — Halaman 13)

```
Input → PDF Parse → Chunk → Embed → RAG Retrieve → LLM Generate → Output
                                                      ▲
                                                (Black Box)
                                            Tidak ada validasi
```

**Mengapa ditolak:** Terlalu linear, bergantung pada Black Box LLM, tidak ada validasi logis.

## ✅ Diagram Baru (4 FASE)

```
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 1: INGESTION                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────────┐  │
│  │ Input    │──▶│ PDF      │──▶│ Section  │──▶│ Chunk &    │  │
│  │ Papers   │   │ Parser   │   │ Splitter │   │ Embed      │  │
│  │ (3-10)   │   │          │   │          │   │ (SciBERT)  │  │
│  └──────────┘   └──────────┘   └──────────┘   └─────┬──────┘  │
│                                                      │         │
│                                                      ▼         │
│                                                ┌──────────┐    │
│                                                │ Vector   │    │
│                                                │ Store    │    │
│                                                └──────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                FASE 2: FACT EXTRACTION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │ Entity Extractor │───▶│ Fact Table       │                   │
│  │ (SciSpaCy + LLM) │    │ Constructor      │                   │
│  │                  │    │                  │                   │
│  │ Extract:         │    │ Generate SPO:    │                   │
│  │ • Methods        │    │ (S, P, O)        │                   │
│  │ • Concepts       │    │ triples          │                   │
│  │ • Findings       │    │                  │                   │
│  │ • Constraints    │    │ → Knowledge      │                   │
│  └──────────────────┘    │   Graph (KG)     │                   │
│                          └────────┬─────────┘                   │
│                                   ▼                             │
│                          ┌──────────────────┐                   │
│                          │ KNOWLEDGE GRAPH  │                   │
│                          │ (Fact Base)      │                   │
│                          │ Nodes: entities  │                   │
│                          │ Edges: relations │                   │
│                          └──────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              FASE 3: AGENTIC ANALYSIS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                AGENT ORCHESTRATOR                        │   │
│  │  Plan → Act → Observe → Reflect → Repeat/Stop           │   │
│  │                                                          │   │
│  │  Tools:                                                  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │   │
│  │  │ RAG      │ │ Paper    │ │ NLI      │ │ KG         │  │   │
│  │  │ Retriever│ │ Analyzer │ │ Checker  │ │ Querier    │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │   │
│  │                                                          │   │
│  │  Output: candidate gap indicators + evidence + reasoning │   │
│  └─────────────────────────────┬────────────────────────────┘   │
│                                │                                │
│                     ┌──────────▼──────────┐                     │
│                     │  RAW LLM OUTPUT     │                     │
│                     │  (belum divalidasi)  │                     │
│                     └──────────┬──────────┘                     │
└────────────────────────────────┼─────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│       FASE 4: LOGICAL CONSISTENCY CHECKER  ◄── KOMPONEN BARU   │
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
│  │                   │ ✅ PASS      │                       │   │
│  │                   │ ⚠️ FLAG      │                       │   │
│  │                   │ ❌ REJECT    │                       │   │
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

### Yang Harus Dilakukan:

- [ ] Hapus diagram lama di Halaman 13
- [ ] Gambar ulang diagram 4 fase di atas (gunakan draw.io atau Lucidchart)
- [ ] Pastikan ada blok **Logical Consistency Checker** setelah LLM output
- [ ] Tunjukkan 3 kemungkinan output: PASS, FLAG, REJECT
- [ ] Jelaskan setiap fase dalam narasi di BAB III
- [ ] Buat versi diagram yang bisa dicetak untuk lampiran

---

# 9. REVISI: SKEMA FAKTA KNOWLEDGE GRAPH (TABEL SPO)

## Masalah yang Diangkat Penguji

> "Saya ingin melihat di Bab III bagaimana Anda mentransformasi teks jurnal yang tidak terstruktur menjadi Tabel Fakta (Predikat-Subjek-Objek). Tanpa tabel fakta yang jelas, Knowledge Graph Anda hanya akan menjadi alat visualisasi, bukan alat penalaran."

## Proses Transformasi Teks ke Tabel Fakta

```
Teks Asli (tidak terstruktur)
    │
    ▼
[Tahap 1] Entity Extraction (SciSpaCy + LLM)
    │  Identifikasi entitas: metode, konsep, dataset, temuan, constraint
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
Tabel Fakta (terstruktur) → masuk ke Knowledge Graph
```

## Ontologi: Tipe Entitas (Node)

| Tipe | Deskripsi | Contoh | Properties |
|------|-----------|--------|------------|
| METHOD | Metode/algoritma/teknik | "CNN", "Random Forest", "BERT" | resource_requirement, scalability, data_requirement |
| CONCEPT | Konsep/teori/framework | "Transfer Learning", "Attention" | abstraction_level |
| DOMAIN | Domain/bidang penerapan | "Medical Imaging", "NLP" | data_availability, constraint |
| FINDING | Temuan empiris | "CNN achieves 95% accuracy" | paper_source, confidence, sample_size |
| DATASET | Dataset yang digunakan | "ImageNet", "CIFAR-10" | size, type, availability |
| METRIC | Metrik evaluasi | "Accuracy", "F1-Score" | — |
| PAPER | Paper sumber | "ResNet (He et al., 2016)" | year, venue, citation_count |
| CONSTRAINT | Keterbatasan/syarat | "High compute", "Low resource" | — |

## Ontologi: Tipe Relasi (Edge/Predikat)

| Predikat | Deskripsi | Domain → Range | Contoh |
|----------|-----------|----------------|--------|
| USES_METHOD | Paper menggunakan metode | PAPER → METHOD | (Paper_A, USES_METHOD, CNN) |
| PROPOSES | Paper mengusulkan sesuatu baru | PAPER → METHOD/CONCEPT | (Paper_A, PROPOSES, ResNet) |
| APPLIES_TO | Metode diterapkan pada domain | METHOD → DOMAIN | (CNN, APPLIES_TO, Medical_Imaging) |
| ACHIEVES | Metode mencapai hasil | METHOD → FINDING | (ResNet, ACHIEVES, "95% accuracy") |
| REQUIRES_RESOURCE | Metode butuh sumber daya | METHOD → CONSTRAINT | (GPT-4, REQUIRES_RESOURCE, high_compute) |
| REQUIRES_DATA | Metode butuh jenis data | METHOD → CONSTRAINT | (Supervised_DL, REQUIRES_DATA, large_labeled) |
| IMPROVES | Metode A meningkatkan metode B | METHOD → METHOD | (ResNet, IMPROVES, VGG) |
| CONTRADICTS | Temuan A bertentangan dgn B | FINDING → FINDING | (Finding_1, CONTRADICTS, Finding_2) |
| EXTENDS | Konsep A memperluas konsep B | CONCEPT → CONCEPT | (Transformer, EXTENDS, Attention) |
| EVALUATED_ON | Metode dievaluasi pada dataset | METHOD → DATASET | (BERT, EVALUATED_ON, GLUE) |
| HAS_CONSTRAINT | Domain punya keterbatasan | DOMAIN → CONSTRAINT | (Mobile_App, HAS_CONSTRAINT, low_resource) |
| DISCUSSES | Paper membahas konsep | PAPER → CONCEPT | (Paper_B, DISCUSSES, Federated_Learning) |

## Contoh Lengkap: Transformasi Teks ke Tabel Fakta

### Input (Teks Asli dari Paper):

> "We propose a novel approach using Convolutional Neural Networks (CNN) for medical image segmentation. Our method achieves 92.3% Dice coefficient on the BraTS dataset. However, the model requires significant GPU memory (>16GB), which limits its deployment on edge devices. In contrast to Smith et al. (2023) who reported 88.1% using traditional U-Net, our approach shows improvement but at higher computational cost."

### Output (Tabel Fakta SPO):

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

### Fakta Turunan (Inferred via Rule Engine):

| # | Subject | Predicate | Object | Inferred By Rule |
|---|---------|-----------|--------|------------------|
| 10 | CNN_Segmentation | INFEASIBLE_FOR | Edge_Deployment | F1: IF REQUIRES_RESOURCE(high_compute) AND HAS_CONSTRAINT(edge_device) THEN INFEASIBLE |

### Contoh Penalaran Rule Engine Menggunakan Tabel Fakta:

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

  VERDICT: ❌ REJECTED
  REASON: "CNN_Segmentation requires GPU_16GB+ (Fact #5) but mobile 
           health app has edge device limitation (Fact #6). 
           Recommendation is infeasible."
```

### Yang Harus Dilakukan:

- [ ] Tambahkan sub-bab "Skema Fakta Knowledge Graph" di BAB III
- [ ] Definisikan Ontologi: tipe entitas (8 tipe) + tipe relasi (12 predikat)
- [ ] Berikan contoh transformasi teks → tabel SPO (minimal 1 contoh lengkap seperti di atas)
- [ ] Jelaskan 3 tahap: Entity Extraction → Relation Extraction → Triple Construction
- [ ] Tunjukkan contoh fakta turunan (inferred facts) dari rule engine
- [ ] Tunjukkan contoh skenario penalaran: fakta + aturan → kesimpulan
- [ ] Implementasikan `FactTable` dan `FactExtractor` di kode

---

# 10. REVISI: FRAMEWORK EVALUASI

## ❌ Versi Lama

Evaluasi hanya mengukur Precision/Recall — seolah gap bisa dinilai benar/salah secara biner.

## ✅ Metrik Tambahan yang Harus Ditambahkan

| # | Metrik | Deskripsi | Cara Mengukur |
|---|--------|-----------|---------------|
| 1 | **Expert Acceptance Rate** | Berapa % indikator yang dinilai pakar sebagai genuine synthesis gap | Pakar review setiap indikator → accept/reject |
| 2 | **Logical Coherence Score** | Apakah indikator logis/masuk akal | Pakar beri skor 1-5 per indikator |
| 3 | **Actionability Score** | Apakah indikator cukup spesifik untuk ditindaklanjuti jadi riset | Pakar beri skor 1-5 |
| 4 | **False Discovery Rate** | Berapa % indikator yang ternyata bukan gap | 1 - acceptance rate |
| 5 | **Semantic vs Human Gap** | Seberapa jauh hasil deteksi semantik dari penilaian manusia | Korelasi Spearman ranking sistem vs ranking pakar |
| 6 | **Rule Engine Rejection Rate** | Berapa % output LLM yang ditolak rule engine | Count rejected / total output |
| 7 | **Rule Engine Precision** | Dari yang ditolak, berapa % memang pantas ditolak | Pakar review item rejected |

## Hipotesis yang Harus Diuji

### Hipotesis Lama (Tetap):
- **H1:** RAG > LLM-only (mengurangi hallucination)
- **H2:** Comparative analysis > Single-paper analysis
- **H3:** With KG > Without KG

### Hipotesis Baru (TAMBAHKAN):
- **H4:** Expert acceptance rate ≥ 50% (lebih dari separuh indikator dinilai genuine oleh pakar)
- **H5:** Logical coherence score ≥ 3.5/5 (indikator masuk akal secara logis)
- **H6:** Agentic system > Pipeline linear RAG+LLM (pada metrik acceptance rate)
- **H7:** Dengan Rule Engine > Tanpa Rule Engine (mengurangi false discovery rate)
- **H8:** Sistem mengurangi waktu identifikasi gap dibandingkan proses manual (user study)

## Perubahan di Ground Truth

```
LAMA:
- Pakar menentukan "expected gaps" → sistem dicocokkan

BARU:
- Pakar JUGA menilai output sistem (bukan hanya dibandingkan expected)
- Pakar memberi label per indikator:
    ✅ "genuine gap" 
    ⚠️ "trivial" 
    ❌ "illogical" 
    ⏭️ "already addressed"
- Hitung acceptance rate dari label tersebut
```

### Yang Harus Dilakukan:

- [ ] Tambahkan 7 metrik evaluasi baru ke BAB III
- [ ] Tambahkan hipotesis H4-H8
- [ ] Revisi ground truth: pakar juga menilai output sistem
- [ ] Revisi success criteria: tambahkan "acceptance rate ≥ 50%"
- [ ] Rencanakan user study: waktu dengan sistem vs tanpa sistem

---

# 11. REVISI: TINJAUAN PUSTAKA & REFERENSI BARU

## Referensi yang WAJIB Ditambahkan

### Tentang Synthesis & Literature Review:

1. Cooper, H. (1998). *Synthesizing Research: A Guide for Literature Reviews* (3rd ed.). Sage Publications.
2. Booth, A., Sutton, A., & Papaioannou, D. (2012). *Systematic Approaches to a Successful Literature Review*. Sage.
3. Pare, G., Trudel, M. C., Jaana, M., & Kitsiou, S. (2015). Synthesizing Information Systems Knowledge: A Typology of Literature Reviews. *Information & Management*, 52(2), 183-199.

### Tentang Research Gap Identification:

4. Muller-Bloch, C., & Kranz, J. (2015). A Framework for Rigorously Identifying Research Gaps in Qualitative Literature Reviews. *ICIS 2015 Proceedings*.
5. Robinson, K. A., Saldanha, I. J., & McKoy, N. A. (2011). Development of a Framework to Identify Research Gaps from Systematic Reviews. *Journal of Clinical Epidemiology*.

### Tentang Neuro-Symbolic AI:

6. Garcez, A., et al. (2019). Neural-Symbolic Computing: An Effective Methodology for Principled Integration of Machine Learning and Reasoning. *Journal of Applied Logics*.
7. Marcus, G. (2020). The Next Decade in AI: Four Steps Towards Robust Artificial Intelligence. *arXiv:2002.06177*.

### Tentang Batas Kemampuan LLM:

8. Marcus, G., & Davis, E. (2020). *Rebooting AI: Building Artificial Intelligence We Can Trust*. Vintage.
9. Bender, E. M., & Koller, A. (2020). Climbing towards NLU: On Meaning, Form, and Understanding in the Age of Data. *ACL 2020*. (Menjelaskan mengapa model bahasa tidak "memahami")

### Tentang Knowledge Graph & Fact Extraction:

10. Ji, S., et al. (2021). A Survey on Knowledge Graphs: Representation, Acquisition, and Applications. *IEEE TNNLS*.
11. Bosselut, A., et al. (2019). COMET: Commonsense Transformers for Automatic Knowledge Graph Construction. *ACL 2019*.

### Tentang Rule-Based Systems:

12. Buchanan, B. G., & Shortliffe, E. H. (1984). *Rule-Based Expert Systems*. Addison-Wesley.
13. Giarratano, J. C., & Riley, G. D. (2005). *Expert Systems: Principles and Programming* (4th ed.). Thomson.

### Tentang NLI untuk Contradiction Detection:

14. Bowman, S., et al. (2015). A Large Annotated Corpus for Learning Natural Language Inference. *EMNLP 2015*.
15. Williams, A., et al. (2018). A Broad-Coverage Challenge Corpus for Sentence Understanding through Inference. *NAACL 2018*.

## Sub-bab Baru di BAB II (Tinjauan Pustaka)

- [ ] Tambahkan: "Definisi Sintesis dalam Konteks Literature Review"
- [ ] Tambahkan: "Batasan Penalaran pada Sistem Berbasis LLM"
- [ ] Tambahkan: "Neuro-Symbolic AI: Integrasi Penalaran Neural dan Simbolik"
- [ ] Tambahkan: "Knowledge Graph sebagai Fact Base untuk Penalaran"
- [ ] Revisi sub-bab "Research Gap" — gunakan definisi dari Cooper & Booth
- [ ] Hapus/revisi klaim bahwa sistem bisa "menemukan gap secara otomatis"

---

# 12. PERUBAHAN FILE KODE

## Dokumen Proposal (Perubahan di Naskah)

| Bagian Proposal | Aksi | Status |
|-----------------|------|--------|
| BAB I - Rumusan Masalah | REVISI: fenomena→kesenjangan→pertanyaan | ⬜ |
| BAB I - Batasan Epistemologis | TAMBAH BARU | ⬜ |
| BAB II - Definisi Synthesis Gap | REVISI: mainstream (Cooper, Booth) | ⬜ |
| BAB II - Sub-bab Neuro-Symbolic AI | TAMBAH BARU | ⬜ |
| BAB II - Sub-bab Batasan LLM | TAMBAH BARU | ⬜ |
| BAB II - Referensi Baru (15 referensi) | TAMBAH | ⬜ |
| BAB III - Diagram Alir (Halaman 13) | REVISI: 4 fase + Logical Consistency Checker | ⬜ |
| BAB III - Pembeda Asosiasi vs Logis | TAMBAH BARU | ⬜ |
| BAB III - Rule-Based Validation Layer | TAMBAH BARU | ⬜ |
| BAB III - Skema Fakta KG (Tabel SPO) | TAMBAH BARU | ⬜ |
| BAB III - Contoh Transformasi Teks→SPO | TAMBAH BARU | ⬜ |
| BAB III - Contoh Penalaran Rule Engine | TAMBAH BARU | ⬜ |
| BAB III - Framework Evaluasi | REVISI: tambah 7 metrik + H4-H8 | ⬜ |

## Kode (File Baru yang Harus Dibuat)

```
backend/app/core/
├── analysis/
│   ├── __init__.py
│   ├── comparative_analyzer.py       # REVISI - pakai definisi baru
│   ├── element_extractor.py          # REVISI
│   └── relation_classifier.py        # BARU - pembeda asosiasi vs logis
├── knowledge/
│   ├── __init__.py
│   ├── kg_constructor.py             # REVISI - pakai ontologi SPO
│   ├── fact_table.py                 # BARU - Tabel Fakta (SPO triples)
│   └── fact_extractor.py             # BARU - Ekstraksi fakta dari teks
├── validation/
│   ├── __init__.py
│   └── rule_engine.py                # BARU - Rule-Based Validation Layer
├── gaps/
│   ├── __init__.py
│   ├── indicator_detector.py         # BARU (ganti synthesis_detector.py)
│   ├── fragmentation_detector.py     # BARU
│   ├── inconsistency_detector.py     # BARU
│   └── incompleteness_detector.py    # BARU
└── agents/
    ├── __init__.py
    ├── coordinator.py                # REVISI - jadi agent orchestrator
    └── tools/                        # BARU - tools untuk agent
        ├── __init__.py
        ├── rag_tool.py
        ├── paper_analyzer_tool.py
        ├── nli_checker_tool.py
        ├── kg_querier_tool.py
        └── self_critic_tool.py
```

## Kode (File yang Harus Dimodifikasi)

| File | Perubahan |
|------|-----------|
| `backend/app/core/agents/coordinator.py` | Ubah dari pipeline linear ke agent orchestrator (LangGraph) |
| `backend/app/core/knowledge_graph/graph_builder.py` | Ubah ke ontologi SPO yang baru |
| `backend/app/core/gap_detection/analyzer.py` | Ubah ke deteksi 3 indikator (fragmentasi, inkonsistensi, ketidaklengkapan) |
| `backend/app/api/routes/analysis.py` | Tambah field `rule_engine_verdict` di response |
| `backend/app/models/responses.py` | Tambah model untuk `RuleEngineResult`, `FactTriple`, `GapIndicator` |
| `backend/config.yaml` | Tambah config untuk rule engine dan fact extraction |

---

# 13. TIMELINE PENGERJAAN

## ⚠️ PERINGATAN PENTING

```
URUTAN YANG BENAR:

1. ✍️  Tulis narasi di proposal DULU (semua revisi BAB I, II, III)
2. 📊  Gambar diagram DULU (diagram alir 4 fase)
3. 📋  Buat tabel aturan dan contoh SPO DULU
4. 👨‍🏫  Diskusikan dengan pembimbing — DAPATKAN PERSETUJUAN
5. ✅  Setelah pembimbing setuju → baru coding
6. 🧪  Coding + unit test
7. 🔄  Update proposal jika ada perubahan saat coding

JANGAN LANGSUNG CODING. Penguji mengkritik KONSEP, bukan KODE.
```

## Timeline Detail

| Minggu | Tugas | Output | Status |
|--------|-------|--------|--------|
| **Minggu 1** (2-8 Mar) | Baca Cooper (1998) & Booth (2012) | Pemahaman definisi mainstream | ⬜ |
| **Minggu 1** | Tulis ulang rumusan masalah | Draft BAB I revisi | ⬜ |
| **Minggu 1** | Tulis ulang definisi synthesis gap | Draft BAB II revisi | ⬜ |
| **Minggu 1** | Tulis batasan epistemologis | Draft sesi batasan | ⬜ |
| **Minggu 1** | **Diskusi dengan pembimbing** | **Persetujuan arah revisi** | ⬜ |
| **Minggu 2** (9-15 Mar) | Tulis sub-bab pembeda asosiasi vs logis | Draft BAB III | ⬜ |
| **Minggu 2** | Tulis sub-bab Rule-Based Validation Layer | Draft BAB III | ⬜ |
| **Minggu 2** | Tulis sub-bab Skema Fakta KG (SPO) + contoh | Draft BAB III | ⬜ |
| **Minggu 2** | Gambar diagram alir baru (4 fase) | Diagram (draw.io) | ⬜ |
| **Minggu 3** (16-22 Mar) | Revisi framework evaluasi + hipotesis baru | Draft BAB III | ⬜ |
| **Minggu 3** | Tambahkan referensi baru (15 referensi) | Draft BAB II revisi | ⬜ |
| **Minggu 3** | Review keseluruhan proposal + konsistensi | Proposal revisi lengkap | ⬜ |
| **Minggu 3** | **Submit ke pembimbing untuk review** | **Feedback pembimbing** | ⬜ |
| **Minggu 4** (23-29 Mar) | Perbaiki berdasarkan feedback pembimbing | Proposal final | ⬜ |
| **Minggu 4** | Mulai implementasi `FactTable` + `FactExtractor` | Kode + unit test | ⬜ |
| **Minggu 5** (30 Mar-5 Apr) | Implementasi `RuleEngine` | Kode + unit test | ⬜ |
| **Minggu 5** | Implementasi `RelationClassifier` | Kode + unit test | ⬜ |
| **Minggu 6** (6-12 Apr) | Refactor `coordinator.py` ke Agent (LangGraph) | Kode + integration test | ⬜ |
| **Minggu 6** | Implementasi agent tools | Kode + unit test | ⬜ |
| **Minggu 7** (13-19 Apr) | Integrasi semua komponen + system test | Prototype working | ⬜ |
| **Minggu 7** | Update proposal jika ada perubahan | Proposal v3 | ⬜ |

---

# 14. CHECKLIST FINAL

## Sebelum Submit Revisi Proposal ke Pembimbing:

### Konseptual (PALING PENTING)
- [ ] Rumusan masalah sudah pola fenomena→kesenjangan→pertanyaan
- [ ] Definisi synthesis gap sesuai Cooper (1998) & Booth (2012)
- [ ] Ada sesi batasan epistemologis yang eksplisit
- [ ] Klaim sistem = "alat bantu deteksi indikator", bukan "pengganti manusia"
- [ ] Istilah "synthesis gap" konsisten di seluruh dokumen
- [ ] Novelty statement jelas (Neuro-Symbolic Agentic, bukan sekadar RAG+LLM)

### Arsitektur
- [ ] Diagram alir 4 fase sudah digambar
- [ ] Ada blok "Logical Consistency Checker" di diagram
- [ ] Mekanisme pembeda asosiasi semantik vs hubungan logis sudah dijelaskan
- [ ] Rule-Based Validation Layer sudah didefinisikan (3 kategori, 9 aturan)
- [ ] Skema Fakta KG (SPO) sudah didefinisikan (8 tipe entitas, 12 predikat)
- [ ] Contoh transformasi teks→SPO sudah ditulis
- [ ] Contoh penalaran rule engine sudah ditulis

### Evaluasi
- [ ] 7 metrik evaluasi baru sudah ditambahkan
- [ ] Hipotesis H4-H8 sudah ditambahkan
- [ ] Ground truth sudah direvisi (pakar juga menilai output)
- [ ] Success criteria mencakup expert acceptance rate

### Referensi
- [ ] 15 referensi baru sudah ditambahkan
- [ ] Sub-bab baru di BAB II sudah ditulis
- [ ] Semua klaim didukung referensi

### Final
- [ ] **Sudah didiskusikan dan disetujui pembimbing**
- [ ] Tidak ada klaim "menemukan gap secara otomatis" yang tersisa
- [ ] Tidak ada definisi "Unexplored Combinations (Method A + Domain B)" yang tersisa
- [ ] Tidak ada diagram linear black-box yang tersisa

---

## ⛔ HAL-HAL YANG TIDAK BOLEH DILAKUKAN

```
❌ JANGAN lanjut coding sebelum konsep disetujui pembimbing
❌ JANGAN gunakan istilah "menemukan gap secara otomatis"
❌ JANGAN definisikan synthesis gap sebagai "kombinasi Method A + Domain B"
❌ JANGAN klaim sistem bisa menalar seperti manusia
❌ JANGAN abaikan batasan epistemologis
❌ JANGAN gunakan rumusan masalah pola "Bagaimana merancang/membangun..."
❌ JANGAN buat diagram linear tanpa validasi logis
❌ JANGAN gunakan KG hanya sebagai visualisasi tanpa tabel fakta SPO
❌ JANGAN evaluasi hanya dengan Precision/Recall tanpa expert acceptance rate
```

---

*Dokumen ini adalah master reference untuk seluruh revisi. Update status checklist setiap kali menyelesaikan satu item.*
