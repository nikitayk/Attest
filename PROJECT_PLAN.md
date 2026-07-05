# ATTEST — Master Build Plan (Refined v2)

**Read this entire document before writing any code.**

This is the locked-in plan for ATTEST: a deployed web app that proves RAG answers are grounded in real, unaltered, timestamped source material — verifiable by anyone without trusting your server.

---

## HOW TO USE THIS DOCUMENT (for you + Cursor)

| When | Do this |
|------|---------|
| **First session** | Paste this file into repo root as `PROJECT_PLAN.md`. Create `PROGRESS.md`. Build only **MVP Core** until Part 6 Week 2 is done. |
| **Every session** | Read `PROJECT_PLAN.md` → read `PROGRESS.md` → pick the **next unchecked item** in Part 6 → build **only that item** → update `PROGRESS.md`. |
| **If stuck >30 min** | Mark item **BLOCKED** in `PROGRESS.md` with reason. Do not skip ahead on MVP Core. |
| **If behind schedule** | Cut from bottom of Part 1B tier list. **Never** cut tamper-and-catch demo. |

**Builder profile:** 4th-year engineering student, 2027 placements. Already shipped SENTINEL (input-trust) and APULSE. New to FastAPI, Merkle trees, Ed25519 — not new to shipping. Difficulty target: integrate known pieces correctly, not invent algorithms.

---

## GLOSSARY (read once)

| Term | Plain English |
|------|---------------|
| **RAG** | Retrieve relevant doc chunks → feed to LLM → generate answer with citations. |
| **Chunk** | Fixed-size slice of a document (e.g. 500 chars, 50 overlap). |
| **SHA-256 hash** | Fingerprint of text. One character change → completely different hash. |
| **Merkle tree** | Tree of hashes. Root summarizes all chunks. Proof = small path proving one chunk belongs to that root (O(log n) size). |
| **Manifest** | Signed record: doc IDs, chunk hashes, Merkle root, timestamp, embedding model version. |
| **Answer Certificate** | Self-contained JSON: query, answer, chunk text + hashes + Merkle proofs + signature. Verifier needs only this + public key. |
| **Fail closed** | On tamper → refuse answer + quarantine. Never silently answer with bad data. |
| **Reseed-on-boot** | On cold start, wipe and rebuild vector store + manifest from committed files. |
| **Lazy integrity check** | Re-hash retrieved chunks against manifest before every answer. |
| **ASI06** | OWASP Agentic Top 10 (Dec 2025): Memory & Context Poisoning — not "#1 risk" (that's ASI01 Goal Hijack). |

---

## PART 0 — CURSOR INSTRUCTIONS (before any feature code)

1. Create folder structure (Part 7).
2. Copy this document verbatim to `PROJECT_PLAN.md`.
3. Create `PROGRESS.md` — update after every Part 6 step:

```markdown
# ATTEST Build Progress

## Current focus
- [ ] Step X.Y — description

## Completed
- [x] Step ...

## Blocked
- Step ... — reason — workaround tried

## Deviations from plan
- None yet | (decision, why, date)

## Eval numbers (fill when ready)
- Tamper detection: __%
- False positive: __%
- Verify latency: __ ms
- Proof size: __ KB
- Ingest throughput: __ docs/sec
```

4. **Tiering is law:** MVP Core → Should-Have → Stretch. Never delay MVP for dashboard polish.
5. **No scope creep:** Do not add dependencies, services, or architecture not listed here without flagging the user first.

---

## PART 1 — WHAT THIS PROJECT IS

**Name:** ATTEST  
**Format:** Deployed web app — three-tab dashboard (Ask / Verify / Corpus Health) + live public URL.  
**One-liner:** Cryptographic chain of custody for RAG answers — proof, not just citations.

### Pitch (30 seconds)

> SENTINEL stops sensitive data going into an LLM. ATTEST proves what came out of a RAG system is grounded in real, unaltered, timestamped source material — verifiable by anyone, without trusting my server.

### Two-project narrative (say this explicitly in interviews)

> I built the input-trust layer (SENTINEL), then the output-trust layer (ATTEST), for LLM pipelines.

### Problem (precise)

RAG cites sources but cannot cryptographically guarantee:

1. Source wasn't altered after ingestion (document poisoning).
2. Citation maps to a real document at a specific point in time.
3. A third party can verify without trusting your backend/logs.

**Threat category:** OWASP Agentic Top 10 — **ASI06: Memory & Context Poisoning**.

**Name in demo:** insider poisoning, indirect prompt injection via retrieved content, silent staleness, unfalsifiable trust ("just trust our logs").

### Why ATTEST (not another RAG tutorial)

| Rejected idea | Why rejected |
|---------------|--------------|
| RAG eval/red-teaming tool | Productized (Promptfoo → OpenAI, RAGAS, Garak mature). "Worse Promptfoo in a month." |
| Generic RAG apps (quiz, finance, medical) | Same listicles every peer has. |
| **ATTEST** | Different axis (provenance/integrity). Extends SENTINEL story. Underbuilt at portfolio scale. |

### Related work (README — cite correctly)

| Work | How to cite |
|------|-------------|
| ZKPROV (arXiv 2506.20915) | Adjacent: training-data provenance via ZK. ATTEST = post-ingestion tamper detection in live RAG. Chose signed-hash over ZK for 4-week scope — show you understand the tradeoff. |
| OWASP ASI06 | Motivation for memory/context poisoning. |
| Sigstore/Rekor | Conceptual model (transparency log). MVP = local Ed25519 only; Rekor = Stretch. |

**Plan B** (only if ATTEST abandoned entirely): Calibrated abstention RAG — knows when to say "I don't know" with calibrated confidence. Do not pivot mid-build.

---

## PART 1B — SCOPE TIERS

| Tier | Contents | If only this ships |
|------|----------|-------------------|
| **MVP Core** (weeks 1–2.5) | Chunk → SHA-256 → Merkle → Ed25519 manifest → RAG → query-time recheck → signed Answer Certificate → standalone verifier CLI | Complete, demoable, interview-ready core |
| **Should-Have** (2.5–3.5) | Integrity monitor (lazy + cron + manual), 3-tab dashboard, eval harness with real numbers | System + UI + metrics |
| **Stretch** | Rekor/OpenTimestamps, Neon Postgres, Docker Compose, polished multi-page UI | README "future work" |

**Golden rule:** Interviewer only sees live tamper demo. That path must be bulletproof.

**Cut order if behind:** Rekor → Neon → dashboard polish → eval breadth (keep fewer real metrics, not placeholders).

**Never cut:** MVP tamper-and-catch sequence.

---

## PART 1C — PLACEMENT POSITIONING (SDE vs AI/ML)

### What interviewers actually test

| Role | They'll probe | Your proof |
|------|---------------|------------|
| **SDE** | System design, APIs, crypto hygiene, testing, deployment | Merkle from scratch, zero-trust verifier, typed boundaries, pytest suite, Render cold-start story |
| **AI/ML** | RAG pipeline, eval metrics, failure modes, responsible AI | Tamper detection rate, false positives, fail-closed behavior, ASI06 framing |
| **Both** | "What did you build vs libraries?" | Hand-rolled Merkle + proof verify; Groq/Chroma are integrations you wired correctly |

### Differentiators vs peers

1. **Two-project trust stack** (SENTINEL + ATTEST) — coherent story, not random projects.
2. **Live demo with adversarial step** — edit file → system refuses → offline verifier still validates old cert.
3. **Deterministic crypto test suite** — no LLM mocking flakiness; honest README claim.
4. **Self-contained certificate** — shows you understand "hash alone proves nothing without text."
5. **Real eval numbers** — even imperfect false-positive rate beats fake [X]%.

### Questions you must answer cold

| Question | Answer |
|----------|--------|
| Why Merkle tree instead of shipping full document in certificate? | O(log n) proof size. |
| Why deterministic chunking? | Re-ingest must reproduce same hashes. |
| Why verifier can't import backend? | Zero-trust claim becomes false. |
| What if attacker tampers before ingestion? | Out of scope; say it honestly. |
| What if signing key is compromised? | Out of scope for MVP; key in env only, rotate per deploy. |
| Why reseed-on-boot? | Render free tier wipes disk; simpler than fighting ephemeral storage. |
| Why Groq not OpenAI? | Free tier, fast demo, no card. |
| Why not ZKPROV approach? | Different problem; ZK is overkill for 4-week portfolio. |

---

## PART 2 — ARCHITECTURE

### Components

| # | Component | Tier | Responsibility |
|---|-----------|------|----------------|
| 1 | Ingestion | MVP | Chunk, hash, Merkle, sign manifest, embed |
| 2 | Store | MVP | Chroma (vectors) + manifest store (SQLite MVP) |
| 3 | Query + Certify | MVP | Retrieve, recheck hashes, generate, sign certificate |
| 4 | Standalone Verifier | MVP | CLI, cryptography + hashlib only |
| 5 | Integrity Monitor | Should-Have | Periodic + lazy + manual recheck, quarantine |
| 6 | Dashboard | Should-Have | Ask / Verify / Corpus Health |

### End-to-end flow

```
Documents (~10 files in backend/data/)
   │
   ▼
[INGEST] chunk(500,50) → SHA-256 each → Merkle tree → sign Manifest
   │
   ▼
[STORE] embeddings → Chroma | manifest → SQLite/file
   │
   ▼ (query)
[QUERY+CERTIFY] top-k retrieve → re-hash chunks vs manifest
   ├─ MATCH → Groq generate → sign AnswerCertificate
   └─ MISMATCH → withhold answer, TAMPERED, quarantine doc_id
   │
   ▼
[VERIFY CLI] certificate + public_key.pem → VALID/INVALID + reason
```

**Integrity monitor** (parallel):
Lazy (every query) + external cron (`POST /monitor/trigger`) + dashboard "Check Now" → whole-file SHA-256 vs manifest → quarantine on drift. Does not silently re-index.

### Certificate schema (locked)

```json
{
  "certificate_id": "uuid4",
  "query": "string",
  "answer": "string",
  "chunks": [
    {
      "doc_id": "string",
      "chunk_index": 0,
      "text": "actual chunk text — required for verification",
      "hash": "hex sha256",
      "merkle_proof": ["hex hash", "..."]
    }
  ],
  "doc_id": "primary doc cited",
  "merkle_root": "hex",
  "manifest_timestamp": "ISO8601 UTC",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "llm_model": "groq model id",
  "signature": "base64 ed25519 over canonical json bytes"
}
```

**Signing payload:** Canonical JSON of all fields except `signature` (sorted keys, no whitespace — document exact serialization in code comments).

**Interview line:** "The certificate is self-contained — verifier needs only the certificate and my public key."

---

## PART 3 — ENGINEERING DECISIONS (every choice + why)

### 3.1 Chunking

| Decision | Value | Why |
|----------|-------|-----|
| Algorithm | Character-based sliding window | Reproducible across machines; no tokenizer version drift |
| chunk_size | 500 | Small enough for precise citations; large enough for context |
| chunk_overlap | 50 | Reduces boundary-split information loss |
| Splitter | Pure function of (text, size, overlap) | Monitor re-reads file from disk and must get identical chunks |
| **Forbidden** | LangChain "smart" splitters, sentence-aware randomness, PDF layout-dependent extraction without normalization | Non-determinism → false tamper alerts |

**Implementation spec** (`ingest.py`):

```python
def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    # Normalize: strip BOM, normalize newlines to \n
    # Step by (chunk_size - overlap), slice [:chunk_size]
    # Empty text → []
```

**PDF handling (MVP):** Extract text with pypdf or pdfplumber, then run same `chunk_text`. Store extracted `.txt` alongside or extract deterministically at ingest only — pick one path and never mix.

### 3.2 Hashing (two levels)

| Level | When | How | Why |
|-------|------|-----|-----|
| Document | Monitor scans all docs | SHA256(utf-8 bytes of normalized file) | Cheap full-corpus drift check |
| Chunk | Ingest + query recheck + Merkle leaves | SHA256(utf-8 chunk text) | Precise citation-level integrity |

**Hash encoding:** lowercase hex strings everywhere (API, JSON, tests).

### 3.3 Merkle tree (hand-rolled — interview centerpiece)

| Decision | Choice | Why |
|----------|--------|-----|
| Tree shape | Binary tree, pad odd level by duplicating last leaf | Simple, standard, easy to explain |
| Leaf order | Chunk index order 0..n-1 within each doc; docs processed in sorted doc_id | Deterministic root |
| Parent hash | SHA256(left_hex + right_hex) as UTF-8 concatenation | Document in code; tests lock behavior |
| Empty tree | Root = SHA256("") or reject empty doc — pick one, test it | Edge case interviewers ask |
| Proof format | List of sibling hashes + "L"/"R" position indicators OR implicit left-to-right pairing — pick one, never change | Verifier must match ingest |

**Required functions** (`ingest.py`):

```python
build_merkle_tree(leaves: list[str]) -> MerkleTree  # root + levels
get_merkle_proof(tree, leaf_index: int) -> list[str]
verify_merkle_proof(leaf_hash, proof, root) -> bool  # also duplicated in standalone verifier
```

**Why hand-rolled:** "I implemented Merkle inclusion proof verification from scratch" > "I piped merkletools."

### 3.4 Signing (Ed25519)

| Decision | Choice | Why |
|----------|--------|-----|
| Library | `cryptography` (pyca) | Battle-tested; never roll your own crypto |
| Keygen | Fresh per deploy | Compromise of old deploy doesn't affect new |
| Private key | Env var `ATTEST_SIGNING_KEY` (PEM or base64 seed) | Never in repo, logs, or request params |
| Public key | `GET /public-key` + committed `backend/keys/public_key.pem` | Two independent sources for verifier |
| Signed objects | Manifest, AnswerCertificate | Same verify function pattern |

**Manifest schema** (`models.py`):

```python
class ChunkRecord(BaseModel):
    doc_id: str
    chunk_index: int
    hash: str  # sha256 hex

class Manifest(BaseModel):
    manifest_id: str
    doc_ids: list[str]
    chunks: list[ChunkRecord]  # ordered
    merkle_root: str
    document_hashes: dict[str, str]  # doc_id -> whole-file hash
    created_at: datetime  # UTC
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    signature: str
```

### 3.5 Persistence

| Decision | MVP | Upgrade (Should-Have/Stretch) |
|----------|-----|--------------------------------|
| Vector store | Chroma in-memory or `/tmp/chroma` | Same — always rebuilt on boot |
| Manifest | SQLite file `/tmp/attest.db` or in-memory + JSON export | Neon Postgres |
| Certificates | SQLite table or JSON files in `/tmp/certs/` | Postgres |
| Boot behavior | Wipe + re-ingest from `backend/data/` | Same unless Neon stores manifest AND you implement incremental ingest (Stretch only) |

**Why reseed-on-boot:** Render free tier wipes local disk on spin-down. ~10 docs re-ingest in seconds — acceptable cold start narrative.

**Startup sequence** (`main.py` lifespan):

1. Load settings + signing key from env
2. Wipe Chroma collection
3. Run ingestion on all `backend/data/*`
4. Persist manifest
5. Log: ingested N docs, M chunks, root=...

### 3.6 Integrity monitor

| Mode | Trigger | Action |
|------|---------|--------|
| Lazy | Every `POST /query` before generate | Re-hash retrieved chunks vs manifest |
| Cron | External cron → `POST /monitor/trigger` every 15 min | Whole-file hash all docs vs manifest |
| Manual | Dashboard "Check Now" → same endpoint | Demo control |

**On mismatch:**

- Set doc status → `QUARANTINED` in store
- Do not re-index silently
- Return typed result (not exception)
- Optional: log/alert structure for dashboard

**Quarantine effect:** Queries retrieving chunks from quarantined doc → fail closed with exact message:

> Source integrity check failed — answer withheld, document quarantined.

### 3.7 Embeddings & LLM

| Component | Choice | Why |
|-----------|--------|-----|
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | ~90MB, local, free, fits 512MB Render |
| Vector DB | ChromaDB | Simple, Python-native, rebuildable |
| LLM | Groq API (`llama-3.3-70b-versatile` or current free model) | Free tier, fast, no credit card |
| RAG pattern | top-k=3, concatenate chunks, simple prompt | Boring = debuggable |

**Groq prompt template** (lock early):

```
You answer ONLY from the provided context. If context is insufficient, say "I don't know."
Context:
{chunks}
Question: {query}
Answer:
```

Store `llm_model` in certificate for reproducibility narrative.

### 3.8 Config (`config.py`)

Single `Settings` class via pydantic-settings. Nothing else reads `os.environ`.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ATTEST_")
    hash_algo: str = "sha256"
    chunk_size: int = 500
    chunk_overlap: int = 50
    signing_key_pem: str  # required in prod
    public_key_path: Path = Path("keys/public_key.pem")
    data_dir: Path = Path("data")
    chroma_path: Path = Path("/tmp/chroma")
    manifest_db_path: Path = Path("/tmp/attest.db")
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    top_k: int = 3
    quarantine_on_mismatch: bool = True
    monitor_interval_seconds: int = 900
    anchor_backend: str = "local"  # "local" | "rekor" (stretch)
```

### 3.9 Typed contracts & error handling

**Rule:** No raw dict across module boundaries. Use Pydantic models:

`ChunkRecord`, `Manifest`, `AnswerCertificate`, `VerifyResult`, `QueryResult`, `MonitorStatus`, `CorpusHealth`

**Rule:** Expected failures are return values, not exceptions.

```python
class VerifyResult(BaseModel):
    ok: bool
    reason: str
    hash_match: bool
    proof_valid: bool
    signature_valid: bool

class QueryResult(BaseModel):
    ok: bool
    answer: str | None
    certificate: AnswerCertificate | None
    error: str | None  # e.g. tamper message
```

### 3.10 Pluggable anchor (future-proof)

```python
def anchor(manifest: Manifest, settings: Settings) -> AnchorResult:
    if settings.anchor_backend == "local":
        return _anchor_local(manifest)  # signature only — MVP
    if settings.anchor_backend == "rekor":
        return _anchor_rekor(manifest)  # Stretch — stub raises NotImplementedError until built
```

### 3.11 API surface (locked)

| Method | Path | Body/Params | Response |
|--------|------|-------------|----------|
| POST | `/ingest` | optional doc_id for single re-ingest | Manifest summary |
| POST | `/query` | `{ "query": "..." }` | QueryResult |
| GET | `/certificate/{id}` | — | AnswerCertificate |
| POST | `/monitor/trigger` | — | MonitorStatus |
| GET | `/monitor/status` | — | last run time, quarantined count |
| GET | `/corpus/health` | — | list docs + status OK/QUARANTINED + hashes |
| GET | `/public-key` | — | PEM text |

**Verifier is NOT an API route** — separate CLI only.

**CORS:** Allow Vercel frontend origin in production.

**Rate limiting** (optional Should-Have): Reuse SENTINEL sliding-window limiter on `/query` — credit comment in code.

### 3.12 Standalone verifier (`backend/verifier/verify.py`)

**Hard constraints:**

- Single file (or `verify.py` + `models_copy.py` with duplicated minimal types — prefer one file)
- Dependencies: `cryptography`, `hashlib`, `json`, `argparse` only
- Must not import `app.*`

**CLI:**

```bash
python verify.py --certificate path/to/cert.json --public-key path/to/public_key.pem
# Exit 0 = VALID, Exit 1 = INVALID
# stdout: VALID — grounded in unaltered source at 2026-07-05T...
#     or: INVALID — reason: merkle proof failed
```

---

## PART 4 — CORPUS PLAN

**Total:** ~10 documents. Quality > quantity.

| Source | Count | Examples |
|--------|-------|----------|
| Self-written markdown | 6–8 | HR policy, security policy, incident runbook, onboarding, data retention, code of conduct |
| Public domain | 2 | NIST excerpt PDF, OWASP doc |

**Location:** `backend/data/{doc_id}.md` or `.pdf`  
**Naming:** `doc_id` = filename stem, lowercase, hyphenated (e.g. `hr-policy.md` → `hr-policy`)

**Do not:** scrape web, use copyrighted content, or grow corpus beyond ~10 for MVP.

---

## PART 5 — TECH STACK (with rejection rationale)

| Component | Choice | Rejected alternative | Why chosen |
|-----------|--------|---------------------|------------|
| Backend | FastAPI | Flask, Django | Async, OpenAPI, standard for ML serving |
| Config | pydantic-settings | Raw os.environ | Single source of truth |
| Vectors | Chroma | Pinecone, Weaviate | Free, local, no account |
| Embeddings | MiniLM-L6-v2 | OpenAI embeddings | Paid API, overkill |
| LLM | Groq | OpenAI, Ollama on Render | Groq free + fast; Ollama too heavy on 512MB |
| Hash | hashlib SHA-256 | Blake3 | SHA-256 universally understood in interviews |
| Sign | Ed25519 | RSA | Smaller keys, faster, modern |
| Merkle | Hand-rolled | merkletools | Interview story |
| Manifest DB | SQLite | Postgres (MVP) | Zero setup; Neon later |
| Backend host | Render free | Vercel for Python | Vercel serverless timeout kills ingest |
| Frontend host | Vercel | Render static | Free, fast CDN |
| Cron | cron-job.org | In-app loop | Render sleeps after 15 min idle |
| UI | React + Vite + Tailwind | Next.js | Matches SENTINEL; simple SPA |
| Tests | pytest | unittest | Ecosystem standard |
| CI | GitHub Actions | — | Free, expected on resume |

---

## PART 6 — BUILD ORDER (detailed)

### Week 1 — Ingest + RAG (MVP Core)

| Step | Deliverable | Done when |
|------|-------------|-----------|
| 1.1 | Repo scaffold, `config.py`, `models.py` | Settings load, tests import |
| 1.2 | `chunk_text` + tests 1–2 | Deterministic chunks |
| 1.3 | SHA-256 helpers + Merkle tree + tests 3–5 | Proofs verify in pytest |
| 1.4 | Ed25519 sign/verify manifest + test 6 | Manifest signature round-trip |
| 1.5 | `vectorstore.py` Chroma + embeddings | Embeddings stored |
| 1.6 | `ingest.py` full pipeline | CLI/script ingests `data/` |
| 1.7 | Groq `query.py` retrieval + generation | `POST /query` returns answer (no cert yet) |
| 1.8 | FastAPI routes stub + lifespan reseed | App boots, ingests, answers |

### Week 2 — Certify + Verify (MVP Core — do not rush past)

| Step | Deliverable | Done when |
|------|-------------|-----------|
| 2.1 | Query-time chunk hash recheck | Tampered chunk → typed failure |
| 2.2 | AnswerCertificate build + sign | Certificate JSON with proofs |
| 2.3 | `GET /certificate/{id}` | Retrieve by ID |
| 2.4 | Standalone `verify.py` + tests 7–9 | Works with backend off |
| 2.5 | End-to-end manual demo script (Part 9) | You can run demo locally twice |

### Week 2.5–3 — Monitor (Should-Have)

| Step | Deliverable |
|------|-------------|
| 3.1 | Document-level hash in manifest |
| 3.2 | `monitor.py` + quarantine state |
| 3.3 | Lazy check wired in query |
| 3.4 | `POST /monitor/trigger`, `GET /monitor/status`, `GET /corpus/health` |
| 3.5 | cron-job.org configured + documented in README |

### Week 3–3.5 — Dashboard + Eval (Should-Have)

| Step | Deliverable |
|------|-------------|
| 4.1 | React 3-tab UI (Ask / Verify / Corpus Health) |
| 4.2 | Wire all API endpoints |
| 4.3 | `eval/run_eval.py` with real metrics table |
| 4.4 | Match SENTINEL visual language |

### Week 3.5–4 — Ship

| Step | Deliverable |
|------|-------------|
| 5.1 | Deploy backend Render, frontend Vercel |
| 5.2 | README per Part 12 + Mermaid diagram |
| 5.3 | 90-second demo video |
| 5.4 | Resume bullets with real numbers (Part 13) |

---

## PART 7 — FOLDER STRUCTURE

```
attest/
├── PROJECT_PLAN.md
├── PROGRESS.md
├── README.md
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── ingest.py          # chunk, hash, merkle, sign
│   │   ├── crypto.py          # hash, merkle, sign helpers (importable by app)
│   │   ├── query.py
│   │   ├── monitor.py
│   │   ├── vectorstore.py
│   │   └── storage.py         # SQLite manifest + certs + quarantine
│   ├── verifier/
│   │   └── verify.py          # NO imports from app/
│   ├── keys/
│   │   └── public_key.pem     # committed
│   ├── data/                  # ~10 corpus files
│   ├── tests/
│   │   ├── test_hash.py
│   │   ├── test_merkle.py
│   │   ├── test_signatures.py
│   │   ├── test_verify_e2e.py
│   │   └── test_verifier_standalone.py
│   ├── requirements.txt
│   └── requirements-dev.txt   # pytest, httpx, etc.
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api/client.js
│   │   ├── pages/Ask.jsx
│   │   ├── pages/Verify.jsx
│   │   └── pages/CorpusHealth.jsx
│   ├── package.json
│   └── vite.config.js
├── eval/
│   └── run_eval.py
└── .github/workflows/ci.yml
```

**Note:** `crypto.py` in app is allowed; verifier copies minimal logic into `verify.py` to keep zero backend dependency — duplicate Merkle verify in verifier file with comment "intentionally duplicated for zero-trust boundary."

---

## PART 8 — TESTING & EVAL

### Pytest suite (deterministic, no LLM)

| Test | Gap it closes |
|------|---------------|
| `test_hash_is_stable` | Same input → same hash always |
| `test_single_char_change_flips_hash` | Sensitivity to tampering |
| `test_merkle_root_changes_if_any_leaf_changes` | Root binds all leaves |
| `test_merkle_proof_valid_for_untampered_chunk` | Happy path proof |
| `test_merkle_proof_fails_for_tampered_chunk` | Proof detects tampered leaf |
| `test_signature_fails_with_wrong_public_key` | Forgery under wrong identity fails |
| `test_reordered_manifest_fails_signature` | Reorder after sign fails (docstring required) |
| `test_verify_end_to_end_untampered_passes` | Full pipeline VALID |
| `test_verify_end_to_end_tampered_fails` | Full pipeline INVALID |
| `test_verifier_runs_with_backend_offline` | Zero-trust claim literal |

**Naming rule:** Test name = exact bug/gap. Docstring = one sentence explaining why this test exists.

### Eval harness (`eval/run_eval.py`)

One command: `python eval/run_eval.py`

| Metric | How to measure |
|--------|----------------|
| Tamper detection rate | N questions; poison K known chunks post-ingest; report caught/K |
| False-positive rate | Re-ingest unmodified corpus M times; report wrongful quarantines/M |
| Verification latency (ms) | Time `verify.py` on 100 certs, p50 |
| Proof size (KB) | Mean JSON size of merkle_proof arrays |
| Ingestion throughput | docs/sec for full corpus |

**Output:** ASCII table + one plain-English line per metric. No placeholder numbers in README.

---

## PART 9 — LIVE DEMO SCRIPT (90 seconds)

1. **Ask tab:** Question → answer + certificate JSON visible.
2. **Editor:** Open `backend/data/hr-policy.md`, change one sentence. Say: "Simulating document poisoning after ingestion."
3. **Ask tab:** Same question → exact message: `Source integrity check failed — answer withheld, document quarantined.`
4. **Terminal (new):** "This has zero access to my server." Run verifier on step 1 cert → `VALID — grounded in unaltered source at [timestamp]`.

Record this video. Live demos fail; video is backup.

---

## PART 10 — FRONTEND SPEC

One SPA, three tabs (not multi-page routing complexity):

| Tab | UI elements | API |
|-----|-------------|-----|
| **Ask** | Query input, Submit, Answer panel, Certificate JSON `<pre>` | `POST /query`, show cert inline |
| **Verify** | Textarea paste cert, optional pubkey override, Verify button, ✅/❌ + reason | Call verifier logic via backend proxy OR run WASM/local — MVP: `POST /verify` is **FORBIDDEN** by plan → Verify tab calls a frontend port of verify logic OR documents "paste cert, run CLI" for MVP. **Decision for Should-Have:** Add `POST /verify-local` that runs same algorithm server-side for UI convenience but README states CLI is the trust anchor. Better MVP: Verify tab shells out is impossible in browser — implement duplicate verify logic in small `frontend/src/lib/verify.js` using Web Crypto for Ed25519 OR instruct user to use CLI output in demo. **Simplest demo path:** Verify tab displays instructions + cert validation via fetched `/public-key` and client-side JS verify (copy crypto logic once). Flag in PROGRESS which approach you chose. |
| **Corpus Health** | Table: doc_id, status, doc_hash, last_checked; "Check Now" button | `GET /corpus/health`, `POST /monitor/trigger` |

**Style:** Reuse SENTINEL colors, typography, card layout.

**Env:** `VITE_API_URL=https://your-render-app.onrender.com`

---

## PART 11 — DEPLOYMENT

### Render (backend)

- **Build:** `pip install -r requirements.txt`
- **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Env vars:** `ATTEST_SIGNING_KEY_PEM`, `ATTEST_GROQ_API_KEY`, `ATTEST_GROQ_MODEL`
- **Cold start:** Expect 30–60s; ingestion runs in lifespan — show loading state in frontend.

### Vercel (frontend)

- **Root:** `frontend/`
- **Env:** `VITE_API_URL`

### Key generation (run locally once per deploy)

```bash
python -c "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; from cryptography.hazmat.primitives import serialization; k=Ed25519PrivateKey.generate(); open('private.pem','wb').write(k.private_bytes(...)); open('public_key.pem','wb').write(k.public_key().public_bytes(...))"
```

Commit `public_key.pem` only. Paste private PEM into Render env.

### cron-job.org

- **URL:** `POST https://your-app.onrender.com/monitor/trigger`
- **Interval:** 15 minutes (keeps warm + monitors)

---

## PART 12 — README STRUCTURE

(Follow original Part 12 — add Architecture diagram, Honest limitations, Eval table with real numbers, Live demo link + video.)

**Limitations (required):**

- No protection against pre-ingestion poisoning
- Compromised signing key breaks trust model
- No external transparency log in MVP
- Reseed-on-boot = manifest timestamp resets on cold start (explain why that's OK for demo)

---

## PART 13 — RESUME BULLETS (fill after eval)

Use real numbers only. Template:

- Architected cryptographic chain-of-custody for agentic RAG (SHA-256 Merkle tree, Ed25519 signed manifests and answer certificates).
- Built integrity monitor with X% tamper detection, Y% false-positive rate on Z-doc eval set.
- Zero-trust standalone verifier — Merkle proofs + signature check, N ms verify latency, O(log n) proof size — addresses OWASP ASI06.

---

## PART 14 — COMMON PITFALLS (read before coding)

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Non-deterministic chunking | False tamper on clean docs | Lock `chunk_text`, normalize newlines |
| Verifier imports backend | Zero-trust claim false | Duplicate verify logic in CLI |
| Signing JSON with whitespace drift | Valid cert fails verify | Canonical `json.dumps(sort_keys=True, separators=(',', ':'))` |
| Hashing wrong encoding | Intermittent mismatches | Always UTF-8 encode before SHA-256 |
| Merkle proof direction ambiguous | Proof fails randomly | Document L/R rule in tests |
| Assuming Chroma persists on Render | Empty retrieval after spin-down | Reseed in lifespan |
| LLM in pytest | Flaky CI | Crypto tests only in CI; eval script separate |
| Placeholder eval metrics | Resume/interview credibility hit | Ship fewer real numbers |

---

## PART 15 — PROGRESS.md UPDATE PROTOCOL

After each Part 6 step:

1. Mark step complete with date.
2. Note any deviation + justification.
3. If eval numbers changed, update README + resume drafts.
4. List next session entry point (exact file/function to open).

---

## PART 16 — SESSION PROMPT FOR CURSOR (copy-paste each session)

```
You are building ATTEST. Read PROJECT_PLAN.md fully, then PROGRESS.md.
Rules:
- Build ONLY the next unchecked item in Part 6.
- MVP Core tier until Week 2 complete — no dashboard, no monitor, no stretch.
- Follow every engineering decision in Part 3 exactly; if you must deviate, stop and document why in PROGRESS.md.
- Typed Pydantic models at all boundaries; expected failures return VerifyResult/QueryResult, never raise.
- Verifier must not import backend code.
- Tests: name after the gap closed, with docstrings.
- After completing the step, update PROGRESS.md.

Current step: [PASTE FROM PROGRESS.md]
```

---

## PART 17 — NAMING

**Final name:** ATTEST  
**Repo:** `attest` or `attest-rag`

---

## Summary of refinements added

- Glossary + placement positioning — SDE vs AI/ML probes and differentiators.
- Locked schemas — Manifest, Certificate, API table with methods.
- Merkle implementation spec — tree shape, hash concatenation, required functions.
- Chunking pseudocode rules — normalization, forbidden splitters.
- Startup lifespan sequence — explicit reseed-on-boot steps.
- Exact demo error string — fail-closed message locked.
- Verify tab strategy — browser/client verify vs CLI trust anchor (decision flagged).
- Week 1–2 step checklist — "done when" criteria for Cursor.
- Pitfalls table — common failure modes from similar projects.
- Session prompt template — paste into every Cursor session.
- Tech stack rejection column — why alternatives were not chosen (interview gold).
- `crypto.py` vs verifier duplication — explicit zero-trust boundary pattern.
