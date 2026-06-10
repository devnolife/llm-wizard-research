import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { DarkModeProvider } from './contexts/DarkModeContext'
import { ToastProvider } from './contexts/ToastContext'
import ErrorBoundary from './components/common/ErrorBoundary'
import Navbar from './components/layout/Navbar'
import UploadPage from './components/pages/UploadPage'
import AnalysisResults from './components/pages/AnalysisResults'
import SearchPage from './components/pages/SearchPage'
import ChatPage from './components/pages/ChatPage'
import DocumentsPage from './components/pages/DocumentsPage'
import NotFoundPage from './components/pages/NotFoundPage'
import RevisionSummaryPage from './components/pages/RevisionSummaryPage'
import GraphPage from './components/pages/GraphPage'

function App() {
  return (
    <DarkModeProvider>
      <ToastProvider>
        <Router>
          <div className="min-h-screen bg-background text-foreground">
            <Navbar />
            <ErrorBoundary>
              <main>
                <Routes>
                  <Route path="/" element={<UploadPage />} />
                  <Route path="/results/:jobId" element={<AnalysisResults />} />
                  <Route path="/search" element={<SearchPage />} />
                  <Route path="/chat" element={<ChatPage />} />
                  <Route path="/documents" element={<DocumentsPage />} />
                  <Route path="/graph" element={<GraphPage />} />
                  <Route path="/revisi" element={<RevisionSummaryPage />} />
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </main>
            </ErrorBoundary>
          </div>
        </Router>
      </ToastProvider>
    </DarkModeProvider>
  )
}

export default App
