import { useState } from 'react'
import { Search, ExternalLink, Calendar, Users, BookOpen, Filter, ChevronDown, Loader, CheckCircle2, Circle, Sparkles, Lightbulb, Tag, X } from 'lucide-react'
import { useToast } from '../../contexts/ToastContext'
import { paperService } from '../../services/paperService'
import Badge from '../common/Badge'
import EmptyState from '../common/EmptyState'
import PageHelp from '../common/PageHelp'

const SOURCES = [
  { id: 'arxiv', label: 'arXiv' },
  { id: 'semantic_scholar', label: 'Semantic Scholar' },
  { id: 'core', label: 'CORE' },
  { id: 'crossref', label: 'CrossRef' },
  { id: 'pubmed', label: 'PubMed' },
  { id: 'europe_pmc', label: 'Europe PMC' },
]

const SearchPage = () => {
  const toast = useToast()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [selectedSources, setSelectedSources] = useState(['arxiv', 'core', 'crossref'])
  const [maxResults, setMaxResults] = useState(10)
  const [yearFrom, setYearFrom] = useState('')
  const [yearTo, setYearTo] = useState('')
  const [hasSearched, setHasSearched] = useState(false)
  const [marked, setMarked] = useState([])
  const [analyzing, setAnalyzing] = useState(false)
  const [selectionResult, setSelectionResult] = useState(null)

  const toggleSource = (id) => {
    setSelectedSources(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    )
  }

  const isMarked = (paper) => marked.some(m => m.title === paper.title)

  const toggleMark = (paper) => {
    setMarked(prev =>
      prev.some(m => m.title === paper.title)
        ? prev.filter(m => m.title !== paper.title)
        : [...prev, paper]
    )
  }

  const handleAnalyzeSelection = async () => {
    if (marked.length < 3) {
      toast.warning('Tandai minimal 3 paper untuk dianalisis')
      return
    }
    setAnalyzing(true)
    setSelectionResult(null)
    try {
      const result = await paperService.analyzeSelection(
        marked.map(p => ({ title: p.title, abstract: p.abstract, authors: p.authors, year: p.year })),
        query
      )
      setSelectionResult(result)
      toast.success('Analisis paper bertanda selesai')
    } catch (err) {
      toast.error(err.userMessage || 'Analisis gagal')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    if (selectedSources.length === 0) {
      toast.warning('Pilih minimal satu sumber')
      return
    }

    setLoading(true)
    setHasSearched(true)
    try {
      const response = await paperService.searchExternalPapers(query, {
        sources: selectedSources,
        max_results: maxResults,
        year_from: yearFrom ? parseInt(yearFrom) : undefined,
        year_to: yearTo ? parseInt(yearTo) : undefined,
      })
      setResults(response.papers || response.results || [])
      toast.success(`Menemukan ${(response.papers || response.results || []).length} paper`)
    } catch (err) {
      toast.error(err.userMessage || 'Pencarian gagal')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleIngest = async (paper) => {
    try {
      await paperService.ingestExternalPaper(paper.id || paper.paper_id, paper.source)
      toast.success(`"${paper.title}" berhasil disimpan`)
    } catch (err) {
      toast.error(err.userMessage || 'Gagal menyimpan paper')
    }
  }

  return (
    <div className="w-full px-6 lg:px-10 py-12">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight mb-2">Cari Paper</h1>
        <p className="text-muted-foreground">
          Cari paper dari database eksternal untuk menambah bahan literatur Anda.
        </p>
      </div>

      <PageHelp
        icon={Search}
        title="Yang akan Anda lihat di sini"
        description="Hasil berupa daftar paper dari database eksternal (bukan koleksi Anda)."
        items={[
          'Tiap hasil menampilkan judul, penulis, tahun, abstrak, dan tautan sumber.',
          'Tandai 3-5 paper yang relevan, lalu klik "Analisis Tanda" untuk menemukan kata kunci yang sama dan saran arah penelitian.',
          'Filter berdasarkan sumber (arXiv, Semantic Scholar, CORE, CrossRef, PubMed, Europe PMC) dan rentang tahun.',
        ]}
        className="mb-8"
      />

      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-8">
        <div className="flex rounded-lg border overflow-hidden bg-card">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Cari paper penelitian..."
            className="flex-1 px-4 py-3 bg-transparent outline-none text-foreground placeholder:text-muted-foreground"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-3 bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Cari
          </button>
        </div>

        {/* Filter Toggle */}
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className="mt-3 flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <Filter className="w-4 h-4" />
          Filter
          <ChevronDown className={`w-3 h-3 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
        </button>

        {/* Filters */}
        {showFilters && (
          <div className="mt-3 p-5 rounded-lg border bg-card">
            <div className="mb-5">
              <label className="block text-sm font-medium mb-2">Sumber</label>
              <div className="flex flex-wrap gap-2">
                {SOURCES.map(source => (
                  <button
                    key={source.id}
                    type="button"
                    onClick={() => toggleSource(source.id)}
                    className={`px-3 py-1.5 rounded-md text-sm font-medium border transition-colors ${selectedSources.includes(source.id)
                      ? 'bg-secondary text-foreground border-border'
                      : 'text-muted-foreground border-transparent hover:bg-secondary/50'
                      }`}
                  >
                    {source.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">Dari Tahun</label>
                <input
                  type="number"
                  value={yearFrom}
                  onChange={e => setYearFrom(e.target.value)}
                  placeholder="mis. 2020"
                  className="w-full px-3 py-2 rounded-md border bg-background text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Sampai Tahun</label>
                <input
                  type="number"
                  value={yearTo}
                  onChange={e => setYearTo(e.target.value)}
                  placeholder="mis. 2024"
                  className="w-full px-3 py-2 rounded-md border bg-background text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Jumlah Hasil</label>
                <select
                  value={maxResults}
                  onChange={e => setMaxResults(parseInt(e.target.value))}
                  className="w-full px-3 py-2 rounded-md border bg-background text-foreground outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </form>

      {/* Results */}
      {loading && (
        <div className="flex justify-center py-12">
          <Loader className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {!loading && hasSearched && results.length === 0 && (
        <EmptyState
          icon={Search}
          title="Tidak ada paper ditemukan"
          description="Coba ubah kata kunci atau filter pencarian"
        />
      )}

      {!loading && results.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground mb-4">
            Menemukan {results.length} paper
          </p>

          {results.map((paper, idx) => (
            <div
              key={paper.id || idx}
              className={`p-5 rounded-lg border bg-card transition-colors ${isMarked(paper) ? 'border-primary ring-1 ring-primary/30 bg-primary/5' : 'hover:bg-secondary/30'
                }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <button
                    onClick={() => toggleMark(paper)}
                    title={isMarked(paper) ? 'Batalkan tanda' : 'Tandai paper ini'}
                    className="mt-0.5 flex-shrink-0 text-muted-foreground hover:text-primary transition-colors"
                  >
                    {isMarked(paper)
                      ? <CheckCircle2 className="w-5 h-5 text-primary" />
                      : <Circle className="w-5 h-5" />}
                  </button>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold mb-1.5">{paper.title}</h3>
                    <div className="flex flex-wrap items-center gap-3 mb-2">
                      {paper.authors && (
                        <span className="flex items-center gap-1 text-sm text-muted-foreground">
                          <Users className="w-3.5 h-3.5" />
                          {Array.isArray(paper.authors) ? paper.authors.slice(0, 3).join(', ') : paper.authors}
                          {Array.isArray(paper.authors) && paper.authors.length > 3 && ' et al.'}
                        </span>
                      )}
                      {paper.year && (
                        <span className="flex items-center gap-1 text-sm text-muted-foreground">
                          <Calendar className="w-3.5 h-3.5" />
                          {paper.year}
                        </span>
                      )}
                      {paper.source && <Badge variant="info">{paper.source}</Badge>}
                    </div>
                    {paper.abstract && (
                      <p className="text-sm text-muted-foreground line-clamp-3">{paper.abstract}</p>
                    )}
                  </div>
                </div>
                <div className="flex flex-col gap-1 flex-shrink-0">
                  {paper.url && (
                    <a
                      href={paper.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                      title="Buka paper"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                  <button
                    onClick={() => handleIngest(paper)}
                    className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                    title="Simpan ke koleksi"
                  >
                    <BookOpen className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Hasil analisis paper bertanda */}
      {selectionResult && (
        <div className="mt-8 rounded-lg border-2 border-primary/30 bg-primary/5 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              <h3 className="text-lg font-semibold">Analisis {selectionResult.paper_count || marked.length} Paper Bertanda</h3>
            </div>
            <button onClick={() => setSelectionResult(null)} className="text-muted-foreground hover:text-foreground" title="Tutup">
              <X className="w-4 h-4" />
            </button>
          </div>

          {selectionResult.summary && (
            <p className="text-sm text-muted-foreground mb-5">{selectionResult.summary}</p>
          )}

          {selectionResult.common_keywords?.length > 0 && (
            <div className="mb-5">
              <div className="flex items-center gap-2 mb-2">
                <Tag className="w-4 h-4 text-purple-500" />
                <h4 className="font-semibold text-sm">Kata Kunci yang Sama</h4>
              </div>
              <div className="flex flex-wrap gap-2">
                {selectionResult.common_keywords.map((kw, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-full text-xs font-medium bg-purple-500/10 text-purple-600 dark:text-purple-400">
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          {selectionResult.shared_themes?.length > 0 && (
            <div className="mb-5">
              <h4 className="font-semibold text-sm mb-2">Tema Bersama</h4>
              <ul className="space-y-1">
                {selectionResult.shared_themes.map((t, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <span className="text-primary mt-0.5">•</span><span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {selectionResult.suggestions?.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Lightbulb className="w-4 h-4 text-amber-500" />
                <h4 className="font-semibold text-sm">Saran Arah Penelitian</h4>
              </div>
              <div className="space-y-2">
                {selectionResult.suggestions.map((s, i) => (
                  <div key={i} className="rounded-lg border bg-card p-4">
                    <div className="flex items-start gap-3">
                      <div className="w-6 h-6 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center flex-shrink-0 text-xs font-bold">
                        {i + 1}
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium text-sm">{s.title}</p>
                        {s.rationale && <p className="text-xs text-muted-foreground mt-1">{s.rationale}</p>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Spacer agar konten tidak tertutup bar melayang */}
      {marked.length > 0 && <div className="h-20" />}

      {/* Bar melayang: aksi untuk paper bertanda */}
      {marked.length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
          <div className="w-full px-6 lg:px-10 py-3 flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-sm">
              <CheckCircle2 className="w-4 h-4 text-primary flex-shrink-0" />
              <span className="font-medium">{marked.length} paper ditandai</span>
              <span className="text-muted-foreground hidden sm:inline">
                {marked.length < 3 ? `— tandai ${3 - marked.length} lagi (disarankan 3-5)` : '— siap dianalisis'}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={() => { setMarked([]); setSelectionResult(null) }}
                className="px-3 py-1.5 rounded-md border text-sm font-medium hover:bg-secondary transition-colors"
              >
                Bersihkan
              </button>
              <button
                onClick={handleAnalyzeSelection}
                disabled={analyzing || marked.length < 3}
                className="inline-flex items-center gap-2 px-4 py-1.5 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {analyzing ? <Loader className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {analyzing ? 'Menganalisis...' : 'Analisis Tanda'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SearchPage
