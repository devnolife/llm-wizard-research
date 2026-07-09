import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, X, Loader } from 'lucide-react'
import { analysisService } from '../../services/analysisService'
import api from '../../services/api'
import { useToast } from '../../contexts/ToastContext'

const UploadPage = () => {
  const toast = useToast()
  const navigate = useNavigate()
  const [files, setFiles] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState({ papers: '-', chunks: '-' })

  useEffect(() => {
    api.get('/api/stats')
      .then(({ data: d }) => {
        setStats({
          papers: d.total_documents ?? d.document_count ?? '-',
          chunks: d.total_chunks ?? '-',
        })
      })
      .catch(() => { })
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
      setError(err.userMessage || 'Unggah gagal. Silakan coba lagi.')
      toast.error(err.userMessage || 'Unggah gagal')
      setUploading(false)
    }
  }

  return (
    <div className="relative w-full px-6 lg:px-10 py-12 max-w-6xl mx-auto">
      {/* Hero */}
      <div className="mb-10 reveal">
        <span className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/5 px-3 py-1 text-xs font-medium text-primary mb-5">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary" />
          </span>
          Neuro-Symbolic Agentic Analysis
        </span>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tight leading-[1.05] mb-4">
          Temukan <span className="text-gradient">celah penelitian</span>
          <br className="hidden sm:block" /> dari paper yang Anda unggah.
        </h1>
        <p className="text-base md:text-lg text-muted-foreground max-w-2xl leading-relaxed">
          Unggah paper PDF — AI mengekstrak topik, membangun knowledge graph, dan
          mendeteksi indikator <em className="not-italic text-foreground font-medium">synthesis gap</em>
          {' '}(fragmentasi, inkonsistensi, ketidaklengkapan) untuk arah penelitian baru.
        </p>
      </div>

      {/* How it works */}
      <div className="rounded-2xl border bg-card/80 p-6 mb-8 shadow-soft">
        <p className="text-sm font-semibold mb-4 flex items-center gap-2">
          <span className="h-1 w-6 rounded-full bg-primary" />
          Cara kerja — 3 langkah
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 reveal">
          {[
            { step: '1', title: 'Unggah Paper', desc: 'Pilih satu atau beberapa file PDF paper penelitian, lalu klik Analisis.' },
            { step: '2', title: 'AI Menganalisis', desc: 'Sistem membaca isi paper, mengekstrak topik & fakta, lalu mencari celah penelitian (~2-5 menit).' },
            { step: '3', title: 'Lihat Hasil', desc: 'Hasil tampil per tab: Ringkasan → Gap Penelitian → Rekomendasi. Gap = ide penelitian baru untuk Anda.' },
          ].map(({ step, title, desc }) => (
            <div key={step} className="flex gap-3.5">
              <div className="grid h-8 w-8 place-items-center rounded-xl bg-primary/10 text-primary text-sm font-bold flex-shrink-0 ring-1 ring-inset ring-primary/20">{step}</div>
              <div>
                <p className="text-sm font-semibold">{title}</p>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8 reveal">
        {[
          { label: 'Paper Terindeks', value: stats.papers },
          { label: 'Chunk di Vector DB', value: typeof stats.chunks === 'number' ? stats.chunks.toLocaleString() : stats.chunks },
          { label: 'Waktu Analisis Rata-rata', value: '~2 menit' },
        ].map((stat, idx) => (
          <div key={idx} className="rounded-2xl border bg-card/80 p-5 lift">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{stat.label}</p>
            <p className="font-display text-3xl font-bold mt-1.5 tabular-nums">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Upload Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`group relative rounded-2xl border-2 border-dashed p-12 text-center transition-all duration-300 ${isDragging
            ? 'border-primary bg-primary/5 scale-[1.01]'
            : 'border-border hover:border-primary/50 hover:bg-primary/[0.03]'
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
          <span className={`mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl transition-all duration-300 ${isDragging ? 'bg-primary text-primary-foreground scale-110' : 'bg-primary/10 text-primary group-hover:scale-105'}`}>
            <Upload className="w-7 h-7" />
          </span>
          <p className="text-lg font-semibold mb-1">Letakkan file PDF di sini</p>
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
          className="mt-6 w-full py-3.5 px-4 rounded-xl bg-primary text-primary-foreground font-semibold shadow-glow transition-all duration-200 hover:bg-primary/90 hover:shadow-lg active:scale-[0.99]"
        >
          Unggah &amp; Auto-Analisis ({files.length} file)
        </button>
      )}

      {/* Progress */}
      {uploading && (
        <div className="mt-6 rounded-lg border bg-card p-6">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium flex items-center gap-2">
              <Loader className="w-4 h-4 animate-spin" />
              {progress < 100 ? 'Mengunggah...' : 'Memproses & Menganalisis...'}
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
              Mengekstrak topik dan menghasilkan insight... Mungkin perlu satu menit.
            </p>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 p-4 rounded-lg border border-destructive/50 bg-destructive/10 text-sm">
          <p className="font-medium text-destructive">Unggah Gagal</p>
          <p className="text-destructive/80 mt-1">{error}</p>
        </div>
      )}

      {/* Features */}
      <div className="mt-12 grid gap-4 md:grid-cols-3">
        {[
          { title: 'Ekstraksi Topik', desc: 'AI mengidentifikasi arah penelitian tiap paper secara otomatis.' },
          { title: 'Deteksi Gap', desc: 'Menyingkap sudut yang kurang diteliti dan pertanyaan yang belum terjawab.' },
          { title: 'Rekomendasi', desc: 'Mengubah insight menjadi langkah berikutnya yang jelas dan berbukti.' },
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
