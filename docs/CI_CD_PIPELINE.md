# CI/CD Pipeline

Continuous integration and deployment workflows for the E-Voting System, powered by GitHub Actions.

---

## Workflows

### 1. CI — Tests & Lint (`.github/workflows/ci.yml`)

**Triggers:** Push or PR to `all` / `main`

| Job | What it does | Services | Duration |
|-----|-------------|----------|----------|
| `backend-tests` | Runs the full Python test suite | PostgreSQL 15, Redis 7 | ~2–3 min |
| `frontend-build` | Installs deps (`npm ci`), builds React app | — | ~1–2 min |
| `integration` | Docker Compose smoke test (health + frontend checks) | All (via Compose) | ~3–5 min |

#### Backend Tests Detail

1. Checks out code.
2. Sets up Python 3.11 with pip caching.
3. Installs `backend/requirements.txt`.
4. Spins up PostgreSQL 15 and Redis 7 as service containers.
5. Initializes the database schema from `database/init.sql`.
6. Runs `pytest tests/ -v --tb=short --junitxml=backend.xml`.
7. Uploads JUnit XML as an artifact.

**Environment variables set in CI:**

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `postgresql://evoting:evoting_pass@localhost:5432/evoting_db` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `SECRET_KEY` | `ci-test-secret-key` |
| `BLOCKCHAIN_URL` | *(empty — blockchain tests skipped)* |

#### Frontend Build Detail

1. Checks out code.
2. Sets up Node.js 18 with npm caching.
3. Runs `npm ci` inside `frontend/`.
4. Builds production bundle (`npm run build` with `CI=false`).
5. Uploads `frontend/build/` as an artifact.

#### Integration Test Detail

1. Runs after `backend-tests` and `frontend-build` pass.
2. `docker compose up -d --build` — starts all services.
3. Polls `http://localhost:8000/health` for up to 60 seconds.
4. Verifies backend health endpoint returns valid JSON.
5. Verifies frontend at `http://localhost:3000` serves HTML.
6. Tears down with `docker compose down -v`.

---

### 2. Deploy — Vercel (`.github/workflows/deploy.yml`)

**Triggers:** Push to `all` / `main`, manual dispatch (`workflow_dispatch`)

| Step | Command |
|------|---------|
| Pull environment | `vercel pull --yes --environment=production` |
| Build | `vercel build --prod` |
| Deploy | `vercel deploy --prebuilt --prod` |
| Verify | HTTP status check on the deployed URL |

---

## Required GitHub Secrets

These must be configured in **Settings → Secrets and variables → Actions**:

| Secret | Purpose |
|--------|---------|
| `VERCEL_TOKEN` | Vercel personal access token |
| `VERCEL_ORG_ID` | From `.vercel/project.json` after `vercel link` |
| `VERCEL_PROJECT_ID` | From `.vercel/project.json` after `vercel link` |

---

## Running Tests Locally

```bash
# All backend tests
cd backend
PYTHONPATH=. python -m pytest tests/ -v

# Specific test file
PYTHONPATH=. python -m pytest tests/test_all_implemented_features.py -v

# Frontend build check
cd frontend
npm ci
npm run build

# Docker integration test
docker-compose up -d --build
curl http://localhost:8000/health
curl http://localhost:3000
docker-compose down -v
```

---

## Troubleshooting CI Failures

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Backend tests fail on DB connection | PostgreSQL service not ready | The workflow has health checks; re-run the job |
| `init.sql` step fails | Schema already exists or permission issue | Step has `continue-on-error: true`; safe to ignore |
| Frontend build fails | Missing lockfile | Ensure `frontend/package-lock.json` is committed |
| Integration health check times out | Docker build error | Check `docker compose logs` in the job output |
| Deploy fails with 401 | Invalid or expired Vercel token | Regenerate the token and update the secret |
