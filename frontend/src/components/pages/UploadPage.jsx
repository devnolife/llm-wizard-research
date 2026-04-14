import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, FileText, X, Sparkles } from 'lucide-react'
import { analysisService } from '../../services/analysisService'
import { useDarkMode } from '../../contexts/DarkModeContext'
import { useToast } from '../../contexts/ToastContext'

const UploadPage = () => {
  const { darkMode } = useDarkMode()
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

      // Navigate to results page
      navigate(`/results/${response.job_id}`)
    } catch (err) {
      setError(err.userMessage || 'Upload failed. Please try again.')
      toast.error(err.userMessage || 'Upload failed')
      setUploading(false)
    }
  }

  return (
    <div className="container mx-auto px-6 py-12">
      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, type: "spring" }}
        className="text-center mb-16"
      >
        <motion.div
          animate={{
            rotate: [0, 10, -10, 0],
            scale: [1, 1.1, 1]
          }}
          transition={{ duration: 3, repeat: Infinity, repeatDelay: 2 }}
          className="inline-block mb-6 relative"
        >
          <Sparkles className={`w-20 h-20 ${darkMode ? 'text-purple-400' : 'text-purple-600'}`} />
          <motion.div
            className="absolute inset-0 blur-2xl"
            animate={{ opacity: [0.3, 0.6, 0.3] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <Sparkles className={`w-20 h-20 ${darkMode ? 'text-purple-400' : 'text-purple-600'}`} />
          </motion.div>
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className={`text-5xl md:text-6xl font-extrabold leading-tight mb-6 bg-gradient-to-r ${
            darkMode
              ? 'from-blue-400 via-purple-400 to-pink-400'
              : 'from-blue-600 via-purple-600 to-pink-600'
          } bg-clip-text text-transparent`}
        >
          Auto-Analyze Your Research
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className={`text-lg md:text-xl max-w-3xl mx-auto leading-relaxed ${
            darkMode ? 'text-gray-300' : 'text-slate-600'
          }`}
        >
          Upload PDF papers once. Our AI extracts core topics, detects meaningful research gaps,
          and synthesizes recommendations automatically.
        </motion.p>

        <div className="relative mt-10 grid gap-5 md:grid-cols-3 max-w-4xl mx-auto">
          {[{
            label: 'Documents Processed', value: '1.4K+', accent: 'from-blue-500 to-cyan-400', icon: '📚'
          }, {
            label: 'Topics Identified', value: '320+', accent: 'from-purple-500 to-pink-500', icon: '🎯'
          }, {
            label: 'Avg. Analysis Time', value: '~2 min', accent: 'from-amber-500 to-orange-500', icon: '⚡'
          }].map((stat, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + idx * 0.1 }}
              whileHover={{ y: -8, scale: 1.05 }}
              className={`relative group rounded-3xl border p-6 backdrop-blur-lg transition-all duration-300 ${
                darkMode
                  ? 'border-white/10 bg-white/5 hover:bg-white/10 shadow-xl'
                  : 'border-white/50 bg-white/50 hover:bg-white/70 shadow-2xl'
              }`}
            >
              <div className="text-3xl mb-3">{stat.icon}</div>
              <p className={`text-xs uppercase tracking-wider font-semibold mb-2 ${
                darkMode ? 'text-gray-400' : 'text-gray-600'
              }`}>
                {stat.label}
              </p>
              <p className={`text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r ${stat.accent}`}>
                {stat.value}
              </p>

              {/* Glow effect on hover */}
              <motion.div
                className={`absolute inset-0 rounded-3xl blur-xl bg-gradient-to-r ${stat.accent} opacity-0 group-hover:opacity-20 transition-opacity duration-300`}
              />
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Upload Area */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.5, type: "spring", stiffness: 100 }}
        className="max-w-4xl mx-auto"
      >
        <motion.div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          animate={isDragging ? { scale: 1.02 } : { scale: 1 }}
          className={`relative rounded-[32px] border-2 border-dashed p-16 transition-all duration-300 backdrop-blur-xl ${
            isDragging
              ? 'border-blue-500/70 bg-gradient-to-br from-blue-500/20 via-purple-500/20 to-pink-500/20 shadow-2xl shadow-blue-500/20'
              : darkMode
                ? 'border-white/20 bg-gradient-to-br from-white/5 to-white/10 hover:bg-white/15 shadow-xl'
                : 'border-gray-300/60 bg-gradient-to-br from-white/80 to-white/60 hover:bg-white/90 shadow-2xl'
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

          <label
            htmlFor="file-input"
            className="cursor-pointer block text-center"
          >
            <motion.div
              animate={{ y: [0, -15, 0] }}
              transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
              className="relative mx-auto mb-8"
            >
              <div className={`flex h-24 w-24 items-center justify-center rounded-3xl border-2 ${
                darkMode
                  ? 'border-white/30 bg-gradient-to-br from-blue-500/20 to-purple-500/20'
                  : 'border-gray-300/50 bg-gradient-to-br from-blue-50 to-purple-50'
              } shadow-lg mx-auto`}>
                <Upload className={`w-12 h-12 ${
                  darkMode ? 'text-blue-400' : 'text-blue-600'
                }`} />
              </div>

              {/* Animated rings */}
              <motion.div
                className="absolute inset-0 rounded-3xl border-2 border-blue-500/30"
                animate={{ scale: [1, 1.3, 1], opacity: [0.5, 0, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              <motion.div
                className="absolute inset-0 rounded-3xl border-2 border-purple-500/30"
                animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
              />
            </motion.div>

            <h3 className={`text-3xl font-bold mb-3 ${
              darkMode ? 'text-white' : 'text-gray-900'
            }`}>
              Drop PDF files here
            </h3>

            <p className={`text-base ${
              darkMode ? 'text-gray-400' : 'text-gray-600'
            }`}>
              or click to browse from your device
            </p>

            <p className={`text-sm mt-3 ${
              darkMode ? 'text-gray-500' : 'text-gray-500'
            }`}>
              Supports: PDF files up to 50MB
            </p>
          </label>

          {/* Decorative gradient blobs */}
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 w-32 h-32 bg-gradient-to-tr from-pink-500/10 to-orange-500/10 rounded-full blur-3xl" />
        </motion.div>

        {/* File List */}
        <AnimatePresence>
          {files.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className="mt-8 space-y-3"
            >
              {files.map((file, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.05 }}
                  whileHover={{ x: 4 }}
                  className={`relative group flex items-center justify-between p-5 rounded-2xl backdrop-blur-lg border ${
                    darkMode
                      ? 'bg-gray-800/80 border-gray-700/50 hover:bg-gray-700/80'
                      : 'bg-white/80 border-gray-200/50 hover:bg-white/90'
                  } shadow-lg transition-all duration-300`}
                >
                  <div className="flex items-center space-x-4 flex-1">
                    <div className={`p-2.5 rounded-xl ${
                      darkMode
                        ? 'bg-blue-500/20'
                        : 'bg-blue-500/10'
                    }`}>
                      <FileText className={`w-5 h-5 ${
                        darkMode ? 'text-blue-400' : 'text-blue-600'
                      }`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-semibold truncate ${
                        darkMode ? 'text-white' : 'text-gray-900'
                      }`}>
                        {file.name}
                      </p>
                      <p className={`text-xs ${
                        darkMode ? 'text-gray-500' : 'text-gray-500'
                      }`}>
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>

                  {!uploading && (
                    <motion.button
                      whileHover={{ scale: 1.15, rotate: 90 }}
                      whileTap={{ scale: 0.9 }}
                      onClick={() => removeFile(index)}
                      className={`p-2 rounded-xl transition-colors ${
                        darkMode
                          ? 'hover:bg-red-500/20 text-red-400'
                          : 'hover:bg-red-100 text-red-600'
                      }`}
                    >
                      <X className="w-5 h-5" />
                    </motion.button>
                  )}

                  {/* Border gradient effect */}
                  <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-blue-500/0 via-purple-500/0 to-pink-500/0 group-hover:from-blue-500/10 group-hover:via-purple-500/10 group-hover:to-pink-500/10 transition-all duration-300" />
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Upload Button */}
        {files.length > 0 && !uploading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-10 text-center"
          >
            <motion.button
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleUploadAndAnalyze}
              className="relative group px-10 py-5 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 text-white font-bold text-lg rounded-2xl shadow-2xl overflow-hidden"
            >
              {/* Animated gradient overlay */}
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
              />

              {/* Button content */}
              <span className="relative z-10 flex items-center gap-2">
                <motion.span
                  animate={{ rotate: [0, 15, 0] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  🚀
                </motion.span>
                Upload & Auto-Analyze ({files.length} file{files.length > 1 ? 's' : ''})
              </span>

              {/* Glow effect */}
              <motion.div
                className="absolute inset-0 blur-xl bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 opacity-50"
                animate={{ opacity: [0.3, 0.6, 0.3] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </motion.button>
          </motion.div>
        )}

        {/* Progress Bar */}
        {uploading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8"
          >
            <div className={`relative p-8 rounded-3xl backdrop-blur-xl border ${
              darkMode
                ? 'bg-gray-800/80 border-gray-700/50'
                : 'bg-white/80 border-gray-200/50'
            } shadow-2xl overflow-hidden`}>
              <div className="flex items-center justify-between mb-4">
                <span className={`text-base font-bold ${
                  darkMode ? 'text-white' : 'text-gray-900'
                }`}>
                  {progress < 100 ? '⬆️ Uploading...' : '🔄 Processing & Analyzing...'}
                </span>
                <motion.span
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                  className={`text-lg font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent`}
                >
                  {progress}%
                </motion.span>
              </div>

              <div className={`relative h-3 rounded-full overflow-hidden ${
                darkMode ? 'bg-gray-700' : 'bg-gray-200'
              }`}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                  className="h-full bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 relative"
                >
                  {/* Shimmer effect */}
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                    animate={{ x: ['-100%', '200%'] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                  />
                </motion.div>
              </div>

              {progress === 100 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-6 flex items-center justify-center gap-2"
                >
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  >
                    <Sparkles className={`w-5 h-5 ${
                      darkMode ? 'text-purple-400' : 'text-purple-600'
                    }`} />
                  </motion.div>
                  <p className={`text-sm font-medium ${
                    darkMode ? 'text-gray-300' : 'text-gray-700'
                  }`}>
                    Extracting topics and generating insights... This may take a minute.
                  </p>
                </motion.div>
              )}

              {/* Animated background particles */}
              <div className="absolute top-0 left-0 w-20 h-20 bg-blue-500/10 rounded-full blur-2xl animate-pulse" />
              <div className="absolute bottom-0 right-0 w-20 h-20 bg-purple-500/10 rounded-full blur-2xl animate-pulse" style={{ animationDelay: '1s' }} />
            </div>
          </motion.div>
        )}

        {/* Error Message */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`mt-6 p-5 rounded-2xl border backdrop-blur-lg ${
              darkMode
                ? 'bg-red-500/10 border-red-500/50'
                : 'bg-red-50/80 border-red-500/30'
            } shadow-lg`}
          >
            <div className="flex items-start space-x-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <p className={`font-semibold mb-1 ${
                  darkMode ? 'text-red-400' : 'text-red-700'
                }`}>
                  Upload Failed
                </p>
                <span className={`text-sm ${
                  darkMode ? 'text-red-300' : 'text-red-600'
                }`}>
                  {error}
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </motion.div>

      {/* Features */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        className="mt-20 grid gap-8 md:grid-cols-3 max-w-6xl mx-auto"
      >
        {[
          {
            icon: '🎯',
            title: 'Auto Topic Extraction',
            desc: 'AI identifies dominant research directions per paper automatically.',
            gradient: 'from-blue-500 to-cyan-500'
          },
          {
            icon: '🔍',
            title: 'Gap Detection',
            desc: 'Surface understudied angles and unanswered questions from combined context.',
            gradient: 'from-purple-500 to-pink-500'
          },
          {
            icon: '💡',
            title: 'Smart Recommendations',
            desc: 'Turn insights into clear next steps, backed by the uploaded evidence.',
            gradient: 'from-amber-500 to-orange-500'
          }
        ].map((feature, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 + idx * 0.1 }}
            whileHover={{ y: -12, scale: 1.02 }}
            className={`group relative rounded-3xl border p-8 text-center backdrop-blur-xl transition-all duration-300 ${
              darkMode
                ? 'border-white/10 bg-gradient-to-br from-white/5 to-white/10 hover:bg-white/15'
                : 'border-white/50 bg-gradient-to-br from-white/70 to-white/50 hover:bg-white/90'
            } shadow-xl hover:shadow-2xl overflow-hidden`}
          >
            {/* Gradient background on hover */}
            <motion.div
              className={`absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300 bg-gradient-to-br ${feature.gradient}`}
            />

            {/* Icon with animated ring */}
            <motion.div
              className="relative inline-block mb-6"
              whileHover={{ rotate: [0, -10, 10, 0] }}
              transition={{ duration: 0.5 }}
            >
              <div className={`text-5xl relative z-10`}>{feature.icon}</div>
              <motion.div
                className={`absolute inset-0 -m-2 rounded-full bg-gradient-to-r ${feature.gradient} opacity-20 blur-xl`}
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </motion.div>

            <h4 className={`text-xl font-bold mb-3 relative z-10 ${
              darkMode ? 'text-white' : 'text-gray-900'
            }`}>
              {feature.title}
            </h4>

            <p className={`text-sm leading-relaxed relative z-10 ${
              darkMode ? 'text-gray-400' : 'text-gray-600'
            }`}>
              {feature.desc}
            </p>

            {/* Bottom gradient bar */}
            <motion.div
              className={`absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r ${feature.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}
            />
          </motion.div>
        ))}
      </motion.div>
    </div>
  )
}

export default UploadPage
