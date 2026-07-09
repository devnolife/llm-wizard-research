import {
  BookOpen, Compass, Lightbulb, Tag, Search, ArrowRight, Sparkles, Loader,
} from 'lucide-react'
import Markdown from '../../common/Markdown'
import DeepAnalysisPanel from './DeepAnalysisPanel'
import { GAP_TYPES, GAP_COLORS, PRIORITY_COLORS } from './constants'

const OverviewTab = ({ data, parsedGaps, parsedRecommendations, deepAnalysis, deepLoading, runDeepAnalysis, setActiveTab }) => (
  <div className="space-y-6">
    {/* Summary Card */}
    <div className="rounded-lg border bg-card p-6">
      <div className="flex items-center gap-2 mb-4">
        <BookOpen className="w-5 h-5 text-primary" />
        <h3 className="text-lg font-semibold">Ringkasan Penelitian</h3>
      </div>
      {data?.summary
        ? <Markdown content={data.summary} />
        : <p className="text-sm text-muted-foreground">Ringkasan tidak tersedia.</p>}
    </div>

    {/* Research Directions — prominent section linking gaps to recommendations */}
    {(parsedGaps.length > 0 || parsedRecommendations.length > 0) && (
      <div className="rounded-lg border-2 border-primary/20 bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5 text-primary" />
            <h3 className="text-lg font-semibold">Arah Penelitian</h3>
          </div>
          <span className="text-xs text-muted-foreground bg-primary/10 text-primary px-2 py-0.5 rounded-full font-medium">
            {parsedRecommendations.length} arah
          </span>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Arah penelitian yang dapat ditindaklanjuti berdasarkan analisis gap sintesis. Setiap arah menjawab gap yang teridentifikasi dalam literatur.
        </p>
        <div className="space-y-3">
          {parsedRecommendations.slice(0, 3).map((rec, idx) => {
            const prio = PRIORITY_COLORS[rec.priority]
            return (
              <div key={idx} className="flex items-start gap-3 p-4 rounded-lg bg-secondary/30 border">
                <div className={`w-8 h-8 rounded-lg ${prio.bg} flex items-center justify-center flex-shrink-0`}>
                  <Lightbulb className={`w-4 h-4 ${prio.text}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {rec.title && <span className="font-medium text-sm">{rec.title}</span>}
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${prio.bg} ${prio.text}`}>
                      {prio.label}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-2">{rec.description}</p>
                  {rec.why && (
                    <p className="text-xs text-muted-foreground/70 mt-1 italic">Why: {rec.why}</p>
                  )}
                </div>
                <button onClick={() => setActiveTab('recommendations')} className="text-xs text-primary hover:underline flex-shrink-0">
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            )
          })}
        </div>
        {parsedRecommendations.length > 3 && (
          <button onClick={() => setActiveTab('recommendations')} className="mt-3 text-xs text-primary hover:underline flex items-center gap-1">
            View all {parsedRecommendations.length} recommendations <ArrowRight className="w-3 h-3" />
          </button>
        )}
      </div>
    )}

    {/* Key Findings Grid */}
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Tag className="w-5 h-5 text-purple-500" />
            <h3 className="font-semibold">Topik Utama</h3>
          </div>
          <button onClick={() => setActiveTab('topics')} className="text-xs text-primary hover:underline flex items-center gap-1">
            View all <ArrowRight className="w-3 h-3" />
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {(data?.topics || []).slice(0, 5).map((topic, idx) => (
            <span key={idx} className="inline-flex items-center px-3 py-1 rounded-full bg-secondary text-xs font-medium">
              {topic.replace(/^\d+[.)]\s*/, '')}
            </span>
          ))}
        </div>
      </div>

      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Search className="w-5 h-5 text-amber-500" />
            <h3 className="font-semibold">Gap Penelitian</h3>
          </div>
          <button onClick={() => setActiveTab('gaps')} className="text-xs text-primary hover:underline flex items-center gap-1">
            View all <ArrowRight className="w-3 h-3" />
          </button>
        </div>
        <div className="space-y-2">
          {parsedGaps.slice(0, 3).map((gap, idx) => {
            const typeKey = gap.type || GAP_TYPES[idx % GAP_TYPES.length]
            const colors = GAP_COLORS[typeKey]
            return (
              <div key={idx} className="flex items-start gap-2 text-sm">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0 mt-0.5 ${colors.bg} ${colors.text}`}>
                  {colors.label.slice(0, 4)}
                </span>
                <span className="text-muted-foreground line-clamp-1">{gap.title || gap.description}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>

    {/* Deep Analysis CTA */}
    {!deepAnalysis && (
      <div className="rounded-lg border bg-card p-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-5 h-5 text-primary" />
            <h3 className="font-semibold">Analisis Mendalam</h3>
          </div>
          <p className="text-sm text-muted-foreground">
            Jalankan pipeline multi-agen untuk indikator gap terstruktur dengan skor kepercayaan, bukti, dan arah penelitian.
          </p>
        </div>
        <button
          onClick={runDeepAnalysis}
          disabled={deepLoading}
          className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2 flex-shrink-0 ml-4"
        >
          {deepLoading ? <Loader className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {deepLoading ? 'Menganalisis...' : 'Jalankan Analisis'}
        </button>
      </div>
    )}

    {deepAnalysis && <DeepAnalysisPanel deepAnalysis={deepAnalysis} />}
  </div>
)

export default OverviewTab
