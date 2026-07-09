import {
  CheckCircle, FileText, Database, Tag, Sparkles, AlertTriangle, Search,
  Target, Lightbulb, Zap, Shield, Compass, ArrowRight,
} from 'lucide-react'
import Term from '../../common/Term'
import Markdown from '../../common/Markdown'
import { GAP_COLORS } from './constants'

// Tampilan Ringkas Awal (default): dari jurnal yang diunggah,
// apa KATEGORI, PERSAMAAN, KEKURANGAN, dan USULANNYA.
const SimpleResultsView = ({ simpleData: sd, data, onShowFull }) => {
  const catColors = ['text-blue-500 bg-blue-500/10', 'text-purple-500 bg-purple-500/10', 'text-emerald-500 bg-emerald-500/10', 'text-amber-500 bg-amber-500/10', 'text-pink-500 bg-pink-500/10']
  return (
    <div className="w-full px-6 lg:px-10 py-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <CheckCircle className="w-6 h-6 text-green-500" />
          <h1 className="text-2xl font-bold tracking-tight">Hasil Awal</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Dari {sd?.papersInfo?.length || data?.files_processed || 0} jurnal yang Anda unggah — ini <strong>kategori</strong>, <strong>persamaan</strong>, <strong>kekurangan</strong>, dan <strong>usulannya</strong>.
        </p>
      </div>

      {/* Daftar jurnal */}
      <div className="rounded-lg border bg-card p-5 mb-6">
        <div className="flex items-center gap-2 mb-3">
          <FileText className="w-5 h-5 text-primary" />
          <h3 className="font-semibold text-sm">Jurnal yang Dianalisis</h3>
        </div>
        <div className="space-y-2">
          {(sd?.papersInfo || []).map((p, i) => (
            <div key={i} className="flex items-start gap-2.5 text-sm">
              <span className="w-5 h-5 rounded bg-secondary flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">{i + 1}</span>
              <span className="flex-1">{p.title}</span>
              {p.already_indexed && (
                <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 text-[10px] font-medium flex-shrink-0" title="Sudah ada di database">
                  <Database className="w-2.5 h-2.5" /> Sudah ada
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ① Kategori */}
      <div className="rounded-lg border bg-card p-5 mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold flex-shrink-0">1</span>
          <Tag className="w-5 h-5 text-purple-500" />
          <h3 className="font-semibold text-sm">Kategori — Jurnal Ini Berbasis Apa</h3>
        </div>
        <p className="text-xs text-muted-foreground mb-4 pl-8">Tiap jurnal dikelompokkan berdasarkan basisnya (metode/pendekatan inti).</p>
        {sd?.categories?.length > 0 ? (
          <div className="grid gap-3 md:grid-cols-2">
            {sd.categories.map((c, i) => (
              <div key={i} className="rounded-lg border bg-secondary/30 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${catColors[i % catColors.length]}`}>{c.basis}</span>
                  <span className="text-[10px] text-muted-foreground">{c.titles.length} jurnal</span>
                </div>
                <ul className="space-y-1">
                  {c.titles.map((t, j) => (
                    <li key={j} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                      <FileText className="w-3 h-3 text-primary flex-shrink-0 mt-0.5" /><span>{t}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground pl-8">Kategori belum tersedia untuk analisis ini.</p>
        )}
      </div>

      {/* ② Persamaan */}
      <div className="rounded-lg border bg-card p-5 mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold flex-shrink-0">2</span>
          <Sparkles className="w-5 h-5 text-amber-500" />
          <h3 className="font-semibold text-sm">Persamaan — Apa yang Sama dari Jurnal-Jurnal Ini</h3>
        </div>
        <p className="text-xs text-muted-foreground mb-4 pl-8">Kata kunci dan tema yang berulang di seluruh jurnal.</p>

        {sd?.summary && <p className="text-sm text-muted-foreground mb-4 pl-8">{sd.summary}</p>}

        {sd?.keywords?.length > 0 && (
          <div className="mb-4 pl-8">
            <p className="text-xs font-medium text-muted-foreground mb-2">Kata Kunci yang Sama</p>
            <div className="flex flex-wrap gap-2">
              {sd.keywords.map((kw, i) => (
                <span key={i} className="px-2.5 py-1 rounded-full text-xs font-medium bg-purple-500/10 text-purple-600 dark:text-purple-400">{kw}</span>
              ))}
            </div>
          </div>
        )}

        {sd?.themes?.length > 0 && (
          <div className="pl-8">
            <p className="text-xs font-medium text-muted-foreground mb-2">Tema Bersama</p>
            <ul className="space-y-1">
              {sd.themes.map((t, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="text-amber-500 mt-0.5">•</span><span>{t}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {(!sd?.keywords?.length && !sd?.themes?.length && !sd?.summary) && (
          <p className="text-sm text-muted-foreground pl-8">Persamaan belum tersedia untuk analisis ini.</p>
        )}
      </div>

      {/* ③ Kekurangan */}
      <div className="rounded-lg border bg-card p-5 mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold flex-shrink-0">3</span>
          <AlertTriangle className="w-5 h-5 text-rose-500" />
          <h3 className="font-semibold text-sm">Kekurangan — Apa yang Kurang dari Tiap Jurnal</h3>
        </div>
        <p className="text-xs text-muted-foreground mb-4 pl-8">
          Dibagi dua: <strong className="text-amber-600 dark:text-amber-400">tersurat</strong> (ditulis langsung oleh penulis) dan{' '}
          <strong className="text-rose-600 dark:text-rose-400">tersirat</strong> (tidak ditulis, tapi disimpulkan dari isi). Tiap poin disertai <strong>dasar</strong> dari jurnal — bukan tebakan.
        </p>

        {sd?.weaknesses?.length > 0 ? (
          <div className="space-y-4 pl-8">
            {sd.weaknesses.map((w, i) => (
              <div key={i} className="rounded-lg border bg-secondary/30 p-4">
                <div className="flex items-start gap-2 mb-3">
                  <FileText className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                  <span className="text-sm font-medium leading-snug">{w.title}</span>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {/* Tersurat */}
                  <div className="rounded-md border border-amber-500/20 bg-amber-500/5 p-3">
                    <div className="flex items-center gap-1.5 mb-2">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                      <span className="text-xs font-semibold text-amber-600 dark:text-amber-400">Tersurat</span>
                      <span className="text-[10px] text-muted-foreground">(ditulis eksplisit)</span>
                    </div>
                    {w.tersurat?.length > 0 ? (
                      <ul className="space-y-2">
                        {w.tersurat.map((t, j) => {
                          const poin = typeof t === 'object' ? t.poin : t
                          const dasar = typeof t === 'object' ? t.dasar : ''
                          const status = typeof t === 'object' ? t.verification_status : ''
                          const conf = typeof t === 'object' ? t.confidence : null
                          return (
                            <li key={j} className="flex items-start gap-1.5 text-xs">
                              <span className="text-amber-500 mt-0.5">•</span>
                              <div>
                                <span className="text-muted-foreground">{poin}</span>
                                {status && (
                                  <span className="ml-1.5 inline-flex items-center gap-0.5 rounded-full bg-emerald-500/15 px-1.5 py-0.5 text-[9px] font-medium text-emerald-700 dark:text-emerald-400 align-middle">
                                    ✓ {status}{conf != null ? ` ${Math.round(conf * 100)}%` : ''}
                                  </span>
                                )}
                                {dasar && (
                                  <p className="text-[11px] text-amber-700/80 dark:text-amber-300/70 mt-0.5">
                                    <span className="font-medium">Dasar:</span> {dasar}
                                  </p>
                                )}
                              </div>
                            </li>
                          )
                        })}
                      </ul>
                    ) : (
                      <p className="text-xs text-muted-foreground italic">Tidak ada kekurangan yang ditulis eksplisit.</p>
                    )}
                  </div>
                  {/* Tersirat */}
                  <div className="rounded-md border border-rose-500/20 bg-rose-500/5 p-3">
                    <div className="flex items-center gap-1.5 mb-2">
                      <Search className="w-3.5 h-3.5 text-rose-500" />
                      <span className="text-xs font-semibold text-rose-600 dark:text-rose-400">Tersirat</span>
                      <span className="text-[10px] text-muted-foreground">(disimpulkan)</span>
                    </div>
                    {w.tersirat?.length > 0 ? (
                      <ul className="space-y-2">
                        {w.tersirat.map((t, j) => {
                          const poin = typeof t === 'object' ? t.poin : t
                          const dasar = typeof t === 'object' ? t.dasar : ''
                          const status = typeof t === 'object' ? t.verification_status : ''
                          const conf = typeof t === 'object' ? t.confidence : null
                          const grounded = status === 'terbukti'
                          return (
                            <li key={j} className="flex items-start gap-1.5 text-xs">
                              <span className="text-rose-500 mt-0.5">•</span>
                              <div>
                                <span className="text-muted-foreground">{poin}</span>
                                {status && (
                                  <span className={`ml-1.5 inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[9px] font-medium align-middle ${grounded ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400' : 'bg-amber-500/15 text-amber-700 dark:text-amber-400'}`}>
                                    {grounded ? '✓' : '≈'} {status}{conf != null ? ` ${Math.round(conf * 100)}%` : ''}
                                  </span>
                                )}
                                {dasar && (
                                  <p className="text-[11px] text-rose-700/80 dark:text-rose-300/70 mt-0.5">
                                    <span className="font-medium">Dasar (dari isi jurnal):</span> {dasar}
                                  </p>
                                )}
                              </div>
                            </li>
                          )
                        })}
                      </ul>
                    ) : (
                      <p className="text-xs text-muted-foreground italic">Tidak terdeteksi kekurangan tersirat.</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground pl-8">Kekurangan belum tersedia untuk analisis ini.</p>
        )}
      </div>

      {/* ④ Usulan Penelitian */}
      <div className="rounded-xl border border-primary/30 bg-gradient-to-br from-primary/5 to-transparent p-5 mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-bold flex-shrink-0">4</span>
          <Target className="w-5 h-5 text-primary" />
          <h3 className="font-semibold text-sm">Usulan — Arah Penelitian dari Kekurangan Ini</h3>
        </div>
        <p className="text-xs text-muted-foreground mb-4 pl-8">
          Dari gap & kekurangan di atas, ini indikator arah penelitian yang bisa Anda kembangkan.
        </p>

        {sd?.primaryRec ? (
          <div className="pl-8 space-y-4">
            {sd.intro && (
              <p className="text-sm leading-relaxed text-foreground/90 border-l-2 border-primary/40 pl-3 italic">
                {sd.intro}
              </p>
            )}

            {/* Kartu judul usulan */}
            <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
              <div className="bg-primary/10 px-4 py-2 flex items-center gap-2 flex-wrap border-b">
                <Lightbulb className="w-4 h-4 text-primary flex-shrink-0" />
                <span className="text-[11px] font-semibold text-primary uppercase tracking-wide">Judul yang diusulkan</span>
                {sd.primaryRec.gap_type && GAP_COLORS[sd.primaryRec.gap_type] && (
                  <span className={`ml-auto px-2 py-0.5 rounded-full text-[10px] font-medium ${GAP_COLORS[sd.primaryRec.gap_type].bg} ${GAP_COLORS[sd.primaryRec.gap_type].text}`} title="Indikator synthesis gap yang dijawab usulan ini">
                    Menjawab: {GAP_COLORS[sd.primaryRec.gap_type].label}
                  </span>
                )}
              </div>
              <div className="p-4 space-y-3">
                {sd.primaryRec.title && (
                  <p className="font-semibold text-sm leading-snug">{sd.primaryRec.title}</p>
                )}
                {sd.primaryRec.description && (
                  <Markdown content={sd.primaryRec.description} className="text-sm text-muted-foreground" />
                )}

                <div className="grid gap-3 sm:grid-cols-2 pt-1">
                  {sd.primaryRec.why && (
                    <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-3">
                      <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 mb-1 flex items-center gap-1">
                        <Target className="w-3.5 h-3.5" /> Mengapa penting
                      </p>
                      <Markdown content={sd.primaryRec.why} className="text-xs text-muted-foreground" />
                    </div>
                  )}
                  {sd.primaryRec.how && (
                    <div className="rounded-md border border-blue-500/20 bg-blue-500/5 p-3">
                      <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 mb-1 flex items-center gap-1">
                        <Zap className="w-3.5 h-3.5" /> Pendekatan
                      </p>
                      <Markdown content={sd.primaryRec.how} className="text-xs text-muted-foreground" />
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Disclaimer ringkas */}
            <p className="flex items-start gap-1.5 text-[11px] text-amber-700/90 dark:text-amber-300/80">
              <Shield className="w-3.5 h-3.5 flex-shrink-0 mt-px" />
              <span>
                <strong>Indikator, bukan kesimpulan</strong> — usulan ini alat bantu keputusan berbasis{' '}
                <Term k="synthesis gap">synthesis gap</Term> dan <strong>perlu Anda validasi</strong> sebelum dijadikan judul.
              </span>
            </p>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground pl-8">Usulan belum tersedia untuk analisis ini.</p>
        )}
      </div>

      {/* CTA ke detail lengkap (banyak tab dibungkus di sini) */}
      <div className="rounded-lg border-2 border-dashed border-primary/30 p-6 text-center">
        <p className="text-sm text-muted-foreground mb-3">
          Cukup sampai sini untuk gambaran utama. Kalau ingin menelusuri lebih dalam — semua gap, rekomendasi, peta jalan, graf & pipeline — buka <strong>Detail</strong>.
        </p>
        <button
          onClick={onShowFull}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Compass className="w-4 h-4" />
          Lihat Detail
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

export default SimpleResultsView
