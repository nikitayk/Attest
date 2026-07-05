import { useState } from 'react'
import { verifyCertificate } from '../api/client'

export default function Verify() {
  const [certificate, setCertificate] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleVerify = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      // Parse certificate JSON
      const cert = JSON.parse(certificate)
      
      // Use server-side verification endpoint
      const data = await verifyCertificate(cert)

      if (data.ok) {
        setResult({
          valid: true,
          reason: data.reason,
          hash_match: data.hash_match,
          proof_valid: data.proof_valid,
          signature_valid: data.signature_valid,
        })
      } else {
        setError(data.reason || 'Verification failed')
      }
    } catch (err) {
      setError('Invalid certificate JSON or verification failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Verify Certificate</h2>
        <p className="text-gray-600 mt-1">
          Paste an AnswerCertificate JSON to verify its cryptographic integrity.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label htmlFor="certificate" className="block text-sm font-medium text-gray-700">
            Certificate JSON
          </label>
          <textarea
            id="certificate"
            value={certificate}
            onChange={(e) => setCertificate(e.target.value)}
            rows={10}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border p-3 font-mono text-xs"
            placeholder='{"certificate_id": "...", "query": "...", ...}'
            required
          />
        </div>
        <button
          onClick={handleVerify}
          disabled={loading}
          className="inline-flex justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
        >
          {loading ? 'Verifying...' : 'Verify'}
        </button>
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
              <h3 className="text-sm font-medium text-red-800">Verification Failed</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {result && (
        <div className="rounded-md bg-green-50 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-green-800">Verification Result</h3>
              <p className="mt-1 text-sm text-green-700">{result.reason}</p>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            <div className="flex items-center text-sm">
              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium mr-2 ${result.hash_match ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                {result.hash_match ? '✓' : '✗'}
              </span>
              <span className="text-gray-700">Hash match</span>
            </div>
            <div className="flex items-center text-sm">
              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium mr-2 ${result.proof_valid ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                {result.proof_valid ? '✓' : '✗'}
              </span>
              <span className="text-gray-700">Merkle proof valid</span>
            </div>
            <div className="flex items-center text-sm">
              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium mr-2 ${result.signature_valid ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                {result.signature_valid ? '✓' : '✗'}
              </span>
              <span className="text-gray-700">Signature valid</span>
            </div>
          </div>
        </div>
      )}

      <div className="bg-blue-50 p-4 rounded-md">
        <h3 className="text-sm font-medium text-blue-800">Zero-Trust Verification</h3>
        <p className="mt-1 text-sm text-blue-700">
          For complete cryptographic verification without trusting the backend, use the standalone CLI:
        </p>
        <pre className="mt-2 bg-blue-100 p-2 rounded text-xs overflow-x-auto">
          python backend/verifier/verify.py --certificate cert.json --public-key backend/keys/public_key.pem
        </pre>
      </div>
    </div>
  )
}
