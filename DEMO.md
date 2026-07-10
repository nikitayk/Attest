# ATTEST Live Demo Script (90 seconds)

This script documents the exact steps to demonstrate ATTEST's tamper detection and zero-trust verification.

## Prerequisites

- Backend running with corpus ingested
- Frontend accessible (or use curl for API)
- Sample document in `backend/data/hr-policy.md`
- Public key at `backend/keys/public_key.pem`

## Demo Steps

### Step 1: Normal Query (Baseline)

**Action:** Ask a question about HR policy.

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the vacation policy?"}'
```

**Expected:** JSON response with `ok: true`, answer text, and certificate object.

**Say:** "The system answers normally and provides a cryptographic certificate proving the answer is grounded in the source documents."

---

### Step 2: Simulate Document Poisoning

**Action:** Edit a source file after ingestion.

```bash
# Open backend/data/hr-policy.md in editor
# Change one sentence, e.g.:
# FROM: "Employees receive 15 days of vacation per year."
# TO:   "Employees receive 0 days of vacation per year."
```

**Say:** "I'm now simulating an insider attack where someone tampers with a document after it was ingested into the system."

---

### Step 3: Query After Tampering

**Action:** Ask the same question again.

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the vacation policy?"}'
```

**Expected:** JSON response with `ok: false`, `error: "Source integrity check failed — answer withheld, document quarantined."`

**Say:** "The system detects the tampering immediately and refuses to answer. It quarantines the document to prevent any answers from being generated from poisoned content."

---

### Step 4: Zero-Trust Verification (Offline)

**Action:** Verify the original certificate using the standalone verifier CLI.

```bash
# Save the certificate from Step 1 to cert.json
python backend/verifier/verify.py \
  --certificate cert.json \
  --public-key backend/keys/public_key.pem
```

**Expected:** Exit code 0, output: `VALID — grounded in unaltered source at [timestamp]`

**Say:** "This verifier has zero access to my server. It only needs the certificate and my public key to cryptographically verify that the answer was grounded in unaltered source material at the time it was generated."

---

## Key Talking Points

- **Fail-closed behavior:** System refuses to answer rather than returning potentially incorrect information
- **Cryptographic proof:** Merkle tree + Ed25519 signature provides mathematical proof of integrity
- **Zero-trust verification:** Anyone can verify certificates without trusting the backend
- **OWASP ASI06:** Addresses Memory & Context Poisoning in agentic systems

## Troubleshooting

- If Step 3 doesn't show quarantine: Check that lazy integrity check is enabled in config
- If verifier fails: Ensure signature encoding is base64 (not hex) in certificate
- If no documents exist: Run ingestion first via `POST /ingest`

## Video Recording Instructions

### Setup

1. **Screen layout:** Use a split-screen or picture-in-picture setup
   - Left/Top: Terminal showing commands and responses
   - Right/Bottom: Browser showing the dashboard (if using UI)
   - Optional: Small camera window for narration

2. **Terminal preparation:**
   - Use a terminal with good contrast (dark background, light text)
   - Set font size to 14-16pt for readability
   - Clear terminal before starting

3. **Browser preparation:**
   - Open the ATTEST dashboard at `http://localhost:5173` (or deployed URL)
   - Open the backend at `http://localhost:8000/docs` for API reference (optional)
   - Have the document editor ready (VS Code or similar)

### Recording Tips

- **Pacing:** Speak clearly and at a moderate pace. Allow 2-3 seconds after each command for the viewer to see the output.
- **Highlighting:** Use terminal highlighting or mouse pointer to draw attention to key outputs (the certificate, the error message, the VALID result).
- **Transitions:** Smoothly switch between terminal, editor, and browser. Use consistent transitions.
- **Audio:** Use a good quality microphone. Record in a quiet environment.

### Post-Production

- Add captions for the spoken content
- Add text overlays for key terms (Merkle tree, Ed25519, zero-trust)
- Trim any dead time or mistakes
- Add a title card with project name and your name
- Add an end card with GitHub repo link and contact info

### Alternative: UI-Based Demo

If using the web dashboard instead of curl:

**Step 1 (Ask tab):**
- Navigate to Ask tab
- Type: "What is the vacation policy?"
- Click Submit
- Show answer and certificate JSON

**Step 2 (Editor):**
- Open `backend/data/hr-policy.md`
- Edit the vacation policy sentence
- Save

**Step 3 (Ask tab):**
- Submit same question
- Show error: "Source integrity check failed — answer withheld, document quarantined."

**Step 4 (Verify tab):**
- Paste the original certificate from Step 1
- Click Verify
- Show VALID result with hash match, Merkle proof valid, signature valid

This approach is more visual and easier to follow for non-technical audiences.

## Corpus questions (including the NIST PDF documents)

The corpus includes two public-domain NIST PDF excerpts alongside the policy markdown, which
exercise the `pypdf` ingestion path. Sample questions for the Ask tab / QA demo:

Policy corpus (markdown):
- "What is the vacation policy?"
- "How long are financial records retained?"
- "What are the steps in the incident response runbook?"

NIST PDF corpus:
- "What are the core functions of the NIST AI Risk Management Framework?"
- "How does the NIST Generative AI Profile describe data poisoning risk?"
- "What does the framework say about information integrity for GenAI systems?"

Out-of-scope (should abstain / 'I don't know'):
- "What is the company's stock price today?"

> Note: running these as an automated QA-accuracy eval requires a Groq API key (the LLM step).
> The crypto/integrity metrics in `eval/run_eval.py` need no LLM and run against all 10 docs.
