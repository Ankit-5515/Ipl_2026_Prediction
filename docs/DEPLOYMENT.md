# Step-by-Step Production Deployment Guide

This guide walks through deploying the **IPL 2026 Match Prediction Platform** to a live production URL using **Neon/Supabase (PostgreSQL)**, **Render/Railway (FastAPI Backend)**, and **Vercel (Next.js Frontend)**, or via **Docker Compose**.

---

## Option A: Local Development & Verification

### 1. Train & Verify the ML Pipeline
```powershell
# From the repository root (c:\Users\shiva\OneDrive\Desktop\IPL 2026)
pip install -r backend/requirements.txt
python -m ml.train
```
**Verify**: Check that `ml/artifacts/ipl_model_v1.joblib`, `ml/artifacts/metrics.json`, and `ml/artifacts/MODEL_CARD.md` are generated.

### 2. Run the Automated Pytest Suite
```powershell
python -m pytest -v
```
**Verify**: All 11 unit and API integration tests pass (`11 passed`).

### 3. Start the FastAPI Backend
```powershell
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
**Verify**:
- Open Swagger UI: `http://localhost:8000/docs`
- Check Health Endpoint: `http://localhost:8000/api/health`

### 4. Start the Next.js Frontend
```powershell
# Open a second terminal inside frontend/
cd frontend
npm install
npm run dev
```
**Verify**: Open `http://localhost:3000` in your browser.

---

## Option B: One-Command Docker Compose (Full Stack + PostgreSQL 16)

```powershell
docker compose up --build -d
```
- **Frontend**: `http://localhost:3000`
- **FastAPI Backend & Swagger Docs**: `http://localhost:8000/docs`
- **PostgreSQL 16**: `localhost:5432`

To stop:
```powershell
docker compose down
```

---

## Option C: Cloud Deployment (Neon DB + Render Backend + Vercel Frontend)

### Step 1 — Provision Managed PostgreSQL on Neon (or Supabase)
1. Sign in to [Neon.tech](https://neon.tech) (or [Supabase](https://supabase.com)) and create a new project named `ipl-2026-predictions`.
2. Copy the PostgreSQL connection string:
   ```text
   postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   *(Note: SQLAlchemy automatically creates the `prediction_records` table on startup via `init_db()`.)*

### Step 2 — Deploy FastAPI + ML Backend on Render (or Railway / Fly.io)

#### Using Render:
1. Push this repository to GitHub:
   ```powershell
   git add .
   git commit -m "feat: upgrade IPL 2026 prediction project to production full-stack app"
   git push origin main
   ```
2. In [Render Dashboard](https://dashboard.render.com), click **New +** $\rightarrow$ **Web Service** and connect your GitHub repository `Ankit-5515/Ipl_2026_Prediction`.
3. Configure the service:
   - **Runtime**: `Docker`
   - **Dockerfile Path**: `backend/Dockerfile`
   - **Docker Build Context Directory**: `.`
   - **Health Check Path**: `/api/health`
4. Add the following **Environment Variables** in Render:
   ```env
   ENVIRONMENT=production
   DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
   CORS_ORIGINS=https://your-vercel-domain.vercel.app,http://localhost:3000
   RATE_LIMIT_PREDICT=60/minute
   CACHE_TTL_SECONDS=300
   ```
5. Click **Create Web Service**. Once live, copy your backend URL (e.g., `https://ipl-2026-api.onrender.com`).

#### Alternative: Using Railway CLI
```powershell
npm i -g @railway/cli
railway login
railway init
railway up
```

### Step 3 — Deploy Next.js Frontend on Vercel

#### Via Vercel Dashboard:
1. Go to [vercel.com/new](https://vercel.com/new) and import `Ankit-5515/Ipl_2026_Prediction`.
2. Set **Root Directory** to `frontend`.
3. Add the **Environment Variable**:
   - `NEXT_PUBLIC_API_URL` = `https://ipl-2026-api.onrender.com` (your Render/Railway backend URL)
4. Click **Deploy**.

#### Via Vercel CLI:
```powershell
cd frontend
npx vercel --prod --env NEXT_PUBLIC_API_URL=https://ipl-2026-api.onrender.com
```

### Step 4 — Enable Free-Tier Cold-Start Keep-Alive
1. In your GitHub repository, navigate to **Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions $\rightarrow$ Variables**.
2. Add a Repository Variable:
   - `PRODUCTION_API_URL` = `https://ipl-2026-api.onrender.com`
3. The `.github/workflows/ci-cd.yml` workflow will automatically ping `GET /api/health` every 14 minutes so your free-tier backend stays warm!
