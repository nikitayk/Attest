# ATTEST — Interview Preparation

A study guide for explaining ATTEST cold. Read top to bottom once; re-read §1, §4, and §9
before an interview. Every number here is real and measured (2026-07-11) — see `eval/results.json`.

---

## 0. If I only have 2 minutes (cheat sheet)

- **One line:** "SENTINEL stops sensitive data going *into* an LLM; ATTEST proves what came
  *out* of a RAG system is grounded in real, unaltered, timestamped source — verifiable by
  anyone, without trusting my server."
- **The single most impressive fact:** I hand-implemented Merkle-tree construction *and*
  inclusion-proof verification from scratch (not a library), and the same proof format
  verifies in three independent places: the backend, a standalone Python CLI, and a
  from-scratch browser verifier.
- **Numbers:** 100% tamper detection, 0% false positives (8-doc adversarial set), 0.32 ms
  p50 verification, ~0.4 KB O(log n) proofs, 12.7 docs/sec ingest.
- **The resume bullets** are in `README.md` under "Resume Bullets".

---

## 1. The 90-second pitch (memorize)

> "RAG systems cite their sources, but a citation isn't proof. There's no cryptographic
> guarantee the source wasn't altered after it was ingested, no proof of *when* it was
> ingested, and no way for a third party to check an answer without trusting your backend.
> That's OWASP ASI06 — Memory & Context Poisoning.
>
> ATTEST fixes that. At ingestion I hash every chunk with SHA-256, build a Merkle tree per
> corpus, and sign the root with an Ed25519 key. Every answer ships with a self-contained
> certificate: the exact chunks used, their hashes, Merkle inclusion proofs, a timestamp,
> and a signature. Before generating an answer I re-hash the retrieved chunks against the
> signed manifest — if anything's been tampered with, the system fails closed: it withholds
> the answer and quarantines the document instead of answering off poisoned text.
>
> The part I'm proudest of is verification. Anyone can take a certificate and my public key
> and verify — recompute the hashes, check the Merkle proofs, check the signature — with
> zero access to my backend. It runs entirely in the browser and as a standalone CLI. So the
> claim 'this answer really came from this exact, unaltered document' isn't 'trust my logs' —
> it's math you can check yourself."

**Two-project story (behavioral / "tell me about a project"):**
"I built a trust stack for LLM pipelines. SENTINEL is the input-trust layer — it guards what
goes into the model. ATTEST is the output-trust layer — it proves what came out is grounded
and unaltered. Same DNA, opposite ends of the pipe. That coherence is deliberate: it shows I
think in systems, not one-off demos."

---

## 2. Every engineering decision — "why this, why not that"

Say these in first person, confidently.

**Why a Merkle tree instead of putting the whole document in the certificate?**
"So the proof is O(log n), not O(n). A certificate only needs the sibling hashes on the path
from one chunk to the root — about 0.4 KB in my eval — instead of shipping the whole corpus.
It's the same reason Bitcoin uses them for SPV proofs."

**Why hand-roll the Merkle tree instead of a library like merkletools?**
"Two reasons. One, it's the load-bearing security primitive — I want to know exactly how leaf
ordering, odd-node padding, and proof direction work, because a subtle mismatch between how
you build the tree and how you verify it silently breaks everything. Two, I have to duplicate
the *verify* half in three places — backend, CLI, browser — so I need it small and fully
understood. 'I implemented Merkle inclusion-proof verification from scratch' is also just a
stronger sentence than 'I imported a package.'"

**Why Ed25519 over RSA?**
"Smaller keys (32-byte public key), faster signing and verification, deterministic signatures
so no bad-randomness footgun, and it's the modern default. RSA would work but it's bigger and
slower with more ways to hold it wrong. I never roll my own signature crypto though — that's
the `cryptography` library; hand-rolling is for the Merkle logic, not the elliptic curve."

**Why SHA-256 and not BLAKE3?**
"BLAKE3 is faster, but SHA-256 is universally understood and every interviewer can reason
about it. Hashing isn't my bottleneck — the embedding model is — so I optimized for clarity."

**Why deterministic, character-based chunking (no 'smart' splitters)?**
"Because the monitor re-reads the file from disk and must reproduce byte-identical chunks to
re-hash them. Any non-determinism — tokenizer version drift, sentence-aware randomness,
layout-dependent PDF extraction — would produce false tamper alerts on clean documents. A
cry-wolf integrity monitor is worthless, so determinism is a correctness requirement, not a
style choice."

**Why can the verifier not import backend code?**
"Because the whole pitch is 'you don't have to trust my server.' If the verifier imported my
app, verifying would depend on my code being honest — the claim becomes circular. So the CLI
depends only on `cryptography` and the standard library, and the browser verifier is a
separate from-scratch implementation. The Merkle-verify logic is *intentionally duplicated*
across them with a comment saying so."

**Why Postgres + pgvector over Chroma/Pinecone?**
"I migrated from SQLite + Chroma to Neon Postgres + pgvector so vectors, manifests, and
certificates live in one transactional store with an HNSW index for similarity search, and so
state survives Render's ephemeral disk. Pinecone/Weaviate would mean another account and
vendor; pgvector is just Postgres."

**Why Groq, not OpenAI?**
"Free tier, fast inference, no credit card for a portfolio project. And the LLM is the *least*
interesting part here — it's swappable; the value is the crypto envelope around it."

**Why reseed-on-boot?**
"Render's free tier wipes local disk on spin-down. Re-ingesting ~10 docs takes seconds, so
rather than fight ephemeral storage I rebuild the vector store and manifest from the committed
corpus on cold start. It's an honest, simple cold-start story."

**Why signed-hash provenance and not zero-knowledge (ZKPROV)?**
"ZK dataset provenance (arXiv 2506.20915) is a different, heavier problem — proving properties
of training data without revealing it. For post-ingestion tamper detection in a live RAG,
signed hashes give me everything I need at a fraction of the complexity. Choosing the
pragmatic tool and being able to explain the tradeoff is the point."

---

## 3. Code-level walkthroughs (be able to sketch these)

### 3a. Merkle tree + proof (`backend/app/crypto.py`)
- `build_merkle_tree(leaves)` — binary tree; on an odd level the last node pairs with itself;
  parent = `SHA256(left_hex + right_hex)` as UTF-8 concatenation of the two hex strings;
  empty input → root = `SHA256("")`. Stores every level so proofs are cheap.
- `get_merkle_proof(tree, leaf_index)` — walks level by level collecting the *sibling* hash;
  the L/R position is implicit from index parity (even index → sibling is on the right).
- `verify_merkle_proof(leaf_hash, proof, root, leaf_index)` — replays that walk: if the
  running index is even, `hash(current, sibling)`, else `hash(sibling, current)`; halve the
  index each step; final value must equal the root.
- **The key invariant:** build and verify must agree on ordering exactly. That's why verify is
  duplicated verbatim in `verifier/verify.py` and `frontend/src/lib/verify.js`.

### 3b. Certificate signing + canonical JSON (`app/crypto.py`)
- `canonical_json_bytes(payload)` = `json.dumps(payload, sort_keys=True,
  separators=(",", ":"), ensure_ascii=False)` encoded UTF-8.
- **Why each flag:** `sort_keys` → order-independent; compact `separators` → no whitespace
  drift; `ensure_ascii=False` → raw UTF-8 so it matches the browser's `JSON.stringify`
  (see the war story in §4). Signature is Ed25519 over these exact bytes, base64-encoded, and
  covers every field *except* `signature` itself.

### 3c. Fail-closed retrieval (`app/query.py` + `app/monitor.py`)
- On every query, retrieved chunks are re-hashed and compared to the signed manifest. On any
  mismatch the pipeline returns a typed failure (never raises) with the exact string
  `"Source integrity check failed — answer withheld, document quarantined."` and the doc is
  marked QUARANTINED. Quarantined docs are excluded from future retrieval. It never silently
  answers from unverified content and never silently re-indexes.

### 3d. Client-side verifier (`frontend/src/lib/verify.js`)
- `verifyCertificateClient(certificate, publicKeyPem)`: strips `signature`, canonicalizes the
  rest (recursive key sort + `JSON.stringify`), verifies Ed25519 with `@noble/ed25519`, then
  for each chunk re-hashes the text with Web Crypto SHA-256 and checks the Merkle proof. The
  only network call anywhere is fetching the public key. Returns
  `{ok, reason, hash_match, proof_valid, signature_valid}` — a result object, not an exception.

---

## 4. Traps & hard questions (honest answers)

**"Isn't this just rebuilding Sigstore / Certificate Transparency?"**
"Conceptually I adapted their model — a signed, independently-verifiable record of provenance —
and I credit them explicitly in the README. The difference is domain: they secure the
*software* supply chain (packages, container images); ATTEST secures the *data* supply chain of
a RAG system. I'm not claiming to have invented transparency logs; a public transparency log
(Rekor) is even listed as future work."

**"What if the signing key is compromised?"**
"Then the trust model breaks — an attacker could sign forged certificates. That's out of scope
for this build and I say so honestly. A production system would need key rotation, an HSM or
KMS instead of an env var, and ideally threshold/multi-party signing. I know the gap; I scoped
it out deliberately for a portfolio timeline."

**"What about poisoning that happens *before* ingestion?"**
"Explicitly out of scope. ATTEST proves a document hasn't changed *since* I ingested it — it's
a chain of custody from ingestion onward. If the source was already poisoned when I first saw
it, my hash faithfully commits to poisoned text. Detecting that is a different problem
(source-reputation / content analysis)."

**"Why not full zero-knowledge proofs?"**
"Different problem and overkill for the timeline. ZKPROV (arXiv 2506.20915) proves properties
about training data without revealing it. I don't need secrecy — I need tamper-evidence and
public verifiability, which signed Merkle proofs give me directly. Reaching for ZK here would
be complexity for its own sake."

**"Did you write this yourself?"**
"I designed the architecture and made the engineering decisions — the Merkle format, the
fail-closed behavior, quarantine-not-reindex, client-side verification, the Neon migration. I
used AI-assisted coding tools in the build workflow, like most engineers do now. I own the
design and the reasoning; I'm not going to claim I hand-typed every line, and I'm not going to
pretend I didn't use modern tooling either."

**"What's actually novel here vs. gluing libraries together?"**
"The Merkle tree and proof verification are hand-implemented, not imported — that's the
concrete answer. Beyond that, the novelty is integration decisions: fail-closed instead of
best-effort, quarantine instead of silent re-index, and verification that runs with zero trust
in the backend in both the browser and a CLI. Groq and pgvector are integrations I wired
correctly; the crypto envelope is the contribution."

**"Walk me through a bug you actually debugged."** (This is gold — use it.)
"Four real ones surfaced only when I ran the full pipeline against a live database, not from
reading the code:
1. The rate limiter (slowapi) silently requires the request parameter to be named exactly
   `request`; a couple of routes named it `req`, which crashed the app on import.
2. SQLAlchemy's async engine needs `greenlet`, which wasn't pinned — every DB call failed.
3. The embedding model returned torch tensors and pgvector only accepts lists/arrays, so the
   real ingest path had never actually worked (production ran a preview path that hid it).
4. The subtle one: the backend signed canonical JSON with `ensure_ascii=True` (escaping
   non-ASCII as `\uXXXX`), but the browser verifier uses `JSON.stringify`, which emits raw
   UTF-8. So any answer with an em-dash produced different signing bytes and failed
   client-side verification. I proved it with a Python-signs / Node-verifies cross-check, then
   set `ensure_ascii=False` on both Python sides and added a regression test.
The lesson I'd give: an audit that only reads code and trusts a checklist misses runtime and
cross-language bugs. You have to execute the thing."

---

## 5. The eval numbers, explained (and their limits)

| Metric | Value | What it really means |
|---|---|---|
| Tamper detection | 100% (8/8) | Every poisoned doc was quarantined |
| False positive | 0% (0/40) | 5 clean re-checks × 8 docs, zero wrongful quarantines |
| Verify latency p50 | 0.32 ms | Standalone verifier over 100 certs |
| Proof size mean | 0.398 KB | O(log n) inclusion proof, not the whole doc |
| Ingest throughput | 12.72 docs/sec | Full chunk→hash→Merkle→embed→sign→store |

**Say this unprompted — it shows maturity:** "100% detection and 0% false positives sounds
too good, so let me be honest about why it's not luck and not that impressive on its own.
Integrity here is exact SHA-256 comparison: a changed byte *always* produces a different hash,
and an unchanged byte *never* does. So these numbers reflect that the crypto is wired
correctly, not a clever ML model. A system that hit 100% detection but had a high
false-positive rate would be useless — it'd cry wolf and get ignored. The genuinely
interesting engineering is the fail-closed pipeline, the O(log n) proofs, and independent
verifiability. And the honest limitations are real: I can't catch pre-ingestion poisoning, a
compromised key breaks the model, and this is document-level exact-match, not semantic drift
detection."

---

## 6. SDE vs AI/ML interviewer angles

**SDE will probe:** system design, API boundaries, crypto hygiene, testing, deployment.
- Typed Pydantic models at every boundary; expected failures are return values
  (`VerifyResult`, `QueryResult`), not exceptions.
- Deterministic test suite (37 tests) with no LLM mocking — the crypto is pure functions, so
  tests are flake-free. Tests are named after the exact gap they close
  (`test_reordered_manifest_fails_signature`, `test_verifier_runs_with_backend_offline`,
  `test_canonical_json_keeps_non_ascii_raw_for_browser_verifier`).
- Zero-trust boundary enforced structurally (verifier imports nothing from `app`).
- Render cold-start / reseed-on-boot story; Docker-compose for local parity.

**AI/ML will probe:** the RAG pipeline, eval methodology, failure modes, responsible AI.
- top-k pgvector retrieval, MiniLM embeddings, deterministic chunking, Groq generation.
- Adversarial eval: poison a known subset, report caught/total *and* false positives on clean
  re-ingestion — the honest pair, not just detection rate.
- Fail-closed behavior maps directly to OWASP ASI06.

**Both will ask "what did you build vs. what's a library?"** → Hand-rolled Merkle + proof
verify (mine); Groq/pgvector/sentence-transformers (integrations wired correctly).

---

## 7. Facts to get exactly right (interviewers will look these up)

- It's **ASI06 — Memory & Context Poisoning**, one of the OWASP Agentic Top 10 (Dec 2025).
  **Do not** call it "#1" — the #1 is ASI01 (Goal Hijack). Saying "#1" is an instant, checkable
  credibility hit.
- ZKPROV = **arXiv 2506.20915**. Cite it as *adjacent* work, not something I implemented.
- Ed25519 public keys are 32 bytes; signatures are 64 bytes.
- The exact fail-closed string: `Source integrity check failed — answer withheld, document
  quarantined.`

---

## 8. Live demo script (also in `DEMO.md`)

1. **Ask tab** — ask a question; show the answer and its certificate (chunk hashes, Merkle
   proof, signature, timestamp).
2. **Edit a source file** on disk, change one sentence — "simulating post-ingestion poisoning."
3. **Ask the same question** — the system re-hashes, detects the mismatch, and returns the
   fail-closed message + quarantines the doc instead of answering off poisoned text.
4. **Verify tab / terminal** — verify the *original* certificate with zero backend access; it
   confirms the answer was grounded in the exact, unaltered text at that timestamp.

Record this as a video — live demos fail, and the tamper-and-catch moment is the whole pitch.

---

## 9. The 60-second recap before you walk in

Trust stack: SENTINEL in, ATTEST out. Hash every chunk (SHA-256) → Merkle tree → sign root
(Ed25519) → certificate per answer → fail closed on mismatch → verify anywhere with zero
backend trust. Hand-rolled Merkle proofs. 100%/0% on the adversarial set (and I know why that's
expected, not lucky). Honest limits: pre-ingestion poisoning, key compromise, no transparency
log yet. Breathe.
