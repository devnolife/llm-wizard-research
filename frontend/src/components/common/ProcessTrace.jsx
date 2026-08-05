import { useState } from 'react'
import {
  Activity, BookOpen, Search, ShieldCheck, Sparkles, ChevronDown, Clock,
} from 'lucide-react'

// "Bagaimana hasil ini diproses?" — 4 kartu fase pipeline yang bisa diklik.
// Tiap kartu menjelaskan CARA KERJA fase tsb (bahasa awam) dan menampilkan
// apa yang BENAR-BENAR terjadi pada analisis ini (dari reasoning_trace backend).
const PHASES = {
  observe: {
    icon: BookOpen,
    title: 'Membaca Jurnal',
    color: 'blue',
    explain:
      'Sistem membaca isi setiap PDF, memecahnya menjadi potongan teks, lalu '
      + 'mengekstrak fakta terstruktur (Subjek–Predikat–Objek) seperti '
      + '"Metode X → digunakan-pada → Domain Y". Fakta inilah dasar semua '
      + 'analisis berikutnya — bukan sekadar kesan umum dari teks.',
  },
  think: {
    icon: Search,
    title: 'Mencari Gap',
    color: 'purple',
    explain:
      'Fakta antar-jurnal dibandingkan untuk menemukan 3 jenis gap: fragmentasi '
      + '(jurnal membahas hal sama tapi tidak saling terhubung), inkonsistensi '
      + '(temuan saling bertentangan — diperiksa model NLI khusus), dan '
      + 'ketidaklengkapan (aspek penting yang tidak dibahas jurnal mana pun).',
  },
  act: {
    icon: ShieldCheck,
    title: 'Memvalidasi',
    color: 'amber',
    explain:
      'Setiap kandidat gap diperiksa Rule Engine — 9 aturan logika (kelayakan, '
      + 'kausalitas, konsistensi) yang bekerja tanpa AI. Gap yang tidak masuk '
      + 'akal ditolak; yang meragukan ditandai "perlu tinjauan". Dari gap yang '
      + 'lolos, sistem menyusun rekomendasi arah penelitian.',
  },
  evaluate: {
    icon: Sparkles,
    title: 'Mengevaluasi Diri',
    color: 'emerald',
    explain:
      'Sebelum hasil ditampilkan, sistem menilai pekerjaannya sendiri: apakah '
      + 'bukti cukup? apakah gap konsisten dengan fakta? Jika skornya rendah, '
      + 'analisis diulang. Karena itu setiap hasil selalu berlabel "perlu '
      + 'validasi manusia" — sistem ini alat bantu, bukan pengganti Anda.',
  },
}

const COLOR = {
  blue: { text: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-500/10', ring: 'ring-blue-500/30' },
  purple: { text: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-500/10', ring: 'ring-purple-500/30' },
  amber: { text: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-500/10', ring: 'ring-amber-500/30' },
  emerald: { text: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-500/10', ring: 'ring-emerald-500/30' },
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  try {
    return new Date(timestamp).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
}

const ProcessTrace = ({ trace = [], stats = null }) => {
  const [openPhase, setOpenPhase] = useState(null)
  if (!trace.length) return null

  // Gabungkan aksi per fase (fase bisa muncul >1x saat ada iterasi ulang)
  const byPhase = {}
  for (const step of trace) {
    if (!byPhase[step.phase]) byPhase[step.phase] = { actions: [], time: formatTime(step.timestamp) }
    byPhase[step.phase].actions.push(...(step.actions || []))
  }
  const phaseKeys = Object.keys(PHASES).filter(k => byPhase[k])

  return (
    <section className="rounded-2xl border bg-card/85 p-5">
      <div className="flex items-center gap-2.5 mb-1">
        <Activity className="w-4 h-4 text-primary" />
        <h2 className="text-sm font-semibold">Bagaimana hasil ini diproses?</h2>
      </div>
      <p className="text-xs text-muted-foreground mb-4">
        Hasil di bawah tidak muncul begitu saja — sistem melewati {phaseKeys.length} tahap.
        Klik tahap mana pun untuk melihat cara kerjanya.
      </p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5">
        {phaseKeys.map((key, index) => {
          const meta = PHASES[key]
          const color = COLOR[meta.color]
          const Icon = meta.icon
          const isOpen = openPhase === key
          return (
            <button
              key={key}
              type="button"
              onClick={() => setOpenPhase(isOpen ? null : key)}
              aria-expanded={isOpen}
              className={`text-left rounded-xl border p-3.5 transition-all ${isOpen
                ? `ring-2 ${color.ring} ${color.bg}`
                : 'hover:border-primary/40 hover:bg-secondary/40'
                }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className={`grid h-8 w-8 place-items-center rounded-lg ${color.bg}`}>
                  <Icon className={`w-4 h-4 ${color.text}`} />
                </span>
                <ChevronDown className={`w-3.5 h-3.5 text-muted-foreground transition-transform ${isOpen ? 'rotate-180' : ''}`} />
              </div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Tahap {index + 1}</p>
              <p className="text-sm font-semibold leading-tight">{meta.title}</p>
            </button>
          )
        })}
      </div>

      {openPhase && (
        <div className="mt-3 rounded-xl border bg-secondary/30 p-4">
          <p className="text-sm leading-relaxed text-foreground/90 mb-3">{PHASES[openPhase].explain}</p>
          <div className="rounded-lg border bg-card p-3">
            <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              <Clock className="w-3 h-3" /> Yang terjadi pada analisis Anda
              {byPhase[openPhase].time && <span className="ml-auto font-normal normal-case">{byPhase[openPhase].time}</span>}
            </p>
            <ul className="space-y-1.5">
              {byPhase[openPhase].actions.map((action, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-foreground/85">
                  <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${COLOR[PHASES[openPhase].color].bg} ring-1 ${COLOR[PHASES[openPhase].color].ring}`} />
                  {action}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {stats && (
        <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
          {Number.isFinite(stats.total_facts) && (
            <span className="rounded-full bg-secondary px-2.5 py-1">Fakta terekstrak: <strong className="text-foreground">{stats.total_facts}</strong></span>
          )}
          {Number.isFinite(stats.total_entities) && (
            <span className="rounded-full bg-secondary px-2.5 py-1">Konsep dikenali: <strong className="text-foreground">{stats.total_entities}</strong></span>
          )}
          {stats.rule_engine && (
            <span className="rounded-full bg-secondary px-2.5 py-1">
              Validasi aturan: <strong className="text-foreground">{stats.rule_engine.passed ?? 0} lolos · {stats.rule_engine.flagged ?? 0} ditandai · {stats.rule_engine.rejected ?? 0} ditolak</strong>
            </span>
          )}
        </div>
      )}
    </section>
  )
}

export default ProcessTrace
