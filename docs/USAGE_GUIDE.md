# Usage Guide

A complete guide to running, using, and testing the E-Voting System locally.

---

## Getting Started

### Prerequisites
- Docker Desktop installed and running
- 8 GB RAM minimum
- Ports must be free: 3000, 8000, 5432, 6379, 8545

### Start the System

```bash
cd E-voting-system
docker-compose up -d
# Wait 30 seconds for initialization
docker-compose ps
```

### Verify Services

| Service | URL | Expected |
|---------|-----|----------|
| Frontend | http://localhost:3000 | React app loads |
| Backend | http://localhost:8000/docs | API docs page |
| Health | http://localhost:8000/health | `{"status":"healthy"}` |

---

## Running an Election

### Step 1: Setup Trustees
Open http://localhost:3000, go to the **Testing** tab, click **Setup Trustees**. Wait for the success message.

### Step 2: Generate Test Votes
Click **Generate 100 Mock Votes**. Wait about 20 seconds (encryption is slow with 2048-bit keys). Success message appears when done.

### Step 3: Generate Ballots
Click **Generate 100 Mock Ballots**. Wait for success.

### Step 4: Aggregate Votes
Click **Tally Ballots**. Votes are aggregated using homomorphic encryption.

### Step 5: Start Tallying
Click **Start Tallying Process**. This prepares the data for trustee decryption.

### Step 6: Trustee Decryption
Go to the **Trustees** tab. Click **Decrypt** for any 3 of the 5 trustees. Each click performs a partial decryption (progress: 1/3, 2/3, 3/3). Optionally click **Show Cryptographic Process Visualization** to see the workflow.

### Step 7: Finalize Results
Return to the **Testing** tab. Click **Finalize Tally on Blockchain**. Results are computed and published.

### Step 8: View Results
Go to the **Results** tab. See vote distribution, winner, and blockchain transaction hash.

---

## Manual QA Tests

### Test 1: Basic Voter Login (No MFA)

1. Open http://localhost:3000
2. Select Role as **Voter**
3. Enter credential: `voter1` (valid: `voter1` through `voter5`)
4. Click **Login**

**Expected:** Logged in immediately with no MFA prompt. Role shows as "voter" in the top bar. Tabs visible: Voter Access, Results, Ledger, Verification.

### Test 2: Voter Access Dashboard

1. After logging in as `voter1`, click the **Voter Access** tab
2. Dashboard loads directly — no separate login screen

**Expected:** Shows "Logged in as" with Security Settings and Election Actions sections. The **Enable 2FA Protection** button is visible.

### Test 3: Enable 2FA

1. In the Voter Access dashboard, click **Enable 2FA Protection**
2. A secret key and provisioning URI appear
3. Copy the secret key
4. Enter the 6-digit OTP from your authenticator app (or generate via CLI — see below)
5. Click **Activate 2FA**

```bash
docker exec evoting_backend python -c "import pyotp; print(pyotp.TOTP('YOUR_SECRET_HERE').now())"
```

**Expected:** Message says "MFA Setup Complete: MFA Enabled". A new token is issued automatically.

### Test 4: Re-Login with 2FA

1. Click **Logout**
2. Select Voter, enter `voter1`, click **Login**
3. An OTP verification screen appears
4. Enter the 6-digit code, click **Verify**

**Expected:** After credentials you see the OTP screen. After a valid OTP you are fully logged in.

| Problem | Cause | Fix |
|---------|-------|-----|
| Shows "mfa_pending" as role | Stale localStorage | Clear browser localStorage and retry |
| "Invalid OTP" error | OTP expired (30 s window) | Generate a fresh OTP immediately |
| Stuck on login screen | Backend unreachable | Check `docker-compose ps`, restart if needed |

### Test 5: Voter Access with 2FA Active

1. After MFA login, click the **Voter Access** tab

**Expected:** Dashboard loads directly. Security Settings shows MFA is already active.

### Test 6: Full Voting Flow

1. Log in as `voter1`
2. Go to **Voter Access** → click **Check Eligibility** → confirm "Eligible" badge
3. Click **Get Blind Credential** → credential issued with signature
4. In the Voting Booth, select a candidate (e.g., Alice Johnson)
5. Click **Review and Encrypt** → review → **Confirm and Submit**

**Expected:** "Vote Submitted" confirmation with receipt hash and timestamp.

### Test 7: Admin Login

1. Log out, select **Admin**, enter credential `admin`, click **Login**

**Expected:** All tabs visible: Results, Ledger, Trustees, Testing, Ops and Audit, Verification, Security Lab.

### Test 8: Other Role Logins

| Role | Credential | Expected Tabs |
|------|------------|---------------|
| Trustee | `trustee` | Trustees, Results, Ledger, Verification |
| Auditor | `auditor` | Results, Ledger, Ops and Audit, Verification |

---

## Common Commands

### Docker
```bash
docker-compose up -d              # Start all services
docker-compose down                # Stop all services
docker-compose down -v             # Full cleanup (removes database)
docker-compose logs -f             # View logs
docker-compose restart backend     # Restart a single service
```

### Reset Database
```bash
curl -X POST "http://localhost:8000/api/mock/reset-database?confirm=true"
```
Or click **Reset Database** in the Testing tab.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Action Failed" on Generate Votes | Wait 20 seconds — encryption is slow. Do not double-click. |
| "Key Mismatch" error | Reset the database and start from Step 1. |
| "Decrypt" button disabled | Complete Steps 1–5 first. |
| No results showing | Ensure 3 trustees have decrypted, then click Finalize. |
| Containers not starting | `docker-compose down -v` then `docker-compose up -d --build` |

---

## API Quick Reference

### Mock Data
```bash
curl -X POST "http://localhost:8000/api/mock/generate-votes?count=100"
curl -X POST "http://localhost:8000/api/mock/setup-trustees"
curl -X POST "http://localhost:8000/api/mock/reset-database?confirm=true"
```

### Tallying
```bash
curl -X POST "http://localhost:8000/api/tally/start" \
  -H "Content-Type: application/json" \
  -d '{"election_id": "YOUR_ELECTION_ID"}'

curl -X POST "http://localhost:8000/api/tally/partial-decrypt/{trustee_id}?election_id={election_id}"

curl -X POST "http://localhost:8000/api/tally/finalize" \
  -H "Content-Type: application/json" \
  -d '{"election_id": "YOUR_ELECTION_ID"}'
```

### Results
```bash
curl "http://localhost:8000/api/results/{election_id}"
```

---

## File Locations

| Purpose | Location |
|---------|----------|
| Frontend code | frontend/src/ |
| Backend code | backend/app/ |
| API routes | backend/app/routers/ |
| Business logic | backend/app/services/ |
| Database models | backend/app/models/ |
| Tests | backend/tests/ |
| Documentation | docs/ |

---

## Development Setup

### Frontend
```bash
cd frontend
npm install
npm start
```

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Running Tests
```bash
cd backend
python run_all_tests.py
# Or individually:
pytest tests/test_epic4.py -v
```
