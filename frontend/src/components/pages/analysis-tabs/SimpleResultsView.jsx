import {
  ArrowRight, BookOpen, CheckCircle, Lightbulb, Search, Shield,
} from 'lucide-react'
import Markdown from '../../common/Markdown'
import ProcessTrace from '../../common/ProcessTrace'
import { GAP_COLORS } from './constants'

// Tampilan hasil default: SATU alur bersambung dari input jurnal → proses →
// gap ditemukan → arah solusi → langkah berikutnya. Semua menempel di
// timeline yang sama sehingga jelas hasil lahir dari proses di atasnya.
const SimpleResultsView = ({ simpleData: sd, data, onShowFull, onFindSources }) => {
  const primaryGap = sd?.primaryGap
  const primaryRec = sd?.primaryRec
  const gapType = primaryGap?.type || primaryGap?.gap_type
  const gapMeta = GAP_COLORS[gapType]
  const suggestedQuery = primaryRec?.title || primaryGap?.title || data?.topics?.[0] || ''

  // Kartu HASIL yang menyambung di ujung timeline proses
  const tail = [
    {
      icon: Search,
      label: 'Hasil — gap ditemukan',
      highlight: true,
      content: primaryGap ? (
        <div className={`rounded-xl border bg-card p-4 border-l-4 ${gapMeta?.border || 'border-l-amber-500'}`}>
          <h2 className="font-semibold leading-snug">{primaryGap.title || 'Celah penelitian utama'}</h2>
          <Markdown
            content={primaryGap.description || 'Sistem menemukan area yang masih perlu disatukan, diuji kembali, atau dilengkapi.'}
            className="mt-2 text-sm text-muted-foreground"
          />
          {gapMeta && (
            <p className="mt-3 text-xs text-muted-foreground">
              Jenis gap: <strong className={gapMeta.text}>{gapMeta.label}</strong> — {gapMeta.desc}.
            </p>
          )}
        </div>
      ) : (
        <div className="rounded-xl border bg-card p-4">
          <p className="text-sm text-muted-foreground">
            Gap utama belum cukup kuat untuk ditampilkan. Buka detail analisis untuk melihat semua indikator.
          </p>
        </div>
      ),
    },
    primaryRec && {
      icon: Lightbulb,
      label: 'Arah solusi yang disarankan',
      content: (
        <div className="rounded-xl border border-primary/30 bg-primary/[0.045] p-4">
          <h2 className="font-semibold leading-snug">{primaryRec.title || 'Usulan penelitian'}</h2>
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
          <p className="mt-3 flex items-start gap-1.5 text-xs text-amber-700/90 dark:text-amber-300/90">
            <Shield className="w-3.5 h-3.5 shrink-0 mt-px" />
            Ini adalah arah awal; tetap validasi dengan literatur dan pembimbing.
          </p>
        </div>
      ),
    },
    {
      icon: BookOpen,
      label: 'Langkah Anda berikutnya',
      content: (
        <div className="rounded-xl border bg-card p-4">
          <h2 className="font-semibold leading-snug">Perkuat solusi dengan jurnal pendukung</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Kami akan membuka pencarian dengan kata kunci yang disarankan, lalu Anda dapat menandai jurnal yang paling relevan.
          </p>
          <button
            type="button"
            onClick={onFindSources}
            disabled={!suggestedQuery}
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <BookOpen className="w-4 h-4" /> Cari Jurnal Pendukung <ArrowRight className="w-4 h-4" />
          </button>
          {suggestedQuery && (
            <p className="mt-2 text-xs text-muted-foreground">
              Kata kunci awal: <span className="font-medium text-foreground">{suggestedQuery}</span>
            </p>
          )}
        </div>
      ),
    },
  ].filter(Boolean)

  return (
    <div className="w-full px-4 sm:px-6 lg:px-10 xl:px-14 py-8 max-w-screen-2xl mx-auto">
      <header className="mb-7">
        <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 mb-3">
          <CheckCircle className="w-5 h-5" />
          <span className="text-sm font-semibold">Analisis selesai</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Dari jurnal Anda sampai gap ditemukan.</h1>
        <p className="text-sm text-muted-foreground mt-2 leading-relaxed max-w-2xl">
          Satu alur lengkap: jurnal dibaca, faktanya dibandingkan, diuji aturan logika, sampai gap dan arah solusi muncul di ujungnya.
        </p>
      </header>

      {/* Layout penuh: proses di kiri, hasil menempel (sticky) di kanan */}
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_380px] xl:grid-cols-[minmax(0,1fr)_420px] items-start">
        <div className="min-w-0">
          {/* Di layar kecil hasil tetap menyambung di timeline yang sama */}
          <div className="lg:hidden">
            <ProcessTrace data={data} tail={tail} />
          </div>
          <div className="hidden lg:block">
            <ProcessTrace data={data} />
          </div>
        </div>

        <aside className="hidden lg:block sticky top-24 space-y-4">
          {tail.map((item, i) => {
            const Icon = item.icon
            return (
              <div key={i}>
                <p className={`mb-2 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.14em] ${item.highlight ? 'text-amber-600 dark:text-amber-400' : 'text-primary'}`}>
                  <Icon className="h-3.5 w-3.5" /> {item.label}
                </p>
                {item.content}
              </div>
            )
          })}
          <div className="pt-1 text-center">
            <button onClick={onShowFull} className="text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
              Lihat semua detail analisis <ArrowRight className="inline w-3.5 h-3.5 ml-1" />
            </button>
          </div>
        </aside>
      </div>

      <div className="mt-7 text-center lg:hidden">
        <button onClick={onShowFull} className="text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
          Saya ingin melihat semua detail analisis <ArrowRight className="inline w-3.5 h-3.5 ml-1" />
        </button>
      </div>
    </div>
  )
}

export default SimpleResultsView
