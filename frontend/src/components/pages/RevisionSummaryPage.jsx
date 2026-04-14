import { useState } from 'react'
import { FileText, ExternalLink, Printer } from 'lucide-react'

const RevisionSummaryPage = () => {
  const [loading, setLoading] = useState(true)

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Header bar */}
      <div className="flex items-center justify-between px-6 py-3 border-b bg-background">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary" />
          <h1 className="text-lg font-semibold">Ringkasan Revisi Proposal</h1>
          <span className="text-xs bg-secondary text-muted-foreground px-2 py-0.5 rounded-full">
            v0 → v3.0
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const iframe = document.getElementById('revision-iframe')
              if (iframe?.contentWindow) {
                iframe.contentWindow.print()
              }
            }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium bg-secondary text-foreground hover:bg-secondary/80 transition-colors"
          >
            <Printer className="w-4 h-4" />
            <span className="hidden sm:inline">Print A4</span>
          </button>
          <a
            href="/ringkasan-revisi.html"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            <span className="hidden sm:inline">Fullscreen</span>
          </a>
        </div>
      </div>

      {/* Loading overlay */}
      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-muted-foreground">Memuat ringkasan revisi...</p>
          </div>
        </div>
      )}

      {/* Iframe */}
      <iframe
        id="revision-iframe"
        src="/ringkasan-revisi.html"
        title="Ringkasan Revisi Proposal"
        className={`flex-1 w-full border-0 ${loading ? 'hidden' : ''}`}
        onLoad={() => setLoading(false)}
      />
    </div>
  )
}

export default RevisionSummaryPage
