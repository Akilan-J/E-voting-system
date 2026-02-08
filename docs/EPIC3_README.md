# Epic 3: Immutable Vote Ledger - Team Integration Guide

## Quick Start (5 Minutes)

### 1. Start the System
```bash
# From project root
docker-compose up -d

# Wait ~30 seconds for containers to start
# Backend will be at: http://localhost:8000
# Frontend will be at: http://localhost:3000
```

### 2. Verify It's Running
```bash
# Check API health
curl http://localhost:8000/health

# View API documentation
# Open in browser: http://localhost:8000/docs
```

### 3. Test the Ledger
```bash
# Generate 5 mock votes (they auto-submit to ledger)
curl -X POST "http://localhost:8000/api/mock/generate-votes?count=5"

# Propose a block
curl -X POST "http://localhost:8000/api/ledger/propose"

# Approve the block (height=1)
curl -X POST "http://localhost:8000/api/ledger/approve?height=1"

# Finalize the block
curl -X POST "http://localhost:8000/api/ledger/finalize?height=1"

# View blocks
curl http://localhost:8000/api/ledger/blocks
```

### 4. View in Frontend
Open `http://localhost:3000` → Click **"🔗 Ledger"** tab

---

## What is Epic 3?

A **blockchain ledger** that makes votes **immutable** and **auditable**. Every vote is cryptographically hashed and stored in blocks that cannot be altered once committed.

**Key Benefits:**
- ✅ Tamper-proof vote records
- ✅ Public verification without revealing votes
- ✅ Cryptographic proof of inclusion (Merkle trees)
- ✅ BFT consensus for reliability

---

## API Endpoints for Integration

### Base URL
```
http://localhost:8000/api/ledger
```

### 1. Submit Vote Entry (Auto-called by Mock Data)
**Endpoint:** `POST /api/ledger/submit`

**Purpose:** Add a vote to the ledger (creates pending entry)

**Request Body:**
```json
{
  "election_id": "uuid-here",
  "vote_id": "uuid-here",
  "ciphertext": "encrypted-vote-data"
}
```

**Response:**
```json
{
  "entry_hash": "abc123...",
  "status": "pending"
}
```

**Integration Note:** Call this after creating an encrypted vote in your voting module.

---

### 2. List Blocks (Read-Only)
**Endpoint:** `GET /api/ledger/blocks`

**Purpose:** Get all committed blocks

**Query Parameters:**
- `election_id` (optional): Filter by election
- `limit` (optional, default=100): Max blocks to return

**Response:**
```json
[
  {
    "height": 1,
    "timestamp": "2026-01-31T14:00:00",
    "prev_hash": "genesis-hash...",
    "merkle_root": "root-hash...",
    "block_hash": "block-hash...",
    "entry_count": 5,
    "commit_cert_hash": "quorum-cert..."
  }
]
```

**Integration Note:** Use this to display blockchain status in dashboards.

---

### 3. Get Merkle Proof (Verification)
**Endpoint:** `GET /api/ledger/proof/{entry_hash}`

**Purpose:** Get cryptographic proof that a vote exists in the ledger

**Response:**
```json
{
  "entry_hash": "abc123...",
  "block_height": 1,
  "leaf_index": 2,
  "merkle_path": ["hash1", "hash2", "hash3"],
  "merkle_root": "root-hash..."
}
```

**Integration Note:** Use this for voter receipt verification - voters can verify their vote was recorded without revealing content.

---

### 4. Verify Chain Integrity
**Endpoint:** `GET /api/ledger/verify-chain`

**Purpose:** Validate entire blockchain (checks all hashes and links)

**Query Parameters:**
- `election_id` (optional): Verify specific election's chain

**Response:**
```json
{
  "valid": true,
  "blocks_verified": 10,
  "last_height": 9
}
```

**Integration Note:** Run this before tallying to ensure data integrity.

---

### 5. Propose Block (Consensus - Step 1)
**Endpoint:** `POST /api/ledger/propose`

**Purpose:** Create a new block from pending entries

**Query Parameters:**
- `election_id` (optional)
- `max_entries` (optional, default=1000)

**Response:**
```json
{
  "height": 2,
  "block_hash": "new-block-hash...",
  "entry_count": 15,
  "status": "proposed"
}
```

**Integration Note:** Call this periodically (e.g., every 5 minutes) or when entry count reaches threshold.

---

### 6. Approve Block (Consensus - Step 2)
**Endpoint:** `POST /api/ledger/approve`

**Purpose:** Sign a proposed block (BFT node approval)

**Query Parameters:**
- `height` (required): Block height to approve
- `election_id` (optional)

**Response:**
```json
{
  "node_id": "node-1",
  "signature": "signature-hash...",
  "approvals_count": 2,
  "quorum_needed": 3
}
```

**Integration Note:** In production, different nodes call this. For demo, call 3 times to reach quorum.

---

### 7. Finalize Block (Consensus - Step 3)
**Endpoint:** `POST /api/ledger/finalize`

**Purpose:** Commit block permanently (requires quorum)

**Query Parameters:**
- `height` (required): Block height to finalize
- `election_id` (optional)

**Response:**
```json
{
  "height": 2,
  "committed": true,
  "commit_cert_hash": "quorum-cert-hash...",
  "timestamp": "2026-01-31T14:05:00"
}
```

**Integration Note:** Call after approvals reach quorum (2f+1). Block becomes immutable.

---

### 8. Node Health Check
**Endpoint:** `GET /api/ledger/node/health`

**Purpose:** Check ledger node status

**Response:**
```json
{
  "node_id": "node-1",
  "status": "healthy",
  "last_block_height": 5,
  "pending_entries": 3
}
```

---

### 9. Create Snapshot (Maintenance)
**Endpoint:** `POST /api/ledger/snapshot/create`

**Purpose:** Create ledger state checkpoint

**Query Parameters:**
- `height` (required): Block height for snapshot
- `election_id` (optional)

**Response:**
```json
{
  "snapshot_hash": "snapshot-hash...",
  "height": 10,
  "status": "created"
}
```

**Integration Note:** Use for backup/recovery. Create snapshots before major operations.

---

### 10. Prune Old Data (Maintenance)
**Endpoint:** `POST /api/ledger/prune`

**Purpose:** Remove old ciphertext (keeps hashes for verification)

**Query Parameters:**
- `height_threshold` (required): Prune entries before this height
- `election_id` (optional)

**Response:**
```json
{
  "pruned_entries": 50,
  "height_threshold": 5,
  "policy": "Pruned payloads before height 5"
}
```

**Integration Note:** Run after election ends to save storage. Verification still works.

---

## Integration Workflow

### For Voting Module Team
```
1. User casts vote
2. Encrypt vote → store in encrypted_votes table
3. Call POST /api/ledger/submit with vote_id and ciphertext
4. Return receipt with entry_hash to voter
```

### For Tallying Module Team
```
1. Before tallying, call GET /api/ledger/verify-chain
2. If valid=true, proceed with tallying
3. After tallying, optionally create snapshot
```

### For Results Module Team
```
1. Display block count from GET /api/ledger/blocks
2. Show "Verified on Blockchain" badge if entry exists
3. Provide "Verify My Vote" feature using GET /api/ledger/proof/{entry_hash}
```

### For Admin Dashboard Team
```
1. Show real-time stats from GET /api/ledger/node/health
2. Display latest blocks from GET /api/ledger/blocks?limit=5
3. Trigger consensus manually:
   - POST /api/ledger/propose
   - POST /api/ledger/approve (3x)
   - POST /api/ledger/finalize
```

---

## Database Tables (For Direct Queries)

If you need to query the database directly:

### `ledger_blocks`
- `height` - Block number (0 = genesis)
- `block_hash` - Unique block identifier
- `prev_hash` - Links to previous block
- `merkle_root` - Root of Merkle tree
- `committed` - Boolean (true = finalized)
- `election_id` - Optional election filter

### `ledger_entries`
- `entry_hash` - Unique vote identifier
- `vote_id` - References encrypted_votes table
- `block_height` - Which block contains this entry
- `ciphertext_hash` - Hash of encrypted vote (nullable after pruning)

### `ledger_approvals`
- `height` - Block being approved
- `node_id` - Approving node
- `signature` - Cryptographic signature

---

## Configuration

### Environment Variables
Add to `.env` file:
```bash
LEDGER_MODE=bft              # Consensus mode
LEDGER_NODE_ID=node-1        # This node's identifier
LEDGER_F=1                   # Byzantine fault tolerance
LEDGER_N=4                   # Total nodes (n = 3f+1)
```

### Quorum Calculation
- **Quorum = 2f + 1**
- Default: f=1, so quorum=3 approvals needed
- Simulates 4-node BFT network

---

## Testing

### Run Unit Tests
```bash
docker-compose exec backend python -m pytest tests/test_ledger.py -v
```

### Manual Testing Workflow
```bash
# 1. Generate votes
curl -X POST "http://localhost:8000/api/mock/generate-votes?count=10"

# 2. Propose block
curl -X POST "http://localhost:8000/api/ledger/propose"

# 3. Approve 3 times (reach quorum)
curl -X POST "http://localhost:8000/api/ledger/approve?height=1"
curl -X POST "http://localhost:8000/api/ledger/approve?height=1"
curl -X POST "http://localhost:8000/api/ledger/approve?height=1"

# 4. Finalize
curl -X POST "http://localhost:8000/api/ledger/finalize?height=1"

# 5. Verify
curl "http://localhost:8000/api/ledger/verify-chain"
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Frontend (React)                    │
│              LedgerExplorer Component                │
└───────────────────┬─────────────────────────────────┘
                    │ GET /api/ledger/blocks
                    ▼
┌─────────────────────────────────────────────────────┐
│              Backend (FastAPI)                       │
│  ┌──────────────────────────────────────────────┐  │
│  │  Router (ledger.py)                          │  │
│  │  - 10 REST endpoints                         │  │
│  └────────────────┬─────────────────────────────┘  │
│                   ▼                                  │
│  ┌──────────────────────────────────────────────┐  │
│  │  LedgerService (ledger_service.py)           │  │
│  │  - BFT consensus logic                       │  │
│  │  - Merkle tree construction                  │  │
│  │  - Chain verification                        │  │
│  └────────────────┬─────────────────────────────┘  │
│                   ▼                                  │
│  ┌──────────────────────────────────────────────┐  │
│  │  Database Models (ledger_models.py)          │  │
│  │  - 7 SQLAlchemy tables                       │  │
│  └──────────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────────┘
                    ▼
        ┌───────────────────────┐
        │   PostgreSQL          │
        │   (ledger_* tables)   │
        └───────────────────────┘
```

---

## Files Created for Epic 3

### Backend
- `backend/app/models/blockchain.py` - Pydantic DTOs
- `backend/app/models/ledger_models.py` - Database schema
- `backend/app/services/ledger_service.py` - Core logic
- `backend/app/routers/ledger.py` - API endpoints
- `backend/tests/test_ledger.py` - Unit tests

### Frontend
- `frontend/src/components/LedgerExplorer.js` - Blockchain viewer

### Configuration
- Updated `backend/app/main.py` - Registered router
- Updated `.env.example` - Added ledger variables

---

## Common Issues & Solutions

### Issue: "No blocks found"
**Solution:** Run the test workflow above to create genesis + first block

### Issue: "Quorum not met"
**Solution:** Call `/approve` endpoint 3 times (or 2f+1 times based on config)

### Issue: "Chain verification failed"
**Solution:** Database may be corrupted. Reset with:
```bash
docker-compose exec backend python -c "from app.models.database import engine, Base; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"
```

### Issue: "Ledger endpoints not showing in Swagger"
**Solution:** Restart backend container:
```bash
docker-compose restart backend
```

---

## Security Notes

⚠️ **For Production Deployment:**
- Replace simulated private keys with HSM
- Deploy multiple physical nodes (not single DB)
- Add network layer (gRPC/TLS) between nodes
- Implement proper access control on write endpoints
- Enable audit logging for all operations

---

## Support

**Questions?** Check:
1. Swagger docs: `http://localhost:8000/docs`
2. Test file: `backend/tests/test_ledger.py`
3. Service code: `backend/app/services/ledger_service.py`

**Need Help?** Contact the Epic 3 team member who implemented this feature.

## Overview
A permissioned BFT (Byzantine Fault Tolerant) blockchain ledger for ensuring vote immutability and auditability in the e-voting system. Votes are cryptographically hashed and stored in an append-only chain with Merkle tree verification.

## Architecture

### Backend Components
- **Models** (`backend/app/models/`)
  - `blockchain.py` - Pydantic DTOs for API validation
  - `ledger_models.py` - SQLAlchemy database schema (7 tables)

- **Service** (`backend/app/services/ledger_service.py`)
  - BFT consensus simulation (Propose → Approve → Finalize)
  - Merkle tree construction for entry verification
  - Chain integrity validation
  - Snapshot and pruning operations

- **Router** (`backend/app/routers/ledger.py`)
  - REST API endpoints for ledger operations

### Frontend Component
- **LedgerExplorer** (`frontend/src/components/LedgerExplorer.js`)
  - Visual blockchain explorer
  - Real-time block display with auto-refresh

## Key Features

### 1. Blockchain Structure
- **Genesis Block** (Height 0) - Automatically created per election
- **Linked Blocks** - Each block references previous via `prev_hash`
- **Merkle Trees** - Efficient proof of entry inclusion
- **Deterministic Hashing** - SHA-256 for all cryptographic operations

### 2. BFT Consensus
- **Quorum**: 2f+1 approvals required (default: 3 of 4 nodes)
- **Phases**:
  1. **Propose** - Leader creates block from pending entries
  2. **Approve** - Nodes sign block hash
  3. **Finalize** - Commit when quorum reached

### 3. Data Integrity
- **Chain Verification** - Validates all block links and hashes
- **Merkle Proofs** - Verify individual entries without full chain
- **Immutability** - Committed blocks cannot be altered

### 4. Maintenance
- **Snapshots** - Point-in-time ledger state for recovery
- **Pruning** - Remove old ciphertext while preserving hashes

## API Endpoints

### Read Operations
```
GET  /api/ledger/blocks              # List all blocks
GET  /api/ledger/proof/{entry_hash}  # Get Merkle proof
GET  /api/ledger/verify-chain        # Verify integrity
GET  /api/ledger/node/health         # Node status
```

### Write Operations
```
POST /api/ledger/submit              # Submit vote entry
POST /api/ledger/propose             # Propose new block
POST /api/ledger/approve             # Approve block
POST /api/ledger/finalize            # Commit block
```

### Maintenance
```
POST /api/ledger/snapshot/create     # Create snapshot
POST /api/ledger/prune               # Prune old data
```

## Database Schema

### Core Tables
- `ledger_blocks` - Blockchain headers
- `ledger_entries` - Vote entries (Merkle leaves)
- `ledger_approvals` - BFT node signatures
- `ledger_nodes` - Consensus participants

### Auxiliary Tables
- `ledger_snapshots` - State checkpoints
- `ledger_events` - Audit trail
- `ledger_pruning` - Pruning records

## Configuration

Environment variables (`.env`):
```bash
LEDGER_MODE=bft              # Consensus mode
LEDGER_NODE_ID=node-1        # This node's ID
LEDGER_F=1                   # Byzantine fault tolerance (f)
LEDGER_N=4                   # Total nodes (n = 3f+1)
```

## Usage Example

### 1. Generate Mock Votes
```bash
POST /api/mock/generate-votes?count=5
```

### 2. Run Consensus
```bash
# Propose block
POST /api/ledger/propose

# Approve (repeat for quorum)
POST /api/ledger/approve?height=1

# Finalize
POST /api/ledger/finalize?height=1
```

### 3. Verify Chain
```bash
GET /api/ledger/verify-chain
# Response: {"valid": true, "blocks_verified": 2}
```

### 4. View in Frontend
Navigate to `http://localhost:3000` → Click "🔗 Ledger" tab

## Testing

Run unit tests:
```bash
docker-compose exec backend python -m pytest tests/test_ledger.py
```

Tests cover:
- SHA-256 hashing
- Merkle tree construction
- Genesis block creation
- Block proposal logic

## Files Created for Epic 3

### Backend
- `backend/app/models/blockchain.py`
- `backend/app/models/ledger_models.py`
- `backend/app/services/ledger_service.py`
- `backend/app/routers/ledger.py`
- `backend/tests/test_ledger.py`

### Frontend
- `frontend/src/components/LedgerExplorer.js`

### Configuration
- Updated `.env.example` with ledger variables
- Updated `backend/app/main.py` to register ledger router

## Technical Notes

### Why PostgreSQL Instead of Ganache?
- **Simpler deployment** - No separate blockchain container
- **Better integration** - Direct SQL queries for analytics
- **Sufficient for demo** - BFT simulation meets requirements
- **Faster builds** - Removed heavy `web3` dependency

### Security Considerations
- Private keys are simulated (use HSM in production)
- Single-node demo (deploy multiple nodes for real BFT)
- No network layer (nodes communicate via shared DB)

## Future Enhancements
- Multi-node deployment with gRPC
- Hardware security module (HSM) integration
- Advanced Merkle proof visualization
- Real-time WebSocket updates for new blocks
