import { useState } from 'react'
import {
  Printer, ChevronDown, ChevronRight,
  CheckCircle2, User,
  MessageSquare, ArrowRight, GraduationCap
} from 'lucide-react'

/* ─── data ─── */
const COMMENTS = [
  {
    id: 1,
    date: '24 Des 2025',
    kategori: 'Target Pengguna',
    komentar: 'Saya tidak setuju pendapat pengusul bahwa ide ini untuk calon peneliti. Sebab calon peneliti harus belajar berpikir sebagaimana manusia akademisi. Saya hanya setuju ini gunakan oleh yang sudah memiliki expertise pada bidangnya.',
    severity: 'warning',
    aksi: [
      'Ubah posisi sistem dari "Sistem Otomatis" \u2192 "Decision Support Tool" untuk peneliti yang sudah expert',
      'Tambah BAB I \u00a71.5: Batasan Epistemologis \u2014 klaim yang TIDAK dibuat oleh sistem',
      'Tegaskan: sistem menghasilkan INDIKATOR, bukan kesimpulan final \u2014 manusia tetap pengambil keputusan',
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
      'TULIS ULANG TOTAL rumusan masalah \u2014 pola FENOMENA \u2192 KESENJANGAN \u2192 PERTANYAAN',
      'RQ1: "Sejauh mana pendekatan agentic mampu mendeteksi indikator synthesis gap?"',
      'RQ2: "Bagaimana mekanisme pembeda semantik-logis memengaruhi akurasi & FDR?"',
      'RQ3: "Apa batasan epistemologis pendekatan ini vs penalaran manusia?"',
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
      'GANTI definisi ke Cooper (1998) & Booth (2012): synthesis gap = literatur BELUM menghasilkan kesimpulan terpadu',
      'Operasionalisasikan jadi 3 indikator: Fragmentasi, Inkonsistensi, Ketidaklengkapan Kolektif',
      'Tegaskan yang BUKAN synthesis gap: \u274c Kombinasi metode-domain, \u274c Topik belum diteliti, \u274c Future work',
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
      'Tambah Batasan Epistemologis (BAB I \u00a71.5) \u2014 akui eksplisit LLM TIDAK mampu menalar induktif',
      'Tambah komponen Neuro-Symbolic: Rule Engine (deduktif) + KG Fact Base + Mekanisme Pembeda 3 lapis',
      'Klaim yang TIDAK dibuat: \u274c Tidak menggantikan review manusia, \u274c Tidak menalar induktif',
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
      'Geser kebaruan ke Neuro-Symbolic Agentic System \u2014 integrasi neural + simbolik',
      '4 pilar novelty: (1) Agentic Architecture, (2) Rule Engine, (3) Semantic-Logic Discriminator, (4) KG as Fact Base',
      'Ubah judul: "RAG dan LLM" \u2192 "Neuro-Symbolic Agentic untuk Deteksi Indikator Synthesis Gap"',
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
      'Tambah Mekanisme Pembeda 3 Lapis di BAB III:',
      'Lapis 1: Semantic Filtering \u2014 similarity > threshold',
      'Lapis 2: Evidence Extraction \u2014 cari penanda kausal ("causes", "leads to") & kontradiksi',
      'Lapis 3: Rule-Based Validation \u2014 cek aturan logika di Fact Base \u2192 VALID / REJECTED',
      'Tanpa penanda eksplisit \u2192 label "co-occurrence only", BUKAN hubungan logis',
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
      'Tambah Rule Engine: 9 aturan dalam 3 kategori',
      'Feasibility (F1-F3): kompatibilitas sumber daya, data, skala',
      'Causality (C1-C3): bukti kausal minimal, arah kausal, confounding',
      'Consistency (K1-K3): non-kontradiksi, konsistensi KG, transitivitas',
      '3 verdict: \u2705 PASS, \u26a0\ufe0f FLAG, \u274c REJECT',
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
      'TULIS ULANG diagram dari 3 tahap linear \u2192 4 Fase:',
      'F1: Ingestion \u2014 PDF \u2192 Chunk \u2192 Embed \u2192 Vector Store',
      'F2: Fact Extraction \u2014 Entity Extractor \u2192 Fact Table \u2192 Knowledge Graph',
      'F3: Agentic Analysis \u2014 Plan \u2192 Act \u2192 Observe \u2192 Reflect \u2192 Repeat/Stop',
      'F4: Logical Consistency Checker \u2014 Rule Engine \u2192 PASS / FLAG / REJECT',
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
      'Transformasi KG jadi Fact Base dengan ontologi eksplisit:',
      '8 tipe entitas: METHOD, CONCEPT, DOMAIN, FINDING, DATASET, METRIC, PAPER, CONSTRAINT',
      '12 predikat relasi: USES_METHOD, PROPOSES, APPLIES_TO, ACHIEVES, dll',
      'Proses: Entity Extraction (SciSpaCy+LLM) \u2192 Relation Extraction \u2192 Triple SPO \u2192 Validasi',
      'Contoh: (Paper_X, PROPOSES, CNN_Seg) \u2192 (CNN_Seg, ACHIEVES, Dice_92.3%)',
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
          @page { size: A4; margin: 18mm 15mm 18mm 20mm; }
          body { font-size: 10pt !important; }
          nav, .no-print { display: none !important; }
          .comment-card { page-break-inside: avoid; margin-bottom: 8pt; }
          .main-scroll { overflow: visible !important; height: auto !important; }
          .print-show { display: block !important; }
          .screen-only { display: none !important; }
        }
      `}</style>

      <div className="main-scroll min-h-[calc(100vh-3.5rem)] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-background/95 backdrop-blur border-b px-6 lg:px-10 py-4 no-print">
          <div className="flex items-center justify-between max-w-4xl mx-auto">
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-primary" />
                Catatan Revisi Proposal
              </h1>
              <p className="text-sm text-muted-foreground mt-0.5">Komentar Penguji \u2192 Aksi yang Dilakukan</p>
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
        <div className="hidden print:block px-6 py-4 mb-2 text-center">
          <h1 className="text-lg font-bold">CATATAN REVISI PROPOSAL TESIS</h1>
          <p className="text-sm">Andi Agung Dwi Arya B (D082251054) \u2014 Magister Teknik Informatika \u2014 UNHAS</p>
          <p className="text-xs text-gray-500 mt-0.5">Seminar: 24\u201325 Des 2025 \u00b7 Penguji: Prof. Dr. Adnan, ST., MT.</p>
        </div>

        <div className="max-w-4xl mx-auto px-6 lg:px-10 py-6">
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
              <span className="text-muted-foreground">\u00b7</span>
              <button onClick={collapseAll} className="text-xs text-primary hover:underline">Tutup semua</button>
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
                    <div className="border-t p-4 space-y-4 screen-only">
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
                      <div className="ml-10 border-l-2 border-emerald-300 dark:border-emerald-700 pl-4">
                        <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                          <ArrowRight className="w-3.5 h-3.5" />
                          Aksi yang dilakukan
                        </p>
                        <div className="space-y-1.5">
                          {item.aksi.map((a, i) => (
                            <div key={i} className="flex items-start gap-2 text-sm">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                              <span>{a}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Content - print (always visible) */}
                  <div className="hidden print-show border-t p-3 space-y-2">
                    <p className="text-sm">{item.komentar}</p>
                    {item.kutipan && <p className="text-xs italic text-red-700">Kutipan: {item.kutipan}</p>}
                    <div className="border-l-2 border-emerald-500 pl-3 mt-2">
                      <p className="text-xs font-bold mb-1">Aksi:</p>
                      {item.aksi.map((a, i) => (
                        <p key={i} className="text-xs">{'\u2713'} {a}</p>
                      ))}
                    </div>
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
