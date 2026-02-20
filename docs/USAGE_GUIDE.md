# Usage Guide

A step-by-step guide to start and use the e-voting system.

---

## Getting Started

### Prerequisites
- Docker Desktop installed and running
- 8GB RAM minimum
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
| Health | http://localhost:8000/health | {"status":"healthy"} |

---

## Running an Election

### Step 1: Setup Trustees
Open http://localhost:3000, go to the Testing tab, click "Setup Trustees". Wait for the success message.

### Step 2: Generate Test Votes
Click "Generate 100 Mock Votes". Wait about 20 seconds (encryption is slow with 2048-bit keys). Success message appears when done.

### Step 3: Generate Ballots
Click "Generate 100 Mock Ballots". Wait for success.

### Step 4: Aggregate Votes
Click "Tally Ballots". Votes are aggregated using homomorphic encryption.

### Step 5: Start Tallying
Click "Start Tallying Process". This prepares the data for trustee decryption.

### Step 6: Trustee Decryption
Go to the Trustees tab. Click "Decrypt" for any 3 of the 5 trustees. Each click performs a partial decryption. Progress: 1/3, 2/3, 3/3. You can optionally click "Show Cryptographic Process Visualization" at the bottom to see the workflow in detail.

### Step 7: Finalize Results
Return to the Testing tab. Click "Finalize Tally on Blockchain". Results are computed and published.

### Step 8: View Results
Go to the Results tab. See vote distribution, winner, and blockchain transaction hash.

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
Or click "Reset Database" in the Testing tab.

---

## Troubleshooting

**"Action Failed" on Generate Votes** - Wait 20 seconds. Encryption takes time. Do not click multiple times.

**"Key Mismatch" error** - Reset the database and start from Step 1. Click each button only once.

**"Decrypt" button disabled** - Complete Steps 1-5 first.

**No results showing** - Make sure 3 trustees have decrypted, then click "Finalize Tally".

**Containers not starting** - Run `docker-compose down -v` then `docker-compose up -d --build`.

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
