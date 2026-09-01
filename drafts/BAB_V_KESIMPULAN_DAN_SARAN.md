# BAB V: KESIMPULAN DAN SARAN

## 5.1 Kesimpulan

Berdasarkan hasil perancangan, implementasi, dan pengujian awal sistem Wizard Research sebagai *Neuro-Symbolic Agentic System* untuk deteksi *synthesis gap*, dapat disimpulkan sebagai berikut:

### 5.1.1 Jawaban terhadap Pertanyaan Penelitian

**RQ1: Bagaimana merancang arsitektur Neuro-Symbolic Agentic yang mampu mengidentifikasi *synthesis gap* pada literatur ilmiah?**

Arsitektur empat fase (Ingestion → Fact Extraction → Agentic Analysis → Logical Checker) berhasil dirancang dan diimplementasikan. Arsitektur ini mengintegrasikan komponen neural (LLM berbasis Ollama untuk ekstraksi dan deteksi) dengan komponen symbolic (Rule Engine dengan 9 aturan validasi dan Fact Table berbasis SPO). Orkestrator LangGraph dengan pola *Observe-Think-Act-Evaluate* menyediakan mekanisme agentic yang memungkinkan penalaran multi-langkah. Pengujian pada 23 paper benchmark (4 topik) menghasilkan 248 fakta SPO dan 14 indikator gap yang valid, dengan rata-rata skor kepercayaan 0,700.

**RQ2: Bagaimana membedakan asosiasi semantik (*semantic co-occurrence*) dari hubungan logis (*causal/contradictory*) dalam konteks deteksi gap?**

Relation Classifier dengan mekanisme 3 lapis berhasil diimplementasikan: (1) penanda linguistik untuk identifikasi awal, (2) analisis struktural untuk konteks, dan (3) verifikasi NLI untuk konfirmasi. Sistem secara konsisten menandai indikator yang berasal dari asosiasi semantik dengan flag `requires_human_validation = True`, membedakannya dari hubungan yang telah terverifikasi secara logis. Hal ini sesuai dengan prinsip epistemologis bahwa LLM tidak melakukan penalaran logis sejati [Marcus, 2020]. Kontribusi lapisan NLI terkonfirmasi secara kuantitatif melalui studi ablasi multi-run (7 run `nli` vs 5 run `no-nli`, seed berbeda per run): mode dengan NLI mendeteksi lebih banyak indikator (Δmedian = 8; 24,3 ± 2,3 vs 15,2 ± 1,9) dengan confidence lebih tinggi, keduanya signifikan setelah koreksi Holm–Bonferroni (Mann–Whitney U, p Holm = 0,0331 < 0,05; Cliff's δ = 1,0).

**RQ3: Bagaimana mengevaluasi kualitas indikator gap yang dihasilkan oleh sistem?**

Framework evaluasi dengan 8 metrik kuantitatif (M1–M8) berhasil diterapkan. Rule Engine dengan 3 kategori aturan (Kelayakan, Kausalitas, Konsistensi) menyediakan validasi otomatis berlapis. Pada korpus benchmark, seluruh 14 indikator melewati validasi Rule Engine (100% PASS), sementara validasi adversarial membuktikan kemampuan diskriminatif lapisan simbolis: 6 dari 6 klaim adversarial diberi verdict sesuai harapan (akurasi 100%), termasuk penolakan klaim yang tidak layak dan pelolosan klaim kontrol. Evaluasi pakar (*Expert Acceptance Rate*) direncanakan pada fase evaluasi penuh untuk mengukur akurasi aktual.

Framework tersebut kemudian diperluas dengan empat metrik kalibrasi dan penelusuran (M9–M12) yang diuji pada korpus aplikatif 35 jurnal: seluruh indikator yang lolos memiliki rantai provenans utuh (100%), abstensi selektif tidak lagi menyala untuk setiap keluaran (0% setelah perbaikan, dari sebelumnya 100%), dan usulan yang tidak berjangkar pada indikator terdeteksi otomatis turun prioritas. Metrik kalibrasi numerik (ECE, Brier, AURC) sengaja **tidak** dilaporkan karena label pakar belum terkumpul — status yang ditampilkan apa adanya kepada pengguna alih-alih disajikan sebagai kalibrasi yang sudah tervalidasi.

### 5.1.2 Kontribusi Utama

Penelitian ini memberikan lima kontribusi utama:

1. **Rule-Based Validation Layer**: Lapisan validasi simbolis dengan 9 aturan dalam 3 kategori (Kelayakan F1-F3, Kausalitas C1-C3, Konsistensi K1-K3) yang beroperasi independen dari LLM. Lapisan ini memastikan bahwa indikator gap memenuhi kriteria logis minimum sebelum disajikan kepada pengguna.

2. **Fact Table berbasis SPO (Subject-Predicate-Object)**: Representasi pengetahuan terstruktur dengan 8 tipe entitas dan 14 tipe predikat yang memungkinkan *grounding* klaim pada fakta terverifikasi, bukan hanya pada output stokastik LLM.

3. **Klaim Epistemologis yang Terkalibrasi**: Sistem secara eksplisit membatasi output sebagai "indikator gap" (*gap indicators*) yang memerlukan validasi manusia, bukan "kesenjangan riset" definitif. Pendekatan ini mengatasi masalah *over-claiming* yang umum pada sistem berbasis LLM.

4. **Indikator Ketiadaan Dukungan Bukti**: Indikator keempat yang mendeteksi klaim yang justru berulang lintas jurnal namun tidak memiliki bukti primer yang dapat ditelusuri, melalui uji kegagalan *retrieval* secara *leave-one-out*. Indikator ini berbeda dari ketidaklengkapan: aspeknya **dibahas dan diklaim**, tetapi tidak terbuktikan — sebuah bentuk gap yang tidak tertangkap oleh ketiga indikator sebelumnya.

5. **Rantai Provenans dan Abstensi Selektif**: Setiap indikator wajib memiliki rantai klaim → jurnal terkutip → kutipan verbatim → hasil validasi yang utuh; indikator dengan rantai terputus atau keyakinan di bawah ambang otomatis ditandai untuk peninjauan manusia. Pengujian pada korpus nyata membuktikan mekanisme ini bersifat diskriminatif (0 dari 2 indikator ditandai) dan bukan sekadar penanda seragam.

---

## 5.2 Saran

### 5.2.1 Pengembangan Lanjutan (Future Work)

1. **Optimasi Fact Extraction**: Modul ekstraksi fakta perlu ditingkatkan dengan *prompt engineering* yang lebih terstruktur dan mekanisme *retry* untuk mengatasi kegagalan parsing JSON. Penggunaan model LLM yang lebih besar (7B-13B parameter) diharapkan meningkatkan kualitas ekstraksi.

2. **Evaluasi oleh Pakar**: Diperlukan evaluasi kualitatif oleh pakar domain untuk mengukur *Expert Acceptance Rate* dan *Logical Coherence Score*. Direkomendasikan melibatkan 3-5 pakar dari berbagai bidang ilmu. Label pakar ini sekaligus menjadi prasyarat pengaktifan kalibrator *temperature scaling*, yang saat ini masih beroperasi sebagai pemetaan identitas sehingga ECE, Brier, dan AURC belum dapat dilaporkan.

3. **Skala Dataset**: Eksperimen perlu diperluas ke 50-100 paper dari berbagai domain untuk menguji robustness dan generalizability sistem. Variasi domain penting untuk memastikan Rule Engine tidak bias pada satu bidang.

4. **Kalibrasi Rule Engine**: Threshold aturan perlu dikalibrasi berdasarkan hasil evaluasi pakar. Tingkat PASS 100% pada eksperimen awal mungkin menunjukkan threshold yang terlalu longgar.

5. **Mode Perbandingan**: Studi ablasi *with-vs-without* telah dilakukan untuk NLI (H9, terkonfirmasi signifikan) dan Rule Engine (H7, tidak signifikan pada jumlah indikator — kontribusinya bersifat kualitatif). Penambahan jumlah run (≥10 per mode) disarankan untuk meningkatkan power uji H6/H7.

6. **Uji Regresi Berbasis Bentuk Data Produksi**: Tiga cacat implementasi pada lapisan provenans hanya terungkap saat pipeline dijalankan pada dokumen nyata (Subbab 4.3.8) karena uji sintetis memakai frasa pendek dan struktur data yang selalu ideal. Pengembangan lanjutan disarankan menambahkan uji yang meniru bentuk data produksi secara spesifik, bukan sekadar bentuk yang valid.

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
