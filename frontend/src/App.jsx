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
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8">
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-2">
              <Pill tone="accent">Cryptographic RAG Assurance</Pill>
              {systemStatus?.manifest_loaded ? (
                <Pill tone="success">Manifest Ready</Pill>
              ) : (
                <Pill tone="warning">Manifest Pending</Pill>
              )}
              <Pill>{modeLabel}</Pill>
            </div>

            <div className="space-y-3">
              <h1 className="text-3xl font-semibold text-white sm:text-4xl">
                ATTEST turns retrieval answers into verifiable evidence.
              </h1>
              <p className="max-w-2xl text-gray-400">
                A professional interface for grounded answers, signed certificates, and corpus integrity monitoring.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Button onClick={() => setActiveTab('ask')}>
                Ask
              </Button>
              <Button variant="secondary" onClick={() => setActiveTab('verify')}>
                Verify
              </Button>
            </div>
          </div>
        </header>

        <nav className="mb-6 border-b border-gray-700">
          <div className="flex gap-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cx(
                  'border-b-2 px-1 py-4 text-sm font-medium transition-colors',
                  activeTab === tab.id
                    ? 'border-blue-500 text-white'
                    : 'border-transparent text-gray-400 hover:border-gray-600 hover:text-gray-200'
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </nav>

        {statusError && (
          <div className="mb-6 rounded-lg border border-red-600/50 bg-red-900/20 p-4 text-sm text-red-100">
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
