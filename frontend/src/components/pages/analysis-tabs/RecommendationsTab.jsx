import { Lightbulb, Target, Zap, ChevronDown, Sparkles, Loader } from 'lucide-react'
import Markdown from '../../common/Markdown'
import DeepAnalysisPanel from './DeepAnalysisPanel'
import { PRIORITY_COLORS } from './constants'

const RecommendationsTab = ({ parsedRecommendations, expandedRecs, setExpandedRecs, deepAnalysis, deepLoading, runDeepAnalysis }) => (
  <div className="space-y-4">
    <div className="flex items-start justify-between mb-2">
      <div>
        <h3 className="text-lg font-semibold">Rekomendasi Penelitian</h3>
        <p className="text-sm text-muted-foreground">
          Arah penelitian yang dapat ditindaklanjuti dengan justifikasi, berdasarkan gap yang terdeteksi dan analisis komparatif.
        </p>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0 ml-4">
        <span className="text-xs text-muted-foreground bg-secondary px-2 py-1 rounded">
          {parsedRecommendations.length} rekomendasi
        </span>
      </div>
    </div>

    {/* Priority Summary */}
    <div className="flex gap-3">
      {['high', 'medium', 'low'].map(p => {
        const count = parsedRecommendations.filter(r => r.priority === p).length
        if (count === 0) return null
        const colors = PRIORITY_COLORS[p]
        return (
          <div key={p} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg ${colors.bg}`}>
            <div className={`w-2 h-2 rounded-full ${p === 'high' ? 'bg-red-500' : p === 'medium' ? 'bg-amber-500' : 'bg-green-500'}`} />
            <span className={`text-xs font-medium ${colors.text}`}>{count} {colors.label}</span>
          </div>
        )
      })}
    </div>

    {/* Recommendation Cards */}
    <div className="space-y-3">
      {parsedRecommendations.map((rec, idx) => {
        const prio = PRIORITY_COLORS[rec.priority]
        const isExpanded = expandedRecs[idx]
        const hasDetails = rec.why || rec.how

        return (
          <div key={idx} className={`rounded-lg border bg-card overflow-hidden hover:border-primary/30 transition-colors border-l-4 ${rec.priority === 'high' ? 'border-l-red-500' : rec.priority === 'medium' ? 'border-l-amber-500' : 'border-l-green-500'
            }`}>
            <div className="p-5">
              <div className="flex items-start gap-4">
                <div className={`w-8 h-8 rounded-lg ${prio.bg} flex items-center justify-center flex-shrink-0`}>
                  <Lightbulb className={`w-4 h-4 ${prio.text}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${prio.bg} ${prio.text}`}>
                      #{idx + 1} · {prio.label}
                    </span>
                    {rec.title && <span className="font-semibold text-sm">{rec.title}</span>}
                  </div>
                  <Markdown content={rec.description} className="text-foreground" />

                  {/* Expandable details */}
                  {hasDetails && (
                    <>
                      <button
                        onClick={() => setExpandedRecs(prev => ({ ...prev, [idx]: !prev[idx] }))}
                        className="flex items-center gap-1 text-xs text-primary mt-2 hover:underline"
                      >
                        {isExpanded ? 'Sembunyikan' : 'Lihat'} detail
                        <ChevronDown className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                      </button>

                      {isExpanded && (
                        <div className="mt-3 space-y-3 pt-3 border-t">
                          {rec.why && (
                            <div>
                              <p className="text-xs font-semibold text-muted-foreground mb-1 flex items-center gap-1">
                                <Target className="w-3 h-3" /> Mengapa Ini Penting
                              </p>
                              <Markdown content={rec.why} className="text-muted-foreground pl-4" />
                            </div>
                          )}
                          {rec.how && (
                            <div>
                              <p className="text-xs font-semibold text-muted-foreground mb-1 flex items-center gap-1">
                                <Zap className="w-3 h-3" /> Pendekatan yang Disarankan
                              </p>
                              <Markdown content={rec.how} className="text-muted-foreground pl-4" />
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        )
      })}
    </div>

    {parsedRecommendations.length === 0 && (
      <div className="text-center py-12 text-muted-foreground">
        <Lightbulb className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p className="text-sm">Belum ada rekomendasi.</p>
      </div>
    )}

    {/* Deep Analysis for more recommendations */}
    {!deepAnalysis && (
      <div className="rounded-lg border-2 border-dashed border-primary/30 p-6 text-center mt-4">
        <Sparkles className="w-8 h-8 text-primary/50 mx-auto mb-2" />
        <h4 className="font-semibold text-sm mb-1">Dapatkan Rekomendasi Paper</h4>
        <p className="text-xs text-muted-foreground mb-3">
          Jalankan analisis mendalam untuk menemukan paper relevan dengan skor relevansi dan penalaran.
        </p>
        <button
          onClick={runDeepAnalysis}
          disabled={deepLoading}
          className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 inline-flex items-center gap-2"
        >
          {deepLoading ? <Loader className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {deepLoading ? 'Menganalisis...' : 'Cari Paper Relevan'}
        </button>
      </div>
    )}

    {deepAnalysis && <DeepAnalysisPanel deepAnalysis={deepAnalysis} />}
  </div>
)

export default RecommendationsTab
