import { useState } from 'react'
import {
  Printer, ChevronDown, ChevronRight,
  CheckCircle2, User, BookOpen,
  MessageSquare, ArrowRight, GraduationCap,
  Lightbulb, GitBranch
} from 'lucide-react'

/* ─── data: each aksi is now { judul, penjelasan, alur?, lokasi? } ─── */
const COMMENTS = [
  {
    id: 1,
    date: '24 Des 2025',
    kategori: 'Target Pengguna',
    komentar: 'Saya tidak setuju pendapat pengusul bahwa ide ini untuk calon peneliti. Sebab calon peneliti harus belajar berpikir sebagaimana manusia akademisi. Saya hanya setuju ini gunakan oleh yang sudah memiliki expertise pada bidangnya.',
    severity: 'warning',
    aksi: [
      {
        judul: 'Reposisi sistem dari "Sistem Otomatis" menjadi "Decision Support Tool"',
        penjelasan: 'Judul lama mengklaim sistem sebagai "Intelligent Research Gap Analyzer: Sistem Otomatis". Ini menyiratkan sistem bisa berjalan tanpa supervisi manusia. Setelah revisi, posisi sistem diubah menjadi alat bantu keputusan (decision support tool) \u2014 artinya sistem hanya menyajikan indikator dan bukti, sedangkan keputusan akhir tetap ada di tangan peneliti yang sudah expert di bidangnya.',
        lokasi: 'BAB I \u00a71.1 Latar Belakang, Judul Tesis',
      },
      {
        judul: 'Tambah bagian Batasan Epistemologis (BAB I \u00a71.5)',
        penjelasan: 'Bagian ini sepenuhnya baru. Di sini dituliskan secara eksplisit apa yang BISA dan TIDAK BISA dilakukan sistem. Tujuannya agar tidak ada klaim berlebihan. Sistem bisa mendeteksi kesamaan topik, terminologi berbeda untuk konsep sama, klaim bertentangan, dan aspek absen. Tapi sistem TIDAK BISA menilai kelayakan kombinasi ide secara mendalam, memahami "mengapa" temuan bertentangan, menentukan apakah gap bermakna, atau menalar secara induktif.',
        lokasi: 'BAB I \u00a71.5 (bagian baru)',
        alur: [
          'Tabel "Kemampuan Sistem" \u2014 5 hal yang BISA dilakukan beserta metode & tingkat keyakinan',
          'Tabel "Keterbatasan Sistem" \u2014 4 hal yang TIDAK BISA dilakukan beserta alasan',
          'Daftar 4 klaim yang secara eksplisit TIDAK dibuat oleh penelitian ini',
          'Pernyataan posisi: Input = papers, Output = indikator gap (bukan gap final), Manusia = pengambil keputusan akhir',
        ],
      },
      {
        judul: 'Tegaskan output = INDIKATOR, bukan kesimpulan final',
        penjelasan: 'Perubahan terminologi kunci di seluruh proposal: kata "menemukan gap" diganti menjadi "mendeteksi indikator gap". Ini bukan sekadar permainan kata \u2014 ini menggeser klaim epistemologis secara fundamental. Sistem menghasilkan sinyal (indikator fragmentasi, inkonsistensi, ketidaklengkapan) beserta bukti pendukung, tetapi keputusan apakah sinyal tersebut benar-benar merupakan synthesis gap yang valid tetap diserahkan kepada peneliti manusia.',
        lokasi: 'Seluruh BAB I\u2013V (perubahan terminologi konsisten)',
      },
    ],
    status: 'done',
  },
  {
    id: 2,
    date: '24 Des 2025',
    kategori: 'Rumusan Masalah',
    komentar: 'Rumusan masalah yang sepertinya ditulis oleh mahasiswa yang tidak paham apa itu masalah. Masalah adalah kesenjangan antara sains dengan kenyataan. Pertanyaan ini adalah pertanyaan seorang pribadi yang tidak tahu cara mengintegrasikan RAG dengan LLM.',
    kutipan: '"Bagaimana merancang arsitektur sistem berbasis RAG dan LLM yang mampu menganalisis beberapa jurnal untuk menemukan celah penelitian (synthesis gap) secara otomatis?"',
    severity: 'fatal',
    aksi: [
      {
        judul: 'TULIS ULANG TOTAL rumusan masalah',
        penjelasan: 'Rumusan lama berbentuk pertanyaan engineer ("Bagaimana merancang..."), bukan pertanyaan peneliti. Tidak ada fenomena, tidak ada kesenjangan pengetahuan. Rumusan baru mengikuti pola ilmiah: mulai dari fenomena yang diamati, lalu tunjukkan kesenjangan pengetahuan yang ada, baru formulasikan pertanyaan yang ingin dijawab.',
        lokasi: 'BAB I \u00a71.2 Rumusan Masalah',
        alur: [
          'FENOMENA: Proses identifikasi synthesis gap saat ini bergantung sepenuhnya pada penalaran induktif manusia yang membutuhkan waktu besar dan sulit direproduksi',
          'KESENJANGAN: Pipeline linear RAG+LLM yang ada tidak memiliki mekanisme validasi logis \u2014 hanya asosiasi semantik, rentan halusinasi dan korelasi semu',
          'PERTANYAAN: 3 Research Questions yang masing-masing menguji aspek berbeda dari solusi yang diusulkan',
        ],
      },
      {
        judul: '3 Research Questions baru yang terstruktur',
        penjelasan: 'Setiap RQ dirancang untuk menguji aspek spesifik: RQ1 menguji efektivitas pendekatan agentic secara keseluruhan, RQ2 menguji kontribusi masing-masing komponen (mekanisme pembeda dan rule engine), dan RQ3 secara jujur mengeksplorasi batasan pendekatan ini dibandingkan penalaran manusia. Pola kata kunci juga berubah dari "Bagaimana merancang..." menjadi "Sejauh mana..." untuk menunjukkan bahwa ini pengukuran, bukan tutorial.',
        lokasi: 'BAB I \u00a71.2',
        alur: [
          'RQ1: "Sejauh mana pendekatan agentic multi-step reasoning yang dilengkapi rule-based validation mampu mendeteksi indikator synthesis gap (fragmentasi, inkonsistensi, ketidaklengkapan kolektif)?"',
          'RQ2: "Bagaimana mekanisme pembeda asosiasi semantik dan hubungan logis serta rule-based validation memengaruhi tingkat akurasi dan false discovery rate?"',
          'RQ3: "Apa batasan-batasan epistemologis pendekatan ini dibandingkan dengan penalaran logis-induktif yang dilakukan peneliti manusia?"',
        ],
      },
    ],
    status: 'done',
  },
  {
    id: 3,
    date: '24 Des 2025',
    kategori: 'Definisi Synthesis Gap',
    komentar: "Definisi 'kombinasi ide baru' terlalu dangkal. Di level S2, sintesis bukan sekadar 'kawin silang' antara Metode X dan Kerangka Y. Sintesis adalah upaya logis untuk menyatukan literatur yang terpecah agar menjadi satu kesimpulan konklusif.",
    severity: 'fatal',
    aksi: [
      {
        judul: 'Ganti definisi ke Cooper (1998) & Booth et al. (2012)',
        penjelasan: 'Definisi lama ("Unexplored Combinations: Method A + Domain B") tidak ditemukan di literatur mainstream dan terlalu dangkal. Definisi baru berdasarkan referensi otoritatif: synthesis gap adalah kondisi di mana literatur yang ada tentang suatu fenomena BELUM menghasilkan kesimpulan terpadu yang konklusif, baik karena fragmentasi, inkonsistensi, atau ketidaklengkapan kolektif. Ini jauh lebih dalam \u2014 bukan soal belum pernah dicoba, tapi soal literatur yang sudah ada belum bisa disatukan.',
        lokasi: 'BAB II \u00a72.3 Definisi Synthesis Gap',
      },
      {
        judul: 'Operasionalisasi jadi 3 indikator terukur',
        penjelasan: 'Agar definisi tidak hanya konseptual, masing-masing aspek dari synthesis gap dijadikan indikator yang dapat dideteksi secara komputasional. Setiap indikator memiliki definisi operasional yang jelas, contoh konkret, dan metode deteksi.',
        lokasi: 'BAB II \u00a72.3, BAB III \u00a73.4',
        alur: [
          'FRAGMENTASI \u2014 Paper-paper membahas fenomena sama dari sudut berbeda tetapi tidak saling mengintegrasikan. Contoh: 10 studi tentang dropout di online learning, masing-masing pakai teori berbeda, tidak ada yang menyatukan.',
          'INKONSISTENSI \u2014 Temuan empiris saling bertentangan dan belum ada yang menyelesaikan. Contoh: Paper A mengatakan gamification meningkatkan motivasi, Paper B mengatakan menurunkan. Belum ada rekonsiliasi.',
          'KETIDAKLENGKAPAN KOLEKTIF \u2014 Aspek-aspek kritis dari fenomena belum dicakup secara bersama oleh literatur yang ada. Contoh: banyak studi efektivitas blended learning, tapi tidak ada yang membahas aspek equity/aksesibilitas.',
        ],
      },
      {
        judul: 'Tegaskan apa yang BUKAN synthesis gap',
        penjelasan: 'Penting untuk membatasi scope agar sistem tidak menghasilkan false positive. Tiga hal ini sering dikira synthesis gap tapi sebenarnya bukan: (1) Kombinasi metode-domain yang belum pernah ada \u2014 itu hanya "belum diterapkan", bukan gap sintesis. (2) Topik yang belum diteliti sama sekali \u2014 itu knowledge gap, bukan synthesis gap. (3) Saran "future work" di akhir paper \u2014 itu explicit gap yang sudah diketahui penulis.',
        lokasi: 'BAB II \u00a72.3, BAB I \u00a71.5',
      },
    ],
    status: 'done',
  },
  {
    id: 4,
    date: '24 Des 2025',
    kategori: 'Kemampuan Semantik',
    komentar: 'Proposal nampak wah.. tapi gagal menjelaskan bagaimana sistem yang berbasis semantik dapat menarik research gap. RAG dan LLM bukan sesuatu yang dapat menalar selayaknya manusia berpikir induktif.',
    severity: 'fatal',
    aksi: [
      {
        judul: 'Akui secara eksplisit: LLM TIDAK mampu menalar induktif',
        penjelasan: 'Penguji benar bahwa LLM bekerja berdasarkan probabilitas statistik (next-token prediction), bukan penalaran induktif sejati. Di BAB I \u00a71.5, hal ini diakui secara eksplisit. LLM hanya mengenali pola statistik dari training data, sementara penalaran induktif membutuhkan kemampuan membentuk generalisasi dari observasi spesifik \u2014 yang merupakan kemampuan kognitif tingkat tinggi manusia.',
        lokasi: 'BAB I \u00a71.5, BAB II \u00a72.4',
      },
      {
        judul: 'Tambah arsitektur Neuro-Symbolic sebagai solusi',
        penjelasan: 'Karena LLM saja tidak cukup, solusinya adalah menggabungkan kekuatan neural (LLM: pattern recognition, language understanding) dengan kekuatan symbolic (Rule Engine: penalaran deduktif, validasi logika). Pendekatan ini disebut Neuro-Symbolic AI (Garcez et al., 2019; Marcus, 2020). LLM bertugas mengekstrak informasi dan menghasilkan kandidat, Rule Engine bertugas memvalidasi secara logis.',
        lokasi: 'BAB II \u00a72.5, BAB III \u00a73.3',
        alur: [
          'Komponen Neural (LLM): Ekstraksi entitas & relasi dari teks, pemahaman bahasa, pencarian semantik via RAG, menghasilkan kandidat indikator gap',
          'Komponen Simbolik (Rule Engine): Validasi logika formal, cek konsistensi terhadap Knowledge Graph, filter berdasarkan 9 aturan (Feasibility, Causality, Consistency)',
          'Komponen Knowledge Graph: Menyimpan fakta terstruktur (SPO triples) yang diekstrak dari papers sebagai basis penalaran deduktif',
          'Integrasi: Output LLM (kandidat) \u2192 Dicek terhadap Fact Base (KG) \u2192 Divalidasi oleh Rule Engine \u2192 Verdict: PASS / FLAG / REJECT',
        ],
      },
      {
        judul: 'Daftar klaim yang secara eksplisit TIDAK dibuat',
        penjelasan: 'Untuk menghindari over-claiming, empat pernyataan negatif dituliskan secara eksplisit: (1) Sistem TIDAK mengklaim mampu menalar secara induktif. (2) Sistem TIDAK mengklaim menemukan gap yang pasti valid. (3) Sistem TIDAK mengklaim menggantikan proses review manusia. (4) Sistem TIDAK mengklaim bahwa pemeringkatan gap bersifat absolut. Ini penting karena menunjukkan kesadaran epistemologis peneliti.',
        lokasi: 'BAB I \u00a71.5 Batasan Epistemologis',
      },
    ],
    status: 'done',
  },
  {
    id: 5,
    date: '25 Des 2025',
    kategori: 'Kebaruan (Novelty)',
    komentar: 'Kombinasi RAG dan LLM sudah banyak diterapkan dan semuanya memiliki fundamental ide yang tidak berbeda. Tidak ada kebaruan dari usulan ini secara mendasar.',
    severity: 'fatal',
    aksi: [
      {
        judul: 'Geser klaim kebaruan ke Neuro-Symbolic Agentic System',
        penjelasan: 'Penguji benar bahwa RAG+LLM pipeline sudah banyak implementasinya (LangChain, LlamaIndex, dsb). Kebaruan tidak bisa diklaim pada level pipeline. Setelah revisi, kebaruan digeser ke integrasi pendekatan neural dengan simbolik dalam arsitektur agentic khusus untuk deteksi indikator synthesis gap \u2014 yang belum ada di literatur.',
        lokasi: 'BAB I \u00a71.1, Judul Tesis',
      },
      {
        judul: '4 pilar kebaruan yang dipertahankan',
        penjelasan: 'Masing-masing pilar menyumbang kebaruan karena sebelumnya tidak ada sistem yang menggabungkan keempat aspek ini untuk tujuan deteksi synthesis gap:',
        alur: [
          'Pilar 1 \u2014 Agentic Architecture: Bukan pipeline linear, tapi agent yang bisa Plan \u2192 Act \u2192 Observe \u2192 Reflect \u2192 Repeat/Stop. Agent bisa cek ulang klaimnya sendiri dan memilih tool yang tepat untuk sub-task berbeda.',
          'Pilar 2 \u2014 Rule Engine: 9 aturan logika formal (Feasibility, Causality, Consistency) yang memfilter output LLM sebelum disajikan ke pengguna. Ini lapisan validasi yang tidak ada di RAG biasa.',
          'Pilar 3 \u2014 Semantic-Logic Discriminator: Mekanisme 3 lapis yang membedakan asosiasi semantik (co-occurrence) dari hubungan logis (kausalitas, kontradiksi).',
          'Pilar 4 \u2014 KG as Fact Base: Knowledge Graph bukan hanya visualisasi, tapi menyimpan fakta terstruktur (SPO triples) yang digunakan Rule Engine untuk penalaran deduktif.',
        ],
      },
      {
        judul: 'Perubahan judul tesis',
        penjelasan: 'Judul lama: "Intelligent Research Gap Analyzer: Sistem Otomatis Berbasis RAG dan LLM untuk Identifikasi Celah Penelitian Multi-Jurnal." Judul baru: "Pendekatan Neuro-Symbolic Agentic untuk Deteksi Indikator Synthesis Gap pada Literatur Ilmiah." Perubahan ini mencerminkan: (1) bukan lagi RAG+LLM biasa, (2) bukan sistem otomatis tapi pendekatan ilmiah, (3) bukan "celah penelitian" yang ambigu tapi "indikator synthesis gap" yang terdefinisi.',
        lokasi: 'Judul, Halaman Judul, Seluruh Proposal',
      },
    ],
    status: 'done',
  },
  {
    id: 6,
    date: '25 Des 2025',
    kategori: 'Pembeda Semantik vs Logis',
    komentar: 'Anda harus menjelaskan bagaimana sistem membedakan antara konsep yang sekadar "sering muncul bersama" dengan konsep yang secara logis memiliki hubungan kausalitas atau kontradiksi.',
    severity: 'fatal',
    aksi: [
      {
        judul: 'Identifikasi 3 jenis hubungan yang harus dibedakan',
        penjelasan: 'Sebelum membangun mekanisme pembeda, perlu ditegaskan dulu ada 3 jenis hubungan: (1) Co-occurrence \u2014 dua konsep sering muncul bersama tanpa hubungan kausal, contoh "Python" dan "machine learning". (2) Kausalitas \u2014 A secara logis memengaruhi B, contoh "Overfitting menyebabkan kebutuhan regularization". (3) Kontradiksi \u2014 temuan A bertentangan dengan B, contoh "Method X meningkatkan akurasi" vs "Method X menurunkan akurasi". Semantik (embedding) hanya bisa mendeteksi co-occurrence. Kausalitas dan kontradiksi butuh analisis lebih dalam.',
        lokasi: 'BAB III \u00a73.5 Mekanisme Pembeda',
      },
      {
        judul: 'Mekanisme Pembeda 3 Lapis',
        penjelasan: 'Solusinya adalah pipeline bertingkat. Setiap kandidat hubungan antar-konsep harus melewati 3 lapis filter sebelum dianggap sebagai hubungan logis yang valid. Jika gagal di lapis manapun, hubungan tersebut di-downgrade atau ditolak.',
        lokasi: 'BAB III \u00a73.5',
        alur: [
          'LAPIS 1 \u2014 Semantic Filtering: Hitung cosine similarity antar-embedding konsep. Jika similarity > threshold, kandidat lolos ke lapis berikutnya. Jika tidak, hubungan dianggap tidak relevan dan dibuang. Ini adalah filter kasar untuk mengurangi jumlah kandidat.',
          'LAPIS 2 \u2014 Evidence Extraction (LLM Agent): LLM mencari bukti eksplisit dalam teks paper. Cari penanda kausal: "causes", "leads to", "results in", "because", "therefore". Cari penanda kontradiksi: "however", "contradicts", "in contrast", "inconsistent with". Jika TIDAK ditemukan penanda eksplisit, hubungan diberi label "co-occurrence only" dan TIDAK dianggap hubungan logis.',
          'LAPIS 3 \u2014 Rule-Based Validation: Kandidat yang lolos lapis 2 dicek terhadap aturan logika di Fact Base (Knowledge Graph). Apakah hubungan ini konsisten dengan fakta yang sudah ada? Apakah arah kausalitas benar? Apakah ada confounding variable? Jika lolos semua aturan: VALID RELATION. Jika melanggar: REJECTED + alasan penolakan.',
        ],
      },
    ],
    status: 'done',
  },
  {
    id: 7,
    date: '25 Des 2025',
    kategori: 'Rule-Based Validation',
    komentar: 'Untuk mengatasi risiko halusinasi LLM, Anda perlu menambahkan komponen Rule-Based Validation. Gunakan Knowledge Graph bukan hanya untuk retrieval, tetapi sebagai Knowledge Base (Fakta). Buatlah aturan logika formal.',
    severity: 'fatal',
    aksi: [
      {
        judul: 'Desain Rule Engine dengan 3 kategori \u00d7 3 aturan = 9 aturan total',
        penjelasan: 'Rule Engine berfungsi sebagai lapisan validasi terakhir sebelum output disajikan ke pengguna. Setiap output LLM (kandidat indikator gap) harus melewati 9 aturan yang dikelompokkan dalam 3 kategori. Rule Engine menggunakan fakta dari Knowledge Graph (Fact Base) untuk melakukan penalaran deduktif.',
        lokasi: 'BAB III \u00a73.6 Rule-Based Validation',
      },
      {
        judul: 'Kategori 1: Kelayakan (Feasibility) \u2014 F1, F2, F3',
        penjelasan: 'Aturan kelayakan memastikan rekomendasi sistem secara praktis masuk akal:',
        alur: [
          'F1 \u2014 Kompatibilitas Sumber Daya: Jika metode yang disarankan butuh sumber daya besar (misal GPT-4, cluster GPU), tapi masalah target berbasis perangkat mobile/edge \u2192 DITOLAK. Contoh: LLM sarankan "gunakan GPT-4 untuk edge device" \u2192 cacat logika.',
          'F2 \u2014 Kompatibilitas Data: Jika metode butuh data besar (supervised deep learning), tapi domain target memiliki data scarce (rare disease, low-resource language) \u2192 FLAG untuk review manusia.',
          'F3 \u2014 Kompatibilitas Skala: Jika metode butuh processing in-memory, tapi konteks masalah adalah big data \u2192 DITOLAK. Skala harus sesuai.',
        ],
      },
      {
        judul: 'Kategori 2: Kausalitas (Causality) \u2014 C1, C2, C3',
        penjelasan: 'Aturan kausalitas memastikan hubungan sebab-akibat yang diklaim sistem memiliki dasar yang kuat:',
        alur: [
          'C1 \u2014 Bukti Kausal Minimal: Hubungan kausal harus didukung minimal 2 sumber independen. Jika hanya 1 paper menyebut hubungan \u2192 DOWNGRADE dari "kausal" ke "korelasi".',
          'C2 \u2014 Arah Kausalitas Benar: Arah sebab-akibat harus logis. Contoh: "Hasil eksperimen menyebabkan hipotesis" \u2192 DITOLAK (arah terbalik \u2014 hipotesis mendahului eksperimen).',
          'C3 \u2014 Confounding Check: Jika A\u2192B tapi ada variabel C yang mungkin menyebabkan keduanya (confounding) \u2192 FLAG untuk review. Sistem harus cek di KG apakah ada path alternatif.',
        ],
      },
      {
        judul: 'Kategori 3: Konsistensi (Consistency) \u2014 K1, K2, K3',
        penjelasan: 'Aturan konsistensi memastikan output sistem tidak saling bertentangan:',
        alur: [
          'K1 \u2014 Non-kontradiksi Internal: Output sistem tidak boleh kontradiksi sendiri. Contoh: rekomendasikan metode X di poin 1 tapi tolak metode X di poin 3 \u2192 FLAG.',
          'K2 \u2014 Konsistensi dengan Fakta KG: Klaim yang dibuat harus didukung oleh fakta di Knowledge Graph. Jika klaim tidak ada basis fakta \u2192 DOWNGRADE confidence score.',
          'K3 \u2014 Transitivitas: Jika "A improves B" dan "B improves C" ada di KG, tapi output bilang "A worsens C" \u2192 FLAG karena melanggar transitivitas.',
        ],
      },
      {
        judul: '3 kemungkinan verdict dan aksi masing-masing',
        penjelasan: 'Setiap kandidat indikator gap mendapat verdict setelah melewati 9 aturan:',
        alur: [
          'PASS \u2014 Lolos semua aturan. Tampilkan ke pengguna dengan confidence score tinggi. Ini adalah indikator yang paling bisa dipercaya.',
          'FLAG \u2014 Melanggar aturan non-kritis. Tetap tampilkan ke pengguna TAPI dengan peringatan "Perlu review manusia" dan penjelasan aturan mana yang dilanggar.',
          'REJECT \u2014 Melanggar aturan kritis (cacat logika fundamental). JANGAN tampilkan ke pengguna. Simpan di log audit dengan alasan penolakan untuk transparansi.',
        ],
      },
    ],
    status: 'done',
  },
  {
    id: 8,
    date: '25 Des 2025',
    kategori: 'Diagram Alir',
    komentar: 'Diagram Anda saat ini masih terlalu linear dan sangat bergantung pada "Black Box" LLM. Tambahkan blok "Logical Consistency Checker". Definisikan logical rules: Aturan Kelayakan, Kausalitas, dan Konsistensi.',
    severity: 'fatal',
    aksi: [
      {
        judul: 'TULIS ULANG TOTAL: dari 3 tahap linear menjadi 4 fase dengan feedback loop',
        penjelasan: 'Diagram lama: Input \u2192 PDF Parse \u2192 Chunk \u2192 Embed \u2192 RAG Retrieve \u2192 LLM Generate \u2192 Output. Masalah: terlalu linear, LLM sebagai "black box" di tengah tanpa validasi, tidak ada pengecekan logika, tidak ada iterasi. Diagram baru memiliki 4 fase yang masing-masing punya input/output jelas, serta feedback loop di Fase 3 (agent bisa mengulang langkah jika perlu).',
        lokasi: 'BAB III \u00a73.2 Diagram Alir Metodologi',
      },
      {
        judul: 'Fase 1: INGESTION \u2014 Dari PDF mentah ke vector store',
        penjelasan: 'Fase ini mengubah input papers (3\u201310 paper PDF per sesi) menjadi representasi yang bisa dicari secara semantik.',
        alur: [
          'Input: 3\u201310 paper ilmiah dalam format PDF',
          'PDF Parser: Ekstrak teks dengan preservasi struktur (judul, abstrak, section, referensi)',
          'Section Splitter: Pisahkan per-section untuk menjaga konteks (Introduction, Method, Results, dsb)',
          'Chunk & Embed: Pecah ke chunk ~512 token, embed menggunakan SciBERT/all-MiniLM',
          'Output: Vector Store (ChromaDB) berisi seluruh chunk dari semua paper, siap untuk retrieval',
        ],
      },
      {
        judul: 'Fase 2: FACT EXTRACTION \u2014 Dari teks ke Knowledge Graph',
        penjelasan: 'Fase ini mengekstrak fakta terstruktur dari teks dan menyimpannya dalam Knowledge Graph sebagai Fact Base. Ini yang membedakan sistem ini dari RAG biasa \u2014 bukan hanya menyimpan teks, tapi juga memahami relasi antar-konsep.',
        alur: [
          'Entity Extractor (SciSpaCy + LLM): Identifikasi entitas ilmiah (METHOD, CONCEPT, DOMAIN, FINDING, dsb)',
          'Relation Extractor (LLM + Pattern Matching): Identifikasi hubungan antar-entitas (USES_METHOD, PROPOSES, CONTRADICTS, dsb)',
          'Fact Table Constructor: Bentuk triple Subject\u2013Predicate\u2013Object (SPO) dari setiap relasi',
          'Validasi: Cek duplikasi, konsistensi, dan kelengkapan triple sebelum masuk KG',
          'Output: Knowledge Graph (Fact Base) berisi fakta-fakta terstruktur yang siap digunakan Rule Engine',
        ],
      },
      {
        judul: 'Fase 3: AGENTIC ANALYSIS \u2014 Agent iteratif dengan multi-tool',
        penjelasan: 'Ini adalah jantung sistem. Berbeda dari pipeline linear, agent bisa merencanakan, bertindak, mengobservasi hasilnya, merefleksikan apakah sudah cukup, dan mengulang jika perlu. Agent memiliki akses ke beberapa tool yang dipilih sesuai kebutuhan sub-task.',
        alur: [
          'PLAN: Agent merencanakan langkah apa yang perlu dilakukan berdasarkan query/tujuan analisis',
          'ACT: Agent menjalankan tool yang dipilih (RAG Retriever, Paper Analyzer, NLI Checker, atau KG Querier)',
          'OBSERVE: Agent mengamati hasil dari tool yang dijalankan',
          'REFLECT: Agent mengevaluasi \u2014 apakah hasilnya cukup? Apakah ada yang perlu dicek ulang?',
          'REPEAT/STOP: Jika belum cukup, kembali ke PLAN dengan konteks baru. Jika sudah, hasilkan output.',
          'Output: Kandidat indikator gap + evidence + reasoning trace (BELUM divalidasi \u2014 masih RAW)',
        ],
      },
      {
        judul: 'Fase 4: LOGICAL CONSISTENCY CHECKER \u2014 Validasi sebelum output',
        penjelasan: 'Fase ini adalah komponen BARU yang diminta penguji. Semua kandidat dari Fase 3 harus melewati validasi logis sebelum disajikan ke pengguna. Ini yang memastikan output bukan sekadar halusinasi LLM.',
        alur: [
          'Input: Kandidat indikator gap dari Fase 3 (belum tervalidasi)',
          'Rule Engine membaca Fact Base (KG) sebagai basis fakta',
          'Cek 9 aturan: Feasibility (F1\u2013F3), Causality (C1\u2013C3), Consistency (K1\u2013K3)',
          'Berikan verdict per kandidat: PASS / FLAG / REJECT',
          'Output ke pengguna: Indikator yang PASS (confidence tinggi) + yang FLAG (perlu review) + reasoning trace + confidence scores',
          'Kandidat REJECT: TIDAK ditampilkan, tapi alasan penolakan tersimpan di log audit',
        ],
      },
    ],
    status: 'done',
  },
  {
    id: 9,
    date: '25 Des 2025',
    kategori: 'Knowledge Graph & Tabel Fakta',
    komentar: 'Saya ingin melihat di Bab III bagaimana Anda mentransformasi teks jurnal menjadi Tabel Fakta (Predikat-Subjek-Objek). Tanpa tabel fakta yang jelas, Knowledge Graph hanya alat visualisasi, bukan alat penalaran.',
    severity: 'fatal',
    aksi: [
      {
        judul: 'Transformasi KG dari alat visualisasi menjadi Fact Base untuk penalaran',
        penjelasan: 'Sebelumnya KG hanya menyimpan nodes & edges untuk divisualisasikan. Setelah revisi, KG dijadikan Fact Base \u2014 kumpulan fakta terstruktur dalam format SPO (Subject\u2013Predicate\u2013Object) yang bisa digunakan Rule Engine untuk melakukan penalaran deduktif. Ini perubahan paradigma: dari visualisasi ke reasoning.',
        lokasi: 'BAB III \u00a73.7 Knowledge Graph sebagai Fact Base',
      },
      {
        judul: 'Ontologi entitas: 8 tipe entitas ilmiah',
        penjelasan: 'Ontologi mendefinisikan "apa saja yang bisa menjadi entitas" dalam KG. 8 tipe dipilih karena mencakup elemen utama dalam paper ilmiah di bidang Computer Science:',
        alur: [
          'METHOD \u2014 Metode/algoritma yang digunakan (contoh: CNN, Random Forest, BERT)',
          'CONCEPT \u2014 Konsep abstrak (contoh: Transfer Learning, Attention Mechanism)',
          'DOMAIN \u2014 Bidang penerapan (contoh: Medical Imaging, NLP, Robotics)',
          'FINDING \u2014 Temuan empiris spesifik (contoh: "CNN achieves 95% accuracy on ImageNet")',
          'DATASET \u2014 Dataset yang digunakan (contoh: ImageNet, CIFAR-10, BraTS)',
          'METRIC \u2014 Metrik evaluasi (contoh: Accuracy, F1-Score, Dice Coefficient)',
          'PAPER \u2014 Paper sumber informasi (contoh: ResNet, He et al., 2016)',
          'CONSTRAINT \u2014 Batasan/kendala (contoh: High compute requirement, Low resource)',
        ],
      },
      {
        judul: 'Ontologi relasi: 12 predikat hubungan',
        penjelasan: 'Predikat mendefinisikan "bagaimana entitas saling berhubungan". 12 predikat dipilih karena mencakup jenis hubungan utama yang ada dalam paper ilmiah: USES_METHOD, PROPOSES, APPLIES_TO, ACHIEVES, REQUIRES_RESOURCE, REQUIRES_DATA, IMPROVES, CONTRADICTS, EXTENDS, EVALUATED_ON, HAS_CONSTRAINT, DISCUSSES. Setiap predikat memiliki aturan domain-range (misalnya USES_METHOD hanya valid antara PAPER dan METHOD).',
        lokasi: 'BAB III \u00a73.7',
      },
      {
        judul: 'Pipeline transformasi: Teks \u2192 Tabel Fakta SPO',
        penjelasan: 'Proses 4 langkah mengubah teks tidak terstruktur menjadi fakta terstruktur yang siap digunakan Rule Engine:',
        lokasi: 'BAB III \u00a73.7',
        alur: [
          'Langkah 1 \u2014 Entity Extraction (SciSpaCy + LLM): SciSpaCy mendeteksi entitas ilmiah umum, LLM menangkap entitas domain-specific yang missed oleh SciSpaCy',
          'Langkah 2 \u2014 Relation Extraction (LLM + Pattern Matching): LLM mengidentifikasi hubungan dari konteks kalimat, Pattern Matching menangkap pola eksplisit ("Method X achieves Y% on Dataset Z")',
          'Langkah 3 \u2014 Triple Construction: Bentuk SPO triple dari setiap relasi. Contoh dari teks "We propose CNN for medical image segmentation, achieves 92.3% Dice on BraTS": (Paper_Current, PROPOSES, CNN_Seg) + (CNN_Seg, APPLIES_TO, Medical_Image_Seg) + (CNN_Seg, ACHIEVES, Dice_92.3%) + (CNN_Seg, EVALUATED_ON, BraTS)',
          'Langkah 4 \u2014 Validasi & Inferensi: Cek duplikasi dan konsistensi. Lalu inferensi fakta turunan \u2014 misalnya dari (CNN_Seg, REQUIRES_RESOURCE, GPU_16GB+) dan Rule F1, sistem bisa menginfer: (CNN_Seg, INFEASIBLE_FOR, Edge_Deployment)',
        ],
      },
    ],
    status: 'done',
  },
]

/* ─── small components ─── */
const Badge = ({ children, variant = 'default' }) => {
  const cls = {
    default: 'bg-secondary text-secondary-foreground',
    fatal: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
    done: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  }
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls[variant] || cls.default}`}>{children}</span>
}

const Card = ({ children, className = '' }) => (
  <div className={`rounded-lg border bg-card text-card-foreground ${className}`}>{children}</div>
)

/* ─── action item renderer ─── */
const ActionItem = ({ aksi, index }) => (
  <div className="rounded-lg bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200/50 dark:border-emerald-800/30 p-4">
    <div className="flex items-start gap-2.5 mb-2">
      <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-500 text-white text-xs font-bold shrink-0 mt-0.5">{index + 1}</span>
      <h4 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300 leading-snug">{aksi.judul}</h4>
    </div>
    <p className="text-sm text-foreground/80 leading-relaxed ml-7.5 pl-[30px]">{aksi.penjelasan}</p>
    {aksi.lokasi && (
      <div className="flex items-center gap-1.5 mt-2 pl-[30px]">
        <BookOpen className="w-3 h-3 text-muted-foreground" />
        <span className="text-xs text-muted-foreground font-medium">{aksi.lokasi}</span>
      </div>
    )}
    {aksi.alur && aksi.alur.length > 0 && (
      <div className="mt-3 pl-[30px]">
        <div className="flex items-center gap-1.5 mb-2">
          <GitBranch className="w-3.5 h-3.5 text-blue-500 dark:text-blue-400" />
          <span className="text-xs font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wide">Alur / Detail</span>
        </div>
        <div className="space-y-2 relative">
          <div className="absolute left-[5px] top-2 bottom-2 w-px bg-blue-200 dark:bg-blue-800" />
          {aksi.alur.map((step, i) => (
            <div key={i} className="flex items-start gap-3 pl-0 relative">
              <div className="w-[11px] h-[11px] rounded-full border-2 border-blue-400 dark:border-blue-500 bg-background shrink-0 mt-1.5 z-10" />
              <p className="text-sm leading-relaxed text-foreground/75">{step}</p>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
)

/* ─── print action item (compact) ─── */
const PrintActionItem = ({ aksi, index }) => (
  <div className="mb-2 pl-4 border-l-2 border-emerald-500">
    <p className="text-xs font-bold">{index + 1}. {aksi.judul}</p>
    <p className="text-xs mt-0.5">{aksi.penjelasan}</p>
    {aksi.lokasi && <p className="text-xs text-gray-500 italic">[{aksi.lokasi}]</p>}
    {aksi.alur && aksi.alur.map((step, i) => (
      <p key={i} className="text-xs ml-3 mt-0.5">{'\u2192'} {step}</p>
    ))}
  </div>
)

/* ─── main page ─── */
const RevisionSummaryPage = () => {
  const [openItems, setOpenItems] = useState({})
  const doneCount = COMMENTS.filter(c => c.status === 'done').length

  const toggle = (id) => setOpenItems(prev => ({ ...prev, [id]: !prev[id] }))
  const expandAll = () => {
    const all = {}
    COMMENTS.forEach(c => { all[c.id] = true })
    setOpenItems(all)
  }
  const collapseAll = () => setOpenItems({})

  return (
    <>
      <style>{`
        @media print {
          @page { size: A4; margin: 15mm 12mm 15mm 15mm; }
          body { font-size: 9pt !important; }
          nav, .no-print { display: none !important; }
          .comment-card { page-break-inside: avoid; margin-bottom: 6pt; }
          .main-scroll { overflow: visible !important; height: auto !important; }
          .print-show { display: block !important; }
          .screen-only { display: none !important; }
        }
      `}</style>

      <div className="main-scroll min-h-[calc(100vh-3.5rem)] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-background/95 backdrop-blur border-b px-6 lg:px-10 py-4 no-print">
          <div className="flex items-center justify-between max-w-5xl mx-auto">
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-primary" />
                Catatan Revisi Proposal
              </h1>
              <p className="text-sm text-muted-foreground mt-0.5">Komentar Penguji → Aksi yang Dilakukan</p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 text-sm">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span className="font-medium">{doneCount}/{COMMENTS.length}</span>
              </div>
              <button onClick={() => window.print()} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90">
                <Printer className="w-4 h-4" />
                <span className="hidden sm:inline">Print A4</span>
              </button>
            </div>
          </div>
        </div>

        {/* Print header */}
        <div className="hidden print:block px-6 py-3 mb-1 text-center">
          <h1 className="text-base font-bold">CATATAN REVISI PROPOSAL TESIS</h1>
          <p className="text-xs">Andi Agung Dwi Arya B (D082251054) — Magister Teknik Informatika — UNHAS</p>
          <p className="text-xs text-gray-500">Seminar: 24–25 Des 2025 · Penguji: Prof. Dr. Adnan, ST., MT.</p>
        </div>

        <div className="max-w-5xl mx-auto px-6 lg:px-10 py-6">
          {/* Info + controls */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <GraduationCap className="w-5 h-5 text-primary" />
              <div>
                <p className="text-sm font-medium">Prof. Dr. Adnan, ST., MT.</p>
                <p className="text-xs text-muted-foreground">24\u201325 Desember 2025 \u00b7 {COMMENTS.filter(c => c.severity === 'fatal').length} FATAL \u00b7 {COMMENTS.filter(c => c.severity === 'warning').length} Arahan</p>
              </div>
            </div>
            <div className="flex gap-2 no-print">
              <button onClick={expandAll} className="text-xs text-primary hover:underline">Buka semua</button>
              <span className="text-muted-foreground">·</span>
              <button onClick={collapseAll} className="text-xs text-primary hover:underline">Tutup semua</button>
            </div>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap items-center gap-4 mb-5 p-3 rounded-lg bg-secondary/30 border no-print">
            <div className="flex items-center gap-1.5">
              <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
              <span className="text-xs text-muted-foreground">Klik kartu untuk melihat detail penjelasan & alur penyelesaian</span>
            </div>
            <div className="flex items-center gap-3 ml-auto text-xs">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> Aksi</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500" /> Alur</span>
            </div>
          </div>

          {/* Comments */}
          <div className="space-y-3">
            {COMMENTS.map((item) => {
              const isOpen = openItems[item.id]
              return (
                <div key={item.id} className="comment-card border rounded-lg overflow-hidden">
                  {/* Header row */}
                  <button
                    onClick={() => toggle(item.id)}
                    className="flex items-center gap-3 w-full px-4 py-3 text-left hover:bg-secondary/30 transition-colors"
                  >
                    {isOpen
                      ? <ChevronDown className="w-4 h-4 shrink-0 text-muted-foreground" />
                      : <ChevronRight className="w-4 h-4 shrink-0 text-muted-foreground" />
                    }
                    <span className="text-xs font-mono text-muted-foreground w-6">#{item.id}</span>
                    <span className="flex-1 text-sm font-medium">{item.kategori}</span>
                    <Badge variant={item.severity}>{item.severity === 'fatal' ? 'FATAL' : 'ARAHAN'}</Badge>
                    <Badge variant="done">{'\u2713'}</Badge>
                  </button>

                  {/* Content - screen */}
                  {isOpen && (
                    <div className="border-t p-4 sm:p-5 space-y-5 screen-only">
                      {/* Komentar */}
                      <div className="flex gap-3">
                        <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center shrink-0">
                          <User className="w-3.5 h-3.5 text-muted-foreground" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-xs text-muted-foreground mb-1">{item.date}</p>
                          <div className="bg-secondary/50 rounded-lg p-3 text-sm leading-relaxed">{item.komentar}</div>
                          {item.kutipan && (
                            <p className="mt-2 text-xs italic text-red-600 dark:text-red-400 bg-red-50/50 dark:bg-red-950/20 rounded p-2">
                              Kutipan asal: {item.kutipan}
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Aksi */}
                      <div className="ml-0 sm:ml-10">
                        <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                          <ArrowRight className="w-3.5 h-3.5" />
                          Aksi yang dilakukan ({item.aksi.length} langkah)
                        </p>
                        <div className="space-y-3">
                          {item.aksi.map((a, i) => (
                            <ActionItem key={i} aksi={a} index={i} />
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Content - print (always visible, compact) */}
                  <div className="hidden print-show border-t p-3 space-y-1">
                    <p className="text-xs">{item.komentar}</p>
                    {item.kutipan && <p className="text-xs italic text-red-700">Kutipan: {item.kutipan}</p>}
                    <p className="text-xs font-bold mt-1 mb-0.5">Aksi ({item.aksi.length}):</p>
                    {item.aksi.map((a, i) => (
                      <PrintActionItem key={i} aksi={a} index={i} />
                    ))}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Progress */}
          <Card className="p-4 mt-6 mb-8">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Progress Revisi</span>
              <span className="text-sm font-bold text-emerald-600">{doneCount}/{COMMENTS.length} selesai</span>
            </div>
            <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
              <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.round((doneCount / COMMENTS.length) * 100)}%` }} />
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}

export default RevisionSummaryPage
