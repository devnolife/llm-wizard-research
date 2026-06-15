import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  CheckCircle, AlertTriangle, Lightbulb, Map, Download, Loader,
  FileText, Database, Tag, Search, ArrowRight, Clock, Target,
  TrendingUp, BarChart3, BookOpen, Zap, Sparkles, ChevronDown,
  Shield, ExternalLink, Compass, Share2, FileDown
} from 'lucide-react'
import { useToast } from '../../contexts/ToastContext'
import { analysisService } from '../../services/analysisService'
import Term from '../common/Term'
import Markdown from '../common/Markdown'

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

// Parse structured recommendation with title/why/how
const parseStructuredRecommendation = (text) => {
  if (!text) return { title: '', description: text || '', why: '', how: '' }
  const titleMatch = text.match(/^(?:\[([^\]]+)\]:\s*)?(.+?)(?:\s*WHY:|$)/s)
  const whyMatch = text.match(/WHY:\s*(.+?)(?:\s*HOW:|$)/s)
  const howMatch = text.match(/HOW:\s*(.+)/s)

  if (whyMatch || howMatch) {
    return {
      title: (titleMatch?.[1] || '').trim(),
      description: (titleMatch?.[2] || text.split(/\s*WHY:/)[0] || '').trim(),
      why: (whyMatch?.[1] || '').trim(),
      how: (howMatch?.[1] || '').trim(),
    }
  }
  // Fallback: try splitting on colon for "Title: description" format
  const colonIdx = text.indexOf(':')
  if (colonIdx > 0 && colonIdx < 80) {
    return { title: text.slice(0, colonIdx).trim(), description: text.slice(colonIdx + 1).trim(), why: '', how: '' }
  }
  return { title: '', description: text, why: '', how: '' }
}

// Parse structured gap with title/description/type
const parseStructuredGap = (text) => {
  if (!text) return { title: '', description: text || '', type: null }
  const titleMatch = text.match(/TITLE:\s*(.+?)(?:\n|DESCRIPTION:|$)/s)
  const descMatch = text.match(/DESCRIPTION:\s*(.+?)(?:\nTYPE:|$)/s)
  const typeMatch = text.match(/TYPE:\s*(FRAGMENTATION|INCONSISTENCY|INCOMPLETENESS)/i)

  if (titleMatch || typeMatch) {
    return {
      title: (titleMatch?.[1] || '').trim(),
      description: (descMatch?.[1] || text).trim(),
      type: typeMatch?.[1]?.toUpperCase() || null,
    }
  }
  return { title: '', description: text, type: null }
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
    if (firstLine.includes('short') || firstLine.includes('pendek')) { label = 'Short Term'; icon = 'zap' }
    else if (firstLine.includes('medium') || firstLine.includes('menengah')) { label = 'Medium Term'; icon = 'trending' }
    else if (firstLine.includes('long') || firstLine.includes('panjang')) { label = 'Long Term'; icon = 'target' }
    const items = parseNumberedList(lines.slice(1).join('\n'))
    if (items.length > 0 && items[0] !== '') phases.push({ label, icon, items })
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
  { id: 'proposal', label: 'Usulan', icon: Target, desc: 'Usulan penelitian baru hasil sintesis dari jurnal Anda: gap yang ditemukan, judul penelitian yang diusulkan, dan alur penelitiannya — dirangkai jadi satu.' },
  { id: 'overview', label: 'Ringkasan', icon: BarChart3, desc: 'Gambaran umum hasil analisis: jumlah topik, gap, dan rekomendasi yang ditemukan dari paper Anda. Mulai dari sini.' },
  { id: 'topics', label: 'Topik & Analisis', icon: Tag, desc: 'Topik-topik utama yang dibahas dalam paper Anda, hasil ekstraksi otomatis oleh AI dari isi dokumen.' },
  { id: 'gaps', label: 'Gap Penelitian', icon: Search, desc: 'Celah penelitian yang belum terisi — bagian yang belum diteliti, temuan yang saling bertentangan, atau topik yang terpecah-pecah. Ini bisa jadi ide penelitian Anda berikutnya.' },
  { id: 'recommendations', label: 'Rekomendasi', icon: Lightbulb, desc: 'Saran arah penelitian yang bisa Anda ambil berdasarkan gap yang ditemukan, lengkap dengan alasan (WHY) dan cara memulainya (HOW).' },
  { id: 'roadmap', label: 'Peta Jalan', icon: Map, desc: 'Rencana penelitian bertahap: apa yang bisa dikerjakan dalam jangka pendek, menengah, dan panjang.' },
  { id: 'knowledge-graph', label: 'Graf Pengetahuan', icon: Share2, desc: 'Peta visual hubungan antar konsep (metode, domain, temuan) yang diekstrak dari paper. Titik = konsep, garis = hubungan antar konsep.' },
  { id: 'pipeline', label: 'Pipeline', icon: Zap, advanced: true, desc: 'Detail teknis proses analisis di belakang layar: berapa fakta yang diekstrak, hasil validasi aturan, dan skor kepercayaan. Untuk verifikasi kualitas hasil.' },
]

const GAP_TYPES = ['FRAGMENTATION', 'INCONSISTENCY', 'INCOMPLETENESS']
const GAP_COLORS = {
  FRAGMENTATION: { border: 'border-blue-500', bg: 'bg-blue-500/10', text: 'text-blue-600 dark:text-blue-400', label: 'Fragmentasi', desc: 'Paper membahas topik yang sama dari sudut berbeda tanpa integrasi' },
  INCONSISTENCY: { border: 'border-amber-500', bg: 'bg-amber-500/10', text: 'text-amber-600 dark:text-amber-400', label: 'Inkonsistensi', desc: 'Temuan yang bertentangan antar paper' },
  INCOMPLETENESS: { border: 'border-red-500', bg: 'bg-red-500/10', text: 'text-red-600 dark:text-red-400', label: 'Ketidaklengkapan', desc: 'Aspek kritis yang belum tercakup dalam literatur' },
}

const PRIORITY_COLORS = {
  high: { bg: 'bg-red-500/10', text: 'text-red-600 dark:text-red-400', label: 'Prioritas Tinggi' },
  medium: { bg: 'bg-amber-500/10', text: 'text-amber-600 dark:text-amber-400', label: 'Prioritas Sedang' },
  low: { bg: 'bg-green-500/10', text: 'text-green-600 dark:text-green-400', label: 'Prioritas Rendah' },
}

// Ubah verdict rule-engine (PASS/FLAG/REJECT atau ACCEPT/REVIEW/REJECT) jadi label ramah
const verdictLabel = (v) => {
  const key = String(v || '').toUpperCase()
  if (key === 'PASS' || key === 'ACCEPT') return 'Lolos'
  if (key === 'FLAG' || key === 'REVIEW') return 'Perlu Ditinjau'
  if (key === 'REJECT') return 'Ditolak'
  return v || ''
}

const LOADING_STEPS = [
  { label: 'Memproses PDF', threshold: 10 },
  { label: 'Mengekstrak Topik', threshold: 40 },
  { label: 'Menganalisis Penelitian', threshold: 60 },
  { label: 'Mendeteksi Gap', threshold: 75 },
  { label: 'Menghasilkan Insight', threshold: 90 },
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
  const [language, setLanguage] = useState('id')
  const [activeTab, setActiveTab] = useState('proposal')
  const [deepAnalysis, setDeepAnalysis] = useState(null)
  const [deepLoading, setDeepLoading] = useState(false)
  const [expandedRecs, setExpandedRecs] = useState({})
  const [advancedMode, setAdvancedMode] = useState(false)

  useEffect(() => {
    let cancelled = false
    const API_BASE = import.meta.env.VITE_API_URL || ''

    // Try SSE first, fall back to polling
    const trySSE = () => {
      try {
        const es = new EventSource(`${API_BASE}/api/stream/${jobId}`)
        es.onmessage = (event) => {
          if (cancelled) { es.close(); return }
          try {
            const payload = JSON.parse(event.data)
            if (payload.type === 'complete') {
              setData(payload.results)
              setProgress(100)
              setLoading(false)
              toast.success('Analisis selesai!')
              es.close()
            } else if (payload.type === 'error') {
              setError(payload.error || payload.message || 'Analisis gagal')
              setLoading(false)
              es.close()
            } else {
              setProgress(payload.progress || 0)
              setProgressMsg(payload.message || 'Memproses...')
            }
          } catch { /* ignore parse errors */ }
        }
        es.onerror = () => {
          es.close()
          if (!cancelled) fallbackPolling()
        }
        return () => { es.close() }
      } catch {
        fallbackPolling()
      }
    }

    const fallbackPolling = () => {
      const fetchResults = async () => {
        try {
          const response = await analysisService.getAnalysisStatus(jobId, language)
          if (cancelled) return
          if (response.status === 'completed') {
            setData(response.results)
            setProgress(100)
            setLoading(false)
            toast.success('Analisis selesai!')
          } else if (response.status === 'processing') {
            setProgress(response.progress || 0)
            setProgressMsg(response.message || 'Memproses...')
            setTimeout(fetchResults, 2000)
          } else if (response.status === 'failed') {
            setError(response.error || 'Analisis gagal')
            setLoading(false)
          }
        } catch (err) {
          if (cancelled) return
          setError(err.userMessage || 'Gagal memuat hasil')
          setLoading(false)
        }
      }
      fetchResults()
    }

    trySSE()
    return () => { cancelled = true }
  }, [jobId, language])

  const parsedRecommendations = useMemo(() => {
    const recs = data?.recommendations || []
    if (Array.isArray(recs)) {
      return recs.map((rec, idx) => {
        if (typeof rec === 'object' && rec !== null) {
          return {
            title: rec.title || '',
            description: rec.description || '',
            why: rec.why || '',
            how: rec.how || '',
            priority: rec.priority || (idx < 2 ? 'high' : idx < 4 ? 'medium' : 'low'),
            index: idx,
          }
        }
        // Legacy string format fallback
        return { ...parseStructuredRecommendation(String(rec)), priority: idx < 2 ? 'high' : idx < 4 ? 'medium' : 'low', index: idx }
      })
    }
    // Legacy: plain text
    const raw = parseNumberedList(recs)
    return raw.map((text, idx) => ({
      ...parseStructuredRecommendation(text),
      priority: idx < 2 ? 'high' : idx < 4 ? 'medium' : 'low',
      index: idx,
    }))
  }, [data?.recommendations])

  const parsedGaps = useMemo(() => {
    const gaps = data?.gaps || []
    return gaps.map((gap, idx) => {
      if (typeof gap === 'object' && gap !== null) {
        return {
          title: gap.title || `Gap ${idx + 1}`,
          description: gap.description || '',
          type: (gap.type || '').toUpperCase() || null,
          confidence: gap.confidence,
          rule_engine_verdict: gap.rule_engine_verdict,
          evidence: gap.evidence || [],
          suggested_directions: gap.suggested_directions || [],
          index: idx,
          raw: gap,
        }
      }
      // Legacy string format fallback
      return { ...parseStructuredGap(String(gap)), index: idx, raw: gap }
    })
  }, [data?.gaps])

  const parsedRoadmap = useMemo(() => {
    const roadmap = data?.roadmap
    if (Array.isArray(roadmap)) {
      return roadmap.map((phase, idx) => {
        if (typeof phase === 'object' && phase !== null) {
          const phaseName = (phase.phase || `Phase ${idx + 1}`).toLowerCase()
          let label = phase.phase || `Phase ${idx + 1}`
          let icon = 'clock'
          if (phaseName.includes('short') || phaseName.includes('pendek') || phaseName.includes('1')) { label = label || 'Short Term'; icon = 'zap' }
          else if (phaseName.includes('medium') || phaseName.includes('menengah') || phaseName.includes('2')) { label = label || 'Medium Term'; icon = 'trending' }
          else if (phaseName.includes('long') || phaseName.includes('panjang') || phaseName.includes('3')) { label = label || 'Long Term'; icon = 'target' }
          return { label, icon, items: phase.items || [] }
        }
        return { label: `Phase ${idx + 1}`, icon: 'clock', items: [String(phase)] }
      })
    }
    // Legacy: plain text
    return parseRoadmap(roadmap)
  }, [data?.roadmap])

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
    return { papersInfo, duplicateCount, paperGroups, intro: data.proposal_intro || '', primaryGap, primaryRec, flow: parsedRoadmap }
  }, [data, parsedGaps, parsedRecommendations, parsedRoadmap])

  // Jika pindah ke mode Sederhana saat berada di tab khusus-Lanjutan, kembali ke Ringkasan
  useEffect(() => {
    if (!advancedMode && TABS.find(t => t.id === activeTab)?.advanced) {
      setActiveTab('overview')
    }
  }, [advancedMode, activeTab])

  const downloadResults = () => {
    const exportData = { ...data }
    if (deepAnalysis) exportData.deep_analysis = deepAnalysis
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `analysis-${jobId}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const exportPdf = async () => {
    try {
      toast.info('Membuat PDF...')
      const { default: html2canvas } = await import('html2canvas')
      const { default: jsPDF } = await import('jspdf')
      const el = document.getElementById('analysis-content')
      if (!el) return
      const canvas = await html2canvas(el, { scale: 1.5, useCORS: true, logging: false })
      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
      const pageW = pdf.internal.pageSize.getWidth()
      const pageH = pdf.internal.pageSize.getHeight()
      const margin = 10
      const imgW = pageW - margin * 2
      const imgH = (canvas.height * imgW) / canvas.width
      let y = margin
      let remaining = imgH
      while (remaining > 0) {
        if (y !== margin) pdf.addPage()
        pdf.addImage(imgData, 'PNG', margin, y === margin ? margin : -(imgH - remaining), imgW, imgH)
        remaining -= (pageH - margin * 2)
        y = margin
      }
      pdf.save(`analysis-${jobId}.pdf`)
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
        data.topics[0].replace(/^\d+[\.\)]\s*/, ''),
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

  // ── Deep Analysis Panel ────────────────────────────────
  const DeepAnalysisPanel = () => {
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

  // ── Tab Content Components ─────────────────────────────

  const ProposalTab = () => {
    if (!proposal) {
      return (
        <div className="text-center py-12 text-muted-foreground">
          <Target className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">Belum ada usulan penelitian. Jalankan analisis terlebih dahulu.</p>
        </div>
      )
    }
    const { papersInfo, duplicateCount, paperGroups, intro, primaryGap, primaryRec, flow } = proposal
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
              </div>
              {primaryGap.title && <p className="font-medium text-sm mb-1">{primaryGap.title}</p>}
              <Markdown content={primaryGap.description} className="text-foreground" />
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
              </div>
              {primaryRec.title && <p className="font-semibold text-sm mb-1">{primaryRec.title}</p>}
              <Markdown content={primaryRec.description} className="text-foreground" />
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

  const OverviewTab = () => (
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
                {topic.replace(/^\d+[\.\)]\s*/, '')}
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

      {deepAnalysis && <DeepAnalysisPanel />}
    </div>
  )

  const TopicsTab = () => (
    <div className="space-y-4">
      <div className="mb-2">
        <h3 className="text-lg font-semibold">Topik Penelitian yang Diekstrak</h3>
        <p className="text-sm text-muted-foreground">Topik yang teridentifikasi dari analisis perbandingan antar-paper yang Anda unggah.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {(data?.topics || []).map((topic, idx) => (
          <div key={idx} className="rounded-lg border bg-card p-5 hover:border-primary/30 transition-colors">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0 text-sm font-bold">
                {idx + 1}
              </div>
              <h4 className="font-medium text-sm leading-snug">{topic.replace(/^\d+[\.\)]\s*/, '')}</h4>
            </div>
          </div>
        ))}
      </div>
      {data?.summary && (
        <div className="rounded-lg border bg-card p-6 mt-6">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen className="w-5 h-5 text-primary" />
            <h3 className="font-semibold">Ringkasan Analisis Komparatif</h3>
          </div>
          <Markdown content={data.summary} />
        </div>
      )}
    </div>
  )

  const GapsTab = () => (
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

      {deepAnalysis && <DeepAnalysisPanel />}
    </div>
  )

  const RecommendationsTab = () => (
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

      {deepAnalysis && <DeepAnalysisPanel />}
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
          <h3 className="text-lg font-semibold">Peta Jalan Penelitian</h3>
          <p className="text-sm text-muted-foreground">Rencana terstruktur untuk arah penelitian masa depan.</p>
        </div>
        <div className="relative">
          {parsedRoadmap.map((phase, phaseIdx) => {
            const Icon = phaseIcons[phase.icon] || Clock
            const colors = phaseColors[phaseIdx % phaseColors.length]
            return (
              <div key={phaseIdx} className="relative flex gap-6 pb-8 last:pb-0">
                {phaseIdx < parsedRoadmap.length - 1 && (
                  <div className={`absolute left-5 top-10 bottom-0 w-0.5 ${colors.line} opacity-20`} />
                )}
                <div className={`w-10 h-10 rounded-xl ${colors.bg} flex items-center justify-center flex-shrink-0`}>
                  <Icon className={`w-5 h-5 ${colors.text}`} />
                </div>
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
            <p className="text-sm">Belum ada peta jalan.</p>
          </div>
        )}
      </div>
    )
  }

  const PipelineTab = () => {
    const trace = data?.reasoning_trace || []
    const ruleReport = data?.rule_engine_report || {}
    const factStats = data?.fact_table_stats || {}
    const mode = data?.execution_mode || 'unknown'
    const indicators = data?.gap_indicators || []

    const VERDICT_COLORS = {
      PASS: 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/30',
      FLAG: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
      REJECT: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30',
    }

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

  // ── Knowledge Graph Tab ──────────────────────────────────
  const KnowledgeGraphTab = () => {
    const canvasRef = useRef(null)
    const [kgData, setKgData] = useState(null)
    const [kgLoading, setKgLoading] = useState(true)

    useEffect(() => {
      import('../../services/api').then(({ default: api }) => {
        api.get('/api/kg/graph')
          .then(res => setKgData(res.data))
          .catch(() => setKgData({ nodes: [], edges: [], stats: { total_nodes: 0, total_edges: 0 } }))
          .finally(() => setKgLoading(false))
      })
    }, [])

    const drawGraph = useCallback(() => {
      if (!kgData || !canvasRef.current) return
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')
      const { nodes, edges } = kgData
      if (!nodes.length) return

      const W = canvas.parentElement.offsetWidth || 800
      const H = 500
      canvas.width = W * 2
      canvas.height = H * 2
      canvas.style.width = W + 'px'
      canvas.style.height = H + 'px'
      ctx.scale(2, 2)

      const colors = {
        entity: '#3b82f6', paper: '#10b981', METHOD: '#8b5cf6',
        DOMAIN: '#f59e0b', FINDING: '#ef4444', default: '#6b7280'
      }

      const positions = nodes.map((_, i) => {
        const angle = (2 * Math.PI * i) / nodes.length
        const r = Math.min(W, H) * 0.35
        return { x: W / 2 + r * Math.cos(angle), y: H / 2 + r * Math.sin(angle) }
      })
      const nodeMap = {}
      nodes.forEach((n, i) => { nodeMap[n.id] = i })

      ctx.clearRect(0, 0, W, H)

      edges.forEach(e => {
        const si = nodeMap[e.source]
        const ti = nodeMap[e.target]
        if (si === undefined || ti === undefined) return
        ctx.beginPath()
        ctx.moveTo(positions[si].x, positions[si].y)
        ctx.lineTo(positions[ti].x, positions[ti].y)
        ctx.strokeStyle = '#d1d5db'
        ctx.lineWidth = 0.5
        ctx.stroke()
      })

      nodes.forEach((n, i) => {
        const { x, y } = positions[i]
        const type = n.entity_type || n.node_type || 'default'
        const col = colors[type] || colors.default
        ctx.beginPath()
        ctx.arc(x, y, 5, 0, Math.PI * 2)
        ctx.fillStyle = col
        ctx.fill()
        ctx.font = '9px sans-serif'
        ctx.fillStyle = '#374151'
        const label = (n.name || n.title || n.id || '').substring(0, 20)
        ctx.fillText(label, x + 7, y + 3)
      })
    }, [kgData])

    useEffect(() => { drawGraph() }, [drawGraph])

    if (kgLoading) return <div className="flex items-center gap-2 p-8"><Loader className="w-5 h-5 animate-spin" /> Memuat graf...</div>

    return (
      <div className="space-y-6">
        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-lg border bg-card p-4 text-center">
            <p className="text-2xl font-bold">{kgData?.stats?.total_nodes || 0}</p>
            <p className="text-xs text-muted-foreground">Node</p>
          </div>
          <div className="rounded-lg border bg-card p-4 text-center">
            <p className="text-2xl font-bold">{kgData?.stats?.total_edges || 0}</p>
            <p className="text-xs text-muted-foreground">Relasi</p>
          </div>
          <div className="rounded-lg border bg-card p-4 text-center">
            <p className="text-2xl font-bold">{new Set((kgData?.nodes || []).map(n => n.entity_type || n.node_type || 'unknown')).size}</p>
            <p className="text-xs text-muted-foreground">Jenis Entitas</p>
          </div>
        </div>

        <div className="rounded-lg border bg-card overflow-hidden">
          <div className="px-4 py-3 border-b flex items-center gap-2">
            <Share2 className="w-4 h-4" />
            <span className="font-medium text-sm">Visualisasi Graf Pengetahuan</span>
          </div>
          {kgData?.nodes?.length ? (
            <div className="p-2">
              <canvas ref={canvasRef} className="w-full rounded" />
              <div className="flex gap-4 mt-3 px-2 flex-wrap">
                {Object.entries({ paper: '#10b981', METHOD: '#8b5cf6', DOMAIN: '#f59e0b', FINDING: '#ef4444', entity: '#3b82f6' }).map(([k, c]) => (
                  <div key={k} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c }} />
                    {k}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground">
              <p className="text-sm">Belum ada data graf pengetahuan. Jalankan analisis dulu.</p>
            </div>
          )}
        </div>
      </div>
    )
  }

  const tabComponents = { proposal: ProposalTab, overview: OverviewTab, topics: TopicsTab, gaps: GapsTab, recommendations: RecommendationsTab, roadmap: RoadmapTab, 'knowledge-graph': KnowledgeGraphTab, pipeline: PipelineTab }
  const ActiveTabComponent = tabComponents[activeTab]

  // ── Main Render ────────────────────────────────────────
  return (
    <div id="analysis-content" className="w-full px-6 lg:px-10 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <CheckCircle className="w-6 h-6 text-green-500" />
              <h1 className="text-2xl font-bold tracking-tight">Analisis Selesai</h1>
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

      <ActiveTabComponent />
    </div>
  )
}

export default AnalysisResults
