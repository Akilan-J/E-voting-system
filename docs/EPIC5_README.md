# Epic 5 - Verification and Audit Operations

## Overview

Epic 5 covers the verification and operational audit layer of the e-voting system. It provides endpoints for voters to verify their receipts, for auditors to replay the ledger, and for security engineers to simulate threats and manage incidents.

---

## Implemented User Stories

### Verification endpoints (public-facing)

**US-62 Receipt verification**
- POST /api/verify/receipt
- Takes a receipt hash from a voter, checks inclusion in the ledger, and returns a Merkle proof. Rate-limited, no login required.

**US-63 Zero-knowledge proof verification**
- POST /api/verify/zk-proof
- Validates a proof bundle against published results and the ledger root. Confirms correct decryption without revealing trustee key shares.

**US-64 Ledger replay audit**
- POST /api/security/replay-ledger
- Replays the entire ledger hash chain and verifies all Merkle roots. Used by auditors to confirm the ledger has not been tampered with after the fact.

**US-65 Transparency dashboard**
- GET /api/ops/dashboard/{election_id}
- Returns aggregate-only metrics (total votes processed, blocks committed, system health) for public visibility. No individual vote data is exposed.

### Operations endpoints (admin/auditor access)

**US-66 Evidence package**
- GET /api/ops/evidence/{election_id}
- Downloads a signed manifest and public artifacts for external review.

**US-68 Threat simulation**
- POST /api/security/simulate
- Runs simulated attack scenarios (replay, tampering, etc.) and reports whether the system detects them. Requires admin or security_engineer role.

**US-69 and US-73 Anomaly detection**
- GET /api/security/anomalies - list detected anomalies
- GET /api/security/anomaly-report - generate a detailed anomaly report

**US-70 Incident response**
- GET/POST /api/ops/incidents - list or create incidents
- PUT /api/ops/incidents/{id} - update incident status
- GET/POST /api/ops/incidents/{id}/actions - view or add actions taken
- GET /api/ops/incidents/{id}/report - generate incident report
- Requires admin, auditor, or security_engineer role.

**US-71 Dispute workflow**
- GET/POST /api/ops/disputes - list or file disputes
- PUT /api/ops/disputes/{id} - update dispute status
- GET /api/ops/disputes/{id}/actions - view actions
- GET /api/ops/disputes/{id}/report - generate dispute report
- Requires admin or auditor role.

**US-72 Compliance report**
- GET /api/ops/compliance-report/{election_id}
- Generates a compliance report for a given election. Requires admin or auditor role.

**US-74 Replay timeline**
- GET /api/security/replay-timeline
- Returns a chronological timeline of all security-relevant events.

---

## Not Implemented

The following Epic 5 stories are not implemented in this repo: US-67, US-75, US-76.

---

## Authentication for Protected Endpoints

Some endpoints require a JWT. In tests, the admin token is obtained via:
```
POST /auth/login with payload: {"credential": "admin"}
```
The token is sent as: `Authorization: Bearer <token>`

---

## Tests

Test file: backend/tests/test_epic5_user_stories.py

```bash
cd backend
pytest tests/test_epic5_user_stories.py -v
```

Additional tests in:
- backend/tests/test_ops_stories.py (evidence, threat sim, incidents, anomalies)
- backend/tests/test_verification_stories.py (receipt, ZK proof, replay, transparency)

All tests use the FastAPI test client and do not require a running server.

---

## Files

| File | Purpose |
|------|---------|
| backend/app/routers/ops.py | Incident, dispute, compliance, evidence, dashboard endpoints |
| backend/app/routers/verification.py | Receipt verification, ZK proof validation |
| backend/app/routers/security.py | Threat simulation, anomaly detection, replay |
| backend/tests/test_epic5_user_stories.py | Combined Epic 5 endpoint tests |
| backend/tests/test_ops_stories.py | Ops-specific tests (US-66, 68, 70, 73) |
| backend/tests/test_verification_stories.py | Verification-specific tests (US-62-65) |
