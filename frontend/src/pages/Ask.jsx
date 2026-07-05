import { useMemo, useState } from 'react'
import { queryBackend } from '../api/client'
import { Alert, Button, CodeBlock, EmptyState, Pill, SectionHeader, Surface } from '../components/ui'

const EXAMPLE_PROMPTS = [
  'What does the security policy say about incident reporting?',
  'Summarize the onboarding expectations for new team members.',
  'What is the documented data retention approach?',
]

export default function Ask({ systemStatus }) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const isPreview = systemStatus?.mode === 'hosted-preview'
  const sources = useMemo(() => result?.certificate?.chunks || [], [result])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await queryBackend(query)

      if (data.ok) {
        setResult(data)
        if (data.certificate) {
          window.localStorage.setItem('attest:last-certificate', JSON.stringify(data.certificate))
        }
      } else {
        setError(data.error || 'Query failed')
      }
    } catch (err) {
      setError('Failed to connect to server')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Surface className="p-6 lg:p-8">
        <SectionHeader
          eyebrow="Grounded Answers"
          title="Ask the corpus and keep the proof attached."
          description="Every successful answer includes a signed certificate, cited chunks, and the Merkle-root context needed for independent verification."
          actions={
            <>
              <Pill tone={isPreview ? 'warning' : 'success'}>
                {isPreview ? 'Preview Retrieval' : 'Semantic Retrieval'}
              </Pill>
              <Pill tone="accent">Signed Certificates</Pill>
            </>
          }
        />

        <div className="mt-8 grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="rounded-3xl border border-white/10 bg-slate-950/40 p-5">
              <label htmlFor="query" className="text-sm font-medium text-slate-200">
                Your question
              </label>
              <textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={6}
                className="mt-3 block w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 text-sm text-white shadow-inner outline-none transition placeholder:text-slate-500 focus:border-cyan-300/40 focus:ring-2 focus:ring-cyan-300/20"
                placeholder="Ask a policy, incident, onboarding, or security question."
                required
              />
            </div>

            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={loading}>
                {loading ? 'Generating answer...' : 'Generate Verified Answer'}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  setQuery('')
                  setResult(null)
                  setError(null)
                }}
              >
                Reset
              </Button>
            </div>
          </form>

          <Surface className="p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
              Suggested prompts
            </p>
            <div className="mt-4 space-y-3">
              {EXAMPLE_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setQuery(prompt)}
                  className="w-full rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-left text-sm text-slate-200 transition hover:border-cyan-300/20 hover:bg-cyan-300/8 hover:text-white"
                >
                  {prompt}
                </button>
              ))}
            </div>
            <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm leading-6 text-slate-300">
              {isPreview ? (
                <>
                  The hosted site uses lightweight lexical retrieval over the checked-in demo corpus
                  to stay stable on free hosting. Certificates are still signed and verifiable.
                </>
              ) : (
                <>
                  Full mode uses vector retrieval plus LLM synthesis for grounded responses backed by
                  signed provenance.
                </>
              )}
            </div>
          </Surface>
        </div>
      </Surface>

      {error && (
        <Alert tone="danger" title="Query failed">
          {error}
        </Alert>
      )}

      {!result && !error && !loading && (
        <EmptyState
          title="Ready for a grounded query"
          description="Submit a question to produce an answer card, cited source chunks, and a signed certificate that can be checked in the Verify tab."
        />
      )}

      {result && (
        <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
          <Surface className="p-6 lg:p-7">
            <div className="flex flex-wrap items-center gap-3">
              <Pill tone="success">Answer Generated</Pill>
              {result.certificate?.doc_id ? <Pill>{result.certificate.doc_id}</Pill> : null}
            </div>
            <h3 className="mt-5 text-2xl font-semibold text-white">Response</h3>
            <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-200">
              {result.answer}
            </p>

            {result.certificate && (
              <div className="mt-8 grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Certificate</p>
                  <p className="mt-3 text-sm text-white">{result.certificate.certificate_id}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Merkle Root</p>
                  <p className="mt-3 break-all text-sm text-white">{result.certificate.merkle_root}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Model Stack</p>
                  <p className="mt-3 text-sm text-white">
                    {result.certificate.embedding_model}
                    <br />
                    <span className="text-slate-400">{result.certificate.llm_model}</span>
                  </p>
                </div>
              </div>
            )}
          </Surface>

          <div className="space-y-6">
            <Surface className="p-6">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                    Source Evidence
                  </p>
                  <h3 className="mt-2 text-xl font-semibold text-white">Retrieved chunks</h3>
                </div>
                <Pill tone="accent">{sources.length} cited</Pill>
              </div>

              <div className="mt-5 space-y-4">
                {sources.map((chunk) => (
                  <div
                    key={`${chunk.doc_id}-${chunk.chunk_index}`}
                    className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Pill>{chunk.doc_id}</Pill>
                      <Pill tone="accent">Chunk {chunk.chunk_index}</Pill>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-slate-300">{chunk.text}</p>
                  </div>
                ))}
              </div>
            </Surface>

            {result.certificate && (
              <Surface className="p-6">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                      Certificate Payload
                    </p>
                    <h3 className="mt-2 text-xl font-semibold text-white">Portable proof</h3>
                  </div>
                  <Button
                    variant="secondary"
                    type="button"
                    onClick={() =>
                      navigator.clipboard.writeText(
                        JSON.stringify(result.certificate, null, 2)
                      )
                    }
                  >
                    Copy JSON
                  </Button>
                </div>
                <div className="mt-5">
                  <CodeBlock>{JSON.stringify(result.certificate, null, 2)}</CodeBlock>
                </div>
              </Surface>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
