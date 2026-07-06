# Neon Postgres + pgvector Setup Guide

## Step 1: Create Neon Database

1. Go to [https://neon.tech](https://neon.tech) and sign up for a free account
2. Create a new project:
   - Click "Create a project"
   - Choose a name (e.g., "attest-db")
   - Select the free tier
   - Choose a region close to you
3. Once created, you'll get a connection string like:
   ```
   postgresql://username:password@ep-xyz.aws.neon.tech/neondb?sslmode=require
   ```

## Step 2: Run Schema Creation

You can run the SQL commands either through the Neon SQL Editor or via psql.

### Option A: Neon SQL Editor (Recommended)
1. Go to your Neon project dashboard
2. Click "SQL Editor" in the sidebar
3. Run these commands one by one:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OK',
    doc_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create chunks table with pgvector
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(384),
    UNIQUE(doc_id, chunk_index)
);

-- Create HNSW index for fast similarity search
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);

-- Create manifests table
CREATE TABLE IF NOT EXISTS manifests (
    manifest_id TEXT PRIMARY KEY,
    merkle_root TEXT NOT NULL,
    chunk_hashes JSONB NOT NULL,
    signature TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create certificates table
CREATE TABLE IF NOT EXISTS certificates (
    certificate_id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    cert_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Option B: Via psql
```bash
psql "postgresql://username:password@ep-xyz.aws.neon.tech/neondb?sslmode=require" -f schema.sql
```

## Step 3: Set Environment Variable

### Windows (PowerShell)
```powershell
$env:ATTEST_DATABASE_URL = "postgresql://username:password@ep-xyz.aws.neon.tech/neondb?sslmode=require"
```

### Windows (Command Prompt)
```cmd
set ATTEST_DATABASE_URL=postgresql://username:password@ep-xyz.aws.neon.tech/neondb?sslmode=require
```

### Linux/Mac
```bash
export ATTEST_DATABASE_URL="postgresql://username:password@ep-xyz.aws.neon.tech/neondb?sslmode=require"
```

### For persistence, add to `.env` file in backend directory:
```
ATTEST_DATABASE_URL=postgresql://username:password@ep-xyz.aws.neon.tech/neondb?sslmode=require
```

## Step 4: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install:
- asyncpg (Postgres async driver)
- pgvector (pgvector support)
- sentence-transformers (local embeddings)
- sqlalchemy (ORM)
- Other existing dependencies

## Step 5: Test the Migration

### Run the backend server:
```bash
cd backend
python -m uvicorn app.main:app --reload
```

### Verify startup:
- The server should connect to Neon
- On first boot, it should ingest the corpus from `backend/data/`
- Subsequent boots should load the existing manifest from Neon

### Test endpoints:
1. **Query**: `POST http://localhost:8000/query` with `{"query": "your question"}`
2. **Monitor**: `GET http://localhost:8000/monitor/status`
3. **Corpus Health**: `GET http://localhost:8000/corpus/health`
4. **Simulate Tampering**: `POST http://localhost:8000/demo/simulate-tampering`

## Troubleshooting

### Connection errors:
- Verify your Neon connection string is correct
- Check that the database is active in Neon dashboard
- Ensure SSL mode is enabled (required by Neon)

### Extension errors:
- Make sure pgvector extension is enabled: `CREATE EXTENSION vector;`
- Some Neon tiers may require enabling extensions in settings

### Embedding errors:
- First run of sentence-transformers will download the model (~100MB)
- Ensure you have internet connection for the first run
- The model will be cached locally after first download

### Vector index errors:
- Ensure the HNSW index was created: `CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);`
- Check that the embedding dimension matches (384 for MiniLM-L6-v2)

## Verification Checklist

- [ ] Neon database created
- [ ] pgvector extension enabled
- [ ] All tables created (documents, chunks, manifests, certificates)
- [ ] HNSW index created on chunks
- [ ] ATTEST_DATABASE_URL environment variable set
- [ ] Dependencies installed
- [ ] Backend server starts without errors
- [ ] First boot ingests corpus successfully
- [ ] Subsequent boots load existing manifest
- [ ] Query endpoint returns answers with certificates
- [ ] Tampering simulation works
