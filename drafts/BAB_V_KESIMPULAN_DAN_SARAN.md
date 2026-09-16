# BAB V: KESIMPULAN DAN SARAN

## 5.1 Kesimpulan

Penelitian ini merancang, mengimplementasikan, dan menguji Wizard Research —
sebuah *Neuro-Symbolic Agentic System* untuk mendeteksi **indikator**
*synthesis gap* (fragmentasi, inkonsistensi, ketidaklengkapan kolektif, dan
ketiadaan dukungan bukti; Cooper, 1998; Booth et al., 2012) pada kumpulan
literatur ilmiah. Sistem diuji pada dua korpus dengan dua rezim eksperimen
yang sengaja dipisahkan: korpus benchmark 23 paper *computer science* (model
lokal yang dapat di-*seed*, untuk uji ablasi multi-run) dan korpus aplikatif
35 jurnal forensika digital berbahasa Indonesia–Inggris (LLM penyedia, untuk
menguji sistem lengkap pada dokumen nyata). Kesimpulan disusun mengikuti tiga
pertanyaan penelitian pada BAB I Subbab 1.2, dengan pembedaan tegas antara apa
yang **terbukti** dan apa yang **belum terukur**.

### 5.1.1 Jawaban terhadap Pertanyaan Penelitian

**RQ1 — Sejauh mana pendekatan *agentic multi-step reasoning* yang dilengkapi
*rule-based validation* mampu mendeteksi indikator *synthesis gap*?**

Keempat indikator dapat dioperasionalkan dan dideteksi pada dokumen nyata
dengan rantai bukti yang dapat ditelusuri (klaim → jurnal terkutip → kutipan
verbatim → verdict validasi). Pada korpus benchmark, sistem menghasilkan 14
indikator dari 4 topik dalam eksekusi yang dirinci (17,2 ± 3,2 per *run* pada
lima *run*), berlandaskan 248 fakta SPO, dengan confidence rerata 0,700. Pada
korpus aplikatif, versi akhir sistem menghasilkan empat indikator yang lolos
validasi — dua fragmentasi, satu ketidaklengkapan kolektif, dan untuk pertama
kalinya satu ketiadaan dukungan bukti — yang saling menguatkan dari sinyal yang
independen satu sama lain: kopling bibliografis bebas-LLM (26 jurnal terpecah
dalam 19 kelompok tanpa rujukan bersama; 318 dari 325 pasangan terputus),
isolasi struktural *embedding* (0,82), peta cakupan aspek (10 dari 10 aspek
kritis tidak dibahas), dan uji kegagalan *retrieval* bukti primer (3 dari 3
klaim pembuka tanpa bukti di korpus). Dua dari indikator tersebut dikorroborasi
oleh pernyataan keterbatasan penulis di dalam korpus (M14: 2/2 yang dapat
dikorroborasi, 4 pernyataan, skor 0,68–0,71). Jawaban atas "sejauh mana"
karena itu adalah: **sistem mampu mendeteksi keempat indikator dengan bukti
yang dapat diaudit, pada dua bahasa, dan dengan sinyal bebas-LLM sebagai
jangkar** — tetapi dalam jumlah kecil per topik (2–4 indikator) dan dengan
stabilitas terbatas untuk temuan yang bergantung pada LLM: hanya 58,1%
pernyataan gap muncul kembali pada ≥ 2 dari 3 *run* identik (Jaccard antar-run
0,45–0,65), dan gap implisit hasil inferensi LLM adalah yang paling tidak
stabil (41% vs 63% untuk keterbatasan yang tersurat). Indikator inkonsistensi
adalah yang paling lemah (confidence 0,50 pada benchmark; tidak terdeteksi pada
korpus aplikatif). Ukuran akhir kemampuan deteksi terhadap penilaian manusia —
*Precision*, *Recall*, dan *F1* terhadap *gold standard* pakar — **belum dapat
dilaporkan** karena sesi penilaian pakar belum terlaksana.

**RQ2 — Bagaimana mekanisme pembeda asosiasi semantik–hubungan logis dan
*rule-based validation* memengaruhi akurasi dan *false discovery rate*?**

Tiga mekanisme terbukti mengubah keluaran ke arah yang dirancang. (a)
Lapisan verifikasi NLI *cross-encoder* meningkatkan jumlah indikator terdeteksi
(Δmedian = 8 per *run*) dan confidence-nya secara signifikan (Mann–Whitney U,
p Holm = 0,0428 pada keluarga 8 uji; Cliff's δ = 1,0; H9), dan indikator yang
hanya bersumber dari asosiasi semantik konsisten diberi label
`requires_human_validation`. (b) Lapisan validasi simbolis terbukti
diskriminatif — 6 dari 6 klaim adversarial menerima verdict sesuai harapan,
dengan penurunan confidence −0,60 pada pelanggaran kelayakan keras dan −0,15
hingga −0,20 pada pelanggaran yang memerlukan telaah manusia — dan verdict-nya
difusikan ke keyakinan terkalibrasi serta abstensi selektif, sehingga pada
korpus aplikatif 1 dari 4 indikator ditahan untuk peninjauan meskipun verdict
PASS, karena kutipannya tidak terambil. (c) Audit silang oleh LLM kritikus dari
model berbeda (H10) adalah penyaring presisi paling agresif: 85,6% kandidat
ditolak, indikator per *run* turun dari 24,3 menjadi 4,2 dengan keyakinan lebih
tinggi (0,791 → 0,884; p Holm = 0,0428). Pada topik kontrol negatif yang
sengaja tidak ada di korpus, sistem menghasilkan 0 indikator palsu pada 4 dari
5 *run* (0,2 ± 0,45 per *run*). Namun **pengaruh terhadap FDR itu sendiri belum
terkuantifikasi**: FDR = 1 − EAR memerlukan label pakar; proksi kuantitatif
Rule Engine (jumlah indikator dan confidence tanpa Rule Engine) tidak berbeda
signifikan (p Holm ≥ 0,48; H7) karena pada paper berkualitas tinggi Rule
Engine memang jarang menolak (RERR 0–4%). Bukti menunjukkan lapisan validasi
**mampu** menurunkan FDR, bukan **seberapa besar** ia menurunkannya. Satu
indikator palsu yang lolos ketiga lapisan dengan confidence 0,885 pada topik
kontrol menegaskan kesimpulan yang lebih fundamental: validasi neural maupun
simbolis tidak dapat menggantikan syarat kutipan verbatim — hanya rantai
provenans yang secara prinsip menolak klaim tentang topik yang tidak ada di
korpus.

**RQ3 — Apa batasan epistemologis pendekatan ini dibandingkan penalaran
logis-induktif peneliti manusia?**

Eksperimen mengonfirmasi dan mempertajam batasan yang dinyatakan pada BAB I
Subbab 1.5 dengan lima temuan empiris: (1) sistem **mendeteksi, tidak menilai
kebermaknaan** — ketiadaan suatu aspek dalam korpus benar secara struktural,
tetapi apakah itu gap yang layak diteliti hanya dapat diputuskan pakar; (2)
penalaran deduktif **terbatas pada fakta yang berhasil diekstrak** (248 fakta
dari 23 paper; 25–29 fakta dari paper representatif korpus forensik), sehingga
verdict PASS pada klaim yang tidak terhubung ke entitas KG adalah konsekuensi
cakupan fakta, bukan pernyataan kebenaran; (3) **stokastisitas adalah sifat**,
bukan gangguan — sistem tidak memiliki satu "jawaban" atas korpus yang sama,
berbeda dari peneliti yang mempertanggungjawabkan satu sintesis, dan pelaporan
k/n adalah pengakuan formal atas batas ini; (4) **sinyal yang paling andal
adalah yang paling sederhana** — kopling bibliografis dan kutipan verbatim
(bebas LLM) menghasilkan indikator berkeyakinan tertinggi dan dapat diaudit,
sedangkan gap implisit hasil inferensi LLM paling tidak stabil dan paling
kurang spesifik (LLM-judge 2,75/5 terhadap kurator manusia); (5) sistem
**tidak dapat menjelaskan "mengapa"** — ia mendeteksi bahwa jurnal tidak
saling mengutip atau temuan bertentangan, bukan sebab komunitas terpecah atau
desain eksperimen mana yang memicu kontradiksi. Kelima temuan ini menegaskan
posisi sistem sebagai *decision support tool* yang mempersempit ruang pencarian
dan menyediakan bukti yang dapat diaudit, sementara penilaian induktif tetap
berada pada peneliti.

### 5.1.2 Kontribusi Utama

Penelitian ini memberikan tujuh kontribusi:

1. **Rule-Based Validation Layer** dengan 9 aturan dalam 3 kategori (Kelayakan
   F1–F3, Kausalitas C1–C3, Konsistensi K1–K3) dan verdict PASS/FLAG/REJECT
   yang beroperasi independen dari LLM dalam waktu <0,01 detik, terbukti
   diskriminatif pada validasi adversarial (6/6).

2. **Fact Table berbasis SPO** dengan 8 tipe entitas, 12 predikat dasar, dan 2
   predikat turunan hasil inferensi Rule Engine (INFEASIBLE_FOR,
   CORRELATES_WITH), yang memungkinkan *grounding* klaim pada fakta
   terstruktur, bukan hanya pada keluaran stokastik LLM.

3. **Operasionalisasi empat indikator *synthesis gap*** yang dapat diukur,
   termasuk **indikator ketiadaan dukungan bukti** — klaim yang berulang lintas
   jurnal tetapi tidak memiliki bukti primer yang dapat ditelusuri (uji
   kegagalan *retrieval leave-one-out*) — yang berbeda dari ketidaklengkapan:
   aspeknya dibahas dan diklaim, tetapi tidak dibuktikan. Indikator ini
   terdeteksi pada korpus aplikatif (3/3 klaim tanpa bukti, 1 *citation echo*).

4. **Sinyal fragmentasi bebas-LLM** melalui kopling bibliografis (Kessler,
   1963) yang dihitung langsung dari daftar pustaka yang diurai tanpa model
   bahasa — memberikan bukti fragmentasi yang tidak bergantung pada LLM mana pun
   dan dapat diaudit (isolasi 0,978; modularitas 0,70; 3 sitasi langsung
   terverifikasi pada korpus forensik).

5. **Rantai provenans, kalibrasi, dan abstensi selektif** sebagai satu
   kesatuan: setiap indikator wajib memiliki rantai klaim → jurnal terkutip →
   kutipan verbatim → verdict; verdict difusikan ke keyakinan (PASS menguatkan,
   FLAG mendiskon, REJECT membatalkan); indikator dengan rantai terputus
   otomatis ditahan. Pada korpus nyata mekanisme ini terbukti diskriminatif
   (1 dari 4 ditahan), bukan penanda seragam.

6. **Lapisan korroborasi pernyataan penulis** yang memperlakukan keterbatasan
   dan *future work* yang ditulis penulis sebagai **bukti** bagi indikator
   lintas-jurnal — bukan sebagai gap dan bukan sebagai skor — dengan pemisahan
   eksplisit antara pernyataan tersurat dan tersirat.

7. **Protokol pelaporan k/n** untuk setiap temuan yang bergantung pada LLM
   (n = 3, ambang stabil ⌈2n/3⌉), beserta bukti empirisnya (58,1% stabil;
   Jaccard 0,45–0,65; gap implisit 41% vs keterbatasan tersurat 63%) — sebuah
   praktik yang belum lazim pada sistem RAG+LLM untuk analisis literatur, yang
   melaporkan satu eksekusi sebagai hasil.

### 5.1.3 Batas Klaim Penelitian Ini

Agar kesimpulan tidak dibaca melampaui buktinya, penelitian ini secara
eksplisit **tidak** menyimpulkan hal-hal berikut:

1. **Tidak** menyimpulkan bahwa indikator yang dihasilkan adalah *genuine
   synthesis gap*. *Expert Acceptance Rate*, *Logical Coherence Score*,
   *Actionability Score*, *False Discovery Rate*, *Semantic vs Human Gap*, dan
   *Rule Engine Precision* belum diukur; keempat kriteria keberhasilan Subbab
   3.7.5 (EAR ≥ 50%, LCS ≥ 3,5, penurunan FDR ≥ 20%, REP ≥ 70%) karena itu
   **belum dapat dinyatakan terpenuhi maupun gagal**. Instrumen pengukurannya
   telah lengkap dan teruji (formulir penilaian dari keluaran final kedua
   korpus, kalkulator metrik dengan Cohen's κ, kalibrator yang aktif otomatis
   setelah ≥ 4 label).

2. **Tidak** melaporkan ECE, Brier, dan AURC: kalibrator masih pemetaan
   identitas (temperature 1,0) karena label pakar belum ada, dan status ini
   ditampilkan apa adanya di antarmuka.

3. **Tidak** membandingkan angka korpus benchmark (Ollama, `llama3.2`/`gpt-oss`)
   dengan angka korpus aplikatif (`claude-opus-4.8-fast`): keduanya sahih
   hanya di dalam kelompoknya.

4. **Tidak** mengklaim H1, H2, dan H8 teruji: H1–H2 tidak lagi memiliki
   konfigurasi pembanding yang bermakna pada sistem akhir (pertanyaannya
   dijawab lebih tajam oleh H6, H7, H9); *user study* H8 tidak dilaksanakan.
   H6 dan H7 tidak signifikan pada proksi kuantitatif; kontribusinya bersifat
   kualitatif (akuntabilitas, kemampuan menolak klaim adversarial).

5. **Tidak** mengklaim *false-gap rate* sistem lengkap ≈ 0: kontrol negatif
   hanya dieksekusi pada mode *cross-critic*, dan satu indikator palsu
   berkeyakinan tinggi terbukti dapat lolos.

---

## 5.2 Saran

### 5.2.1 Prioritas Segera: Melengkapi Evaluasi yang Tertunda

1. **Sesi penilaian pakar** (prasyarat H4, H5, H7, dan keempat kriteria
   keberhasilan). Protokolnya sudah siap: minimal dua pakar forensika digital
   menilai secara *blinded* keempat indikator korpus aplikatif (eksekusi final)
   dan 18 indikator eksekusi `full` seed 43 korpus benchmark memakai formulir yang dibangkitkan dari keluaran final
   (`experiments/expert_eval/expert_form_forensik.xlsx`,
   `expert_form_benchmark.xlsx`) dengan rubrik *genuine / trivial / illogical /
   already addressed*, LCS, AS, peringkat, dan justifikasi REJECT; kesepakatan
   diukur dengan Cohen's κ (target ≥ 0,6) dan Krippendorff's α bila penilai
   > 2; ketidaksepakatan diselesaikan dengan penilai ketiga. Karena jumlah
   indikator per korpus kecil, sesi ini sebaiknya dijalankan pada keluaran
   gabungan beberapa *run* (union beranotasi k/n) agar himpunan yang dinilai
   cukup besar dan sekaligus menghasilkan **recall** terhadap *gold standard*
   pakar yang diidentifikasi sebelum melihat keluaran sistem.

2. **Aktivasi kalibrasi dan pelaporan ECE/Brier/AURC** segera setelah ≥ 4 label
   pakar tersedia; validasi silang implementasi ECE/temperature scaling dan
   ambang konformal terhadap pustaka baku (MAPIE, net:cal) sebelum angkanya
   dilaporkan.

3. **Kontrol negatif pada semua mode** (`full`, `nli`, dan pipeline korpus
   aplikatif), bukan hanya *cross-critic*, dengan ≥ 5 *run* per mode, agar
   *false-gap rate* konfigurasi yang benar-benar dipakai diketahui.

4. ***User study* H8** (*within-subject*, 10–15 mahasiswa S2/S3, dua kondisi
   *counterbalanced*) untuk mengukur penghematan waktu dan kualitas gap yang
   diidentifikasi dengan dan tanpa sistem.

### 5.2.2 Pengembangan Lanjutan

1. **Satu jalur validasi**. Eksekusi ulang versi akhir mengungkap Rule Engine
   berjalan dua kali dengan pengait fakta berbeda (analyzer dan koordinator)
   dan menghasilkan verdict yang berbeda; perbaikan sementara memfusikan
   verdict final ke kalibrasi, tetapi desain yang benar adalah satu pengait
   fakta dan satu verdict per indikator.

2. **Analisis sensitivitas ambang Rule Engine**. Penyesuaian confidence per
   aturan (−0,60 untuk F1/F3, −0,15 hingga −0,20 untuk C1/K1) dan default
   FLAG saat bukti tidak cukup masih *rule-of-thumb*; label pakar memungkinkan
   penyetelannya secara empiris.

3. **Stabilitas keputusan kritikus**. Mode *cross-critic* efektif memangkas
   kandidat tetapi keputusannya sendiri stokastik (1–11 indikator akhir per
   *run*); pelaporan k/n perlu diterapkan pada keputusan kritikus, dan
   kritikus deterministik (aturan atau NLI) layak dibandingkan dengan kritikus
   LLM.

4. **Komponen NLI dan *reranker* multibahasa**. Model NLI
   (`nli-deberta-v3-xsmall`) dan *reranker* (`ms-marco-MiniLM`) yang dipakai
   hanya dilatih pada bahasa Inggris, padahal korpus aplikatif berbahasa
   Indonesia; pengganti multibahasa (mis. mDeBERTa-XNLI, bge-reranker-v2-m3)
   dan evaluasinya pada SciFact/SciNLI/Evidence Inference telah dipetakan pada
   `docs/SUMBER_GITHUB.md`. Ini langkah paling langsung untuk memperkuat
   indikator inkonsistensi yang saat ini paling lemah.

5. **Cakupan fakta SPO**. Ekstraksi fakta hanya dilakukan pada paper
   representatif topik (25–29 fakta dari 4 paper pada korpus forensik);
   memperluasnya ke seluruh korpus — dengan pra-ekstraksi entitas bebas-LLM
   (mis. scispaCy) dan *baseline* ekstraksi relasi non-LLM sebagai pembanding —
   akan membuat aturan kausalitas dan konsistensi lebih sering benar-benar
   menyala, bukan lolos secara *default*.

6. **Skala dan domain**. Korpus 35 jurnal forensika digital telah membuktikan
   generalisasi lintas domain dan bahasa dari benchmark *computer science*;
   langkah berikutnya adalah 50–100 jurnal per domain pada dua domain tambahan
   dengan pakar domain masing-masing.

7. **Uji regresi berbentuk data produksi**. Empat cacat *silent* (tiga pada
   lapisan provenans, satu pada fusi verdict–kalibrasi) hanya terungkap pada
   dokumen nyata; setiap komponen baru sebaiknya disertai uji yang meniru
   bentuk data produksi, bukan sekadar bentuk yang valid.

### 5.2.3 Keterbatasan yang Perlu Diatasi

1. **Ketergantungan pada LLM dan penyedianya**. Kualitas ekstraksi fakta dan
   penambangan gap bergantung pada model; model penyedia tidak menjamin
   determinisme dan tidak mengekspos parameter *decoding*, sehingga stabilitas
   hanya dapat diukur secara empiris (k/n), bukan dikendalikan.

2. **Ketergantungan pada kualitas PDF**. Sepuluh dari 35 jurnal tidak dapat
   diikutkan dalam kopling bibliografis karena daftar pustakanya tidak terurai
   (editorial, bab buku, PDF Cyrillic, daftar pustaka terpotong); penguraian
   referensi berbasis GROBID/anystyle akan memperluas cakupan sinyal bebas-LLM.

3. **Skalabilitas**. Fase profil jurnal dan ekstraksi fakta mendominasi waktu
   (≈ 12 menit untuk 35 jurnal; 98,7% waktu benchmark pada ekstraksi fakta);
   paralelisasi dan *caching* per jurnal diperlukan untuk ratusan dokumen.

4. **Jumlah indikator yang kecil**. Dua hingga empat indikator per topik
   membuat evaluasi statistik per korpus lemah; evaluasi pakar sebaiknya
   dilakukan pada union beberapa *run* dan beberapa korpus.

### 5.2.4 Potensi Aplikasi

1. **Asisten riset akademis**: membantu mahasiswa dan peneliti menyempitkan
   ruang pencarian *synthesis gap* dari sekumpulan jurnal yang telah dipilih,
   dengan bukti kutipan yang dapat diperiksa — bukan menggantikan pembacaan.
2. **Penilaian proposal**: mendukung penelaah memeriksa apakah gap yang
   diklaim sebuah proposal benar-benar tidak terjawab korpus yang dirujuknya
   (uji kebaruan) dan apakah klaimnya berjangkar pada bukti primer.
3. **Pemetaan lanskap riset**: kopling bibliografis dan peta cakupan aspek
   memvisualisasikan komunitas yang terpecah dan sel bukti yang kosong pada
   suatu bidang.
4. **Audit kutipan**: indikator ketiadaan dukungan bukti dan *citation echo*
   dapat dipakai untuk menandai klaim latar belakang yang diwariskan antar
   paper tanpa bukti primer.
