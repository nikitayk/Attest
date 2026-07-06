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
cd attest/backend

python -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

k = Ed25519PrivateKey.generate()
private_pem = k.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption()
)
public_pem = k.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo
)

with open('private.pem', 'wb') as f:
    f.write(private_pem)
with open('keys/public_key.pem', 'wb') as f:
    f.write(public_pem)

print('Keys generated successfully')
print('Private key saved to: private.pem (DO NOT COMMIT)')
print('Public key saved to: keys/public_key.pem (COMMIT THIS)')
"
```

**Important:**
- Commit `backend/keys/public_key.pem` to Git
- Keep `private.pem` secure locally - you'll paste it into Render
- Never commit the private key to the repository

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
- `ATTEST_SIGNING_KEY_PEM`: Paste the entire content of your `private.pem` file (including the `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----` lines)
- `ATTEST_GROQ_API_KEY`: Your Groq API key from https://console.groq.com/
- `ATTEST_GROQ_MODEL`: `llama-3.3-70b-versatile` (or current free model)
- `ATTEST_ALLOWED_ORIGINS`: Your Vercel origin, for example `https://attest-frontend.vercel.app`
- `ATTEST_AUTO_INGEST_ON_STARTUP`: `false` on Render free tier to avoid cold-start memory spikes
- `ATTEST_CHROMA_PATH`: `/tmp/chroma`
- `ATTEST_MANIFEST_DB_PATH`: `/tmp/attest.db`

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

Expected response:
```json
{
  "status": "ok",
  "manifest_loaded": false
}
```

With `ATTEST_AUTO_INGEST_ON_STARTUP=false`, `manifest_loaded` stays `false` until you seed the corpus.

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

**Issue**: ChromaDB build error on Windows
- This is expected locally; Render uses Linux so it will work fine
- If deploying locally on Windows, install MSVC build tools

### Frontend can't connect to backend

**Issue**: CORS errors
- Check that `ATTEST_ALLOWED_ORIGINS` exactly matches your Vercel URL
- Check that `VITE_API_URL` is set correctly in Vercel
- Verify the backend URL is accessible

**Issue**: Network timeout
- Render free tier spins down after 15 min inactivity
- First request after spin-down is faster when startup ingest is disabled
- Set up cron-job.org to keep it warm

### Render runs out of memory

**Issue**: Service OOMs during startup or first ingest
- Set `ATTEST_AUTO_INGEST_ON_STARTUP=false` so Render boots before embeddings are computed
- Keep `ATTEST_CHROMA_PATH=/tmp/chroma` so Chroma uses disk-backed storage instead of in-memory state
- Trigger `/ingest` manually after deploy, or upload documents incrementally from the frontend
- If manual ingest still OOMs, move to Render Starter; 512MB is tight for Python + Chroma + sentence-transformers

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
