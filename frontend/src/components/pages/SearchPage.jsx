import { useState } from 'react'
import { Search, ExternalLink, Calendar, Users, BookOpen, Filter, ChevronDown, Loader } from 'lucide-react'
import { useToast } from '../../contexts/ToastContext'
import { paperService } from '../../services/paperService'
import Badge from '../common/Badge'
import EmptyState from '../common/EmptyState'

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

  const toggleSource = (id) => {
    setSelectedSources(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    )
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    if (selectedSources.length === 0) {
      toast.warning('Please select at least one source')
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
      toast.success(`Found ${(response.papers || response.results || []).length} papers`)
    } catch (err) {
      toast.error(err.userMessage || 'Search failed')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleIngest = async (paper) => {
    try {
      await paperService.ingestExternalPaper(paper.id || paper.paper_id, paper.source)
      toast.success(`"${paper.title}" ingested successfully`)
    } catch (err) {
      toast.error(err.userMessage || 'Failed to ingest paper')
    }
  }

  return (
    <div className="container mx-auto max-w-4xl px-6 py-12">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight mb-2">Search Papers</h1>
        <p className="text-muted-foreground">
          Search across arXiv, Semantic Scholar, CORE, PubMed, CrossRef, and Europe PMC
        </p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-8">
        <div className="flex rounded-lg border overflow-hidden bg-card">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search for research papers..."
            className="flex-1 px-4 py-3 bg-transparent outline-none text-foreground placeholder:text-muted-foreground"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-3 bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Search
          </button>
        </div>

        {/* Filter Toggle */}
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className="mt-3 flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <Filter className="w-4 h-4" />
          Filters
          <ChevronDown className={`w-3 h-3 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
        </button>

        {/* Filters */}
        {showFilters && (
          <div className="mt-3 p-5 rounded-lg border bg-card">
            <div className="mb-5">
              <label className="block text-sm font-medium mb-2">Sources</label>
              <div className="flex flex-wrap gap-2">
                {SOURCES.map(source => (
                  <button
                    key={source.id}
                    type="button"
                    onClick={() => toggleSource(source.id)}
                    className={`px-3 py-1.5 rounded-md text-sm font-medium border transition-colors ${
                      selectedSources.includes(source.id)
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
                <label className="block text-sm font-medium mb-1.5">Year From</label>
                <input
                  type="number"
                  value={yearFrom}
                  onChange={e => setYearFrom(e.target.value)}
                  placeholder="e.g. 2020"
                  className="w-full px-3 py-2 rounded-md border bg-background text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Year To</label>
                <input
                  type="number"
                  value={yearTo}
                  onChange={e => setYearTo(e.target.value)}
                  placeholder="e.g. 2024"
                  className="w-full px-3 py-2 rounded-md border bg-background text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Max Results</label>
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
          title="No papers found"
          description="Try adjusting your search query or filters"
        />
      )}

      {!loading && results.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground mb-4">
            Found {results.length} papers
          </p>

          {results.map((paper, idx) => (
            <div
              key={paper.id || idx}
              className="p-5 rounded-lg border bg-card hover:bg-secondary/30 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
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
                <div className="flex flex-col gap-1 flex-shrink-0">
                  {paper.url && (
                    <a
                      href={paper.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                      title="Open paper"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                  <button
                    onClick={() => handleIngest(paper)}
                    className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                    title="Ingest paper"
                  >
                    <BookOpen className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default SearchPage
