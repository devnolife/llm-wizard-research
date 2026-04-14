import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { DarkModeProvider, useDarkMode } from './contexts/DarkModeContext'
import { ToastProvider } from './contexts/ToastContext'
import ErrorBoundary from './components/common/ErrorBoundary'
import Navbar from './components/layout/Navbar'
import UploadPage from './components/pages/UploadPage'
import AnalysisResults from './components/pages/AnalysisResults'
import SearchPage from './components/pages/SearchPage'
import ChatPage from './components/pages/ChatPage'
import DocumentsPage from './components/pages/DocumentsPage'
import NotFoundPage from './components/pages/NotFoundPage'

const AppContent = () => {
  const { darkMode } = useDarkMode()

  return (
    <div className={`min-h-screen transition-all duration-500 relative overflow-hidden ${
      darkMode
        ? 'bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900'
        : 'bg-gradient-to-br from-blue-50 via-indigo-50 via-purple-50 to-pink-50'
    }`}>
      {/* Animated background shapes */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className={`absolute -top-40 -right-40 w-96 h-96 rounded-full blur-3xl opacity-20 animate-pulse ${
          darkMode
            ? 'bg-gradient-to-br from-blue-500 to-purple-500'
            : 'bg-gradient-to-br from-blue-300 to-purple-300'
        }`} style={{ animationDuration: '8s' }} />
        <div className={`absolute -bottom-40 -left-40 w-96 h-96 rounded-full blur-3xl opacity-20 animate-pulse ${
          darkMode
            ? 'bg-gradient-to-tr from-purple-500 to-pink-500'
            : 'bg-gradient-to-tr from-purple-300 to-pink-300'
        }`} style={{ animationDuration: '10s', animationDelay: '2s' }} />
        <div className={`absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full blur-3xl opacity-10 animate-pulse ${
          darkMode
            ? 'bg-gradient-to-br from-cyan-500 to-blue-500'
            : 'bg-gradient-to-br from-cyan-300 to-blue-300'
        }`} style={{ animationDuration: '12s', animationDelay: '4s' }} />
        <div className={`absolute inset-0 opacity-[0.02] ${
          darkMode ? 'bg-white' : 'bg-gray-900'
        }`} style={{
          backgroundImage: `
            linear-gradient(${darkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'} 1px, transparent 1px),
            linear-gradient(90deg, ${darkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'} 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }} />
      </div>

      {/* Content */}
      <div className="relative z-10">
        <Navbar />
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/results/:jobId" element={<AnalysisResults />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </ErrorBoundary>
      </div>
    </div>
  )
}

function App() {
  return (
    <DarkModeProvider>
      <ToastProvider>
        <Router>
          <AppContent />
        </Router>
      </ToastProvider>
    </DarkModeProvider>
  )
}

export default App
