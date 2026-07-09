import { Sparkles, Shield, Compass } from 'lucide-react'
import Markdown from '../../common/Markdown'
import { verdictLabel } from '../../../utils/analysisParser'
import { GAP_COLORS } from './constants'

const DeepAnalysisPanel = ({ deepAnalysis }) => {
  if (!deepAnalysis) return null
  const indicators = deepAnalysis.gap_indicators || []
  const recs = deepAnalysis.recommendations || []

  return (
    <div className="space-y-6 mt-6">
      <div className="rounded-lg border-2 border-primary/20 bg-primary/5 p-4">
        <div className="flex items-center gap-2 mb-1">
          <Sparkles className="w-4 h-4 text-primary" />
          <span className="text-sm font-semibold">Hasil Analisis Mendalam</span>
        </div>
        <p className="text-xs text-muted-foreground">
          Deteksi gap lanjutan menggunakan pipeline multi-agen dengan {indicators.length} indikator gap ditemukan.
        </p>
      </div>

      {/* Gap Indicators */}
      {indicators.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-semibold text-sm">Indikator Gap Sintesis</h4>
          {indicators.map((gi, idx) => {
            const typeKey = (gi.indicator_type || '').toUpperCase()
            const colors = GAP_COLORS[typeKey] || GAP_COLORS.FRAGMENTATION
            return (
              <div key={idx} className={`rounded-lg border bg-card overflow-hidden border-l-4 ${colors.border}`}>
                <div className="p-5">
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
                        {colors.label}
                      </span>
                      {gi.confidence > 0 && (
                        <span className="text-xs text-muted-foreground">
                          Keyakinan: {(gi.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                      {gi.rule_engine_verdict && (
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${gi.rule_engine_verdict === 'PASS' ? 'bg-green-500/10 text-green-600 dark:text-green-400' :
                          gi.rule_engine_verdict === 'FLAG' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400' :
                            'bg-red-500/10 text-red-600 dark:text-red-400'
                          }`}>
                          <Shield className="w-3 h-3 inline mr-1" />{verdictLabel(gi.rule_engine_verdict)}
                        </span>
                      )}
                    </div>
                  </div>

                  {gi.title && <h5 className="font-medium text-sm mb-2">{gi.title}</h5>}
                  <Markdown content={gi.description} />

                  {/* Confidence Bar */}
                  {gi.confidence > 0 && (
                    <div className="mt-3 flex items-center gap-2">
                      <div className="flex-1 bg-secondary rounded-full h-1.5">
                        <div className={`h-1.5 rounded-full ${gi.confidence > 0.7 ? 'bg-green-500' : gi.confidence > 0.4 ? 'bg-amber-500' : 'bg-red-500'
                          }`} style={{ width: `${gi.confidence * 100}%` }} />
                      </div>
                      <span className="text-xs text-muted-foreground w-8">{(gi.confidence * 100).toFixed(0)}%</span>
                    </div>
                  )}

                  {/* Evidence */}
                  {gi.evidence?.length > 0 && (
                    <div className="mt-3 pt-3 border-t">
                      <p className="text-xs font-medium text-muted-foreground mb-2">Bukti Pendukung</p>
                      <div className="space-y-1">
                        {gi.evidence.slice(0, 3).map((ev, i) => (
                          <p key={i} className="text-xs text-muted-foreground/80 pl-3 border-l-2 border-border">{ev}</p>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Suggested Directions */}
                  {gi.suggested_directions?.length > 0 && (
                    <div className="mt-3 pt-3 border-t">
                      <p className="text-xs font-medium text-muted-foreground mb-2">Arah Penelitian yang Disarankan</p>
                      <div className="space-y-1">
                        {gi.suggested_directions.map((dir, i) => (
                          <div key={i} className="flex items-start gap-2">
                            <Compass className="w-3 h-3 text-primary flex-shrink-0 mt-0.5" />
                            <span className="text-xs text-muted-foreground">{dir}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Structured Recommendations from Deep Analysis */}
      {recs.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-semibold text-sm">Rekomendasi Paper</h4>
          {recs.map((rec, idx) => (
            <div key={idx} className="rounded-lg border bg-card p-4 flex items-start gap-3">
              <div className="w-7 h-7 rounded bg-primary/10 text-primary flex items-center justify-center flex-shrink-0 text-xs font-bold">
                {rec.rank || idx + 1}
              </div>
              <div className="flex-1 min-w-0">
                <h5 className="font-medium text-sm">{rec.title || 'Tanpa Judul'}</h5>
                <p className="text-xs text-muted-foreground mt-1">{rec.reason || rec.reasons?.join('; ') || ''}</p>
                {rec.relevance_score > 0 && (
                  <div className="flex items-center gap-2 mt-2">
                    <div className="flex-1 bg-secondary rounded-full h-1 max-w-[120px]">
                      <div className="bg-primary h-1 rounded-full" style={{ width: `${Math.min(rec.relevance_score * 100, 100)}%` }} />
                    </div>
                    <span className="text-xs text-muted-foreground">{(rec.relevance_score * 100).toFixed(0)}% cocok</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default DeepAnalysisPanel
