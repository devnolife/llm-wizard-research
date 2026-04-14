import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FileText, Trash2, Search, Database, BarChart3, RefreshCw, Loader } from 'lucide-react'
import { useDarkMode } from '../../contexts/DarkModeContext'
import { useToast } from '../../contexts/ToastContext'
import { documentService } from '../../services/documentService'
import EmptyState from '../common/EmptyState'
import Badge from '../common/Badge'

const DocumentsPage = () => {
  const { darkMode } = useDarkMode()
  const toast = useToast()

  const [stats, setStats] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [searching, setSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  const fetchStats = async () => {
    try {
      const data = await documentService.getStats()
      setStats(data)
    } catch (err) {
      toast.error(err.userMessage || 'Failed to fetch stats')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
  }, [])

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchQuery.trim()) return

    setSearching(true)
    setHasSearched(true)
    try {
      const data = await documentService.search(searchQuery)
      setSearchResults(data.results || [])
    } catch (err) {
      toast.error(err.userMessage || 'Search failed')
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }

  const handleDelete = async (docId, title) => {
    if (!confirm(`Delete "${title || docId}"?`)) return

    try {
      await documentService.deleteDocument(docId)
      toast.success('Document deleted')
      fetchStats()
      if (hasSearched) {
        setSearchResults(prev => prev.filter(r => r.id !== docId))
      }
    } catch (err) {
      toast.error(err.userMessage || 'Failed to delete document')
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
              ? 'bg-gradient-to-br from-amber-500/20 to-orange-500/20'
              : 'bg-gradient-to-br from-amber-100 to-orange-100'
          }`}>
            <Database className={`w-12 h-12 ${darkMode ? 'text-amber-400' : 'text-amber-600'}`} />
          </div>
        </motion.div>

        <h1 className={`text-4xl md:text-5xl font-extrabold mb-4 bg-gradient-to-r ${
          darkMode
            ? 'from-amber-400 via-orange-400 to-red-400'
            : 'from-amber-600 via-orange-600 to-red-600'
        } bg-clip-text text-transparent`}>
          Documents
        </h1>
        <p className={`text-lg max-w-2xl mx-auto ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          Manage your research document collection and vector store
        </p>
      </motion.div>

      {/* Stats Cards */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader className={`w-10 h-10 animate-spin ${darkMode ? 'text-blue-400' : 'text-blue-600'}`} />
        </div>
      ) : stats && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto mb-12"
        >
          {[
            {
              icon: FileText,
              label: 'Total Documents',
              value: stats.total_documents ?? stats.document_count ?? '—',
              gradient: 'from-blue-500 to-cyan-500',
              iconColor: darkMode ? 'text-blue-400' : 'text-blue-600',
            },
            {
              icon: BarChart3,
              label: 'Total Chunks',
              value: stats.total_chunks ?? stats.chunk_count ?? '—',
              gradient: 'from-purple-500 to-pink-500',
              iconColor: darkMode ? 'text-purple-400' : 'text-purple-600',
            },
            {
              icon: Database,
              label: 'Vector Store',
              value: stats.vector_count ?? stats.collection_count ?? '—',
              gradient: 'from-amber-500 to-orange-500',
              iconColor: darkMode ? 'text-amber-400' : 'text-amber-600',
            },
          ].map((stat, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + idx * 0.1 }}
              whileHover={{ y: -4, scale: 1.02 }}
              className={`relative rounded-3xl border p-6 backdrop-blur-xl overflow-hidden ${
                darkMode
                  ? 'bg-gray-800/80 border-gray-700/50'
                  : 'bg-white/80 border-gray-200/50'
              } shadow-xl`}
            >
              <stat.icon className={`w-8 h-8 mb-3 ${stat.iconColor}`} />
              <p className={`text-sm font-medium mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {stat.label}
              </p>
              <p className={`text-3xl font-bold bg-gradient-to-r ${stat.gradient} bg-clip-text text-transparent`}>
                {stat.value}
              </p>
            </motion.div>
          ))}

          <div className="md:col-span-3 flex justify-center">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => { setLoading(true); fetchStats() }}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                darkMode
                  ? 'bg-gray-700/50 text-gray-300 hover:bg-gray-600/50'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <RefreshCw className="w-4 h-4" />
              Refresh Stats
            </motion.button>
          </div>
        </motion.div>
      )}

      {/* Search */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="max-w-4xl mx-auto"
      >
        <form onSubmit={handleSearch} className="mb-8">
          <div className={`flex rounded-2xl overflow-hidden border backdrop-blur-xl shadow-xl ${
            darkMode
              ? 'bg-gray-800/80 border-gray-700/50'
              : 'bg-white/80 border-gray-200/50'
          }`}>
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search your documents..."
              className={`flex-1 px-6 py-4 bg-transparent outline-none ${
                darkMode ? 'text-white placeholder-gray-500' : 'text-gray-900 placeholder-gray-400'
              }`}
            />
            <button
              type="submit"
              disabled={searching || !searchQuery.trim()}
              className="px-8 py-4 bg-gradient-to-r from-amber-600 to-orange-600 text-white font-semibold hover:from-amber-500 hover:to-orange-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {searching ? (
                <Loader className="w-5 h-5 animate-spin" />
              ) : (
                <Search className="w-5 h-5" />
              )}
              Search
            </button>
          </div>
        </form>

        {/* Search Results */}
        {!searching && hasSearched && searchResults.length === 0 && (
          <EmptyState
            icon={Search}
            title="No results found"
            description="Try a different search query"
          />
        )}

        <AnimatePresence>
          {searchResults.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4"
            >
              <p className={`text-sm font-medium mb-4 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Found {searchResults.length} results
              </p>

              {searchResults.map((result, idx) => (
                <motion.div
                  key={result.id || idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className={`p-5 rounded-2xl border backdrop-blur-xl ${
                    darkMode
                      ? 'bg-gray-800/80 border-gray-700/50'
                      : 'bg-white/80 border-gray-200/50'
                  } shadow-lg`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className={`w-4 h-4 flex-shrink-0 ${darkMode ? 'text-blue-400' : 'text-blue-600'}`} />
                        <h4 className={`font-bold truncate ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                          {result.metadata?.title || result.metadata?.source || 'Untitled'}
                        </h4>
                      </div>
                      <p className={`text-sm line-clamp-3 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        {result.content || result.text || result.page_content || ''}
                      </p>
                      {result.score !== undefined && (
                        <Badge variant="info" className="mt-2">
                          Score: {(result.score * 100).toFixed(1)}%
                        </Badge>
                      )}
                    </div>
                    <button
                      onClick={() => handleDelete(result.id, result.metadata?.title)}
                      className={`p-2 rounded-xl transition-colors flex-shrink-0 ${
                        darkMode
                          ? 'hover:bg-red-500/20 text-gray-500 hover:text-red-400'
                          : 'hover:bg-red-50 text-gray-400 hover:text-red-600'
                      }`}
                      title="Delete document"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}

export default DocumentsPage
