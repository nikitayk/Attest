import { useState } from 'react'
import { verifyCertificate } from '../api/client'
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
      <Surface className="p-6 lg:p-8">
        <SectionHeader
          eyebrow="Independent Verification"
          title="Prove the answer is grounded, untampered, and signed."
          description="Paste or import any answer certificate, then validate its chunk hashes, Merkle proofs, and signature with the backend verifier."
          actions={
            <>
              <Pill tone="accent">Server Verification</Pill>
              <Pill tone={systemStatus?.capabilities?.verify ? 'success' : 'warning'}>
                {systemStatus?.capabilities?.verify ? 'Verifier Online' : 'Verifier Offline'}
              </Pill>
            </>
          }
        />

        <div className="mt-8 grid gap-6 xl:grid-cols-[1.05fr,0.95fr]">
          <div className="space-y-5">
            <div className="rounded-3xl border border-white/10 bg-slate-950/40 p-5">
              <label htmlFor="certificate" className="text-sm font-medium text-slate-200">
                Certificate JSON
              </label>
              <textarea
                id="certificate"
                value={certificate}
                onChange={(e) => setCertificate(e.target.value)}
                rows={14}
                className="mt-3 block w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 font-mono text-xs leading-6 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-300/40 focus:ring-2 focus:ring-cyan-300/20"
                placeholder='{"certificate_id": "...", "query": "...", ...}'
                required
              />
            </div>

            <div className="flex flex-wrap gap-3">
              <Button onClick={handleVerify} disabled={loading}>
                {loading ? 'Verifying certificate...' : 'Run Verification'}
              </Button>
              <Button variant="secondary" onClick={loadLastCertificate}>
                Load Last Generated Certificate
              </Button>
              <label className="inline-flex cursor-pointer items-center justify-center rounded-2xl border border-white/10 bg-white/[0.08] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-white/[0.12]">
                Import JSON File
                <input type="file" accept=".json" className="hidden" onChange={handleImportFile} />
              </label>
            </div>
          </div>

          <div className="space-y-5">
            <Surface className="p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                Verification Pipeline
              </p>
              <div className="mt-4 space-y-3">
                {CHECK_ITEMS.map((item, index) => (
                  <div
                    key={item.key}
                    className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
                  >
                    <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
                      Step {index + 1}
                    </p>
                    <p className="mt-2 text-sm text-slate-200">{item.label}</p>
                  </div>
                ))}
              </div>
            </Surface>

            <Surface className="p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                Zero-Trust Option
              </p>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                For an offline workflow, export the certificate and run the standalone CLI verifier
                against the public key.
              </p>
              <div className="mt-4">
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
        <Surface className="p-6 lg:p-8">
          <div className="flex flex-wrap items-center gap-3">
            <Pill tone="success">Certificate Valid</Pill>
            <Pill tone="accent">All cryptographic checks passed</Pill>
          </div>
          <h3 className="mt-5 text-2xl font-semibold text-white">Verification result</h3>
          <p className="mt-3 text-sm leading-7 text-slate-300">{result.reason}</p>

          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {CHECK_ITEMS.map((item) => {
              const passed = result[item.key]
              return (
                <div
                  key={item.key}
                  className="rounded-2xl border border-white/10 bg-white/[0.03] p-5"
                >
                  <Pill tone={passed ? 'success' : 'danger'}>{passed ? 'Passed' : 'Failed'}</Pill>
                  <p className="mt-4 text-sm leading-6 text-slate-200">{item.label}</p>
                </div>
              )
            })}
          </div>
        </Surface>
      )}

      {certificate && (
        <Surface className="p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            Current Payload
          </p>
          <div className="mt-4">
            <CodeBlock>{certificate}</CodeBlock>
          </div>
        </Surface>
      )}
    </div>
  )
}
