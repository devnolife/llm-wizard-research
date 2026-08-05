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
    <div className={`rounded-xl border border-border/60 p-3.5 shadow-sm transition-shadow hover:shadow-md ${props.tone || 'bg-card/80 backdrop-blur-sm'}`}>
      <p className="mb-2 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
        <BlkIcon className="h-3.5 w-3.5" /> {props.label}
      </p>
      {props.children}
    </div>
  )
}

// Aksen warna per langkah agar tiap fase mudah dikenali
const STEP_ACCENTS = [
  { ring: 'ring-sky-500/25', bg: 'bg-sky-500/10', text: 'text-sky-600 dark:text-sky-400', dot: 'bg-sky-500' },
  { ring: 'ring-violet-500/25', bg: 'bg-violet-500/10', text: 'text-violet-600 dark:text-violet-400', dot: 'bg-violet-500' },
  { ring: 'ring-amber-500/25', bg: 'bg-amber-500/10', text: 'text-amber-600 dark:text-amber-400', dot: 'bg-amber-500' },
  { ring: 'ring-emerald-500/25', bg: 'bg-emerald-500/10', text: 'text-emerald-600 dark:text-emerald-400', dot: 'bg-emerald-500' },
  { ring: 'ring-fuchsia-500/25', bg: 'bg-fuchsia-500/10', text: 'text-fuchsia-600 dark:text-fuchsia-400', dot: 'bg-fuchsia-500' },
]

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
  const sampleFacts = data.sample_facts || []
  const llmModel = data.llm_info?.model || ''
  const phaseTime = {}
  for (const step of trace) if (step.phase && step.timestamp) phaseTime[step.phase] = fmtTime(step.timestamp)
  const critiqueAction = trace.filter(s => s.phase === 'evaluate').flatMap(s => s.actions || [])
    .find(a => /score/i.test(a)) || null
  const critiqueScore = critiqueAction ? (critiqueAction.match(/([0-9.]+)/) || [])[1] : null
  const evaluateActions = trace.filter(s => s.phase === 'evaluate')
    .flatMap(s => s.actions || []).filter(a => typeof a === 'string').slice(0, 5)

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
        <ul className="space-y-3">
          {papers.map((p, i) => (
            <li key={i} className="rounded-md border bg-card p-2.5">
              <div className="flex items-start gap-2.5">
                <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary/70" />
                <div className="min-w-0 text-xs">
                  <p className="font-medium leading-snug text-foreground/90">{p.title || p.source}</p>
                  <p className="mt-0.5 text-muted-foreground">
                    {[p.source, p.year && `tahun ${p.year}`,
                    Number.isFinite(Number(p.num_chunks)) && `dipotong menjadi ${p.num_chunks} bagian`,
                    Number.isFinite(Number(p.similarity_percent)) && `kemiripan dengan jurnal lain: ${p.similarity_percent}%`]
                      .filter(Boolean).join(' · ')}
                  </p>
                </div>
              </div>
              {/* Isi dokumen ASLI, terlihat digunting menjadi potongan bernomor */}
              {(p.sample_chunks || []).length > 0 && (
                <div className="mt-2 space-y-0">
                  {p.sample_chunks.map((chunk, ci) => (
                    <div key={ci}>
                      {ci > 0 && (
                        <div className="my-1 flex items-center gap-2 pl-1" aria-hidden="true">
                          <span className="text-[10px]">✂️</span>
                          <span className="flex-1 border-t border-dashed border-primary/40" />
                          <span className="text-[9px] font-semibold uppercase tracking-wide text-primary/60">dipotong di sini</span>
                          <span className="flex-1 border-t border-dashed border-primary/40" />
                        </div>
                      )}
                      <div className="rounded-md border border-blue-400/30 bg-blue-500/[0.05] px-2.5 py-2">
                        <p className="mb-1 text-[9px] font-bold uppercase tracking-wide text-blue-600 dark:text-blue-400">
                          Potongan #{(chunk.chunk_index ?? ci) + 1}
                          {chunk.section ? ` · bagian: ${chunk.section}` : ''}
                        </p>
                        <p className="font-serif text-[11px] leading-relaxed text-foreground/80">
                          "{chunk.text}…"
                        </p>
                      </div>
                    </div>
                  ))}
                  {Number.isFinite(Number(p.num_chunks)) && p.num_chunks > (p.sample_chunks?.length || 0) && (
                    <p className="mt-1.5 pl-1 text-[10px] text-muted-foreground">
                      …dan {p.num_chunks - p.sample_chunks.length} potongan lainnya dari jurnal ini.
                    </p>
                  )}
                </div>
              )}
            </li>
          ))}
          {!papers.some(p => (p.sample_chunks || []).length > 0) && (
            <li className="rounded-md border border-dashed bg-secondary/30 p-2.5 text-[11px] text-muted-foreground">
              Cuplikan isi dokumen tersedia untuk analisis yang dijalankan setelah pembaruan ini — unggah ulang untuk melihat isi potongan.
            </li>
          )}
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
      what: `Potongan-potongan tadi dikirim ke AI (model ${llmModel || 'bahasa lokal'}) dengan perintah: "baca teks ini, keluarkan klaim penting sebagai fakta 3 bagian Subjek → Hubungan → Objek". AI menjawab dalam format terstruktur, lalu sistem memeriksa & menyimpannya ke tabel fakta. Total ${nEntities} hal dikenali (${entityBreakdown}).`,
      example: (
        <div className="space-y-2 text-xs">
          {sampleFacts.length > 0 ? (
            <>
              <p className="text-muted-foreground">
                Fakta ASLI yang dicatat AI dari jurnal Anda (bukan contoh karangan):
              </p>
              <ul className="space-y-1.5">
                {sampleFacts.map((f, i) => (
                  <li key={i} className="rounded-md border bg-card p-2">
                    <div className="flex flex-wrap items-center gap-1.5 font-medium">
                      <span className="rounded bg-blue-500/10 px-2 py-0.5 text-blue-600 dark:text-blue-400" title={ENTITY_LABELS[f.subject_type] || f.subject_type}>{f.subject}</span>
                      <CornerDownRight className="h-3 w-3 text-muted-foreground" />
                      <span className="rounded bg-secondary px-2 py-0.5">"{PREDICATE_LABELS[f.predicate] || f.predicate}"</span>
                      <CornerDownRight className="h-3 w-3 text-muted-foreground" />
                      <span className="rounded bg-purple-500/10 px-2 py-0.5 text-purple-600 dark:text-purple-400" title={ENTITY_LABELS[f.object_type] || f.object_type}>{f.object}</span>
                    </div>
                    <p className="mt-1 text-[10px] text-muted-foreground">
                      {[f.source_paper && `dari: ${f.source_paper}`,
                      Number.isFinite(Number(f.confidence)) && `keyakinan ${(f.confidence * 100).toFixed(0)}%`]
                        .filter(Boolean).join(' · ')}
                    </p>
                  </li>
                ))}
              </ul>
            </>
          ) : topPredicate && (
            <>
              <p className="text-muted-foreground">Bentuk fakta yang dicatat dari jurnal Anda, misalnya:</p>
              <div className="flex flex-wrap items-center gap-1.5 rounded-md border bg-card p-2.5 font-medium">
                <span className="rounded bg-blue-500/10 px-2 py-1 text-blue-600 dark:text-blue-400">metode (mis. CRNN)</span>
                <CornerDownRight className="h-3 w-3 text-muted-foreground" />
                <span className="rounded bg-secondary px-2 py-1">"{PREDICATE_LABELS[topPredicate[0]] || topPredicate[0]}"</span>
                <CornerDownRight className="h-3 w-3 text-muted-foreground" />
                <span className="rounded bg-purple-500/10 px-2 py-1 text-purple-600 dark:text-purple-400">domain (mis. pengenalan struk)</span>
              </div>
            </>
          )}
          {predicateRows.length > 0 && (
            <>
              <p className="mb-1 mt-2 font-semibold text-foreground/80">Rekap semua jenis hubungan yang tercatat:</p>
              <ul className="space-y-1">
                {predicateRows.map(([pred, count]) => (
                  <li key={pred} className="flex items-center justify-between rounded-md border bg-card px-2.5 py-1.5">
                    <span className="text-foreground/85">"{PREDICATE_LABELS[pred] || pred.toLowerCase().replace(/_/g, ' ')}"</span>
                    <span className="font-semibold text-primary">{count} fakta</span>
                  </li>
                ))}
              </ul>
            </>
          )}
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
                const evidence = (ind.evidence || []).filter(e => typeof e === 'string')
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
                    {evidence.length > 0 && (
                      <details className="mt-1.5">
                        <summary className="cursor-pointer text-[11px] font-medium text-primary hover:underline">
                          Bukti yang dipakai sistem ({evidence.length})
                        </summary>
                        <ul className="mt-1 space-y-1">
                          {evidence.map((e, ei) => (
                            <li key={ei} className="rounded bg-secondary/50 px-2 py-1 text-[11px] leading-snug text-muted-foreground">
                              {String(e).slice(0, 260)}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
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
        <div className="space-y-2.5">
          <div className="text-[11px]">
            <p className="mb-1 font-semibold text-foreground/80">9 aturan yang dipakai (tanpa AI, murni logika):</p>
            <div className="flex flex-wrap gap-1">
              {[
                ['F1 Sumber daya', 'blue'], ['F2 Ketersediaan data', 'blue'], ['F3 Skala riset', 'blue'],
                ['C1 Bukti minimal', 'amber'], ['C2 Arah sebab-akibat', 'amber'], ['C3 Faktor perancu', 'amber'],
                ['K1 Non-kontradiksi', 'purple'], ['K2 Kecocokan fakta', 'purple'], ['K3 Transitivitas', 'purple'],
              ].map(([label, c]) => (
                <span key={label} className={`rounded-full border px-2 py-0.5 font-medium ${c === 'blue' ? 'border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400'
                  : c === 'amber' ? 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400'
                    : 'border-purple-500/30 bg-purple-500/10 text-purple-600 dark:text-purple-400'}`}>
                  {label}
                </span>
              ))}
            </div>
            <p className="mt-1 text-muted-foreground">Biru = kelayakan · Kuning = sebab-akibat · Ungu = konsistensi</p>
          </div>
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
        </div>
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
        <div className="space-y-2 text-xs">
          <div className="rounded-md border bg-card p-2.5">
            <p className="font-medium text-foreground/90">Skor kritik-diri: <strong>{critiqueScore}</strong> dari 1.00 → di atas ambang, tidak perlu revisi.</p>
            <p className="mt-1 text-muted-foreground">Dinilai dari: kelengkapan hasil, dukungan bukti, konsistensi antar bagian, dan kepatuhan aturan.</p>
          </div>
          {evaluateActions.length > 0 && (
            <div className="rounded-md border bg-card p-2.5">
              <p className="mb-1 font-semibold text-foreground/80">Catatan asli dari sistem (tahap evaluasi):</p>
              <ul className="space-y-1">
                {evaluateActions.map((a, i) => (
                  <li key={i} className="rounded bg-secondary/50 px-2 py-1 font-mono text-[11px] text-muted-foreground">{a}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="rounded-md border bg-card p-2.5 text-[11px] text-muted-foreground">
            <p className="mb-1 font-semibold text-foreground/80">Siklus kerja agen (OTAE) yang baru saja selesai:</p>
            <p className="font-medium">
              👁 Amati (baca PDF & catat fakta) → 🧠 Pikir (bandingkan antar jurnal) → ⚙️ Aksi (uji aturan & susun hasil) → ✅ Evaluasi (nilai diri sendiri) — kalau skor rendah, siklus diulang.
            </p>
          </div>
        </div>
      ),
      result: 'Hasil dinyatakan layak tampil — dengan catatan tetap perlu validasi manusia.',
      why: 'Skor ini jujur mengakui batas sistem: 0.80 artinya "cukup baik untuk jadi bahan pertimbangan", bukan "pasti benar". Keputusan akhir tetap milik Anda dan pembimbing.',
    },
  ].filter(Boolean)

  return (
    <section className="overflow-hidden rounded-2xl border bg-gradient-to-b from-card to-card/60 shadow-sm">
      {/* ── Header modern ── */}
      <div className="border-b bg-gradient-to-r from-primary/[0.07] via-transparent to-violet-500/[0.06] px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold tracking-tight">Laporan proses lengkap</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">Dari PDF masuk sampai gap ditemukan — setiap langkah transparan & bisa dilacak.</p>
          </div>
          <button
            type="button"
            onClick={() => setShowExplain(v => !v)}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-full border bg-card/80 px-3 py-1.5 text-xs font-medium text-muted-foreground shadow-sm transition-all hover:text-foreground hover:shadow"
          >
            {showExplain ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            {showExplain ? 'Sembunyikan penjelasan' : 'Tampilkan penjelasan'}
          </button>
        </div>
        {/* Ringkasan langkah sebagai pill navigasi visual */}
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {steps.map((s, i) => {
            const a = STEP_ACCENTS[i % STEP_ACCENTS.length]
            return (
              <span key={i} className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold ${a.bg} ${a.text}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${a.dot}`} />
                {i + 1}. {String(s.title).split('—')[0].split(':')[0].slice(0, 34)}
              </span>
            )
          })}
        </div>
      </div>

      <div className="p-5">
        <ol className="relative">
          {steps.map((step, index) => {
            const Icon = step.icon
            const a = STEP_ACCENTS[index % STEP_ACCENTS.length]
            return (
              <li key={index} className="relative flex gap-4 pb-8 last:pb-8">
                <span className="absolute left-[19px] top-10 bottom-0 w-px bg-gradient-to-b from-border via-border to-transparent" aria-hidden="true" />
                <span className={`relative z-10 grid h-10 w-10 shrink-0 place-items-center rounded-2xl ring-4 ${a.ring} ${a.bg} ${a.text} shadow-sm`}>
                  <Icon className="h-[18px] w-[18px]" />
                </span>
                <div className="min-w-0 flex-1 pt-0.5">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                    <p className={`text-[11px] font-bold uppercase tracking-[0.14em] ${a.text}`}>
                      Langkah {index + 1} dari {steps.length}
                    </p>
                    {step.time && (
                      <span className="rounded-full bg-secondary/70 px-2 py-0.5 text-[10px] font-medium text-muted-foreground">⏱ {step.time}</span>
                    )}
                  </div>
                  <p className="mt-1 text-[15px] font-semibold leading-snug tracking-tight">{step.title}</p>

                  <div className="mt-3 space-y-2.5">
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
              <li key={`tail-${index}`} className="relative flex gap-4 pb-8 last:pb-0">
                {!isLast && (
                  <span className="absolute left-[19px] top-10 bottom-0 w-px bg-gradient-to-b from-border to-transparent" aria-hidden="true" />
                )}
                <span className={`relative z-10 grid h-10 w-10 shrink-0 place-items-center rounded-2xl shadow-md ${item.highlight
                  ? 'bg-gradient-to-br from-amber-400 to-amber-600 text-white ring-4 ring-amber-500/25'
                  : 'bg-gradient-to-br from-primary to-primary/70 text-primary-foreground ring-4 ring-primary/20'}`}>
                  <Icon className="h-[18px] w-[18px]" />
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
      </div>
    </section>
  )
}

export default ProcessTrace
