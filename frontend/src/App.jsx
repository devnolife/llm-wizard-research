import { lazy } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { DarkModeProvider } from './contexts/DarkModeContext'
import { ToastProvider } from './contexts/ToastContext'
import ErrorBoundary from './components/common/ErrorBoundary'
import LazyBoundary from './components/common/LazyBoundary'
import Navbar from './components/layout/Navbar'
import UploadPage from './components/pages/UploadPage'

const AnalysisResults = lazy(() => import('./components/pages/AnalysisResults'))
const SearchPage = lazy(() => import('./components/pages/SearchPage'))
const ChatPage = lazy(() => import('./components/pages/ChatPage'))
const DocumentsPage = lazy(() => import('./components/pages/DocumentsPage'))
const NotFoundPage = lazy(() => import('./components/pages/NotFoundPage'))
const RevisionSummaryPage = lazy(() => import('./components/pages/RevisionSummaryPage'))
const GraphPage = lazy(() => import('./components/pages/GraphPage'))

const routeElement = (element) => <ErrorBoundary>{element}</ErrorBoundary>

function App() {
  return (
    <DarkModeProvider>
      <ToastProvider>
        <Router>
          <div className="relative min-h-screen text-foreground">
            <div className="atmosphere" aria-hidden="true" />
            <div className="relative z-10">
              <Navbar />
              <ErrorBoundary>
                <main>
                  <LazyBoundary>
                    <Routes>
                      <Route path="/" element={routeElement(<UploadPage />)} />
                      <Route path="/results/:jobId" element={routeElement(<AnalysisResults />)} />
                      <Route path="/search" element={routeElement(<SearchPage />)} />
                      <Route path="/chat" element={routeElement(<ChatPage />)} />
                      <Route path="/documents" element={routeElement(<DocumentsPage />)} />
                      <Route path="/graph" element={routeElement(<GraphPage />)} />
                      <Route path="/revisi" element={routeElement(<RevisionSummaryPage />)} />
                      <Route path="*" element={routeElement(<NotFoundPage />)} />
                    </Routes>
                  </LazyBoundary>
                </main>
              </ErrorBoundary>
            </div>
          </div>
        </Router>
      </ToastProvider>
    </DarkModeProvider>
  )
}

export default App
