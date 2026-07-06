import { useEffect, useState, useRef } from 'react'
import Ask from './pages/Ask'
import Verify from './pages/Verify'
import CorpusHealth from './pages/CorpusHealth'
import PipelineDiagram from './components/PipelineDiagram'
import { getSystemStatus } from './api/client'
import { Button, Pill, Surface, cx } from './components/ui'

function App() {
  const [currentPage, setCurrentPage] = useState('hero') // 'hero', 'ask', 'verify', 'corpus'
  const [systemStatus, setSystemStatus] = useState(null)
  const [statusError, setStatusError] = useState(null)

  useEffect(() => {
    const loadStatus = async () => {
      try {
        const status = await getSystemStatus()
        setSystemStatus(status)
      } catch (error) {
        setStatusError(error.message)
      }
    }

    loadStatus()
  }, [])

  const navigateTo = (page) => {
    if (document.startViewTransition) {
      document.startViewTransition(() => {
        setCurrentPage(page)
      })
    } else {
      setCurrentPage(page)
    }
  }

  if (currentPage !== 'hero') {
    return (
      <div className="min-h-screen bg-slate-900 text-white">
        <nav className="sticky top-0 z-50 border-b border-slate-700 bg-slate-900/95 backdrop-blur">
          <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between">
              <button
                onClick={() => navigateTo('hero')}
                className="text-xl font-semibold text-gold-400 hover:text-gold-300 transition-colors"
              >
                ← ATTEST
              </button>
              <div className="flex items-center gap-4">
                <button
                  onClick={() => navigateTo('ask')}
                  className={cx(
                    "px-3 py-1 text-sm rounded transition-colors",
                    currentPage === 'ask' ? "bg-gold-500 text-slate-900" : "text-gray-300 hover:text-white"
                  )}
                >
                  Ask
                </button>
                <button
                  onClick={() => navigateTo('verify')}
                  className={cx(
                    "px-3 py-1 text-sm rounded transition-colors",
                    currentPage === 'verify' ? "bg-gold-500 text-slate-900" : "text-gray-300 hover:text-white"
                  )}
                >
                  Verify
                </button>
                <button
                  onClick={() => navigateTo('corpus')}
                  className={cx(
                    "px-3 py-1 text-sm rounded transition-colors",
                    currentPage === 'corpus' ? "bg-gold-500 text-slate-900" : "text-gray-300 hover:text-white"
                  )}
                >
                  Corpus
                </button>
                <a
                  href="https://github.com/nikitayk/Attest"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-gray-300 hover:text-white transition-colors"
                >
                  GitHub
                </a>
              </div>
            </div>
          </div>
        </nav>
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
          {currentPage === 'ask' && <Ask systemStatus={systemStatus} />}
          {currentPage === 'verify' && <Verify systemStatus={systemStatus} />}
          {currentPage === 'corpus' && <CorpusHealth systemStatus={systemStatus} />}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Sticky Nav */}
      <nav className="sticky top-0 z-50 border-b border-slate-700 bg-slate-900/95 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="text-2xl font-bold text-gold-400">ATTEST</div>
            <div className="flex items-center gap-6">
              <a
                href="https://github.com/nikitayk/Attest"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-gold-400 hover:text-gold-300 transition-colors"
              >
                GitHub ↗
              </a>
              <a
                href="https://nikitayk.github.io/SENTINEL"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Pill tone="accent">SENTINEL ↗</Pill>
              </a>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 text-center">
          <div className="space-y-8">
            <div className="flex flex-wrap items-center justify-center gap-2 hero-stagger-1">
              <Pill tone="accent">🔏 Don't trust the citation. Verify the proof.</Pill>
            </div>

            <h1 className="text-6xl sm:text-7xl lg:text-8xl font-bold text-white hero-stagger-2">
              ATTEST
            </h1>

            <p className="max-w-3xl mx-auto text-xl text-gray-400 hero-stagger-3">
              Signed, hashed, Merkle-proofed — RAG you don't have to take on faith.
            </p>

            {/* Feature Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
              <Surface
                className="p-8 text-left cursor-pointer hover:border-gold-400 transition-all duration-200"
                onClick={() => navigateTo('ask')}
              >
                <div className="text-4xl mb-4">❓</div>
                <h3 className="text-2xl font-semibold text-white mb-2">Ask</h3>
                <p className="text-gray-400">
                  Query the corpus and get answers with verifiable cryptographic certificates.
                </p>
              </Surface>

              <Surface
                className="p-8 text-left cursor-pointer hover:border-gold-400 transition-all duration-200"
                onClick={() => navigateTo('verify')}
              >
                <div className="text-4xl mb-4">✓</div>
                <h3 className="text-2xl font-semibold text-white mb-2">Verify</h3>
                <p className="text-gray-400">
                  Verify certificates without trusting the backend — zero-trust proof.
                </p>
              </Surface>

              <Surface
                className="p-8 text-left cursor-pointer hover:border-gold-400 transition-all duration-200"
                onClick={() => navigateTo('corpus')}
              >
                <div className="text-4xl mb-4">📁</div>
                <h3 className="text-2xl font-semibold text-white mb-2">Corpus</h3>
                <p className="text-gray-400">
                  Monitor corpus health and see tampering detection in action.
                </p>
              </Surface>
            </div>
          </div>
        </div>
      </section>

      {/* Pipeline Diagram */}
      <section className="py-16 bg-slate-800">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <p className="text-sm font-semibold uppercase tracking-wider text-gold-400 mb-4">
              How it works
            </p>
            <h2 className="text-3xl font-semibold text-white">
              Cryptographic Chain of Custody
            </h2>
          </div>
          <PipelineDiagram />
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-slate-700 bg-slate-900">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="space-y-8">
            <div className="space-y-4">
              <p className="text-sm text-gray-400">
                Limitations: No protection against pre-ingestion poisoning. Compromised signing key breaks trust model.
                <a
                  href="https://github.com/nikitayk/Attest#limitations"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gold-400 hover:text-gold-300 ml-2"
                >
                  Read more on GitHub →
                </a>
              </p>
            </div>

            <div className="space-y-4">
              <p className="text-sm font-semibold text-white">More from the trust stack</p>
              <div className="flex flex-wrap gap-4">
                <a
                  href="https://nikitayk.github.io/SENTINEL"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-gold-400 hover:text-gold-300 transition-colors"
                >
                  SENTINEL — Input trust layer
                </a>
              </div>
            </div>

            <p className="text-xs text-gray-500">
              © 2026 ATTEST. Built with cryptographic integrity.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
