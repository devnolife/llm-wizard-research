import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, X, Loader } from 'lucide-react'
import { analysisService } from '../../services/analysisService'
import { useDarkMode } from '../../contexts/DarkModeContext'
import { useToast } from '../../contexts/ToastContext'

const UploadPage = () => {
  const { darkMode } = useDarkMode()
  const toast = useToast()
  const navigate = useNavigate()
  const [files, setFiles] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState({ papers: '-', chunks: '-' })

  useEffect(() => {
    const API_BASE = import.meta.env.VITE_API_URL || ''
    fetch(`${API_BASE}/api/stats`)
      .then(r => r.json())
      .then(d => {
        setStats({
          papers: d.total_documents ?? d.document_count ?? '-',
          chunks: d.total_chunks ?? '-',
        })
      })
      .catch(() => {})
  }, [])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      file => file.type === 'application/pdf'
    )
    setFiles(prev => [...prev, ...droppedFiles])
  }, [])

  const handleFileInput = (e) => {
    const selectedFiles = Array.from(e.target.files).filter(
      file => file.type === 'application/pdf'
    )
    setFiles(prev => [...prev, ...selectedFiles])
  }

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUploadAndAnalyze = async () => {
    if (files.length === 0) return
    setUploading(true)
    setError(null)
    setProgress(0)

    try {
      const response = await analysisService.uploadAndAnalyze(
        files,
        (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          setProgress(percentCompleted)
        }
      )
      navigate(`/results/${response.job_id}`)
    } catch (err) {
      setError(err.userMessage || 'Upload failed. Please try again.')
      toast.error(err.userMessage || 'Upload failed')
      setUploading(false)
    }
  }

  return (
    <div className="w-full px-6 lg:px-10 py-12">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight mb-2">Auto-Analisis Penelitian</h1>
        <p className="text-muted-foreground">
          Unggah paper PDF. AI mengekstrak topik, mendeteksi gap penelitian, dan menghasilkan rekomendasi.
        </p>
      </div>

      {/* How it works */}
      <div className="rounded-lg border bg-card p-5 mb-8">
        <p className="text-sm font-semibold mb-3">Cara kerja — 3 langkah:</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { step: '1', title: 'Unggah Paper', desc: 'Pilih satu atau beberapa file PDF paper penelitian, lalu klik Analisis.' },
            { step: '2', title: 'AI Menganalisis', desc: 'Sistem membaca isi paper, mengekstrak topik & fakta, lalu mencari celah penelitian (~2-5 menit).' },
            { step: '3', title: 'Lihat Hasil', desc: 'Hasil tampil per tab: Ringkasan → Gap Penelitian → Rekomendasi. Gap = ide penelitian baru untuk Anda.' },
          ].map(({ step, title, desc }) => (
            <div key={step} className="flex gap-3">
              <div className="w-7 h-7 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-bold flex-shrink-0">{step}</div>
              <div>
                <p className="text-sm font-medium">{title}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: 'Paper Terindeks', value: stats.papers },
          { label: 'Chunk di Vector DB', value: typeof stats.chunks === 'number' ? stats.chunks.toLocaleString() : stats.chunks },
          { label: 'Waktu Analisis Rata-rata', value: '~2 menit' },
        ].map((stat, idx) => (
          <div key={idx} className="rounded-lg border bg-card p-4">
            <p className="text-sm text-muted-foreground">{stat.label}</p>
            <p className="text-2xl font-bold">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Upload Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative rounded-lg border-2 border-dashed p-12 text-center transition-colors ${
          isDragging
            ? 'border-foreground/50 bg-secondary'
            : 'border-border hover:border-foreground/30 hover:bg-secondary/50'
        }`}
      >
        <input
          type="file"
          multiple
          accept=".pdf"
          onChange={handleFileInput}
          className="hidden"
          id="file-input"
          disabled={uploading}
        />
        <label htmlFor="file-input" className="cursor-pointer block">
          <Upload className="w-10 h-10 mx-auto mb-4 text-muted-foreground" />
          <p className="text-lg font-medium mb-1">Letakkan file PDF di sini</p>
          <p className="text-sm text-muted-foreground">atau klik untuk memilih dari perangkat Anda</p>
          <p className="text-xs text-muted-foreground mt-2">Format: File PDF maksimal 50MB</p>
        </label>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          {files.map((file, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 rounded-lg border bg-card"
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{file.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
              {!uploading && (
                <button
                  onClick={() => removeFile(index)}
                  className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Upload Button */}
      {files.length > 0 && !uploading && (
        <button
          onClick={handleUploadAndAnalyze}
          className="mt-6 w-full py-3 px-4 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
        >
          Unggah & Auto-Analisis ({files.length} file)
        </button>
      )}

      {/* Progress */}
      {uploading && (
        <div className="mt-6 rounded-lg border bg-card p-6">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium flex items-center gap-2">
              <Loader className="w-4 h-4 animate-spin" />
              {progress < 100 ? 'Uploading...' : 'Processing & Analyzing...'}
            </span>
            <span className="text-sm font-mono">{progress}%</span>
          </div>
          <div className="h-2 rounded-full bg-secondary overflow-hidden">
            <div
              className="h-full bg-foreground rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          {progress === 100 && (
            <p className="text-xs text-muted-foreground mt-3">
              Extracting topics and generating insights... This may take a minute.
            </p>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 p-4 rounded-lg border border-destructive/50 bg-destructive/10 text-sm">
          <p className="font-medium text-destructive">Upload Failed</p>
          <p className="text-destructive/80 mt-1">{error}</p>
        </div>
      )}

      {/* Features */}
      <div className="mt-12 grid gap-4 md:grid-cols-3">
        {[
          { title: 'Topic Extraction', desc: 'AI identifies research directions per paper automatically.' },
          { title: 'Gap Detection', desc: 'Surface understudied angles and unanswered questions.' },
          { title: 'Recommendations', desc: 'Turn insights into clear next steps with evidence.' },
        ].map((feature, idx) => (
          <div key={idx} className="rounded-lg border bg-card p-5">
            <h4 className="font-medium mb-1">{feature.title}</h4>
            <p className="text-sm text-muted-foreground">{feature.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default UploadPage
