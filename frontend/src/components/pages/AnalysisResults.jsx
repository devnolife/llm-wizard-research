import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, AlertTriangle, Lightbulb, Map, ChevronDown, ChevronUp, Download, Loader } from 'lucide-react'
import axios from 'axios'

const AnalysisResults = ({ darkMode }) => {
  const { jobId } = useParams()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [expandedSections, setExpandedSections] = useState({
    topics: true,
    summary: true,
    gaps: true,
    recommendations: true,
    roadmap: true
  })

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const response = await axios.get(`http://localhost:8000/api/analysis-status/${jobId}`)

        if (response.data.status === 'completed') {
          setData(response.data.results)
          setLoading(false)
        } else if (response.data.status === 'processing') {
          // Poll again after 3 seconds
          setTimeout(fetchResults, 3000)
        } else if (response.data.status === 'failed') {
          setError(response.data.error || 'Analysis failed')
          setLoading(false)
        }
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to fetch results')
        setLoading(false)
      }
    }

    fetchResults()
  }, [jobId])

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  const downloadResults = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `analysis-${jobId}.json`
    a.click()
  }

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-6">
        <motion.div className="relative">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          >
            <Loader className={`w-20 h-20 ${darkMode ? 'text-blue-400' : 'text-blue-600'}`} />
          </motion.div>
          <motion.div
            className="absolute inset-0 blur-2xl"
            animate={{ opacity: [0.3, 0.6, 0.3], scale: [1, 1.2, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <Loader className={`w-20 h-20 ${darkMode ? 'text-blue-400' : 'text-blue-600'}`} />
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-center"
        >
          <h3 className={`text-2xl font-bold mb-2 bg-gradient-to-r ${
            darkMode
              ? 'from-blue-400 via-purple-400 to-pink-400'
              : 'from-blue-600 via-purple-600 to-pink-600'
          } bg-clip-text text-transparent`}>
            Analyzing Your Research
          </h3>
          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Please wait while we process your documents...
          </p>
        </motion.div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-2xl mx-auto text-center"
        >
          <motion.div
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="inline-block mb-6"
          >
            <AlertTriangle className="w-20 h-20 text-red-500 mx-auto" />
          </motion.div>
          <h2 className={`text-3xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Analysis Failed
          </h2>
          <p className={`text-lg ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>{error}</p>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => window.location.href = '/'}
            className={`mt-8 px-8 py-4 rounded-2xl font-semibold ${
              darkMode
                ? 'bg-gradient-to-r from-blue-600 to-purple-600'
                : 'bg-gradient-to-r from-blue-500 to-purple-500'
            } text-white shadow-xl`}
          >
            Try Again
          </motion.button>
        </motion.div>
      </div>
    )
  }

  const SectionCard = ({ title, icon: Icon, children, section }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      className={`group rounded-3xl overflow-hidden backdrop-blur-xl border transition-all duration-300 ${
        darkMode
          ? 'bg-gray-800/80 border-gray-700/50 hover:bg-gray-700/80'
          : 'bg-white/80 border-gray-200/50 hover:bg-white/90'
      } shadow-xl hover:shadow-2xl`}
    >
      <button
        onClick={() => toggleSection(section)}
        className={`w-full p-7 flex items-center justify-between transition-colors`}
      >
        <div className="flex items-center space-x-4">
          <motion.div
            whileHover={{ rotate: 360 }}
            transition={{ duration: 0.5 }}
            className={`p-3 rounded-2xl ${
              darkMode
                ? 'bg-gradient-to-br from-blue-500/20 to-purple-500/20'
                : 'bg-gradient-to-br from-blue-500/10 to-purple-500/10'
            }`}
          >
            <Icon className={`w-6 h-6 ${darkMode ? 'text-blue-400' : 'text-blue-600'}`} />
          </motion.div>
          <h3 className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            {title}
          </h3>
        </div>
        <motion.div
          animate={{ rotate: expandedSections[section] ? 180 : 0 }}
          transition={{ duration: 0.3 }}
        >
          <ChevronDown className={`w-5 h-5 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`} />
        </motion.div>
      </button>

      <AnimatePresence>
        {expandedSections[section] && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className={`px-7 pb-7 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )

  return (
    <div className="container mx-auto px-6 py-12">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 100 }}
        className="text-center mb-16"
      >
        <motion.div
          animate={{ scale: [1, 1.15, 1] }}
          transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
          className="inline-block mb-6 relative"
        >
          <CheckCircle className="w-20 h-20 text-green-500" />
          <motion.div
            className="absolute inset-0 blur-2xl"
            animate={{ opacity: [0.3, 0.6, 0.3] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <CheckCircle className="w-20 h-20 text-green-500" />
          </motion.div>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className={`text-5xl md:text-6xl font-extrabold mb-4 bg-gradient-to-r ${
            darkMode
              ? 'from-green-400 via-emerald-400 to-teal-400'
              : 'from-green-600 via-emerald-600 to-teal-600'
          } bg-clip-text text-transparent`}
        >
          Analysis Complete!
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className={`text-xl mb-8 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}
        >
          Here are your AI-generated insights
        </motion.p>

        <motion.button
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          whileHover={{ scale: 1.05, y: -2 }}
          whileTap={{ scale: 0.95 }}
          onClick={downloadResults}
          className={`relative group px-8 py-4 rounded-2xl flex items-center gap-3 mx-auto font-semibold overflow-hidden ${
            darkMode
              ? 'bg-gradient-to-r from-gray-700 to-gray-600 hover:from-gray-600 hover:to-gray-500 text-white'
              : 'bg-gradient-to-r from-gray-100 to-gray-200 hover:from-gray-200 hover:to-gray-300 text-gray-900'
          } shadow-xl`}
        >
          <Download className="w-5 h-5 relative z-10" />
          <span className="relative z-10">Download Results</span>

          {/* Hover effect */}
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
          />
        </motion.button>
      </motion.div>

      {/* Results */}
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Topics */}
        {data?.topics && (
          <SectionCard title="Extracted Topics" icon={CheckCircle} section="topics">
            <div className="grid gap-3 md:grid-cols-2">
              {data.topics.map((topic, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: idx * 0.05 }}
                  whileHover={{ scale: 1.03, x: 4 }}
                  className={`group relative p-5 rounded-2xl border transition-all duration-300 ${
                    darkMode
                      ? 'bg-gradient-to-br from-blue-500/10 to-purple-500/10 border-blue-500/20 hover:border-blue-500/40'
                      : 'bg-gradient-to-br from-blue-50 to-purple-50 border-blue-200/50 hover:border-blue-400/50'
                  } shadow-md hover:shadow-lg`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">🎯</span>
                    <span className={`font-semibold flex-1 ${
                      darkMode ? 'text-white' : 'text-gray-900'
                    }`}>
                      {topic}
                    </span>
                  </div>

                  {/* Gradient accent */}
                  <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-purple-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-b-2xl" />
                </motion.div>
              ))}
            </div>
          </SectionCard>
        )}

        {/* Summary */}
        {data?.summary && (
          <SectionCard title="Research Summary" icon={CheckCircle} section="summary">
            <div className="prose max-w-none">
              <p className={`whitespace-pre-wrap ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                {data.summary}
              </p>
            </div>
          </SectionCard>
        )}

        {/* Gaps */}
        {data?.gaps && data.gaps.length > 0 && (
          <SectionCard title="Research Gaps" icon={AlertTriangle} section="gaps">
            <div className="space-y-4">
              {data.gaps.map((gap, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.08 }}
                  whileHover={{ x: 4, scale: 1.01 }}
                  className={`group relative p-6 rounded-2xl border-l-4 backdrop-blur-sm transition-all duration-300 ${
                    darkMode
                      ? 'bg-gradient-to-r from-yellow-500/10 to-orange-500/5 border-yellow-500 hover:bg-yellow-500/15'
                      : 'bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-500 hover:bg-yellow-100'
                  } shadow-md hover:shadow-lg`}
                >
                  <div className="flex items-start gap-4">
                    <motion.div
                      whileHover={{ rotate: [0, -10, 10, 0] }}
                      transition={{ duration: 0.5 }}
                      className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center font-bold ${
                        darkMode
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : 'bg-yellow-200 text-yellow-700'
                      }`}
                    >
                      {idx + 1}
                    </motion.div>
                    <div className="flex-1">
                      <h4 className={`font-bold text-lg mb-2 ${
                        darkMode ? 'text-yellow-400' : 'text-yellow-700'
                      }`}>
                        Research Gap #{idx + 1}
                      </h4>
                      <p className={`text-sm leading-relaxed ${
                        darkMode ? 'text-gray-300' : 'text-gray-700'
                      }`}>
                        {gap}
                      </p>
                    </div>
                  </div>

                  {/* Warning icon decoration */}
                  <div className={`absolute top-4 right-4 opacity-10 group-hover:opacity-20 transition-opacity`}>
                    <AlertTriangle className="w-8 h-8" />
                  </div>
                </motion.div>
              ))}
            </div>
          </SectionCard>
        )}

        {/* Recommendations */}
        {data?.recommendations && (
          <SectionCard title="Recommendations" icon={Lightbulb} section="recommendations">
            <div className="prose max-w-none">
              <p className={`whitespace-pre-wrap ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                {data.recommendations}
              </p>
            </div>
          </SectionCard>
        )}

        {/* Roadmap */}
        {data?.roadmap && (
          <SectionCard title="Research Roadmap" icon={Map} section="roadmap">
            <div className="prose max-w-none">
              <p className={`whitespace-pre-wrap ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                {data.roadmap}
              </p>
            </div>
          </SectionCard>
        )}
      </div>
    </div>
  )
}

export default AnalysisResults
