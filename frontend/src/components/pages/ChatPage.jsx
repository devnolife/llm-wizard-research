import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader, Trash2, MessageSquare } from 'lucide-react'
import { useToast } from '../../contexts/ToastContext'
import { analysisService } from '../../services/analysisService'
import EmptyState from '../common/EmptyState'
import PageHelp from '../common/PageHelp'
import Term from '../common/Term'
import Markdown from '../common/Markdown'

const ChatPage = () => {
  const toast = useToast()
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId] = useState(() => crypto.randomUUID())

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
      const response = await analysisService.chat(text, conversationId)
      const botMsg = {
        role: 'assistant',
        content: response.response || response.answer || response.message || JSON.stringify(response),
        timestamp: new Date(),
        sources: response.sources || [],
      }
      setMessages(prev => [...prev, botMsg])
    } catch (err) {
      toast.error(err.userMessage || 'Gagal mendapat jawaban')
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Maaf, terjadi kesalahan. Silakan coba lagi.',
        timestamp: new Date(),
        isError: true,
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const clearChat = () => {
    setMessages([])
    toast.info('Chat dibersihkan')
  }

  return (
    <div className="w-full px-6 lg:px-10 py-6 h-[calc(100vh-80px)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Asisten Penelitian</h1>
          <p className="text-sm text-muted-foreground">Tanyakan tentang korpus penelitian Anda</p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="p-2 rounded-md text-muted-foreground hover:text-destructive hover:bg-secondary transition-colors"
            title="Hapus chat"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      <PageHelp
        icon={MessageSquare}
        title="Yang akan Anda lihat di sini"
        description={<>Tanya-jawab dengan AI tentang paper yang sudah tersimpan (berbasis <Term k="RAG">RAG</Term>). Jawaban disertai daftar sumber paper yang dirujuk.</>}
        className="mb-4"
      />

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto rounded-lg border bg-card p-4 mb-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <EmptyState
              icon={MessageSquare}
              title="Mulai percakapan"
              description="Tanyakan tentang topik penelitian, gap, metodologi, atau apapun terkait paper yang Anda unggah"
            />
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'assistant' && (
                  <div className="flex-shrink-0 w-7 h-7 rounded-md bg-secondary flex items-center justify-center">
                    <Bot className="w-4 h-4 text-muted-foreground" />
                  </div>
                )}

                <div className={`max-w-[75%] px-4 py-3 rounded-lg text-sm leading-relaxed ${msg.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : msg.isError
                    ? 'bg-destructive/10 border border-destructive/30 text-destructive'
                    : 'bg-secondary text-foreground'
                  }`}>
                  {msg.role === 'assistant' && !msg.isError
                    ? <Markdown content={msg.content} className="text-current" />
                    : <p className="whitespace-pre-wrap">{msg.content}</p>}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-border/50">
                      <p className="text-xs font-medium opacity-70 mb-1">Sumber:</p>
                      {msg.sources.map((src, i) => (
                        <p key={i} className="text-xs opacity-60">• {src}</p>
                      ))}
                    </div>
                  )}
                </div>

                {msg.role === 'user' && (
                  <div className="flex-shrink-0 w-7 h-7 rounded-md bg-primary/10 flex items-center justify-center">
                    <User className="w-4 h-4 text-primary" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-7 h-7 rounded-md bg-secondary flex items-center justify-center">
                  <Bot className="w-4 h-4 text-muted-foreground" />
                </div>
                <div className="px-4 py-3 rounded-lg bg-secondary">
                  <Loader className="w-4 h-4 animate-spin text-muted-foreground" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="flex rounded-lg border overflow-hidden bg-card">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Tanyakan tentang penelitian Anda..."
          disabled={loading}
          className="flex-1 px-4 py-3 bg-transparent outline-none text-foreground placeholder:text-muted-foreground"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-4 py-3 bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </form>
    </div>
  )
}

export default ChatPage
