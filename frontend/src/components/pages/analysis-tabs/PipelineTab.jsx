import { Zap, Shield, AlertTriangle, Clock, ArrowRight, TrendingUp } from 'lucide-react'
import Term from '../../common/Term'
import { verdictLabel } from '../../../utils/analysisParser'
import { GAP_COLORS } from './constants'

const VERDICT_COLORS = {
  PASS: 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/30',
  FLAG: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
  REJECT: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30',
}

const PipelineTab = ({ data }) => {
  const trace = data?.reasoning_trace || []
  const ruleReport = data?.rule_engine_report || {}
  const factStats = data?.fact_table_stats || {}
  const mode = data?.execution_mode || 'unknown'
  const indicators = data?.gap_indicators || []

  return (
    <div className="space-y-6">
      <div className="mb-2">
        <h3 className="text-lg font-semibold">Pipeline <Term k="Neuro-Simbolik">Neuro-Simbolik</Term></h3>
        <p className="text-sm text-muted-foreground">
          Rincian eksekusi dari siklus agen Observasi → Berpikir → Aksi → Evaluasi.
        </p>
      </div>

      {/* Execution Mode Banner */}
      <div className={`rounded-lg border p-4 flex items-center gap-3 ${mode === 'langgraph' ? 'border-green-500/30 bg-green-500/5' :
        mode === 'sequential' ? 'border-amber-500/30 bg-amber-500/5' :
          'border-border bg-card'
        }`}>
        <Zap className={`w-5 h-5 ${mode === 'langgraph' ? 'text-green-500' : mode === 'sequential' ? 'text-amber-500' : 'text-muted-foreground'
          }`} />
        <div>
          <p className="text-sm font-medium">
            Mode Eksekusi: <span className="font-bold uppercase">{mode}</span>
          </p>
          <p className="text-xs text-muted-foreground">
            {mode === 'langgraph' ? 'LangGraph StateGraph penuh dengan percabangan kondisional dan loop kritik-mandiri.' :
              mode === 'sequential' ? 'Pipeline cadangan berurutan (LangGraph tidak tersedia).' :
                'Cadangan LLM-saja (koordinator tidak tersedia).'}
          </p>
        </div>
      </div>

      {/* Dashboard Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-lg border bg-card p-4 text-center">
          <p className="text-2xl font-bold text-cyan-500">{factStats.total_entities || 0}</p>
          <p className="text-xs text-muted-foreground">Entitas <Term k="KG">KG</Term></p>
        </div>
        <div className="rounded-lg border bg-card p-4 text-center">
          <p className="text-2xl font-bold text-indigo-500">{factStats.total_facts || 0}</p>
          <p className="text-xs text-muted-foreground">Fakta <Term k="SPO">SPO</Term></p>
        </div>
        <div className="rounded-lg border bg-card p-4 text-center">
          <p className="text-2xl font-bold text-green-500">{ruleReport.passed || 0}</p>
          <p className="text-xs text-muted-foreground">Aturan Lolos</p>
        </div>
        <div className="rounded-lg border bg-card p-4 text-center">
          <p className="text-2xl font-bold text-amber-500">{ruleReport.flagged || 0}</p>
          <p className="text-xs text-muted-foreground">Aturan Ditandai</p>
        </div>
      </div>

      {/* Rule Engine Report */}
      {(ruleReport.total > 0) && (
        <div className="rounded-lg border bg-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-primary" />
            <h4 className="font-semibold">Validasi <Term k="Rule Engine">Rule Engine</Term></h4>
          </div>
          <div className="flex items-center gap-6 mb-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-sm">{ruleReport.passed || 0} Lolos</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-amber-500" />
              <span className="text-sm">{ruleReport.flagged || 0} Ditandai</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span className="text-sm">{ruleReport.rejected || 0} Ditolak</span>
            </div>
          </div>
          <div className="w-full bg-secondary rounded-full h-2.5 flex overflow-hidden">
            {ruleReport.total > 0 && (
              <>
                <div className="bg-green-500 h-2.5" style={{ width: `${(ruleReport.passed / ruleReport.total) * 100}%` }} />
                <div className="bg-amber-500 h-2.5" style={{ width: `${(ruleReport.flagged / ruleReport.total) * 100}%` }} />
                <div className="bg-red-500 h-2.5" style={{ width: `${(ruleReport.rejected / ruleReport.total) * 100}%` }} />
              </>
            )}
          </div>
        </div>
      )}

      {/* Gap Indicators with Verdicts */}
      {indicators.length > 0 && (
        <div className="rounded-lg border bg-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <h4 className="font-semibold">Indikator Gap Tervalidasi</h4>
            <span className="ml-auto text-xs text-muted-foreground bg-secondary px-2 py-0.5 rounded-full">
              {indicators.length} indikator
            </span>
          </div>
          <div className="space-y-3">
            {indicators.map((gi, idx) => {
              const verdict = gi.rule_engine_verdict || 'PASS'
              const vColors = VERDICT_COLORS[verdict] || VERDICT_COLORS.PASS
              const typeKey = (gi.type || gi.indicator_type || '').toUpperCase()
              const gapColor = GAP_COLORS[typeKey] || GAP_COLORS.FRAGMENTATION
              return (
                <div key={idx} className={`rounded-lg border p-4 border-l-4 ${gapColor.border}`}>
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${gapColor.bg} ${gapColor.text}`}>
                      {gapColor.label}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${vColors}`}>
                      <Shield className="w-3 h-3 inline mr-1" />{verdictLabel(verdict)}
                    </span>
                    {gi.confidence > 0 && (
                      <span className="text-xs text-muted-foreground">
                        {(gi.confidence * 100).toFixed(0)}% keyakinan
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{gi.description || gi.title}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Reasoning Trace */}
      {trace.length > 0 && (
        <div className="rounded-lg border bg-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-5 h-5 text-primary" />
            <h4 className="font-semibold">Jejak Penalaran</h4>
          </div>
          <div className="space-y-4">
            {trace.map((entry, idx) => {
              const phaseColors = {
                observe: 'border-blue-500 bg-blue-500/10',
                think: 'border-purple-500 bg-purple-500/10',
                act: 'border-green-500 bg-green-500/10',
                evaluate: 'border-amber-500 bg-amber-500/10',
              }
              const pColor = phaseColors[entry.phase] || 'border-border bg-secondary/30'
              return (
                <div key={idx} className={`rounded-lg border-l-4 p-4 ${pColor}`}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-semibold capitalize">{entry.phase}</span>
                    {entry.iteration !== undefined && (
                      <span className="text-xs text-muted-foreground">Iterasi {entry.iteration}</span>
                    )}
                    {entry.timestamp && (
                      <span className="text-xs text-muted-foreground ml-auto">
                        {new Date(entry.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                  {entry.actions?.length > 0 && (
                    <ul className="space-y-1">
                      {entry.actions.map((action, ai) => (
                        <li key={ai} className="text-xs text-muted-foreground flex items-start gap-2">
                          <ArrowRight className="w-3 h-3 flex-shrink-0 mt-0.5" />
                          <span>{typeof action === 'string' ? action : JSON.stringify(action)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {entry.error && (
                    <p className="text-xs text-red-500 mt-1">Galat: {entry.error}</p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {trace.length === 0 && !ruleReport.total && indicators.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <Zap className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">Belum ada data pipeline. Analisis mungkin memakai mode LLM-saja.</p>
        </div>
      )}

      {/* Evaluation Metrics */}
      {data?.eval_metrics && (
        <div className="rounded-lg border bg-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-primary" />
            <h4 className="font-semibold">Metrik Evaluasi</h4>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            {[
              { label: 'Skor Pipeline', value: data.eval_metrics.pipeline_score, color: 'text-green-500' },
              { label: 'Cakupan Topik', value: data.eval_metrics.topic_coverage, color: 'text-blue-500' },
              { label: 'Kelengkapan Rekomendasi', value: data.eval_metrics.recommendation_completeness, color: 'text-purple-500' },
              { label: 'Kepadatan KG', value: data.eval_metrics.kg_density, color: 'text-amber-500' },
            ].map((m, i) => (
              <div key={i} className="text-center">
                <p className={`text-2xl font-bold ${m.color}`}>{(m.value * 100).toFixed(0)}%</p>
                <p className="text-xs text-muted-foreground">{m.label}</p>
                <div className="mt-1 h-1.5 rounded-full bg-secondary overflow-hidden">
                  <div className="h-full rounded-full bg-current transition-all" style={{ width: `${Math.min(m.value * 100, 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground border-t pt-3">
            <span>Topik: {data.eval_metrics.total_topics}</span>
            <span>Gap: {data.eval_metrics.total_gaps}</span>
            <span>Rekomendasi: {data.eval_metrics.total_recommendations}</span>
            <span>Fakta: {data.eval_metrics.total_facts}</span>
            <span>Entitas: {data.eval_metrics.total_entities}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default PipelineTab
