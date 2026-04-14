# BAB V: KESIMPULAN DAN SARAN

## 5.1 Kesimpulan

Berdasarkan hasil perancangan, implementasi, dan pengujian awal sistem Wizard Research sebagai *Neuro-Symbolic Agentic System* untuk deteksi *synthesis gap*, dapat disimpulkan sebagai berikut:

### 5.1.1 Jawaban terhadap Pertanyaan Penelitian

**RQ1: Bagaimana merancang arsitektur Neuro-Symbolic Agentic yang mampu mengidentifikasi *synthesis gap* pada literatur ilmiah?**

Arsitektur empat fase (Ingestion → Fact Extraction → Agentic Analysis → Logical Checker) berhasil dirancang dan diimplementasikan. Arsitektur ini mengintegrasikan komponen neural (LLM berbasis Ollama untuk ekstraksi dan deteksi) dengan komponen symbolic (Rule Engine dengan 9 aturan validasi dan Fact Table berbasis SPO). Orkestrator LangGraph dengan pola *Observe-Think-Act-Evaluate* menyediakan mekanisme agentic yang memungkinkan penalaran multi-langkah. Pengujian pada 5 paper benchmark menghasilkan 9 indikator gap yang valid dari 3 topik query, dengan rata-rata skor kepercayaan 0.739.

**RQ2: Bagaimana membedakan asosiasi semantik (*semantic co-occurrence*) dari hubungan logis (*causal/contradictory*) dalam konteks deteksi gap?**

Relation Classifier dengan mekanisme 3 lapis berhasil diimplementasikan: (1) penanda linguistik untuk identifikasi awal, (2) analisis struktural untuk konteks, dan (3) verifikasi NLI untuk konfirmasi. Sistem secara konsisten menandai indikator yang berasal dari asosiasi semantik dengan flag `requires_human_validation = True`, membedakannya dari hubungan yang telah terverifikasi secara logis. Hal ini sesuai dengan prinsip epistemologis bahwa LLM tidak melakukan penalaran logis sejati [Marcus, 2020].

**RQ3: Bagaimana mengevaluasi kualitas indikator gap yang dihasilkan oleh sistem?**

Framework evaluasi dengan 6 metrik kuantitatif berhasil diterapkan. Rule Engine dengan 3 kategori aturan (Kelayakan, Kausalitas, Konsistensi) menyediakan validasi otomatis berlapis. Pada pengujian awal, seluruh 9 indikator melewati validasi Rule Engine (100% PASS), menunjukkan konsistensi internal output. Evaluasi pakar (*Expert Acceptance Rate*) direncanakan pada fase evaluasi penuh untuk mengukur akurasi aktual.

### 5.1.2 Kontribusi Utama

Penelitian ini memberikan tiga kontribusi utama:

1. **Rule-Based Validation Layer**: Lapisan validasi simbolis dengan 9 aturan dalam 3 kategori (Kelayakan F1-F3, Kausalitas C1-C3, Konsistensi K1-K3) yang beroperasi independen dari LLM. Lapisan ini memastikan bahwa indikator gap memenuhi kriteria logis minimum sebelum disajikan kepada pengguna.

2. **Fact Table berbasis SPO (Subject-Predicate-Object)**: Representasi pengetahuan terstruktur dengan 8 tipe entitas dan 14 tipe predikat yang memungkinkan *grounding* klaim pada fakta terverifikasi, bukan hanya pada output stokastik LLM.

3. **Klaim Epistemologis yang Terkalibrasi**: Sistem secara eksplisit membatasi output sebagai "indikator gap" (*gap indicators*) yang memerlukan validasi manusia, bukan "kesenjangan riset" definitif. Pendekatan ini mengatasi masalah *over-claiming* yang umum pada sistem berbasis LLM.

---

## 5.2 Saran

### 5.2.1 Pengembangan Lanjutan (Future Work)

1. **Optimasi Fact Extraction**: Modul ekstraksi fakta perlu ditingkatkan dengan *prompt engineering* yang lebih terstruktur dan mekanisme *retry* untuk mengatasi kegagalan parsing JSON. Penggunaan model LLM yang lebih besar (7B-13B parameter) diharapkan meningkatkan kualitas ekstraksi.

2. **Evaluasi oleh Pakar**: Diperlukan evaluasi kualitatif oleh pakar domain untuk mengukur *Expert Acceptance Rate* dan *Logical Coherence Score*. Direkomendasikan melibatkan 3-5 pakar dari berbagai bidang ilmu.

3. **Skala Dataset**: Eksperimen perlu diperluas ke 50-100 paper dari berbagai domain untuk menguji robustness dan generalizability sistem. Variasi domain penting untuk memastikan Rule Engine tidak bias pada satu bidang.

4. **Kalibrasi Rule Engine**: Threshold aturan perlu dikalibrasi berdasarkan hasil evaluasi pakar. Tingkat PASS 100% pada eksperimen awal mungkin menunjukkan threshold yang terlalu longgar.

5. **Mode Perbandingan**: Implementasi mode perbandingan *with-vs-without* Rule Engine untuk mengukur secara kuantitatif kontribusi lapisan validasi simbolis terhadap kualitas output.

### 5.2.2 Keterbatasan yang Perlu Diatasi

1. **Ketergantungan pada Kualitas LLM**: Komponen neural sangat bergantung pada kemampuan model bahasa. Penelitian lanjutan perlu mengeksplorasi model spesialis (*domain-specific fine-tuned*) untuk domain tertentu.

2. **Skalabilitas**: Sistem perlu dioptimasi untuk menangani ratusan paper secara efisien, termasuk paralelisasi proses fact extraction dan implementasi caching.

3. **Multilingualitas**: Saat ini sistem hanya mendukung paper berbahasa Inggris. Perluasan ke bahasa lain (termasuk Bahasa Indonesia) memerlukan adaptasi pada penanda linguistik dan model embedding.

### 5.2.3 Potensi Aplikasi

Sistem ini berpotensi diterapkan pada:

1. **Asisten Riset Akademis**: Membantu mahasiswa dan peneliti mengidentifikasi area riset yang belum tereksplor secara sistematis.

2. **Evaluasi Proposal Penelitian**: Mendukung reviewer dalam menilai apakah proposal riset mengatasi gap yang genuine.

3. **Pemetaan Lanskap Riset**: Visualisasi hubungan antar topik dan identifikasi area "putih" (*white spots*) dalam peta riset suatu bidang.

4. **Deteksi Duplikasi Riset**: Mengidentifikasi area yang sudah terlalu banyak diteliti (*oversaturated*) versus area yang kurang mendapat perhatian.
