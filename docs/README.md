# E-Voting System

A privacy-preserving electronic voting platform that uses homomorphic encryption to tally votes without decrypting individual ballots, threshold cryptography so no single party can access results alone, and an immutable hash-chained ledger for auditability.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation and Setup](#installation-and-setup)
3. [System Architecture](#system-architecture)
4. [Running a Demo Election](#running-a-demo-election)
5. [User Roles](#user-roles)
6. [Cryptographic Design](#cryptographic-design)
7. [API Endpoints](#api-endpoints)
8. [Project Structure](#project-structure)
9. [Testing](#testing)
10. [Local Development](#local-development)
11. [Deployment (Vercel)](#deployment-vercel)
12. [CI/CD (GitHub Actions)](#cicd-github-actions)
13. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Docker Desktop (running)
- Minimum 8 GB RAM
- The following ports must be free: 3000, 8000, 5432, 8545

---

## Installation and Setup

```bash
cd E-voting-system
docker-compose up -d
```

Give it about 30 seconds for the database to initialize, then verify:

```bash
docker-compose ps
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

To tear everything down (including the database volume):

```bash
docker-compose down -v
```

---

## System Architecture

The project is a four-service stack orchestrated by Docker Compose:

```
React 18 (:3000)  --->  FastAPI (:8000)  --->  PostgreSQL 15 (:5432)
                                          --->  Ganache (:8545)
```

- **Frontend** serves the voter, admin, trustee, auditor, and security-engineer interfaces. Role-based tab visibility is enforced at login.
- **Backend** exposes REST endpoints for authentication, vote encryption, tallying, ledger management, verification, and operational audit. JWT-based auth with optional TOTP MFA.
- **PostgreSQL** stores users, elections, encrypted votes, trustee shares, tallying sessions, partial decryptions, results, audit logs, incidents, and disputes.
- **Ganache** acts as a local Ethereum node for publishing finalized election results on-chain.

---

## Running a Demo Election

The system ships with a built-in testing workflow. Open the frontend at http://localhost:3000 and log in as `admin`.

### Phase 1 — Setup (Testing tab)
1. **Setup Trustees** — generates 5 trustees and splits the election private key into 5 shares using Shamir's Secret Sharing.
2. **Generate 100 Mock Votes** — creates 100 Paillier-encrypted ballots. Takes roughly 20 seconds due to 2048-bit encryption.
3. **Generate 100 Mock Ballots** — registers the ballots in the database.
4. **Tally Ballots** — aggregates all ciphertexts homomorphically (multiplies encrypted values to get encrypted sums).
5. **Start Tallying Process** — marks the election as ready for trustee decryption.

### Phase 2 — Decryption (Trustees tab)
6. Click **Decrypt** on any 3 of the 5 trustees. Each one contributes a partial decryption using their key share. The UI shows progress (1/3, 2/3, 3/3).

### Phase 3 — Finalization (Testing tab)
7. **Finalize Tally on Blockchain** — reconstructs the plaintext result from the 3 partial decryptions and publishes it to Ganache.

### Phase 4 — Results (Results tab)
8. View the vote distribution per candidate, the declared winner, and the blockchain transaction hash.

---

## User Roles

| Role | Credential | What they can access |
|------|------------|---------------------|
| Voter | voter1 through voter5 | Voter Access, Results, Ledger, Verification |
| Admin | admin | All tabs |
| Trustee | trustee | Trustees, Results, Ledger, Verification |
| Auditor | auditor | Results, Ledger, Ops & Audit, Verification |
| Security Engineer | security_engineer | Security Lab, Ops & Audit, Ledger, Verification |

MFA (TOTP) can be enabled per voter from the Voter Access dashboard. See [docs/MFA_CODE_GUIDE.md](MFA_CODE_GUIDE.md) for details on generating codes.

---

## Cryptographic Design

### Homomorphic encryption
Votes are encrypted using the Paillier cryptosystem with 2048-bit keys. The additive homomorphic property allows the backend to compute E(v1 + v2 + ... + vn) = E(v1) * E(v2) * ... * E(vn) without decrypting any individual ballot. The frontend additionally performs client-side encryption with RSA-OAEP via the Web Crypto API before submitting to the backend.

### Threshold decryption
The election private key is split into 5 shares (Shamir's Secret Sharing, threshold 3). No single trustee holds the full key. Decryption requires at least 3 trustees to contribute partial results, which are combined server-side to reconstruct the plaintext tally.

### Blind signatures
Voter credential issuance uses an RSA blind-signature protocol. The authentication zone (Zone 1) knows who the voter is; the vote-casting zone (Zone 3) only sees an anonymous signed token. The issuer signs a blinded token it cannot read, and the voter unblinds it. This breaks the link between identity and ballot.

### Immutable ledger
Encrypted votes are appended to a hash-chained, Merkle-tree-backed ledger. Blocks go through a BFT consensus simulation (propose, approve x3, finalize) before they are committed. Merkle proofs let voters verify inclusion without revealing vote content.

### Audit chain
All system operations (credential issuance, vote submission, tally actions, incident reports) are logged in a tamper-evident hash chain where each entry contains the hash of the previous entry.

---

## API Endpoints

Base URL: `http://localhost:8000`

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| /auth/login | POST | Authenticate and receive JWT |
| /auth/mfa/setup | POST | Enable TOTP MFA |
| /auth/mfa/verify | POST | Verify TOTP code |

### Voting
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/voter/check-eligibility | POST | Check voter eligibility |
| /api/voter/issue-credential | POST | Issue blind-signed credential |
| /api/voter/cast-vote | POST | Submit encrypted vote with token |

### Tallying
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/tally/start | POST | Begin tallying for an election |
| /api/tally/partial-decrypt/{trustee_id} | POST | Trustee partial decryption |
| /api/tally/finalize | POST | Combine partials, publish result |
| /api/tally/status/{election_id} | GET | Tallying progress |

### Ledger
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/ledger/submit | POST | Submit vote entry |
| /api/ledger/propose | POST | Propose new block |
| /api/ledger/approve | POST | Approve proposed block |
| /api/ledger/finalize | POST | Finalize block after quorum |
| /api/ledger/blocks | GET | List committed blocks |
| /api/ledger/proof/{entry_hash} | GET | Merkle inclusion proof |
| /api/ledger/verify-chain | GET | Validate full chain integrity |

### Verification and Ops
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/verify/receipt | POST | Verify voter receipt |
| /api/verify/zk-proof | POST | Validate ZK proof bundle |
| /api/security/replay-ledger | POST | Replay and verify ledger |
| /api/security/simulate | POST | Run threat simulation |
| /api/ops/dashboard/{election_id} | GET | Transparency metrics |
| /api/ops/evidence/{election_id} | GET | Download evidence package |
| /api/ops/incidents | GET/POST | Incident management |
| /api/ops/disputes | GET/POST | Dispute workflow |
| /api/ops/compliance-report/{election_id} | GET | Compliance report |

### Mock / Testing
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/mock/setup-trustees | POST | Initialize trustee shares |
| /api/mock/generate-votes?count=N | POST | Generate encrypted test votes |
| /api/mock/reset-database?confirm=true | POST | Wipe and reinitialize database |

Interactive Swagger documentation is available at http://localhost:8000/docs.

---

## Project Structure

```
E-voting-system/
  docker-compose.yml
  vercel.json                      # Vercel deployment configuration
  pytest.ini
  start.ps1                        # PowerShell launcher
  reset_demo.ps1                   # Demo reset script

  .github/
    workflows/
      ci.yml                       # CI: backend tests, frontend build, integration
      deploy.yml                   # CD: Vercel production deploy

  frontend/
    src/
      App.js                       # Root component, routing, role-based tabs
      components/
        VoterAccess.js             # Credential issuance, ballot submission
        TestingPanel.jsx           # Admin testing workflow
        TrusteePanel.jsx           # Trustee decryption interface
        ResultsDashboard.jsx       # Election result charts
        LedgerExplorer.jsx         # Block browser
        VerificationPortal.jsx     # Receipt and ZK proof verification
        OpsDashboard.js            # Incident/dispute/compliance ops
        SecurityLab.jsx            # Threat simulation interface
        CryptoVisualizer.jsx       # Cryptographic flow visualization
        TallyAudit.jsx             # Tally audit trail
      services/
        webauthn.js                # WebAuthn helpers
    package.json

  backend/
    app/
      main.py                     # FastAPI app, lifespan, router registration
      routers/
        auth.py                   # Login, JWT, MFA
        voter.py                  # Eligibility, credential, vote cast
        tallying.py               # Tally start, partial decrypt, finalize
        trustees.py               # Trustee management
        results.py                # Result retrieval
        ledger.py                 # Ledger CRUD and consensus
        ops.py                    # Incidents, disputes, compliance, evidence
        verification.py           # Receipt and ZK proof verification
        security.py               # Threat sim, anomaly detection, replay
        mock_data.py              # Test data generation
        biometric.py              # WebAuthn biometric endpoints (optional)
      services/
        encryption.py             # Paillier homomorphic encryption
        tallying.py               # Tallying business logic
        threshold_crypto.py       # Shamir's Secret Sharing
        ledger_service.py         # Ledger core (Merkle tree, BFT, chain verify)
        monitoring.py             # System monitoring
      models/                     # SQLAlchemy and Pydantic models
    tests/
      test_epic4.py               # Paillier, threshold, aggregation (19 tests)
      test_epic4_endpoints.py     # Tally API integration (1 test)
      test_security_epic_manual.py # Full security flow (1 test)
      test_ledger.py              # Ledger hashing, Merkle, genesis (8 tests)
      test_epic3_enhancements.py  # Block validation, signatures (14 tests)
      test_epic5_user_stories.py  # Epic 5 endpoints (11 tests)
      test_ops_stories.py         # Ops workflows (4 tests)
      test_verification_stories.py # Verification endpoints (4 tests)
      test_all_implemented_features.py  # Cross-epic (41 tests)
    run_all_tests.py              # Master test runner
    requirements.txt

  database/
    init.sql                      # Schema initialization

  blockchain/
    contracts/                    # Solidity contracts (if applicable)

  artifacts/                      # Signed reports (anomaly, compliance, etc.)

  scripts/
    verify_integration.py         # Integration verification helper

  docs/
    DEPLOYMENT_GUIDE.md           # Vercel + Render deployment guide
    CI_CD_PIPELINE.md             # GitHub Actions CI/CD reference
    EPIC3_README.md               # Ledger module documentation
    EPIC4_README.md               # Tallying and security architecture
    EPIC5_README.md               # Verification and audit ops
    USAGE_GUIDE.md                # Usage guide + manual QA tests
    USER_STORIES.md               # Full user stories (all epics)
    TEST_COVERAGE_REPORT.md       # Test suite breakdown
    MFA_CODE_GUIDE.md             # MFA setup instructions
```

---

## Testing

The project has 9 test files with 103 tests total. All tests pass on the current codebase.

```bash
cd backend
python run_all_tests.py
```

The runner executes each file individually and reports results grouped by epic:

| Suite | Tests | Covers |
|-------|-------|--------|
| test_epic4.py | 19 | Paillier encrypt/decrypt, homomorphic aggregation, Shamir split/reconstruct |
| test_epic3_enhancements.py | 14 | Config loading, RSA signatures, block structure validation |
| test_all_implemented_features.py | 41 | Cross-epic: auth, ballots, ledger, encryption, verification |
| test_epic5_user_stories.py | 11 | Receipt, ZK proof, replay, dashboard, incidents, disputes |
| test_ledger.py | 8 | Hashing, Merkle tree, genesis block, chain linkage |
| test_ops_stories.py | 4 | Evidence, threat sim, incident lifecycle, anomalies |
| test_verification_stories.py | 4 | Receipt proof, ZK validation, chain replay, stats |
| test_epic4_endpoints.py | 1 | Tally REST API integration |
| test_security_epic_manual.py | 1 | Login, eligibility, blind credential, anonymous vote |

To run a specific file:

```bash
pytest tests/test_epic4.py -v
```

---

## Local Development

### Frontend (without Docker)
```bash
cd frontend
npm install
npm start
```

### Backend (without Docker)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend expects a running PostgreSQL instance. Connection parameters are read from environment variables (see `.env.example`).

### Common Docker commands

```bash
docker-compose up -d              # start all services
docker-compose down                # stop all services
docker-compose down -v             # stop and delete volumes
docker-compose logs -f             # stream logs
docker-compose restart backend     # restart one service
docker-compose up -d --build       # rebuild images
```

---

## Deployment (Vercel)

The React frontend is configured for deployment on **Vercel**.

### Quick deploy
```bash
npm install -g vercel
cd E-voting-system
vercel link
vercel --prod
```

Or connect the GitHub repository directly in the [Vercel dashboard](https://vercel.com/new) — it auto-detects `vercel.json` and deploys on every push.

### Configuration
- `vercel.json` at project root defines build command, output directory, SPA rewrites, and security headers
- Build: `cd frontend && npm install && npm run build`
- Output: `frontend/build`

> **Note:** Vercel hosts the frontend SPA only. The backend (FastAPI + PostgreSQL + Redis + Ganache) must be deployed separately (Docker Compose, cloud VM, or container service).

---

## CI/CD (GitHub Actions)

Two workflows run automatically on push/PR to `all` or `main`:

### CI Pipeline (`.github/workflows/ci.yml`)
| Job | What it does |
|-----|-------------|
| **backend-tests** | Runs 103 Python tests against PostgreSQL 15 + Redis 7 service containers |
| **frontend-build** | Builds the React production bundle with Node 18 |
| **integration** | Docker Compose smoke test — builds images, checks `/health`, verifies frontend |

### CD Pipeline (`.github/workflows/deploy.yml`)
Deploys the frontend to Vercel on every push to `all` or `main`.

**Required GitHub Secrets:**
| Secret | How to get it |
|--------|--------------|
| `VERCEL_TOKEN` | [Vercel → Settings → Tokens](https://vercel.com/account/tokens) |
| `VERCEL_ORG_ID` | From `.vercel/project.json` after `vercel link` |
| `VERCEL_PROJECT_ID` | From `.vercel/project.json` after `vercel link` |

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) and [CI_CD_PIPELINE.md](CI_CD_PIPELINE.md) for full details.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| "Action Failed" on vote generation | Encryption takes ~20s for 100 ballots | Wait for it to finish; do not click again |
| Key mismatch on finalize | Steps were run out of order or repeated | Reset the database and redo steps 1-7 in order |
| Decrypt button greyed out | Tallying process not started | Complete all 5 setup steps first |
| No results after finalize | Fewer than 3 trustees decrypted | Decrypt with at least 3 trustees, then finalize |
| Containers fail to start | Port conflict or stale volumes | `docker-compose down -v && docker-compose up -d --build` |
| "mfa_pending" shown as role | Stale browser localStorage | Clear localStorage for localhost:3000 and refresh |

---

## Further Documentation

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) — Vercel frontend + Render backend deployment
- [CI_CD_PIPELINE.md](CI_CD_PIPELINE.md) — GitHub Actions CI/CD workflows and troubleshooting
- [EPIC3_README.md](EPIC3_README.md) — Immutable ledger: BFT consensus, Merkle proofs, chain verification
- [EPIC4_README.md](EPIC4_README.md) — Cryptographic pipeline: Paillier, threshold decryption, blind signatures, security zones
- [EPIC5_README.md](EPIC5_README.md) — Verification and audit: receipt verification, anomaly detection, incident response
- [USAGE_GUIDE.md](USAGE_GUIDE.md) — Usage walkthrough + manual QA tests
- [USER_STORIES.md](USER_STORIES.md) — Full user stories for all epics
- [TEST_COVERAGE_REPORT.md](TEST_COVERAGE_REPORT.md) — Full test suite breakdown
- [MFA_CODE_GUIDE.md](MFA_CODE_GUIDE.md) — How to get TOTP codes for MFA login

---

This is a demonstration system built for academic evaluation. It is not intended for production use without significant hardening (HSM key management, physical trustee separation, network-layer encryption, voter identity verification, external audit infrastructure).
