# EPIC 5 - Verification and Audit Ops

This README documents only the EPIC 5 user stories that are implemented in this repo and how they are tested.

## Implemented user stories and endpoints

US-62 Receipt verification
- Endpoint: POST /api/verify/receipt
- Purpose: Verify receipt inclusion and return a Merkle proof
- Notes: Rate-limited; no login required

US-63 ZK proof verification
- Endpoint: POST /api/verify/zk-proof
- Purpose: Validate proof bundle against published results and ledger root

US-64 Ledger replay audit
- Endpoint: POST /api/security/replay-ledger
- Purpose: Verify ledger hash chain and Merkle roots

US-65 Transparency dashboard
- Endpoint: GET /api/ops/dashboard/{election_id}
- Purpose: Aggregate-only metrics for public visibility

US-66 Evidence package
- Endpoint: GET /api/ops/evidence/{election_id}
- Purpose: Download signed manifest and public artifacts

US-68 Threat simulation
- Endpoint: POST /api/security/simulate
- Auth: Admin or security engineer

US-69 and US-73 Anomaly detection
- Endpoint: GET /api/security/anomalies
- Report: GET /api/security/anomaly-report

US-70 Incident response
- Endpoints: /api/ops/incidents (GET, POST), /api/ops/incidents/{id} (PUT), /api/ops/incidents/{id}/actions (GET, POST), /api/ops/incidents/{id}/report (GET)
- Auth: Admin, auditor, or security engineer (see endpoint)

US-71 Dispute workflow
- Endpoints: /api/ops/disputes (GET, POST), /api/ops/disputes/{id} (PUT), /api/ops/disputes/{id}/actions (GET), /api/ops/disputes/{id}/report (GET)
- Auth: Admin or auditor

US-72 Compliance report
- Endpoint: GET /api/ops/compliance-report/{election_id}
- Auth: Admin or auditor

US-74 Replay timeline
- Endpoint: GET /api/security/replay-timeline

## Tests

The EPIC 5 test suite exercises only the implemented endpoints listed above.

- Test file: backend/tests/test_epic5_user_stories.py
- Run:
	- PYTHONPATH=backend pytest backend/tests/test_epic5_user_stories.py -v

## Auth notes for tests

Some endpoints require a JWT. The tests obtain an admin token via:

- POST /auth/login with payload: {"credential": "admin"}

The token is then sent as:

- Authorization: Bearer <token>

## Not implemented in this repo

The following EPIC 5 user stories are not implemented and are not covered by tests here: US-67, US-75, US-76.