# ATTEST Build Progress

## Current focus

- [x] **Neon Postgres + pgvector Migration Complete** — Migrated persistence layer from local SQLite + ChromaDB to Neon Postgres with pgvector (2026-07-06)
  - Created SQLAlchemy models for Postgres schema (documents, chunks, manifests, certificates)
  - Rewrote storage.py to use async Postgres instead of SQLite
  - Rewrote vectorstore.py to use pgvector + sentence-transformers instead of ChromaDB
  - Updated main.py lifespan to connect to Neon and only ingest on first-ever boot
  - Updated all endpoints to work with async storage/vectorstore
  - Updated monitor.py and query.py to work with async operations
  - Added POST /demo/simulate-tampering endpoint for demo tampering simulation
  - Updated requirements.txt with asyncpg, pgvector, and sentence-transformers
  - Removed chromadb dependency

**Next session entry point:** Set up Neon database and run schema creation, then test the migrated system

## Completed

- [x] **Part 0** — Folder structure, `PROJECT_PLAN.md`, `PROGRESS.md` (2026-07-05)
- [x] **Step 1.1** — `config.py`, `models.py`, requirements, scaffold tests (2026-07-05)
- [x] **Step 1.2** — `chunk_text` + deterministic chunk tests (2026-07-05)
- [x] **Step 1.3** — SHA-256 helpers + Merkle tree + tests 3–5 (2026-07-05)
- [x] **Step 1.4** — Ed25519 sign/verify manifest + test 6 (2026-07-05)
- [x] **Step 1.5** — `vectorstore.py` Chroma + embeddings (2026-07-05)
- [x] **Step 1.6** — `ingest.py` full pipeline (2026-07-05)
- [x] **Step 1.7** — Groq `query.py` retrieval + generation (2026-07-05)
- [x] **Step 1.8** — FastAPI routes stub + lifespan reseed (2026-07-05)
- [x] **Step 2.1** — Query-time chunk hash recheck (2026-07-05)
- [x] **Step 2.2** — AnswerCertificate build + sign (2026-07-05)
- [x] **Step 2.3** — GET /certificate/{id} (2026-07-05)
- [x] **Step 2.4** — Standalone `verify.py` + tests 7–9 (2026-07-05)
- [x] **Step 2.5** — End-to-end manual demo script (2026-07-05)
- [x] **Step 3.1** — Document-level hash in manifest (2026-07-05)
- [x] **Step 3.2** — `monitor.py` + quarantine state (2026-07-05)
- [x] **Step 3.3** — Lazy check wired in query (2026-07-05)
- [x] **Step 3.4** — POST /monitor/trigger, GET /monitor/status, GET /corpus/health (2026-07-05)
- [x] **Step 3.5** — cron-job.org configured + documented (2026-07-05)
- [x] **Step 4.1** — React 3-tab UI (Ask / Verify / Corpus Health) (2026-07-05)
- [x] **Step 4.2** — Wired all API endpoints (POST /verify, CORS, API client) (2026-07-05)
- [x] **Step 4.3** — eval/run_eval.py with real metrics table (2026-07-05)
- [x] **Step 4.4** — UI styling improvements (custom scrollbar, consistent design) (2026-07-05)
- [x] **Step 5.2** — README with Mermaid diagram, deployment instructions, demo script, resume bullets (2026-07-05)
- [x] **Part 4 Corpus** — 8 real markdown documents created (hr-policy, security-policy, incident-runbook, onboarding, data-retention, code-of-conduct, engineering-standards, product-roadmap) (2026-07-05)
- [x] **Key generation** — generate_keys.py script and .gitignore for private key (2026-07-05)
- [x] **GitHub Actions CI** — Full CI pipeline with pytest and eval harness (2026-07-05)
- [x] **test_verify_e2e.py** — 3 comprehensive end-to-end tests (untampered, tampered, storage integration) (2026-07-05)

## Blocked

_None yet._

## Deviations from plan

- **Windows local dev:** `chromadb` requires MSVC build tools on Windows. Step 1.1 tests use minimal deps only (`pydantic`, `cryptography`, `pytest`). Full `requirements-dev.txt` installs on Linux/Render CI.

## Eval numbers (fill when ready)

- Tamper detection: __%
- False positive: __%
- Verify latency: __ ms
- Proof size: __ KB
- Ingest throughput: __ docs/sec
