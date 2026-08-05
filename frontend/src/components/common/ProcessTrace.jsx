import { useState } from 'react'
import {
  BookOpen, ListChecks, GitCompareArrows, ShieldCheck, Flag, ChevronDown,
} from 'lucide-react'

// "Perjalanan jurnal Anda" — cerita berurutan: jurnal diapakan dulu,
// lalu apa, sampai jadi hasil di bawah. Semua angka diambil dari
// analisis NYATA pengguna (bukan teks statis).
const ENTITY_LABELS = {
  METHOD: 'metode', DOMAIN: 'domain', CONCEPT: 'konsep',
  FINDING: 'temuan', DATASET: 'dataset', METRIC: 'metrik',
  PAPER: 'paper', CONSTRAINT: 'batasan',
}

const GAP_LABELS = {
  FRAGMENTATION: 'fragmentasi',
  INCONSISTENCY: 'kontradiksi',
  INCOMPLETENESS: 'ketidaklengkapan',
}

const ProcessTrace = ({ data }) => {
  const [openStep, setOpenStep] = useState(null)
  if (!data) return null

  const papers = data.papers_info || (data.papers || []).map(t => ({ title: t }))
  const nPapers = papers.length || data.files_processed || 0
  const stats = data.fact_table_stats || {}
  const nFacts = stats.total_facts || 0
  const nEntities = stats.total_entities || 0
  const entityBreakdown = Object.entries(stats.entities_by_type || {})
    .map(([type, count]) => `${count} ${ENTITY_LABELS[type] || type.toLowerCase()}`)
    .join(', ')
  const indicators = data.gap_indicators || data.gaps || []
  const nCandidates = indicators.length
  const gapTypeCounts = {}
  for (const ind of indicators) {
    const t = String(ind.indicator_type || ind.type || ind.gap_type || '').toUpperCase()
    if (GAP_LABELS[t]) gapTypeCounts[t] = (gapTypeCounts[t] || 0) + 1
  }
  const gapSummary = Object.entries(gapTypeCounts)
    .map(([t, n]) => `${n} ${GAP_LABELS[t]}`)
    .join(', ')
  const rule = data.rule_engine_report || {}
  const nRecs = (data.recommendations || []).length

  if (!nPapers) return null

  const steps = [
    {
      icon: BookOpen,
      title: `${nPapers} jurnal Anda dibaca satu per satu`,
      desc: 'Setiap PDF dipecah menjadi potongan teks kecil supaya isinya bisa dianalisis menyeluruh — bukan hanya abstrak.',
      how: 'Teks diambil per halaman, dipotong menjadi bagian ±500 kata, lalu tiap potongan diubah menjadi angka (embedding) agar komputer bisa membandingkan maknanya.',
      detail: papers.map(p => p.title).filter(Boolean),
    },
    nFacts > 0 && {
      icon: ListChecks,
      title: `Dari isinya, sistem mencatat ${nFacts} fakta penting`,
      desc: `Sistem mengenali ${nEntities} hal (${entityBreakdown}) dan mencatat hubungannya sebagai fakta, contohnya: "metode A dipakai pada masalah B".`,
      how: 'Setiap kalimat penting diubah menjadi fakta 3 bagian: Subjek → Hubungan → Objek. Fakta yang tercatat inilah yang dibandingkan — jadi kesimpulan bisa dilacak balik ke jurnal, bukan karangan AI.',
    },
    {
      icon: GitCompareArrows,
      title: nCandidates > 0
        ? `Fakta antar-jurnal dibandingkan → ketemu ${nCandidates} calon gap`
        : 'Fakta antar-jurnal dibandingkan',
      desc: gapSummary
        ? `Jenisnya: ${gapSummary}. Ini baru CALON gap — belum tentu semuanya benar.`
        : 'Sistem mencari topik yang terpecah, temuan yang bertentangan, dan aspek yang belum dibahas siapa pun.',
      how: 'Tiga pemeriksaan berjalan: (1) apakah jurnal membahas hal sama tapi tidak saling menyebut? (2) apakah ada dua temuan yang bertabrakan? — dicek model AI khusus kontradiksi (NLI), (3) adakah aspek penting yang kosong di semua jurnal?',
    },
    (rule.total || 0) > 0 && {
      icon: ShieldCheck,
      title: `Setiap calon gap diuji 9 aturan logika`,
      desc: `Hasilnya: ${rule.passed ?? 0} lolos penuh, ${rule.flagged ?? 0} ditandai "perlu tinjauan", ${rule.rejected ?? 0} dibuang.`,
      how: 'Aturan ini bekerja TANPA AI — murni logika (kelayakan, sebab-akibat, konsistensi). Gap yang tidak masuk akal otomatis gugur di sini, jadi yang sampai ke Anda sudah tersaring.',
    },
    {
      icon: Flag,
      title: nRecs > 0
        ? 'Gap terkuat dipilih, lalu disusun usulan penelitian'
        : 'Gap terkuat dipilih untuk ditampilkan',
      desc: 'Itulah yang Anda lihat di bawah ini. Semua tetap berlabel "perlu validasi manusia" — sistem ini alat bantu, keputusan tetap di tangan Anda dan pembimbing.',
      how: 'Gap diurutkan berdasarkan tingkat keyakinan (confidence) setelah penyesuaian aturan. Usulan dibuat menjawab gap tersebut, lengkap dengan alasan dan cara memulai.',
    },
  ].filter(Boolean)

  return (
    <section className="rounded-2xl border bg-card/85 p-5">
      <h2 className="text-sm font-semibold mb-1">Apa yang terjadi pada jurnal Anda?</h2>
      <p className="text-xs text-muted-foreground mb-5">
        Urutan prosesnya dari awal sampai hasil — klik <em>"Bagaimana caranya?"</em> bila ingin tahu lebih dalam.
      </p>

      <ol className="relative">
        {steps.map((step, index) => {
          const Icon = step.icon
          const isLast = index === steps.length - 1
          const isOpen = openStep === index
          return (
            <li key={index} className="relative flex gap-3.5 pb-5 last:pb-0">
              {/* Garis penghubung vertikal */}
              {!isLast && (
                <span className="absolute left-[17px] top-9 bottom-0 w-px bg-border" aria-hidden="true" />
              )}
              <span className={`relative z-10 grid h-9 w-9 shrink-0 place-items-center rounded-full border-2 ${isLast ? 'border-primary bg-primary text-primary-foreground' : 'border-primary/30 bg-primary/10 text-primary'}`}>
                <Icon className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1 pt-1">
                <p className="text-sm font-semibold leading-snug">{step.title}</p>
                <p className="mt-1 text-sm text-muted-foreground leading-relaxed">{step.desc}</p>

                {step.detail?.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {step.detail.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-foreground/80">
                        <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-primary/60" />
                        {item}
                      </li>
                    ))}
                  </ul>
                )}

                <button
                  type="button"
                  onClick={() => setOpenStep(isOpen ? null : index)}
                  aria-expanded={isOpen}
                  className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                >
                  Bagaimana caranya?
                  <ChevronDown className={`h-3 w-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                </button>
                {isOpen && (
                  <p className="mt-2 rounded-lg border bg-secondary/40 p-3 text-xs leading-relaxed text-foreground/85">
                    {step.how}
                  </p>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}

export default ProcessTrace
