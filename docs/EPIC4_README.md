# Epic 4 -- Secure Tally and Proofs

Module Owner: Kapil
Status: Complete
User Stories: US-47 through US-61

---

## Table of Contents

- [Overview](#overview)
- [Homomorphic Encryption](#homomorphic-encryption-paillier)
- [Threshold Cryptography](#threshold-cryptography-shamirs-secret-sharing)
- [User Story Implementation Map](#user-story-implementation-map)
- [Tally Enhancement Services](#tally-enhancement-services)
- [API Endpoints](#api-endpoints)
- [File Reference](#file-reference)
- [Data Flow](#data-flow)
- [Known Issues Fixed During Development](#known-issues-fixed-during-development)
- [Testing](#testing)
- [Dependencies](#dependencies)
- [Docker Configuration](#docker-configuration)
- [Production Considerations](#production-considerations)

---

## Overview

Epic 4 implements the privacy-preserving tallying pipeline. Its scope is everything that happens after encrypted votes land in the database and before final results are published: homomorphic aggregation, threshold decryption by trustees, fault detection, audit transcripts, and reproducibility verification.

The module does not handle voter authentication, credential issuance, or ledger consensus. Those belong to Epic 1 and Epic 3 respectively. Epic 4 consumes encrypted votes produced by those modules and outputs verified, signed tally results.

Core responsibilities:
1. Homomorphic vote aggregation (Paillier cryptosystem, 2048-bit keys)
2. Threshold decryption using Shamir's Secret Sharing (3-of-5 trustees)
3. Fault detection with a circuit breaker pattern to block publication on error
4. Ballot manifest computation for deterministic input validation
5. Tally transcript generation for auditability
6. Recount-on-demand using the same encrypted snapshot
7. Reproducibility reporting to verify deterministic output
8. Multiple election type support (plurality, approval, ranked-choice, referendum)
9. Trustee timeout and retry management
10. Tally node isolation enforcement

---

## Homomorphic Encryption (Paillier)

The system uses the Paillier cryptosystem with 2048-bit keys. Paillier provides additive homomorphism: given two encrypted values E(a) and E(b), multiplying the ciphertexts yields E(a+b) without decrypting either value.

This property allows votes to be tallied in encrypted form. Individual vote plaintexts are never exposed during aggregation.

How it works in this project:
- A keypair is generated once per election. The public key is stored in the election record.
- Each vote is encrypted as a one-hot vector (e.g. 3 candidates, vote for candidate 2 = [0, 1, 0]). Each element of the vector is encrypted individually with the public key.
- Aggregation multiplies corresponding ciphertext elements across all votes. The result is an encrypted vector of vote totals.
- Decryption of the aggregate requires the private key, which is never held by a single party (see threshold crypto below).

The encryption service is in `backend/app/services/encryption.py` (291 lines). It exposes `generate_keypair()`, `encrypt_vote()`, `aggregate_votes()`, `decrypt_tally()`, `partial_decrypt()`, and `combine_partial_decryptions()`.

---

## Threshold Cryptography (Shamir's Secret Sharing)

The election private key is split into 5 shares using Shamir's Secret Sharing, with a reconstruction threshold of 3. This means:
- At least 3 out of 5 trustees must submit their partial decryption for the tally to complete
- Any 2 or fewer trustees cannot reconstruct the key
- No single trustee or compromised machine can reveal individual votes

Each trustee performs a partial decryption using their key share. The tallying service collects these partials, verifies them (US-48), and reconstructs the final tally once the threshold is met.

The threshold crypto code is in `backend/app/services/threshold_crypto.py` (253 lines). It implements polynomial evaluation for share generation and Lagrange interpolation for reconstruction.

Configuration (set via environment variables in docker-compose):
- `KEY_SIZE=2048` -- Paillier key length
- `THRESHOLD=3` -- minimum shares needed
- `TOTAL_TRUSTEES=5` -- total shares generated

---

## User Story Implementation Map

This table maps each Epic 4 user story to the code that implements it. Stories marked as partial have the core logic in place but lack certain acceptance criteria (noted in the details column).

| User Story | Title | Status | Implementation | Details |
|------------|-------|--------|----------------|---------|
| US-47 | Threshold decryption | Done | threshold_crypto.py, tallying.py | 3-of-5 Shamir scheme. Shares not logged. Reconstruction only after threshold verified shares. |
| US-48 | Partial share verification | Done | tally_enhancements.py `verify_partial_decryption_share()` | Deterministic structural checks: base64 decode, required fields, index match, dimension match. Evidence hash persisted. Invalid shares trigger circuit breaker fault (US-53). |
| US-49 | Final decryption reconstruction | Done | tallying.py `finalize_tally()` | Combines verified partials, computes final tally dict, generates verification hash, writes result to DB, publishes transcript (US-57). |
| US-50 | ZK proof of correct aggregation | Partial | tallying.py `_generate_decryption_proof()` | Simplified hash-based proof binding trustee ID, timestamp, and ciphertext hash. Not a full zero-knowledge proof -- serves as a tamper-evident binding. |
| US-51 | Public verification tool | Not impl. | -- | Verification hash is generated and stored with results. A standalone offline verification tool was not built. The verification hash can be checked manually against the published result package. |
| US-52 | Recount-on-demand | Done | tally_enhancements.py `perform_real_recount()` | Re-aggregates from the same encrypted snapshot, re-decrypts, compares output hash against published result. Generates signed recount report with match/mismatch status. |
| US-53 | Tally fault detection | Done | tally_enhancements.py `TallyCircuitBreaker` | Circuit breaker pattern with CLOSED/OPEN/HALF_OPEN states. Threshold of 3 faults before trip. Blocks result publication when open. 300-second recovery timeout. Integrated into start_tallying and partial_decrypt flows. |
| US-54 | Ballot set integrity | Done | tally_enhancements.py `compute_ballot_manifest()` | Builds deterministic manifest from accepted ballots sorted by vote_id. Computes SHA-256 manifest hash. Manifest used as sole aggregation input. Hash logged to audit trail. |
| US-55 | Outlier detection on aggregates | Not impl. | -- | Aggregate anomaly detection is handled in the security router (Epic 5, US-69/US-73), not in the tallying module. |
| US-56 | Encrypted intermediate totals | Partial | tallying.py (TallyingSession model) | Aggregated ciphertext is stored in the TallyingSession record and persists across the decryption phase. RBAC-restricted access to the ciphertext column is not separately enforced beyond the existing endpoint auth. |
| US-57 | Tally computation audit log | Done | tally_enhancements.py `generate_tally_transcript()` | Transcript includes software hash, params hash, manifest hash, output hash, and chronological operation log from audit records. Transcript hash computed for integrity. |
| US-58 | Multiple election types | Done | tally_enhancements.py (election type functions) | Supports plurality, approval, ranked-choice, and referendum. Per-type validation rules implemented. Tally adapter selection based on election config. |
| US-59 | Tally reproducibility | Done | tally_enhancements.py `generate_reproducibility_report()` | Freezes snapshot hash, manifest hash, software hash, params hash. Re-runs tally and compares output hashes. Reports reproducible/mismatch status. |
| US-60 | Tally node isolation | Done | tally_enhancements.py `TallyIsolationEnforcer` | Environment-based enforcement. Checks TALLY_ISOLATED_MODE, TALLY_BLOCK_OUTBOUND, TALLY_ALLOWED_ENDPOINTS. Reports enforcement level (strict vs advisory). Intended for production deployment behind network segmentation. |
| US-61 | Trustee timeout/retry | Done | tally_enhancements.py `TrusteeTimeoutManager` | SLA timer (default 60 min), retry schedule (max 3 retries per trustee), escalation when threshold becomes unachievable, trustee replacement workflow trigger. Integrated into start_tallying flow. |

Summary: 12 of 15 user stories fully implemented, 2 partial, 1 not implemented.

---

## Tally Enhancement Services

The file `backend/app/services/tally_enhancements.py` (879 lines) was built specifically to complete the remaining Epic 4 user stories beyond the core tallying pipeline. Each section is labeled with its user story number in the source code.

### Circuit Breaker (US-53)

The `TallyCircuitBreaker` class monitors fault signals during aggregation and decryption. When the fault count reaches the threshold (default 3), the breaker trips to OPEN state and blocks result publication. After a recovery timeout (300 seconds), it transitions to HALF_OPEN to allow a cautious retry. Per-election instances are managed through `get_circuit_breaker(election_id)`.

Faults are recorded automatically when:
- Homomorphic aggregation fails (in `start_tallying`)
- A partial decryption share fails verification (in `partial_decrypt`)

### Ballot Manifest (US-54)

`compute_ballot_manifest()` queries all encrypted votes for an election, filters to accepted ones (non-empty ciphertext), sorts by vote_id for determinism, computes a per-entry SHA-256 hash, and produces a manifest hash over the full sorted list. This manifest is computed before aggregation and its hash is written to the audit log.

### Share Verification (US-48)

`verify_partial_decryption_share()` performs deterministic checks on each trustee's submitted share: valid base64 encoding, required JSON fields present, share index matches expected value, and partial_values dimension matches the aggregated ciphertext dimension. Returns a verification result with an evidence hash that gets persisted.

### Tally Transcript (US-57)

`generate_tally_transcript()` produces a formal record of the tally computation. It includes the software version hash, encryption parameter hash, manifest hash, output hash, and a chronological list of all tally-related operations pulled from the audit log. The entire transcript is itself hashed for integrity.

### Election Types (US-58)

Four election types are supported with per-type validation:
- **Plurality**: single candidate selection, one-hot encoding
- **Approval**: multiple candidate selection, binary vector encoding
- **Ranked-choice**: ordered candidate rankings, rank vector encoding
- **Referendum**: Yes/No/Abstain, one-hot encoding with fixed candidates

`validate_ballot_for_type()` enforces the constraints for each type before a ballot enters the aggregation pipeline.

### Reproducibility Report (US-59)

`generate_reproducibility_report()` freezes all input parameters (software hash, params hash, manifest hash, snapshot hash), recomputes the output verification hash from stored results, and compares it against the originally published hash. Reports either "reproducible" or "mismatch_detected".

### Tally Node Isolation (US-60)

`TallyIsolationEnforcer` reads environment variables to determine whether the tally service is running in isolated mode. It reports network segmentation status, allowed outbound endpoints, enforcement level (strict or advisory), and provides an endpoint allowlist check. This is configuration-driven and intended for production deployment.

### Trustee Timeout Manager (US-61)

`TrusteeTimeoutManager` tracks per-election share collection with an SLA timer. It records which trustees have submitted, monitors the deadline, triggers retries (up to 3 per trustee), and escalates when the threshold becomes unachievable. The escalation includes a recommendation for the trustee replacement workflow.

### Recount (US-52)

`perform_real_recount()` loads the same encrypted vote snapshot, re-runs the full homomorphic aggregation and decryption pipeline, and compares the recount output hash against the published verification hash. The recount report includes both tallies side by side, timing information, and a match/mismatch verdict. An audit log entry is created for every recount.

---

## API Endpoints

All endpoints are under the `/api/tally` prefix and are defined in `backend/app/routers/tallying.py`.

| Endpoint | Method | Auth | User Story | Purpose |
|----------|--------|------|------------|---------|
| /api/tally/start | POST | Admin | US-47 | Begin tallying: aggregate encrypted votes, create session, start trustee timeout tracking |
| /api/tally/partial-decrypt/{trustee_id} | POST | Trustee | US-47, US-48 | Submit partial decryption, verify share, record in timeout manager |
| /api/tally/finalize | POST | Admin | US-49 | Combine verified partials, compute final result, generate transcript |
| /api/tally/status/{election_id} | GET | Any | -- | Check current tallying session status |
| /api/tally/aggregate-info/{election_id} | GET | Any | US-56 | Get aggregation info (vote count, ciphertext size, session status) |
| /api/tally/manifest/{election_id} | GET | Any | US-54 | Compute and return ballot manifest with integrity hash |
| /api/tally/circuit-breaker/{election_id} | GET | Any | US-53 | Get circuit breaker status (state, fault count, recent faults) |
| /api/tally/circuit-breaker/{election_id}/reset | POST | Admin | US-53 | Reset circuit breaker after fault resolution |
| /api/tally/transcript/{election_id} | GET | Any | US-57 | Get tally computation transcript with operation log |
| /api/tally/reproducibility/{election_id} | GET | Any | US-59 | Generate reproducibility verification report |
| /api/tally/recount/{election_id} | POST | Admin/Auditor | US-52 | Perform real recount and compare against published results |
| /api/tally/trustee-timeout/{election_id} | GET | Any | US-61 | Get trustee share collection status with timeout/retry info |
| /api/tally/isolation-status | GET | Any | US-60 | Get tally node isolation enforcement status |
| /api/tally/election-types | GET | Any | US-58 | List supported election types and their configurations |

---

## File Reference

| File | Location | What it does |
|------|----------|--------------|
| encryption.py | backend/app/services/ | Paillier key generation, encrypt, decrypt, aggregate, partial decrypt, combine partials (291 lines) |
| threshold_crypto.py | backend/app/services/ | Shamir key splitting, polynomial evaluation, Lagrange reconstruction (253 lines) |
| tallying.py | backend/app/services/ | Tally workflow coordinator: start, partial decrypt, finalize (553 lines) |
| tally_enhancements.py | backend/app/services/ | All enhancement features: circuit breaker, manifest, share verification, transcript, election types, reproducibility, isolation, timeout, recount (879 lines) |
| tallying.py | backend/app/routers/ | Tallying API endpoints, 14 routes (407 lines) |
| test_epic4.py | backend/tests/ | Unit and integration tests for the crypto and tally layer |

---

## Data Flow

The tallying process follows this sequence:

1. Admin calls `/api/tally/start` with an election ID
2. The service loads the election public key and retrieves all encrypted votes
3. Circuit breaker state is checked -- if OPEN, tallying is blocked (US-53)
4. A ballot manifest is computed from accepted votes, sorted deterministically (US-54)
5. Encrypted votes are aggregated homomorphically (ciphertext multiplication)
6. If any vote fails to aggregate, a fault is recorded in the circuit breaker
7. The aggregated ciphertext is stored in a TallyingSession record (US-56)
8. Trustee timeout tracking begins with a configurable SLA deadline (US-61)
9. Each trustee calls `/api/tally/partial-decrypt/{trustee_id}`
10. Each submitted share is verified deterministically (US-48)
11. If a share fails verification, the circuit breaker records a fault
12. The timeout manager tracks which trustees have submitted and retries if needed
13. Once 3+ verified partials are collected, admin calls `/api/tally/finalize`
14. Circuit breaker is checked again before finalization
15. Verified partials are combined via Lagrange interpolation to reconstruct the decryption key
16. The aggregated ciphertext is decrypted to produce final vote counts
17. A verification hash is computed deterministically over the results
18. A tally transcript is generated with software hash, params hash, manifest hash, and operation log (US-57)
19. Results are stored in the ElectionResult table

After finalization, auditors can:
- Request a recount (US-52) to re-aggregate and re-decrypt from the same snapshot
- Pull the reproducibility report (US-59) to verify deterministic output
- Review the tally transcript (US-57) for step-by-step operation history

---

## Known Issues Fixed During Development

**Key mismatch error** -- Encrypted votes were failing decryption because each trustee was generating a separate key pair instead of sharing the election key. Fixed by modifying setup_trustees to use the election keypair and distributing shares of that single key.

**Timeout on bulk vote encryption** -- Generating 100 encrypted votes was hitting the default 10-second API timeout. Increased to 60 seconds. Paillier encryption with 2048-bit keys is inherently slow for large batches.

**Private key not loaded before partial decryption** -- The partial decryption function was called without first loading the private key from the election record. Added explicit key loading in the partial_decrypt method.

---

## Testing

### Unit tests

```bash
cd backend
pytest tests/test_epic4.py -v
```

The test file contains 19 tests across 7 test classes:

| Class | Tests | What it covers |
|-------|-------|----------------|
| TestEncryptionService | 4 | Keypair generation, encrypt/decrypt roundtrip, public key loading, private key loading |
| TestThresholdCryptoService | 4 | Threshold config (3-of-5), secret splitting, unique indices, minimum shares required |
| TestVoteAggregation | 2 | Aggregate empty list error, single vote aggregation |
| TestTallyingService | 2 | Service initialization, start tallying requires valid election |
| TestErrorHandling | 3 | Decrypt without private key, partial decrypt without key, invalid candidate ID |
| TestKeyConsistency | 1 | Same key reconstructed from different share subsets |
| TestIntegration | 1 | Full encryption workflow (generate, encrypt, aggregate, decrypt) |
| TestKnownErrors | 2 | Key mismatch scenario, timeout scenario |

### Integration tests (require running server)

```bash
pytest tests/test_epic4_endpoints.py -v
```

These test the REST API flow end-to-end: tally start, partial decrypt submission, and finalization through the HTTP endpoints.

### Running all project tests

```bash
cd backend
python run_all_tests.py
```

This runs all 9 test suites (103 tests total) and reports results grouped by epic.

---

## Dependencies

```
phe==1.5.0             # Paillier homomorphic encryption
secretsharing          # Shamir's Secret Sharing
cryptography           # General cryptographic primitives (hashing, signing)
```

These are the libraries directly used by Epic 4 services. Other project dependencies (fastapi, sqlalchemy, etc.) are shared across all epics.

---

## Docker Configuration

The project uses Docker Compose to run all services. The configuration relevant to Epic 4 is in `docker-compose.yml` at the project root.

### Services

**postgres** (PostgreSQL 15 Alpine)
- Container: `evoting_postgres`
- Port: 5432
- Stores election records, encrypted votes, tallying sessions, partial decryptions, election results, and audit logs
- Database initialized from `database/init.sql`
- Health check: `pg_isready` every 10 seconds
- Volume: `postgres_data` for persistent storage

**redis** (Redis 7 Alpine)
- Container: `evoting_redis`
- Port: 6379
- Used for session caching and rate limiting
- Health check: `redis-cli ping` every 10 seconds

**backend** (FastAPI)
- Container: `evoting_backend`
- Port: 8000
- Built from `backend/Dockerfile`
- Environment variables relevant to Epic 4:
  - `KEY_SIZE=2048` -- Paillier key length in bits
  - `THRESHOLD=3` -- minimum trustee shares needed for decryption
  - `TOTAL_TRUSTEES=5` -- total number of key shares generated
  - `BLOCKCHAIN_RPC=http://ganache:8545` -- endpoint for result publication
- Depends on: postgres (healthy)
- Volume: `./backend:/app` for live reload during development
- Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Health check: HTTP GET to `/health` every 30 seconds

**frontend** (React 18)
- Container: `evoting_frontend`
- Port: 3000
- Built from `frontend/Dockerfile` (development target)
- Proxies API requests to the backend at `http://backend:8000`
- Includes the TrusteePanel and ResultsDashboard components that interact with Epic 4 endpoints

**ganache** (Local Ethereum Blockchain)
- Container: `evoting_ganache`
- Port: 8545
- 10 accounts, chain ID 1337
- Used for publishing finalized tally results on-chain

**pgadmin** (Optional, requires `--profile tools`)
- Container: `evoting_pgadmin`
- Port: 5050
- Web-based database management interface

### Running the Stack

```bash
# Start all services
docker compose up --build

# Start with PGAdmin included
docker compose --profile tools up --build

# Start only backend and its dependencies
docker compose up postgres redis backend

# Rebuild backend after dependency changes
docker compose up --build backend
```

### Volumes

| Volume | Purpose |
|--------|---------|
| postgres_data | Persistent database storage |
| backend_cache | Python package cache |
| pgadmin_data | PGAdmin configuration and sessions |

### Network

All services run on the `evoting_network` bridge network. Services reference each other by container name (e.g., the backend connects to `postgres:5432` and `ganache:8545`).

### Environment Variables

Default values are provided for development. Override for production by creating a `.env` file in the project root:

```env
POSTGRES_DB=evoting
POSTGRES_USER=admin
POSTGRES_PASSWORD=secure_password
SECRET_KEY=dev_secret_key_change_in_production
BLOCKCHAIN_RPC=http://ganache:8545
```

---

## Production Considerations

This is a demonstration system. For production deployment:
- Deploy trustees on separate physical machines instead of a shared database
- Set `TALLY_ISOLATED_MODE=true` and `TALLY_BLOCK_OUTBOUND=true` to enforce network segmentation (US-60)
- Add mTLS between trustee nodes and the tallying service
- Replace the simplified hash-based proof (US-50) with a proper zero-knowledge proof library
- Build the standalone public verification tool (US-51) for offline result verification
- Use hardware security modules for key share storage instead of database columns
- Add rate limiting on public-facing tally status endpoints
- Configure production trustee timeout values via `TRUSTEE_TIMEOUT_MINUTES` and `TRUSTEE_MAX_RETRIES`
