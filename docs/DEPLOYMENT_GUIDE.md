# Deployment Guide

Full deployment reference for the E-Voting System.  
**Frontend** is hosted on Vercel. **Backend** is hosted on Render.

---

## Architecture Overview

```
Push/PR to all or main
         │
         ├──► CI Workflow (.github/workflows/ci.yml)
         │       ├── backend-tests  (Python 3.11 + PostgreSQL + Redis)
         │       ├── frontend-build (Node 18 + React build)
         │       └── integration    (Docker Compose smoke test)
         │
         └──► Deploy Workflow (.github/workflows/deploy.yml)
                 ├── vercel pull
                 ├── vercel build --prod
                 ├── vercel deploy --prebuilt --prod
                 └── HTTP verification
```

---

## 1. Frontend — Vercel

### Configuration

| Setting | Value |
|---------|-------|
| Framework | Create React App |
| Build command | `cd frontend && npm install && npm run build` |
| Output directory | `frontend/build` |
| Node.js version | 18 |
| SPA routing | All paths rewrite to `/index.html` |

### Security Headers

Every response includes:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

### API Proxy

`vercel.json` rewrites `/api/*`, `/auth/*`, `/health`, `/docs`, and `/openapi.json` to the Render backend, so the frontend calls its own domain and Vercel proxies to the API.

### Setup Steps

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Link the project**
   ```bash
   cd E-voting-system
   vercel link
   ```
   Choose **Create a new project** when prompted. This creates `.vercel/project.json` (already in `.gitignore`).

3. **Get your IDs** from `.vercel/project.json`:
   ```json
   { "projectId": "prj_xxx", "orgId": "team_xxx" }
   ```

4. **Create a Vercel token** at [vercel.com/account/tokens](https://vercel.com/account/tokens).

5. **Add GitHub Secrets** (Settings → Secrets → Actions):

   | Secret | Value |
   |--------|-------|
   | `VERCEL_TOKEN` | Personal access token from step 4 |
   | `VERCEL_ORG_ID` | `orgId` from `.vercel/project.json` |
   | `VERCEL_PROJECT_ID` | `projectId` from `.vercel/project.json` |

6. **Push to deploy** — every push to `all` or `main` triggers the deploy workflow automatically.

7. **Manual deploy** (optional):
   ```bash
   vercel --prod
   ```

---

## 2. Backend — Render

### Configuration

The backend is defined in `render.yaml` (Render Blueprint):

| Setting | Value |
|---------|-------|
| Runtime | Python 3.11 |
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/health` |
| Plan | Free |

### Database

A free-tier PostgreSQL instance is provisioned automatically by `render.yaml` and connected via the `DATABASE_URL` environment variable.

### Environment Variables

| Variable | Source |
|----------|--------|
| `DATABASE_URL` | Auto-set from Render PostgreSQL |
| `FRONTEND_URL` | Set to the Vercel production URL |
| `SECRET_KEY` | Generate a strong random value |

### Deployment

Render auto-deploys on every push to the connected branch. To set up:

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click **New → Blueprint**
3. Connect the GitHub repo and select `render.yaml`
4. Render provisions the web service and database automatically

---

## 3. Live URLs

| Component | URL |
|-----------|-----|
| Frontend | `https://e-voting-system-cyan.vercel.app` |
| Backend | `https://e-voting-backend-q8x9.onrender.com` |
| Health check | `https://e-voting-backend-q8x9.onrender.com/health` |
| API docs | `https://e-voting-backend-q8x9.onrender.com/docs` |

---

## 4. Local Development

```bash
# Start all services locally
docker-compose up -d

# Backend tests
cd backend
PYTHONPATH=. python -m pytest tests/ -v

# Frontend dev server
cd frontend
npm start
```
