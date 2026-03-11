# DevOps Guide — E-Voting System

Complete DevOps reference covering infrastructure, containerization, CI/CD, deployment, monitoring, and operational procedures.

> For CI/CD workflow specifics, see [CI_CD_PIPELINE.md](CI_CD_PIPELINE.md).  
> For step-by-step deployment instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Technology Stack](#2-technology-stack)
3. [Repository Structure](#3-repository-structure)
4. [Containerization](#4-containerization)
5. [Docker Compose — Local Environment](#5-docker-compose--local-environment)
6. [CI/CD Pipeline](#6-cicd-pipeline)
7. [Deployment Targets](#7-deployment-targets)
8. [Environment Variables](#8-environment-variables)
9. [Database Management](#9-database-management)
10. [Networking & Reverse Proxy](#10-networking--reverse-proxy)
11. [Health Checks & Monitoring](#11-health-checks--monitoring)
12. [Security Practices](#12-security-practices)
13. [Helper Scripts](#13-helper-scripts)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. System Architecture

```
                         ┌─────────────────────────┐
            HTTPS        │   Vercel (Frontend CDN)  │
  User  ───────────────► │   React SPA / Static     │
                         │   SPA rewrites → /index  │
                         └───────────┬──────────────┘
                                     │ /api/* /auth/* proxy
                                     ▼
                         ┌─────────────────────────┐
                         │  Render (Backend API)    │
                         │  FastAPI + Uvicorn       │
                         │  Python 3.11             │
                         └───┬───────────┬──────────┘
                             │           │
                ┌────────────▼┐   ┌──────▼──────────┐
                │ PostgreSQL  │   │ Redis            │
                │ 15 (Render) │   │ 7 (session/cache)│
                └─────────────┘   └─────────────────┘
                             │
                    ┌────────▼────────┐
                    │ Ganache / EVM   │
                    │ (local only)    │
                    └─────────────────┘
```

**Production split:**
- **Frontend** → Vercel (global CDN, SPA routing, security headers)
- **Backend** → Render (auto-deploy, managed PostgreSQL)

**Local development** uses Docker Compose to run all services together.

---

## 2. Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React (Create React App) | 18 |
| Backend | FastAPI + Uvicorn | Python 3.11 |
| Database | PostgreSQL | 15 |
| Cache / Sessions | Redis | 7 |
| Blockchain (local) | Ganache | latest |
| Containerization | Docker + Docker Compose | v2 |
| CI/CD | GitHub Actions | v4 actions |
| Frontend Hosting | Vercel | — |
| Backend Hosting | Render | — |
| DB Admin (optional) | PGAdmin 4 | latest |

---

## 3. Repository Structure

```
E-voting-system/
├── .github/workflows/
│   ├── ci.yml              # CI — tests, build, integration
│   └── deploy.yml          # CD — deploy frontend to Vercel
├── backend/
│   ├── Dockerfile          # Python 3.11-slim image
│   ├── requirements.txt    # Python dependencies
│   ├── app/                # FastAPI application
│   │   ├── main.py
│   │   ├── config/         # Settings & configuration
│   │   ├── core/           # Auth, security, middleware
│   │   ├── models/         # SQLAlchemy models
│   │   ├── routers/        # API route handlers
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── utils/          # Helpers & utilities
│   └── tests/              # Pytest test suite
├── frontend/
│   ├── Dockerfile          # Multi-stage: dev / build / nginx
│   ├── nginx.conf          # Production reverse proxy config
│   ├── package.json
│   ├── public/
│   └── src/                # React source code
├── blockchain/
│   └── contracts/          # Solidity contracts
├── database/
│   └── init.sql            # Schema initialization script
├── artifacts/              # Build artifacts, reports, keys
├── docs/                   # Documentation
├── docker-compose.yml      # Full local environment
├── render.yaml             # Render Blueprint (backend + DB)
├── vercel.json             # Vercel configuration (frontend)
├── pytest.ini              # Pytest warning filters
├── start.ps1               # Windows startup script
└── reset_demo.ps1          # Reset demo data script
```

---

## 4. Containerization

### 4.1 Backend Dockerfile

**Image:** `python:3.11-slim`

```
WORKDIR /app
COPY requirements.txt → pip install
COPY . .
EXPOSE 8000
HEALTHCHECK via python http.client → /health
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Key points:
- Requirements are copied first for Docker layer caching.
- Health check uses Python's `http.client` (no curl dependency).
- `--reload` is used for development; remove for production builds.
- Logs directory created at `/app/logs`.

### 4.2 Frontend Dockerfile (Multi-Stage)

| Stage | Base Image | Purpose |
|-------|-----------|---------|
| `development` | `node:18-alpine` | `npm start` dev server on port 3000 |
| `build` | `node:18-alpine` | `npm ci --only=production` + `npm run build` |
| `production` | `nginx:alpine` | Serves static build via nginx on port 80 |

The `docker-compose.yml` targets the `development` stage. For production images, build with `--target production`.

### 4.3 Building Production Images

```bash
# Backend
docker build -t evoting-backend:latest ./backend

# Frontend (production with nginx)
docker build --target production -t evoting-frontend:latest ./frontend
```

---

## 5. Docker Compose — Local Environment

The `docker-compose.yml` orchestrates six services:

| Service | Container | Port | Purpose |
|---------|----------|------|---------|
| `postgres` | `evoting_postgres` | 5432 | PostgreSQL 15 database |
| `redis` | `evoting_redis` | 6379 | Cache and session store |
| `backend` | `evoting_backend` | 8000 | FastAPI API server |
| `frontend` | `evoting_frontend` | 3000 | React development server |
| `ganache` | `evoting_ganache` | 8545 | Local Ethereum blockchain |
| `pgadmin` | `evoting_pgadmin` | 5050 | DB admin UI (tools profile) |

### 5.1 Startup

```bash
# Start all core services
docker-compose up -d --build

# Include PGAdmin (optional tools profile)
docker-compose --profile tools up -d --build

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 5.2 Service Dependencies

```
postgres (healthy) ──► backend ──► frontend
redis               ──► backend
ganache             ──► backend (BLOCKCHAIN_RPC)
postgres            ──► pgadmin (tools profile)
```

The backend waits for PostgreSQL to be healthy before starting (`condition: service_healthy`).

### 5.3 Volumes

| Volume | Purpose |
|--------|---------|
| `postgres_data` | Persistent database storage |
| `backend_cache` | Pip cache for faster rebuilds |
| `pgadmin_data` | PGAdmin session data |

### 5.4 Network

All services join the `evoting_network` bridge network, allowing inter-service DNS resolution (e.g., `postgres`, `backend`, `redis`).

### 5.5 Teardown

```bash
# Stop and remove containers
docker-compose down

# Stop, remove containers, AND delete volumes (full reset)
docker-compose down -v
```

---

## 6. CI/CD Pipeline

The project uses two GitHub Actions workflows. Full details in [CI_CD_PIPELINE.md](CI_CD_PIPELINE.md).

### 6.1 CI Workflow (`.github/workflows/ci.yml`)

**Triggers:** Push or PR to `main`

```
┌──────────────────┐    ┌─────────────────┐
│  backend-tests   │    │  frontend-build  │
│  Python 3.11     │    │  Node 18         │
│  + PostgreSQL 15 │    │  npm ci → build  │
│  + Redis 7       │    │                  │
└────────┬─────────┘    └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
            ┌─────────────────┐
            │   integration   │
            │  Docker Compose │
            │  smoke tests    │
            └─────────────────┘
```

**Jobs:**

1. **`backend-tests`** — Spins up PostgreSQL 15 and Redis 7 as service containers, initializes the DB schema from `database/init.sql`, runs `pytest tests/ -v`, and uploads JUnit XML results as artifacts.

2. **`frontend-build`** — Installs dependencies with `npm ci`, builds the React app (`CI=false` to avoid treating warnings as errors), and uploads the `frontend/build/` directory as an artifact.

3. **`integration`** — Runs after both jobs pass. Starts all services with `docker compose up -d --build`, polls the `/health` endpoint for up to 60 seconds, verifies backend returns valid JSON, checks the frontend serves HTML, then tears down with `docker compose down -v`.

### 6.2 CD Workflow (`.github/workflows/deploy.yml`)

**Triggers:** Push to `main`, manual dispatch (`workflow_dispatch`)

```
checkout → install Vercel CLI → vercel pull → vercel build --prod → vercel deploy --prebuilt --prod → HTTP verify
```

Deploys the frontend to Vercel production. The deployed URL is written to `$GITHUB_STEP_SUMMARY` for visibility in the Actions UI.

### 6.3 Required GitHub Secrets

| Secret | Purpose | Where to find it |
|--------|---------|-------------------|
| `VERCEL_TOKEN` | Vercel API access | [vercel.com/account/tokens](https://vercel.com/account/tokens) |
| `VERCEL_ORG_ID` | Organization/team ID | `.vercel/project.json` after `vercel link` |
| `VERCEL_PROJECT_ID` | Project ID | `.vercel/project.json` after `vercel link` |

### 6.4 Artifacts Produced

| Artifact | Source Job | Contents |
|----------|-----------|----------|
| `backend-test-results` | `backend-tests` | JUnit XML (`backend.xml`) |
| `frontend-build` | `frontend-build` | Production React build |

---

## 7. Deployment Targets

### 7.1 Frontend — Vercel

| Setting | Value |
|---------|-------|
| Framework | Create React App |
| Build command | `cd frontend && npm install && CI=false npm run build` |
| Output directory | `frontend/build` |
| Node.js | 18 |

**Configuration (`vercel.json`):**
- SPA catch-all: `/(.*) → /index.html`
- API proxy: `/api/*`, `/auth/*`, `/health`, `/docs`, `/openapi.json` → Render backend
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`

### 7.2 Backend — Render

Provisioned via `render.yaml` (Render Blueprint):

| Setting | Value |
|---------|-------|
| Runtime | Python 3.11 |
| Root directory | `backend` |
| Build | `pip install -r requirements.txt` |
| Start | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/health` |
| Plan | Free tier |

**Database:** A free-tier PostgreSQL instance is auto-provisioned by the Blueprint. Connection details are injected as environment variables.

**Deployment flow:**
1. Go to [dashboard.render.com](https://dashboard.render.com)
2. **New → Blueprint** → connect the GitHub repo
3. Select `render.yaml` — Render provisions the web service and database automatically
4. Subsequent pushes to the connected branch trigger auto-deploy

### 7.3 Live URLs

| Component | URL |
|-----------|-----|
| Frontend | `https://e-voting-system-cyan.vercel.app` |
| Backend API | `https://e-voting-backend-q8x9.onrender.com` |
| Health Check | `https://e-voting-backend-q8x9.onrender.com/health` |
| API Docs (Swagger) | `https://e-voting-backend-q8x9.onrender.com/docs` |

---

## 8. Environment Variables

### 8.1 Backend Variables

| Variable | Local (Docker Compose) | CI | Production (Render) |
|----------|----------------------|-----|---------------------|
| `POSTGRES_HOST` | `postgres` | `localhost` | Auto (fromDatabase) |
| `POSTGRES_PORT` | `5432` | `5432` | Auto (fromDatabase) |
| `POSTGRES_DB` | `evoting` | `evoting_db` | Auto (fromDatabase) |
| `POSTGRES_USER` | `admin` | `evoting` | Auto (fromDatabase) |
| `POSTGRES_PASSWORD` | `secure_password` | `evoting_pass` | Auto (fromDatabase) |
| `DATABASE_URL` | — | `postgresql://evoting:evoting_pass@localhost:5432/evoting_db` | Auto (connectionString) |
| `SECRET_KEY` | `dev_secret_key_change_in_production` | `ci-test-secret-key` | Auto-generated |
| `BLOCKCHAIN_RPC` | `http://ganache:8545` | *(empty)* | — |
| `REDIS_URL` | — | `redis://localhost:6379/0` | — |
| `API_HOST` | `0.0.0.0` | — | — |
| `API_PORT` | `8000` | — | `$PORT` (Render) |
| `FRONTEND_URL` | — | — | `https://e-voting-system-cyan.vercel.app` |
| `KEY_SIZE` | `2048` | — | — |
| `THRESHOLD` | `3` | — | — |
| `TOTAL_TRUSTEES` | `5` | — | — |

### 8.2 Frontend Variables

| Variable | Local (Docker Compose) | Production (Vercel) |
|----------|----------------------|---------------------|
| `REACT_APP_API_URL` | `http://localhost:8000/api` | Proxied via `vercel.json` |
| `REACT_APP_WS_URL` | `ws://localhost:8000/ws` | — |
| `PROXY_TARGET` | `http://backend:8000` | — |

### 8.3 PGAdmin (Optional)

| Variable | Default |
|----------|---------|
| `PGADMIN_EMAIL` | `admin@evoting.com` |
| `PGADMIN_PASSWORD` | `admin` |

---

## 9. Database Management

### 9.1 Schema Initialization

The schema is defined in `database/init.sql` and includes:

- PostgreSQL extensions: `uuid-ossp`, `pgcrypto`
- Core tables: `trustees`, `elections`, `encrypted_votes`, `partial_decryptions`, and more
- UUID-based primary keys with auto-generation
- Foreign key relationships with cascading deletes
- JSONB columns for flexible data (candidates, encryption params)

**Initialization methods:**
- **Docker Compose:** Mounted as `/docker-entrypoint-initdb.d/init.sql` — runs on first volume creation
- **CI:** Executed via `psql -f database/init.sql`
- **Render:** Manually run against the provisioned database or via the app's startup

### 9.2 Accessing the Database

```bash
# Via Docker (local)
docker exec -it evoting_postgres psql -U admin -d evoting

# Via PGAdmin (local, tools profile)
# Navigate to http://localhost:5050

# Via helper scripts
cd backend && python view_db.py
# or from project root
.\view_db.ps1
```

### 9.3 Resetting Data

```bash
# Via API endpoint (local dev)
curl -X POST http://localhost:8000/api/mock/reset-database

# Via PowerShell script
.\reset_demo.ps1

# Full volume reset
docker-compose down -v
docker-compose up -d --build
```

---

## 10. Networking & Reverse Proxy

### 10.1 Local (Docker Compose)

All services share the `evoting_network` bridge. Service names resolve as DNS hostnames:
- Frontend calls backend at `http://backend:8000`
- Backend calls PostgreSQL at `postgres:5432`
- Backend calls Redis at `redis:6379`
- Backend calls Ganache at `ganache:8545`

### 10.2 Production (Nginx)

The frontend production Dockerfile includes an nginx stage with `nginx.conf`:

```
/           → SPA (try_files → /index.html)
/api/*      → proxy_pass http://backend:8000
/auth/*     → proxy_pass http://backend:8000
*.js|css|…  → 1-year cache, immutable
```

### 10.3 Production (Vercel)

`vercel.json` handles routing at the CDN edge:

| Route | Destination |
|-------|-------------|
| `/api/:path*` | Render backend |
| `/auth/:path*` | Render backend |
| `/health` | Render backend |
| `/docs` | Render backend |
| `/openapi.json` | Render backend |
| `/(.*) ` | `/index.html` (SPA fallback) |

---

## 11. Health Checks & Monitoring

### 11.1 Health Check Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `GET /health` | Backend liveness | `200 OK` with JSON status |

### 11.2 Docker Health Checks

| Service | Method | Interval | Retries |
|---------|--------|----------|---------|
| PostgreSQL | `pg_isready` | 10s | 5 |
| Redis | `redis-cli ping` | 10s | 3 |
| Backend | Python HTTP GET `/health` | 30s | 3 |

### 11.3 CI Health Checks

The integration job polls `/health` every 2 seconds for up to 60 seconds before running smoke tests.

### 11.4 Render Health Check

Render monitors the `/health` endpoint and automatically restarts the service if it becomes unresponsive.

---

## 12. Security Practices

### 12.1 Secrets Management

- **Local:** Environment variables in `.env` or `docker-compose.yml` defaults (development only)
- **CI:** GitHub Actions secrets (encrypted at rest)
- **Production:** Render auto-generated secrets / environment variables, Vercel project settings
- **Never commit:** `.env` files, API keys, tokens, or private keys to version control

### 12.2 HTTP Security Headers (Vercel)

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME-type sniffing |
| `X-Frame-Options` | `DENY` | Block clickjacking |
| `X-XSS-Protection` | `1; mode=block` | XSS filter |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer leakage |

### 12.3 Container Security

- Base images use `-slim` (Python) and `-alpine` (Node, Redis, PostgreSQL) variants for minimal attack surface
- No root user escalation required
- System dependencies are minimized (curl not installed in backend image)

### 12.4 Database Security

- Passwords configurable via environment variables — defaults are for development only
- `pgcrypto` extension enabled for server-side encryption support
- UUID-based IDs prevent sequential ID enumeration

### 12.5 API Security

- Rate limiting via `slowapi`
- JWT-based authentication (`python-jose`)
- MFA support (`pyotp`)
- CORS configured via `FRONTEND_URL`

---

## 13. Helper Scripts

### 13.1 `start.ps1` — Full Startup (Windows)

Performs a complete startup sequence:
1. Verifies Docker is running
2. Stops existing containers
3. Builds and starts all services
4. Waits for backend health check
5. Opens browser to `http://localhost:3000`

```powershell
.\start.ps1
```

### 13.2 `reset_demo.ps1` — Reset Demo Data (Windows)

Calls `POST /api/mock/reset-database` to clear all data and start fresh.

```powershell
.\reset_demo.ps1
```

### 13.3 `view_db.ps1` / `backend/view_db.py` — Database Inspector

Connects to the database and displays current table contents for debugging.

```powershell
.\view_db.ps1
# or
cd backend && python view_db.py
```

---

## 14. Troubleshooting

### 14.1 Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Backend can't connect to DB | PostgreSQL not healthy yet | Wait for health check or restart: `docker-compose restart backend` |
| Port 5432 already in use | Local PostgreSQL running | Stop local instance or change compose port mapping |
| Port 3000 already in use | Another dev server running | Kill the process or change the port |
| Frontend can't reach API | Wrong `REACT_APP_API_URL` | Ensure it points to `http://localhost:8000/api` locally |
| `init.sql` fails in CI | Schema already exists | `continue-on-error: true` in the workflow handles this |
| Docker build hangs | Network issue or slow image pull | Check Docker network and try `docker-compose pull` first |
| Vercel deploy 401 | Expired or invalid token | Regenerate at [vercel.com/account/tokens](https://vercel.com/account/tokens) |
| Render deploy fails | Missing environment variable | Check `render.yaml` and Render dashboard |
| Tests fail on blockchain calls | Ganache not running / `BLOCKCHAIN_URL` empty | Blockchain tests skip in CI (`BLOCKCHAIN_URL=""`) |

### 14.2 Useful Diagnostic Commands

```bash
# Check running containers
docker-compose ps

# View service logs
docker-compose logs -f backend
docker-compose logs -f postgres

# Inspect container networking
docker network inspect evoting_network

# Test backend health (local)
curl http://localhost:8000/health | python -m json.tool

# Test frontend (local)
curl -s http://localhost:3000 | head -5

# Run backend tests locally
cd backend
PYTHONPATH=. python -m pytest tests/ -v

# Build frontend manually
cd frontend
npm ci
npm run build

# Check database connection
docker exec -it evoting_postgres psql -U admin -d evoting -c "\dt"
```

### 14.3 CI–Specific Debugging

Refer to [CI_CD_PIPELINE.md — Troubleshooting CI Failures](CI_CD_PIPELINE.md#troubleshooting-ci-failures) for CI-specific issues including:
- Backend test DB connection failures
- Frontend lockfile issues
- Integration health check timeouts
- Deploy token expiration

---

## Quick Reference

```bash
# ─── Local Development ──────────────────────
docker-compose up -d --build          # Start everything
docker-compose down -v                # Full teardown
.\start.ps1                           # Windows one-click start
.\reset_demo.ps1                      # Clear demo data

# ─── Testing ────────────────────────────────
cd backend && python -m pytest tests/ -v   # Backend tests
cd frontend && npm run build               # Frontend build check

# ─── Production ─────────────────────────────
# Frontend: Push to main → GitHub Actions → Vercel
# Backend:  Push to main → Render auto-deploy

# ─── URLs ───────────────────────────────────
# Local:   http://localhost:3000 (frontend)  http://localhost:8000 (backend)
# Prod:    https://e-voting-system-cyan.vercel.app
#          https://e-voting-backend-q8x9.onrender.com
```
