import { useState, useEffect, useCallback } from 'react'
import { FileText, Trash2, Search, Database, BarChart3, RefreshCw, Loader } from 'lucide-react'
import useToast from '../../hooks/useToast'
import { documentService } from '../../services/documentService'
import EmptyState from '../common/EmptyState'
import Badge from '../common/Badge'
import PageHelp from '../common/PageHelp'

const DocumentsPage = () => {
  const toast = useToast()
  const [stats, setStats] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [searching, setSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  const fetchStats = useCallback(async () => {
    try {
      const data = await documentService.getStats()
      setStats(data)
    } catch (err) {
      toast.error(err.userMessage || 'Gagal memuat statistik')
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => { fetchStats() }, [fetchStats])

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    setSearching(true)
    setHasSearched(true)
    try {
      const data = await documentService.search(searchQuery)
      setSearchResults(data.results || [])
    } catch (err) {
      toast.error(err.userMessage || 'Pencarian gagal')
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }

  const handleDelete = async (docId, title) => {
    if (!confirm(`Hapus "${title || docId}"?`)) return
    try {
      await documentService.deleteDocument(docId)
      toast.success('Dokumen dihapus')
      fetchStats()
      if (hasSearched) setSearchResults(prev => prev.filter(r => r.id !== docId))
    } catch (err) {
      toast.error(err.userMessage || 'Gagal menghapus dokumen')
    }
  }

  return (
    <div className="w-full px-6 lg:px-10 py-12">
      {/* Header */}
      <div className="mb-6 reveal">
        <h1 className="text-3xl font-bold tracking-tight mb-2">Dokumen</h1>
        <p className="text-muted-foreground">Kelola koleksi dokumen penelitian dan vector store Anda</p>
      </div>

      <PageHelp
        icon={Database}
        title="Yang akan Anda lihat di sini"
        description="Daftar dan statistik seluruh paper yang tersimpan di database Anda."
        items={[
          'Statistik: total dokumen, total chunk, dan jumlah entri vector store.',
          'Cari isi dokumen, lihat detailnya, atau hapus dokumen dari koleksi.',
        ]}
        className="mb-8"
      />

      {/* Stats */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {[
            { icon: FileText, label: 'Total Dokumen', value: stats.total_documents ?? stats.document_count ?? '—' },
            { icon: BarChart3, label: 'Total Chunk', value: stats.total_chunks ?? stats.chunk_count ?? '—' },
            { icon: Database, label: 'Vector Store', value: stats.vector_count ?? stats.collection_count ?? '—' },
          ].map((stat, idx) => (
            <div key={idx} className="rounded-2xl border bg-card/80 p-5 lift">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-inset ring-primary/20 mb-3">
                <stat.icon className="w-[18px] h-[18px]" />
              </span>
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{stat.label}</p>
              <p className="font-display text-3xl font-bold mt-1 tabular-nums">{stat.value}</p>
            </div>
          ))}
          <div className="md:col-span-3">
            <button
              onClick={() => { setLoading(true); fetchStats() }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md border text-sm font-medium hover:bg-secondary transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Segarkan
            </button>
          </div>
        </div>
      )}

      {/* Search */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex rounded-lg border overflow-hidden bg-card">
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Cari dokumen Anda..."
            className="flex-1 px-4 py-3 bg-transparent outline-none text-foreground placeholder:text-muted-foreground"
          />
          <button
            type="submit"
            disabled={searching || !searchQuery.trim()}
            className="px-6 py-3 bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {searching ? <Loader className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Cari
          </button>
        </div>
      </form>

      {/* Results */}
      {!searching && hasSearched && searchResults.length === 0 && (
        <EmptyState icon={Search} title="Tidak ada hasil" description="Coba kata kunci lain" />
      )}

      {searchResults.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground mb-4">Menemukan {searchResults.length} hasil</p>
          {searchResults.map((result, idx) => (
            <div key={result.id || idx} className="p-4 rounded-xl border bg-card/80 lift">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <FileText className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
                    <h4 className="font-semibold truncate">
                      {result.metadata?.title || result.metadata?.source || 'Tanpa Judul'}
                    </h4>
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-3">
                    {result.content || result.text || result.page_content || ''}
                  </p>
                  {result.score !== undefined && (
                    <Badge variant="info" className="mt-2">Skor: {(result.score * 100).toFixed(1)}%</Badge>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(result.id, result.metadata?.title)}
                  className="p-2 rounded-md text-muted-foreground hover:text-destructive hover:bg-secondary transition-colors flex-shrink-0"
                  title="Hapus dokumen"
                  aria-label={`Hapus dokumen ${result.metadata?.title || result.id || ''}`}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default DocumentsPage
