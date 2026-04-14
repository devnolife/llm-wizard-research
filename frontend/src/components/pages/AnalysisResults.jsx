import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { CheckCircle, AlertTriangle, Lightbulb, Map, ChevronDown, Download, Loader } from 'lucide-react'
import { useDarkMode } from '../../contexts/DarkModeContext'
import { useToast } from '../../contexts/ToastContext'
import { analysisService } from '../../services/analysisService'

const AnalysisResults = () => {
  const { darkMode } = useDarkMode()
  const toast = useToast()
  const navigate = useNavigate()
  const { jobId } = useParams()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [language, setLanguage] = useState('en')
  const [expandedSections, setExpandedSections] = useState({
    topics: true,
    summary: true,
    gaps: true,
    recommendations: true,
    roadmap: true
  })

  useEffect(() => {
    let cancelled = false

    const fetchResults = async () => {
      try {
        const response = await analysisService.getAnalysisStatus(jobId, language)
        if (cancelled) return

        if (response.status === 'completed') {
          setData(response.results)
          setLoading(false)
          toast.success('Analysis complete!')
        } else if (response.status === 'processing') {
          setTimeout(fetchResults, 3000)
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

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  const downloadResults = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `analysis-${jobId}.json`
    a.click()
  }

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4">
        <Loader className="w-8 h-8 animate-spin text-muted-foreground" />
        <div className="text-center">
          <h3 className="text-xl font-semibold mb-1">Analyzing Your Research</h3>
          <p className="text-sm text-muted-foreground">Please wait while we process your documents...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto max-w-2xl px-6 py-12 text-center">
        <AlertTriangle className="w-12 h-12 text-destructive mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Analysis Failed</h2>
        <p className="text-muted-foreground mb-6">{error}</p>
        <button
          onClick={() => navigate('/')}
          className="px-6 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
        >
          Try Again
        </button>
      </div>
    )
  }

  const SectionCard = ({ title, icon: Icon, children, section }) => (
    <div className="rounded-lg border bg-card overflow-hidden">
      <button
        onClick={() => toggleSection(section)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-secondary/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon className="w-5 h-5 text-muted-foreground" />
          <h3 className="text-lg font-semibold">{title}</h3>
        </div>
        <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${expandedSections[section] ? 'rotate-180' : ''}`} />
      </button>
      {expandedSections[section] && (
        <div className="px-6 pb-6 text-sm leading-relaxed">{children}</div>
      )}
    </div>
  )

  return (
    <div className="container mx-auto max-w-4xl px-6 py-12">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <CheckCircle className="w-6 h-6 text-green-500" />
          <h1 className="text-3xl font-bold tracking-tight">Analysis Complete</h1>
        </div>
        <p className="text-muted-foreground">Here are your AI-generated insights</p>

        {/* Language Toggle + Download */}
        <div className="flex items-center gap-3 mt-6 flex-wrap">
          <div className="flex rounded-lg border overflow-hidden">
            <button
              onClick={() => setLanguage('en')}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                language === 'en' ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:bg-secondary/50'
              }`}
            >
              English
            </button>
            <button
              onClick={() => setLanguage('id')}
              className={`px-4 py-2 text-sm font-medium transition-colors border-l ${
                language === 'id' ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:bg-secondary/50'
              }`}
            >
              Bahasa Indonesia
            </button>
          </div>
          <button
            onClick={downloadResults}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium hover:bg-secondary transition-colors"
          >
            <Download className="w-4 h-4" />
            Download JSON
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="space-y-4">
        {data?.topics && (
          <SectionCard title="Extracted Topics" icon={CheckCircle} section="topics">
            <div className="grid gap-2 md:grid-cols-2">
              {data.topics.map((topic, idx) => (
                <div key={idx} className="flex items-start gap-2 p-3 rounded-md bg-secondary/50">
                  <span className="text-muted-foreground text-xs font-mono mt-0.5">{idx + 1}.</span>
                  <span className="font-medium text-sm">{topic}</span>
                </div>
              ))}
            </div>
          </SectionCard>
        )}

        {data?.summary && (
          <SectionCard title="Research Summary" icon={CheckCircle} section="summary">
            <p className="whitespace-pre-wrap text-muted-foreground">{data.summary}</p>
          </SectionCard>
        )}

        {data?.gaps && data.gaps.length > 0 && (
          <SectionCard title="Research Gaps" icon={AlertTriangle} section="gaps">
            <div className="space-y-3">
              {data.gaps.map((gap, idx) => (
                <div key={idx} className="flex gap-3 p-4 rounded-md border-l-2 border-yellow-500 bg-secondary/30">
                  <span className="flex-shrink-0 w-6 h-6 rounded text-xs font-bold flex items-center justify-center bg-yellow-500/10 text-yellow-600 dark:text-yellow-400">
                    {idx + 1}
                  </span>
                  <p className="text-sm text-muted-foreground">{gap}</p>
                </div>
              ))}
            </div>
          </SectionCard>
        )}

        {data?.recommendations && (
          <SectionCard title="Recommendations" icon={Lightbulb} section="recommendations">
            <p className="whitespace-pre-wrap text-muted-foreground">{data.recommendations}</p>
          </SectionCard>
        )}

        {data?.roadmap && (
          <SectionCard title="Research Roadmap" icon={Map} section="roadmap">
            <p className="whitespace-pre-wrap text-muted-foreground">{data.roadmap}</p>
          </SectionCard>
        )}
      </div>
    </div>
  )
}

export default AnalysisResults
