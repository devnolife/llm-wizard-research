import {
  Target, FileText, Database, Tag, Search, Lightbulb, Map, ArrowRight,
  Clock, TrendingUp, BookOpen, Zap, Shield,
} from 'lucide-react'
import Term from '../../common/Term'
import Markdown from '../../common/Markdown'
import { verdictLabel } from '../../../utils/analysisParser'
import { GAP_TYPES, GAP_COLORS, GAP_METHOD, PRIORITY_COLORS } from './constants'

const ProposalTab = ({ proposal, data, setActiveTab }) => {
  if (!proposal) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Target className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p className="text-sm">Belum ada usulan penelitian. Jalankan analisis terlebih dahulu.</p>
      </div>
    )
  }
  const { papersInfo, duplicateCount, paperGroups, intro, primaryGap, primaryRec, flow, relatedRefs } = proposal
  const gapType = primaryGap?.type || GAP_TYPES[0]
  const gapColors = GAP_COLORS[gapType] || GAP_COLORS.FRAGMENTATION
  const recPrio = PRIORITY_COLORS[primaryRec?.priority] || PRIORITY_COLORS.high
  const phaseIcons = { zap: Zap, trending: TrendingUp, target: Target, clock: Clock }

  return (
    <div className="space-y-6">
      {/* Hero: AI intro + sumber jurnal */}
      <div className="rounded-lg border-2 border-primary/30 bg-primary/5 p-6">
        <div className="flex items-center gap-2 mb-3">
          <Target className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold">Usulan Penelitian Baru</h3>
        </div>
        {intro && <p className="text-sm leading-relaxed mb-4">{intro}</p>}

        {/* Disclaimer: posisi sistem sebagai alat bantu keputusan (sesuai revisi penguji) */}
        <div className="flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 mb-4">
          <Shield className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-amber-700 dark:text-amber-300 leading-relaxed">
            <strong>Indikator, bukan kesimpulan.</strong> Usulan ini dihasilkan sebagai <em>alat bantu keputusan</em>{' '}
            (decision-support) berbasis indikator <Term k="synthesis gap">synthesis gap</Term>.
            Keputusan akhir tetap berada di tangan peneliti — semua usulan <strong>perlu divalidasi</strong> secara manual.
          </p>
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1.5">
            Disintesis dari {papersInfo.length || data?.files_processed || 0} jurnal:
          </p>
          <div className="flex flex-wrap gap-2">
            {papersInfo.length > 0 ? papersInfo.map((p, i) => (
              <span key={i} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-card border text-xs">
                <FileText className="w-3 h-3 text-primary flex-shrink-0" />
                <span className="max-w-[260px] truncate" title={p.title}>{p.title}</span>
                {p.already_indexed && (
                  <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 text-[10px] font-medium" title="Paper ini sudah ada di database, tidak diindeks ulang">
                    <Database className="w-2.5 h-2.5" /> Sudah ada
                  </span>
                )}
              </span>
            )) : (
              <span className="text-xs text-muted-foreground">{data?.files_processed || 0} dokumen diproses</span>
            )}
          </div>
          {duplicateCount > 0 && (
            <p className="mt-2 text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
              <Database className="w-3 h-3 flex-shrink-0" />
              {duplicateCount} dari {papersInfo.length} jurnal sudah ada di database — dipakai ulang tanpa pengindeksan ganda.
            </p>
          )}
        </div>
      </div>

      {/* Pengelompokan jurnal berdasarkan basis */}
      {paperGroups.length > 0 && (
        <div className="rounded-lg border bg-card p-5">
          <div className="flex items-center gap-2 mb-1">
            <Tag className="w-5 h-5 text-purple-500" />
            <h4 className="font-semibold text-sm">Pengelompokan Jurnal</h4>
          </div>
          <p className="text-xs text-muted-foreground mb-4">
            Jurnal yang Anda unggah dikelompokkan berdasarkan basisnya (metode/pendekatan inti).
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            {paperGroups.map((g, i) => (
              <div key={i} className="rounded-lg border bg-secondary/30 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-500/10 text-purple-600 dark:text-purple-400">
                    {g.basis}
                  </span>
                  <span className="text-[10px] text-muted-foreground">{g.titles.length} jurnal</span>
                </div>
                <ul className="space-y-1">
                  {g.titles.map((t, j) => (
                    <li key={j} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                      <FileText className="w-3 h-3 text-primary flex-shrink-0 mt-0.5" />
                      <span>{t}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Flow: Jurnal → Gap → Usulan → Alur */}
      <div className="flex items-center justify-center gap-2 flex-wrap text-xs font-medium">
        {[
          { icon: FileText, label: `${papersInfo.length || data?.files_processed || 0} Jurnal`, color: 'text-blue-500 bg-blue-500/10' },
          { icon: Search, label: 'Gap', color: 'text-amber-500 bg-amber-500/10' },
          { icon: Lightbulb, label: 'Usulan', color: 'text-primary bg-primary/10' },
          { icon: Map, label: 'Alur', color: 'text-emerald-500 bg-emerald-500/10' },
        ].map((step, i, arr) => (
          <div key={i} className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full ${step.color}`}>
              <step.icon className="w-3.5 h-3.5" />{step.label}
            </span>
            {i < arr.length - 1 && <ArrowRight className="w-4 h-4 text-muted-foreground" />}
          </div>
        ))}
      </div>

      {/* ① Gap yang Ditemukan */}
      {primaryGap && (
        <div className={`rounded-lg border bg-card overflow-hidden border-l-4 ${gapColors.border}`}>
          <div className="p-5">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className="w-6 h-6 rounded-full bg-secondary flex items-center justify-center text-xs font-bold flex-shrink-0">1</span>
              <h4 className="font-semibold text-sm">Gap yang Ditemukan</h4>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${gapColors.bg} ${gapColors.text}`}>{gapColors.label}</span>
              {primaryGap.confidence != null && primaryGap.confidence > 0 && (
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-muted text-muted-foreground">
                  Keyakinan: {(primaryGap.confidence * 100).toFixed(0)}%
                </span>
              )}
              {primaryGap.rule_engine_verdict && (
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${String(primaryGap.rule_engine_verdict).toUpperCase() === 'PASS' || String(primaryGap.rule_engine_verdict).toUpperCase() === 'ACCEPT' ? 'bg-green-500/10 text-green-600 dark:text-green-400' : String(primaryGap.rule_engine_verdict).toUpperCase() === 'REJECT' ? 'bg-red-500/10 text-red-600 dark:text-red-400' : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'}`} title="Hasil validasi Rule Engine (simbolik)">
                  <Term k="Rule Engine">Rule Engine</Term>: {verdictLabel(primaryGap.rule_engine_verdict)}
                </span>
              )}
            </div>
            {primaryGap.title && <p className="font-medium text-sm mb-1">{primaryGap.title}</p>}
            <Markdown content={primaryGap.description} className="text-foreground" />
            {GAP_METHOD[gapType] && (
              <div className={`mt-3 rounded-md border-l-2 ${gapColors.border} ${gapColors.bg} p-3`}>
                <div className="flex items-center gap-1.5 mb-1">
                  <Search className={`w-3.5 h-3.5 ${gapColors.text}`} />
                  <p className={`text-xs font-semibold ${gapColors.text}`}>Bagaimana gap ini ditemukan?</p>
                </div>
                <p className="text-xs text-muted-foreground">{GAP_METHOD[gapType].how}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ② Usulan Penelitian */}
      {primaryRec && (
        <div className={`rounded-lg border bg-card overflow-hidden border-l-4 ${primaryRec.priority === 'high' ? 'border-l-red-500' : primaryRec.priority === 'medium' ? 'border-l-amber-500' : 'border-l-green-500'
          }`}>
          <div className="p-5">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className="w-6 h-6 rounded-full bg-secondary flex items-center justify-center text-xs font-bold flex-shrink-0">2</span>
              <h4 className="font-semibold text-sm">Usulan Penelitian</h4>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${recPrio.bg} ${recPrio.text}`}>{recPrio.label}</span>
              {primaryRec.gap_type && GAP_COLORS[primaryRec.gap_type] && (
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${GAP_COLORS[primaryRec.gap_type].bg} ${GAP_COLORS[primaryRec.gap_type].text}`} title="Indikator synthesis gap yang dijawab usulan ini">
                  Menjawab: {GAP_COLORS[primaryRec.gap_type].label}
                </span>
              )}
            </div>
            {primaryRec.title && <p className="font-semibold text-sm mb-1">{primaryRec.title}</p>}
            <Markdown content={primaryRec.description} className="text-foreground" />
            <p className="mt-2 text-[11px] text-muted-foreground italic flex items-center gap-1">
              <Shield className="w-3 h-3 flex-shrink-0" />
              Bersifat indikatif — perlu ditinjau & divalidasi peneliti sebelum dijadikan judul final.
            </p>
            {(primaryRec.why || primaryRec.how) && (
              <div className="mt-3 space-y-3 pt-3 border-t">
                {primaryRec.why && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground mb-1 flex items-center gap-1">
                      <Target className="w-3 h-3" /> Mengapa Ini Penting
                    </p>
                    <Markdown content={primaryRec.why} className="text-muted-foreground pl-4" />
                  </div>
                )}
                {primaryRec.how && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground mb-1 flex items-center gap-1">
                      <Zap className="w-3 h-3" /> Pendekatan yang Disarankan
                    </p>
                    <Markdown content={primaryRec.how} className="text-muted-foreground pl-4" />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ③ Alur Penelitian */}
      {flow.length > 0 && (
        <div className="rounded-lg border bg-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <span className="w-6 h-6 rounded-full bg-secondary flex items-center justify-center text-xs font-bold flex-shrink-0">3</span>
            <h4 className="font-semibold text-sm">Alur Penelitian</h4>
          </div>
          <div className="relative">
            {flow.map((phase, phaseIdx) => {
              const Icon = phaseIcons[phase.icon] || Clock
              return (
                <div key={phaseIdx} className="relative flex gap-4 pb-6 last:pb-0">
                  {phaseIdx < flow.length - 1 && (
                    <div className="absolute left-4 top-9 bottom-0 w-0.5 bg-border" />
                  )}
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-4 h-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm mb-2">{phase.label}</p>
                    <div className="space-y-1.5">
                      {phase.items.map((item, idx) => (
                        <div key={idx} className="flex items-start gap-2 text-sm text-muted-foreground">
                          <ArrowRight className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                          <span>{item}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Paper rujukan pendukung (dari korpus) */}
      {relatedRefs?.length > 0 && (
        <div className="rounded-lg border bg-card p-5">
          <div className="flex items-center gap-2 mb-1">
            <BookOpen className="w-5 h-5 text-cyan-500" />
            <h4 className="font-semibold text-sm">Paper Rujukan Pendukung</h4>
          </div>
          <p className="text-xs text-muted-foreground mb-4">
            Paper relevan dari koleksi yang dapat memperkuat usulan ini (bahan bacaan awal — bukan bagian dari usulan).
          </p>
          <ul className="space-y-2">
            {relatedRefs.slice(0, 5).map((ref, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm">
                <span className="w-5 h-5 rounded bg-secondary flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">{i + 1}</span>
                <div className="min-w-0">
                  <p className="font-medium leading-snug">{ref.title}</p>
                  {ref.reason && <p className="text-xs text-muted-foreground mt-0.5">{ref.reason}</p>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* CTA ke detail */}
      <div className="flex items-center justify-center gap-4 text-xs">
        <button onClick={() => setActiveTab('gaps')} className="text-primary hover:underline flex items-center gap-1">
          Lihat semua gap <ArrowRight className="w-3 h-3" />
        </button>
        <button onClick={() => setActiveTab('recommendations')} className="text-primary hover:underline flex items-center gap-1">
          Lihat semua rekomendasi <ArrowRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  )
}

export default ProposalTab
