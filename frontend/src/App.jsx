import { useEffect, useMemo, useState } from 'react'
import Ask from './pages/Ask'
import Verify from './pages/Verify'
import CorpusHealth from './pages/CorpusHealth'
import { getApiUrl, getSystemStatus } from './api/client'
import { Button, MetricCard, Pill, Surface, cx } from './components/ui'

function App() {
  const [activeTab, setActiveTab] = useState('ask')
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

  const tabs = useMemo(
    () => [
      { id: 'ask', label: 'Ask' },
      { id: 'verify', label: 'Verify' },
      { id: 'corpus-health', label: 'Corpus Health' },
    ],
    []
  )

  const modeLabel =
    systemStatus?.mode === 'hosted-preview' ? 'Hosted Preview' : 'Full Runtime'

  const capabilities = systemStatus?.capabilities || {}

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#07111f] text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.16),transparent_30%),radial-gradient(circle_at_top_right,rgba(99,102,241,0.16),transparent_28%),linear-gradient(180deg,#081120_0%,#040814_100%)]" />
      <div className="pointer-events-none absolute inset-x-0 top-[-18rem] mx-auto h-[34rem] w-[34rem] rounded-full bg-cyan-400/10 blur-3xl" />

      <div className="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-8">
          <Surface className="overflow-hidden">
            <div className="grid gap-8 p-6 lg:grid-cols-[1.6fr,1fr] lg:p-8">
              <div className="space-y-6">
                <div className="flex flex-wrap items-center gap-3">
                  <Pill tone="accent">Cryptographic RAG Assurance</Pill>
                  <Pill tone={systemStatus?.manifest_loaded ? 'success' : 'warning'}>
                    {systemStatus?.manifest_loaded ? 'Manifest Ready' : 'Manifest Pending'}
                  </Pill>
                  <Pill>{modeLabel}</Pill>
                </div>

                <div className="space-y-4">
                  <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                    ATTEST turns retrieval answers into verifiable evidence.
                  </h1>
                  <p className="max-w-2xl text-base leading-7 text-slate-300">
                    A portfolio-grade interface for grounded answers, signed certificates, and
                    corpus integrity monitoring. The live deployment favors reliability over raw
                    compute, so hosted preview mode is explicit instead of pretending everything is
                    available.
                  </p>
                </div>

                <div className="flex flex-wrap gap-3">
                  <Button variant="primary" onClick={() => setActiveTab('ask')}>
                    Explore Ask
                  </Button>
                  <Button variant="secondary" onClick={() => setActiveTab('verify')}>
                    Verify A Certificate
                  </Button>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
                <MetricCard
                  label="Runtime"
                  value={modeLabel}
                  hint={
                    systemStatus?.mode === 'hosted-preview'
                      ? 'Optimized for a stable live demo on free hosting.'
                      : 'Full semantic retrieval and mutation workflow enabled.'
                  }
                />
                <MetricCard
                  label="Backend"
                  value={getApiUrl().replace(/^https?:\/\//, '')}
                  hint="Current API endpoint used by the deployed frontend."
                />
              </div>
            </div>
          </Surface>
        </header>

        <section className="mb-6 grid gap-4 md:grid-cols-3">
          <MetricCard
            label="Query"
            value={capabilities.query ? 'Available' : 'Offline'}
            hint="Generates grounded answers and signed certificates."
          />
          <MetricCard
            label="Verification"
            value={capabilities.verify ? 'Available' : 'Offline'}
            hint="Checks hash, Merkle proof, and signature validity."
          />
          <MetricCard
            label="Mutations"
            value={capabilities.document_upload ? 'Enabled' : 'Read-only'}
            hint="Seed ingest, uploads, and deletes adapt to deployment mode."
          />
        </section>

        <nav className="mb-6 flex flex-wrap gap-3">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cx(
                'rounded-2xl border px-4 py-2.5 text-sm font-medium transition duration-200',
                activeTab === tab.id
                  ? 'border-cyan-300/30 bg-cyan-300/12 text-white shadow-[0_0_0_1px_rgba(103,232,249,0.08)]'
                  : 'border-white/10 bg-white/[0.04] text-slate-300 hover:border-white/20 hover:bg-white/[0.08] hover:text-white'
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {statusError && (
          <div className="mb-6 rounded-2xl border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-100">
            Unable to load runtime status: {statusError}
          </div>
        )}

        <main className="pb-10">
          {activeTab === 'ask' && <Ask systemStatus={systemStatus} />}
          {activeTab === 'verify' && <Verify systemStatus={systemStatus} />}
          {activeTab === 'corpus-health' && <CorpusHealth systemStatus={systemStatus} />}
        </main>
      </div>
    </div>
  )
}

export default App
