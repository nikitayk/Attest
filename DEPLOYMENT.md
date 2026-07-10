# ATTEST Deployment Guide

This guide walks through deploying ATTEST to production using Render (backend) and Vercel (frontend).

## Prerequisites

- GitHub account with ATTEST repository pushed
- Render account (free tier)
- Vercel account (free tier)
- Groq API key (free tier available at https://console.groq.com/)
- Local backend env copied from `backend/.env.example`
- Local frontend env copied from `frontend/.env.example`
- Python 3.11 or 3.12 recommended for full local backend installs

## Step 1: Generate Ed25519 Keys

Generate a new keypair locally. You'll do this once per deployment.

```bash
cd backend
python generate_keys.py
```

This writes `keys/public_key.pem` (commit this) and `keys/private.pem` (gitignored).

**Important:**
- Commit `backend/keys/public_key.pem` to Git — the browser/CLI verifiers fetch it.
- Set `keys/private.pem`'s full contents as `ATTEST_SIGNING_KEY_PEM` in Render (Step 2).
- The committed public key and the Render private key **must be the same pair**, or every
  certificate will fail verification. (The audit found the live deploy serving a *placeholder*
  public key with no matching private key — this step fixes that.)
- Never commit the private key.

## Step 1.5: Create Local Env Files

Before deploying, create local env files from the checked-in examples:

```bash
cd attest
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env
```

Then update:

- `backend/.env`: set `ATTEST_SIGNING_KEY_PEM`, `ATTEST_GROQ_API_KEY`, and `ATTEST_ALLOWED_ORIGINS`
- `frontend/.env`: set `VITE_API_URL=http://localhost:8000` for local dev

## Step 2: Deploy Backend to Render

### 2.1 Push Code to GitHub

Ensure your code is pushed to GitHub:
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

### 2.2 Create Render Web Service

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:

**Build & Deploy Settings:**
- **Root Directory**: `backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Environment Variables:**
- `ATTEST_DATABASE_URL`: Your Neon Postgres connection string (`postgresql://...`). **Required** — the app will not boot without it.
- `ATTEST_SIGNING_KEY_PEM`: Paste the entire content of your `keys/private.pem` file (including the `-----BEGIN PRIVATE KEY-----` / `-----END PRIVATE KEY-----` lines)
- `ATTEST_GROQ_API_KEY`: Your Groq API key from https://console.groq.com/
- `ATTEST_GROQ_MODEL`: `llama-3.3-70b-versatile` (or current free model)
- `ATTEST_ALLOWED_ORIGINS`: Your Vercel origin, for example `https://attest-eight.vercel.app`
- `ATTEST_AUTO_INGEST_ON_STARTUP`: `false` on the free tier (see "Memory & the free tier" below)
- `ATTEST_HOSTED_PREVIEW_MODE`: `true` on the free tier (lexical preview embeddings, no torch)

> `render.yaml` already declares these (secrets as `sync: false`); set the secret values in
> the dashboard. `ATTEST_CHROMA_PATH` / `ATTEST_MANIFEST_DB_PATH` are **obsolete** after the
> Neon migration — do not set them.

**Instance Settings:**
- **Instance Type**: Free
- **Region**: Choose closest to your users

### 2.3 Wait for Deployment

Render will:
1. Build the environment
2. Install dependencies
3. Start the FastAPI server
4. Skip corpus ingestion on boot when `ATTEST_AUTO_INGEST_ON_STARTUP=false`

### 2.4 Verify Backend

Once deployed, test the health endpoint:
```bash
curl https://your-app-name.onrender.com/health
```

Expected response (fields include `mode` and `capabilities`):
```json
{
  "status": "healthy",
  "manifest_loaded": false,
  "mode": "hosted-preview",
  "database": "connected",
  "document_count": 0
}
```

If `status` is `unhealthy`, the `error` field usually means `ATTEST_DATABASE_URL` is wrong or
Neon is unreachable. With `ATTEST_AUTO_INGEST_ON_STARTUP=false`, `manifest_loaded` stays
`false` until you seed the corpus.

Then trigger the initial corpus build after the service is healthy:
```bash
curl -X POST https://your-app-name.onrender.com/ingest \
  -H "Content-Type: application/json" \
  -d "{}"
```

You can also open the frontend and use the `Ingest Seed Data` button in the `Corpus Health` tab.

**Note the backend URL** - you'll need it for frontend deployment (e.g., `https://attest-backend-xyz.onrender.com`)

## Step 3: Deploy Frontend to Vercel

### 3.1 Import Project on Vercel

1. Go to [vercel.com](https://vercel.com)
2. Click **"Add New..."** → **"Project"**
3. Import your GitHub repository
4. Configure the project:

**Project Settings:**
- **Framework Preset**: Vite
- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`

**Environment Variables:**
- `VITE_API_URL`: Your Render backend URL (e.g., `https://attest-backend-xyz.onrender.com`)

### 3.2 Deploy

Click **"Deploy"**. Vercel will:
1. Install dependencies
2. Build the React app
3. Deploy to their CDN

### 3.3 Verify Frontend

Once deployed, visit your Vercel URL. You should see:
- ATTEST header
- Three tabs: Ask, Verify, Corpus Health
- Working query functionality

## Step 4: Configure Cron Monitoring (Optional but Recommended)

To keep the Render instance warm and run regular integrity checks:

1. Go to [cron-job.org](https://cron-job.org)
2. Create a new cron job:
   - **Title**: ATTEST Integrity Monitor
   - **URL**: `https://your-app-name.onrender.com/monitor/trigger`
   - **Method**: POST
   - **Interval**: 15 minutes
   - **Save**

This ensures:
- Render doesn't spin down from inactivity
- Regular integrity checks run automatically
- Tamper detection happens on a schedule

## Step 5: Test End-to-End

### 5.1 Test Query

1. Go to your Vercel frontend URL
2. Navigate to the **Ask** tab
3. Enter a query about your documents (e.g., "What is the data retention policy?")
4. Submit and verify you get an answer with a certificate

### 5.2 Test Tamper Detection

1. SSH into your Render instance (or use the Render shell)
2. Navigate to `/tmp/attest/data/` (or wherever your data is stored)
3. Edit a document file
4. Run the same query again
5. Verify you get the error: "Source integrity check failed — answer withheld, document quarantined"

### 5.3 Test Verification

1. Copy a certificate JSON from the Ask tab
2. Run the standalone verifier locally:
```bash
cd attest/backend
python -m verifier.verify \
  --certificate <path-to-cert.json> \
  --public-key keys/public_key.pem
```
3. Verify it returns: "VALID — grounded in unaltered source at [timestamp]"

## Troubleshooting

### Backend fails to start

**Issue**: Missing environment variables
- Check Render logs for "ATTEST_SIGNING_KEY_PEM is required" or similar
- Ensure all env vars are set in Render dashboard

**Issue**: `greenlet` / async DB errors
- SQLAlchemy's async engine requires `greenlet` (now pinned in `requirements.txt`). If you see
  "the greenlet library is required", reinstall dependencies.

### Frontend can't connect to backend

**Issue**: CORS errors
- Check that `ATTEST_ALLOWED_ORIGINS` exactly matches your Vercel URL
- Check that `VITE_API_URL` is set correctly in Vercel
- Verify the backend URL is accessible

**Issue**: Network timeout
- Render free tier spins down after 15 min inactivity
- First request after spin-down is faster when startup ingest is disabled
- Set up cron-job.org to keep it warm

### Memory & the free tier (measured — read this honestly)

Ingestion memory was instrumented with `ATTEST_INGEST_LOG_MEMORY=true`. Measured RSS on a full
8-doc ingest with batched embedding (`ATTEST_INGEST_BATCH_SIZE=16`, `gc.collect()` per batch,
model loaded once):

| Point | RSS |
|---|---|
| Start (embedding model loaded) | ~437 MB |
| After first embed batch | ~534 MB |
| Peak / complete | ~540 MB |

The batched-embedding fix keeps *incremental* growth tiny (~3 MB per subsequent batch), so the
earlier boot-time-vs-ingest-time OOM was a real fix — but the **torch + sentence-transformers
baseline alone (~437 MB) already crowds Render's 512 MB free tier**, and the embedding peak
(~540 MB) exceeds it. Honest conclusion: **you cannot run full semantic embeddings on the
free tier.** Two options:

1. **Free tier (current):** run `ATTEST_HOSTED_PREVIEW_MODE=true`. This uses lightweight
   lexical preview embeddings (no torch), so the box fits in 512 MB. The entire crypto story —
   hashing, Merkle proofs, signing, fail-closed quarantine, client-side/CLI verification — is
   fully real; only retrieval quality is lexical rather than semantic. This is the honest
   free-tier demo.
2. **Semantic retrieval:** upgrade to Render Starter (or any ≥1 GB instance), set
   `ATTEST_HOSTED_PREVIEW_MODE=false` and `ATTEST_ALLOW_MUTATING_OPERATIONS=true`, then trigger
   `/ingest` once against Neon.

Either way, keep `ATTEST_AUTO_INGEST_ON_STARTUP=false` so the service becomes healthy before
any heavy work runs.

### Ingestion fails on cold start

**Issue**: No documents found
- Ensure `backend/data/` has markdown files
- Check Render logs for "No .md or .txt files found"

**Issue**: Groq API error
- Verify `ATTEST_GROQ_API_KEY` is valid
- Check Groq console for API key status

## Cost Summary

**Free Tier Usage:**
- Render: Free (750 hours/month, 512MB RAM)
- Vercel: Free (unlimited bandwidth for personal projects)
- Groq: Free tier available
- Total: $0/month

**Upgrade Path (if needed):**
- Render Starter: $7/month (better performance)
- Groq paid: $0.59/1M tokens (if exceeding free limits)

## Post-Deployment Checklist

- [ ] Backend health endpoint returns `{"status": "ok", "manifest_loaded": true}`
- [ ] Frontend loads and shows three tabs
- [ ] Query returns answer with certificate
- [ ] Certificate verification works with standalone CLI
- [ ] Tamper detection triggers quarantine
- [ ] Cron job configured (optional)
- [ ] Monitor status endpoint shows recent checks
- [ ] Document upload works in Corpus Health tab

## Security Notes

1. **Never commit private keys** - The `private.pem` file should never be in Git
2. **Rotate keys periodically** - Generate new keys and update Render env var
3. **Monitor API usage** - Check Groq console for token usage
4. **Update dependencies** - Run `pip install -r requirements.txt --upgrade` periodically

## Support

If you encounter issues:
1. Check Render logs (Build & Deploy tabs)
2. Check Vercel deployment logs
3. Review this guide's troubleshooting section
4. Open an issue on GitHub with error details
