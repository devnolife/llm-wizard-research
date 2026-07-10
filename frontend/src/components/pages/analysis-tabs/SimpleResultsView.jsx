import {
  ArrowRight, BookOpen, CheckCircle, FileText, Lightbulb, Search, Shield,
} from 'lucide-react'
import Markdown from '../../common/Markdown'
import { GAP_COLORS } from './constants'

// Default result view: one clear research path, not every available metric.
const SimpleResultsView = ({ simpleData: sd, data, onShowFull, onFindSources }) => {
  const papers = sd?.papersInfo || []
  const primaryGap = sd?.primaryGap
  const primaryRec = sd?.primaryRec
  const gapType = primaryGap?.type || primaryGap?.gap_type
  const gapMeta = GAP_COLORS[gapType]
  const suggestedQuery = primaryRec?.title || primaryGap?.title || data?.topics?.[0] || ''

  const steps = [
    { number: '01', label: 'Jurnal Anda', icon: FileText, complete: papers.length > 0 },
    { number: '02', label: 'Gap utama', icon: Search, complete: Boolean(primaryGap) },
    { number: '03', label: 'Arah solusi', icon: Lightbulb, complete: Boolean(primaryRec) },
    { number: '04', label: 'Jurnal pendukung', icon: BookOpen, complete: false },
  ]

  return (
    <div className="w-full px-6 lg:px-10 py-8 max-w-3xl mx-auto">
      <header className="mb-7">
        <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 mb-3">
          <CheckCircle className="w-5 h-5" />
          <span className="text-sm font-semibold">Analisis selesai</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Ikuti hasilnya, satu langkah demi satu.</h1>
        <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
          Mulai dari jurnal Anda, pahami gap utamanya, pilih arah solusi, lalu cari jurnal yang dapat memperkuat solusi tersebut.
        </p>
      </header>

      <ol className="flex items-center gap-1.5 mb-8 overflow-x-auto pb-1" aria-label="Kemajuan alur penelitian">
        {steps.map((step, index) => {
          const StepIcon = step.icon
          return (
            <li key={step.number} className="flex items-center gap-1.5 shrink-0">
              <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium ${step.complete ? 'border-primary/30 bg-primary/10 text-primary' : 'border-border bg-card text-muted-foreground'}`}>
                <StepIcon className="w-3.5 h-3.5" /> {step.number} · {step.label}
              </span>
              {index < steps.length - 1 && <ArrowRight className="w-3.5 h-3.5 text-muted-foreground/60" aria-hidden="true" />}
            </li>
          )
        })}
      </ol>

      <div className="space-y-4">
        <section className="rounded-2xl border bg-card/85 p-5">
          <div className="flex items-start gap-3">
            <span className="grid h-8 w-8 place-items-center rounded-xl bg-primary/10 text-primary text-sm font-bold shrink-0">1</span>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Jurnal yang dibaca</p>
              <h2 className="font-semibold mt-1">{papers.length || data?.files_processed || 0} jurnal menjadi dasar analisis</h2>
              <p className="text-sm text-muted-foreground mt-1">Sistem hanya memakai jurnal pada analisis ini.</p>
              {papers.length > 0 && (
                <details className="mt-3 group">
                  <summary className="cursor-pointer text-sm font-medium text-primary hover:underline">Lihat daftar jurnal</summary>
                  <ol className="mt-3 space-y-2 border-l border-border pl-3">
                    {papers.map((paper, index) => (
                      <li key={`${paper.title}-${index}`} className="text-sm text-muted-foreground leading-snug">{paper.title}</li>
                    ))}
                  </ol>
                </details>
              )}
            </div>
          </div>
        </section>

        <section className={`rounded-2xl border bg-card/85 p-5 border-l-4 ${gapMeta?.border || 'border-l-amber-500'}`}>
          <div className="flex items-start gap-3">
            <span className={`grid h-8 w-8 place-items-center rounded-xl text-sm font-bold shrink-0 ${gapMeta?.bg || 'bg-amber-500/10'} ${gapMeta?.text || 'text-amber-600 dark:text-amber-400'}`}>2</span>
            <div className="min-w-0 flex-1">
              <p className={`text-xs font-semibold uppercase tracking-[0.14em] ${gapMeta?.text || 'text-amber-600 dark:text-amber-400'}`}>Gap yang perlu dijawab</p>
              {primaryGap ? (
                <>
                  <h2 className="font-semibold mt-1">{primaryGap.title || 'Celah penelitian utama'}</h2>
                  <Markdown content={primaryGap.description || 'Sistem menemukan area yang masih perlu disatukan, diuji kembali, atau dilengkapi.'} className="mt-2 text-sm text-muted-foreground" />
                  {gapMeta && <p className="mt-3 text-xs text-muted-foreground">Jenis gap: <strong className={gapMeta.text}>{gapMeta.label}</strong> — {gapMeta.desc}.</p>}
                </>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">Gap utama belum cukup kuat untuk ditampilkan. Buka detail untuk melihat semua indikator.</p>
              )}
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-primary/30 bg-primary/[0.045] p-5">
          <div className="flex items-start gap-3">
            <span className="grid h-8 w-8 place-items-center rounded-xl bg-primary text-primary-foreground text-sm font-bold shrink-0">3</span>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Arah solusi yang disarankan</p>
              {primaryRec ? (
                <>
                  <h2 className="font-semibold mt-1">{primaryRec.title || 'Usulan penelitian'}</h2>
                  <Markdown content={primaryRec.description || ''} className="mt-2 text-sm text-muted-foreground" />
                  {(primaryRec.why || primaryRec.how) && (
                    <details className="mt-3 group">
                      <summary className="cursor-pointer text-sm font-medium text-primary hover:underline">Mengapa dan bagaimana memulainya</summary>
                      <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        {primaryRec.why && <div className="rounded-lg border bg-card p-3 text-xs text-muted-foreground"><strong className="text-foreground">Mengapa:</strong> {primaryRec.why}</div>}
                        {primaryRec.how && <div className="rounded-lg border bg-card p-3 text-xs text-muted-foreground"><strong className="text-foreground">Bagaimana:</strong> {primaryRec.how}</div>}
                      </div>
                    </details>
                  )}
                  <p className="mt-3 flex items-start gap-1.5 text-xs text-amber-700/90 dark:text-amber-300/90"><Shield className="w-3.5 h-3.5 shrink-0 mt-px" />Ini adalah arah awal; tetap validasi dengan literatur dan pembimbing.</p>
                </>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">Belum ada arah solusi yang dapat disarankan dari hasil ini.</p>
              )}
            </div>
          </div>
        </section>

        <section className="rounded-2xl border bg-card/85 p-5">
          <div className="flex items-start gap-3">
            <span className="grid h-8 w-8 place-items-center rounded-xl bg-secondary text-foreground text-sm font-bold shrink-0">4</span>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Perkuat solusi dengan jurnal lain</p>
              <h2 className="font-semibold mt-1">Cari jurnal pendukung untuk solusi ini</h2>
              <p className="text-sm text-muted-foreground mt-1">Kami akan membuka pencarian dengan kata kunci yang disarankan, lalu Anda dapat menandai jurnal yang paling relevan.</p>
              <button
                type="button"
                onClick={onFindSources}
                disabled={!suggestedQuery}
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <BookOpen className="w-4 h-4" /> Cari Jurnal Pendukung <ArrowRight className="w-4 h-4" />
              </button>
              {suggestedQuery && <p className="mt-2 text-xs text-muted-foreground">Kata kunci awal: <span className="font-medium text-foreground">{suggestedQuery}</span></p>}
            </div>
          </div>
        </section>
      </div>

      <div className="mt-7 text-center">
        <button onClick={onShowFull} className="text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
          Saya ingin melihat semua detail analisis <ArrowRight className="inline w-3.5 h-3.5 ml-1" />
        </button>
      </div>
    </div>
  )
}

export default SimpleResultsView
