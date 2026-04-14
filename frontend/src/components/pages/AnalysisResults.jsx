import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  CheckCircle, AlertTriangle, Lightbulb, Map, Download, Loader,
  FileText, Database, Tag, Search, ArrowRight, Clock, Target,
  TrendingUp, BarChart3, BookOpen, Layers, Zap
} from 'lucide-react'
import { useToast } from '../../contexts/ToastContext'
import { analysisService } from '../../services/analysisService'

// Parse numbered text block into structured items
const parseNumberedList = (text) => {
  if (!text) return []
  if (Array.isArray(text)) return text
  const lines = text.split('\n').filter(l => l.trim())
  const items = []
  let current = ''
  for (const line of lines) {
    if (/^\d+[\.\)]\s/.test(line.trim())) {
      if (current) items.push(current.trim())
      current = line.trim().replace(/^\d+[\.\)]\s*/, '')
    } else if (line.trim().startsWith('-') || line.trim().startsWith('•')) {
      if (current) items.push(current.trim())
      current = line.trim().replace(/^[-•]\s*/, '')
    } else {
      current += ' ' + line.trim()
    }
  }
  if (current) items.push(current.trim())
  return items.length > 0 ? items : [text]
}

// Parse roadmap into phases
const parseRoadmap = (text) => {
  if (!text) return []
  const phases = []
  const sections = text.split(/(?=(?:short|medium|long|phase|tahap|jangka)\s*[-:]?\s*(?:term|pendek|menengah|panjang)?)/i)

  for (const section of sections) {
    if (!section.trim()) continue
    const lines = section.trim().split('\n').filter(l => l.trim())
    if (lines.length === 0) continue

    let label = 'Phase'
    let icon = 'clock'
    const firstLine = lines[0].toLowerCase()
    if (firstLine.includes('short') || firstLine.includes('pendek')) {
      label = 'Short Term'
      icon = 'zap'
    } else if (firstLine.includes('medium') || firstLine.includes('menengah')) {
      label = 'Medium Term'
      icon = 'trending'
    } else if (firstLine.includes('long') || firstLine.includes('panjang')) {
      label = 'Long Term'
      icon = 'target'
    }

    const items = parseNumberedList(lines.slice(1).join('\n'))
    if (items.length > 0 && items[0] !== '') {
      phases.push({ label, icon, items })
    }
  }

  if (phases.length === 0) {
    const items = parseNumberedList(text)
    if (items.length > 1) {
      const third = Math.ceil(items.length / 3)
      phases.push({ label: 'Short Term', icon: 'zap', items: items.slice(0, third) })
      phases.push({ label: 'Medium Term', icon: 'trending', items: items.slice(third, third * 2) })
      phases.push({ label: 'Long Term', icon: 'target', items: items.slice(third * 2) })
    } else {
      phases.push({ label: 'Research Plan', icon: 'clock', items })
    }
  }
  return phases
}

const TABS = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'topics', label: 'Topics & Analysis', icon: Tag },
  { id: 'gaps', label: 'Research Gaps', icon: Search },
  { id: 'recommendations', label: 'Recommendations', icon: Lightbulb },
  { id: 'roadmap', label: 'Roadmap', icon: Map },
]

const GAP_TYPES = ['FRAGMENTATION', 'INCONSISTENCY', 'INCOMPLETENESS']
const GAP_COLORS = {
  FRAGMENTATION: { border: 'border-blue-500', bg: 'bg-blue-500/10', text: 'text-blue-600 dark:text-blue-400', label: 'Fragmentation' },
  INCONSISTENCY: { border: 'border-amber-500', bg: 'bg-amber-500/10', text: 'text-amber-600 dark:text-amber-400', label: 'Inconsistency' },
  INCOMPLETENESS: { border: 'border-red-500', bg: 'bg-red-500/10', text: 'text-red-600 dark:text-red-400', label: 'Incompleteness' },
}

const LOADING_STEPS = [
  { label: 'Processing PDFs', threshold: 10 },
  { label: 'Extracting Topics', threshold: 40 },
  { label: 'Analyzing Research', threshold: 60 },
  { label: 'Detecting Gaps', threshold: 75 },
  { label: 'Generating Insights', threshold: 90 },
]

const AnalysisResults = () => {
  const toast = useToast()
  const navigate = useNavigate()
  const { jobId } = useParams()
  const [loading, setLoading] = useState(true)
  const [progress, setProgress] = useState(0)
  const [progressMsg, setProgressMsg] = useState('')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [language, setLanguage] = useState('en')
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    let cancelled = false
    const fetchResults = async () => {
      try {
        const response = await analysisService.getAnalysisStatus(jobId, language)
        if (cancelled) return
        if (response.status === 'completed') {
          setData(response.results)
          setProgress(100)
          setLoading(false)
          toast.success('Analysis complete!')
        } else if (response.status === 'processing') {
          setProgress(response.progress || 0)
          setProgressMsg(response.message || 'Processing...')
          setTimeout(fetchResults, 2000)
        } else if (response.status === 'failed') {
          setError(response.error || 'Analysis failed')
          setLoading(false)
        }
      } catch (err) {
        if (cancelled) return
        setError(err.userMessage || 'Failed to fetch results')
        setLoading(false)
      }
    }
    fetchResults()
    return () => { cancelled = true }
  }, [jobId, language])

  const parsedRecommendations = useMemo(() => parseNumberedList(data?.recommendations), [data?.recommendations])
  const parsedRoadmap = useMemo(() => parseRoadmap(data?.roadmap), [data?.roadmap])

  const stats = useMemo(() => {
    if (!data) return []
    return [
      { label: 'Files Processed', value: data.files_processed || 0, icon: FileText, color: 'text-blue-500' },
      { label: 'Chunks Analyzed', value: data.total_chunks || 0, icon: Database, color: 'text-green-500' },
      { label: 'Topics Found', value: data.topics?.length || 0, icon: Tag, color: 'text-purple-500' },
      { label: 'Gaps Detected', value: data.gaps?.length || 0, icon: AlertTriangle, color: 'text-amber-500' },
    ]
  }, [data])

  const downloadResults = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `analysis-${jobId}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  // ── Loading State ──────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center px-6">
        <div className="w-full max-w-lg">
          <div className="text-center mb-8">
            <Loader className="w-10 h-10 animate-spin text-primary mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-1">Analyzing Your Research</h2>
            <p className="text-sm text-muted-foreground">{progressMsg || 'Preparing analysis pipeline...'}</p>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-secondary rounded-full h-2 mb-6">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-500"
              style={{ width: `${Math.max(progress, 5)}%` }}
            />
          </div>

          {/* Steps */}
          <div className="space-y-3">
            {LOADING_STEPS.map((step, idx) => {
              const isActive = progress >= step.threshold
              const isCurrent = progress >= step.threshold && (idx === LOADING_STEPS.length - 1 || progress < LOADING_STEPS[idx + 1].threshold)
              return (
                <div key={idx} className={`flex items-center gap-3 text-sm ${isActive ? 'text-foreground' : 'text-muted-foreground/50'}`}>
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                    isActive ? 'bg-primary text-primary-foreground' : 'bg-secondary text-muted-foreground'
                  }`}>
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
          <h2 className="text-xl font-bold mb-2">Analysis Failed</h2>
          <p className="text-sm text-muted-foreground mb-6">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  // ── Tab Content Components ─────────────────────────────

  const OverviewTab = () => (
    <div className="space-y-6">
      {/* Summary Card */}
      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <BookOpen className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold">Research Summary</h3>
        </div>
        <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-wrap">
          {data?.summary || 'No summary available.'}
        </p>
      </div>

      {/* Key Findings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Topics Preview */}
        <div className="rounded-lg border bg-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Tag className="w-5 h-5 text-purple-500" />
              <h3 className="font-semibold">Key Topics</h3>
            </div>
            <button onClick={() => setActiveTab('topics')} className="text-xs text-primary hover:underline flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {(data?.topics || []).slice(0, 5).map((topic, idx) => (
              <span key={idx} className="inline-flex items-center px-3 py-1 rounded-full bg-secondary text-xs font-medium">
                {topic.replace(/^\d+[\.\)]\s*/, '')}
              </span>
            ))}
          </div>
        </div>

        {/* Gaps Preview */}
        <div className="rounded-lg border bg-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Search className="w-5 h-5 text-amber-500" />
              <h3 className="font-semibold">Research Gaps</h3>
            </div>
            <button onClick={() => setActiveTab('gaps')} className="text-xs text-primary hover:underline flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="space-y-2">
            {(data?.gaps || []).slice(0, 3).map((gap, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm">
                <span className="w-5 h-5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center flex-shrink-0 text-xs font-bold mt-0.5">
                  {idx + 1}
                </span>
                <span className="text-muted-foreground line-clamp-2">{gap}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recommendations Preview */}
      {parsedRecommendations.length > 0 && (
        <div className="rounded-lg border bg-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-green-500" />
              <h3 className="font-semibold">Top Recommendations</h3>
            </div>
            <button onClick={() => setActiveTab('recommendations')} className="text-xs text-primary hover:underline flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="space-y-2">
            {parsedRecommendations.slice(0, 3).map((rec, idx) => (
              <div key={idx} className="flex items-start gap-3 p-3 rounded-md bg-secondary/30">
                <Zap className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                <span className="text-sm text-muted-foreground">{rec}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )

  const TopicsTab = () => (
    <div className="space-y-4">
      <div className="mb-2">
        <h3 className="text-lg font-semibold">Extracted Research Topics</h3>
        <p className="text-sm text-muted-foreground">Topics identified from comparative analysis of your uploaded papers.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {(data?.topics || []).map((topic, idx) => (
          <div key={idx} className="rounded-lg border bg-card p-5 hover:border-primary/30 transition-colors">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0 text-sm font-bold">
                {idx + 1}
              </div>
              <div>
                <h4 className="font-medium text-sm leading-snug">{topic.replace(/^\d+[\.\)]\s*/, '')}</h4>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary Section */}
      {data?.summary && (
        <div className="rounded-lg border bg-card p-6 mt-6">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen className="w-5 h-5 text-primary" />
            <h3 className="font-semibold">Comparative Analysis Summary</h3>
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-wrap">{data.summary}</p>
        </div>
      )}
    </div>
  )

  const GapsTab = () => {
    const gaps = data?.gaps || []
    return (
      <div className="space-y-4">
        <div className="mb-2">
          <h3 className="text-lg font-semibold">Synthesis Gap Detection</h3>
          <p className="text-sm text-muted-foreground">
            Research gaps identified through cross-paper comparative analysis. Based on Cooper (1998) indicators:
            Fragmentation, Inconsistency, and Incompleteness.
          </p>
        </div>

        {/* Gap Type Legend */}
        <div className="flex flex-wrap gap-3 p-4 rounded-lg bg-secondary/30 border">
          {GAP_TYPES.map(type => {
            const c = GAP_COLORS[type]
            return (
              <div key={type} className="flex items-center gap-2 text-xs">
                <div className={`w-3 h-3 rounded-sm ${c.bg} ${c.border} border`} />
                <span className="text-muted-foreground">{c.label}</span>
              </div>
            )
          })}
        </div>

        {/* Gap Cards */}
        <div className="space-y-4">
          {gaps.map((gap, idx) => {
            const typeKey = GAP_TYPES[idx % GAP_TYPES.length]
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
                    </div>
                  </div>
                  <p className="text-sm text-foreground leading-relaxed">{gap}</p>
                </div>
              </div>
            )
          })}
        </div>

        {gaps.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <Search className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm">No research gaps detected.</p>
          </div>
        )}
      </div>
    )
  }

  const RecommendationsTab = () => (
    <div className="space-y-4">
      <div className="mb-2">
        <h3 className="text-lg font-semibold">Research Recommendations</h3>
        <p className="text-sm text-muted-foreground">Actionable research directions based on detected gaps and analysis.</p>
      </div>

      <div className="space-y-3">
        {parsedRecommendations.map((rec, idx) => (
          <div key={idx} className="rounded-lg border bg-card p-5 hover:border-primary/30 transition-colors">
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-lg bg-green-500/10 text-green-600 dark:text-green-400 flex items-center justify-center flex-shrink-0 text-sm font-bold">
                {idx + 1}
              </div>
              <div className="flex-1">
                <p className="text-sm text-foreground leading-relaxed">{rec}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {parsedRecommendations.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <Lightbulb className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No recommendations available.</p>
        </div>
      )}
    </div>
  )

  const RoadmapTab = () => {
    const phaseIcons = { zap: Zap, trending: TrendingUp, target: Target, clock: Clock }
    const phaseColors = [
      { bg: 'bg-blue-500/10', text: 'text-blue-600 dark:text-blue-400', line: 'bg-blue-500' },
      { bg: 'bg-purple-500/10', text: 'text-purple-600 dark:text-purple-400', line: 'bg-purple-500' },
      { bg: 'bg-emerald-500/10', text: 'text-emerald-600 dark:text-emerald-400', line: 'bg-emerald-500' },
    ]

    return (
      <div className="space-y-4">
        <div className="mb-2">
          <h3 className="text-lg font-semibold">Research Roadmap</h3>
          <p className="text-sm text-muted-foreground">Structured plan for future research directions.</p>
        </div>

        <div className="relative">
          {parsedRoadmap.map((phase, phaseIdx) => {
            const Icon = phaseIcons[phase.icon] || Clock
            const colors = phaseColors[phaseIdx % phaseColors.length]
            return (
              <div key={phaseIdx} className="relative flex gap-6 pb-8 last:pb-0">
                {/* Timeline line */}
                {phaseIdx < parsedRoadmap.length - 1 && (
                  <div className={`absolute left-5 top-10 bottom-0 w-0.5 ${colors.line} opacity-20`} />
                )}
                {/* Icon */}
                <div className={`w-10 h-10 rounded-xl ${colors.bg} flex items-center justify-center flex-shrink-0`}>
                  <Icon className={`w-5 h-5 ${colors.text}`} />
                </div>
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold mb-3">{phase.label}</h4>
                  <div className="space-y-2">
                    {phase.items.map((item, idx) => (
                      <div key={idx} className="flex items-start gap-2 p-3 rounded-md bg-secondary/30">
                        <ArrowRight className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                        <span className="text-sm text-muted-foreground">{item}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {parsedRoadmap.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <Map className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm">No roadmap available.</p>
          </div>
        )}
      </div>
    )
  }

  const tabComponents = {
    overview: OverviewTab,
    topics: TopicsTab,
    gaps: GapsTab,
    recommendations: RecommendationsTab,
    roadmap: RoadmapTab,
  }

  const ActiveTabComponent = tabComponents[activeTab]

  // ── Main Render ────────────────────────────────────────
  return (
    <div className="w-full px-6 lg:px-10 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <CheckCircle className="w-6 h-6 text-green-500" />
              <h1 className="text-2xl font-bold tracking-tight">Analysis Complete</h1>
            </div>
            <p className="text-sm text-muted-foreground">AI-powered research insights from your uploaded papers</p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border overflow-hidden">
              <button
                onClick={() => setLanguage('en')}
                className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                  language === 'en' ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:bg-secondary/50'
                }`}
              >EN</button>
              <button
                onClick={() => setLanguage('id')}
                className={`px-3 py-1.5 text-xs font-medium transition-colors border-l ${
                  language === 'id' ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:bg-secondary/50'
                }`}
              >ID</button>
            </div>
            <button
              onClick={downloadResults}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium hover:bg-secondary transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Export
            </button>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
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
      <div className="border-b mb-6">
        <div className="flex gap-1 -mb-px overflow-x-auto">
          {TABS.map(tab => {
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  isActive
                    ? 'border-primary text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Tab Content */}
      <ActiveTabComponent />
    </div>
  )
}

export default AnalysisResults
