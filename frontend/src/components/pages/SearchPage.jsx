import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search, ExternalLink, Calendar, Users, BookOpen, Filter, ChevronDown, Loader, CheckCircle2, Circle, Sparkles, Lightbulb, Tag, Upload, X } from 'lucide-react'
import useToast from '../../hooks/useToast'
import { paperService } from '../../services/paperService'
import { documentService } from '../../services/documentService'
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
  { id: 'sciencedirect', label: 'ScienceDirect' },
]

const SearchPage = () => {
  const toast = useToast()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const suggestedQuery = searchParams.get('q') || ''
  const isSolutionSearch = searchParams.get('from') === 'solution'
  const autoSearchQuery = useRef(null)
  const [query, setQuery] = useState(() => suggestedQuery)
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
  const [manualFile, setManualFile] = useState(null)
  const [manualUploading, setManualUploading] = useState(false)
  const [manualUploadResult, setManualUploadResult] = useState(null)

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

  const searchPapers = useCallback(async (queryText) => {
    if (!queryText.trim()) return
    if (selectedSources.length === 0) {
      toast.warning('Pilih minimal satu sumber')
      return
    }

    setLoading(true)
    setHasSearched(true)
    try {
      const response = await paperService.searchExternalPapers(queryText, {
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
  }, [maxResults, selectedSources, toast, yearFrom, yearTo])

  const handleSearch = (e) => {
    e.preventDefault()
    searchPapers(query)
  }

  useEffect(() => {
    if (!suggestedQuery || autoSearchQuery.current === suggestedQuery) return
    autoSearchQuery.current = suggestedQuery
    setQuery(suggestedQuery)
    searchPapers(suggestedQuery)
  }, [searchPapers, suggestedQuery])

  const handleIngest = async (paper) => {
    try {
      await paperService.ingestExternalPaper(paper.id || paper.paper_id, paper.source)
      toast.success(`"${paper.title}" berhasil disimpan`)
    } catch (err) {
      toast.error(err.userMessage || 'Gagal menyimpan paper')
    }
  }

  const handleManualFile = (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      toast.warning('Pilih file PDF jurnal')
      event.target.value = ''
      return
    }
    setManualFile(file)
    setManualUploadResult(null)
  }

  const handleManualUpload = async () => {
    if (!manualFile) return
    setManualUploading(true)
    try {
      const result = await documentService.uploadDocument(manualFile)
      setManualUploadResult(result)
      setManualFile(null)
      toast.success('Jurnal Anda berhasil disimpan ke koleksi')
    } catch (err) {
      toast.error(err.userMessage || 'Gagal mengunggah jurnal')
    } finally {
      setManualUploading(false)
    }
  }

  return (
    <div className="w-full px-6 lg:px-10 py-12">
      {/* Header */}
      <div className="mb-6 reveal">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary mb-2">
          {isSolutionSearch ? 'Langkah 4 dari 4' : 'Literatur pendukung'}
        </p>
        <h1 className="text-3xl font-bold tracking-tight mb-2">
          {isSolutionSearch ? 'Cari Jurnal Pendukung' : 'Cari Paper'}
        </h1>
        <p className="text-muted-foreground">
          {isSolutionSearch
            ? 'Mulai dari kata kunci solusi di bawah, lalu tandai jurnal yang paling dapat memperkuat arah penelitian Anda.'
            : 'Cari paper dari database eksternal untuk menambah bahan literatur Anda.'}
        </p>
      </div>

      <PageHelp
        icon={Search}
        title={isSolutionSearch ? 'Cari bukti pendukung untuk solusi Anda' : 'Yang akan Anda lihat di sini'}
        description={isSolutionSearch
          ? 'Baca abstrak hasil pencarian, tandai yang relevan, lalu simpan atau analisis beberapa paper pilihan.'
          : 'Hasil berupa daftar paper dari database eksternal (bukan koleksi Anda).'}
        items={isSolutionSearch
          ? ['Kata kunci sudah diisi otomatis. Anda tetap dapat mengubahnya sebelum atau sesudah pencarian.']
          : ['Tandai 3–5 paper relevan untuk melihat tema bersama dan saran arah penelitian.']}
        className="mb-8"
      />

      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-8">
        <div className="flex rounded-lg border overflow-hidden bg-card">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Masukkan kata kunci solusi atau topik..."
            aria-label="Kata kunci pencarian jurnal"
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
        <div className="max-w-2xl mx-auto space-y-4">
          <EmptyState
            icon={Search}
            title="Tidak ada paper ditemukan"
            description="Coba ubah kata kunci atau filter pencarian. Jika Anda sudah punya jurnal sendiri, unggah saja di bawah."
          />

          <section className="rounded-2xl border border-primary/25 bg-primary/[0.045] p-5">
            <div className="flex items-start gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary/10 text-primary shrink-0">
                <Upload className="w-5 h-5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Alternatif</p>
                <h2 className="font-semibold mt-1">Punya jurnal sendiri? Unggah ke koleksi.</h2>
                <p className="text-sm text-muted-foreground mt-1">Jurnal PDF akan disimpan agar bisa dicari dan dipakai dalam analisis berikutnya.</p>

                {!manualUploadResult ? (
                  <div className="mt-4 flex flex-col sm:flex-row gap-3">
                    <label className="flex-1 cursor-pointer rounded-lg border border-dashed bg-card px-3 py-2.5 text-sm text-muted-foreground hover:border-primary/50 transition-colors">
                      <input type="file" accept=".pdf,application/pdf" onChange={handleManualFile} className="sr-only" />
                      {manualFile ? manualFile.name : 'Pilih jurnal PDF…'}
                    </label>
                    <button
                      type="button"
                      onClick={handleManualUpload}
                      disabled={!manualFile || manualUploading}
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {manualUploading ? <Loader className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                      {manualUploading ? 'Mengunggah…' : 'Unggah Jurnal'}
                    </button>
                  </div>
                ) : (
                  <div className="mt-4 rounded-lg border bg-card p-3">
                    <p className="text-sm font-medium">{manualUploadResult.message || 'Jurnal berhasil disimpan.'}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button type="button" onClick={() => navigate('/documents')} className="rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-secondary transition-colors">Lihat Koleksi</button>
                      <button type="button" onClick={() => navigate('/')} className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">Analisis Jurnal</button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>
        </div>
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

          <div>
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="w-4 h-4 text-amber-500" />
              <h4 className="font-semibold text-sm">Arah Penelitian yang Didukung Paper Bertanda</h4>
            </div>
            {selectionResult.suggestion_note && (
              <p className="text-xs text-muted-foreground mb-3">{selectionResult.suggestion_note}</p>
            )}
            {selectionResult.suggestions?.length > 0 ? (
              <div className="space-y-2">
                {selectionResult.suggestions.map((s, i) => (
                  <div key={i} className="rounded-lg border bg-card p-4">
                    <div className="flex items-start gap-3">
                      <div className="w-6 h-6 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center flex-shrink-0 text-xs font-bold">
                        {i + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-medium text-sm">{s.title}</p>
                          {s.gap_type && <Badge variant="info">{s.gap_type}</Badge>}
                        </div>
                        {s.rationale && <p className="text-xs text-muted-foreground mt-1">{s.rationale}</p>}
                        {s.basis && (
                          <p className="mt-2 rounded-md bg-secondary/70 px-2.5 py-2 text-xs text-muted-foreground">
                            <strong className="text-foreground">Dasar dari abstrak:</strong> {s.basis}
                          </p>
                        )}
                        {s.source_papers?.length > 0 && (
                          <div className="mt-2 flex flex-wrap items-center gap-1.5">
                            <BookOpen className="w-3.5 h-3.5 text-primary" />
                            {s.source_papers.map((title, sourceIndex) => (
                              <span key={`${title}-${sourceIndex}`} className="rounded-full border bg-primary/5 px-2 py-0.5 text-[11px] text-muted-foreground">
                                {title}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-amber-500/25 bg-amber-500/5 p-4 text-sm text-muted-foreground">
                Bukti dari abstrak paper bertanda belum cukup untuk membuat arah penelitian yang kuat. Coba tandai paper yang lebih berhubungan atau baca detail hasil pencarian terlebih dahulu.
              </div>
            )}
          </div>
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
