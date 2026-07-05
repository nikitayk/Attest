/**
 * API client for ATTEST backend.
 * Centralizes all backend communication.
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Query the RAG system.
 */
export async function queryBackend(queryText) {
  const response = await fetch(`${API_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: queryText }),
  });
  return response.json();
}

/**
 * Retrieve a certificate by ID.
 */
export async function getCertificate(certificateId) {
  const response = await fetch(`${API_URL}/certificate/${certificateId}`);
  return response.json();
}

/**
 * Verify a certificate server-side.
 * Note: For zero-trust verification, use the standalone CLI verifier.
 */
export async function verifyCertificate(certificate, publicKeyOverride = null) {
  const response = await fetch(`${API_URL}/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      certificate,
      public_key_override: publicKeyOverride,
    }),
  });
  return response.json();
}

/**
 * Trigger corpus integrity check.
 */
export async function triggerMonitor() {
  const response = await fetch(`${API_URL}/monitor/trigger`, {
    method: 'POST',
  });
  return response.json();
}

/**
 * Get monitor status.
 */
export async function getMonitorStatus() {
  const response = await fetch(`${API_URL}/monitor/status`);
  return response.json();
}

/**
 * Get corpus health.
 */
export async function getCorpusHealth() {
  const response = await fetch(`${API_URL}/corpus/health`);
  return response.json();
}

/**
 * Get public key.
 */
export async function getPublicKey() {
  const response = await fetch(`${API_URL}/public-key`);
  return response.text();
}

/**
 * Trigger ingestion.
 */
export async function triggerIngest(docId = null) {
  const response = await fetch(`${API_URL}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(docId ? { doc_id: docId } : {}),
  });
  return response.json();
}

/**
 * Upload a document.
 */
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_URL}/documents`, {
    method: 'POST',
    body: formData,
  });
  return response.json();
}

/**
 * List all documents.
 */
export async function listDocuments() {
  const response = await fetch(`${API_URL}/documents`);
  return response.json();
}

/**
 * Delete a document.
 */
export async function deleteDocument(docId) {
  const response = await fetch(`${API_URL}/documents/${docId}`, {
    method: 'DELETE',
  });
  return response.json();
}
