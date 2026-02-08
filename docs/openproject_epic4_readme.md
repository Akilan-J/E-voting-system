# Epic 4: Privacy-Preserving Tallying & Result Verification
## OpenProject Configuration Guide

**Epic Owner:** Kapil  
**Sprint:** Epic 4 Implementation  
**Theme:** Cryptographic Vote Tallying  
**Status:** Completed

---

## 📋 Epic Overview

**Epic Goal:**  
Implement a privacy-preserving tallying system where encrypted votes can be counted without revealing individual choices, using threshold cryptography to ensure no single party can decrypt results alone.

**Business Value:**  
- Ensures voter privacy through homomorphic encryption
- Prevents single point of failure with 3-of-5 threshold scheme
- Provides cryptographic result verification
- Enables transparent yet private vote counting

---

## 🎯 User Stories for Backlog

### Story 1: Homomorphic Vote Encryption
**As a** system administrator  
**I want** votes to be encrypted using Paillier homomorphic encryption  
**So that** individual votes remain private while still being mathematically countable

**Acceptance Criteria:**
- [ ] System generates public/private keypair for election
- [ ] Each vote is encrypted to a ciphertext that hides the choice
- [ ] Encrypted votes can be stored without revealing content
- [ ] Zero-knowledge proofs verify vote validity without decryption

**Story Points:** 8  
**Priority:** Critical  
**Components:** Backend Service - Encryption

---

### Story 2: Threshold Key Generation
**As a** election administrator  
**I want** the decryption key split among 5 trustees using Shamir's Secret Sharing  
**So that** at least 3 must cooperate to decrypt results (preventing single-party control)

**Acceptance Criteria:**
- [ ] Private key split into 5 shares (one per trustee)
- [ ] Any 3 shares can reconstruct the key (threshold = 3)
- [ ] Individual shares reveal nothing about the key
- [ ] Lagrange interpolation correctly combines shares

**Story Points:** 8  
**Priority:** Critical  
**Components:** Backend Service - Threshold Crypto

---

### Story 3: Homomorphic Vote Aggregation
**As a** tallying service  
**I want** to aggregate encrypted votes without decrypting them  
**So that** the tally process preserves privacy throughout counting

**Acceptance Criteria:**
- [ ] Multiple encrypted votes can be combined (homomorphic addition)
- [ ] Aggregated ciphertext represents sum of all votes
- [ ] Process works without accessing individual vote content
- [ ] Aggregation completes within reasonable time (< 60s for 100 votes)

**Story Points:** 5  
**Priority:** Critical  
**Components:** Backend Service - Tallying

---

### Story 4: Trustee Partial Decryption
**As a** trustee  
**I want** to provide my partial decryption without revealing my share  
**So that** I contribute to tallying while maintaining security

**Acceptance Criteria:**
- [ ] Trustee can submit partial decryption for aggregated ciphertext
- [ ] Partial decryption computed using trustee's key share
- [ ] Share itself is not transmitted (only computation result)
- [ ] System tracks which trustees have contributed (3/5 progress)

**Story Points:** 5  
**Priority:** High  
**Components:** Backend Router - Tallying, Frontend - Trustee Panel

---

### Story 5: Threshold Decryption & Result Finalization
**As a** election administrator  
**I want** to finalize results once 3+ trustees have provided partial decryptions  
**So that** the final tally is revealed only with sufficient trustee cooperation

**Acceptance Criteria:**
- [ ] System validates at least 3 partial decryptions received
- [ ] Lagrange interpolation combines partial decryptions
- [ ] Final plaintext tally is correctly computed
- [ ] Result verification hash is generated

**Story Points:** 8  
**Priority:** Critical  
**Components:** Backend Service - Tallying, Backend Router - Results

---

### Story 6: Cryptographic Result Verification
**As a** auditor  
**I want** to verify that results match the encrypted votes  
**So that** I can ensure no tampering occurred during tallying

**Acceptance Criteria:**
- [ ] Verification hash computed from final tally
- [ ] Hash can be independently verified against published results
- [ ] Zero-knowledge proofs validate tally correctness
- [ ] Audit log records all tallying operations

**Story Points:** 5  
**Priority:** High  
**Components:** Backend Router - Results

---

### Story 7: Trustee Management Interface
**As a** trustee  
**I want** a user interface to view my status and submit decryptions  
**So that** I can participate in the tallying process easily

**Acceptance Criteria:**
- [ ] UI displays all 5 trustees with their status
- [ ] Progress bar shows decryption completion (0/3 → 3/3)
- [ ] Trustee can click button to submit partial decryption
- [ ] Visual feedback confirms successful submission

**Story Points:** 5  
**Priority:** Medium  
**Components:** Frontend - Trustee Panel

---

### Story 8: Results Visualization Dashboard
**As a** election observer  
**I want** to view final results with visual charts  
**So that** I can understand election outcomes at a glance

**Acceptance Criteria:**
- [ ] Results displayed as bar chart with percentages
- [ ] Winner highlighted with badge/crown
- [ ] Total votes and participation rate shown
- [ ] Verification status clearly indicated

**Story Points:** 5  
**Priority:** Medium  
**Components:** Frontend - Results Dashboard

---

### Story 9: Cryptographic Process Visualization
**As a** stakeholder  
**I want** to see animated demonstrations of encryption, aggregation, and decryption  
**So that** I can understand how privacy-preserving tallying works

**Acceptance Criteria:**
- [ ] Encryption demo shows plaintext → ciphertext transformation
- [ ] Aggregation demo shows homomorphic vote combination
- [ ] Decryption demo shows threshold reconstruction (3-of-5)
- [ ] Educational explanations accompany each demo

**Story Points:** 8  
**Priority:** Low (Nice-to-have)  
**Components:** Frontend - Crypto Visualizer

---

## 🧩 Task Breakdown by Component

### Backend Service: Encryption (`encryption.py`)
**Tasks:**
1. Implement Paillier keypair generation
2. Implement vote encryption with randomization
3. Implement homomorphic aggregation (ciphertext multiplication)
4. Implement full decryption with private key
5. Implement partial decryption for threshold scheme
6. Add zero-knowledge proof generation
7. Add error handling for key mismatches
8. Optimize for batch encryption (100+ votes)

**Estimated:** 3 days

---

### Backend Service: Threshold Crypto (`threshold_crypto.py`)
**Tasks:**
1. Implement Shamir's Secret Sharing split algorithm
2. Generate polynomial coefficients for secret
3. Evaluate polynomial at trustee indices (1-5)
4. Implement Lagrange interpolation for reconstruction
5. Add validation for minimum threshold (3 shares)
6. Handle edge cases (duplicate indices, invalid shares)
7. Add logging for debugging

**Estimated:** 2 days

---

### Backend Service: Tallying (`tallying.py`)
**Tasks:**
1. Create TallyingService class
2. Implement start_tallying() - create session, aggregate votes
3. Implement add_partial_decryption() - store trustee contributions
4. Implement finalize_tally() - combine partials, compute result
5. Add validation for election state (must have votes)
6. Add validation for trustee threshold (3/5)
7. Generate verification hash for results
8. Handle timeout scenarios

**Estimated:** 2.5 days

---

### Backend Router: Trustees (`trustees.py`)
**Tasks:**
1. Create POST /api/trustees/register endpoint
2. Create GET /api/trustees endpoint (list all)
3. Create GET /api/trustees/{id} endpoint
4. Create POST /api/trustees/{id}/key-share endpoint
5. Create GET /api/trustees/threshold/info endpoint
6. Add request/response validation schemas
7. Add error handling and logging
8. Document endpoints with OpenAPI

**Estimated:** 1.5 days

---

### Backend Router: Tallying (`tallying.py`)
**Tasks:**
1. Create POST /api/tally/start endpoint
2. Create POST /api/tally/partial-decrypt/{trustee_id} endpoint
3. Create POST /api/tally/finalize endpoint
4. Create GET /api/tally/status/{election_id} endpoint
5. Create GET /api/tally/aggregate-info/{election_id} endpoint
6. Add async support for long operations
7. Add proper error messages
8. Document API endpoints

**Estimated:** 2 days

---

### Backend Router: Results (`results.py`)
**Tasks:**
1. Create GET /api/results endpoint (all results)
2. Create GET /api/results/{election_id} endpoint
3. Create POST /api/results/verify endpoint
4. Create GET /api/results/audit-log/{election_id} endpoint
5. Create GET /api/results/summary/{election_id} endpoint
6. Add result caching for performance
7. Add verification logic
8. Document endpoints

**Estimated:** 1.5 days

---

### Frontend: Trustee Panel (`TrusteePanel.jsx`)
**Tasks:**
1. Design trustee card layout (5 cards)
2. Implement decrypt button for each trustee
3. Add progress bar (0/3 → 3/3)
4. Add loading states during decryption
5. Add success/error message display
6. Implement auto-refresh (every 5s)
7. Add visual feedback for completed trustees
8. Style with CSS (modern card design)

**Estimated:** 1.5 days

---

### Frontend: Results Dashboard (`ResultsDashboard.jsx`)
**Tasks:**
1. Design stats card layout (votes, participation, status)
2. Implement bar chart for vote distribution
3. Add winner highlighting (badge/crown)
4. Add verification section (hash display)
5. Add refresh button
6. Implement data fetching from API
7. Style with CSS (gradient cards, animations)
8. Add responsive design for mobile

**Estimated:** 1.5 days

---

### Frontend: Crypto Visualizer (`CryptoVisualizer.jsx`)
**Tasks:**
1. Design 3-tab layout (Encryption, Aggregation, Decryption)
2. Implement encryption animation (5 votes encrypting)
3. Implement aggregation animation (combining ciphertexts)
4. Implement decryption animation (3/5 trustees)
5. Add mathematical formulas display
6. Add educational info panels
7. Style with CSS (animations, gradients, colors)
8. Add reset functionality

**Estimated:** 3 days

---

### Testing: Unit Tests (`test_epic4.py`)
**Tasks:**
1. Write tests for encryption service (8 tests)
2. Write tests for threshold crypto service (5 tests)
3. Write tests for vote aggregation (2 tests)
4. Write tests for tallying service (2 tests)
5. Write tests for error handling (3 tests)
6. Write tests for key consistency (1 test)
7. Write integration tests (1 test)
8. Write tests for known bugs (2 tests)
9. Achieve 90%+ code coverage

**Estimated:** 2 days

---

## 📊 Sprint Planning

### Sprint 1: Core Cryptography (Week 1)
**Goal:** Implement encryption and threshold crypto foundations

**Tasks:**
- Encryption service implementation
- Threshold crypto service implementation
- Unit tests for both services
- API endpoint for key generation

**Deliverable:** Working encryption/decryption with threshold scheme

---

### Sprint 2: Tallying Workflow (Week 2)
**Goal:** Build the tallying pipeline from aggregation to finalization

**Tasks:**
- Tallying service implementation
- Tallying router endpoints
- Partial decryption logic
- Integration tests

**Deliverable:** Complete tallying API ready for frontend

---

### Sprint 3: Frontend & Visualization (Week 3)
**Goal:** Create user interfaces for trustees and results

**Tasks:**
- Trustee Panel component
- Results Dashboard component
- API integration
- Styling and animations

**Deliverable:** Working UI for tallying workflow

---

### Sprint 4: Advanced Features (Week 4)
**Goal:** Add verification, audit logging, and demos

**Tasks:**
- Crypto Visualizer component
- Results verification endpoint
- Audit logging
- Documentation
- Final testing

**Deliverable:** Complete Epic 4 with all features

---

## 🎯 Definition of Done

**For Each Story:**
- [ ] Code implemented and passes linting
- [ ] Unit tests written with 80%+ coverage
- [ ] Integration tests pass
- [ ] API endpoints documented
- [ ] Frontend components styled and responsive
- [ ] Code reviewed by peer
- [ ] Merged to main branch
- [ ] Manual testing completed

**For Epic:**
- [ ] All user stories completed
- [ ] 19/19 unit tests passing
- [ ] End-to-end workflow tested
- [ ] Documentation written
- [ ] Demo prepared
- [ ] Security review completed

---

## 📦 Backlog Items to Add

### High Priority
1. **Story 1:** Homomorphic Vote Encryption
2. **Story 2:** Threshold Key Generation
3. **Story 3:** Homomorphic Vote Aggregation
4. **Story 4:** Trustee Partial Decryption
5. **Story 5:** Threshold Decryption & Result Finalization

### Medium Priority
6. **Story 6:** Cryptographic Result Verification
7. **Story 7:** Trustee Management Interface
8. **Story 8:** Results Visualization Dashboard

### Low Priority (Nice-to-Have)
9. **Story 9:** Cryptographic Process Visualization

### Technical Debt Items
- Optimize encryption performance for 1000+ votes
- Add Redis caching for aggregated ciphertexts
- Implement key rotation mechanism
- Add trustee authentication/authorization
- Add rate limiting for tallying endpoints

---

## 🔧 Technical Architecture

### Technology Stack
- **Backend:** Python 3.11, FastAPI, SQLAlchemy
- **Cryptography:** phe library (Paillier), custom Shamir implementation
- **Frontend:** React 18, Axios
- **Testing:** pytest, unittest.mock
- **Database:** PostgreSQL

### Key Dependencies
```
phe>=1.5.0  # Homomorphic encryption
```

---

## 🚀 Deployment Considerations

1. **Key Management:**
   - Election keypair stored securely in database
   - Trustee shares encrypted at rest
   - Private key never logged or transmitted

2. **Performance:**
   - ~1-2 seconds per vote encryption
   - ~5-10 seconds for 100 vote aggregation
   - Partial decryption < 1 second per trustee

3. **Security:**
   - All crypto operations server-side
   - Shares never transmitted in plaintext
   - Audit logs for all tallying operations

---

## 📈 Success Metrics

- **Functionality:** 100% of acceptance criteria met
- **Performance:** Tally 100 votes in < 60 seconds
- **Reliability:** Zero key mismatch errors in production
- **Usability:** Trustees complete workflow without training
- **Test Coverage:** 90%+ code coverage

---

## 🐛 Known Issues & Resolutions

### Issue 1: Key Mismatch Error
**Problem:** "encrypted_number was encrypted against a different key"  
**Cause:** Each trustee had separate keys instead of shared election key  
**Resolution:** All trustees use same election keypair, only shares differ

### Issue 2: Timeout During Aggregation
**Problem:** "Action failed (timeout)" for 100 votes  
**Cause:** 10 second timeout too short for encryption  
**Resolution:** Increased timeout to 60s, optimized aggregation

### Issue 3: Docker Container Health Check
**Problem:** Backend showing unhealthy due to curl not in slim image  
**Cause:** Healthcheck used curl command  
**Resolution:** Changed to Python http.client for healthcheck

---

## 📚 References

- **Paillier Cryptosystem:** [Wikipedia](https://en.wikipedia.org/wiki/Paillier_cryptosystem)
- **Shamir's Secret Sharing:** [Wikipedia](https://en.wikipedia.org/wiki/Shamir%27s_Secret_Sharing)
- **Threshold Cryptography:** Academic papers on distributed key management
- **phe Library Docs:** [python-paillier](https://github.com/data61/python-paillier)

---

**Document Version:** 1.0  
**Last Updated:** February 8, 2026  
**Author:** Kapil - Epic 4 Owner
