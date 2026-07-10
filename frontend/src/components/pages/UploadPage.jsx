import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, X, Loader, Search, Lightbulb, BookOpen, ArrowRight } from 'lucide-react'
import { analysisService } from '../../services/analysisService'
import useToast from '../../hooks/useToast'

const UploadPage = () => {
  const toast = useToast()
  const navigate = useNavigate()
  const [files, setFiles] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)
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
    <div className="relative w-full px-6 lg:px-10 py-12 max-w-5xl mx-auto">
      <header className="mb-8 max-w-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary mb-3">Mulai dari sini</p>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tight leading-[1.04] mb-4">
          Unggah jurnal.<br />Ikuti <span className="text-gradient">satu jalur sederhana.</span>
        </h1>
        <p className="text-base text-muted-foreground leading-relaxed">
          Tidak perlu memahami semua menu di awal. Mulai dengan jurnal Anda; sistem akan memandu Anda sampai menemukan gap, solusi, dan jurnal pendukungnya.
        </p>
      </header>

      <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-8" aria-label="Alur penelitian sederhana">
        {[
          { number: '01', title: 'Unggah jurnal', desc: 'Pilih PDF Anda.', icon: Upload, active: true },
          { number: '02', title: 'Lihat gap', desc: 'Temukan celah utama.', icon: Search },
          { number: '03', title: 'Pilih solusi', desc: 'Dapatkan arah riset.', icon: Lightbulb },
          { number: '04', title: 'Cari pendukung', desc: 'Temukan jurnal terkait.', icon: BookOpen },
        ].map((step) => {
          const StepIcon = step.icon
          return (
            <li key={step.number} className={`relative rounded-xl border p-4 ${step.active ? 'border-primary/40 bg-primary/5 shadow-sm' : 'bg-card/65'}`}>
              <div className="flex items-center justify-between mb-4">
                <span className={`font-mono text-[11px] font-bold ${step.active ? 'text-primary' : 'text-muted-foreground'}`}>{step.number}</span>
                <StepIcon className={`w-4 h-4 ${step.active ? 'text-primary' : 'text-muted-foreground'}`} />
              </div>
              <p className="text-sm font-semibold">{step.title}</p>
              <p className="text-xs text-muted-foreground mt-1">{step.desc}</p>
            </li>
          )
        })}
      </ol>

      {/* Upload Area */}
      <section className="rounded-2xl border bg-card/80 p-2 shadow-soft">
        <div className="px-5 pt-5 pb-3 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary mb-1">Langkah 1 dari 4</p>
            <h2 className="text-xl font-semibold">Unggah jurnal yang ingin dibandingkan</h2>
          </div>
          <ArrowRight className="w-5 h-5 text-primary mt-1" aria-hidden="true" />
        </div>
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          role="region"
          aria-label="Area unggah jurnal PDF"
          className={`group relative mx-3 mb-3 rounded-xl border-2 border-dashed p-10 text-center transition-all duration-300 ${isDragging
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
            <p className="text-lg font-semibold mb-1">Pilih jurnal PDF Anda</p>
            <p className="text-sm text-muted-foreground">Tarik file ke sini atau klik untuk memilih. Disarankan 2–5 jurnal.</p>
            <p className="text-xs text-muted-foreground mt-2">PDF maksimal 50MB per file</p>
          </label>
        </div>
      </section>

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
                  aria-label={`Hapus ${file.name}`}
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
          Lanjut: Temukan Gap dari {files.length} Jurnal
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

    </div>
  )
}

export default UploadPage
