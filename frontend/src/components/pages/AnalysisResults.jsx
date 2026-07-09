import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  CheckCircle, AlertTriangle, Loader, FileText, Database, Tag,
  ArrowRight, Zap, Shield, Download, FileDown,
} from 'lucide-react'
import { useToast } from '../../contexts/ToastContext'
import { analysisService } from '../../services/analysisService'
import Term from '../common/Term'
import useAnalysisJob from '../../hooks/useAnalysisJob'
import { parseRecommendations, parseGaps, parseRoadmapData } from '../../utils/analysisParser'
import { downloadResultsJson, exportElementToPdf } from '../../utils/exportResults'
import { TABS, LOADING_STEPS } from './analysis-tabs/constants'
import ProposalTab from './analysis-tabs/ProposalTab'
import OverviewTab from './analysis-tabs/OverviewTab'
import TopicsTab from './analysis-tabs/TopicsTab'
import GapsTab from './analysis-tabs/GapsTab'
import RecommendationsTab from './analysis-tabs/RecommendationsTab'
import RoadmapTab from './analysis-tabs/RoadmapTab'
import KnowledgeGraphTab from './analysis-tabs/KnowledgeGraphTab'
import PipelineTab from './analysis-tabs/PipelineTab'
import SimpleResultsView from './analysis-tabs/SimpleResultsView'

const AnalysisResults = () => {
  const toast = useToast()
  const navigate = useNavigate()
  const { jobId } = useParams()
  const [language, setLanguage] = useState('id')
  const [activeTab, setActiveTab] = useState('proposal')
  const [deepAnalysis, setDeepAnalysis] = useState(null)
  const [deepLoading, setDeepLoading] = useState(false)
  const [expandedRecs, setExpandedRecs] = useState({})
  const [advancedMode, setAdvancedMode] = useState(false)
  const [showFullAnalysis, setShowFullAnalysis] = useState(false)

  const { loading, progress, progressMsg, data, error } = useAnalysisJob(jobId, language, {
    onComplete: () => toast.success('Analisis selesai!'),
  })

  const parsedRecommendations = useMemo(() => parseRecommendations(data?.recommendations), [data?.recommendations])
  const parsedGaps = useMemo(() => parseGaps(data?.gaps), [data?.gaps])
  const parsedRoadmap = useMemo(() => parseRoadmapData(data?.roadmap), [data?.roadmap])

  const stats = useMemo(() => {
    if (!data) return []
    const base = [
      { label: 'File Diproses', value: data.files_processed || 0, icon: FileText, color: 'text-blue-500' },
      { label: 'Chunk Dianalisis', value: data.total_chunks || 0, icon: Database, color: 'text-green-500' },
      { label: 'Topik Ditemukan', value: data.topics?.length || 0, icon: Tag, color: 'text-purple-500' },
      { label: 'Gap Terdeteksi', value: data.gaps?.length || 0, icon: AlertTriangle, color: 'text-amber-500' },
    ]
    if (data.fact_table_stats?.total_entities) {
      base.push({ label: <>Entitas <Term k="KG">KG</Term></>, value: data.fact_table_stats.total_entities, icon: Database, color: 'text-cyan-500' })
    }
    if (data.fact_table_stats?.total_facts) {
      base.push({ label: <>Fakta <Term k="SPO">SPO</Term></>, value: data.fact_table_stats.total_facts, icon: Shield, color: 'text-indigo-500' })
    }
    return base
  }, [data])

  // Sintesis "Usulan Penelitian Baru": gabungkan jurnal → gap utama → usulan utama → alur
  const proposal = useMemo(() => {
    if (!data) return null
    const papers = data.papers || []
    const papersInfo = data.papers_info || papers.map(t => ({ title: t, already_indexed: false }))
    const duplicateCount = data.duplicate_papers ?? papersInfo.filter(p => p.already_indexed).length
    // Gap utama: confidence tertinggi, fallback ke yang pertama
    const primaryGap = [...parsedGaps].sort((a, b) => (b.confidence || 0) - (a.confidence || 0))[0] || null
    // Usulan utama: prioritas 'high' lebih dulu, fallback ke yang pertama
    const primaryRec = parsedRecommendations.find(r => r.priority === 'high') || parsedRecommendations[0] || null
    if (!primaryGap && !primaryRec) return null
    // Kelompokkan jurnal berdasarkan basis (metode/pendekatan inti)
    const groups = {}
    for (const g of (data.paper_groups || [])) {
      const basis = (g.basis || 'Lainnya').trim()
      if (!groups[basis]) groups[basis] = []
      groups[basis].push(g.title)
    }
    const paperGroups = Object.entries(groups).map(([basis, titles]) => ({ basis, titles }))
    const relatedRefs = data.related_paper_refs || []
    return { papersInfo, duplicateCount, paperGroups, intro: data.proposal_intro || '', primaryGap, primaryRec, flow: parsedRoadmap, relatedRefs }
  }, [data, parsedGaps, parsedRecommendations, parsedRoadmap])

  // Data untuk tampilan ringkas awal: kategori + persamaan dari jurnal terunggah
  const simpleData = useMemo(() => {
    if (!data) return null
    const papersInfo = data.papers_info || (data.papers || []).map(t => ({ title: t, already_indexed: false }))
    const groups = {}
    for (const g of (data.paper_groups || [])) {
      const basis = (g.basis || 'Lainnya').trim()
      if (!groups[basis]) groups[basis] = []
      groups[basis].push(g.title)
    }
    const categories = Object.entries(groups).map(([basis, titles]) => ({ basis, titles }))
    const sim = data.paper_similarity || {}
    // Kekurangan per jurnal: tersurat (ditulis eksplisit) & tersirat (disimpulkan)
    const weaknesses = (data.paper_weaknesses || []).filter(
      w => (w.tersurat?.length || 0) > 0 || (w.tersirat?.length || 0) > 0
    )
    // Usulan utama (indikator) + gap yang dijawab, untuk langkah ④
    const primaryGap = [...parsedGaps].sort((a, b) => (b.confidence || 0) - (a.confidence || 0))[0] || null
    const primaryRec = parsedRecommendations.find(r => r.priority === 'high') || parsedRecommendations[0] || null
    return {
      papersInfo,
      categories,
      keywords: sim.common_keywords || [],
      themes: sim.shared_themes || [],
      summary: sim.summary || '',
      weaknesses,
      primaryGap,
      primaryRec,
      intro: data.proposal_intro || '',
    }
  }, [data, parsedGaps, parsedRecommendations])

  // Jika pindah ke mode Sederhana saat berada di tab khusus-Lanjutan, kembali ke Ringkasan
  useEffect(() => {
    if (!advancedMode && TABS.find(t => t.id === activeTab)?.advanced) {
      setActiveTab('overview')
    }
  }, [advancedMode, activeTab])

  const downloadResults = () => downloadResultsJson(data, deepAnalysis, jobId)

  const exportPdf = async () => {
    try {
      toast.info('Membuat PDF...')
      await exportElementToPdf('analysis-content', `analysis-${jobId}.pdf`)
      toast.success('PDF berhasil diekspor!')
    } catch (e) {
      toast.error('Gagal ekspor PDF: ' + e.message)
    }
  }

  const runDeepAnalysis = async () => {
    if (!data?.topics?.length) return
    setDeepLoading(true)
    try {
      const result = await analysisService.getRecommendations(
        data.topics[0].replace(/^\d+[.)]\s*/, ''),
        { max_results: 10, strategy: 'hybrid' }
      )
      setDeepAnalysis(result)
      toast.success('Analisis mendalam selesai!')
    } catch (err) {
      toast.error('Analisis mendalam gagal: ' + (err.userMessage || err.message))
    } finally {
      setDeepLoading(false)
    }
  }

  // ── Loading State ──────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center px-6">
        <div className="w-full max-w-lg">
          <div className="text-center mb-8">
            <Loader className="w-10 h-10 animate-spin text-primary mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-1">Menganalisis Penelitian Anda</h2>
            <p className="text-sm text-muted-foreground">{progressMsg || 'Menyiapkan analisis...'}</p>
          </div>
          <div className="w-full bg-secondary rounded-full h-2 mb-6">
            <div className="bg-primary h-2 rounded-full transition-all duration-500" style={{ width: `${Math.max(progress, 5)}%` }} />
          </div>
          <div className="space-y-3">
            {LOADING_STEPS.map((step, idx) => {
              const isActive = progress >= step.threshold
              const isCurrent = isActive && (idx === LOADING_STEPS.length - 1 || progress < LOADING_STEPS[idx + 1].threshold)
              return (
                <div key={idx} className={`flex items-center gap-3 text-sm ${isActive ? 'text-foreground' : 'text-muted-foreground/50'}`}>
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${isActive ? 'bg-primary text-primary-foreground' : 'bg-secondary text-muted-foreground'}`}>
                    {isActive ? '✓' : idx + 1}
                  </div>
                  <span className={isCurrent ? 'font-medium' : ''}>{step.label}</span>
                  {isCurrent && <Loader className="w-3 h-3 animate-spin ml-auto" />}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  // ── Error State ────────────────────────────────────────
  if (error) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center px-6">
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-8 text-center max-w-md">
          <AlertTriangle className="w-12 h-12 text-destructive mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">Analisis Gagal</h2>
          <p className="text-sm text-muted-foreground mb-6">{error}</p>
          <button onClick={() => navigate('/')} className="px-6 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors">
            Coba Lagi
          </button>
        </div>
      </div>
    )
  }

  // ── Tampilan Ringkas Awal (default) ────────────────────
  if (!showFullAnalysis) {
    return <SimpleResultsView simpleData={simpleData} data={data} onShowFull={() => setShowFullAnalysis(true)} />
  }

  // ── Main Render ────────────────────────────────────────
  const tabProps = {
    proposal: { proposal, data, setActiveTab },
    overview: { data, parsedGaps, parsedRecommendations, deepAnalysis, deepLoading, runDeepAnalysis, setActiveTab },
    topics: { data },
    gaps: { data, parsedGaps, deepAnalysis, deepLoading, runDeepAnalysis },
    recommendations: { parsedRecommendations, expandedRecs, setExpandedRecs, deepAnalysis, deepLoading, runDeepAnalysis },
    roadmap: { parsedRoadmap },
    'knowledge-graph': {},
    pipeline: { data },
  }
  const tabComponents = { proposal: ProposalTab, overview: OverviewTab, topics: TopicsTab, gaps: GapsTab, recommendations: RecommendationsTab, roadmap: RoadmapTab, 'knowledge-graph': KnowledgeGraphTab, pipeline: PipelineTab }
  const ActiveTabComponent = tabComponents[activeTab]

  return (
    <div id="analysis-content" className="w-full px-6 lg:px-10 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <button
              onClick={() => setShowFullAnalysis(false)}
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-2 transition-colors"
            >
              <ArrowRight className="w-3.5 h-3.5 rotate-180" /> Kembali ke Hasil Awal
            </button>
            <div className="flex items-center gap-3 mb-1">
              <CheckCircle className="w-6 h-6 text-green-500" />
              <h1 className="text-2xl font-bold tracking-tight">Detail Analisis</h1>
            </div>
            <p className="text-sm text-muted-foreground">
              Insight penelitian berbasis AI dari paper yang Anda unggah
              {data?.execution_mode && (
                <span className={`ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${data.execution_mode === 'langgraph' ? 'bg-green-500/10 text-green-600 dark:text-green-400' :
                  data.execution_mode === 'sequential' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400' :
                    'bg-secondary text-muted-foreground'
                  }`}>
                  <Zap className="w-3 h-3" />{data.execution_mode}
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border overflow-hidden">
              <button onClick={() => setAdvancedMode(false)} title="Tampilan ringkas tanpa detail teknis" className={`px-3 py-1.5 text-xs font-medium transition-colors ${!advancedMode ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:bg-secondary/50'}`}>Sederhana</button>
              <button onClick={() => setAdvancedMode(true)} title="Tampilkan tab teknis (Pipeline) untuk verifikasi" className={`px-3 py-1.5 text-xs font-medium transition-colors border-l ${advancedMode ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:bg-secondary/50'}`}>Lanjutan</button>
            </div>
            <div className="flex rounded-lg border overflow-hidden">
              <button onClick={() => setLanguage('en')} className={`px-3 py-1.5 text-xs font-medium transition-colors ${language === 'en' ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:bg-secondary/50'}`}>EN</button>
              <button onClick={() => setLanguage('id')} className={`px-3 py-1.5 text-xs font-medium transition-colors border-l ${language === 'id' ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:bg-secondary/50'}`}>ID</button>
            </div>
            <button onClick={downloadResults} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium hover:bg-secondary transition-colors">
              <Download className="w-3.5 h-3.5" /> JSON
            </button>
            <button onClick={exportPdf} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium hover:bg-secondary transition-colors">
              <FileDown className="w-3.5 h-3.5" /> PDF
            </button>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className={`grid gap-4 mb-8 ${stats.length <= 4 ? 'grid-cols-2 md:grid-cols-4' : 'grid-cols-2 md:grid-cols-3 lg:grid-cols-6'}`}>
        {stats.map((stat, idx) => (
          <div key={idx} className="rounded-lg border bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center">
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <div>
                <p className="text-2xl font-bold">{stat.value}</p>
                <p className="text-xs text-muted-foreground">{stat.label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Tab Navigation */}
      <div className="border-b mb-4">
        <div className="flex gap-1 -mb-px overflow-x-auto">
          {TABS.filter(tab => advancedMode || !tab.advanced).map(tab => {
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                title={tab.desc}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${isActive ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
                  }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Tab Description Banner */}
      {(() => {
        const tab = TABS.find(t => t.id === activeTab)
        return tab?.desc ? (
          <div className="flex items-start gap-2.5 mb-6 px-4 py-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
            <tab.icon className="w-4 h-4 mt-0.5 text-blue-500 flex-shrink-0" />
            <p className="text-sm text-muted-foreground">{tab.desc}</p>
          </div>
        ) : null
      })()}

      <ActiveTabComponent {...tabProps[activeTab]} />
    </div>
  )
}

export default AnalysisResults
