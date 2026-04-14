import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, ExternalLink, Calendar, Users, BookOpen, Filter, ChevronDown, Loader } from 'lucide-react'
import { useDarkMode } from '../../contexts/DarkModeContext'
import { useToast } from '../../contexts/ToastContext'
import { paperService } from '../../services/paperService'
import Badge from '../common/Badge'
import EmptyState from '../common/EmptyState'

const SOURCES = [
  { id: 'arxiv', label: 'arXiv', color: 'text-red-500' },
  { id: 'semantic_scholar', label: 'Semantic Scholar', color: 'text-blue-500' },
  { id: 'core', label: 'CORE', color: 'text-green-500' },
  { id: 'crossref', label: 'CrossRef', color: 'text-purple-500' },
  { id: 'pubmed', label: 'PubMed', color: 'text-orange-500' },
  { id: 'europe_pmc', label: 'Europe PMC', color: 'text-teal-500' },
]

const SearchPage = () => {
  const { darkMode } = useDarkMode()
  const toast = useToast()
  const navigate = useNavigate()

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
    <div className="container mx-auto px-6 py-12">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <motion.div
          animate={{ rotate: [0, 5, -5, 0] }}
          transition={{ duration: 4, repeat: Infinity }}
          className="inline-block mb-6"
        >
          <div className={`p-4 rounded-3xl ${
            darkMode
              ? 'bg-gradient-to-br from-blue-500/20 to-cyan-500/20'
              : 'bg-gradient-to-br from-blue-100 to-cyan-100'
          }`}>
            <Search className={`w-12 h-12 ${darkMode ? 'text-blue-400' : 'text-blue-600'}`} />
          </div>
        </motion.div>

        <h1 className={`text-4xl md:text-5xl font-extrabold mb-4 bg-gradient-to-r ${
          darkMode
            ? 'from-blue-400 via-cyan-400 to-teal-400'
            : 'from-blue-600 via-cyan-600 to-teal-600'
        } bg-clip-text text-transparent`}>
          Search Papers
        </h1>
        <p className={`text-lg max-w-2xl mx-auto ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          Search across arXiv, Semantic Scholar, CORE, PubMed, CrossRef, and Europe PMC
        </p>
      </motion.div>

      {/* Search Form */}
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        onSubmit={handleSearch}
        className="max-w-4xl mx-auto mb-12"
      >
        <div className={`flex rounded-2xl overflow-hidden border backdrop-blur-xl shadow-xl ${
          darkMode
            ? 'bg-gray-800/80 border-gray-700/50'
            : 'bg-white/80 border-gray-200/50'
        }`}>
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search for research papers..."
            className={`flex-1 px-6 py-4 bg-transparent outline-none text-lg ${
              darkMode ? 'text-white placeholder-gray-500' : 'text-gray-900 placeholder-gray-400'
            }`}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-semibold hover:from-blue-500 hover:to-cyan-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? (
              <Loader className="w-5 h-5 animate-spin" />
            ) : (
              <Search className="w-5 h-5" />
            )}
            Search
          </button>
        </div>

        {/* Filter Toggle */}
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className={`mt-4 flex items-center gap-2 text-sm font-medium ${
            darkMode ? 'text-gray-400 hover:text-gray-300' : 'text-gray-600 hover:text-gray-800'
          } transition-colors`}
        >
          <Filter className="w-4 h-4" />
          Filters
          <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
        </button>

        {/* Filters */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div className={`mt-4 p-6 rounded-2xl border ${
                darkMode
                  ? 'bg-gray-800/60 border-gray-700/50'
                  : 'bg-white/60 border-gray-200/50'
              }`}>
                {/* Sources */}
                <div className="mb-6">
                  <label className={`block text-sm font-semibold mb-3 ${
                    darkMode ? 'text-gray-300' : 'text-gray-700'
                  }`}>Sources</label>
                  <div className="flex flex-wrap gap-2">
                    {SOURCES.map(source => (
                      <button
                        key={source.id}
                        type="button"
                        onClick={() => toggleSource(source.id)}
                        className={`px-4 py-2 rounded-xl text-sm font-medium transition-all border ${
                          selectedSources.includes(source.id)
                            ? darkMode
                              ? 'bg-blue-600/20 border-blue-500/50 text-blue-400'
                              : 'bg-blue-50 border-blue-300 text-blue-700'
                            : darkMode
                              ? 'bg-gray-700/50 border-gray-600/50 text-gray-400 hover:bg-gray-600/50'
                              : 'bg-gray-100 border-gray-200 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {source.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Year Range & Max Results */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className={`block text-sm font-semibold mb-2 ${
                      darkMode ? 'text-gray-300' : 'text-gray-700'
                    }`}>Year From</label>
                    <input
                      type="number"
                      value={yearFrom}
                      onChange={e => setYearFrom(e.target.value)}
                      placeholder="e.g. 2020"
                      className={`w-full px-4 py-2.5 rounded-xl border outline-none transition-colors ${
                        darkMode
                          ? 'bg-gray-700/50 border-gray-600/50 text-white placeholder-gray-500 focus:border-blue-500'
                          : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-blue-500'
                      }`}
                    />
                  </div>
                  <div>
                    <label className={`block text-sm font-semibold mb-2 ${
                      darkMode ? 'text-gray-300' : 'text-gray-700'
                    }`}>Year To</label>
                    <input
                      type="number"
                      value={yearTo}
                      onChange={e => setYearTo(e.target.value)}
                      placeholder="e.g. 2024"
                      className={`w-full px-4 py-2.5 rounded-xl border outline-none transition-colors ${
                        darkMode
                          ? 'bg-gray-700/50 border-gray-600/50 text-white placeholder-gray-500 focus:border-blue-500'
                          : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-blue-500'
                      }`}
                    />
                  </div>
                  <div>
                    <label className={`block text-sm font-semibold mb-2 ${
                      darkMode ? 'text-gray-300' : 'text-gray-700'
                    }`}>Max Results</label>
                    <select
                      value={maxResults}
                      onChange={e => setMaxResults(parseInt(e.target.value))}
                      className={`w-full px-4 py-2.5 rounded-xl border outline-none transition-colors ${
                        darkMode
                          ? 'bg-gray-700/50 border-gray-600/50 text-white focus:border-blue-500'
                          : 'bg-white border-gray-200 text-gray-900 focus:border-blue-500'
                      }`}
                    >
                      <option value={5}>5</option>
                      <option value={10}>10</option>
                      <option value={20}>20</option>
                      <option value={50}>50</option>
                    </select>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.form>

      {/* Results */}
      <div className="max-w-4xl mx-auto">
        {loading && (
          <div className="flex justify-center py-12">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            >
              <Loader className={`w-12 h-12 ${darkMode ? 'text-blue-400' : 'text-blue-600'}`} />
            </motion.div>
          </div>
        )}

        {!loading && hasSearched && results.length === 0 && (
          <EmptyState
            icon={Search}
            title="No papers found"
            description="Try adjusting your search query or filters"
          />
        )}

        <AnimatePresence>
          {!loading && results.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4"
            >
              <p className={`text-sm font-medium mb-6 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Found {results.length} papers
              </p>

              {results.map((paper, idx) => (
                <motion.div
                  key={paper.id || idx}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  whileHover={{ y: -2 }}
                  className={`p-6 rounded-2xl border backdrop-blur-xl transition-all duration-300 ${
                    darkMode
                      ? 'bg-gray-800/80 border-gray-700/50 hover:bg-gray-700/80'
                      : 'bg-white/80 border-gray-200/50 hover:bg-white/90'
                  } shadow-lg hover:shadow-xl`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className={`text-lg font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                        {paper.title}
                      </h3>

                      <div className="flex flex-wrap items-center gap-3 mb-3">
                        {paper.authors && (
                          <span className={`flex items-center gap-1 text-sm ${
                            darkMode ? 'text-gray-400' : 'text-gray-600'
                          }`}>
                            <Users className="w-3.5 h-3.5" />
                            {Array.isArray(paper.authors) ? paper.authors.slice(0, 3).join(', ') : paper.authors}
                            {Array.isArray(paper.authors) && paper.authors.length > 3 && ' et al.'}
                          </span>
                        )}
                        {paper.year && (
                          <span className={`flex items-center gap-1 text-sm ${
                            darkMode ? 'text-gray-400' : 'text-gray-600'
                          }`}>
                            <Calendar className="w-3.5 h-3.5" />
                            {paper.year}
                          </span>
                        )}
                        {paper.source && (
                          <Badge variant="info">{paper.source}</Badge>
                        )}
                      </div>

                      {paper.abstract && (
                        <p className={`text-sm leading-relaxed line-clamp-3 ${
                          darkMode ? 'text-gray-400' : 'text-gray-600'
                        }`}>
                          {paper.abstract}
                        </p>
                      )}
                    </div>

                    <div className="flex flex-col gap-2 flex-shrink-0">
                      {paper.url && (
                        <a
                          href={paper.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={`p-2 rounded-xl transition-colors ${
                            darkMode
                              ? 'hover:bg-gray-700 text-gray-400 hover:text-blue-400'
                              : 'hover:bg-gray-100 text-gray-500 hover:text-blue-600'
                          }`}
                          title="Open paper"
                        >
                          <ExternalLink className="w-5 h-5" />
                        </a>
                      )}
                      <button
                        onClick={() => handleIngest(paper)}
                        className={`p-2 rounded-xl transition-colors ${
                          darkMode
                            ? 'hover:bg-gray-700 text-gray-400 hover:text-green-400'
                            : 'hover:bg-gray-100 text-gray-500 hover:text-green-600'
                        }`}
                        title="Ingest paper"
                      >
                        <BookOpen className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default SearchPage
