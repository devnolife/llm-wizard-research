import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, User, Loader, Trash2, MessageSquare } from 'lucide-react'
import { useDarkMode } from '../../contexts/DarkModeContext'
import { useToast } from '../../contexts/ToastContext'
import { analysisService } from '../../services/analysisService'
import EmptyState from '../common/EmptyState'

const ChatPage = () => {
  const { darkMode } = useDarkMode()
  const toast = useToast()
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async (e) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { role: 'user', content: text, timestamp: new Date() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const response = await analysisService.chat(text)
      const botMsg = {
        role: 'assistant',
        content: response.response || response.answer || response.message || JSON.stringify(response),
        timestamp: new Date(),
        sources: response.sources || [],
      }
      setMessages(prev => [...prev, botMsg])
    } catch (err) {
      toast.error(err.userMessage || 'Failed to get response')
      const errorMsg = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
        isError: true,
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const clearChat = () => {
    setMessages([])
    toast.info('Chat cleared')
  }

  return (
    <div className="container mx-auto px-6 py-8 max-w-4xl h-[calc(100vh-80px)] flex flex-col">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-6"
      >
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-2xl ${
            darkMode
              ? 'bg-gradient-to-br from-purple-500/20 to-pink-500/20'
              : 'bg-gradient-to-br from-purple-100 to-pink-100'
          }`}>
            <Bot className={`w-8 h-8 ${darkMode ? 'text-purple-400' : 'text-purple-600'}`} />
          </div>
          <div>
            <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Research Assistant
            </h1>
            <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Ask questions about your research corpus
            </p>
          </div>
        </div>

        {messages.length > 0 && (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={clearChat}
            className={`p-2.5 rounded-xl transition-colors ${
              darkMode
                ? 'hover:bg-gray-700 text-gray-400 hover:text-red-400'
                : 'hover:bg-gray-100 text-gray-500 hover:text-red-600'
            }`}
            title="Clear chat"
          >
            <Trash2 className="w-5 h-5" />
          </motion.button>
        )}
      </motion.div>

      {/* Messages Area */}
      <div className={`flex-1 overflow-y-auto rounded-3xl border backdrop-blur-xl p-6 mb-4 ${
        darkMode
          ? 'bg-gray-800/60 border-gray-700/50'
          : 'bg-white/60 border-gray-200/50'
      } shadow-xl`}>
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <EmptyState
              icon={MessageSquare}
              title="Start a conversation"
              description="Ask about research topics, gaps, methodologies, or anything related to your uploaded papers"
            />
          </div>
        ) : (
          <div className="space-y-6">
            <AnimatePresence>
              {messages.map((msg, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.05 }}
                  className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center ${
                      msg.isError
                        ? 'bg-red-500/20'
                        : darkMode
                          ? 'bg-purple-500/20'
                          : 'bg-purple-100'
                    }`}>
                      <Bot className={`w-4 h-4 ${
                        msg.isError ? 'text-red-400' : darkMode ? 'text-purple-400' : 'text-purple-600'
                      }`} />
                    </div>
                  )}

                  <div className={`max-w-[75%] p-4 rounded-2xl ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white'
                      : msg.isError
                        ? darkMode
                          ? 'bg-red-500/10 border border-red-500/30 text-red-300'
                          : 'bg-red-50 border border-red-200 text-red-700'
                        : darkMode
                          ? 'bg-gray-700/80 text-gray-200'
                          : 'bg-gray-100 text-gray-800'
                  }`}>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>

                    {msg.sources && msg.sources.length > 0 && (
                      <div className={`mt-3 pt-3 border-t ${
                        darkMode ? 'border-gray-600' : 'border-gray-200'
                      }`}>
                        <p className="text-xs font-semibold mb-1 opacity-70">Sources:</p>
                        {msg.sources.map((src, i) => (
                          <p key={i} className="text-xs opacity-60">• {src}</p>
                        ))}
                      </div>
                    )}
                  </div>

                  {msg.role === 'user' && (
                    <div className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center ${
                      darkMode ? 'bg-blue-500/20' : 'bg-blue-100'
                    }`}>
                      <User className={`w-4 h-4 ${darkMode ? 'text-blue-400' : 'text-blue-600'}`} />
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>

            {loading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-4"
              >
                <div className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center ${
                  darkMode ? 'bg-purple-500/20' : 'bg-purple-100'
                }`}>
                  <Bot className={`w-4 h-4 ${darkMode ? 'text-purple-400' : 'text-purple-600'}`} />
                </div>
                <div className={`px-4 py-3 rounded-2xl ${
                  darkMode ? 'bg-gray-700/80' : 'bg-gray-100'
                }`}>
                  <div className="flex gap-1.5">
                    {[0, 1, 2].map(i => (
                      <motion.div
                        key={i}
                        className={`w-2 h-2 rounded-full ${darkMode ? 'bg-gray-400' : 'bg-gray-500'}`}
                        animate={{ y: [0, -6, 0] }}
                        transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }}
                      />
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        onSubmit={handleSend}
        className={`flex rounded-2xl overflow-hidden border backdrop-blur-xl shadow-xl ${
          darkMode
            ? 'bg-gray-800/80 border-gray-700/50'
            : 'bg-white/80 border-gray-200/50'
        }`}
      >
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask about your research..."
          disabled={loading}
          className={`flex-1 px-6 py-4 bg-transparent outline-none ${
            darkMode ? 'text-white placeholder-gray-500' : 'text-gray-900 placeholder-gray-400'
          }`}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-6 py-4 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold hover:from-purple-500 hover:to-pink-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? (
            <Loader className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </motion.form>
    </div>
  )
}

export default ChatPage
