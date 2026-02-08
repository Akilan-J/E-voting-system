# E-Voting System - Usage Guide

A step-by-step guide to start and use the e-voting system.

---

## Getting Started

### Prerequisites
- Docker Desktop installed and running
- 8GB RAM minimum
- These ports must be free: 3000, 8000, 5432, 6379, 8545

### Start the System

```bash
# Navigate to project folder
cd E-voting-system

# Start all containers
docker-compose up -d

# Wait 30 seconds for initialization
# Check all containers are running
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
1. Open http://localhost:3000
2. Go to **Testing** tab
3. Click **"Setup Trustees"**
4. Wait for success message

### Step 2: Generate Test Votes
1. Click **"Generate 100 Mock Votes"**
2. Wait 20 seconds (encryption takes time)
3. Success message appears

### Step 3: Generate Ballots
1. Click **"Generate 100 Mock Ballots"**
2. Wait for success

### Step 4: Aggregate Votes
1. Click **"Tally Ballots"**
2. Votes are aggregated using homomorphic encryption

### Step 5: Start Tallying
1. Click **"Start Tallying Process"**
2. This prepares for trustee decryption

### Step 6: Trustee Decryption
1. Go to **Trustees** tab
2. Click **"Decrypt"** for any 3 trustees
3. Each click does a partial decryption
4. Watch progress: 1/3 → 2/3 → 3/3
5. (Optional) Click **"Show Cryptographic Process Visualization"** at the bottom to see the workflow in detail

### Step 7: Finalize Results
1. Return to **Testing** tab
2. Click **"Finalize Tally on Blockchain"**
3. Results are computed and published

### Step 8: View Results
1. Go to **Results** tab
2. See vote distribution and winner
3. Blockchain transaction hash shown

---

## Common Commands

### Docker Commands
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart a service
docker-compose restart backend
docker-compose restart frontend

# Full reset (deletes database)
docker-compose down -v
docker-compose up -d
```

### Reset Database
```bash
curl -X POST "http://localhost:8000/api/mock/reset-database?confirm=true"
```

Or click **"Reset Database"** in the Testing tab.

---

## Troubleshooting

### "Action Failed" on Generate Votes
- Wait 20 seconds - encryption is slow
- Don't click multiple times

### "Key Mismatch" Error
- Reset the database
- Start workflow from Step 1
- Click each button only once

### "Decrypt" Button Disabled
- Complete Steps 1-5 first
- Make sure tallying started

### No Results Showing
- Ensure 3 trustees decrypted
- Click "Finalize Tally"

### Containers Not Starting
```bash
docker-compose down -v
docker-compose up -d --build
```

---

## API Quick Reference

### Mock Data
```bash
# Generate votes
curl -X POST "http://localhost:8000/api/mock/generate-votes?count=100"

# Setup trustees
curl -X POST "http://localhost:8000/api/mock/setup-trustees"

# Reset database
curl -X POST "http://localhost:8000/api/mock/reset-database?confirm=true"
```

### Tallying
```bash
# Start tallying
curl -X POST "http://localhost:8000/api/tally/start" \
  -H "Content-Type: application/json" \
  -d '{"election_id": "YOUR_ELECTION_ID"}'

# Partial decrypt
curl -X POST "http://localhost:8000/api/tally/partial-decrypt/{trustee_id}?election_id={election_id}"

# Finalize
curl -X POST "http://localhost:8000/api/tally/finalize" \
  -H "Content-Type: application/json" \
  -d '{"election_id": "YOUR_ELECTION_ID"}'
```

### Results
```bash
# Get results
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
pytest tests/ -v
```
