import { useEffect, useState, useRef } from 'react'
import Ask from './pages/Ask'
import Verify from './pages/Verify'
import CorpusHealth from './pages/CorpusHealth'
import PipelineDiagram from './components/PipelineDiagram'
import { getSystemStatus } from './api/client'
import { Button, Pill, Surface, cx } from './components/ui'

function App() {
  const [activeTab, setActiveTab] = useState('ask')
  const [systemStatus, setSystemStatus] = useState(null)
  const [statusError, setStatusError] = useState(null)
  const [corpusMode, setCorpusMode] = useState('demo')
  const problemRef = useRef(null)
  const howItWorksRef = useRef(null)
  const tryItRef = useRef(null)
  const stackRef = useRef(null)

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

  // IntersectionObserver for scroll reveal
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible')
          }
        })
      },
      { threshold: 0.1 }
    )

    const refs = [problemRef, howItWorksRef, tryItRef, stackRef]
    refs.forEach((ref) => {
      if (ref.current) {
        observer.observe(ref.current)
      }
    })

    return () => {
      refs.forEach((ref) => {
        if (ref.current) {
          observer.unobserve(ref.current)
        }
      })
    }
  }, [])

  const tabs = [
    { id: 'ask', label: 'Ask' },
    { id: 'verify', label: 'Verify' },
    { id: 'corpus-health', label: 'Corpus Health' },
  ]

  const scrollToSection = (sectionId) => {
    const element = document.getElementById(sectionId)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' })
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Sticky Nav */}
      <nav className="sticky top-0 z-50 border-b border-slate-700 bg-slate-900/95 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xl font-semibold text-gold-400">ATTEST</span>
            </div>
            <div className="flex items-center gap-6">
              <button
                onClick={() => scrollToSection('problem')}
                className="text-sm text-gray-300 hover:text-white transition-colors"
              >
                How it works
              </button>
              <button
                onClick={() => scrollToSection('try-it')}
                className="text-sm text-gray-300 hover:text-white transition-colors"
              >
                Try it
              </button>
              <button
                onClick={() => scrollToSection('stack')}
                className="text-sm text-gray-300 hover:text-white transition-colors"
              >
                Stack
              </button>
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

      {/* Section 1: Hero */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="space-y-8">
            <div className="flex flex-wrap items-center gap-2 hero-stagger-1">
              <Pill tone="accent">🔏 Don't Trust. Verify.</Pill>
              <Pill>CRYPTOGRAPHIC PROVENANCE · RAG INTEGRITY</Pill>
            </div>

            <div className="space-y-6">
              <h1 className="text-4xl font-semibold text-white sm:text-5xl lg:text-6xl hero-stagger-2">
                RAG answers that carry their own proof.
              </h1>
              <p className="max-w-3xl text-lg text-gray-400 hero-stagger-3">
                ATTEST hashes every source chunk into a Merkle tree, signs the manifest
                with Ed25519, and re-checks it before every answer — so a poisoned
                document gets quarantined, not cited. Any certificate can be verified
                offline, by anyone, without trusting my backend.
              </p>
            </div>

            <div className="flex flex-wrap gap-4 hero-stagger-4">
              <Button onClick={() => scrollToSection('try-it')}>
                Try the Demo →
              </Button>
              <Button
                variant="secondary"
                onClick={() => window.open('https://github.com/nikitayk/Attest/blob/main/backend/verifier/verify.py', '_blank')}
              >
                Read the Verifier Source ↗
              </Button>
            </div>

            <div className="flex flex-wrap gap-4 text-sm text-gray-400 hero-stagger-5">
              <span>SHA-256 + Merkle + Ed25519</span>
              <span>·</span>
              <span>Fail-closed on tamper</span>
              <span>·</span>
              <span>Offline zero-trust verifier</span>
              <span>·</span>
              <span>Self-contained certificates</span>
            </div>

            <div className="pt-4 hero-stagger-6">
              <a
                href="https://nikitayk.github.io/SENTINEL"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm text-gold-400 hover:text-gold-300 transition-colors"
              >
                Sibling project: SENTINEL — secures what goes in →
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: The Problem */}
      <section ref={problemRef} id="problem" className="scroll-reveal py-16 bg-slate-800">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="space-y-12">
            <div className="space-y-4">
              <p className="text-sm font-semibold uppercase tracking-wider text-gold-400">
                01 · THE PROBLEM
              </p>
              <h2 className="text-3xl font-semibold text-white">
                RAG cites sources. It can't prove they're real.
              </h2>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
              <Surface className="p-6">
                <h3 className="text-lg font-semibold text-white mb-3">Poisoning</h3>
                <p className="text-sm text-gray-400">
                  Documents can be altered after ingestion, changing answers without detection.
                </p>
              </Surface>
              <Surface className="p-6">
                <h3 className="text-lg font-semibold text-white mb-3">Staleness</h3>
                <p className="text-sm text-gray-400">
                  Citations don't prove the document existed at a specific point in time.
                </p>
              </Surface>
              <Surface className="p-6">
                <h3 className="text-lg font-semibold text-white mb-3">Blind Trust</h3>
                <p className="text-sm text-gray-400">
                  Third parties can't verify without trusting your backend or logs.
                </p>
              </Surface>
            </div>

            <div className="flex items-center gap-2">
              <Pill tone="warning">OWASP ASI06</Pill>
              <span className="text-sm text-gray-400">— Memory & Context Poisoning</span>
            </div>
          </div>
        </div>
      </section>

      {/* Section 3: How It Works */}
      <section ref={howItWorksRef} id="how-it-works" className="scroll-reveal py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="space-y-12">
            <div className="space-y-4">
              <p className="text-sm font-semibold uppercase tracking-wider text-gold-400">
                02 · HOW IT WORKS
              </p>
              <h2 className="text-3xl font-semibold text-white">
                Cryptographic chain of custody
              </h2>
            </div>

            <PipelineDiagram />
          </div>
        </div>
      </section>

      {/* Section 4: Try It */}
      <section ref={tryItRef} id="try-it" className="scroll-reveal py-16 bg-slate-800">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="space-y-8">
            <div className="space-y-4">
              <p className="text-sm font-semibold uppercase tracking-wider text-gold-400">
                03 · TRY IT
              </p>
              <h2 className="text-3xl font-semibold text-white">
                Interactive demo
              </h2>
            </div>

            {/* Corpus Mode Toggle */}
            <div className="flex items-center gap-4">
              <button
                onClick={() => setCorpusMode('demo')}
                className={cx(
                  'px-4 py-2 text-sm font-medium rounded-md transition-colors',
                  corpusMode === 'demo'
                    ? 'bg-gold-500 text-slate-900'
                    : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
                )}
              >
                Demo Corpus
              </button>
              <button
                onClick={() => setCorpusMode('upload')}
                disabled
                className={cx(
                  'px-4 py-2 text-sm font-medium rounded-md transition-colors',
                  corpusMode === 'upload'
                    ? 'bg-gold-500 text-slate-900'
                    : 'bg-slate-700 text-gray-400 disabled:cursor-not-allowed'
                )}
              >
                Your Documents (coming soon)
              </button>
            </div>

            {/* Tab Navigation */}
            <nav className="border-b border-slate-700">
              <div className="flex gap-6">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cx(
                      'border-b-2 px-1 py-4 text-sm font-medium transition-colors',
                      activeTab === tab.id
                        ? 'border-gold-400 text-white'
                        : 'border-transparent text-gray-400 hover:border-slate-600 hover:text-gray-200'
                    )}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </nav>

            {statusError && (
              <div className="rounded-lg border border-red-600/50 bg-red-900/20 p-4 text-sm text-red-100">
                Unable to load runtime status: {statusError}
              </div>
            )}

            <div className="pb-10">
              {activeTab === 'ask' && <Ask systemStatus={systemStatus} />}
              {activeTab === 'verify' && <Verify systemStatus={systemStatus} />}
              {activeTab === 'corpus-health' && <CorpusHealth systemStatus={systemStatus} />}
            </div>
          </div>
        </div>
      </section>

      {/* Section 5: Built With */}
      <section ref={stackRef} id="stack" className="scroll-reveal py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="space-y-12">
            <div className="space-y-4">
              <p className="text-sm font-semibold uppercase tracking-wider text-gold-400">
                04 · BUILT WITH
              </p>
              <h2 className="text-3xl font-semibold text-white">
                Technology stack
              </h2>
            </div>

            <div className="flex flex-wrap gap-3">
              <Pill>FastAPI</Pill>
              <Pill>ChromaDB</Pill>
              <Pill>sentence-transformers</Pill>
              <Pill>Groq</Pill>
              <Pill>Ed25519</Pill>
              <Pill>Merkle Tree (hand-rolled)</Pill>
              <Pill>React + Vite + Tailwind</Pill>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-slate-700 bg-slate-800">
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
                <a
                  href="#"
                  className="text-sm text-gray-400 cursor-not-allowed"
                  title="Coming soon"
                >
                  ADPULSE — Real-time bidding
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
