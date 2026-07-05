import { useState, useEffect } from 'react'
import { getCorpusHealth, triggerMonitor, triggerIngest, uploadDocument, listDocuments, deleteDocument } from '../api/client'
import { Alert, Button, CodeBlock, EmptyState, Pill, SectionHeader, Surface } from '../components/ui'

export default function CorpusHealth({ systemStatus }) {
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

  const isPreview = systemStatus?.mode === 'hosted-preview'

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
      <Surface className="p-6">
        <SectionHeader
          eyebrow="Corpus Integrity"
          title="Monitor document health and quarantine status."
          description="Track cryptographic integrity, run integrity checks, and manage document ingestion. The hosted preview uses a pre-built corpus for stability."
          actions={
            <>
              <Pill tone={isPreview ? 'warning' : 'success'}>
                {isPreview ? 'Preview Mode' : 'Full Runtime'}
              </Pill>
              <Pill tone="accent">Cryptographic Monitoring</Pill>
            </>
          }
        />

        <div className="mt-6 flex flex-wrap gap-3">
          <Button onClick={handleIngest} disabled={ingesting || isPreview}>
            {ingesting ? 'Ingesting...' : 'Ingest Seed Data'}
          </Button>
          <Button variant="secondary" onClick={handleRunMonitor} disabled={monitoring}>
            {monitoring ? 'Checking...' : 'Run Integrity Check'}
          </Button>
          <Button variant="ghost" onClick={fetchHealth} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh Status'}
          </Button>
          {/* TODO: Simulate Tampering button requires new backend endpoint POST /simulate-tampering
               This endpoint should flip one byte on a COPY of a seeded demo doc and re-trigger monitor.
               Flagged per master prompt section 2.4 - confirm before building backend surface. */}
          <Button variant="danger" disabled>
            Simulate Tampering (Demo Mode)
          </Button>
        </div>

        {isPreview && (
          <div className="mt-4 rounded-md border border-yellow-600/50 bg-yellow-900/20 p-4 text-sm text-yellow-100">
            <strong>Preview mode:</strong> Seed ingestion and document uploads are disabled on the hosted deployment to ensure stability on free hosting.
          </div>
        )}
      </Surface>

      {error && (
        <Alert tone="danger" title="Operation failed">
          {error}
        </Alert>
      )}

      {monitorStatus && !error && (
        <Surface className="p-6">
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone="success">Integrity Check Complete</Pill>
            <Pill>{monitorStatus.docs_checked} documents checked</Pill>
          </div>
          <h3 className="mt-4 text-xl font-semibold text-white">Last scan results</h3>
          <p className="mt-2 text-sm text-gray-300">
            Checked at {monitorStatus.last_run ? new Date(monitorStatus.last_run).toLocaleString() : 'unknown time'}.
            {monitorStatus.quarantined_count === 0
              ? ' No mismatches detected.'
              : ` Quarantined ${monitorStatus.quarantined_count} document(s): ${monitorStatus.mismatches.join(', ')}`}
          </p>
        </Surface>
      )}

      {health && (
        <Surface className="p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
                Document Status
              </p>
              <h3 className="mt-2 text-xl font-semibold text-white">Corpus overview</h3>
            </div>
            <Pill tone={health.quarantined_count === 0 ? 'success' : 'danger'}>
              {health.quarantined_count === 0 ? 'All OK' : `${health.quarantined_count} Quarantined`}
            </Pill>
          </div>

          <div className="mt-4 space-y-3">
            {health.documents.map((doc) => (
              <div
                key={doc.doc_id}
                className="rounded-md border border-gray-600 bg-slate-700/30 p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className={`h-2 w-2 rounded-full ${
                      doc.status === 'OK' ? 'bg-green-500' : 'bg-red-500'
                    }`} />
                    <p className="text-sm font-medium text-white">{doc.doc_id}</p>
                  </div>
                  <Pill tone={doc.status === 'OK' ? 'success' : 'danger'}>
                    {doc.status}
                  </Pill>
                </div>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wider text-gray-500">Document hash</p>
                    <p className="mt-1 font-mono text-sm text-gray-300">{doc.doc_hash.substring(0, 32)}...</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wider text-gray-500">Last checked</p>
                    <p className="mt-1 text-sm text-gray-300">
                      {doc.last_checked ? new Date(doc.last_checked).toLocaleString() : 'Never'}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Surface>
      )}

      {!health && !loading && !error && (
        <EmptyState
          title="No corpus health data"
          description="Run an integrity check or refresh to load the current corpus status."
        />
      )}

      {!isPreview && (
        <>
          <Surface className="p-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
                  Document Upload
                </p>
                <h3 className="mt-2 text-xl font-semibold text-white">Add to corpus</h3>
              </div>
            </div>

            <div className="mt-4 space-y-4">
              <div>
                <label htmlFor="file-upload" className="block text-sm font-medium text-gray-300">
                  Select file (.txt, .md, .pdf)
                </label>
                <input
                  id="file-upload"
                  type="file"
                  onChange={handleFileSelect}
                  accept=".txt,.md,.pdf"
                  className="mt-2 block w-full text-sm text-gray-300 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-gray-700 file:text-gray-200 hover:file:bg-gray-600"
                />
              </div>

              {selectedFile && (
                <div className="rounded-md border border-gray-600 bg-gray-700/30 p-4">
                  <p className="text-sm text-gray-200">
                    Selected: <span className="font-medium">{selectedFile.name}</span> ({(selectedFile.size / 1024).toFixed(2)} KB)
                  </p>
                </div>
              )}

              {uploadError && (
                <Alert tone="danger" title="Upload error">
                  {uploadError}
                </Alert>
              )}

              <Button onClick={handleUpload} disabled={!selectedFile || uploading}>
                {uploading ? 'Uploading...' : 'Upload Document'}
              </Button>
            </div>
          </Surface>

          <Surface className="p-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
                  Document Library
                </p>
                <h3 className="mt-2 text-xl font-semibold text-white">Uploaded documents ({documents.length})</h3>
              </div>
            </div>

            {documents.length === 0 ? (
              <EmptyState
                title="No documents yet"
                description="Upload documents to build your corpus."
              />
            ) : (
              <div className="mt-4 space-y-3">
                {documents.map((doc) => (
                  <div
                    key={doc.doc_id}
                    className="rounded-md border border-gray-600 bg-slate-700/30 p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white truncate">{doc.filename}</p>
                        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-gray-400">
                          <span>ID: {doc.doc_id}</span>
                          <span>•</span>
                          <span>{doc.chunk_count} chunks</span>
                        </div>
                        <p className="mt-2 font-mono text-xs text-gray-500">
                          Hash: {doc.doc_hash.substring(0, 32)}...
                        </p>
                      </div>
                      <Button
                        variant="secondary"
                        onClick={() => handleDelete(doc.doc_id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Surface>
        </>
      )}
    </div>
  )
}
