# Epic 4: Privacy-Preserving Tallying & Result Verification

**Module Owner:** Kapil  
**Status:** 80% Complete  
**Integration:** Fully integrated with Epic 3 (Ledger)

---

## Overview

Epic 4 implements the core cryptographic voting system using **homomorphic encryption** for privacy-preserving vote tallying and **threshold cryptography** for secure result decryption.

---

## Module Structure

```
Epic 4 Components:
├── Backend Services
│   ├── encryption.py      - Paillier homomorphic encryption
│   ├── tallying.py        - Vote aggregation and result computation
│   └── threshold_crypto.py - Shamir's Secret Sharing (3-of-5)
│
├── Backend Routers (API)
│   ├── tallying.py        - Start/finalize tallying endpoints
│   ├── trustees.py        - Trustee management endpoints
│   └── results.py         - Result retrieval endpoints
│
├── Frontend Components
│   ├── TestingPanel.jsx   - Testing workflow UI
│   ├── TrusteePanel.jsx   - Trustee decryption UI
│   └── ResultsDashboard.jsx - Results display UI
│
└── Unit Tests
    └── test_epic4.py      - Pytest unit tests
```

---

## Features Implemented

### 1. Homomorphic Encryption (Paillier)
- 2048-bit key generation
- Vote encryption without revealing content
- Encrypted vote aggregation (addition in ciphertext space)
- Secure decryption

### 2. Threshold Cryptography
- 3-of-5 Shamir's Secret Sharing
- Key share distribution to trustees
- Collaborative decryption (no single point of failure)

### 3. Vote Tallying
- Encrypted ballot aggregation
- Partial decryption by trustees
- Final result computation

### 4. Result Verification
- Merkle tree for ballot integrity
- Zero-knowledge proofs for correct decryption
- Blockchain publication for immutability

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tally/start` | POST | Begin tallying process |
| `/api/tally/partial-decrypt/{trustee_id}` | POST | Trustee partial decryption |
| `/api/tally/finalize` | POST | Compute final results |
| `/api/tally/status/{election_id}` | GET | Get tallying status |
| `/api/trustees` | GET | List all trustees |
| `/api/results/{election_id}` | GET | Get election results |

---

## Integration Points

### With Epic 3 (Ledger)
- Votes are submitted to the ledger after encryption
- Results are published to blockchain after finalization
- Merkle roots verify vote integrity

### With Epic 2 (Voter Access)
- Receives encrypted votes from voters
- Validates vote format before tallying

---

## Testing

### Running Unit Tests
```bash
cd backend
pytest tests/test_epic4.py -v
```

### Test Coverage
- Encryption/decryption operations
- Vote aggregation
- Threshold key sharing
- Partial decryption flow
- Result computation

---

## Key Files Reference

| File | Location | Purpose |
|------|----------|---------|
| encryption.py | backend/app/services/ | Paillier cryptosystem implementation |
| tallying.py | backend/app/services/ | Core tallying business logic |
| threshold_crypto.py | backend/app/services/ | Key splitting and reconstruction |
| tallying.py | backend/app/routers/ | Tallying API endpoints |
| trustees.py | backend/app/routers/ | Trustee management API |
| results.py | backend/app/routers/ | Results retrieval API |
| TrusteePanel.jsx | frontend/src/components/ | Trustee decryption UI |
| ResultsDashboard.jsx | frontend/src/components/ | Results display UI |
| TestingPanel.jsx | frontend/src/components/ | Testing workflow UI |

---

## Known Issues & Fixes

### Issue 1: Key Mismatch Error
**Problem:** "encrypted_number was encrypted against a different key"  
**Cause:** Trustees generated separate keys instead of sharing election key  
**Fix:** Modified `setup_trustees` to use election's keypair

### Issue 2: Request Timeout  
**Problem:** Vote generation showing "Action Failed"  
**Cause:** 10-second timeout was too short for 100 vote encryption  
**Fix:** Increased API timeout to 60 seconds

### Issue 3: Private Key Not Loaded  
**Problem:** Partial decryption failing  
**Cause:** Private key not loaded before decryption  
**Fix:** Added key loading in partial_decrypt function

---

## Security Considerations

- Private keys are split using Shamir's Secret Sharing
- No single trustee can decrypt results alone
- All operations are logged for audit
- Results are cryptographically verified before publication

---

## Dependencies

```
phe==1.5.0          # Paillier homomorphic encryption
secretsharing       # Shamir's Secret Sharing
cryptography        # General crypto utilities
pytest              # Unit testing
```

---

## Workflow Diagram

```
          [Voter Casts Vote]
                 │
                 ▼
        [Vote Encrypted (Paillier)]
                 │
                 ▼
        [Stored in Database + Ledger]
                 │
                 ▼
        [Start Tallying Process]
                 │
                 ▼
   [Homomorphic Aggregation E(v1)×E(v2)×...]
                 │
                 ▼
    ┌──────────────────────────┐
    │ Trustee 1 Partial Decrypt │
    │ Trustee 2 Partial Decrypt │
    │ Trustee 3 Partial Decrypt │
    └──────────────────────────┘
                 │
                 ▼
        [Combine 3 Partial Results]
                 │
                 ▼
          [Final Tally Revealed]
                 │
                 ▼
      [Publish to Blockchain]
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Jan 2026 | Initial implementation |
| 1.1.0 | Jan 2026 | Fixed key mismatch issues |
| 1.2.0 | Feb 2026 | Added unit tests, documentation |

## Actual Code Locations

Epic 4 code is integrated into the main project structure:

### Backend Services (backend/app/services/)
- `encryption.py` - Paillier homomorphic encryption
- `tallying.py` - Vote aggregation and result computation
- `threshold_crypto.py` - Shamir's Secret Sharing (3-of-5)

### Backend Routers (backend/app/routers/)
- `tallying.py` - Tallying API endpoints
- `trustees.py` - Trustee management
- `results.py` - Result retrieval and verification

### Frontend Components (frontend/src/components/)
- `TestingPanel.jsx` - Testing workflow UI
- `TrusteePanel.jsx` - Trustee decryption interface
- `ResultsDashboard.jsx` - Results display

### Unit Tests (backend/tests/)
- `test_epic4.py` - Pytest tests for Epic 4

## Documentation

See `/docs/EPIC4_README.md` for complete documentation.

## Quick Reference

| Feature | Status |
|---------|--------|
| Homomorphic Encryption | ✅ Complete |
| Threshold Crypto (3-of-5) | ✅ Complete |
| Vote Aggregation | ✅ Complete |
| Partial Decryption | ✅ Complete |
| Result Verification | ✅ Complete |
| Unit Tests | ✅ Complete |

## Testing

```bash
cd backend
pytest tests/test_epic4.py -v
```