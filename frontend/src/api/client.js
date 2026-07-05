const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function parseResponse(response) {
  const contentType = response.headers.get('content-type') || ''

  if (contentType.includes('application/json')) {
    return response.json()
  }

  return response.text()
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, options)
  const payload = await parseResponse(response)

  if (!response.ok) {
    const message =
      payload?.detail ||
      payload?.error ||
      (typeof payload === 'string' ? payload : 'Request failed')

    throw new Error(message)
  }

  return payload
}

export function getApiUrl() {
  return API_URL
}

export async function getSystemStatus() {
  return apiRequest('/health')
}

export async function queryBackend(queryText) {
  return apiRequest('/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: queryText }),
  })
}

export async function getCertificate(certificateId) {
  return apiRequest(`/certificate/${certificateId}`)
}

export async function verifyCertificate(certificate, publicKeyOverride = null) {
  return apiRequest('/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      certificate,
      public_key_override: publicKeyOverride,
    }),
  })
}

export async function triggerMonitor() {
  return apiRequest('/monitor/trigger', {
    method: 'POST',
  })
}

export async function getMonitorStatus() {
  return apiRequest('/monitor/status')
}

export async function getCorpusHealth() {
  return apiRequest('/corpus/health')
}

export async function getPublicKey() {
  return apiRequest('/public-key')
}

export async function triggerIngest(docId = null) {
  return apiRequest('/ingest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(docId ? { doc_id: docId } : {}),
  })
}

export async function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)

  return apiRequest('/documents', {
    method: 'POST',
    body: formData,
  })
}

export async function listDocuments() {
  return apiRequest('/documents')
}

export async function deleteDocument(docId) {
  return apiRequest(`/documents/${docId}`, {
    method: 'DELETE',
  })
}
