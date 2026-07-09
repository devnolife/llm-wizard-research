import {
  FileText, Database, Share2, Search, Shield, Compass, Sparkles, Loader,
} from 'lucide-react'
import Markdown from '../../common/Markdown'
import DeepAnalysisPanel from './DeepAnalysisPanel'
import { verdictLabel } from '../../../utils/analysisParser'
import { GAP_TYPES, GAP_COLORS, GAP_METHOD } from './constants'

const GapsTab = ({ data, parsedGaps, deepAnalysis, deepLoading, runDeepAnalysis }) => (
  <div className="space-y-4">
    <div className="mb-2">
      <h3 className="text-lg font-semibold">Deteksi Gap Sintesis</h3>
      <p className="text-sm text-muted-foreground">
        Gap penelitian yang teridentifikasi melalui analisis komparatif lintas paper, dikategorikan berdasarkan indikator Cooper (1998).
      </p>
    </div>

    {/* Gap Type Legend */}
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      {GAP_TYPES.map(type => {
        const c = GAP_COLORS[type]
        const count = parsedGaps.filter(g => (g.type || GAP_TYPES[g.index % GAP_TYPES.length]) === type).length
        return (
          <div key={type} className={`flex items-start gap-3 p-3 rounded-lg border ${c.border} border-l-4`}>
            <div className={`w-8 h-8 rounded ${c.bg} flex items-center justify-center flex-shrink-0`}>
              <span className={`text-sm font-bold ${c.text}`}>{count}</span>
            </div>
            <div>
              <p className={`text-sm font-medium ${c.text}`}>{c.label}</p>
              <p className="text-xs text-muted-foreground">{c.desc}</p>
            </div>
          </div>
        )
      })}
    </div>

    {/* Bagaimana cara menemukan gap — metodologi pipeline (data nyata) */}
    {(() => {
      const nPapers = data?.files_processed || data?.papers_info?.length || data?.papers?.length || 0
      const nChunks = data?.total_chunks || 0
      const nFacts = data?.fact_table_stats?.total_facts || 0
      const nEntities = data?.fact_table_stats?.total_entities || 0
      const rr = data?.rule_engine_report || {}
      const ruleTotal = rr.total ?? parsedGaps.filter(g => g.rule_engine_verdict).length
      const steps = [
        {
          icon: FileText, color: 'text-blue-500',
          title: 'Baca & pecah jurnal',
          desc: `Sistem membaca ${nPapers || 'beberapa'} jurnal${nChunks ? ` dan memecahnya menjadi ${nChunks} potongan teks` : ''} agar bisa dianalisis mendetail.`,
        },
        {
          icon: Database, color: 'text-emerald-500',
          title: 'Ekstraksi fakta (SPO)',
          desc: `Tiap kalimat penting diubah jadi fakta Subjek–Predikat–Objek${(nFacts || nEntities) ? ` — terkumpul ${nFacts} fakta dari ${nEntities} entitas` : ''}.`,
        },
        {
          icon: Share2, color: 'text-purple-500',
          title: 'Bangun Knowledge Graph',
          desc: 'Fakta-fakta dirangkai jadi peta keterhubungan antar-konsep & antar-paper, sehingga celah antar-jurnal terlihat.',
        },
        {
          icon: Search, color: 'text-amber-500',
          title: 'Bandingkan antar-paper',
          desc: 'Sistem mencari 3 sinyal gap: Fragmentasi (tak terintegrasi), Inkonsistensi (saling bertentangan), dan Ketidaklengkapan (aspek belum tercakup).',
        },
        {
          icon: Shield, color: 'text-green-500',
          title: 'Validasi Rule Engine',
          desc: `Tiap calon gap diuji 9 aturan logika${ruleTotal ? ` (${ruleTotal} indikator diperiksa)` : ''} lalu diberi status Lolos / Perlu Ditinjau / Ditolak.`,
        },
      ]
      return (
        <div className="rounded-lg border bg-card p-5">
          <div className="flex items-center gap-2 mb-1">
            <Compass className="w-5 h-5 text-primary" />
            <h4 className="font-semibold text-sm">Bagaimana Cara Sistem Menemukan Gap Ini?</h4>
          </div>
          <p className="text-xs text-muted-foreground mb-4">
            Gap tidak ditebak — diperoleh lewat 5 langkah berikut, mengikuti model 3 indikator Cooper (1998).
          </p>
          <ol className="space-y-3">
            {steps.map((s, i) => {
              const Icon = s.icon
              return (
                <li key={i} className="flex items-start gap-3">
                  <span className="w-6 h-6 rounded-full bg-secondary flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">{i + 1}</span>
                  <Icon className={`w-4 h-4 ${s.color} flex-shrink-0 mt-1`} />
                  <div>
                    <p className="text-sm font-medium leading-snug">{s.title}</p>
                    <p className="text-xs text-muted-foreground">{s.desc}</p>
                  </div>
                </li>
              )
            })}
          </ol>
        </div>
      )
    })()}

    {/* Gap Cards */}
    <div className="space-y-4">
      {parsedGaps.map((gap, idx) => {
        const typeKey = gap.type || GAP_TYPES[idx % GAP_TYPES.length]
        const colors = GAP_COLORS[typeKey]
        return (
          <div key={idx} className={`rounded-lg border bg-card overflow-hidden border-l-4 ${colors.border}`}>
            <div className="p-5">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg ${colors.bg} flex items-center justify-center flex-shrink-0`}>
                    <span className={`text-sm font-bold ${colors.text}`}>{idx + 1}</span>
                  </div>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
                    {colors.label}
                  </span>
                  {gap.confidence != null && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-muted text-muted-foreground">
                      Keyakinan: {(gap.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                  {gap.rule_engine_verdict && (
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${gap.rule_engine_verdict === 'ACCEPT' ? 'bg-green-500/10 text-green-600' :
                      gap.rule_engine_verdict === 'REVIEW' ? 'bg-amber-500/10 text-amber-600' :
                        'bg-red-500/10 text-red-600'
                      }`}>
                      {verdictLabel(gap.rule_engine_verdict)}
                    </span>
                  )}
                </div>
              </div>
              {gap.title && <h4 className="font-medium text-sm mb-2">{gap.title}</h4>}
              <Markdown content={gap.description} className="text-foreground" />

              {/* Cara menemukan gap ini — metode deteksi per jenis */}
              {GAP_METHOD[typeKey] && (
                <div className={`mt-3 rounded-md border-l-2 ${colors.border} ${colors.bg} p-3`}>
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Search className={`w-3.5 h-3.5 ${colors.text}`} />
                    <p className={`text-xs font-semibold ${colors.text}`}>Cara menemukan gap ini</p>
                  </div>
                  <p className="text-xs text-muted-foreground mb-1">
                    <span className="font-medium text-foreground">Yang dicari:</span> {GAP_METHOD[typeKey].look}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">Cara deteksi:</span> {GAP_METHOD[typeKey].how}
                  </p>
                  {(gap.confidence != null || gap.rule_engine_verdict) && (
                    <p className="text-xs text-muted-foreground mt-1.5 pt-1.5 border-t border-border/60">
                      <span className="font-medium text-foreground">Hasil:</span>{' '}
                      {gap.confidence != null && `tingkat keyakinan ${(gap.confidence * 100).toFixed(0)}%`}
                      {gap.confidence != null && gap.rule_engine_verdict && ', '}
                      {gap.rule_engine_verdict && `divalidasi Rule Engine → ${verdictLabel(gap.rule_engine_verdict)}`}
                      .
                    </p>
                  )}
                </div>
              )}

              {gap.evidence?.length > 0 && (
                <div className="mt-3 pt-3 border-t border-border">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Bukti:</p>
                  <ul className="text-xs text-muted-foreground space-y-1">
                    {gap.evidence.map((ev, i) => <li key={i} className="flex items-start gap-1"><span>•</span><span>{ev}</span></li>)}
                  </ul>
                </div>
              )}
              {gap.suggested_directions?.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Arah yang Disarankan:</p>
                  {gap.suggested_directions.some(d => String(d).length > 40) ? (
                    <ul className="space-y-1">
                      {gap.suggested_directions.map((dir, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                          <Compass className="w-3.5 h-3.5 text-primary flex-shrink-0 mt-0.5" />
                          <span>{dir}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {gap.suggested_directions.map((dir, i) => (
                        <span key={i} className="px-2 py-0.5 rounded-full text-xs bg-primary/10 text-primary">{dir}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>

    {parsedGaps.length === 0 && (
      <div className="text-center py-12 text-muted-foreground">
        <Search className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p className="text-sm">Tidak ada gap penelitian yang terdeteksi.</p>
      </div>
    )}

    {/* Deep Analysis CTA in Gaps tab */}
    {!deepAnalysis && parsedGaps.length > 0 && (
      <div className="rounded-lg border-2 border-dashed border-primary/30 p-6 text-center">
        <Sparkles className="w-8 h-8 text-primary/50 mx-auto mb-2" />
        <h4 className="font-semibold text-sm mb-1">Ingin insight lebih mendalam?</h4>
        <p className="text-xs text-muted-foreground mb-3">
          Jalankan analisis mendalam untuk mendapatkan indikator gap terstruktur dengan skor kepercayaan, bukti, dan arah penelitian yang disarankan.
        </p>
        <button
          onClick={runDeepAnalysis}
          disabled={deepLoading}
          className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 inline-flex items-center gap-2"
        >
          {deepLoading ? <Loader className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {deepLoading ? 'Memproses...' : 'Jalankan Analisis Mendalam'}
        </button>
      </div>
    )}

    {deepAnalysis && <DeepAnalysisPanel deepAnalysis={deepAnalysis} />}
  </div>
)

export default GapsTab
