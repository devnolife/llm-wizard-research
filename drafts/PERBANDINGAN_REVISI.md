# 📊 PERBANDINGAN PROPOSAL LAMA vs PROPOSAL REVISI

**Dokumen Perbandingan Detail**
**Tanggal:** Juni 2025
**Mahasiswa:** Andi Agung Dwi Arya B (D082251054)
**Program:** Magister Teknik Informatika — Universitas Hasanuddin

---

## 1. Ringkasan Perubahan

Revisi proposal ini merupakan perubahan **fundamental dan menyeluruh**, bukan sekadar perbaikan kosmetik. Perubahan didorong oleh kritik penguji yang menyoroti kelemahan konseptual, arsitektural, dan metodologis pada proposal awal. Berikut ringkasan perubahan besar yang terjadi:

| # | Aspek | Perubahan |
|---|-------|-----------|
| 1 | **Judul** | Dari "Intelligent Research Gap Analyzer: Sistem Otomatis Berbasis RAG dan LLM" menjadi pendekatan **Neuro-Symbolic Agentic** untuk deteksi *synthesis gap* |
| 2 | **Paradigma** | Dari *pipeline linear* RAG+LLM → menjadi **arsitektur Agentic multi-step reasoning** dengan validasi simbolik |
| 3 | **Rumusan Masalah** | Dari pola "*Bagaimana merancang/membangun...*" → menjadi pola "*Sejauh mana...*" (fenomena → kesenjangan → pertanyaan) |
| 4 | **Definisi Synthesis Gap** | Dari definisi naif ("kombinasi Method A + Domain B") → menjadi definisi berbasis Cooper (1998) & Booth (2012) dengan 3 indikator terukur |
| 5 | **Batasan Epistemologis** | **BARU** — bagian eksplisit tentang apa yang bisa dan tidak bisa dilakukan sistem |
| 6 | **Arsitektur** | Dari 3 tahap linear (Input → Proses → Output) → menjadi **4 Fase** dengan Logical Consistency Checker |
| 7 | **Rule Engine** | **BARU** — 9 aturan dalam 3 kategori (Feasibility, Causality, Consistency) |
| 8 | **Knowledge Graph** | Dari sekadar visualisasi → menjadi **Fact Base** dengan ontologi eksplisit (8 tipe entitas, 12+ predikat, tabel SPO) |
| 9 | **Mekanisme Pembeda** | **BARU** — 3 lapis pembeda asosiasi semantik vs hubungan logis |
| 10 | **Evaluasi** | Dari 3 uji teknis (latency, faithfulness, konsistensi) → menjadi **7 metrik + 8 hipotesis + user study** |
| 11 | **Tinjauan Pustaka** | Dari 2 sub-bab (State of Art + Metode) → menjadi **10 sub-bab** dengan teori yang jauh lebih dalam |
| 12 | **Posisi Sistem** | Dari "sistem otomatis" → menjadi **"alat bantu keputusan (decision support tool)"** |
| 13 | **Referensi** | Dari 25 referensi teknis → ditambah **15+ referensi baru** termasuk fondasi konseptual (Cooper, Booth, Garcez, Marcus, Bender) |

---

## 2. Perbandingan Detail Per Bagian

---

### 2.1 BAB I — PENDAHULUAN

#### 2.1.1 Judul Penelitian

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Judul ID | *Intelligent Research Gap Analyzer: Sistem Otomatis Berbasis RAG dan LLM untuk Generasi Rekomendasi Penelitian Lanjutan dari Analisis Jurnal* | Fokus pada pendekatan **Neuro-Symbolic Agentic** untuk deteksi *synthesis gap* (judul perlu diformalisasi oleh pembimbing) | ✅ SUDAH DIREVISI |
| Kata Kunci | "Otomatis", "Generasi Rekomendasi" | "Neuro-Symbolic", "Agentic", "Synthesis Gap Detection", "Decision Support" | ✅ SUDAH DIREVISI |
| Klaim | Klaim membuat sistem "otomatis" | Klaim membuat "alat bantu deteksi indikator" | ✅ SUDAH DIREVISI |

#### 2.1.2 Latar Belakang

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Panjang | ~5 paragraf, fokus pada masalah teknis (halusinasi, latency, Vector DB) | ~8 paragraf, fokus pada **masalah epistemologis** + teknis | ✅ SUDAH DIREVISI |
| Framing masalah | Masalah = LLM halusinasi + DB lambat | Masalah = *pipeline linear* tidak bisa menalar bertahap, tidak bisa membedakan asosiasi semantik vs kausal, tidak ada validasi logis | ✅ SUDAH DIREVISI |
| Landasan teori | Tidak ada rujukan teori tentang *research gap* | Merujuk Cooper (1998), Booth et al. (2012) untuk definisi *synthesis gap* | ✅ SUDAH DIREVISI |
| Keterbatasan LLM | Hanya menyebut halusinasi | Menyebut halusinasi + *context window* + *static knowledge* + ketidakmampuan membedakan korelasi vs kausal | ✅ SUDAH DIREVISI |
| Paradigma | Pipeline linear RAG+LLM | Paradigma *AI Agent* + *multi-step reasoning* + *Rule-Based Validation* (Neuro-Symbolic) | ✅ SUDAH DIREVISI |
| Definisi *synthesis gap* | "Peluang penelitian dari hasil perpaduan wawasan" (naif) | "Kondisi di mana literatur belum menghasilkan kesimpulan terpadu: fragmentasi, inkonsistensi, ketidaklengkapan kolektif" | ✅ SUDAH DIREVISI |
| *Spurious correlation* | Tidak dibahas | Dibahas secara eksplisit sebagai risiko *pipeline linear* | 🆕 BAGIAN BARU |

#### 2.1.3 Rumusan Masalah

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Pola | "*Bagaimana merancang arsitektur...*" dan "*Bagaimana mengoptimalkan...*" | Pola fenomena → kesenjangan → pertanyaan penelitian | ✅ SUDAH DIREVISI |
| Jumlah pertanyaan | 2 pertanyaan | 3 pertanyaan penelitian | ✅ SUDAH DIREVISI |
| RQ1 Lama | "Bagaimana merancang arsitektur sistem berbasis RAG dan LLM yang mampu menganalisis beberapa jurnal untuk menemukan celah penelitian?" | — | — |
| RQ1 Baru | — | "Sejauh mana pendekatan *agentic multi-step reasoning* yang dilengkapi *rule-based validation* mampu mendeteksi indikator *synthesis gap* (fragmentasi, inkonsistensi, ketidaklengkapan kolektif)?" | ✅ SUDAH DIREVISI |
| RQ2 Lama | "Bagaimana mengoptimalkan akurasi serta hasil analisis sistem agar tetap relevan?" | — | — |
| RQ2 Baru | — | "Bagaimana mekanisme pembeda asosiasi semantik dan hubungan logis serta *rule-based validation* memengaruhi tingkat akurasi dan *false discovery rate*?" | ✅ SUDAH DIREVISI |
| RQ3 | **Tidak ada** | "Apa batasan-batasan epistemologis pendekatan ini dibandingkan penalaran logis-induktif manusia?" | 🆕 BAGIAN BARU |
| Penjelasan per RQ | Tidak ada justifikasi per pertanyaan | Setiap pertanyaan disertai paragraf penjelasan mengapa pertanyaan tersebut penting | ✅ SUDAH DIREVISI |

#### 2.1.4 Tujuan Penelitian

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Tujuan 1 Lama | "Merancang dan membangun arsitektur sistem" | — | — |
| Tujuan 1 Baru | — | "**Mengukur** kemampuan pendekatan Neuro-Symbolic Agentic dalam mendeteksi indikator *synthesis gap*" | ✅ SUDAH DIREVISI |
| Tujuan 2 Lama | "Mengoptimalkan akurasi dan konsistensi hasil" | — | — |
| Tujuan 2 Baru | — | "**Menganalisis** pengaruh mekanisme pembeda + *rule-based validation* terhadap kualitas deteksi" | ✅ SUDAH DIREVISI |
| Tujuan 3 | **Tidak ada** | "**Mengidentifikasi dan mendeskripsikan** batasan-batasan epistemologis sistem secara eksplisit" | 🆕 BAGIAN BARU |
| Alignment dengan RQ | Tidak selaras sempurna | Setiap tujuan menjawab tepat satu pertanyaan penelitian | ✅ SUDAH DIREVISI |

#### 2.1.5 Manfaat Penelitian

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Manfaat Teoretis | 3 poin umum (Metodologi, RAG Architecture, Integrasi KG+LLM) | 3 poin yang lebih tajam: (a) batas kemampuan Neuro-Symbolic, (b) operasionalisasi *synthesis gap*, (c) kerangka evaluasi standar | ✅ SUDAH DIREVISI |
| Manfaat Praktis | 3 poin sederhana (hemat waktu, alat bimbingan, percepat inovasi) | 3 poin spesifik: (a) peneliti individu — dengan disclaimer "alat bantu", (b) kelompok riset — pemantauan literatur, (c) komunitas luas — *open-source* + modular | ✅ SUDAH DIREVISI |

#### 2.1.6 Batasan Epistemologis Sistem

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Keberadaan | **TIDAK ADA** | Bagian 1.5 lengkap dengan 4 sub-bagian | 🆕 BAGIAN BARU |
| Apa yang BISA dilakukan sistem | Tidak didefinisikan | Tabel 6 kemampuan dengan metode dan tingkat keyakinan | 🆕 BAGIAN BARU |
| Apa yang TIDAK BISA dilakukan | Tidak didefinisikan | Tabel 4 keterbatasan fundamental dengan alasan dan implikasi | 🆕 BAGIAN BARU |
| Posisi sistem | Disebut "alat bantu" secara sekilas | Didefinisikan eksplisit sebagai *decision support tool* + diagram posisi | 🆕 BAGIAN BARU |
| Klaim yang TIDAK dibuat | Tidak ada | 4 klaim negatif eksplisit (tidak menalar induktif, tidak menemukan gap pasti valid, dll.) | 🆕 BAGIAN BARU |

#### 2.1.7 Batasan Masalah

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Cakupan domain | arXiv, ACM, IEEE, Semantic Scholar, PubMed | CS khususnya AI/ML/NLP/IR, 2015–2025, bahasa Inggris | ✅ SUDAH DIREVISI |
| Input makalah | Tidak disebutkan jumlah | 3–10 makalah per sesi, dengan justifikasi | ✅ SUDAH DIREVISI |
| KG | "Lightweight KG (Makalah-Konsep-Metode)" | "Lightweight KG tanpa ontologi penuh, tanpa *graph embedding*" dengan justifikasi ilmiah [Abu-Salih et al., 2024] | ✅ SUDAH DIREVISI |
| Rule Engine | **Tidak ada** | 3 kategori aturan, bersifat deduktif, tidak mencakup penilaian substantif | 🆕 BAGIAN BARU |
| Evaluasi | Tidak jelas | Validasi pakar 3–5 evaluator, studi pengguna 10–15 peneliti, perbandingan *baseline* | ✅ SUDAH DIREVISI |
| Posisi sistem | "Alat bantu otomatisasi, tidak jaminan 100%" | "Prototipe penelitian, bukan *production-ready*, alat bantu bukan otonom" | ✅ SUDAH DIREVISI |

---

### 2.2 BAB II — TINJAUAN PUSTAKA

#### 2.2.1 Struktur Keseluruhan

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Jumlah sub-bab | 4 sub-bab (State of Art, Metode, Kerangka Pikir, Alur Sistem) | **10 sub-bab** yang komprehensif | ✅ SUDAH DIREVISI |
| Kedalaman teori | Sangat dangkal, fokus pada teknis | Mendalam, mencakup fondasi konseptual dan epistemologis | ✅ SUDAH DIREVISI |
| Referensi | Dominan referensi teknis/engineering | Ditambah referensi fondasi (Cooper, Booth, Garcez, Marcus, Bender, Buchanan) | ✅ SUDAH DIREVISI |

#### 2.2.2 Perbandingan Sub-Bab

| Sub-Bab | Proposal Lama | Proposal Revisi | Status |
|---------|---------------|-----------------|--------|
| **2.1 Sintesis dalam Literature Review** | **Tidak ada** — langsung ke State of Art | Sub-bab lengkap tentang definisi sintesis, perbedaan dengan ringkasan, Cooper (1998) & Booth (2012) | 🆕 BAGIAN BARU |
| **2.2 Research Gap: Definisi & Identifikasi** | Definisi *synthesis gap* hanya 1 kalimat ("peluang dari persilangan ide") | 3 sub-sub-bab: Pengertian Research Gap, Definisi Synthesis Gap (3 indikator), Tiga Indikator Synthesis Gap | ✅ SUDAH DIREVISI |
| **2.3 LLM dan RAG** | Hanya menyebut halusinasi dan Vector DB | Lebih sistematis: definisi LLM, mekanisme RAG, **keterbatasan fundamental** keduanya | ✅ SUDAH DIREVISI |
| **2.4 Batasan Penalaran LLM** | **Tidak ada** | Sub-bab baru: representasi semantik vs penalaran induktif, pandangan kritis (Bender & Koller), risiko dalam deteksi research gap | 🆕 BAGIAN BARU |
| **2.5 Neuro-Symbolic AI** | **Tidak ada** | Sub-bab baru: konsep dasar, menuju AI robust (Marcus, 2020), pendekatan integrasi (neural + simbolik) | 🆕 BAGIAN BARU |
| **2.6 Knowledge Graph sebagai Fact Base** | Hanya 1 paragraf "Lightweight KG" | Sub-bab lengkap: definisi & representasi (triple SPO), KG sebagai basis penalaran, ontologi untuk analisis literatur | ✅ SUDAH DIREVISI |
| **2.7 Rule-Based Expert Systems** | **Tidak ada** | Sub-bab baru: fondasi konseptual (Buchanan & Shortliffe, Giarratano & Riley), *forward chaining*, formalisasi aturan IF-THEN | 🆕 BAGIAN BARU |
| **2.8 Natural Language Inference (NLI)** | **Tidak ada** | Sub-bab baru: definisi & tugas (*entailment/contradiction/neutral*), corpus multi-genre, aplikasi untuk *contradiction detection* | 🆕 BAGIAN BARU |
| **2.9 AI Agent & Multi-Step Reasoning** | **Tidak ada** | Sub-bab baru: konsep AI Agent, ReAct Pattern (Yao et al., 2023), LangGraph/LangChain, perbedaan dari *pipeline linear* | 🆕 BAGIAN BARU |
| **2.10 Penelitian Terkait & Posisi** | State of Art (tabel 10 penelitian) + kesimpulan | Tabel penelitian terdahulu yang diperbarui + **kebaruan penelitian** yang eksplisit: 4 komponen novelty | ✅ SUDAH DIREVISI |
| State of Art (Tabel) | 10 penelitian | Tetap ada, diperbarui dan diselaraskan dengan arah baru | ✅ SUDAH DIREVISI |
| Kerangka Pikir | Diagram "Kondisi Saat Ini → Solusi → Hasil" | Diganti dengan narasi posisi penelitian yang lebih ilmiah | ✅ SUDAH DIREVISI |
| Alur Sistem | 3 tahap (Input → Proses → Output) | Dipindahkan ke BAB III sebagai bagian arsitektur 4 fase | ✅ SUDAH DIREVISI |

#### 2.2.3 Definisi Synthesis Gap

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Definisi | "Peluang riset baru dari penggabungan ide antar-jurnal" = **salah** menurut penguji | Berdasarkan Cooper (1998): "kondisi literatur belum menghasilkan kesimpulan terpadu" | ✅ SUDAH DIREVISI |
| Contoh | "Menggabungkan Metode X + Kerangka Y" = *unexplored combination*, **bukan** *synthesis gap* | 3 indikator: **fragmentasi** (literatur terpecah), **inkonsistensi** (temuan bertentangan), **ketidaklengkapan kolektif** (aspek kritis belum tercakup) | ✅ SUDAH DIREVISI |
| Apa yang BUKAN synthesis gap | Tidak didefinisikan | Didefinisikan: bukan kombinasi metode baru, bukan absence topic | 🆕 BAGIAN BARU |

---

### 2.3 BAB III — METODOLOGI PENELITIAN

#### 2.3.1 Desain Penelitian

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Metodologi | *Design Science Research* (5 tahap linear) | *Mixed methods*: (1) pengembangan sistem, (2) evaluasi eksperimental, (3) penilaian pakar | ✅ SUDAH DIREVISI |
| Justifikasi | Tidak ada justifikasi mengapa DSR | Justifikasi: *synthesis gap detection* butuh validasi kualitatif + kuantitatif | ✅ SUDAH DIREVISI |

#### 2.3.2 Arsitektur Sistem

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Struktur | 3 tahap linear: Input → Pemrosesan (Vector DB) → Analisis (RAG Pipeline) | **4 Fase**: (1) Ingestion, (2) Fact Extraction, (3) Agentic Analysis, (4) Logical Consistency Checker | ✅ SUDAH DIREVISI |
| Diagram | Diagram linear *black-box* | Diagram 4 fase detail dengan komponen internal per fase | ✅ SUDAH DIREVISI |
| Agent | Disebut "agen otomatis" sekilas tanpa penjelasan | 5 *tools* terpisah: Retriever, NLI Checker, KG Query, Gap Detector, Self-Critic | ✅ SUDAH DIREVISI |
| Orchestrator | **Tidak ada** | LLM Agent sebagai *orchestrator* dengan siklus Plan → Act → Observe → Reflect → Repeat/Stop | 🆕 BAGIAN BARU |
| Fase 1: Ingestion | Chunking sederhana | PDF parsing → section-aware chunking → embedding (SciBERT) → dual storage (Vector DB + KG) | ✅ SUDAH DIREVISI |
| Fase 2: Fact Extraction | **Tidak ada sebagai fase terpisah** | Fase khusus: IE dari teks → triple SPO → populasi KG → inferensi fakta turunan | 🆕 BAGIAN BARU |
| Fase 3: Agentic Analysis | Linear RAG pipeline | Siklus agentic dengan 5 *tools* dan *self-correction* | ✅ SUDAH DIREVISI |
| Fase 4: Logical Consistency Checker | **Tidak ada** | *Rule Engine* memverifikasi output agent terhadap aturan logika | 🆕 BAGIAN BARU |

#### 2.3.3 Mekanisme Pembeda Asosiasi Semantik vs Hubungan Logis

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Keberadaan | **Tidak ada** — semua hubungan dianggap bermakna | Bagian 3.3 lengkap | 🆕 BAGIAN BARU |
| Jenis hubungan | Tidak dibedakan | 3 jenis: *co-occurrence* (semantik), kausalitas, kontradiksi | 🆕 BAGIAN BARU |
| Mekanisme | Tidak ada | **3 lapis**: (1) Semantic Filtering (cosine > 0.75), (2) Evidence Extraction (penanda linguistik via LLM Agent), (3) Rule-Based Validation | 🆕 BAGIAN BARU |
| Penanda linguistik | Tidak ada | Didefinisikan: kausal ("causes", "leads to", dll.), kontradiksi ("however", "contradicts", dll.) | 🆕 BAGIAN BARU |

#### 2.3.4 Rule-Based Validation Layer

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Keberadaan | **Tidak ada** | Bagian 3.4 lengkap | 🆕 BAGIAN BARU |
| Arsitektur | — | Fact Base (dari KG) + Rule Base (9 aturan) + Inference Engine (*forward chaining*) | 🆕 BAGIAN BARU |
| Aturan Kelayakan | — | 3 aturan: kompatibilitas sumber daya (F1), data (F2), skala (F3) | 🆕 BAGIAN BARU |
| Aturan Kausalitas | — | 3 aturan: bukti minimal (C1), arah kausalitas (C2), *confounding* (C3) | 🆕 BAGIAN BARU |
| Aturan Konsistensi | — | 3 aturan: non-kontradiksi internal (K1), konsistensi dengan KG (K2), transitivitas (K3) | 🆕 BAGIAN BARU |
| Verdict | — | 3 kemungkinan: PASS, FLAG, REJECT | 🆕 BAGIAN BARU |
| Contoh skenario | — | Contoh *end-to-end* (CNN di mobile → REJECT karena ketidaksesuaian resource) | 🆕 BAGIAN BARU |

#### 2.3.5 Skema Fakta Knowledge Graph (Tabel SPO)

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Ontologi | Tidak ada definisi formal | 8 tipe entitas + 12+ predikat relasi | 🆕 BAGIAN BARU |
| Representasi | Disebut "Makalah-Konsep-Metode" tanpa skema | Triple SPO (*Subject-Predicate-Object*) dengan metadata | ✅ SUDAH DIREVISI |
| Tipe entitas | 3 (Paper, Concept, Method) | 8 (METHOD, CONCEPT, DOMAIN, FINDING, DATASET, METRIC, PAPER, CONSTRAINT) | ✅ SUDAH DIREVISI |
| Contoh transformasi | Tidak ada | Contoh lengkap teks → tabel SPO → fakta turunan | 🆕 BAGIAN BARU |

#### 2.3.6 Deteksi Indikator Synthesis Gap

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Definisi indikator | "Explicit gaps, implicit gaps, synthesis gaps" — tidak jelas | 3 indikator operasional: fragmentasi, inkonsistensi, ketidaklengkapan kolektif | ✅ SUDAH DIREVISI |
| Metode deteksi | Tidak jelas | Metode spesifik per indikator: topic clustering (fragmentasi), pairwise NLI (inkonsistensi), coverage analysis (ketidaklengkapan) | 🆕 BAGIAN BARU |
| Contoh workflow | Tidak ada | Contoh *agentic workflow trace* langkah per langkah | 🆕 BAGIAN BARU |

#### 2.3.7 Framework Evaluasi

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Metrik | 3 uji teknis: *Latency Test*, *RAG Fidelity* (Faithfulness Score), *Konsistensi Output* | **7 metrik**: EAR, LCS, AS, FDR, SHG, RERR, REP | ✅ SUDAH DIREVISI |
| Hipotesis Lama | Tidak ada hipotesis formal | H1 (RAG vs standalone), H2 (multi vs single), H3 (KG vs no KG) — **tetap** | ✅ SUDAH DIREVISI |
| Hipotesis Baru | — | H4 (EAR ≥ 50%), H5 (LCS ≥ 3.5/5), H6 (agentic vs linear), H7 (Rule Engine menurunkan FDR), H8 (mengurangi waktu vs manual) | 🆕 BAGIAN BARU |
| Ground Truth | Menggunakan RAGAS (otomatis) | Pakar domain melabeli output: *Genuine Gap*, *Trivial*, *Illogical*, *Already Addressed* | ✅ SUDAH DIREVISI |
| Desain Eksperimental | Tidak ada perbandingan konfigurasi | 3 konfigurasi: Baseline (linear RAG+LLM), Agentic Only, Full System (Agent + Rule Engine) | 🆕 BAGIAN BARU |
| User Study | Tidak ada | *Within-subject design* dengan 10–15 partisipan, Kondisi A (manual) vs Kondisi B (dengan sistem) | 🆕 BAGIAN BARU |
| Kriteria Keberhasilan | Tidak didefinisikan | Tabel eksplisit: EAR ≥ 50%, LCS ≥ 3.5/5, FDR turun ≥ 20%, REP ≥ 70% | 🆕 BAGIAN BARU |
| Validasi pakar | Tidak ada | 3–5 evaluator pakar domain | 🆕 BAGIAN BARU |

#### 2.3.8 Novelty Statement

| Aspek | Proposal Lama | Proposal Revisi | Status |
|-------|---------------|-----------------|--------|
| Keberadaan | Disebut sekilas di latar belakang | Bagian 3.8 yang eksplisit dan terstruktur | ✅ SUDAH DIREVISI |
| Klaim Novelty Lama | RAG + LLM + Vector DB + Lightweight KG | — | — |
| Klaim Novelty Baru | — | 4 komponen: (1) Agentic multi-step reasoning, (2) Rule-Based Validation Layer, (3) Mekanisme pembeda semantik vs logis, (4) KG sebagai Fact Base | ✅ SUDAH DIREVISI |
| Pembeda | Tidak jelas apa yang baru dibanding penelitian lain | Eksplisit: "Kebaruan bukan pada RAG/LLM, melainkan pada integrasi penalaran simbolik + neural untuk *synthesis gap*" | ✅ SUDAH DIREVISI |

---

## 3. Checklist revisi.md Bagian 14 — Pemetaan ke Draf Baru

### 3.1 Konseptual (PALING PENTING)

| # | Item Checklist | Status | Lokasi di Draf Baru |
|---|---------------|--------|---------------------|
| 1 | Rumusan masalah sudah pola fenomena → kesenjangan → pertanyaan | ✅ | BAB I, §1.2 — paragraf narasi sebelum 3 pertanyaan menjelaskan fenomena dan kesenjangan |
| 2 | Definisi *synthesis gap* sesuai Cooper (1998) & Booth (2012) | ✅ | BAB II, §2.2.2 — definisi eksplisit + 3 indikator di §2.2.3 |
| 3 | Ada sesi batasan epistemologis yang eksplisit | ✅ | BAB I, §1.5 — 4 sub-bagian: Bisa, Tidak Bisa, Posisi, Klaim Negatif |
| 4 | Klaim sistem = "alat bantu deteksi indikator", bukan "pengganti manusia" | ✅ | BAB I §1.5.3 + §1.5.4 — dinyatakan eksplisit |
| 5 | Istilah *synthesis gap* konsisten di seluruh dokumen | ✅ | Konsisten di BAB I, II, III — merujuk pada 3 indikator yang sama |
| 6 | Novelty statement jelas (Neuro-Symbolic Agentic) | ✅ | BAB III, §3.8 — 4 komponen novelty didefinisikan |

### 3.2 Arsitektur

| # | Item Checklist | Status | Lokasi di Draf Baru |
|---|---------------|--------|---------------------|
| 7 | Diagram alir 4 fase sudah digambar | ✅ | BAB III, §3.2 — diagram ASCII 4 fase (Ingestion, Fact Extraction, Agentic Analysis, Logical Consistency Checker) |
| 8 | Ada blok "Logical Consistency Checker" di diagram | ✅ | BAB III, §3.2.4 — Fase 4 khusus untuk Logical Consistency Checker |
| 9 | Mekanisme pembeda asosiasi semantik vs hubungan logis | ✅ | BAB III, §3.3 — mekanisme 3 lapis lengkap |
| 10 | Rule-Based Validation Layer (3 kategori, 9 aturan) | ✅ | BAB III, §3.4.2 — F1-F3, C1-C3, K1-K3 |
| 11 | Skema Fakta KG (SPO) didefinisikan (8 tipe entitas, 12 predikat) | ✅ | BAB III, §3.5.1 — tabel tipe entitas + tipe relasi |
| 12 | Contoh transformasi teks → SPO sudah ditulis | ⚠️ | BAB III, §3.5 — ontologi didefinisikan, contoh transformasi perlu diperkuat (contoh lebih lengkap ada di revisi.md §9) |
| 13 | Contoh penalaran rule engine sudah ditulis | ✅ | BAB III, §3.4.4 — contoh skenario CNN di mobile |

### 3.3 Evaluasi

| # | Item Checklist | Status | Lokasi di Draf Baru |
|---|---------------|--------|---------------------|
| 14 | 7 metrik evaluasi baru sudah ditambahkan | ✅ | BAB III, §3.7.1 — tabel 7 metrik (EAR, LCS, AS, FDR, SHG, RERR, REP) |
| 15 | Hipotesis H4–H8 sudah ditambahkan | ✅ | BAB III, §3.7.2 — H4 sampai H8 |
| 16 | Ground truth sudah direvisi (pakar menilai output) | ✅ | BAB III, §3.7.3 — tabel label pakar (Genuine Gap, Trivial, Illogical, Already Addressed) |
| 17 | Success criteria mencakup *expert acceptance rate* | ✅ | BAB III, §3.7.5 — EAR ≥ 50% |

### 3.4 Referensi

| # | Item Checklist | Status | Lokasi di Draf Baru |
|---|---------------|--------|---------------------|
| 18 | 15 referensi baru sudah ditambahkan | ✅ | BAB II & III — referensi Cooper, Booth, Garcez, Marcus, Bender, Buchanan, Giarratano, Bowman, Hevner, Ji, LangChain, dll. |
| 19 | Sub-bab baru di BAB II sudah ditulis | ✅ | BAB II — 6 sub-bab baru (§2.4–§2.9) |
| 20 | Semua klaim didukung referensi | ✅ | Setiap klaim utama disertai rujukan dalam kurung siku |

### 3.5 Final

| # | Item Checklist | Status | Lokasi di Draf Baru |
|---|---------------|--------|---------------------|
| 21 | Sudah didiskusikan dan disetujui pembimbing | ❌ | **BELUM** — draf perlu diajukan ke pembimbing |
| 22 | Tidak ada klaim "menemukan gap secara otomatis" yang tersisa | ✅ | Istilah diubah ke "mendeteksi indikator" |
| 23 | Tidak ada definisi "Unexplored Combinations (Method A + Domain B)" yang tersisa | ✅ | Definisi *synthesis gap* sepenuhnya berbasis Cooper/Booth |
| 24 | Tidak ada diagram linear *black-box* yang tersisa | ✅ | Diagram baru 4 fase, bukan linear |

---

## 4. Hal yang Masih Perlu Dikerjakan

### 4.1 Prioritas Tinggi — Harus Sebelum Submit ke Pembimbing

| # | Item | Keterangan |
|---|------|------------|
| 1 | **Diskusi dan persetujuan pembimbing** | Seluruh draf BAB I–III perlu didiskusikan dengan pembimbing. Ini adalah syarat utama sebelum melanjutkan ke implementasi. |
| 2 | **Finalisasi judul resmi** | Judul baru belum diformalisasi secara resmi. Perlu disetujui pembimbing. |
| 3 | **Contoh transformasi teks → SPO yang lebih lengkap** | Di BAB III §3.5 ontologi sudah didefinisikan, tetapi contoh transformasi *end-to-end* dari teks asli paper ke tabel SPO perlu diperkuat. Contoh di revisi.md Bagian 9 bisa dijadikan acuan. |
| 4 | **Daftar pustaka terpadu** | Setiap BAB memiliki daftar pustaka terpisah. Perlu digabungkan menjadi satu daftar pustaka terpadu untuk proposal final. |

### 4.2 Prioritas Sedang — Setelah Persetujuan Konsep

| # | Item | Keterangan |
|---|------|------------|
| 5 | **BAB IV (Jadwal Penelitian)** | Belum ditulis. Perlu menyesuaikan timeline di revisi.md §13 ke format BAB IV. |
| 6 | **Implementasi kode** | Belum boleh dimulai sampai konsep disetujui pembimbing (sesuai peringatan di revisi.md §13). |
| 7 | **Detail teknis *NLI Checker*** | Bagian NLI di BAB II §2.8 perlu diperkuat dengan detail model yang akan digunakan (misalnya *fine-tuned* DeBERTa pada MultiNLI) dan *threshold* klasifikasi. |
| 8 | **Pilot study untuk kalibrasi *threshold*** | Beberapa parameter (cosine similarity threshold 0.75, NLI contradiction threshold 0.7) perlu dikalibrasi melalui pilot study. |

### 4.3 Prioritas Rendah — Penyempurnaan

| # | Item | Keterangan |
|---|------|------------|
| 9 | **Formatting dan konsistensi** | Menyatukan gaya penulisan antar-BAB (format tabel, level heading, gaya sitasi). |
| 10 | **Abstrak dan kata kunci** | Belum ditulis karena menunggu finalisasi seluruh konten. |
| 11 | **Lampiran** | Contoh output yang diharapkan, instrumen evaluasi pakar, dan formulir persetujuan *user study*. |

### 4.4 Hal-hal yang Tidak Boleh Dilakukan (Reminder)

Berdasarkan revisi.md §14:
- ❌ **JANGAN** lanjut coding sebelum konsep disetujui pembimbing
- ❌ **JANGAN** gunakan istilah "menemukan gap secara otomatis"
- ❌ **JANGAN** definisikan *synthesis gap* sebagai "kombinasi Method A + Domain B"
- ❌ **JANGAN** klaim sistem bisa menalar seperti manusia
- ❌ **JANGAN** abaikan batasan epistemologis
- ❌ **JANGAN** gunakan rumusan masalah pola "Bagaimana merancang/membangun..."
- ❌ **JANGAN** buat diagram linear tanpa validasi logis
- ❌ **JANGAN** gunakan KG hanya sebagai visualisasi tanpa tabel fakta SPO

---

*Dokumen ini dibuat berdasarkan perbandingan antara proposal_full_text.txt (proposal lama), draf BAB I/II/III (proposal revisi), dan checklist revisi.md Bagian 14.*
