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
  const [demoTab, setDemoTab] = useState('ask')
  const [corpusTab, setCorpusTab] = useState('demo')

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

  const scrollToSection = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
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
              <button onClick={() => scrollToSection('problem')} className="text-sm text-gray-300 hover:text-white transition-colors">How it works</button>
              <button onClick={() => scrollToSection('demo')} className="text-sm text-gray-300 hover:text-white transition-colors">Try it</button>
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

      {/* Hero Section (Simplified) */}
      <section className="py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 text-center">
          <div className="space-y-8">
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Pill tone="accent">🔏 Don't Trust. Verify.</Pill>
              <Pill tone="neutral">CRYPTOGRAPHIC PROVENANCE · RAG INTEGRITY</Pill>
            </div>

            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-white">
              RAG answers that carry their own proof.
            </h1>

            <p className="max-w-3xl mx-auto text-xl text-gray-400">
              ATTEST hashes every source chunk into a Merkle tree, signs the manifest with Ed25519, and re-checks it before every answer — so a poisoned document gets quarantined, not cited. Any certificate can be verified offline, by anyone, without trusting my backend.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-4">
              <Button variant="primary" onClick={() => scrollToSection('demo')}>
                Try the Demo →
              </Button>
              <Button variant="secondary" onClick={() => window.open('https://github.com/nikitayk/Attest/blob/main/backend/verifier/verify.py', '_blank')}>
                Read the Verifier Source ↗
              </Button>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
              <span className="text-sm text-gray-500">SHA-256 + Merkle + Ed25519</span>
              <span className="text-gray-700">·</span>
              <span className="text-sm text-gray-500">Fail-closed on tamper</span>
              <span className="text-gray-700">·</span>
              <span className="text-sm text-gray-500">Offline zero-trust verifier</span>
              <span className="text-gray-700">·</span>
              <span className="text-sm text-gray-500">Self-contained certificates</span>
            </div>

            <div className="pt-4">
              <a href="https://nikitayk.github.io/SENTINEL" target="_blank" rel="noopener noreferrer" className="text-sm text-gold-400 hover:text-gold-300 transition-colors">
                Sibling project: SENTINEL — secures what goes in →
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* 01 - THE PROBLEM */}
      <section id="problem" className="py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="mb-12">
            <p className="text-sm font-semibold uppercase tracking-wider text-gold-400 mb-4">
              01 · THE PROBLEM
            </p>
            <h2 className="text-3xl font-semibold text-white">
              RAG cites sources. It can't prove they're real.
            </h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Surface className="p-8">
              <h3 className="text-2xl font-semibold text-white mb-3">Poisoning</h3>
              <p className="text-gray-400">Documents can be altered after ingestion, changing answers without detection.</p>
            </Surface>
            <Surface className="p-8">
              <h3 className="text-2xl font-semibold text-white mb-3">Staleness</h3>
              <p className="text-gray-400">Citations don't prove the document existed at a specific point in time.</p>
            </Surface>
            <Surface className="p-8">
              <h3 className="text-2xl font-semibold text-white mb-3">Blind Trust</h3>
              <p className="text-gray-400">Third parties can't verify without trusting your backend or logs.</p>
            </Surface>
          </div>

          <div className="mt-10 flex items-center gap-3">
            <Pill tone="accent">OWASP AI06</Pill>
            <span className="text-gray-400">— Memory & Context Poisoning</span>
          </div>
        </div>
      </section>

      {/* 02 - HOW IT WORKS */}
      <section id="how-it-works" className="py-16 bg-slate-800">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="mb-12">
            <p className="text-sm font-semibold uppercase tracking-wider text-gold-400 mb-4">
              02 · HOW IT WORKS
            </p>
            <h2 className="text-3xl font-semibold text-white">
              Cryptographic chain of custody
            </h2>
          </div>
          <PipelineDiagram />
        </div>
      </section>

      {/* 03 - TRY IT */}
      <section id="demo" className="py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="mb-12">
            <p className="text-sm font-semibold uppercase tracking-wider text-gold-400 mb-4">
              03 · TRY IT
            </p>
            <h2 className="text-3xl font-semibold text-white mb-6">
              Interactive demo
            </h2>
            <div className="flex gap-3">
              <button
                onClick={() => setCorpusTab('demo')}
                className={cx(
                  "px-4 py-2 text-sm rounded-md transition-colors",
                  corpusTab === 'demo' ? "bg-gold-500 text-slate-900" : "bg-slate-800 text-gray-300 hover:bg-slate-700"
                )}
              >
                Demo Corpus
              </button>
              <button
                onClick={() => setCorpusTab('your')}
                className={cx(
                  "px-4 py-2 text-sm rounded-md transition-colors",
                  corpusTab === 'your' ? "bg-gold-500 text-slate-900" : "bg-slate-800 text-gray-300 hover:bg-slate-700"
                )}
              >
                Your Documents (coming soon)
              </button>
            </div>
          </div>

          <div className="flex gap-1 mb-6 border-b border-slate-700">
            {['ask', 'verify', 'corpus'].map((tab) => (
              <button
                key={tab}
                onClick={() => setDemoTab(tab)}
                className={cx(
                  "px-4 py-3 text-sm font-medium transition-colors border-b-2",
                  demoTab === tab 
                    ? "text-gold-400 border-gold-400" 
                    : "text-gray-400 border-transparent hover:text-gray-200"
                )}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          <div className="min-h-[500px]">
            {demoTab === 'ask' && <Ask systemStatus={systemStatus} />}
            {demoTab === 'verify' && <Verify systemStatus={systemStatus} />}
            {demoTab === 'corpus' && <CorpusHealth systemStatus={systemStatus} />}
          </div>
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
