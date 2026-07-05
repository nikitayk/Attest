import { useState, useEffect } from 'react'
import { getCorpusHealth, triggerMonitor, triggerIngest, uploadDocument, listDocuments, deleteDocument } from '../api/client'

export default function CorpusHealth() {
  const [health, setHealth] = useState(null)
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(false)
  const [monitoring, setMonitoring] = useState(false)
  const [ingesting, setIngesting] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [uploadError, setUploadError] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [monitorStatus, setMonitorStatus] = useState(null)

  const fetchHealth = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await getCorpusHealth()
      
      if (data.error) {
        setError(data.error)
      } else {
        setHealth(data)
      }
    } catch (err) {
      setError('Failed to fetch corpus health')
    } finally {
      setLoading(false)
    }
  }

  const fetchDocuments = async () => {
    try {
      const data = await listDocuments()
      setDocuments(data.documents || [])
    } catch (err) {
      console.error('Failed to fetch documents:', err)
    }
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
      setUploadError(null)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please select a file')
      return
    }

    setUploading(true)
    setUploadError(null)

    try {
      const result = await uploadDocument(selectedFile)
      
      if (result.error) {
        setUploadError(result.error)
      } else {
        setSelectedFile(null)
        await fetchDocuments()
        await fetchHealth()
      }
    } catch (err) {
      setUploadError('Failed to upload document')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (docId) => {
    if (!confirm(`Delete document ${docId}?`)) {
      return
    }

    try {
      const result = await deleteDocument(docId)
      
      if (result.error) {
        setError(result.error)
      } else {
        await fetchDocuments()
        await fetchHealth()
      }
    } catch (err) {
      setError('Failed to delete document')
    }
  }

  const handleRunMonitor = async () => {
    setMonitoring(true)
    setError(null)

    try {
      const result = await triggerMonitor()

      if (result.error) {
        setError(result.error)
      } else {
        setMonitorStatus(result)
        await fetchDocuments()
        await fetchHealth()
      }
    } catch (err) {
      setError('Failed to run integrity monitor')
    } finally {
      setMonitoring(false)
    }
  }

  const handleIngest = async () => {
    setIngesting(true)
    setError(null)

    try {
      const result = await triggerIngest()

      if (result.error) {
        setError(result.error)
      } else {
        await fetchDocuments()
        await fetchHealth()
      }
    } catch (err) {
      setError('Failed to ingest seed documents')
    } finally {
      setIngesting(false)
    }
  }

  useEffect(() => {
    fetchHealth()
    fetchDocuments()
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Corpus Health</h2>
          <p className="text-gray-600 mt-1">
            Monitor document integrity and quarantine status.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleIngest}
            disabled={ingesting}
            className="inline-flex justify-center rounded-md border border-transparent bg-amber-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 disabled:opacity-50"
          >
            {ingesting ? 'Ingesting...' : 'Ingest Seed Data'}
          </button>
          <button
            onClick={handleRunMonitor}
            disabled={monitoring}
            className="inline-flex justify-center rounded-md border border-transparent bg-emerald-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 disabled:opacity-50"
          >
            {monitoring ? 'Checking...' : 'Check Now'}
          </button>
          <button
            onClick={fetchHealth}
            disabled={loading}
            className="inline-flex justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {monitorStatus && !error && (
        <div className="rounded-md bg-blue-50 p-4">
          <h3 className="text-sm font-medium text-blue-900">Last Integrity Check</h3>
          <p className="mt-1 text-sm text-blue-700">
            Checked {monitorStatus.docs_checked} documents at{' '}
            {monitorStatus.last_run ? new Date(monitorStatus.last_run).toLocaleString() : 'unknown time'}.
            {monitorStatus.quarantined_count === 0
              ? ' No mismatches detected.'
              : ` Quarantined ${monitorStatus.quarantined_count} document(s): ${monitorStatus.mismatches.join(', ')}`}
          </p>
        </div>
      )}

      {health && (
        <div className="space-y-4">
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <div className="px-4 py-5 sm:p-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg leading-6 font-medium text-gray-900">
                  Document Status
                </h3>
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                  health.quarantined_count === 0
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                }`}>
                  {health.quarantined_count === 0 ? 'All OK' : `${health.quarantined_count} Quarantined`}
                </span>
              </div>
            </div>
            <ul className="divide-y divide-gray-200">
              {health.documents.map((doc) => (
                <li key={doc.doc_id} className="px-4 py-4 sm:px-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className={`flex-shrink-0 h-2 w-2 rounded-full ${
                        doc.status === 'OK' ? 'bg-green-500' : 'bg-red-500'
                      }`} />
                      <p className="ml-3 text-sm font-medium text-gray-900">
                        {doc.doc_id}
                      </p>
                    </div>
                    <div className="ml-4 flex items-center">
                      <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                        doc.status === 'OK'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {doc.status}
                      </span>
                    </div>
                  </div>
                  <div className="mt-2 sm:flex sm:justify-between">
                    <div className="sm:flex">
                      <p className="flex items-center text-sm text-gray-500">
                        <span className="truncate">Hash: {doc.doc_hash.substring(0, 16)}...</span>
                      </p>
                    </div>
                    <div className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
                      <p>
                        Last checked: {doc.last_checked ? new Date(doc.last_checked).toLocaleString() : 'Never'}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {!health && !loading && !error && (
        <div className="text-center py-12">
          <p className="text-gray-500">No corpus health data available</p>
        </div>
      )}

      {/* Document Upload Section */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Upload Document</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select file (.txt, .md, .pdf)
            </label>
            <input
              type="file"
              onChange={handleFileSelect}
              accept=".txt,.md,.pdf"
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100"
            />
          </div>
          {selectedFile && (
            <p className="text-sm text-gray-600">
              Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)
            </p>
          )}
          {uploadError && (
            <div className="rounded-md bg-red-50 p-3">
              <p className="text-sm text-red-700">{uploadError}</p>
            </div>
          )}
          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className="inline-flex justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : 'Upload Document'}
          </button>
        </div>
      </div>

      {/* Document List Section */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">
            Documents ({documents.length})
          </h3>
        </div>
        {documents.length === 0 ? (
          <div className="px-4 py-8 text-center text-gray-500">
            No documents uploaded yet
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {documents.map((doc) => (
              <li key={doc.doc_id} className="px-4 py-4 sm:px-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {doc.filename}
                    </p>
                    <p className="mt-1 flex items-center text-sm text-gray-500">
                      <span className="truncate">ID: {doc.doc_id}</span>
                      <span className="mx-2">•</span>
                      <span>{doc.chunk_count} chunks</span>
                    </p>
                    <p className="mt-1 text-xs text-gray-400">
                      Hash: {doc.doc_hash.substring(0, 32)}...
                    </p>
                  </div>
                  <div className="ml-4 flex-shrink-0">
                    <button
                      onClick={() => handleDelete(doc.doc_id)}
                      className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
