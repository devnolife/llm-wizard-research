# BAB I
# PENDAHULUAN

## 1.1 Latar Belakang

Pertumbuhan volume publikasi ilmiah dalam dua dekade terakhir telah mengalami peningkatan yang sangat signifikan. Berdasarkan data dari berbagai basis data ilmiah internasional, jumlah artikel yang dipublikasikan setiap tahunnya telah melampaui angka jutaan, dengan laju pertumbuhan yang terus meningkat secara eksponensial [Johnson et al., 2018]. Dalam domain *Computer Science* saja, repositori seperti arXiv mencatat puluhan ribu makalah baru setiap bulannya. Kondisi ini menimbulkan tantangan fundamental bagi para peneliti: bagaimana menelaah, menyintesis, dan mengidentifikasi peluang penelitian dari korpus literatur yang sedemikian masif secara efektif dan efisien.

*Large Language Models* (LLM) seperti GPT-4, Claude, dan Gemini telah menunjukkan kemampuan luar biasa dalam memproses dan menghasilkan teks bahasa alami, termasuk dalam domain ilmiah. Namun, LLM memiliki keterbatasan mendasar yang membatasi pemanfaatannya untuk analisis literatur ilmiah secara mendalam. Pertama, LLM rentan terhadap *hallucination* — menghasilkan informasi yang terdengar meyakinkan namun tidak didukung oleh bukti faktual [Chelli et al., 2024]. Kedua, LLM memiliki batasan *context window* yang menyulitkan pemrosesan simultan terhadap banyak dokumen secara utuh [Nallapati et al., 2024]. Ketiga, pengetahuan LLM bersifat statis, terbatas pada data pelatihan dan tidak mencakup publikasi terbaru.

Pendekatan *Retrieval-Augmented Generation* (RAG) muncul sebagai solusi untuk mengatasi beberapa keterbatasan tersebut. Dengan mengintegrasikan mekanisme pencarian dokumen (*retrieval*) ke dalam proses generasi teks, RAG memungkinkan LLM untuk mengakses dan merujuk pada konten dokumen aktual, sehingga mengurangi risiko halusinasi dan memungkinkan analisis terhadap literatur yang lebih baru [Lewis et al., 2020]. Berbagai penelitian telah menunjukkan efektivitas RAG dalam tugas-tugas seperti *question answering*, peringkasan dokumen, dan ekstraksi informasi dari teks ilmiah.

Meskipun demikian, identifikasi *research gap* — khususnya *synthesis gap* — merupakan proses kognitif yang jauh lebih kompleks daripada sekadar pencarian dan peringkasan informasi. Dalam proses identifikasi *research gap*, peneliti tidak hanya membaca satu dokumen secara terisolasi, melainkan melakukan analisis komparatif terhadap sejumlah literatur secara simultan. Peneliti membandingkan temuan-temuan dari berbagai studi, mengevaluasi konsistensi antar-hasil, dan menarik kesimpulan induktif tentang apa yang secara kolektif belum terjawab oleh literatur yang ada [Cooper, 1998; Booth et al., 2012]. Proses *comparative multi-paper analysis* dan sintesis lintas-dokumen inilah yang menjadi inti dari identifikasi *synthesis gap* — yaitu kondisi di mana literatur yang ada tentang suatu fenomena belum menghasilkan kesimpulan terpadu yang konklusif, baik karena fragmentasi, inkonsistensi, maupun ketidaklengkapan kolektif.

Pendekatan *pipeline* linear RAG+LLM (*retrieve-then-generate*) yang banyak digunakan saat ini memiliki keterbatasan mendasar untuk tugas identifikasi *synthesis gap*. Secara arsitektural, *pipeline* linear beroperasi pada level representasi semantik — kesamaan vektor dan generasi probabilistik — tanpa mekanisme penalaran bertahap dan validasi logis [Zhang et al., 2025]. Pendekatan ini berisiko menghasilkan korelasi semu (*spurious correlation*): dua konsep yang sering muncul bersama dalam teks (*co-occurrence*) dapat secara keliru diidentifikasi sebagai memiliki hubungan kausal, padahal hubungan tersebut hanya bersifat asosiatif-semantik. Lebih jauh, *pipeline* linear tidak memiliki mekanisme untuk memverifikasi apakah suatu rekomendasi *gap* secara logis konsisten dan layak (*feasible*), sehingga output yang dihasilkan dapat mencakup *gap* yang tidak bermakna atau bahkan cacat secara logika.

Paradigma *AI Agent* dengan kemampuan *multi-step reasoning* yang diintegrasikan dengan *Rule-Based Validation* menawarkan pendekatan yang secara struktural lebih mendekati proses kognitif peneliti manusia. Berbeda dengan *pipeline* linear, arsitektur *agentic* memungkinkan penalaran bertahap melalui siklus *Plan–Act–Observe–Evaluate–Repeat*, di mana setiap langkah dapat memanggil komponen (*tool*) yang berbeda sesuai kebutuhan [Yao et al., 2023]. Integrasi *Rule-Based Validation Layer* — yang terinspirasi dari prinsip sistem pakar dan logika formal — memberikan lapisan verifikasi deduktif di atas output penalaran neural, sehingga rekomendasi yang tidak memenuhi aturan kelayakan, kausalitas, atau konsistensi dapat disaring sebelum disajikan kepada pengguna. Pendekatan Neuro-Simbolik (*Neuro-Symbolic*) ini — yang menggabungkan penalaran neural (LLM *agent*) dengan penalaran simbolik (*rule engine* + *fact table*) — belum dieksplorasi secara memadai untuk domain spesifik deteksi *synthesis gap* dalam literatur ilmiah.

Berdasarkan uraian di atas, penelitian ini mengusulkan pengembangan sistem deteksi *synthesis gap* berbasis pendekatan *Neuro-Symbolic Agentic* yang mengintegrasikan: (1) arsitektur *agentic multi-step reasoning* untuk penalaran bertahap; (2) *Retrieval-Augmented Generation* untuk *grounding* faktual; (3) *Knowledge Graph* sebagai basis fakta terstruktur; dan (4) *Rule-Based Validation Layer* untuk validasi konsistensi logis. Sistem ini diposisikan sebagai alat bantu keputusan (*decision support tool*) yang menyajikan indikator-indikator *synthesis gap* kepada peneliti manusia, bukan sebagai pengganti proses penalaran induktif manusia.

---

## 1.2 Rumusan Masalah

Identifikasi *research gap* merupakan tahap kritis dalam penelitian ilmiah yang membutuhkan kemampuan sintesis tingkat tinggi: peneliti membaca sejumlah literatur, membandingkan temuan-temuan, menalar secara induktif, dan menyimpulkan apa yang belum terjawab secara kolektif [Cooper, 1998; Booth et al., 2012]. Proses ini secara kognitif bersifat logis-induktif — peneliti tidak sekadar mencari "apa yang belum ada," melainkan mengevaluasi apakah temuan-temuan yang sudah ada secara kolektif telah menghasilkan pemahaman yang utuh atau masih terfragmentasi dan inkonsisten.

Di sisi lain, pendekatan *pipeline* linear RAG+LLM (*retrieve-then-generate*) yang banyak digunakan saat ini beroperasi pada level representasi semantik — kesamaan vektor dan generasi probabilistik — tanpa mekanisme penalaran bertahap dan validasi logis. Pendekatan ini berisiko menghasilkan korelasi semu (*spurious correlation*) dan tidak mampu membedakan asosiasi semantik dari hubungan kausal yang sesungguhnya.

Paradigma *AI Agent* dengan kemampuan *multi-step reasoning* dan *rule-based validation* menawarkan pendekatan yang secara struktural lebih mendekati proses kognitif peneliti. Namun, belum diketahui secara memadai sejauh mana pendekatan *agentic* yang dilengkapi lapisan validasi logika formal mampu mendeteksi indikator-indikator *synthesis gap*, dan di mana batas kemampuannya dibandingkan penalaran manusia.

Berdasarkan kesenjangan tersebut, penelitian ini merumuskan tiga pertanyaan penelitian sebagai berikut:

1. **Sejauh mana pendekatan *agentic multi-step reasoning* yang dilengkapi *rule-based validation* mampu mendeteksi indikator *synthesis gap* (fragmentasi, inkonsistensi, dan ketidaklengkapan kolektif) dalam literatur ilmiah?**

   Pertanyaan ini menguji kemampuan inti sistem dalam mengidentifikasi tiga indikator utama *synthesis gap* sebagaimana didefinisikan oleh Cooper [1998] dan Booth et al. [2012]. Fragmentasi merujuk pada kondisi literatur yang terpecah-pecah tanpa integrasi; inkonsistensi merujuk pada temuan empiris yang saling bertentangan tanpa rekonsiliasi; dan ketidaklengkapan kolektif merujuk pada aspek-aspek kritis fenomena yang belum tercakup secara bersama oleh literatur yang ada.

2. **Bagaimana mekanisme pembeda asosiasi semantik dan hubungan logis (kausalitas/kontradiksi) serta *rule-based validation* memengaruhi tingkat akurasi dan *false discovery rate* dalam deteksi indikator *synthesis gap*?**

   Pertanyaan ini menginvestigasi kontribusi spesifik dari dua komponen kebaruan utama: (a) mekanisme tiga lapis untuk membedakan *co-occurrence* semantik dari hubungan kausal dan kontradiktif yang sesungguhnya, serta (b) lapisan validasi berbasis aturan yang menyaring rekomendasi berdasarkan kriteria kelayakan, kausalitas, dan konsistensi logis.

3. **Apa batasan-batasan epistemologis pendekatan ini dibandingkan dengan penalaran logis-induktif yang dilakukan peneliti manusia?**

   Pertanyaan ini secara eksplisit mengakui bahwa sistem komputasional memiliki batas kemampuan yang fundamental. Identifikasi batasan epistemologis — yaitu apa yang secara prinsip dapat dan tidak dapat dilakukan oleh sistem — merupakan kontribusi ilmiah yang sama pentingnya dengan demonstrasi kemampuan sistem.

---

## 1.3 Tujuan Penelitian

Berdasarkan rumusan masalah di atas, penelitian ini memiliki tujuan sebagai berikut:

1. **Mengukur kemampuan pendekatan *Neuro-Symbolic Agentic* dalam mendeteksi indikator *synthesis gap*.**

   Secara spesifik, tujuan ini mencakup pengembangan dan evaluasi sistem yang mengintegrasikan arsitektur *agentic multi-step reasoning*, RAG, *Knowledge Graph*, dan *Rule-Based Validation Layer* untuk mendeteksi tiga indikator *synthesis gap* — fragmentasi, inkonsistensi, dan ketidaklengkapan kolektif — dalam korpus literatur ilmiah. Evaluasi dilakukan melalui validasi pakar dengan metrik *Precision*, *Recall*, dan *F1-score*, serta perbandingan terhadap pendekatan *baseline* (*LLM-only*, analisis dokumen tunggal).

2. **Menganalisis pengaruh mekanisme pembeda asosiasi semantik–hubungan logis dan *rule-based validation* terhadap kualitas deteksi.**

   Tujuan ini mencakup evaluasi komparatif untuk mengisolasi kontribusi masing-masing komponen: (a) dampak mekanisme pembeda tiga lapis (penyaringan semantik, ekstraksi bukti, validasi aturan) terhadap kemampuan sistem membedakan *co-occurrence* dari hubungan kausal/kontradiktif; dan (b) dampak *Rule-Based Validation Layer* terhadap penurunan *false discovery rate* dan peningkatan presisi output sistem.

3. **Mengidentifikasi dan mendeskripsikan batasan-batasan epistemologis sistem secara eksplisit.**

   Tujuan ini mencakup analisis sistematis terhadap perbedaan fundamental antara penalaran yang dilakukan sistem (semantik-asosiatif dan deduktif-simbolik) dengan penalaran logis-induktif yang dilakukan peneliti manusia, serta formulasi rekomendasi tentang bagaimana sistem seharusnya diposisikan dan digunakan dalam praktik penelitian.

---

## 1.4 Manfaat Penelitian

Penelitian ini diharapkan memberikan manfaat baik secara teoretis maupun praktis:

### 1.4.1 Manfaat Teoretis

a. **Kontribusi terhadap pemahaman tentang batas kemampuan sistem *Neuro-Symbolic* dalam penalaran ilmiah.**
   Penelitian ini memberikan bukti empiris tentang sejauh mana integrasi penalaran neural (LLM) dengan penalaran simbolik (*rule engine*) mampu mendekati — dan di mana gagal mendekati — proses kognitif sintesis literatur yang dilakukan peneliti manusia. Temuan ini berkontribusi pada diskusi yang lebih luas tentang batas kemampuan kecerdasan buatan dalam tugas-tugas yang membutuhkan penalaran tingkat tinggi.

b. **Operasionalisasi konsep *synthesis gap* dalam konteks komputasional.**
   Dengan mendefinisikan tiga indikator *synthesis gap* yang terukur (fragmentasi, inkonsistensi, dan ketidaklengkapan kolektif) berdasarkan kerangka Cooper [1998] dan Booth et al. [2012], penelitian ini menyediakan definisi operasional yang dapat digunakan oleh penelitian selanjutnya dalam domain *automated literature analysis*.

c. **Kerangka evaluasi untuk sistem deteksi *research gap*.**
   Metodologi evaluasi yang dikembangkan — yang mencakup validasi pakar, perbandingan *baseline*, dan analisis batasan epistemologis — dapat diadopsi sebagai kerangka standar untuk mengevaluasi sistem serupa di masa mendatang.

### 1.4.2 Manfaat Praktis

a. **Bagi peneliti individu.**
   Sistem yang dikembangkan dapat membantu peneliti dalam tahap awal perencanaan penelitian dengan menyajikan indikator-indikator *synthesis gap* dari literatur yang relevan, sehingga mempercepat proses identifikasi peluang penelitian yang bermakna. Perlu ditekankan bahwa sistem berfungsi sebagai alat bantu yang menyajikan kandidat indikator, dan keputusan akhir tetap berada di tangan peneliti.

b. **Bagi kelompok riset dan laboratorium.**
   Sistem dapat dimanfaatkan untuk pemantauan literatur secara sistematis dalam suatu domain, membantu identifikasi area-area di mana fragmentasi atau inkonsistensi temuan membuka peluang untuk kontribusi penelitian baru.

c. **Bagi komunitas ilmiah yang lebih luas.**
   Implementasi *open-source* memungkinkan komunitas untuk mengadopsi, memodifikasi, dan mengembangkan sistem lebih lanjut. Arsitektur modular (*agentic* dengan *tool*-*tool* yang dapat diganti) memudahkan adaptasi ke domain ilmiah yang berbeda.

---

## 1.5 Batasan Epistemologis Sistem

Bagian ini secara eksplisit mendefinisikan apa yang dapat dan tidak dapat dilakukan oleh sistem yang dikembangkan, sebagai bentuk kejujuran ilmiah dan untuk mencegah klaim yang melampaui kapabilitas aktual sistem.

### 1.5.1 Apa yang DAPAT Dilakukan Sistem

Sistem yang dikembangkan beroperasi pada level semantik dan deduktif-simbolik, dengan kemampuan sebagai berikut:

| Kemampuan | Metode | Tingkat Keyakinan |
|-----------|--------|-------------------|
| Mendeteksi kesamaan topik antar-makalah | *Semantic similarity* (embedding SciBERT) | Tinggi |
| Mendeteksi terminologi berbeda untuk konsep yang sama | *Clustering* semantik | Tinggi |
| Mendeteksi klaim yang saling bertentangan | *Natural Language Inference* (NLI) + *Rule Engine* | Sedang–Tinggi |
| Mengidentifikasi aspek yang absen dari suatu makalah | Analisis cakupan (*coverage gap analysis*) | Sedang |
| Memvalidasi kelayakan logis suatu rekomendasi | *Rule-Based Validation* | Tinggi |
| Mengelompokkan makalah berdasarkan pendekatan | *Topic clustering* | Tinggi |

### 1.5.2 Apa yang TIDAK DAPAT Dilakukan Sistem

Terdapat batasan-batasan fundamental yang tidak dapat diatasi oleh arsitektur yang diusulkan:

| Keterbatasan | Alasan | Implikasi |
|-------------|--------|-----------|
| Menilai apakah suatu kombinasi ide logis secara mendalam | Membutuhkan penalaran kausal yang melampaui *rule engine* sederhana | *Rule engine* menangkap *constraint* eksplisit, bukan penilaian substantif |
| Memahami **mengapa** temuan saling bertentangan | Membutuhkan pemahaman konteks eksperimental yang mendalam | Sistem mendeteksi kontradiksi, bukan menjelaskan penyebabnya |
| Menentukan apakah suatu *gap* bermakna untuk dijadikan riset | Membutuhkan *scientific judgment* | Pemeringkatan bersifat heuristik, bukan substantif |
| Melakukan penalaran induktif sejati | LLM bersifat probabilistik, *Rule Engine* bersifat deduktif — keduanya bukan induktif | Sistem mengidentifikasi **indikator**, bukan menarik kesimpulan induktif |

### 1.5.3 Posisi Sistem

Sistem ini diposisikan sebagai **alat bantu keputusan** (*decision support tool*), **bukan** pengganti penalaran manusia. Dalam alur kerja yang diusulkan, sistem menerima masukan berupa sejumlah makalah ilmiah dan menghasilkan keluaran berupa **indikator** *synthesis gap* — bukan *synthesis gap* final. Peneliti manusia, dengan kapasitas penalaran induktif dan penilaian substantif, berperan sebagai pengambil keputusan akhir yang menerima atau menolak indikator-indikator yang disajikan oleh sistem.

### 1.5.4 Klaim yang TIDAK Dibuat

Untuk menghindari ambiguitas, berikut adalah klaim-klaim yang secara eksplisit **tidak** dibuat dalam penelitian ini:

1. Sistem **tidak** mengklaim mampu menalar secara induktif. Penalaran sistem bersifat asosiatif-semantik (via LLM) dan deduktif-simbolik (via *rule engine*), bukan induktif.
2. Sistem **tidak** mengklaim menemukan *gap* yang pasti valid. Output sistem adalah kandidat indikator yang memerlukan validasi manusia.
3. Sistem **tidak** mengklaim menggantikan proses *review* manusia. Sistem mempercepat identifikasi, bukan mengotomasi keputusan.
4. Sistem **tidak** mengklaim bahwa semua *synthesis gap* dapat dideteksi secara komputasional. Terdapat *gap* yang hanya dapat diidentifikasi melalui wawasan (*insight*) dan pengalaman domain seorang peneliti.

---

## 1.6 Batasan Masalah

Untuk memfokuskan penelitian dan memastikan kelayakan pencapaian dalam kerangka waktu yang tersedia, penelitian ini memiliki batasan-batasan sebagai berikut:

1. **Cakupan domain dan temporal.**
   Penelitian ini dibatasi pada domain *Computer Science*, khususnya sub-domain *Artificial Intelligence*, *Machine Learning*, *Natural Language Processing*, dan *Information Retrieval*. Periode publikasi yang dianalisis dibatasi pada rentang 2015–2025. Bahasa dokumen yang diproses adalah bahasa Inggris (*English*), mengingat mayoritas publikasi ilmiah di domain ini menggunakan bahasa Inggris dan model bahasa ilmiah pra-latih (SciBERT) dioptimasi untuk bahasa tersebut.

2. **Jumlah masukan makalah.**
   Setiap sesi analisis menerima masukan 3–10 makalah ilmiah. Batasan ini didasarkan pada pertimbangan beban kognitif (*cognitive load*) pengguna dalam mengevaluasi hasil dan keterbatasan komputasional dalam memproses dokumen secara simultan. Mekanisme akuisisi makalah (pencarian dan pemilihan) bukan merupakan fokus penelitian; analisis dimulai setelah makalah tersedia.

3. **Arsitektur *Knowledge Graph*.**
   *Knowledge Graph* yang dibangun bersifat ringan (*lightweight*), terbatas pada relasi *Paper*–*Concept*–*Method* tanpa rekayasa ontologi penuh (*full ontology engineering*) dan tanpa *graph embedding*. Pendekatan ini dipilih karena konstruksi ontologi penuh memerlukan upaya dan keahlian yang substansial [Abu-Salih et al., 2024] dan berada di luar cakupan tesis ini.

4. **Cakupan *Rule Engine*.**
   *Rule-Based Validation Layer* mengimplementasikan aturan logika dalam tiga kategori — kelayakan (*feasibility*), kausalitas (*causality*), dan konsistensi (*consistency*) — yang didefinisikan berdasarkan tinjauan literatur dan konsultasi pakar. Sistem aturan ini bersifat deduktif dan terbatas pada *constraint* yang dapat diformalisasi; aturan tersebut tidak mencakup penilaian substantif ilmiah.

5. **Evaluasi.**
   Evaluasi dilakukan melalui validasi pakar oleh 3–5 *evaluator* ahli domain, studi pengguna dengan 10–15 peneliti, dan perbandingan *baseline* (pendekatan *LLM-only* dan analisis dokumen tunggal). Evaluasi bersifat kuantitatif (metrik *Precision*, *Recall*, *F1-score*, *false discovery rate*) dan kualitatif (penilaian relevansi, kebaruan, dan kelayakan oleh pakar).

6. **Posisi sistem.**
   Sistem yang dikembangkan merupakan prototipe untuk keperluan penelitian dan evaluasi, bukan sistem siap produksi (*production-ready*). Sistem diposisikan sebagai alat bantu keputusan, bukan sistem yang beroperasi secara otonom tanpa supervisi manusia.

---

*Dokumen ini merupakan draf BAB I yang disusun berdasarkan panduan revisi dalam dokumen revisi.md (khususnya Bagian 2 dan 4) serta REVISI_PROPOSAL.md. Draf ini perlu didiskusikan dengan pembimbing sebelum finalisasi.*
