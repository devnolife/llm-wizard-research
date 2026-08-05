import { useState } from 'react'
import {
  BookOpen, ListChecks, GitCompareArrows, ShieldCheck, Flag, ChevronDown,
  FileText, Quote,
} from 'lucide-react'

// "Apa yang terjadi pada jurnal Anda?" — cerita proses berurutan dengan
// DETAIL NYATA per langkah (judul jurnal, fakta, bukti kutipan, verdict).
const ENTITY_LABELS = {
  METHOD: 'metode', DOMAIN: 'domain', CONCEPT: 'konsep',
  FINDING: 'temuan', DATASET: 'dataset', METRIC: 'metrik',
  PAPER: 'paper', CONSTRAINT: 'batasan',
}

const PREDICATE_LABELS = {
  APPLIES_TO: 'diterapkan pada', USES_METHOD: 'menggunakan metode',
  DISCUSSES: 'membahas', IMPROVES: 'meningkatkan', CONTRADICTS: 'bertentangan dengan',
  EXTENDS: 'memperluas', ACHIEVES: 'mencapai', PROPOSES: 'mengusulkan',
  REQUIRES_DATA: 'membutuhkan data', REQUIRES_RESOURCE: 'membutuhkan sumber daya',
  HAS_CONSTRAINT: 'memiliki batasan',
}

const GAP_LABELS = {
  FRAGMENTATION: 'fragmentasi',
  INCONSISTENCY: 'kontradiksi',
  INCOMPLETENESS: 'ketidaklengkapan',
}

const VERDICT_META = {
  PASS: { label: 'LOLOS', cls: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' },
  FLAG: { label: 'PERLU TINJAUAN', cls: 'bg-amber-500/10 text-amber-600 dark:text-amber-400' },
  REJECT: { label: 'DITOLAK', cls: 'bg-red-500/10 text-red-600 dark:text-red-400' },
}

const gapTypeOf = (ind) => String(ind.indicator_type || ind.type || ind.gap_type || '').toUpperCase()
const verdictOf = (ind) => {
  const v = String(ind.rule_engine_verdict || ind.verdict || '').toUpperCase()
  for (const key of Object.keys(VERDICT_META)) if (v.includes(key)) return key
  return null
}

const ProcessTrace = ({ data }) => {
  const [openStep, setOpenStep] = useState(null)
  if (!data) return null

  const papers = data.papers_info || (data.papers || []).map(t => ({ title: t }))
  const nPapers = papers.length || data.files_processed || 0
  const totalChunks = data.total_chunks || 0
  const stats = data.fact_table_stats || {}
  const nFacts = stats.total_facts || 0
  const nEntities = stats.total_entities || 0
  const entityBreakdown = Object.entries(stats.entities_by_type || {})
    .map(([type, count]) => `${count} ${ENTITY_LABELS[type] || type.toLowerCase()}`)
    .join(', ')
  const predicateRows = Object.entries(stats.facts_by_predicate || {})
    .sort((a, b) => b[1] - a[1])
  const indicators = data.gap_indicators || data.gaps || []
  const nCandidates = indicators.length
  const gapTypeCounts = {}
  for (const ind of indicators) {
    const t = gapTypeOf(ind)
    if (GAP_LABELS[t]) gapTypeCounts[t] = (gapTypeCounts[t] || 0) + 1
  }
  const gapSummary = Object.entries(gapTypeCounts)
    .map(([t, n]) => `${n} ${GAP_LABELS[t]}`)
    .join(', ')
  const rule = data.rule_engine_report || {}
  const recs = data.recommendations || []
  const primaryRec = recs.find(r => r.priority === 'high') || recs[0] || null

  if (!nPapers) return null

  const steps = [
    {
      icon: BookOpen,
      title: `${nPapers} jurnal Anda dibaca satu per satu`,
      desc: totalChunks
        ? `Isi PDF dipecah menjadi ${totalChunks} potongan teks supaya bisa dianalisis menyeluruh — bukan hanya abstrak.`
        : 'Isi PDF dipecah menjadi potongan teks kecil supaya bisa dianalisis menyeluruh.',
      how: 'Teks diambil per halaman, dipotong ±500 kata per bagian, lalu tiap potongan diubah menjadi angka (embedding) agar komputer bisa membandingkan makna antar jurnal.',
      detail: (
        <ul className="space-y-2">
          {papers.map((p, i) => (
            <li key={i} className="flex items-start gap-2.5 rounded-lg border bg-card p-2.5">
              <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary/70" />
              <div className="min-w-0 text-xs">
                <p className="font-medium text-foreground/90 leading-snug">{p.title || p.source}</p>
                <p className="mt-0.5 text-muted-foreground">
                  {[p.source, p.year && `tahun ${p.year}`,
                  Number.isFinite(Number(p.similarity_percent)) && `kemiripan antar-jurnal ${p.similarity_percent}%`]
                    .filter(Boolean).join(' · ')}
                </p>
              </div>
            </li>
          ))}
        </ul>
      ),
    },
    nFacts > 0 && {
      icon: ListChecks,
      title: `Dari isinya, sistem mencatat ${nFacts} fakta penting`,
      desc: `Sistem mengenali ${nEntities} hal (${entityBreakdown}) dan mencatat hubungannya sebagai fakta.`,
      how: 'Setiap kalimat penting diubah menjadi fakta 3 bagian: Subjek → Hubungan → Objek (contoh: "CRNN → diterapkan pada → pengenalan struk"). Kesimpulan apa pun bisa dilacak balik ke fakta ini — bukan karangan AI.',
      detail: predicateRows.length > 0 && (
        <div className="text-xs">
          <p className="mb-1.5 font-medium text-foreground/80">Jenis hubungan yang tercatat:</p>
          <ul className="space-y-1">
            {predicateRows.map(([pred, count]) => (
              <li key={pred} className="flex items-center justify-between rounded-md bg-card border px-2.5 py-1.5">
                <span className="text-foreground/85">"{PREDICATE_LABELS[pred] || pred.toLowerCase().replace(/_/g, ' ')}"</span>
                <span className="font-semibold text-primary">{count} fakta</span>
              </li>
            ))}
          </ul>
        </div>
      ),
    },
    {
      icon: GitCompareArrows,
      title: nCandidates > 0
        ? `Fakta antar-jurnal dibandingkan → ketemu ${nCandidates} calon gap`
        : 'Fakta antar-jurnal dibandingkan',
      desc: gapSummary
        ? `Jenisnya: ${gapSummary}. Ini baru CALON gap — belum tentu semuanya benar.`
        : 'Sistem mencari topik terpecah, temuan bertentangan, dan aspek yang belum dibahas.',
      how: 'Tiga pemeriksaan: (1) jurnal membahas hal sama tapi tak saling menyebut? (2) ada temuan bertabrakan? — dicek model AI khusus kontradiksi (NLI), (3) ada aspek penting yang kosong di semua jurnal?',
      detail: nCandidates > 0 && (
        <ul className="space-y-2">
          {indicators.map((ind, i) => {
            const t = gapTypeOf(ind)
            const quotes = (ind.supporting_quotes || []).slice(0, 2)
            return (
              <li key={i} className="rounded-lg border bg-card p-2.5 text-xs">
                <p className="font-medium text-foreground/90">
                  <span className="mr-1.5 rounded bg-secondary px-1.5 py-0.5 text-[10px] font-semibold uppercase">{GAP_LABELS[t] || t}</span>
                  {Number.isFinite(Number(ind.confidence)) && (
                    <span className="text-muted-foreground">keyakinan {(Number(ind.confidence) * 100).toFixed(0)}%</span>
                  )}
                </p>
                <p className="mt-1 text-foreground/80 leading-snug">{String(ind.description || '').slice(0, 220)}</p>
                {quotes.length > 0 && (
                  <div className="mt-1.5 space-y-1">
                    {quotes.map((q, qi) => (
                      <p key={qi} className="flex items-start gap-1.5 rounded bg-secondary/50 px-2 py-1 italic text-muted-foreground">
                        <Quote className="mt-0.5 h-3 w-3 shrink-0" />
                        <span>"{String(q.quote || '').slice(0, 160)}…"{q.source_paper ? ` — ${q.source_paper}` : ''}</span>
                      </p>
                    ))}
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      ),
    },
    (rule.total || 0) > 0 && {
      icon: ShieldCheck,
      title: 'Setiap calon gap diuji 9 aturan logika',
      desc: `Hasilnya: ${rule.passed ?? 0} lolos penuh, ${rule.flagged ?? 0} ditandai "perlu tinjauan", ${rule.rejected ?? 0} dibuang.`,
      how: 'Aturan ini bekerja TANPA AI — murni logika (kelayakan, sebab-akibat, konsistensi). Gap yang tidak masuk akal gugur di sini, jadi yang sampai ke Anda sudah tersaring.',
      detail: (
        <ul className="space-y-1.5">
          {indicators.map((ind, i) => {
            const v = verdictOf(ind)
            const meta = v ? VERDICT_META[v] : null
            if (!meta) return null
            return (
              <li key={i} className="flex items-center justify-between gap-2 rounded-md border bg-card px-2.5 py-1.5 text-xs">
                <span className="min-w-0 truncate text-foreground/85">
                  {GAP_LABELS[gapTypeOf(ind)] || 'gap'} — {String(ind.description || '').slice(0, 70)}…
                </span>
                <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${meta.cls}`}>{meta.label}</span>
              </li>
            )
          })}
        </ul>
      ),
    },
    {
      icon: Flag,
      title: primaryRec
        ? 'Gap terkuat dipilih, lalu disusun usulan penelitian'
        : 'Gap terkuat dipilih untuk ditampilkan',
      desc: 'Itulah yang Anda lihat di bawah. Semua berlabel "perlu validasi manusia" — keputusan tetap di tangan Anda dan pembimbing.',
      how: 'Gap diurutkan berdasarkan keyakinan setelah penyesuaian aturan. Usulan disusun menjawab gap tersebut, lengkap dengan alasan dan cara memulai.',
      detail: primaryRec && (
        <div className="rounded-lg border bg-card p-2.5 text-xs">
          <p className="font-medium text-foreground/90 leading-snug">{primaryRec.title}</p>
          {primaryRec.gap_type && (
            <p className="mt-1 text-muted-foreground">
              Menjawab gap: <strong>{GAP_LABELS[String(primaryRec.gap_type).toUpperCase()] || primaryRec.gap_type}</strong>
              {primaryRec.priority && <> · prioritas <strong>{primaryRec.priority === 'high' ? 'tinggi' : primaryRec.priority === 'medium' ? 'sedang' : 'rendah'}</strong></>}
            </p>
          )}
        </div>
      ),
    },
  ].filter(Boolean)

  return (
    <section className="rounded-2xl border bg-card/85 p-5">
      <h2 className="text-sm font-semibold mb-1">Apa yang terjadi pada jurnal Anda?</h2>
      <p className="text-xs text-muted-foreground mb-5">
        Urutan prosesnya dari awal sampai hasil — klik <em>"Lihat detail"</em> pada tiap langkah untuk bukti lengkapnya.
      </p>

      <ol className="relative">
        {steps.map((step, index) => {
          const Icon = step.icon
          const isLast = index === steps.length - 1
          const isOpen = openStep === index
          return (
            <li key={index} className="relative flex gap-3.5 pb-5 last:pb-0">
              {!isLast && (
                <span className="absolute left-[17px] top-9 bottom-0 w-px bg-border" aria-hidden="true" />
              )}
              <span className={`relative z-10 grid h-9 w-9 shrink-0 place-items-center rounded-full border-2 ${isLast ? 'border-primary bg-primary text-primary-foreground' : 'border-primary/30 bg-primary/10 text-primary'}`}>
                <Icon className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1 pt-1">
                <p className="text-sm font-semibold leading-snug">{step.title}</p>
                <p className="mt-1 text-sm text-muted-foreground leading-relaxed">{step.desc}</p>

                {(step.detail || step.how) && (
                  <button
                    type="button"
                    onClick={() => setOpenStep(isOpen ? null : index)}
                    aria-expanded={isOpen}
                    className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                  >
                    {isOpen ? 'Tutup detail' : 'Lihat detail'}
                    <ChevronDown className={`h-3 w-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                  </button>
                )}
                {isOpen && (
                  <div className="mt-2 space-y-2.5 rounded-xl border bg-secondary/30 p-3">
                    {step.how && (
                      <p className="text-xs leading-relaxed text-foreground/85">
                        <strong className="text-foreground">Cara kerja:</strong> {step.how}
                      </p>
                    )}
                    {step.detail}
                  </div>
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
