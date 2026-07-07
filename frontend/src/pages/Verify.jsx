import { useState } from 'react'
import { getPublicKey } from '../api/client'
import { verifyCertificateClient } from '../lib/verify'
import { Alert, Button, CodeBlock, Pill, SectionHeader, Surface } from '../components/ui'

const CHECK_ITEMS = [
  { key: 'hash_match', label: 'Chunk hashes match source text' },
  { key: 'proof_valid', label: 'Merkle proofs recompute the manifest root' },
  { key: 'signature_valid', label: 'Ed25519 signature validates against the public key' },
]

export default function Verify({ systemStatus }) {
  const [certificate, setCertificate] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [visibleChecks, setVisibleChecks] = useState([false, false, false])

  const handleVerify = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const cert = JSON.parse(certificate)
      const publicKeyPem = await getPublicKey()
      const data = await verifyCertificateClient(cert, publicKeyPem)

      if (data.ok) {
        setResult({
          valid: true,
          reason: data.reason,
          hash_match: data.hash_match,
          proof_valid: data.proof_valid,
          signature_valid: data.signature_valid,
        })
        setVisibleChecks([false, false, false])
        setTimeout(() => setVisibleChecks([true, false, false]), 250)
        setTimeout(() => setVisibleChecks([true, true, false]), 500)
        setTimeout(() => setVisibleChecks([true, true, true]), 750)
      } else {
        setError(data.reason || 'Verification failed')
      }
    } catch (err) {
      setError(err.message || 'Invalid certificate JSON or verification failed')
    } finally {
      setLoading(false)
    }
  }

  const loadLastCertificate = () => {
    const cached = window.localStorage.getItem('attest:last-certificate')
    if (!cached) {
      setError('No generated certificate is stored in this browser yet.')
      return
    }

    setCertificate(cached)
    setError(null)
    setResult(null)
  }

  const handleImportFile = async (event) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    try {
      const content = await file.text()
      setCertificate(content)
      setError(null)
      setResult(null)
    } catch {
      setError('Unable to read the selected certificate file.')
    }
  }

  return (
    <div className="space-y-6">
      <Surface className="p-6">
        <SectionHeader
          eyebrow="Independent Verification"
          title="Prove the answer is grounded, untampered, and signed."
          description="Paste or import any answer certificate. Verification runs entirely in your browser using the published public key — no trust in the backend required."
          actions={
            <>
              <Pill tone="accent">Client-Side Zero-Trust</Pill>
              <Pill tone={systemStatus?.capabilities?.verify ? 'success' : 'warning'}>
                {systemStatus?.capabilities?.verify ? 'Public Key Available' : 'Public Key Offline'}
              </Pill>
            </>
          }
        />

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="space-y-4">
            <div>
              <label htmlFor="certificate" className="block text-sm font-medium text-gray-300">
                Certificate JSON
              </label>
              <textarea
                id="certificate"
                value={certificate}
                onChange={(e) => setCertificate(e.target.value)}
                rows={14}
                className="mt-2 block w-full rounded-md border border-gray-600 bg-slate-800 px-3 py-2 font-mono text-xs text-gray-200 placeholder-gray-500 focus:border-gold-400 focus:outline-none focus:ring-1 focus:ring-gold-400"
                placeholder='{"certificate_id": "...", "query": "...", ...}'
                required
              />
            </div>

            <div className="flex gap-3">
              <Button onClick={handleVerify} disabled={loading}>
                {loading ? 'Verifying certificate...' : 'Run Verification'}
              </Button>
              <Button variant="secondary" onClick={loadLastCertificate}>
                Load Last Generated Certificate
              </Button>
              <label className="inline-flex cursor-pointer items-center justify-center rounded-md border border-gray-600 bg-gray-700/50 px-4 py-2 text-sm font-medium text-gray-200 hover:bg-gray-700">
                Import JSON File
                <input type="file" accept=".json" className="hidden" onChange={handleImportFile} />
              </label>
            </div>
          </div>

          <div className="space-y-4">
            <Surface className="p-4">
              <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
                Verification Pipeline
              </p>
              <div className="mt-3 space-y-2">
                {CHECK_ITEMS.map((item, index) => (
                  <div
                    key={item.key}
                    className="rounded-md border border-gray-600 bg-slate-700/30 p-3"
                  >
                    <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
                      Step {index + 1}
                    </p>
                    <p className="mt-1 text-sm text-gray-200">{item.label}</p>
                  </div>
                ))}
              </div>
            </Surface>

            <Surface className="p-4">
              <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
                Offline CLI Option
              </p>
              <p className="mt-2 text-sm text-gray-300">
                For a fully offline workflow, export the certificate and run the standalone Python
                verifier against the public key.
              </p>
              <div className="mt-3">
                <CodeBlock>
                  python backend/verifier/verify.py --certificate cert.json --public-key
                  {' '}backend/keys/public_key.pem
                </CodeBlock>
              </div>
            </Surface>
          </div>
        </div>
      </Surface>

      {error && (
        <Alert tone="danger" title="Verification failed">
          {error}
        </Alert>
      )}

      {result && (
        <Surface className="p-6">
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone="success">Certificate Valid</Pill>
            <Pill tone="accent">Verified locally in browser</Pill>
          </div>
          <h3 className="mt-4 text-xl font-semibold text-white">Verification result</h3>
          <p className="mt-2 text-sm text-gray-300">{result.reason}</p>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {CHECK_ITEMS.map((item, index) => {
              const passed = result[item.key]
              const isVisible = visibleChecks[index]
              return (
                <div
                  key={item.key}
                  className={`rounded-md border border-gray-600 bg-slate-700/30 p-4 transition-opacity duration-300 ${
                    isVisible ? 'opacity-100' : 'opacity-0'
                  }`}
                >
                  <Pill tone={passed ? 'success' : 'danger'}>{passed ? 'Passed' : 'Failed'}</Pill>
                  <p className="mt-2 text-sm text-gray-200">{item.label}</p>
                </div>
              )
            })}
          </div>
        </Surface>
      )}

      {certificate && (
        <Surface className="p-6">
          <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
            Current Payload
          </p>
          <div className="mt-3">
            <CodeBlock>{certificate}</CodeBlock>
          </div>
        </Surface>
      )}
    </div>
  )
}
