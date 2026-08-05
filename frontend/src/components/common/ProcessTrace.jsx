import { useState } from 'react'
import {
  BookOpen, ListChecks, GitCompareArrows, ShieldCheck, Sparkles,
  FileText, Quote, Eye, EyeOff, HelpCircle, FlaskConical, BarChart3, CornerDownRight,
} from 'lucide-react'
import StepVisual from './StepVisual'

// ═══════════════════════════════════════════════════════════════════
// LAPORAN PROSES LENGKAP — semua langkah TERBUKA PENUH secara default.
// Pola tetap per langkah:
//   ❓ Apa yang dilakukan  →  🔍 Contoh nyata dari jurnal Anda
//   →  📊 Hasil langkah ini  →  ➡ Kenapa penting (jembatan ke langkah berikut)
// Tombol "Sembunyikan penjelasan" untuk yang sudah paham.
// ═══════════════════════════════════════════════════════════════════

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
  FRAGMENTATION: 'Fragmentasi',
  INCONSISTENCY: 'Kontradiksi',
  INCOMPLETENESS: 'Ketidaklengkapan',
}

const GAP_EXPLAIN = {
  FRAGMENTATION: 'jurnal membahas hal yang sama tetapi tidak saling terhubung',
  INCONSISTENCY: 'dua jurnal menyatakan hal yang saling bertentangan',
  INCOMPLETENESS: 'ada aspek penting yang tidak dibahas jurnal mana pun',
}

const VERDICT_META = {
  PASS: { label: 'LOLOS', cls: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30' },
  FLAG: { label: 'PERLU TINJAUAN', cls: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30' },
  REJECT: { label: 'DITOLAK', cls: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30' },
}

const gapTypeOf = (ind) => String(ind.indicator_type || ind.type || ind.gap_type || '').toUpperCase()
const verdictOf = (ind) => {
  const v = String(ind.rule_engine_verdict || ind.verdict || '').toUpperCase()
  for (const key of Object.keys(VERDICT_META)) if (v.includes(key)) return key
  return null
}
const fmtTime = (ts) => {
  if (!ts) return null
  try { return new Date(ts).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) } catch { return null }
}

// ── Sub-blok dengan pola tetap ─────────────────────────────────────
const Blk = (props) => {
  const BlkIcon = props.icon
  return (
    <div className={`rounded-lg border p-3 ${props.tone || 'bg-card'}`}>
      <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
        <BlkIcon className="h-3.5 w-3.5" /> {props.label}
      </p>
      {props.children}
    </div>
  )
}

const ProcessTrace = ({ data, tail = [] }) => {
  const [showExplain, setShowExplain] = useState(true)
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
  const predicateRows = Object.entries(stats.facts_by_predicate || {}).sort((a, b) => b[1] - a[1])
  const topPredicate = predicateRows[0]
  const indicators = data.gap_indicators || data.gaps || []
  const nCandidates = indicators.length
  const rule = data.rule_engine_report || {}
  const trace = data.reasoning_trace || []
  const phaseTime = {}
  for (const step of trace) if (step.phase && step.timestamp) phaseTime[step.phase] = fmtTime(step.timestamp)
  const critiqueAction = trace.filter(s => s.phase === 'evaluate').flatMap(s => s.actions || [])
    .find(a => /score/i.test(a)) || null
  const critiqueScore = critiqueAction ? (critiqueAction.match(/([0-9.]+)/) || [])[1] : null

  // Contoh nyata: gap NLI dengan kutipan Paper A vs Paper B (bila ada)
  const nliGap = indicators.find(ind =>
    gapTypeOf(ind) === 'INCONSISTENCY' && (ind.supporting_quotes || []).length >= 2)
  const exampleQuoteA = nliGap?.supporting_quotes?.[0]
  const exampleQuoteB = nliGap?.supporting_quotes?.[1]

  if (!nPapers) return null

  const RULE_LIST = 'Kelayakan (3 aturan: sumber daya, data, skala) · Sebab-akibat (3 aturan: bukti minimal, arah, faktor perancu) · Konsistensi (3 aturan: non-kontradiksi internal, kecocokan fakta, transitivitas)'

  const steps = [
    // ── LANGKAH 1 ──────────────────────────────────────────────────
    {
      icon: BookOpen,
      time: phaseTime.observe,
      title: `Menerima & membaca ${nPapers} jurnal PDF`,
      visual: { kind: 'ingest', nPapers, nChunks: totalChunks },
      what: `Setiap PDF dibuka, teksnya diambil halaman demi halaman, lalu dipotong menjadi ${totalChunks || 'ratusan'} bagian kecil (±500 kata per bagian, disebut "potongan"). Setiap potongan diubah menjadi deretan angka (embedding) supaya komputer bisa MENGUKUR kemiripan makna antar potongan — bukan cuma mencocokkan kata.`,
      example: (
        <ul className="space-y-2">
          {papers.map((p, i) => (
            <li key={i} className="flex items-start gap-2.5 rounded-md border bg-card p-2.5">
              <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary/70" />
              <div className="min-w-0 text-xs">
                <p className="font-medium leading-snug text-foreground/90">{p.title || p.source}</p>
                <p className="mt-0.5 text-muted-foreground">
                  {[p.source, p.year && `tahun ${p.year}`,
                  Number.isFinite(Number(p.similarity_percent)) && `kemiripan dengan jurnal lain: ${p.similarity_percent}%`]
                    .filter(Boolean).join(' · ')}
                </p>
              </div>
            </li>
          ))}
        </ul>
      ),
      result: `${nPapers} jurnal terbaca utuh → ${totalChunks || '—'} potongan teks siap dianalisis.`,
      why: 'Tanpa dipecah kecil, komputer hanya bisa membaca "kesan umum". Dengan potongan kecil + embedding, setiap kalimat penting bisa ditemukan dan dibandingkan antar jurnal di langkah berikutnya.',
    },
    // ── LANGKAH 2 ──────────────────────────────────────────────────
    nFacts > 0 && {
      icon: ListChecks,
      time: phaseTime.observe,
      title: `Mencatat ${nFacts} fakta penting dari isi jurnal`,
      visual: { kind: 'facts', nFacts },
      what: `Dari potongan-potongan tadi, AI membaca kalimat demi kalimat dan mencatat klaim penting sebagai "fakta" 3 bagian: Subjek → Hubungan → Objek. Sistem mengenali ${nEntities} hal (${entityBreakdown}) lalu menghubungkannya.`,
      example: topPredicate && (
        <div className="space-y-2 text-xs">
          <p className="text-muted-foreground">Bentuk fakta yang dicatat dari jurnal Anda, misalnya:</p>
          <div className="flex flex-wrap items-center gap-1.5 rounded-md border bg-card p-2.5 font-medium">
            <span className="rounded bg-blue-500/10 px-2 py-1 text-blue-600 dark:text-blue-400">metode (mis. CRNN)</span>
            <CornerDownRight className="h-3 w-3 text-muted-foreground" />
            <span className="rounded bg-secondary px-2 py-1">"{PREDICATE_LABELS[topPredicate[0]] || topPredicate[0]}"</span>
            <CornerDownRight className="h-3 w-3 text-muted-foreground" />
            <span className="rounded bg-purple-500/10 px-2 py-1 text-purple-600 dark:text-purple-400">domain (mis. pengenalan struk)</span>
          </div>
          <p className="mb-1 mt-2 font-semibold text-foreground/80">Semua jenis hubungan yang tercatat:</p>
          <ul className="space-y-1">
            {predicateRows.map(([pred, count]) => (
              <li key={pred} className="flex items-center justify-between rounded-md border bg-card px-2.5 py-1.5">
                <span className="text-foreground/85">"{PREDICATE_LABELS[pred] || pred.toLowerCase().replace(/_/g, ' ')}"</span>
                <span className="font-semibold text-primary">{count} fakta</span>
              </li>
            ))}
          </ul>
        </div>
      ),
      result: `${nFacts} fakta + ${nEntities} konsep tersimpan dalam tabel fakta.`,
      why: 'Langkah 3 TIDAK membandingkan teks mentah — ia membandingkan fakta-fakta ini. Karena setiap fakta menunjuk kalimat asalnya, semua kesimpulan bisa dilacak balik ke jurnal (bukan karangan AI).',
    },
    // ── LANGKAH 3 ──────────────────────────────────────────────────
    {
      icon: GitCompareArrows,
      time: phaseTime.think,
      title: nCandidates > 0
        ? `Membandingkan fakta antar jurnal → ${nCandidates} calon gap ditemukan`
        : 'Membandingkan fakta antar jurnal',
      visual: { kind: 'compare', nGaps: nCandidates },
      what: 'Tiga pemeriksaan dijalankan sekaligus: (1) FRAGMENTASI — adakah jurnal yang membahas hal sama tapi tidak saling menyebut? (2) KONTRADIKSI — adakah dua temuan yang bertabrakan? Setiap pasangan klaim diuji model AI khusus bernama NLI yang tugasnya HANYA menilai "dua kalimat ini sejalan, netral, atau bertentangan?" (3) KETIDAKLENGKAPAN — aspek apa yang seharusnya dibahas tetapi kosong di SEMUA jurnal?',
      example: (
        <div className="space-y-2.5">
          {exampleQuoteA && exampleQuoteB && (
            <div className="rounded-md border border-amber-500/30 bg-amber-500/[0.05] p-2.5 text-xs">
              <p className="mb-2 font-semibold text-amber-700 dark:text-amber-400">
                Contoh nyata — dua kalimat dari jurnal BERBEDA yang dinilai bertentangan
                {Number.isFinite(Number(nliGap?.confidence)) && ` (keyakinan NLI ${(nliGap.confidence * 100).toFixed(0)}%)`}:
              </p>
              <div className="space-y-1.5">
                <p className="flex items-start gap-1.5 rounded bg-card px-2 py-1.5">
                  <Quote className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground" />
                  <span className="italic text-foreground/85">
                    Jurnal A: "{String(exampleQuoteA.quote || '').slice(0, 180)}…"
                  </span>
                </p>
                <p className="text-center text-[10px] font-bold uppercase tracking-widest text-amber-600 dark:text-amber-400">⚡ bertentangan dengan</p>
                <p className="flex items-start gap-1.5 rounded bg-card px-2 py-1.5">
                  <Quote className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground" />
                  <span className="italic text-foreground/85">
                    Jurnal B: "{String(exampleQuoteB.quote || '').slice(0, 180)}…"
                  </span>
                </p>
              </div>
            </div>
          )}
          {nCandidates > 0 && (
            <ul className="space-y-1.5 text-xs">
              {indicators.map((ind, i) => {
                const t = gapTypeOf(ind)
                return (
                  <li key={i} className="rounded-md border bg-card p-2.5">
                    <p className="font-semibold text-foreground/90">
                      Calon gap {i + 1}: {GAP_LABELS[t] || t}
                      {Number.isFinite(Number(ind.confidence)) && (
                        <span className="ml-1.5 font-normal text-muted-foreground">· keyakinan awal {(Number(ind.confidence) * 100).toFixed(0)}%</span>
                      )}
                    </p>
                    <p className="mt-0.5 text-muted-foreground">({GAP_EXPLAIN[t] || ''})</p>
                    <p className="mt-1 leading-snug text-foreground/80">{String(ind.description || '').slice(0, 200)}</p>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      ),
      result: `${nCandidates} calon gap: ${Object.entries(indicators.reduce((acc, ind) => { const t = gapTypeOf(ind); if (GAP_LABELS[t]) acc[t] = (acc[t] || 0) + 1; return acc }, {})).map(([t, n]) => `${n} ${GAP_LABELS[t].toLowerCase()}`).join(', ') || '—'}.`,
      why: 'Ini baru CALON — AI bisa salah. Karena itu semuanya wajib melewati pemeriksaan logika di langkah berikutnya sebelum boleh tampil sebagai hasil.',
    },
    // ── LANGKAH 4 ──────────────────────────────────────────────────
    (rule.total || 0) > 0 && {
      icon: ShieldCheck,
      time: phaseTime.act,
      title: `Menguji ${rule.total} calon gap dengan 9 aturan logika`,
      visual: { kind: 'rules', passed: rule.passed ?? 0, flagged: rule.flagged ?? 0, rejected: rule.rejected ?? 0 },
      what: `Setiap calon gap diperiksa Rule Engine — pemeriksa yang bekerja TANPA AI, murni logika. 9 aturannya: ${RULE_LIST}. Gap yang melanggar aturan keras DITOLAK; yang kurang bukti DITANDAI "perlu tinjauan" dan keyakinannya dipotong.`,
      example: (
        <ul className="space-y-1.5 text-xs">
          {indicators.map((ind, i) => {
            const v = verdictOf(ind)
            const meta = v ? VERDICT_META[v] : null
            if (!meta) return null
            const conf = Number(ind.confidence)
            const adj = Number(ind.adjusted_confidence)
            const cut = Number.isFinite(conf) && Number.isFinite(adj) && adj < conf
            return (
              <li key={i} className={`rounded-md border p-2.5 ${meta.cls}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold">Calon gap {i + 1} ({GAP_LABELS[gapTypeOf(ind)] || 'gap'})</span>
                  <span className="shrink-0 rounded-full border bg-card px-2 py-0.5 text-[10px] font-bold">{meta.label}</span>
                </div>
                {cut && (
                  <p className="mt-1 text-[11px]">
                    Keyakinan dipotong: {(conf * 100).toFixed(0)}% → {(adj * 100).toFixed(0)}% (penalti karena bukti belum lengkap)
                  </p>
                )}
              </li>
            )
          })}
        </ul>
      ),
      result: `${rule.passed ?? 0} lolos penuh · ${rule.flagged ?? 0} ditandai "perlu tinjauan" · ${rule.rejected ?? 0} dibuang.`,
      why: 'Inilah pembeda sistem ini dari sekadar bertanya ke ChatGPT: ada penyaring logika independen yang menghukum klaim tanpa bukti, sehingga gap yang sampai ke Anda sudah teruji dua kali (AI + logika).',
    },
    // ── LANGKAH 5 ──────────────────────────────────────────────────
    critiqueScore && {
      icon: Sparkles,
      time: phaseTime.evaluate,
      title: `Sistem menilai pekerjaannya sendiri: skor ${critiqueScore}`,
      visual: { kind: 'score', score: critiqueScore },
      what: 'Sebelum menampilkan apa pun, sistem mengevaluasi hasilnya sendiri: apakah bukti cukup? apakah gap konsisten dengan fakta yang dicatat? apakah rekomendasi menjawab gap? Skor di bawah ambang akan memicu analisis ulang otomatis.',
      example: (
        <div className="rounded-md border bg-card p-2.5 text-xs">
          <p className="font-medium text-foreground/90">Skor kritik-diri: <strong>{critiqueScore}</strong> dari 1.00 → di atas ambang, tidak perlu revisi.</p>
          <p className="mt-1 text-muted-foreground">Dinilai dari: kelengkapan hasil, dukungan bukti, konsistensi antar bagian, dan kepatuhan aturan.</p>
        </div>
      ),
      result: 'Hasil dinyatakan layak tampil — dengan catatan tetap perlu validasi manusia.',
      why: 'Skor ini jujur mengakui batas sistem: 0.80 artinya "cukup baik untuk jadi bahan pertimbangan", bukan "pasti benar". Keputusan akhir tetap milik Anda dan pembimbing.',
    },
  ].filter(Boolean)

  return (
    <section className="rounded-2xl border bg-card/85 p-5">
      <div className="mb-1 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">Laporan proses lengkap — dari PDF masuk sampai gap ditemukan</h2>
        <button
          type="button"
          onClick={() => setShowExplain(v => !v)}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground hover:bg-secondary"
        >
          {showExplain ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
          {showExplain ? 'Sembunyikan penjelasan' : 'Tampilkan penjelasan'}
        </button>
      </div>
      <p className="mb-6 text-xs text-muted-foreground">
        Setiap langkah dijelaskan lengkap: apa yang dilakukan, contoh nyata dari jurnal Anda, hasilnya, dan kenapa langkah itu penting.
      </p>

      <ol className="relative">
        {steps.map((step, index) => {
          const Icon = step.icon
          return (
            <li key={index} className="relative flex gap-3.5 pb-7 last:pb-7">
              <span className="absolute left-[17px] top-9 bottom-0 w-px bg-border" aria-hidden="true" />
              <span className="relative z-10 grid h-9 w-9 shrink-0 place-items-center rounded-full border-2 border-primary/30 bg-primary/10 text-primary">
                <Icon className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1 pt-0.5">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-primary">
                    Langkah {index + 1} dari {steps.length}
                  </p>
                  {step.time && <span className="text-[10px] text-muted-foreground">⏱ {step.time}</span>}
                </div>
                <p className="mt-0.5 text-sm font-semibold leading-snug">{step.title}</p>

                <div className="mt-2.5 space-y-2.5">
                  {step.visual && <StepVisual {...step.visual} />}
                  {showExplain && step.what && (
                    <Blk icon={HelpCircle} label="Apa yang dilakukan">
                      <p className="text-xs leading-relaxed text-foreground/85">{step.what}</p>
                    </Blk>
                  )}
                  {step.example && (
                    <Blk icon={FlaskConical} label="Contoh nyata dari jurnal Anda" tone="bg-secondary/30">
                      {step.example}
                    </Blk>
                  )}
                  {step.result && (
                    <Blk icon={BarChart3} label="Hasil langkah ini" tone="bg-primary/[0.04]">
                      <p className="text-xs font-medium text-foreground/90">{step.result}</p>
                    </Blk>
                  )}
                  {showExplain && step.why && (
                    <p className="flex items-start gap-1.5 pl-1 text-xs leading-relaxed text-muted-foreground">
                      <CornerDownRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary/60" />
                      <span><strong className="text-foreground/80">Kenapa penting:</strong> {step.why}</span>
                    </p>
                  )}
                </div>
              </div>
            </li>
          )
        })}

        {/* ── HASIL AKHIR — menyambung di timeline yang sama ── */}
        {tail.map((item, index) => {
          const Icon = item.icon
          const isLast = index === tail.length - 1
          return (
            <li key={`tail-${index}`} className="relative flex gap-3.5 pb-7 last:pb-0">
              {!isLast && (
                <span className="absolute left-[17px] top-9 bottom-0 w-px bg-border" aria-hidden="true" />
              )}
              <span className={`relative z-10 grid h-9 w-9 shrink-0 place-items-center rounded-full border-2 ${item.highlight
                ? 'border-amber-500 bg-amber-500 text-white'
                : 'border-primary bg-primary text-primary-foreground'}`}>
                <Icon className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1 pt-0.5">
                <p className={`mb-1.5 text-[11px] font-bold uppercase tracking-[0.14em] ${item.highlight ? 'text-amber-600 dark:text-amber-400' : 'text-primary'}`}>
                  {item.label}
                </p>
                {item.content}
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}

export default ProcessTrace
