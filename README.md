# ATTEST — Cryptographic Chain of Custody for RAG Answers

> ATTEST provides cryptographic proof that RAG answers are grounded in real, unaltered, timestamped source material. It detects tampering, quarantines compromised documents, and issues verifiable certificates for every answer.

**Status:** Production-ready with Neon Postgres + pgvector persistence. See `PROJECT_PLAN.md` and `PROGRESS.md`.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Neon Postgres account (free tier available)
- Groq API key

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python generate_keys.py  # Generate Ed25519 keypair
```

Create `.env` file:
```bash
ATTEST_DATABASE_URL=postgresql://user:pass@ep-xyz.aws.neon.tech/neondb
ATTEST_GROQ_API_KEY=your-groq-api-key
ATTEST_GROQ_MODEL=llama-3.3-70b-versatile
ATTEST_ALLOWED_ORIGINS=http://localhost:5173
ATTEST_DATA_DIR=data
ATTEST_CHUNK_SIZE=500
ATTEST_CHUNK_OVERLAP=50
ATTEST_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ATTEST_TOP_K=3
ATTEST_QUARANTINE_ON_MISMATCH=true
```

Set up Neon database (see `NEON_SETUP.md` for detailed instructions):
```sql
CREATE EXTENSION vector;
CREATE TABLE documents (...);
CREATE TABLE chunks (...);
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE TABLE manifests (...);
CREATE TABLE certificates (...);
```

Start the server:
```bash
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to access the application.

## Architecture

ATTEST provides cryptographic proof that RAG answers are grounded in unaltered source material:

1. **Ingestion**: Documents are chunked, hashed (SHA-256), organized into a Merkle tree, and signed with Ed25519
2. **Query**: Retrieved chunks are re-hashed against the manifest before answer generation
3. **Certificate**: Answers include a self-contained certificate with Merkle proofs and signature
4. **Verification**: Standalone CLI verifies certificates without trusting the backend

```mermaid
graph TD
    A[Documents] --> B[Ingest]
    B --> C[Chunk 500 chars]
    C --> D[SHA-256 Hash]
    D --> E[Merkle Tree]
    E --> F[Ed25519 Sign Manifest]
    F --> G[Neon Postgres]
    G --> H[pgvector Embeddings]
    G --> I[Manifest Table]
    
    J[Query] --> K[Retrieve top-k pgvector]
    K --> L[Re-hash chunks]
    L --> M{Match?}
    M -->|Yes| N[Groq Generate]
    M -->|No| O[Quarantine]
    N --> P[Sign Certificate]
    P --> Q[Return Answer + Cert]
    
    R[Verify CLI] --> S[Load Certificate]
    S --> T[Verify Signature]
    T --> U[Verify Merkle Proofs]
    U --> V[VALID/INVALID]
    
    style M fill:#f9f,stroke:#333,stroke-width:4px
    style O fill:#f99,stroke:#333,stroke-width:2px
    style V fill:#9f9,stroke:#333,stroke-width:2px
    style G fill:#e0f7fa,stroke:#333,stroke-width:2px
```

## Integrity Monitor

The system includes three modes of integrity checking:

- **Lazy**: Every query re-hashes retrieved chunks against the manifest
- **Cron**: External cron job triggers full corpus health checks every 15 minutes
- **Manual**: Dashboard "Check Now" button triggers immediate health check

### Cron Configuration

To set up automated monitoring:

1. Go to [cron-job.org](https://cron-job.org)
2. Create a new cron job with:
   - **URL**: `https://your-app.onrender.com/monitor/trigger`
   - **Method**: POST
   - **Interval**: 15 minutes
   - **Headers**: None required

This keeps the Render instance warm and ensures regular integrity checks.

## Demo

See `DEMO.md` for the 90-second live demo script showing tamper detection and zero-trust verification.

## Zero-Trust Verification

Verify any certificate without trusting the backend:

```bash
python backend/verifier/verify.py \
  --certificate path/to/cert.json \
  --public-key backend/keys/public_key.pem
```

## Limitations

- No protection against pre-ingestion poisoning
- Compromised signing key breaks trust model
- No external transparency log in MVP (Rekor is Stretch)
- First boot requires full corpus ingestion (subsequent boots load from Neon)

## 📚 API Endpoints

### Query
- `POST /query` - Query the RAG system and get answer with certificate
- `GET /certificate/{certificate_id}` - Retrieve a stored certificate

### Document Management
- `POST /documents` - Upload a new document
- `GET /documents` - List all documents with quarantine status
- `DELETE /documents/{doc_id}` - Delete a document

### Monitoring
- `POST /monitor/trigger` - Trigger full corpus integrity check
- `GET /monitor/status` - Get last monitor run status
- `GET /corpus/health` - Get health status of all documents

### Demo
- `POST /demo/simulate-tampering` - Simulate document tampering for demo

### Other
- `POST /ingest` - Manually trigger corpus ingestion
- `GET /public-key` - Get the Ed25519 public key for verification

## Tech Stack

- **Backend**: FastAPI, Neon Postgres, pgvector, SQLAlchemy, sentence-transformers, Groq
- **Crypto**: SHA-256, Ed25519 (cryptography library)
- **Frontend**: React + Vite + Tailwind
- **Database**: Neon Postgres with pgvector extension for vector similarity search
- **Deployment**: Render (backend), Vercel (frontend)

## 🌐 Deployment

### Backend (Render)

1. **Create Neon Database**
   - Sign up at [neon.tech](https://neon.tech)
   - Create a free project
   - Run the schema from `NEON_SETUP.md`

2. **Deploy to Render**
   - Push code to GitHub
   - Create new Web Service on Render
   - Connect repository and select `attest/backend` as root directory
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Environment variables:
     - `ATTEST_DATABASE_URL`: Your Neon connection string
     - `ATTEST_GROQ_API_KEY`: Your Groq API key
     - `ATTEST_GROQ_MODEL`: `llama-3.3-70b-versatile`
     - `ATTEST_ALLOWED_ORIGINS`: Your Vercel app URL

3. **Generate Keys**
   ```bash
   cd backend
   python generate_keys.py
   ```
   - Commit `backend/keys/public_key.pem` to repository
   - Copy `backend/keys/private.pem` content and set as `ATTEST_SIGNING_KEY_PEM` in Render env (or let system read from file)

### Frontend (Vercel)

1. Push code to GitHub
2. Import project on Vercel
3. Root directory: `attest/frontend`
4. Build command: `npm run build`
5. Output directory: `dist`
6. Environment variable: `VITE_API_URL` (your Render backend URL)

## 🎯 Features

- **Cryptographic Chain of Custody**: Every answer includes a verifiable certificate with Merkle proofs
- **Tamper Detection**: Automatic detection of document tampering via hash verification
- **Quarantine System**: Compromised documents are automatically quarantined
- **Zero-Trust Verification**: Standalone CLI verifies certificates without trusting the backend
- **Integrity Monitor**: Lazy, cron-based, and manual integrity checking modes
- **Persistent Storage**: Neon Postgres with pgvector for reliable vector storage
- **Document Management**: Upload, delete, and list documents via API
- **Demo Tampering**: `/demo/simulate-tampering` endpoint for demonstrating tamper detection

## Evaluation

Run the evaluation harness to measure system performance:

```bash
cd attest
python eval/run_eval.py
```

This outputs metrics for:
- Tamper detection rate
- False positive rate
- Verification latency (p50)
- Proof size (mean)
- Ingestion throughput

## Related Work

- **ZKPROV** (arXiv 2506.20915): Training-data provenance via ZK. ATTEST = post-ingestion tamper detection in live RAG. Chose signed-hash over ZK for 4-week scope.
- **OWASP ASI06**: Memory & Context Poisoning — the threat category ATTEST addresses.
- **Sigstore/Rekor**: Conceptual model (transparency log). MVP = local Ed25519 only; Rekor = Stretch.

## Resume Bullets

- Architected cryptographic chain-of-custody for agentic RAG (SHA-256 Merkle tree, Ed25519 signed manifests and answer certificates)
- Built integrity monitor with lazy, cron-based, and manual integrity checking modes
- Zero-trust standalone verifier — Merkle proofs + signature check, addresses OWASP ASI06
- Implemented fail-closed RAG pipeline that quarantines tampered documents instead of returning poisoned answers
- Migrated persistence from local SQLite + ChromaDB to Neon Postgres + pgvector for production-ready vector storage
- Deployed full-stack system with React frontend, FastAPI backend, pgvector vector store, and Groq LLM integration

## 📖 Documentation

- `PROJECT_PLAN.md` - Full project architecture and implementation plan
- `PROGRESS.md` - Build progress and completion status
- `NEON_SETUP.md` - Detailed Neon Postgres setup instructions
- `DEMO.md` - Demo script for tamper detection demonstration
- `DEPLOYMENT.md` - Deployment guide for Render and Vercel

## 🔧 Troubleshooting

### Backend won't start
- Ensure Neon database is set up with pgvector extension
- Check `ATTEST_DATABASE_URL` is correct in `.env`
- Verify Groq API key is valid

### Embedding errors
- First run downloads sentence-transformers model (~100MB)
- Ensure internet connection for initial model download

### Database connection errors
- Verify Neon connection string format
- Check that pgvector extension is enabled
- Ensure SSL is handled correctly (asyncpg handles SSL automatically)

## 🤝 Contributing

This is a demonstration project for cryptographic chain of custody in RAG systems. Feel free to fork and experiment!
