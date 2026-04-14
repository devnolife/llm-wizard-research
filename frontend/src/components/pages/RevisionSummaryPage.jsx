import { useState, useRef } from 'react'
import {
  FileText, Printer, ChevronDown, ChevronRight,
  CheckCircle2, AlertTriangle, XCircle, Clock,
  BookOpen, Target, Layers, Shield, Database,
  GitBranch, BarChart3, FileCheck, Lightbulb, Ban,
  MessageSquare, ArrowRight, Quote, User, GraduationCap
} from 'lucide-react'

/* ─── data ─── */
const TIMELINE = [
  { version: 'v0', date: 'Des 2025', file: 'draf_proposal.pdf', label: 'Draft Proposal Awal', desc: 'Pipeline linear RAG+LLM', status: 'done' },
  { version: 'v1.0', date: '20 Des 2025', file: 'REVISI_PROPOSAL_OLD.md', label: 'Revisi Pertama', desc: 'Fokus Comparative Multi-Paper Analysis', status: 'done' },
  { version: 'v1.1', date: '20 Des 2025', file: 'REVISI_PROPOSAL.md', label: 'Koreksi Fokus', desc: 'Bukan paper search, tapi analisis setelah papers ada', status: 'done' },
  { version: 'v2.0', date: '2 Mar 2026', file: 'revisi.md', label: 'Master Dokumen Revisi', desc: 'Respons menyeluruh terhadap 8 kritik FATAL penguji', status: 'done' },
  { version: 'v3.0', date: '24 Mar 2026', file: 'PROPOSAL_REVISI_FINAL_v2.docx', label: 'Proposal Final', desc: 'BAB I–V lengkap dengan seluruh revisi terintegrasi', status: 'done' },
]

const SEMINAR_COMMENTS = [
  {
    id: 1,
    date: '24 Desember 2025',
    penguji: 'Prof. Dr. Adnan, ST., MT.',
    kategori: 'Target Pengguna',
    komentar: 'Saya tidak setuju pendapat pengusul bahwa ide ini untuk calon peneliti. Sebab calon peneliti harus belajar berpikir sebagaimana manusia akademisi. Saya hanya setuju ini gunakan oleh yang sudah memiliki expertise pada bidangnya.',
    solusi: 'Posisi sistem direvisi secara eksplisit menjadi "alat bantu keputusan (decision support tool)" untuk peneliti yang SUDAH memiliki expertise. Sistem menghasilkan indikator, bukan kesimpulan — peneliti manusia tetap pengambil keputusan akhir.',
    penjelasan: 'Perubahan ini tercermin di BAB I §1.5 (Batasan Epistemologis) dan perubahan judul dari "Sistem Otomatis" menjadi pendekatan yang menghasilkan "Indikator". Klaim-klaim yang TIDAK dibuat oleh sistem juga ditegaskan secara eksplisit.',
    ref: 'batasan',
    severity: 'warning',
  },
  {
    id: 2,
    date: '24 Desember 2025',
    penguji: 'Prof. Dr. Adnan, ST., MT.',
    kategori: 'Rumusan Masalah',
    komentar: 'Rumusan masalah yang sepertinya ditulis oleh mahasiswa yang tidak paham apa itu masalah. Masalah adalah kesenjangan antara sains dengan kenyataan. Harusnya disini dituliskan sebuah pertanyaan yang mengindikasikan kesenjangan tersebut. Pertanyaan ini adalah pertanyaan seorang pribadi yang tidak tahu cara mengintegrasikan RAG dengan LLM untuk keperluan identifikasi gap penelitian.',
    kutipan_asal: '"Bagaimana merancang arsitektur sistem berbasis RAG dan LLM yang mampu menganalisis beberapa jurnal untuk menemukan celah penelitian (synthesis gap) secara otomatis?"',
    solusi: 'Rumusan masalah DITULIS ULANG TOTAL menggunakan pola FENOMENA → KESENJANGAN → PERTANYAAN. Kata kunci berubah dari "Bagaimana merancang..." (pertanyaan engineer) menjadi "Sejauh mana..." (pertanyaan peneliti). Sekarang terdiri dari 3 Research Questions yang mengindikasikan kesenjangan pengetahuan.',
    penjelasan: 'RQ1: Sejauh mana pendekatan agentic mampu mendeteksi indikator synthesis gap? RQ2: Bagaimana mekanisme pembeda memengaruhi akurasi? RQ3: Apa batasan epistemologis pendekatan ini?',
    ref: 'rumusan',
    severity: 'danger',
  },
  {
    id: 3,
    date: '24 Desember 2025',
    penguji: 'Prof. Dr. Adnan, ST., MT.',
    kategori: 'Definisi Synthesis Gap',
    komentar: 'Definisi \'kombinasi ide baru\' yang pengusul tulis itu terlalu dangkal. Di level S2, sintesis bukan sekadar \'kawin silang\' antara Metode X dan Kerangka Y. Sintesis adalah upaya logis untuk menyatukan literatur yang terpecah agar menjadi satu kesimpulan yang konklusif. Bagaimana sistemmu bisa menjamin bahwa kombinasi X dan Y itu logis?',
    solusi: 'Definisi synthesis gap DIGANTI TOTAL dengan definisi Cooper (1998) & Booth, Sutton & Papaioannou (2012): synthesis gap = kondisi di mana literatur BELUM menghasilkan kesimpulan terpadu yang konklusif. Dioperasionalisasikan menjadi 3 indikator terukur: Fragmentasi, Inkonsistensi, Ketidaklengkapan Kolektif.',
    penjelasan: 'Yang BUKAN synthesis gap juga ditegaskan: ❌ Kombinasi metode-domain yang belum pernah ada (itu hanya "belum diterapkan"). ❌ Topik yang belum diteliti (itu knowledge gap). Sistem tidak menjamin kombinasi logis — sistem mendeteksi INDIKATOR bahwa literatur terpecah.',
    ref: 'gap',
    severity: 'danger',
  },
  {
    id: 4,
    date: '24 Desember 2025',
    penguji: 'Prof. Dr. Adnan, ST., MT.',
    kategori: 'Kemampuan Semantik vs Penalaran',
    komentar: 'Proposal agung nampak wah.. tapi gagal menjelaskan bagaimana sistem yang berbasis semantik dapat menarik research gap. RAG dan LLM bukan sesuatu yang dapat menalar selayaknya manusia berpikir induktif.',
    solusi: 'Ditambahkan bagian Batasan Epistemologis (BAB I §1.5) yang secara eksplisit mengakui bahwa LLM TIDAK mampu menalar induktif. Sistem diposisikan sebagai decision support tool yang menghasilkan indikator, bukan gap final.',
    penjelasan: 'Untuk mengompensasi keterbatasan LLM, ditambahkan komponen Neuro-Symbolic: Rule Engine (penalaran deduktif formal) + Knowledge Graph sebagai Fact Base + Mekanisme pembeda 3 lapis. Klaim yang TIDAK dibuat: sistem TIDAK menggantikan review manusia, TIDAK menalar induktif, TIDAK menemukan gap yang pasti valid.',
    ref: 'batasan',
    severity: 'danger',
  },
  {
    id: 5,
    date: '25 Desember 2025',
    penguji: 'Prof. Dr. Adnan, ST., MT.',
    kategori: 'Kebaruan (Novelty)',
    komentar: 'Kombinasi RAG dan LLM sudah banyak diterapkan dan semuanya memiliki fundamental ide yang tidak berbeda. Tidak ada kebaruan dari usulan ini secara mendasar. Hanya berbeda dalam penerapan.',
    solusi: 'Kebaruan digeser dari "RAG+LLM untuk research gap" (sudah banyak) ke Neuro-Symbolic Agentic System — integrasi penalaran neural (LLM) + simbolik (Rule Engine) dalam arsitektur agentic untuk deteksi synthesis gap. Ini BELUM ADA di literatur.',
    penjelasan: '4 pilar kebaruan: (1) Agentic Architecture — multi-step reasoning, bukan pipeline linear. (2) Rule Engine — 9 aturan formal untuk validasi output. (3) Semantic-Logic Discriminator — 3 lapis pembeda. (4) KG sebagai Fact Base — bukan sekadar visualisasi.',
    ref: 'arsitektur',
    severity: 'danger',
  },
  {
    id: 6,
    date: '25 Desember 2025',
    penguji: 'Prof. Dr. Adnan, ST., MT.',
    kategori: 'Penalaran Induktif vs Semantik',
    komentar: 'Anda harus menjelaskan bagaimana sistem membedakan antara konsep yang sekadar "sering muncul bersama" dengan konsep yang secara logis memiliki hubungan kausalitas atau kontradiksi.',
    solusi: 'Ditambahkan Mekanisme Pembeda 3 Lapis: (1) Semantic Filtering — filter berdasarkan similarity threshold. (2) Evidence Extraction — cari bukti eksplisit: penanda kausal (causes, leads to) & kontradiksi (however, contradicts). (3) Rule-Based Validation — cek terhadap aturan logika di Fact Base.',
    penjelasan: 'Tanpa penanda eksplisit dalam teks, hubungan dilabel "co-occurrence only" — tidak diklaim sebagai hubungan logis. Ini mencegah spurious correlation yang dikhawatirkan Prof.',
    ref: 'pembeda',
    severity: 'danger',
  },
  {
    id: 7,
    date: '25 Desember 2025',
    penguji: 'Prof. Dr. Adnan, ST., MT.',
    kategori: 'Rule-Based Validation Layer',
    komentar: 'Untuk mengatasi risiko halusinasi LLM dalam menyimpulkan gap, Anda perlu menambahkan satu komponen Rule-Based Validation. Gunakan Knowledge Graph bukan hanya untuk pencarian (retrieval), tetapi sebagai Knowledge Base (Fakta). Buatlah aturan logika formal.',
    solusi: 'Ditambahkan Rule Engine lengkap dengan 9 aturan dalam 3 kategori: Feasibility (F1-F3), Causality (C1-C3), Consistency (K1-K3). Setiap output LLM dicek terhadap aturan sebelum ditampilkan. 3 kemungkinan verdict: PASS, FLAG, REJECT.',
    penjelasan: 'Contoh implementasi: Jika LLM menyarankan "GPT-4 untuk edge device" → Rule F1 (kompatibilitas sumber daya) menolak karena cacat logika. Knowledge Graph digunakan sebagai Fact Base untuk menyediakan fakta bagi Rule Engine, bukan sekadar retrieval.',
    ref: 'rules',
    severity: 'danger',
  },
  {
    id: 8,
    date: '25 Desember 2025',
    penguji: 'Prof. Dr. Adnan, ST., MT.',
    kategori: 'Diagram Alir & Logical Checker',
    komentar: 'Diagram Anda saat ini masih terlalu linear dan sangat bergantung pada "Black Box" LLM. Tambahkan blok "Logical Consistency Checker" setelah proses Reasoning LLM. Definisikan logical rules: Aturan Kelayakan, Aturan Kausalitas, dan Aturan Konsistensi.',
    solusi: 'Diagram alir DITULIS ULANG TOTAL dari 3 tahap linear menjadi 4 Fase: (1) Ingestion, (2) Fact Extraction, (3) Agentic Analysis, (4) Logical Consistency Checker. Fase 4 adalah komponen BARU yang menjalankan Rule Engine sebagai filter terakhir.',
    penjelasan: 'Aturan sudah didefinisikan: Kelayakan (F1-F3), Kausalitas (C1-C3), Konsistensi (K1-K3). Arsitektur berubah dari monolitik ke modular agentic — agent dapat memanggil tool berbeda untuk sub-task berbeda, termasuk Rule Engine.',
    ref: 'arsitektur',
    severity: 'danger',
  },
  {
    id: 9,
    date: '25 Desember 2025',
    penguji: 'Prof. Dr. Adnan, ST., MT.',
    kategori: 'Knowledge Graph & Tabel Fakta',
    komentar: 'Saya ingin melihat di Bab III bagaimana Anda mentransformasi teks jurnal yang tidak terstruktur menjadi Tabel Fakta (Predikat-Subjek-Objek). Tanpa tabel fakta yang jelas, Knowledge Graph Anda hanya akan menjadi alat visualisasi, bukan alat penalaran.',
    solusi: 'KG ditransformasi menjadi Fact Base dengan ontologi eksplisit: 8 tipe entitas (METHOD, CONCEPT, DOMAIN, FINDING, DATASET, METRIC, PAPER, CONSTRAINT) dan 12 predikat relasi. Proses transformasi: Entity Extraction (SciSpaCy + LLM) → Relation Extraction → Triple Construction & Validation → Tabel SPO.',
    penjelasan: 'Contoh: Dari teks "We propose CNN for medical image segmentation, achieves 92.3% Dice..." → SPO: (Paper_Current, PROPOSES, CNN_Segmentation), (CNN_Segmentation, ACHIEVES, Dice_92.3%). Fakta turunan juga diinfer: CNN_Segmentation → INFEASIBLE_FOR → Edge_Deployment (via Rule F1).',
    ref: 'kg',
    severity: 'danger',
  },
]

const KRITIK = [
  { no: 1, tahap: 1, kritik: 'Rumusan masalah bukan "masalah" — hanya spesifikasi teknis berbentuk pertanyaan', respons: 'Direvisi menggunakan pola FENOMENA → KESENJANGAN → PERTANYAAN. Kata kunci berubah dari "Bagaimana merancang..." menjadi "Sejauh mana..."' },
  { no: 2, tahap: 1, kritik: 'Definisi synthesis gap tidak mainstream — "Kombinasi Method A + Domain B" terlalu dangkal', respons: 'Diganti dengan definisi Cooper (1998) & Booth (2012): fragmentasi, inkonsistensi, ketidaklengkapan kolektif' },
  { no: 3, tahap: 1, kritik: 'Tidak dijelaskan bagaimana sistem semantik menarik research gap — batas kemampuan LLM tidak diakui', respons: 'Ditambahkan bagian Batasan Epistemologis yang eksplisit (BAB I §1.5) — sistem adalah decision support tool' },
  { no: 4, tahap: 1, kritik: 'RAG+LLM bukan sesuatu yang baru — tidak ada kebaruan mendasar', respons: 'Kebaruan digeser ke Neuro-Symbolic Agentic System — integrasi penalaran neural + simbolik' },
  { no: 5, tahap: 2, kritik: 'Tidak bisa bedakan asosiasi semantik vs hubungan logis', respons: 'Ditambahkan mekanisme 3 lapis: Semantic Filtering → Evidence Extraction → Rule-Based Validation' },
  { no: 6, tahap: 2, kritik: 'Perlu Rule-Based Validation Layer', respons: 'Ditambahkan Rule Engine dengan 9 aturan dalam 3 kategori (F1–F3, C1–C3, K1–K3) dan 3 verdict' },
  { no: 7, tahap: 2, kritik: 'Diagram alir terlalu linear & black box', respons: 'Direvisi menjadi 4 Fase: Ingestion → Fact Extraction → Agentic Analysis → Logical Consistency Checker' },
  { no: 8, tahap: 2, kritik: 'Knowledge Graph tanpa Tabel Fakta SPO', respons: 'KG ditransformasi menjadi Fact Base dengan ontologi eksplisit: 8 tipe entitas, 12 predikat, tabel SPO' },
]

const RULES = [
  { id: 'F1', cat: 'Feasibility', rule: 'Kompatibilitas sumber daya', example: 'LLM sarankan "GPT-4 untuk edge device" → DITOLAK' },
  { id: 'F2', cat: 'Feasibility', rule: 'Kompatibilitas data', example: '"Supervised DL untuk rare disease" (data scarce) → FLAG' },
  { id: 'F3', cat: 'Feasibility', rule: 'Kompatibilitas skala', example: '"In-memory processing untuk big data" → DITOLAK' },
  { id: 'C1', cat: 'Causality', rule: 'Bukti kausal minimal (≥2 sumber)', example: 'Hanya 1 paper menyebut hubungan → DOWNGRADE ke korelasi' },
  { id: 'C2', cat: 'Causality', rule: 'Arah kausalitas benar', example: '"Hasil eksperimen menyebabkan hipotesis" → DITOLAK' },
  { id: 'C3', cat: 'Causality', rule: 'Confounding check', example: 'A→B tapi ada C yang mungkin menyebabkan keduanya → FLAG' },
  { id: 'K1', cat: 'Consistency', rule: 'Non-kontradiksi internal', example: 'Sistem rekomendasikan X di poin 1 tapi tolak X di poin 3 → FLAG' },
  { id: 'K2', cat: 'Consistency', rule: 'Konsistensi dengan fakta KG', example: 'Klaim tidak didukung fakta KG → DOWNGRADE confidence' },
  { id: 'K3', cat: 'Consistency', rule: 'Transitivitas', example: '"A improves B" + "B improves C" tapi output bilang "A worsens C" → FLAG' },
]

const METRIK = [
  { no: 1, name: 'Expert Acceptance Rate (EAR)', desc: '% indikator yang dinilai pakar sebagai genuine synthesis gap' },
  { no: 2, name: 'Logical Coherence Score (LCS)', desc: 'Skor 1-5 dari pakar: apakah indikator logis/masuk akal' },
  { no: 3, name: 'Actionability Score (AS)', desc: 'Skor 1-5: apakah indikator cukup spesifik untuk ditindaklanjuti' },
  { no: 4, name: 'False Discovery Rate (FDR)', desc: '% indikator yang ternyata bukan gap' },
  { no: 5, name: 'Semantic vs Human Gap (SHG)', desc: 'Korelasi Spearman ranking sistem vs ranking pakar' },
  { no: 6, name: 'Rule Engine Rejection Rate (RERR)', desc: '% output LLM yang ditolak rule engine' },
  { no: 7, name: 'Rule Engine Precision (REP)', desc: 'Dari yang ditolak, berapa % memang pantas ditolak' },
]

const IMPL_STATUS = [
  { komponen: 'Agent Orchestrator (LangGraph)', file: 'backend/app/core/agents/', status: 'done' },
  { komponen: 'RAG Pipeline', file: 'backend/app/core/rag/', status: 'done' },
  { komponen: 'Gap Analyzer (3 indikator)', file: 'backend/app/core/gap_detection/analyzer.py', status: 'done' },
  { komponen: 'Rule Engine', file: 'backend/app/core/gap_detection/rule_engine.py', status: 'done' },
  { komponen: 'Fact Table', file: 'backend/app/core/gap_detection/fact_table.py', status: 'done' },
  { komponen: 'Recommendation Engine', file: 'backend/app/core/recommendation/engine.py', status: 'done' },
  { komponen: 'ChromaDB Vector Store', file: 'chroma_db/ (1423 dokumen)', status: 'done' },
  { komponen: 'Frontend Dashboard', file: 'frontend/src/components/', status: 'done' },
  { komponen: 'Mekanisme pembeda semantik vs logis', file: 'NLI + Evidence Extraction', status: 'partial' },
  { komponen: 'Evaluasi 7 metrik', file: '—', status: 'pending' },
  { komponen: 'User study', file: '—', status: 'pending' },
]

const RINGKASAN_TABEL = [
  { aspek: 'Judul', sebelum: 'RAG + LLM otomatis', sesudah: 'Neuro-Symbolic Agentic' },
  { aspek: 'Rumusan masalah', sebelum: '"Bagaimana merancang..."', sesudah: '"Sejauh mana..."' },
  { aspek: 'Definisi synthesis gap', sebelum: 'Kombinasi Method+Domain', sesudah: 'Cooper (1998): fragmentasi, inkonsistensi, ketidaklengkapan' },
  { aspek: 'Batasan epistemologis', sebelum: 'Tidak ada', sesudah: 'Eksplisit (BISA/TIDAK BISA)' },
  { aspek: 'Arsitektur', sebelum: 'Pipeline linear 3 tahap', sesudah: '4 Fase + Agentic + Rule Engine' },
  { aspek: 'Validasi logis', sebelum: 'Tidak ada', sesudah: 'Rule Engine (9 aturan, 3 kategori)' },
  { aspek: 'Knowledge Graph', sebelum: 'Visualisasi saja', sesudah: 'Fact Base (SPO triples)' },
  { aspek: 'Pembeda semantik vs logis', sebelum: 'Tidak ada', sesudah: 'Mekanisme 3 lapis' },
  { aspek: 'Evaluasi', sebelum: 'Precision/Recall saja', sesudah: '7 metrik + 8 hipotesis + user study' },
  { aspek: 'Posisi sistem', sebelum: '"Sistem otomatis"', sesudah: '"Decision support tool"' },
  { aspek: 'Referensi', sebelum: '25 teknis', sesudah: '40+ (termasuk fondasi konseptual)' },
  { aspek: 'Kebaruan', sebelum: 'RAG+LLM (sudah banyak)', sesudah: 'Neuro-Symbolic untuk synthesis gap (belum ada)' },
]

/* ─── small components ─── */
const Badge = ({ children, variant = 'default' }) => {
  const cls = {
    default: 'bg-secondary text-secondary-foreground',
    success: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
    warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
    danger: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    info: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    new: 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-400',
  }
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls[variant] || cls.default}`}>{children}</span>
}

const StatusIcon = ({ status }) => {
  if (status === 'done') return <CheckCircle2 className="w-4 h-4 text-emerald-500" />
  if (status === 'partial') return <AlertTriangle className="w-4 h-4 text-amber-500" />
  return <Clock className="w-4 h-4 text-muted-foreground" />
}

const Card = ({ children, className = '' }) => (
  <div className={`rounded-lg border bg-card text-card-foreground ${className}`}>{children}</div>
)

const Section = ({ id, icon: Icon, title, badge, children }) => (
  <section id={id} className="print-section">
    <div className="flex items-center gap-3 mb-4">
      {Icon && <Icon className="w-5 h-5 text-primary shrink-0 no-print" />}
      <h2 className="text-xl font-semibold">{title}</h2>
      {badge && <Badge variant="new">{badge}</Badge>}
    </div>
    {children}
  </section>
)

const CompareBox = ({ label, variant, children }) => {
  const styles = variant === 'old'
    ? 'border-red-200 bg-red-50/50 dark:border-red-900/50 dark:bg-red-950/20'
    : 'border-emerald-200 bg-emerald-50/50 dark:border-emerald-900/50 dark:bg-emerald-950/20'
  const labelCls = variant === 'old' ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'
  return (
    <div className={`rounded-lg border p-4 ${styles}`}>
      <div className={`text-xs font-semibold uppercase tracking-wide mb-2 ${labelCls}`}>{label}</div>
      <div className="text-sm leading-relaxed">{children}</div>
    </div>
  )
}

const Collapsible = ({ title, defaultOpen = false, children }) => {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border rounded-lg">
      <button onClick={() => setOpen(!open)} className="flex items-center justify-between w-full px-4 py-3 text-sm font-medium text-left hover:bg-secondary/50 transition-colors">
        {title}
        {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>
      {open && <div className="px-4 pb-4 border-t">{children}</div>}
    </div>
  )
}

/* ─── main page ─── */
const RevisionSummaryPage = () => {
  const [activeSection, setActiveSection] = useState('timeline')
  const contentRef = useRef(null)

  const NAV_ITEMS = [
    { id: 'timeline', label: 'Timeline Progress', icon: GitBranch },
    { id: 'seminar', label: 'Catatan Seminar', icon: MessageSquare },
    { id: 'kritik', label: 'Kritik & Respons', icon: Target },
    { id: 'judul', label: 'Perubahan Judul', icon: FileText },
    { id: 'rumusan', label: 'Rumusan Masalah', icon: Lightbulb },
    { id: 'gap', label: 'Definisi Synthesis Gap', icon: BookOpen },
    { id: 'arsitektur', label: 'Arsitektur', icon: Layers },
    { id: 'rules', label: 'Rule Engine', icon: Shield },
    { id: 'kg', label: 'Knowledge Graph', icon: Database },
    { id: 'pembeda', label: 'Mekanisme Pembeda', icon: GitBranch },
    { id: 'batasan', label: 'Batasan Epistemologis', icon: Ban },
    { id: 'evaluasi', label: 'Framework Evaluasi', icon: BarChart3 },
    { id: 'implementasi', label: 'Status Implementasi', icon: FileCheck },
    { id: 'ringkasan', label: 'Ringkasan', icon: FileText },
  ]

  const scrollTo = (id) => {
    setActiveSection(id)
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const doneCount = IMPL_STATUS.filter(i => i.status === 'done').length
  const totalCount = IMPL_STATUS.length
  const progress = Math.round((doneCount / totalCount) * 100)

  return (
    <>
      {/* Print styles */}
      <style>{`
        @media print {
          @page { size: A4; margin: 18mm 15mm 18mm 20mm; }
          body { font-size: 10pt !important; }
          nav, .no-print { display: none !important; }
          .print-section { page-break-inside: avoid; margin-bottom: 12pt; }
          .print-break { page-break-before: always; }
          table { font-size: 9pt; }
          h2 { page-break-after: avoid; }
          .sidebar-nav { display: none !important; }
          .main-scroll { margin-left: 0 !important; padding: 0 !important; overflow: visible !important; height: auto !important; }
          .page-wrapper { display: block !important; }
        }
      `}</style>

      <div className="page-wrapper flex h-[calc(100vh-3.5rem)]">
        {/* Sidebar navigation */}
        <aside className="sidebar-nav no-print w-60 shrink-0 border-r bg-card overflow-y-auto hidden lg:block">
          <div className="p-4 border-b">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Ringkasan Revisi</h3>
            <p className="text-xs text-muted-foreground">Proposal Tesis v0 → v3.0</p>
          </div>
          <nav className="p-2 space-y-0.5">
            {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => scrollTo(id)}
                className={`flex items-center gap-2 w-full px-3 py-2 rounded-md text-xs transition-colors text-left ${
                  activeSection === id
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                }`}
              >
                <Icon className="w-3.5 h-3.5 shrink-0" />
                {label}
              </button>
            ))}
          </nav>
          {/* Print button in sidebar */}
          <div className="p-3 border-t">
            <button
              onClick={() => window.print()}
              className="flex items-center justify-center gap-2 w-full px-3 py-2 rounded-md text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Printer className="w-3.5 h-3.5" />
              Print A4
            </button>
          </div>
        </aside>

        {/* Main content */}
        <div ref={contentRef} className="main-scroll flex-1 overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 z-10 bg-background/95 backdrop-blur border-b px-6 lg:px-10 py-4 no-print">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold">Ringkasan Revisi Proposal Tesis</h1>
                <p className="text-sm text-muted-foreground mt-0.5">
                  Andi Agung Dwi Arya B — Magister Teknik Informatika, Universitas Hasanuddin
                </p>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block">
                  <div className="text-sm font-medium">{progress}%</div>
                  <div className="text-xs text-muted-foreground">Implementasi</div>
                </div>
                <div className="w-20 h-2 bg-secondary rounded-full overflow-hidden hidden sm:block">
                  <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${progress}%` }} />
                </div>
                <button
                  onClick={() => window.print()}
                  className="lg:hidden inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <Printer className="w-4 h-4" />
                  Print
                </button>
              </div>
            </div>
          </div>

          {/* Print header */}
          <div className="hidden print:block px-6 py-4 mb-4">
            <h1 className="text-xl font-bold text-center">RINGKASAN REVISI PROPOSAL TESIS</h1>
            <p className="text-center text-sm mt-1">Andi Agung Dwi Arya B (D082251054) — Magister Teknik Informatika — Universitas Hasanuddin</p>
            <p className="text-center text-xs text-gray-500 mt-0.5">Kompilasi: April 2026</p>
          </div>

          <div className="px-6 lg:px-10 py-6 space-y-10 max-w-5xl">

            {/* ── 1. TIMELINE PROGRESS ── */}
            <Section id="timeline" icon={GitBranch} title="Timeline Progress Revisi">
              <div className="relative">
                {TIMELINE.map((item, i) => (
                  <div key={item.version} className="flex gap-4 mb-6 last:mb-0">
                    {/* Line + dot */}
                    <div className="flex flex-col items-center">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                        item.status === 'done' ? 'bg-primary text-primary-foreground' : 'bg-secondary text-muted-foreground'
                      }`}>
                        {item.status === 'done' ? <CheckCircle2 className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
                      </div>
                      {i < TIMELINE.length - 1 && <div className="w-px flex-1 bg-border mt-1" />}
                    </div>
                    {/* Content */}
                    <div className="pb-2 pt-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant={i === TIMELINE.length - 1 ? 'success' : 'default'}>{item.version}</Badge>
                        <span className="text-xs text-muted-foreground">{item.date}</span>
                      </div>
                      <h3 className="font-medium mt-1">{item.label}</h3>
                      <p className="text-sm text-muted-foreground">{item.desc}</p>
                      <code className="text-xs text-muted-foreground mt-1 block">{item.file}</code>
                    </div>
                  </div>
                ))}
              </div>
            </Section>

            {/* ── CATATAN SEMINAR/UJIAN ── */}
            <Section id="seminar" icon={MessageSquare} title="Catatan Seminar / Ujian Proposal">
              <Card className="p-4 mb-4 bg-amber-50/50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/50">
                <div className="flex items-start gap-3">
                  <GraduationCap className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <h3 className="text-sm font-semibold">Seminar Proposal — 24-25 Desember 2025</h3>
                    <p className="text-xs text-muted-foreground mt-1">Penguji: <strong>Prof. Dr. Adnan, ST., MT.</strong> — Menyampaikan 9 poin kritik & arahan fundamental yang menjadi dasar seluruh revisi proposal.</p>
                  </div>
                </div>
              </Card>

              <div className="space-y-4">
                {SEMINAR_COMMENTS.map((item) => (
                  <Card key={item.id} className="overflow-hidden">
                    {/* Header */}
                    <div className={`px-4 py-2 flex items-center justify-between text-xs ${
                      item.severity === 'danger' ? 'bg-red-50 dark:bg-red-950/30 border-b border-red-200 dark:border-red-900/50' : 'bg-amber-50 dark:bg-amber-950/30 border-b border-amber-200 dark:border-amber-900/50'
                    }`}>
                      <div className="flex items-center gap-2">
                        <Badge variant={item.severity === 'danger' ? 'danger' : 'warning'}>Kritik #{item.id}</Badge>
                        <span className="font-medium">{item.kategori}</span>
                      </div>
                      <span className="text-muted-foreground">{item.date}</span>
                    </div>

                    <div className="p-4 space-y-3">
                      {/* Komentar penguji */}
                      <div className="flex gap-3">
                        <div className="shrink-0 mt-1">
                          <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center">
                            <User className="w-3.5 h-3.5 text-muted-foreground" />
                          </div>
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-muted-foreground mb-1">{item.penguji}</p>
                          <div className="bg-secondary/50 rounded-lg p-3 text-sm leading-relaxed italic">
                            "{item.komentar}"
                          </div>
                          {item.kutipan_asal && (
                            <div className="mt-2 flex items-start gap-2 bg-red-50/70 dark:bg-red-950/20 rounded p-2 text-xs">
                              <Quote className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
                              <span className="text-red-600 dark:text-red-400 italic">{item.kutipan_asal}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Solusi */}
                      <div className="ml-10 border-l-2 border-emerald-300 dark:border-emerald-700 pl-4">
                        <div className="flex items-center gap-2 mb-1">
                          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                          <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wide">Solusi yang Dilakukan</span>
                        </div>
                        <p className="text-sm">{item.solusi}</p>
                      </div>

                      {/* Penjelasan */}
                      <div className="ml-10 bg-blue-50/50 dark:bg-blue-950/20 rounded-lg p-3">
                        <p className="text-xs font-semibold text-blue-700 dark:text-blue-400 mb-1">Penjelasan Detail</p>
                        <p className="text-xs text-muted-foreground leading-relaxed">{item.penjelasan}</p>
                      </div>

                      {/* Link ke section terkait */}
                      <button
                        onClick={() => scrollTo(item.ref)}
                        className="ml-10 inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
                      >
                        <ArrowRight className="w-3 h-3" />
                        Lihat detail di section terkait
                      </button>
                    </div>
                  </Card>
                ))}
              </div>

              {/* Summary stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
                <Card className="p-3 text-center">
                  <div className="text-2xl font-bold text-primary">9</div>
                  <div className="text-xs text-muted-foreground">Total Kritik</div>
                </Card>
                <Card className="p-3 text-center">
                  <div className="text-2xl font-bold text-emerald-500">9</div>
                  <div className="text-xs text-muted-foreground">Sudah Direspons</div>
                </Card>
                <Card className="p-3 text-center">
                  <div className="text-2xl font-bold text-red-500">8</div>
                  <div className="text-xs text-muted-foreground">Kritik FATAL</div>
                </Card>
                <Card className="p-3 text-center">
                  <div className="text-2xl font-bold text-amber-500">1</div>
                  <div className="text-xs text-muted-foreground">Saran/Arahan</div>
                </Card>
              </div>
            </Section>

            {/* ── 2. KRITIK PENGUJI ── */}
            <Section id="kritik" icon={Target} title="8 Kritik Penguji & Respons">
              <p className="text-sm text-muted-foreground mb-4">Penguji menyampaikan <strong>8 kritik FATAL</strong> dalam 2 tahap:</p>

              <div className="mb-4">
                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">Tahap 1 — Fondasi Konseptual</h3>
                <div className="space-y-3">
                  {KRITIK.filter(k => k.tahap === 1).map(k => (
                    <Card key={k.no} className="p-4">
                      <div className="flex items-start gap-3">
                        <span className="w-6 h-6 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 flex items-center justify-center text-xs font-bold shrink-0">{k.no}</span>
                        <div className="min-w-0">
                          <p className="text-sm font-medium">{k.kritik}</p>
                          <div className="mt-2 flex items-start gap-2 text-sm text-emerald-700 dark:text-emerald-400">
                            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                            <span>{k.respons}</span>
                          </div>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">Tahap 2 — Arsitektur & Metodologi</h3>
                <div className="space-y-3">
                  {KRITIK.filter(k => k.tahap === 2).map(k => (
                    <Card key={k.no} className="p-4">
                      <div className="flex items-start gap-3">
                        <span className="w-6 h-6 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 flex items-center justify-center text-xs font-bold shrink-0">{k.no}</span>
                        <div className="min-w-0">
                          <p className="text-sm font-medium">{k.kritik}</p>
                          <div className="mt-2 flex items-start gap-2 text-sm text-emerald-700 dark:text-emerald-400">
                            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                            <span>{k.respons}</span>
                          </div>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>

              <Card className="p-4 mt-4 bg-blue-50/50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900/50">
                <h4 className="text-sm font-semibold mb-2">Pola Tuntutan Penguji</h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                  <div><Badge variant="info">KONSEPTUAL</Badge><p className="mt-1 text-muted-foreground">Perbaiki definisi synthesis gap & akui batas kemampuan sistem</p></div>
                  <div><Badge variant="info">KEBARUAN</Badge><p className="mt-1 text-muted-foreground">RAG+LLM bukan kebaruan → perlu AI Agent + Rule Engine</p></div>
                  <div><Badge variant="info">PENALARAN</Badge><p className="mt-1 text-muted-foreground">Bukan hanya semantik → harus ada lapisan logika formal</p></div>
                </div>
              </Card>
            </Section>

            {/* ── 3. PERUBAHAN JUDUL ── */}
            <Section id="judul" icon={FileText} title="Perubahan Judul">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <CompareBox label="❌ Lama (Ditolak)" variant="old">
                  <p className="font-medium">"Intelligent Research Gap Analyzer: Sistem Otomatis Berbasis RAG dan LLM"</p>
                  <p className="mt-2 text-muted-foreground">Paradigma: Pipeline linear RAG+LLM</p>
                  <p className="text-muted-foreground">Posisi: "Sistem otomatis"</p>
                </CompareBox>
                <CompareBox label="✅ Baru (Diterima)" variant="new">
                  <p className="font-medium">Pendekatan Neuro-Symbolic Agentic untuk Deteksi Indikator Synthesis Gap</p>
                  <p className="mt-2 text-muted-foreground">Paradigma: Agentic multi-step reasoning + validasi simbolik</p>
                  <p className="text-muted-foreground">Posisi: "Alat bantu keputusan (decision support tool)"</p>
                </CompareBox>
              </div>
            </Section>

            {/* ── 4. RUMUSAN MASALAH ── */}
            <Section id="rumusan" icon={Lightbulb} title="Revisi Rumusan Masalah">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <CompareBox label="❌ Lama (Ditolak)" variant="old">
                  <p className="italic">"Bagaimana merancang arsitektur sistem berbasis RAG dan LLM yang mampu menganalisis beberapa jurnal untuk menemukan celah penelitian secara otomatis?"</p>
                  <p className="mt-2 text-xs text-red-600 dark:text-red-400">Pertanyaan engineer, bukan pertanyaan peneliti.</p>
                </CompareBox>
                <CompareBox label="✅ Baru (Diterima)" variant="new">
                  <p className="text-xs text-emerald-600 dark:text-emerald-400 mb-2">Pola: FENOMENA → KESENJANGAN → PERTANYAAN</p>
                  <ol className="space-y-2 text-sm list-decimal list-inside">
                    <li><strong>Sejauh mana</strong> pendekatan agentic multi-step reasoning mampu mendeteksi indikator synthesis gap?</li>
                    <li><strong>Bagaimana</strong> mekanisme pembeda semantik-logis memengaruhi akurasi & false discovery rate?</li>
                    <li><strong>Apa batasan epistemologis</strong> pendekatan ini dibandingkan penalaran manusia?</li>
                  </ol>
                </CompareBox>
              </div>
            </Section>

            {/* ── 5. DEFINISI SYNTHESIS GAP ── */}
            <Section id="gap" icon={BookOpen} title="Revisi Definisi Synthesis Gap">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <CompareBox label="❌ Lama" variant="old">
                  <p>3 Types: Unexplored Combinations, Bridging Gaps, Resolution Gaps</p>
                  <p className="mt-2 text-xs text-red-600 dark:text-red-400">"Unexplored Combinations" = kawin silang dangkal — CNN + Medical Imaging bukan sintesis.</p>
                </CompareBox>
                <CompareBox label="✅ Baru — Cooper (1998)" variant="new">
                  <p className="italic">Synthesis gap = kondisi di mana literatur BELUM menghasilkan kesimpulan terpadu yang konklusif</p>
                </CompareBox>
              </div>
              <h3 className="text-sm font-semibold mb-3">3 Indikator Terukur</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  { name: 'Fragmentasi', desc: 'Paper-paper membahas fenomena sama dari sudut berbeda tetapi tidak saling mengintegrasikan', color: 'border-blue-300 dark:border-blue-800' },
                  { name: 'Inkonsistensi', desc: 'Temuan empiris saling bertentangan dan belum ada yang menyelesaikan', color: 'border-amber-300 dark:border-amber-800' },
                  { name: 'Ketidaklengkapan', desc: 'Aspek kritis dari fenomena belum dicakup secara bersama oleh literatur', color: 'border-violet-300 dark:border-violet-800' },
                ].map(ind => (
                  <Card key={ind.name} className={`p-4 border-l-4 ${ind.color}`}>
                    <h4 className="font-medium text-sm">{ind.name}</h4>
                    <p className="text-xs text-muted-foreground mt-1">{ind.desc}</p>
                  </Card>
                ))}
              </div>
            </Section>

            {/* ── 6. ARSITEKTUR ── */}
            <Section id="arsitektur" icon={Layers} title="Perubahan Arsitektur">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <CompareBox label="❌ Pipeline Linear (Lama)" variant="old">
                  <pre className="text-xs whitespace-pre-wrap font-mono">Input → PDF Parse → Chunk → Embed → RAG → LLM → Output{'\n'}                                         (Black Box){'\n'}                                     Tidak ada validasi</pre>
                </CompareBox>
                <CompareBox label="✅ 4 Fase (Baru)" variant="new">
                  <div className="space-y-2 text-xs">
                    {[
                      { fase: '1', name: 'INGESTION', desc: 'PDF → Section Split → Chunk & Embed → Vector Store' },
                      { fase: '2', name: 'FACT EXTRACTION', desc: 'Entity Extractor → Fact Table → Knowledge Graph' },
                      { fase: '3', name: 'AGENTIC ANALYSIS', desc: 'Plan → Act → Observe → Reflect → Repeat/Stop' },
                      { fase: '4', name: 'LOGICAL CHECKER', desc: 'Rule Engine → Verdict: PASS / FLAG / REJECT' },
                    ].map(f => (
                      <div key={f.fase} className="flex items-start gap-2">
                        <span className="bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400 rounded px-1.5 py-0.5 font-bold shrink-0">F{f.fase}</span>
                        <div><span className="font-semibold">{f.name}</span> — {f.desc}</div>
                      </div>
                    ))}
                  </div>
                </CompareBox>
              </div>

              <Card className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-secondary/50">
                      <th className="px-4 py-2 text-left font-medium">Aspek</th>
                      <th className="px-4 py-2 text-left font-medium">Pipeline Linear</th>
                      <th className="px-4 py-2 text-left font-medium">Agentic + Rule Engine</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {[
                      ['Proses', 'Linear: Retrieve → Generate → selesai', 'Iteratif: Plan → Act → Observe → Reflect'],
                      ['Self-verification', '❌ Tidak ada', '✅ Agent cek ulang klaimnya'],
                      ['Tool use', 'Monolitik', 'Modular — tool berbeda per sub-task'],
                      ['Validasi logis', '❌ Tidak ada', '✅ Rule Engine sebagai tool'],
                      ['Kebaruan', '❌ Sudah banyak implementasi', '✅ Agent + Rule Engine untuk synthesis gap'],
                    ].map(([aspek, lama, baru]) => (
                      <tr key={aspek}>
                        <td className="px-4 py-2 font-medium">{aspek}</td>
                        <td className="px-4 py-2 text-muted-foreground">{lama}</td>
                        <td className="px-4 py-2">{baru}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </Section>

            {/* ── 7. RULE ENGINE ── */}
            <Section id="rules" icon={Shield} title="Rule-Based Validation Layer" badge="BARU">
              <p className="text-sm text-muted-foreground mb-4">Rule Engine menyaring output LLM sebelum disajikan ke pengguna — <strong>3 Kategori × 3 Aturan = 9 Aturan Total</strong></p>

              {['Feasibility', 'Causality', 'Consistency'].map(cat => (
                <div key={cat} className="mb-4">
                  <h3 className="text-sm font-semibold mb-2">{cat} ({RULES.filter(r => r.cat === cat).map(r => r.id).join(', ')})</h3>
                  <div className="space-y-2">
                    {RULES.filter(r => r.cat === cat).map(r => (
                      <Card key={r.id} className="p-3 flex items-start gap-3">
                        <Badge>{r.id}</Badge>
                        <div className="min-w-0">
                          <p className="text-sm font-medium">{r.rule}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">{r.example}</p>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              ))}

              <h3 className="text-sm font-semibold mb-3">3 Verdict</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Card className="p-3 border-l-4 border-l-emerald-400">
                  <div className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-500" /><span className="font-medium text-sm">PASS</span></div>
                  <p className="text-xs text-muted-foreground mt-1">Output lolos semua aturan — tampilkan dengan confidence score</p>
                </Card>
                <Card className="p-3 border-l-4 border-l-amber-400">
                  <div className="flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-500" /><span className="font-medium text-sm">FLAG</span></div>
                  <p className="text-xs text-muted-foreground mt-1">Melanggar aturan non-kritis — tampilkan dengan peringatan</p>
                </Card>
                <Card className="p-3 border-l-4 border-l-red-400">
                  <div className="flex items-center gap-2"><XCircle className="w-4 h-4 text-red-500" /><span className="font-medium text-sm">REJECT</span></div>
                  <p className="text-xs text-muted-foreground mt-1">Melanggar aturan kritis — JANGAN tampilkan + berikan alasan</p>
                </Card>
              </div>
            </Section>

            {/* ── 8. KNOWLEDGE GRAPH ── */}
            <Section id="kg" icon={Database} title="Knowledge Graph → Fact Base" badge="BARU">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <CompareBox label="❌ Lama" variant="old">
                  <p>Fungsi: Alat visualisasi hubungan</p>
                  <p>Struktur: Sekadar nodes & edges</p>
                  <p>Pemanfaatan: Tidak digunakan untuk reasoning</p>
                </CompareBox>
                <CompareBox label="✅ Baru" variant="new">
                  <p>Fungsi: <strong>Fact Base</strong> untuk penalaran formal</p>
                  <p>Struktur: Tabel Fakta SPO (Subject–Predicate–Object)</p>
                  <p>Pemanfaatan: Digunakan oleh Rule Engine</p>
                </CompareBox>
              </div>

              <Collapsible title="Ontologi: 8 Tipe Entitas & 12 Predikat">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 mb-4">
                  {['METHOD', 'CONCEPT', 'DOMAIN', 'FINDING', 'DATASET', 'METRIC', 'PAPER', 'CONSTRAINT'].map(t => (
                    <Badge key={t}>{t}</Badge>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">12 Predikat: USES_METHOD, PROPOSES, APPLIES_TO, ACHIEVES, REQUIRES_RESOURCE, REQUIRES_DATA, IMPROVES, CONTRADICTS, EXTENDS, EVALUATED_ON, HAS_CONSTRAINT, DISCUSSES</p>
              </Collapsible>

              <Collapsible title="Contoh Tabel Fakta SPO">
                <Card className="overflow-x-auto mt-3">
                  <table className="w-full text-xs">
                    <thead><tr className="border-b bg-secondary/50"><th className="px-3 py-2 text-left">Subject</th><th className="px-3 py-2 text-left">Predicate</th><th className="px-3 py-2 text-left">Object</th></tr></thead>
                    <tbody className="divide-y">
                      {[
                        ['Paper_Current', 'PROPOSES', 'CNN_Segmentation'],
                        ['CNN_Segmentation', 'APPLIES_TO', 'Medical_Image_Segmentation'],
                        ['CNN_Segmentation', 'ACHIEVES', 'Dice_92.3%'],
                        ['CNN_Segmentation', 'EVALUATED_ON', 'BraTS_Dataset'],
                        ['CNN_Segmentation', 'REQUIRES_RESOURCE', 'GPU_16GB+'],
                      ].map(([s, p, o], i) => (
                        <tr key={i}><td className="px-3 py-1.5 font-mono">{s}</td><td className="px-3 py-1.5 font-mono text-primary">{p}</td><td className="px-3 py-1.5 font-mono">{o}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
              </Collapsible>
            </Section>

            {/* ── 9. MEKANISME PEMBEDA ── */}
            <Section id="pembeda" icon={GitBranch} title="Mekanisme Pembeda Semantik vs Logis" badge="BARU">
              <p className="text-sm text-muted-foreground mb-4">Menyelesaikan masalah: sistem tidak bisa bedakan "sering muncul bersama" (co-occurrence) vs "benar-benar berhubungan secara logis."</p>

              <div className="space-y-3 mb-4">
                {[
                  { name: 'Lapis 1 — Semantic Filtering', desc: 'Similarity > threshold? → Ya: lanjut / Tidak: buang', icon: '🔍' },
                  { name: 'Lapis 2 — Evidence Extraction', desc: 'Cari bukti eksplisit: penanda kausal ("causes", "leads to") & kontradiksi ("however", "contradicts")', icon: '📄' },
                  { name: 'Lapis 3 — Rule-Based Validation', desc: 'Cek terhadap aturan logika di Fact Base → VALID RELATION / REJECTED + alasan', icon: '⚖️' },
                ].map((layer, i) => (
                  <Card key={i} className="p-4 flex items-start gap-3">
                    <span className="text-xl">{layer.icon}</span>
                    <div>
                      <h4 className="text-sm font-medium">{layer.name}</h4>
                      <p className="text-xs text-muted-foreground mt-0.5">{layer.desc}</p>
                    </div>
                  </Card>
                ))}
              </div>
            </Section>

            {/* ── 10. BATASAN EPISTEMOLOGIS ── */}
            <Section id="batasan" icon={Ban} title="Batasan Epistemologis" badge="BARU">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <Card className="p-4 border-l-4 border-l-emerald-400">
                  <h3 className="text-sm font-semibold flex items-center gap-2 mb-3"><CheckCircle2 className="w-4 h-4 text-emerald-500" />Yang DAPAT Dilakukan</h3>
                  <ul className="space-y-2 text-xs text-muted-foreground">
                    <li>✅ Mendeteksi kesamaan topik antar-paper (Semantic similarity)</li>
                    <li>✅ Mendeteksi terminologi berbeda untuk konsep sama</li>
                    <li>✅ Mendeteksi klaim yang saling bertentangan (NLI + Rule Engine)</li>
                    <li>✅ Mengidentifikasi aspek absen dari paper</li>
                    <li>✅ Memvalidasi kelayakan logis rekomendasi</li>
                  </ul>
                </Card>
                <Card className="p-4 border-l-4 border-l-red-400">
                  <h3 className="text-sm font-semibold flex items-center gap-2 mb-3"><XCircle className="w-4 h-4 text-red-500" />Yang TIDAK DAPAT Dilakukan</h3>
                  <ul className="space-y-2 text-xs text-muted-foreground">
                    <li>❌ Menilai apakah kombinasi ide logis secara mendalam</li>
                    <li>❌ Memahami <em>mengapa</em> temuan saling bertentangan</li>
                    <li>❌ Menentukan apakah gap bermakna untuk dijadikan riset</li>
                    <li>❌ Melakukan penalaran induktif sejati</li>
                  </ul>
                </Card>
              </div>
              <Card className="p-4 bg-blue-50/50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900/50">
                <h4 className="text-sm font-semibold mb-1">Posisi Sistem</h4>
                <p className="text-sm text-muted-foreground">Sistem = <strong>alat bantu keputusan</strong> (decision support tool). Input: paper-paper. Output: <strong>indikator</strong> synthesis gap (bukan synthesis gap final). Peneliti manusia = pengambil keputusan akhir.</p>
              </Card>
            </Section>

            {/* ── 11. FRAMEWORK EVALUASI ── */}
            <Section id="evaluasi" icon={BarChart3} title="Revisi Framework Evaluasi">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <CompareBox label="❌ Lama" variant="old">
                  <p>Hanya mengukur Precision/Recall — seolah gap bisa dinilai benar/salah secara biner.</p>
                </CompareBox>
                <CompareBox label="✅ Baru — 7 Metrik Tambahan" variant="new">
                  <p>Evaluasi multi-dimensi + hipotesis + user study</p>
                </CompareBox>
              </div>

              <Card className="overflow-x-auto mb-4">
                <table className="w-full text-sm">
                  <thead><tr className="border-b bg-secondary/50"><th className="px-4 py-2 text-left">#</th><th className="px-4 py-2 text-left">Metrik</th><th className="px-4 py-2 text-left">Deskripsi</th></tr></thead>
                  <tbody className="divide-y">
                    {METRIK.map(m => (
                      <tr key={m.no}><td className="px-4 py-2 font-medium">{m.no}</td><td className="px-4 py-2 font-medium text-primary">{m.name}</td><td className="px-4 py-2 text-muted-foreground">{m.desc}</td></tr>
                    ))}
                  </tbody>
                </table>
              </Card>

              <Collapsible title="Hipotesis H4–H8">
                <div className="space-y-2 mt-3">
                  {[
                    { id: 'H4', claim: 'Expert acceptance rate ≥ 50%' },
                    { id: 'H5', claim: 'Logical coherence score ≥ 3.5/5' },
                    { id: 'H6', claim: 'Agentic system > Pipeline linear RAG+LLM (pada metrik acceptance rate)' },
                    { id: 'H7', claim: 'Dengan Rule Engine > Tanpa Rule Engine (mengurangi false discovery rate)' },
                    { id: 'H8', claim: 'Sistem mengurangi waktu identifikasi gap vs proses manual (user study)' },
                  ].map(h => (
                    <div key={h.id} className="flex items-start gap-2 text-sm">
                      <Badge variant="info">{h.id}</Badge>
                      <span>{h.claim}</span>
                    </div>
                  ))}
                </div>
              </Collapsible>
            </Section>

            {/* ── 12. STATUS IMPLEMENTASI ── */}
            <Section id="implementasi" icon={FileCheck} title="Status Implementasi">
              {/* Progress bar */}
              <Card className="p-4 mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">Progress Keseluruhan</span>
                  <span className="text-sm font-bold text-primary">{doneCount}/{totalCount} ({progress}%)</span>
                </div>
                <div className="w-full h-3 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${progress}%` }} />
                </div>
              </Card>

              <Card className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b bg-secondary/50">
                    <th className="px-4 py-2 text-left">Komponen</th>
                    <th className="px-4 py-2 text-left">File</th>
                    <th className="px-4 py-2 text-center">Status</th>
                  </tr></thead>
                  <tbody className="divide-y">
                    {IMPL_STATUS.map((item, i) => (
                      <tr key={i}>
                        <td className="px-4 py-2 font-medium">{item.komponen}</td>
                        <td className="px-4 py-2 text-xs font-mono text-muted-foreground">{item.file}</td>
                        <td className="px-4 py-2 text-center">
                          <div className="flex items-center justify-center gap-1.5">
                            <StatusIcon status={item.status} />
                            <span className="text-xs">
                              {item.status === 'done' ? 'Selesai' : item.status === 'partial' ? 'Parsial' : 'Belum'}
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </Section>

            {/* ── 13. RINGKASAN TABEL ── */}
            <Section id="ringkasan" icon={FileText} title="Ringkasan: Sebelum vs Sesudah">
              <Card className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b bg-secondary/50">
                    <th className="px-4 py-2 text-left w-8">#</th>
                    <th className="px-4 py-2 text-left">Aspek</th>
                    <th className="px-4 py-2 text-left">Sebelum</th>
                    <th className="px-4 py-2 text-left">Sesudah</th>
                  </tr></thead>
                  <tbody className="divide-y">
                    {RINGKASAN_TABEL.map((row, i) => (
                      <tr key={i}>
                        <td className="px-4 py-2 text-muted-foreground">{i + 1}</td>
                        <td className="px-4 py-2 font-medium">{row.aspek}</td>
                        <td className="px-4 py-2 text-red-600 dark:text-red-400 line-through text-xs">{row.sebelum}</td>
                        <td className="px-4 py-2 text-emerald-600 dark:text-emerald-400 text-xs font-medium">{row.sesudah}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </Section>

            {/* Footer */}
            <div className="text-xs text-muted-foreground border-t pt-4 pb-8">
              <p>Dokumen ini merangkum seluruh revisi proposal dari versi awal (v0) hingga final (v3.0).</p>
              <p className="mt-1">Sumber: revisi.md, REVISI_PROPOSAL.md, REVISI_PROPOSAL_OLD.md, drafts/PERBANDINGAN_REVISI.md, drafts/BAB_I_PENDAHULUAN.md–BAB_V_KESIMPULAN_DAN_SARAN.md, drafts/NOVELTY_STATEMENT.md, drafts/REVIEW_KONSISTENSI.md</p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default RevisionSummaryPage
