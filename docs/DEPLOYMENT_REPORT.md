# Deployment & CI/CD Report

**Project:** E-Voting System  
**Date:** 2026-03-10  
**Repository:** https://github.com/niranjanagopinath/E-voting-system  

---

## 1. Deployment Platform — Vercel

### Configuration
The frontend React SPA is configured for deployment on **Vercel** via the root-level `vercel.json`.

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

### API Routing
Vercel rewrites `/api/*` and `/auth/*` paths to allow connecting a backend API (configurable via Vercel environment variables or Serverless Functions).

### Setup Instructions
1. Install the Vercel CLI: `npm install -g vercel`
2. Link the repository:
   ```bash
   cd E-voting-system
   vercel link
   ```
3. Set environment variables in the Vercel dashboard (or via CLI):
   - No environment variables are required for the frontend-only deploy
   - For backend API proxy, configure `REACT_APP_API_URL` if needed
4. Deploy:
   ```bash
   vercel --prod
   ```

### GitHub Integration
Alternatively, connect the repository directly in the Vercel dashboard:
1. Go to [vercel.com/new](https://vercel.com/new)
2. Import `niranjanagopinath/E-voting-system`
3. Vercel auto-detects `vercel.json` and builds accordingly
4. Every push to `all` or `main` triggers a production deploy

---

## 2. CI/CD Pipeline — GitHub Actions

### Workflow: CI (`.github/workflows/ci.yml`)
**Triggers:** Push to `all`/`main`, pull requests to `all`/`main`

| Job | Purpose | Runtime |
|-----|---------|---------|
| `backend-tests` | Python 3.11 tests against PostgreSQL 15 + Redis 7 | ~2-3 min |
| `frontend-build` | Node 18 build + lint | ~1-2 min |
| `integration` | Docker Compose smoke test (health + frontend checks) | ~3-5 min |

#### Backend Test Job
- Spins up PostgreSQL 15 and Redis 7 as service containers
- Installs Python dependencies from `backend/requirements.txt`
- Initializes the database schema from `database/init.sql`
- Runs all 103 tests via `pytest` with JUnit XML output
- Uploads test results as artifacts

#### Frontend Build Job
- Installs dependencies with `npm ci` (lockfile-based)
- Builds production bundle
- Uploads the `frontend/build/` directory as artifact

#### Integration Job
- Runs after backend-tests and frontend-build pass
- Builds all Docker images and starts services
- Verifies backend health endpoint (`/health`)
- Verifies frontend serves HTML
- Tears down cleanly with `docker compose down -v`

### Workflow: Deploy (`.github/workflows/deploy.yml`)
**Triggers:** Push to `all`/`main`, manual dispatch

| Step | Action |
|------|--------|
| Pull Vercel env | `vercel pull --yes --environment=production` |
| Build | `vercel build --prod` |
| Deploy | `vercel deploy --prebuilt --prod` |
| Verify | HTTP status check on deployed URL |

#### Required GitHub Secrets
| Secret | Description |
|--------|-------------|
| `VERCEL_TOKEN` | Vercel personal access token ([Settings → Tokens](https://vercel.com/account/tokens)) |
| `VERCEL_ORG_ID` | From `.vercel/project.json` after `vercel link` |
| `VERCEL_PROJECT_ID` | From `.vercel/project.json` after `vercel link` |

---

## 3. Pipeline Architecture

```
Push/PR to all or main
         │
         ├──► CI Workflow
         │       ├── backend-tests (Python 3.11 + PostgreSQL + Redis)
         │       ├── frontend-build (Node 18 + React build)
         │       └── integration (Docker Compose smoke test)
         │
         └──► Deploy Workflow
                 ├── vercel pull
                 ├── vercel build --prod
                 ├── vercel deploy --prebuilt --prod
                 └── HTTP verification
```

---

## 4. Local Development Verification

Before pushing, run locally:

```bash
# Backend tests
cd backend
python -m pytest tests/ -v

# Frontend build
cd frontend
npm ci
npm run build

# Full stack
docker-compose up -d --build
curl http://localhost:8000/health
```

---

## 5. Deployment Checklist

- [x] `vercel.json` configured with build command, output directory, and rewrites
- [x] Security headers added (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection)
- [x] CI workflow: backend tests, frontend build, Docker integration test
- [x] CD workflow: Vercel deploy with environment pull, build, deploy, verify
- [x] SPA routing: all client-side routes rewrite to `/index.html`
- [x] Artifacts: test results uploaded as GitHub Actions artifacts
- [ ] GitHub Secrets: `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` (must be set by repo owner)
- [ ] Vercel project linked via `vercel link` (one-time setup)

---

## 6. Notes

- **Frontend-only deploy:** Vercel deploys the React SPA. The backend (FastAPI, PostgreSQL, Redis, Ganache) runs separately via Docker Compose on your own infrastructure.
- **Backend hosting:** For full-stack production, deploy backend services on a cloud VM, container service, or PaaS, and update the frontend API base URL accordingly.
- **Branch strategy:** `all` is the integration branch; `main` is the stable release branch. Both trigger CI/CD.
- **Test count:** 103 tests across 9 test suites covering crypto, API, ledger, ops, and security.
