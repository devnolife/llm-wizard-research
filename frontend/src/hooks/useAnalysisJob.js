import { useState, useEffect, useCallback } from 'react'
import { analysisService } from '../services/analysisService'

// Track analysis job progress via SSE with polling fallback.
// Properly cleans up EventSource + timers on unmount / dependency change (fixes P2).
const useAnalysisJob = (jobId, language, { onComplete } = {}) => {
  const [loading, setLoading] = useState(true)
  const [progress, setProgress] = useState(0)
  const [progressMsg, setProgressMsg] = useState('')
  const [activities, setActivities] = useState([])
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [status, setStatus] = useState('queued')
  const [refreshToken, setRefreshToken] = useState(0)

  // Log proses lengkap: setiap pesan/tahap baru dicatat dengan jam, agar
  // pengguna melihat SEMUA langkah (ekstraksi tiap PDF, topik, analisis
  // neuro-symbolic, dst) — bukan hanya pesan terakhir.
  const appendActivity = useCallback((text, kind = 'info') => {
    if (!text) return
    setActivities(prev => {
      if (prev.length && prev[prev.length - 1].text === text) return prev
      const time = new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      return [...prev.slice(-60), { text, kind, time }]
    })
  }, [])

  const cancel = useCallback(async () => {
    const response = await analysisService.cancelAnalysis(jobId)
    setStatus(response.status)
    setProgressMsg(response.message || 'Pembatalan diminta...')
    return response
  }, [jobId])

  const retry = useCallback(async () => {
    const response = await analysisService.retryAnalysis(jobId)
    setError(null)
    setData(null)
    setActivities([])
    setStatus(response.status)
    setProgress(response.progress || 0)
    setProgressMsg(response.message || 'Menjadwalkan ulang analisis...')
    setLoading(true)
    setRefreshToken(value => value + 1)
    return response
  }, [jobId])

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
          setStatus(response.status || 'unknown')
          if (response.status === 'completed') {
            setData(response.results)
            setProgress(100)
            setLoading(false)
            onComplete?.()
          } else if (['queued', 'processing', 'running'].includes(response.status)) {
            setProgress(response.progress || 0)
            const msg = response.message || (response.status === 'queued' ? 'Menunggu worker...' : 'Memproses...')
            setProgressMsg(msg)
            appendActivity(msg)
            timerId = setTimeout(fetchResults, 2000)
          } else if (['failed', 'interrupted', 'cancelled'].includes(response.status)) {
            setError(response.error || response.message || 'Analisis gagal')
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
            setStatus('completed')
            setData(payload.results)
            setProgress(100)
            setLoading(false)
            onComplete?.()
            es.close()
          } else if (payload.type === 'error') {
            setStatus(payload.status || 'failed')
            setError(payload.error || payload.message || 'Analisis gagal')
            setLoading(false)
            es.close()
          } else if (payload.type === 'phase') {
            const phase = payload.phase || payload.data?.phase
            const eventType = payload.event_type || ''
            if (phase) {
              setProgressMsg(`Tahap: ${phase}`)
              appendActivity(
                eventType.includes('completed') ? `Tahap selesai: ${phase}` : `Tahap dimulai: ${phase}`,
                'phase',
              )
            }
          } else {
            setStatus(payload.status || 'running')
            setProgress(payload.progress || 0)
            const msg = payload.message || 'Memproses...'
            setProgressMsg(msg)
            appendActivity(msg)
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
  }, [jobId, language, refreshToken])

  return { loading, progress, progressMsg, activities, data, error, status, cancel, retry }
}

export default useAnalysisJob
