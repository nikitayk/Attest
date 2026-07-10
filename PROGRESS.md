# ATTEST Build Progress

## Current focus

- [x] **Audit, fix, test, and document pass complete (2026-07-11).** Verified every prior
  claim against real code, fixed latent runtime bugs found only by executing the pipeline,
  ran a real adversarial eval, and updated all docs with measured numbers.

**Next session entry point:** Deploy — provision Neon, set Render env (`ATTEST_DATABASE_URL`,
`ATTEST_SIGNING_KEY_PEM` from the freshly generated `backend/keys/private.pem`,
`ATTEST_GROQ_API_KEY`), re-ingest the corpus, and confirm the live tamper-and-verify demo.
See `DEPLOYMENT.md`.

## Completed

- [x] **Part 0–2 (MVP core)** — config, models, deterministic chunking, SHA-256 helpers,
  hand-rolled Merkle tree + proofs, Ed25519 signing, ingest pipeline, Groq query,
  query-time recheck, answer certificates, standalone verifier CLI.
- [x] **Part 3 (monitor)** — document-level hashing, quarantine state, lazy + cron + manual
  checks, `/monitor/trigger`, `/monitor/status`, `/corpus/health`.
- [x] **Part 4 (dashboard + eval)** — React 3-tab UI (Ask / Verify / Corpus Health),
  client-side browser verifier, eval harness.
- [x] **Neon Postgres + pgvector migration** — async SQLAlchemy, `pgvector.Vector(384)`,
  HNSW cosine index, reseed/first-boot lifespan. Verified against a live pgvector container.
- [x] **Docker** — `backend/Dockerfile`, `frontend/Dockerfile`, root `docker-compose.yml`
  (pgvector db + backend + frontend). `docker compose up -d db` used for local eval/tests.
- [x] **Client-side zero-trust verifier** — `frontend/src/lib/verify.js` (`@noble/ed25519`
  + Web Crypto). No server-side `/verify` route. Cross-checked byte-for-byte against the
  Python signer (see Deviations).
- [x] **Real eval run** — adversarial poison-all + clean re-check on the 8-doc corpus.
- [x] **Test suite green** — 37 passed with a DB / 36 passed + 1 skipped without one.

## Fixed during the 2026-07-11 pass (bugs the prior checklist did not catch)

- [x] **slowapi route params** — `@limiter.limit` requires a parameter literally named
  `request`; `/ingest`, `/query`, `/demo/run-isolated` used `req`, which crashed
  `app.main` on import. Renamed Starlette params to `request`, body params to `payload`.
- [x] **Missing `greenlet` dependency** — SQLAlchemy async needs it; every DB call failed
  without it. Pinned in `requirements.txt`.
- [x] **Embeddings unstorable** — `SentenceTransformer.encode(convert_to_numpy=False)`
  returned torch tensors that pgvector rejects, so the real ingest path never worked.
  Switched to numpy + `.tolist()` with an empty-batch guard.
- [x] **Canonical-JSON cross-language mismatch** — signer used `ensure_ascii=True` while the
  browser verifier emits raw UTF-8; any non-ASCII (e.g. an em-dash from the LLM) broke
  client-side verification. Set `ensure_ascii=False` in `app/crypto.py` and
  `verifier/verify.py`; added a regression test.
- [x] **Orphaned signing key** — committed `public_key.pem` had no matching private key.
  Generated a fresh Ed25519 keypair (public committed, private gitignored + handed off for
  the Render env var).
- [x] **Stale tests** — updated async-migration drift in `test_api_endpoints.py` /
  `test_verify_e2e.py`; removed the obsolete `POST /verify` test (route intentionally
  absent) and replaced it with a test asserting its absence.
- [x] **Cleanup** — removed leftover `storage_old.py` / `vectorstore_old.py`.

## Blocked

- **Live deployment is a hollow shell until the deploy step runs.** As of the audit the
  Render backend returned an empty corpus, `manifest_loaded: false`, and a *placeholder*
  public key — so no certificate could actually be verified in production. Requires the
  account-holder to complete the Neon + Render env steps above (not done autonomously).

## Deviations from plan

- **Client-side verifier (vs. plan Part 3.11 "CLI only").** The Verify tab does full
  Ed25519 + SHA-256 + Merkle verification in-browser. Rationale: makes "verifiable by anyone
  without trusting my server" literally true in the UI, not just the CLI. There is
  deliberately **no** `POST /verify` route so the backend can never be the trust boundary.
  The standalone CLI remains the canonical offline path. (Decision date: pre-existing in the
  repo; validated and documented 2026-07-11.)
- **`ensure_ascii=False` canonical JSON.** Required so the Python signer and the JS/CLI
  verifiers produce identical signing bytes. Load-bearing, not cosmetic.
- **Extra endpoints beyond the locked API surface** — `/documents*`, `/demo/*`, `/metrics`,
  `/healthz`. Kept (they power the dashboard/demo) but noted as drift from Part 3.11.
- **Render free tier is marginal for full embeddings.** sentence-transformers + torch
  baseline RSS is ~437 MB, peaking ~540 MB during ingest — above the 512 MB free tier even
  with batched embedding + gc. Production therefore runs in `hosted_preview_mode` (lexical
  preview embeddings, no torch). Documented honestly in `DEPLOYMENT.md`.

## Eval numbers (measured 2026-07-11, 8-doc corpus / 44 chunks, local pgvector)

- Tamper detection: **100%** (8/8 poisoned docs quarantined)
- False positive: **0%** (0/40 clean re-checks)
- Verify latency (p50): **0.32 ms** (100 certificates)
- Proof size (mean): **0.398 KB** (O(log n) Merkle inclusion proof)
- Ingest throughput: **12.72 docs/sec**

Raw output: `eval/results.json`.
