import { useState, useEffect } from 'react'
import { analysisService } from '../services/analysisService'

// Track analysis job progress via SSE with polling fallback.
// Properly cleans up EventSource + timers on unmount / dependency change (fixes P2).
const useAnalysisJob = (jobId, language, { onComplete } = {}) => {
  const [loading, setLoading] = useState(true)
  const [progress, setProgress] = useState(0)
  const [progressMsg, setProgressMsg] = useState('')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    let es = null
    let timerId = null
    const API_BASE = import.meta.env.VITE_API_URL || ''

    const fallbackPolling = () => {
      const fetchResults = async () => {
        try {
          const response = await analysisService.getAnalysisStatus(jobId, language)
          if (cancelled) return
          if (response.status === 'completed') {
            setData(response.results)
            setProgress(100)
            setLoading(false)
            onComplete?.()
          } else if (response.status === 'processing') {
            setProgress(response.progress || 0)
            setProgressMsg(response.message || 'Memproses...')
            timerId = setTimeout(fetchResults, 2000)
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

    // Try SSE first, fall back to polling
    try {
      es = new EventSource(`${API_BASE}/api/stream/${jobId}`)
      es.onmessage = (event) => {
        if (cancelled) { es.close(); return }
        try {
          const payload = JSON.parse(event.data)
          if (payload.type === 'complete') {
            setData(payload.results)
            setProgress(100)
            setLoading(false)
            onComplete?.()
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
    } catch {
      fallbackPolling()
    }

    return () => {
      cancelled = true
      if (es) es.close()
      if (timerId) clearTimeout(timerId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, language])

  return { loading, progress, progressMsg, data, error }
}

export default useAnalysisJob
