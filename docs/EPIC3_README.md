# Epic 3 - Immutable Vote Ledger

## Overview

Epic 3 implements a blockchain-style ledger that stores encrypted votes in an immutable, auditable chain. Every vote submitted to the system is hashed and stored in blocks that cannot be tampered with once committed. The ledger uses Merkle trees for efficient verification and a BFT consensus simulation for block finalization.

---

## Quick Start

### Starting the system

```bash
docker-compose up -d
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

### Testing the ledger manually

```bash
# Generate some mock votes
curl -X POST "http://localhost:8000/api/mock/generate-votes?count=5"

# Propose a block from pending entries
curl -X POST "http://localhost:8000/api/ledger/propose"

# Approve the block (call 3 times to reach quorum)
curl -X POST "http://localhost:8000/api/ledger/approve?height=1"

# Finalize the block
curl -X POST "http://localhost:8000/api/ledger/finalize?height=1"

# View committed blocks
curl http://localhost:8000/api/ledger/blocks
```

The frontend has a Ledger tab where you can browse blocks visually.

---

## API Endpoints

Base URL: `http://localhost:8000/api/ledger`

### POST /submit
Add a vote entry to the ledger (creates a pending entry). Called automatically when votes are cast.

Request body:
```json
{
  "election_id": "uuid",
  "vote_id": "uuid",
  "ciphertext": "encrypted-vote-data"
}
```

### GET /blocks
List all committed blocks. Optional query params: `election_id`, `limit` (default 100).

### GET /proof/{entry_hash}
Get a Merkle proof for a specific vote entry. Used for voter receipt verification — voters can check that their vote was recorded without revealing what they voted for.

### GET /verify-chain
Validate the entire blockchain by checking all hashes and links. Returns `valid: true/false` with block count. Run this before tallying to make sure nothing was tampered with.

### POST /propose
Create a new block from pending entries. Call this periodically or when enough votes accumulate.

### POST /approve
Sign a proposed block (BFT node approval). Query param: `height` (required). In production this would be called by different nodes; for the demo, call it 3 times to reach quorum.

### POST /finalize
Commit a block permanently after quorum is reached. Query param: `height` (required).

### GET /node/health
Check ledger node status — current block height, pending entry count.

### POST /snapshot/create
Create a ledger state checkpoint at a given block height. Useful for backup before major operations.

### POST /prune
Remove old ciphertext data below a given height threshold. Hashes are preserved so verification still works, but storage is reduced.

---

## Integration with Other Modules

### For the voting module
After encrypting a vote, call POST /api/ledger/submit with the vote_id and ciphertext. Return the entry_hash to the voter as a receipt.

### For the tallying module
Before starting the tally, call GET /api/ledger/verify-chain. Proceed only if valid is true.

### For the results module
Use GET /api/ledger/blocks to show blockchain status. Use GET /api/ledger/proof/{entry_hash} for the "verify my vote" feature.

---

## Consensus

The ledger simulates a 4-node BFT network. Quorum is calculated as 2f+1, where f=1 (one Byzantine fault tolerated), so 3 approvals are needed.

The flow is: Propose -> Approve (x3) -> Finalize. Once finalized, a block is immutable.

Configuration via environment variables:
```
LEDGER_MODE=bft
LEDGER_NODE_ID=node-1
LEDGER_F=1
LEDGER_N=4
```

---

## Database Tables

| Table | Key columns | Purpose |
|-------|-------------|---------|
| ledger_blocks | height, block_hash, prev_hash, merkle_root, committed | Block storage, height 0 is genesis |
| ledger_entries | entry_hash, vote_id, block_height, ciphertext_hash | Individual vote entries |
| ledger_approvals | height, node_id, signature | Node approval records |

---

## Block Validation (US-40)

Blocks go through several checks before they can be committed:
- Signature verification (blocks are signed by nodes)
- Size limits (10MB max, 10000 entries per block)
- Structure validation (height must be monotonically increasing, hash linkage must be correct, Merkle roots are recomputed and compared)

### Rate limiting (US-45)

Public read endpoints like GET /blocks are rate-limited to 100 requests per minute to prevent abuse.

---

## Files

### Backend
- backend/app/models/blockchain.py - Pydantic DTOs
- backend/app/models/ledger_models.py - SQLAlchemy database schema (7 tables)
- backend/app/services/ledger_service.py - Core logic (BFT consensus, Merkle tree, chain verification)
- backend/app/routers/ledger.py - REST API endpoints
- backend/tests/test_ledger.py - Unit tests

### Frontend
- frontend/src/components/LedgerExplorer.js - Block browser component

---

## Running Tests

```bash
cd backend
pytest tests/test_ledger.py -v
pytest tests/test_epic3_enhancements.py -v
```

test_ledger.py covers: hashing, Merkle tree construction, genesis block creation, digital signatures, block validation.

test_epic3_enhancements.py covers: config loading, signature generation and verification, block structure validation.

---

## Common Issues

**No blocks found** - The system starts empty. Generate mock votes and run the consensus workflow (propose, approve x3, finalize) to create the first block.

**Quorum not met** - You need to call the approve endpoint 3 times (or 2f+1 based on config).

**Chain verification failed** - The database may have been corrupted. Reset by dropping and recreating tables, or use docker-compose down -v to start fresh.

---

## Production Notes

For a real deployment, the following would need to change:
- Replace simulated private keys with HSM-backed keys
- Deploy actual separate nodes instead of a single-database simulation
- Add gRPC/TLS between nodes
- Implement proper access control on write endpoints
- Enable persistent audit logging for all operations
