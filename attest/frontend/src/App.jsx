import { useState } from 'react'
import Ask from './pages/Ask'
import Verify from './pages/Verify'
import CorpusHealth from './pages/CorpusHealth'

function App() {
  const [activeTab, setActiveTab] = useState('ask')

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">ATTEST</h1>
          <p className="text-sm text-gray-600">Cryptographic chain of custody for RAG answers</p>
        </div>
      </header>

      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('ask')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'ask'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Ask
            </button>
            <button
              onClick={() => setActiveTab('verify')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'verify'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Verify
            </button>
            <button
              onClick={() => setActiveTab('corpus-health')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'corpus-health'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Corpus Health
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {activeTab === 'ask' && <Ask />}
        {activeTab === 'verify' && <Verify />}
        {activeTab === 'corpus-health' && <CorpusHealth />}
      </main>
    </div>
  )
}

export default App
