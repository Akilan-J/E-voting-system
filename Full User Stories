## EPIC 1 — Voter Access & Credentials

**US-1**
**User Story:** As a voter, I want to authenticate using an official digital ID, so that my eligibility can be verified.
**Acceptance Criteria:**
Given a voter has a valid digital ID
When the voter logs in
Then the voter is authenticated and a session is created
**Task Set:**
Configure OIDC/SAML login flow and callback verification
Issue session token (JWT/cookie) and store session state (Redis/DB)
Map verified claims to eligibility lookup key (hashed)
Write authentication events to audit log
**Constraints:**
No raw ID documents stored; store minimal hashed identifiers only

---

**US-2**
**User Story:** As a voter, I want optional MFA, so that my account cannot be misused.
**Acceptance Criteria:**
Given MFA is enabled for the voter
When the voter logs in
Then MFA verification is required before access is granted
**Task Set:**
Implement TOTP enrollment and secret storage (encrypted/KMS)
Add MFA challenge step in login pipeline
Apply OTP retry limits and lockout counters (Redis)
Log MFA success/failure events
**Constraints:**
MFA must not create identity-to-ballot linkage

---

**US-3**
**User Story:** As an election administrator, I want to verify voter eligibility, so that unauthorized participation is prevented.
**Acceptance Criteria:**
Given a voter record exists in the registry
When eligibility is checked for an election
Then the system returns eligible/ineligible with a reason code
**Task Set:**
Define eligibility rule model and reason codes per election
Implement `/eligibility/check` backed by registry DB (indexed by hashed ID)
Cache short-lived decisions (TTL) to handle peak traffic
Persist eligibility decisions to audit log (no PII)

---

**US-4**
**User Story:** As a voter, I want a blind-signed voting credential, so that my later ballot cannot be linked to my identity.
**Acceptance Criteria:**
Given the voter is verified as eligible
When the credential is issued using blind signing
Then the issuer cannot link the credential to the voter identity
**Task Set:**
Implement blind-sign protocol (blind → sign → unblind) using vetted crypto library
Define token format (election_id, exp, token_id, signature) and store only token hash
Expose token signature verification using issuer public key
Record credential issuance event to audit log (no join key)
**Constraints:**
Identity service and token issuer must not share identifiers or databases

---

**US-5**
**User Story:** As a security officer, I want voting credentials to expire after the election, so that post-election misuse is prevented.
**Acceptance Criteria:**
Given the election has closed
When a credential is used
Then the submission is rejected as expired
**Task Set:**
Bind credential expiry to signed election config (open/close time)
Enforce expiry validation in submission validator using server time
Implement election-level revoke-all switch (DB/Redis flag)
Log expiry/revocation rejections as audit events
**Constraints:**
Server time is authoritative; client time not trusted

---

**US-6**
**User Story:** As an election administrator, I want duplicate registration detection, so that each person registers only once.
**Acceptance Criteria:**
Given a new registration is submitted
When it matches an existing voter by dedupe rules
Then the registration is flagged or blocked per policy
**Task Set:**
Define dedupe keys (salted hashes) and optional fuzzy match rules
Implement duplicate check in registration pipeline (DB query + decision)
Create admin review queue for flagged duplicates (merge/reject/allow)
Audit-log all resolution actions with actor and timestamp
**Constraints:**
Do not store raw identifiers in logs or UI

---

**US-7**
**User Story:** As a token registry operator, I want to track whether a credential token is used, so that double voting is prevented.
**Acceptance Criteria:**
Given a token is unused
When a ballot is accepted
Then the token status becomes used and cannot be reused
**Task Set:**
Create token status store keyed by token_hash (UNUSED/USED/REVOKED)
Implement atomic check-and-set on submission (DB transaction or Redis SETNX)
Mark USED only after ledger commit succeeds
Reject reuse attempts and emit security event
**Constraints:**
Token status updates must be atomic (race-safe)

---

**US-8**
**User Story:** As an operations lead, I want RBAC enforced, so that sensitive functions are restricted to authorized roles.
**Acceptance Criteria:**
Given a user lacks a required permission
When they attempt a protected action
Then access is denied and the attempt is logged
**Task Set:**
Define roles/permissions matrix and map to API scopes
Implement authorization middleware on all admin/trustee/auditor endpoints
Add admin UI to assign roles and rotate privileges
Write permission changes and denials to audit log

---

**US-9**
**User Story:** As an auditor, I want admin actions logged, so that insider manipulation can be detected.
**Acceptance Criteria:**
Given an admin performs a privileged action
When the action is committed
Then an immutable audit entry is recorded
**Task Set:**
Define audit schema (actor, action, resource, timestamp, prev_hash)
Implement append-only audit writer with hash chaining
Store logs in immutable storage (WORM table/bucket)
Provide auditor query/export with hash-chain verification
**Constraints:**
Audit logs must not contain decrypted ballots or vote choices

---

**US-10**
**User Story:** As a trustee, I want to hold only a key share, so that decryption requires collaboration.
**Acceptance Criteria:**
Given fewer than threshold shares are available
When decryption is attempted
Then results cannot be decrypted
**Task Set:**
Configure threshold scheme parameters (t-of-n) and trustee registry
Generate shares (ceremony script/module) and encrypt per trustee public key
Deliver shares over mTLS and require proof-of-possession confirmation
Audit-log trustee assignment and confirmations
**Constraints:**
Key shares must never be written to application logs

---

**US-11**
**User Story:** As a key management officer, I want key rotation supported, so that compromise impact is limited.
**Acceptance Criteria:**
Given keys are rotated
When new credentials are issued
Then the latest key version is used automatically
**Task Set:**
Model key versioning and bind artifacts to `key_id`
Implement rotation workflow (generate → activate → retire)
Update issuer/validator to resolve active `key_id` per election
Preserve historical verification via archived public keys

---

**US-12**
**User Story:** As a platform security engineer, I want private keys stored in HSM/KMS, so that secrets are never exposed in plaintext.
**Acceptance Criteria:**
Given a signing operation is required
When signing runs
Then the private key is never exported and usage is auditable
**Task Set:**
Create non-exportable keys in KMS/HSM and lock policies
Implement signer service that calls KMS for cryptographic operations
Enable key-usage audit logs and anomaly alerts
Block plaintext key configs via CI checks
**Constraints:**
No plaintext private keys in env/config/files

---

**US-13**
**User Story:** As a security analyst, I want authentication rate limiting, so that brute-force attacks fail.
**Acceptance Criteria:**
Given repeated failed logins occur
When thresholds are exceeded
Then further attempts are throttled or blocked
**Task Set:**
Define rate-limit rules (per IP + per account) and cooldown windows
Implement sliding-window counters in Redis and enforce in auth middleware
Emit metrics and security events for blocks
Tune thresholds for peak election traffic

---

**US-14**
**User Story:** As a fraud monitoring operator, I want IP/geo anomalies detected during login, so that suspicious access is flagged.
**Acceptance Criteria:**
Given an unusual login pattern occurs
When the user attempts login
Then step-up verification or blocking is triggered and logged
**Task Set:**
Define risk scoring rules (geo shift, impossible travel, device token mismatch)
Implement risk scorer integrated into login pipeline
Trigger MFA/deny based on score thresholds
Store alerts in security event store (minimal metadata)
**Constraints:**
Collect minimal signals (privacy-preserving)

---

**US-15**
**User Story:** As an election administrator, I want a credential revocation feature, so that compromised tokens cannot be used.
**Acceptance Criteria:**
Given a token is revoked
When it is presented for ballot submission
Then submission is rejected and logged
**Task Set:**
Implement revocation list keyed by token_hash with reason + approvals
Add revocation check in submission validator before ledger write
Propagate revocations via DB + Redis cache
Audit-log revocation actions with actor and timestamp

---

**US-16**
**User Story:** As an auditor, I want registration verification without identity-to-token linkage, so that ghost voters can be detected while preserving privacy.
**Acceptance Criteria:**
Given registration records exist
When an audit report is generated
Then counts are verifiable without linking identities to tokens
**Task Set:**
Separate identity registry and token registry with no join keys
Generate aggregate proofs (counts + signed hashes) from both stores independently
Verify proofs against immutable audit logs
Export audit report with hashes and timestamps
**Constraints:**
Audit output must be aggregate-only (no per-voter traceability)

---

# EPIC 2 — Private Ballot Submission

**US-17**
**User Story:** As a voter, I want my ballot encrypted on the client, so that my vote stays private.
**Acceptance Criteria:**
Given a voter selects a candidate
When they submit the ballot
Then only encrypted ballot data is transmitted
**Task Set:**
Define ballot encoding (candidate→plaintext vector) and crypto parameters
Implement client encryption using election public key + CSPRNG nonce
Serialize ciphertext canonically for transport/storage
Scrub plaintext selection from memory after encryption
**Constraints:**
Use vetted crypto libraries; no custom crypto

---

**US-18**
**User Story:** As a tallying engineer, I want homomorphic encryption integrated, so that ballots can be aggregated without decryption.
**Acceptance Criteria:**
Given encrypted ballots exist
When aggregation is executed
Then the aggregated ciphertext remains valid for decryption
**Task Set:**
Select additive HE scheme and parameter set for expected election size
Implement shared serialization/deserialization library for ciphertexts
Build test vectors for encrypt→add→decrypt correctness
Benchmark aggregation latency for peak loads

---

**US-19**
**User Story:** As a backend developer, I want ballot schema validation, so that malformed submissions are rejected.
**Acceptance Criteria:**
Given a ballot package is submitted
When it violates schema rules
Then it is rejected with a safe validation error
**Task Set:**
Define ballot package schema (election_id, token_proof, ciphertext, zk_proof, nonce, version)
Implement schema validator before crypto verification
Return deterministic error codes and log rejection reason safely
Version the schema for backward compatibility

---

**US-20**
**User Story:** As a voter, I want a ZK proof attached to my encrypted ballot, so that validity is verified without revealing my choice.
**Acceptance Criteria:**
Given a ballot is encrypted
When the proof is verified
Then invalid ballots are rejected without learning the vote
**Task Set:**
Define proof statement (valid candidate domain / one-hot) bound to election_id + nonce
Implement client proof generation using chosen ZK toolkit
Implement server proof verification as a mandatory validator step
Store proof with ciphertext for audit verification
**Constraints:**
Proof generation must be feasible on client devices

---

**US-21**
**User Story:** As a validation engineer, I want encrypted ballot size limits enforced, so that oversized payload attacks are blocked.
**Acceptance Criteria:**
Given a submission exceeds size limits
When it is received
Then it is rejected before heavy processing or ledger write
**Task Set:**
Define max byte limits per field based on crypto params
Enforce request size at gateway and field size in validator
Reject before parsing/decompression vulnerabilities
Log oversize attempts as security events

---

**US-22**
**User Story:** As a ballot validator, I want candidate validity enforced, so that ballots cannot encode invalid candidates.
**Acceptance Criteria:**
Given a ballot encodes an invalid candidate
When validation runs
Then it is rejected deterministically
**Task Set:**
Publish signed candidate list and candidate_count per election version
Bind ZK proof constraints to candidate_count
Reject mismatched election/candidate versions
Audit-log validation failures using safe codes
**Constraints:**
Do not reveal which candidate value failed

---

**US-23**
**User Story:** As an election administrator, I want a time-bounded submission window, so that late ballots are rejected fairly.
**Acceptance Criteria:**
Given the election is closed
When a ballot is submitted
Then it is rejected as late
**Task Set:**
Store open/close times in signed election configuration
Enforce server-time checks during submission validation
Define grace policy for clock drift and network delay
Log late submissions with timestamp and election_id
**Constraints:**
Client clock must not be trusted

---

**US-24**
**User Story:** As a security engineer, I want replay protection, so that duplicate submissions cannot create extra votes.
**Acceptance Criteria:**
Given the same ballot submission is replayed
When it is received again
Then only the first is accepted and others are rejected
**Task Set:**
Require nonce per submission and bind to token_hash
Maintain replay cache using Redis SETNX with TTL
Reject seen (token_hash, nonce) pairs before ledger write
Emit replay alerts to security monitoring

---

**US-25**
**User Story:** As a voter, I want a receipt after voting, so that I can verify inclusion in the ledger later.
**Acceptance Criteria:**
Given a ballot is committed to the ledger
When the voter requests proof
Then a receipt can be used to verify inclusion
**Task Set:**
Define receipt format as hash of ledger_tx + ciphertext_hash (+ proof_hash)
Generate receipt only after ledger commit confirmation
Implement receipt verification endpoint using Merkle inclusion proof
Ensure receipt output contains no vote content
**Constraints:**
Receipt must not reveal vote choice (anti-coercion)

---

**US-26**
**User Story:** As an election operator, I want client integrity checks, so that tampered clients cannot inject votes.
**Acceptance Criteria:**
Given a tampered client submits a ballot
When integrity verification fails
Then submission is rejected and logged
**Task Set:**
Define client integrity method (signed build hash / attestation token)
Verify integrity evidence during submission validation
Reject and log integrity failures with correlation IDs
Rotate signing keys and maintain allowlist of versions
**Constraints:**
Avoid excessive device fingerprinting

---

**US-27**
**User Story:** As a voter, I want TLS with certificate pinning, so that ballot transmission cannot be intercepted.
**Acceptance Criteria:**
Given a MITM presents an invalid certificate
When the client connects
Then the connection fails and no ballot is sent
**Task Set:**
Enforce modern TLS settings at gateway (disable weak ciphers/protocols)
Implement certificate pinning in client with backup pin for rotation
Monitor certificate expiry and automate renewal/rollover plan
Fail closed (no downgrade to insecure transport)
**Constraints:**
Pin rotation must not cause election-day outages

---

**US-28**
**User Story:** As a voter, I want safe retry and re-encryption support, so that local encryption failures do not stop me from voting.
**Acceptance Criteria:**
Given encryption fails locally
When the voter retries
Then a fresh ciphertext is generated and only one ballot is accepted
**Task Set:**
Implement client retry state machine (fail → re-encrypt with new nonce → resubmit)
Ensure server-side idempotency using token-used + replay checks
Return safe error codes for recoverable crypto failures
Log aggregate failure metrics without storing selections

---

**US-29**
**User Story:** As a voter, I want the ballot displayed in my preferred language, so that I can vote confidently.
**Acceptance Criteria:**
Given a language is selected
When the ballot renders
Then labels are translated without changing candidate identifiers
**Task Set:**
Implement i18n bundles for ballot UI strings with fallback rules
Keep candidate IDs canonical and map translations to display names only
Sign translation bundles per election to prevent tampering
Test UI layout for different script lengths
**Constraints:**
Candidate identifiers must remain constant across locales

---

**US-30**
**User Story:** As a voter, I want to preview my choices before encryption, so that I can correct mistakes.
**Acceptance Criteria:**
Given the voter reaches the preview screen
When they confirm
Then encryption occurs only after explicit confirmation
**Task Set:**
Add review UI step showing selected options from in-memory state
Require explicit “Confirm & Encrypt” action
Allow back/edit and then re-preview before encryption
Prevent persistence of selections after submission
**Constraints:**
Do not store selections in logs/local storage after submit

---

**US-31**
**User Story:** As a voter with accessibility needs, I want an accessible voting flow, so that I can vote independently.
**Acceptance Criteria:**
Given keyboard-only navigation is used
When the voter completes the flow
Then they can submit successfully without blocked steps
**Task Set:**
Implement keyboard navigation + focus order + ARIA labels across ballot UI
Support text scaling and contrast modes without breaking layout
Add automated checks for missing ARIA/focus traps
Validate with screen-reader testing
**Constraints:**
Accessibility must not weaken security controls

---

# EPIC 3 — Immutable Vote Ledger

**US-32**
**User Story:** As a ledger node operator, I want a permissioned blockchain, so that only trusted nodes can write blocks.
**Acceptance Criteria:**
Given an untrusted node attempts to write
When it submits a block
Then the block is rejected and logged
**Task Set:**
Define node identity model (CA + node certs) and membership registry
Configure permissioned network genesis and access control list
Enforce mTLS on block submission and inter-node RPC
Audit-log membership and write attempts
**Constraints:**
Membership changes must be auditable

---

**US-33**
**User Story:** As a consensus maintainer, I want BFT consensus, so that malicious nodes cannot corrupt the ledger.
**Acceptance Criteria:**
Given up to f faulty nodes exist
When blocks are proposed
Then honest nodes commit the same chain state
**Task Set:**
Select BFT protocol and quorum rules (n, f, 2f+1)
Implement proposal/prepare/commit pipeline and view-change handling
Persist commit certificates with block metadata
Simulate byzantine faults in test environment

---

**US-34**
**User Story:** As an auditor, I want an append-only ledger, so that past votes cannot be deleted or rewritten.
**Acceptance Criteria:**
Given a historical block exists
When modification is attempted
Then verification fails and the mutation is detected
**Task Set:**
Enforce immutable storage semantics for blocks (no update/delete APIs)
Store blocks by height with monotonic increase checks
Add verifier that recomputes chain hashes and rejects mutations
Record mutation attempts as security incidents
**Constraints:**
No admin “edit” function allowed

---

**US-35**
**User Story:** As an observer, I want hash-linked blocks, so that ledger tampering is provably detectable.
**Acceptance Criteria:**
Given any block is altered
When hashes are recomputed
Then the chain breaks at the altered block
**Task Set:**
Define canonical block header encoding and hash function
Compute block hash including prev_hash and merkle_root
Implement Merkle tree per block over ballot entries
Build chain verifier (genesis→tip) with Merkle proof checks

---

**US-36**
**User Story:** As a platform operator, I want multi-node replication, so that the ledger remains available during failures.
**Acceptance Criteria:**
Given some nodes are offline
When new blocks are committed
Then the ledger remains readable and consistent on healthy nodes
**Task Set:**
Implement catch-up sync (request missing blocks by height + verify proofs)
Replicate block storage across nodes and validate before commit
Add failover routing for read-only queries
Detect and prevent split-brain writes

---

**US-37**
**User Story:** As an observer, I want a ledger explorer UI, so that I can browse encrypted ballots and block metadata.
**Acceptance Criteria:**
Given a block exists
When it is viewed
Then only encrypted entries and metadata are shown
**Task Set:**
Implement read-only APIs for block list, block detail, entry lookup by receipt
Add pagination and canonical hash display
Show Merkle inclusion proof verification results
Sanitize all inputs/outputs against XSS and injection
**Constraints:**
Explorer must not expose plaintext or node secrets

---

**US-38**
**User Story:** As a node operator, I want node health monitoring, so that offline or desynced nodes are detected quickly.
**Acceptance Criteria:**
Given a node falls behind
When monitoring runs
Then an alert is triggered with node lag details
**Task Set:**
Expose node health signals (heartbeat, last_height, peer connectivity)
Collect metrics and compute lag/availability thresholds
Trigger alerts on offline/lag conditions
Store monitoring events for audit/incident review

---

**US-39**
**User Story:** As a security analyst, I want consensus failure alerts, so that attacks or stalls are detected early.
**Acceptance Criteria:**
Given consensus stalls beyond timeout
When monitoring detects no commits
Then a consensus-stalled alert is raised
**Task Set:**
Export consensus telemetry (view-changes, failed proposals, commit latency)
Define alert thresholds and dedup rules
Capture evidence bundle (node IDs, heights, hashes)
Log incidents into incident tracker

---

**US-40**
**User Story:** As a validator node, I want strict block validation rules, so that poisoned blocks are rejected.
**Acceptance Criteria:**
Given a block violates validation rules
When received by nodes
Then it is rejected deterministically
**Task Set:**
Define validation rules (signature, prev_hash, height, merkle_root, size limits)
Implement deterministic validation pipeline before commit
Add test cases for malformed blocks to ensure consistent rejection
Record rejected block hashes for analysis
**Constraints:**
Validation must be deterministic across nodes

---

**US-41**
**User Story:** As an operator, I want ledger snapshotting, so that node rebuilds are faster.
**Acceptance Criteria:**
Given a snapshot exists
When a node joins
Then it restores quickly and verifies to the current tip hash
**Task Set:**
Define snapshot artifact (height, tip_hash, state files) and signing method
Implement snapshot creation job and restore procedure
Verify restored state against chain proofs
Store snapshots in immutable storage with retention policy

---

**US-42**
**User Story:** As an auditor, I want ledger-backed event anchoring, so that election events cannot be rewritten.
**Acceptance Criteria:**
Given an election event occurs
When it is recorded
Then it is anchored immutably and verifiable later
**Task Set:**
Define event schema (open/close, config hash, trustee actions)
Write events as signed entries to ledger event stream
Implement replay verifier that checks signatures and ordering
Export event proofs in audit bundle
**Constraints:**
Event stream must not contain voter identities

---

**US-43**
**User Story:** As a node operator, I want distributed node authentication, so that peers are verified before syncing data.
**Acceptance Criteria:**
Given an unknown peer connects
When authentication is checked
Then the connection is rejected and logged
**Task Set:**
Set up PKI (CA, node cert issuance, allowlist)
Enforce mutual TLS on all node RPC calls
Reject untrusted certs and log failures
Support cert rotation without downtime

---

**US-44**
**User Story:** As a governance operator, I want write-quorum enforcement, so that a block is accepted only with enough approvals.
**Acceptance Criteria:**
Given quorum signatures are not met
When a block is proposed
Then the block is not committed
**Task Set:**
Define quorum certificate format (2f+1 signatures)
Require quorum certificate before block finalization
Verify certificate signatures for every committed block
Expose verifier report for auditors

---

**US-45**
**User Story:** As a citizen, I want public read access to encrypted ledger data, so that transparency is possible without privacy loss.
**Acceptance Criteria:**
Given public read mode is enabled
When users browse the ledger
Then only encrypted data and metadata are accessible
**Task Set:**
Publish read-only API gateway endpoints (blocks/headers/proofs)
Enforce strict “no write” routing and RBAC for internal endpoints
Add caching and rate-limiting for public traffic
Redact operational internals from responses
**Constraints:**
Public endpoints must be read-only by design

---

**US-46**
**User Story:** As a platform operator, I want a retention/pruning policy, so that storage is controlled without breaking auditability.
**Acceptance Criteria:**
Given pruning runs under policy
When auditors verify the chain
Then end-to-end integrity checks still succeed
**Task Set:**
Define retention tiers (headers/hashes permanent; payloads archived after period)
Implement pruning job that preserves hashes and writes pruning event to ledger
Implement archive retrieval for audit cases
Block pruning during disputes/audits
**Constraints:**
Never prune integrity evidence (headers/hashes)

---

# EPIC 4 — Secure Tally & Proofs

**US-47**
**User Story:** As trustees, I want threshold decryption, so that no single trustee can decrypt results alone.
**Acceptance Criteria:**
Given fewer than threshold shares exist
When decryption is attempted
Then reconstruction fails
**Task Set:**
Configure threshold parameters and trustee registry
Implement signed share submission endpoint
Verify trustee identity and accept only authorized shares
Trigger reconstruction only after threshold verified shares
**Constraints:**
Shares must not appear in logs

---

**US-48**
**User Story:** As a tally verification officer, I want each partial decryption share verified, so that invalid shares are detected.
**Acceptance Criteria:**
Given an invalid share is submitted
When verification runs
Then it is rejected and flagged for audit
**Task Set:**
Define verification method for shares (scheme-specific proofs/checks)
Implement deterministic share verifier
Persist verification outcomes and evidence hashes
Alert on repeated invalid shares
**Constraints:**
Verification must be deterministic

---

**US-49**
**User Story:** As a tallying service owner, I want final decryption reconstruction, so that results are computed correctly.
**Acceptance Criteria:**
Given threshold verified shares exist
When reconstruction runs
Then signed plaintext results are produced
**Task Set:**
Bind reconstruction input to ledger snapshot hash and manifest hash
Combine verified shares to decrypt aggregated ciphertext
Sign results and publish result package (totals + hashes)
Write reconstruction transcript hash to audit log
**Constraints:**
Run in isolated environment for tally

---

**US-50**
**User Story:** As an auditor, I want ZK proof of correct aggregation, so that results match the ledger ballots.
**Acceptance Criteria:**
Given a published tally and ledger snapshot exist
When proof verification runs
Then incorrect/missing ballots cause verification failure
**Task Set:**
Define statement “tally = homomorphic sum of snapshot ballots”
Generate proof bound to snapshot hash and manifest
Publish proof bundle with verifier inputs
Implement verifier to validate using public ledger artifacts
**Constraints:**
Proof must not leak individual votes

---

**US-51**
**User Story:** As an observer, I want a public tally verification tool, so that I can verify results independently.
**Acceptance Criteria:**
Given the evidence bundle is available
When verification is executed
Then a deterministic pass/fail report is produced
**Task Set:**
Implement tool to verify ledger hash chain and snapshot hash
Verify tally proof and result signature
Output structured report with failure reasons and hashes
Support offline verification with downloaded bundle

---

**US-52**
**User Story:** As an auditor, I want recount-on-demand, so that results can be revalidated without recollecting votes.
**Acceptance Criteria:**
Given the same snapshot is used
When recount runs
Then results match the published totals exactly
**Task Set:**
Reuse snapshot manifest to recompute encrypted aggregation
Re-run threshold decryption using verified shares
Compare output hashes and totals with published package
Generate signed recount report

---

**US-53**
**User Story:** As a tally operations engineer, I want tally fault detection, so that failures stop incorrect publication.
**Acceptance Criteria:**
Given homomorphic aggregation fails
When fault is detected
Then publishing is halted and an alert is generated
**Task Set:**
Define fault signals (invalid ciphertext, missing ballots, verifier failure)
Implement circuit-breaker that blocks publish on fault
Emit alerts and persist fault evidence hashes
Record incident in audit/incident store
**Constraints:**
Fault handling must not reveal vote content

---

**US-54**
**User Story:** As a tally officer, I want ballot set integrity checks, so that only validated ballots are included.
**Acceptance Criteria:**
Given unvalidated ballots exist
When tally inputs are prepared
Then unvalidated ballots are excluded deterministically
**Task Set:**
Build ballot manifest from ledger snapshot using accepted-status criteria
Sort deterministically and compute manifest hash
Use manifest as sole input for aggregation
Audit-log manifest hash and counts
**Constraints:**
Deterministic ordering required

---

**US-55**
**User Story:** As an auditor, I want outlier detection on aggregate patterns, so that suspicious spikes are flagged.
**Acceptance Criteria:**
Given a synthetic spike scenario exists
When detection runs
Then an anomaly alert is produced
**Task Set:**
Define aggregate-only anomaly metrics (turnout rate changes, time spikes)
Compute metrics from token-used counts and ledger height over time
Trigger alerts based on thresholds
Export anomaly report with time window and hashes
**Constraints:**
No per-voter analytics

---

**US-56**
**User Story:** As a tally engineer, I want encrypted intermediate totals stored, so that tally progress is preserved securely.
**Acceptance Criteria:**
Given tally is in progress
When intermediate totals are stored
Then they remain encrypted and integrity-protected
**Task Set:**
Store encrypted totals with snapshot hash and key_id metadata
Hash and sign stored artifacts for integrity
Restrict access via RBAC and isolated storage
Log read/write operations to audit trail

---

**US-57**
**User Story:** As an auditor, I want a tally computation audit log, so that each step is transparent and reproducible.
**Acceptance Criteria:**
Given tally completes
When the transcript is exported
Then it includes hashes/versions needed for verification
**Task Set:**
Define transcript schema (software hash, params hash, manifest hash, output hash)
Write transcript as append-only records
Sign transcript export for integrity
Provide verifier that checks transcript consistency
**Constraints:**
Transcript must not include secrets (shares/keys)

---

**US-58**
**User Story:** As an election administrator, I want multiple election types supported, so that referendums and ranked-choice can be tallied.
**Acceptance Criteria:**
Given ranked-choice config is enabled
When ballots are validated
Then ranked-choice constraints are enforced
**Task Set:**
Define election-type config and encoding adapters per type
Implement validation rules per election type
Implement tally adapter selection based on config
Add test suites per type for determinism

---

**US-59**
**User Story:** As an auditor, I want tally reproducibility, so that reruns produce the same output deterministically.
**Acceptance Criteria:**
Given identical inputs are used
When tally is rerun
Then output hashes match exactly
**Task Set:**
Freeze snapshot hash, manifest hash, software hash, params hash
Enforce deterministic ordering and disable nondeterministic operations
Re-run tally and compare output hashes
Publish reproducibility report

---

**US-60**
**User Story:** As a security engineer, I want tally nodes isolated, so that network and side-channel risks are reduced.
**Acceptance Criteria:**
Given tally mode is active
When outbound network access is attempted
Then it is blocked except approved channels
**Task Set:**
Deploy tally service in segmented network with hardened OS baseline
Restrict outbound network and enforce allowlisted endpoints only
Require audited access controls for operator actions
Store tamper-evident logs for all accesses
**Constraints:**
Isolation must still allow secure trustee share submission

---

**US-61**
**User Story:** As a tally coordinator, I want timeout and retry handling for trustee shares, so that decryption can proceed if a trustee is offline.
**Acceptance Criteria:**
Given a trustee is offline
When timeout is reached
Then retries occur and tally proceeds if threshold remains achievable
**Task Set:**
Define share collection SLA timers and retry schedule
Track received shares vs threshold and trigger escalation
Support trustee replacement workflow under governance controls
Audit-log timeouts, retries, and overrides

---

# EPIC 5 — Verification & Audit Ops

**US-62**
**User Story:** As a voter, I want a receipt verification portal, so that I can confirm my ballot is included in the ledger.
**Acceptance Criteria:**
Given a valid receipt exists
When the receipt is checked
Then inclusion proof is shown as valid
**Task Set:**
Implement receipt lookup mapping to ledger tx/block reference
Verify Merkle inclusion proof for the receipt entry
Return deterministic verified/not-verified response
Rate-limit lookups to prevent enumeration
**Constraints:**
Portal must not require login (preserve anonymity)

---

**US-63**
**User Story:** As an observer, I want a ZK proof verification UI, so that I can validate tally proofs independently.
**Acceptance Criteria:**
Given a proof bundle is published
When verification is executed
Then pass/fail with reason codes is displayed
**Task Set:**
Implement verifier UI that loads proof + snapshot + result signature
Run proof verification locally/server-side using public artifacts
Display deterministic outputs and evidence hashes
Export verification report

---

**US-64**
**User Story:** As an auditor, I want a ledger replay audit tool, so that I can confirm all ballots are included and untampered.
**Acceptance Criteria:**
Given the ledger contains blocks
When replay audit runs
Then hash-chain or Merkle mismatches are detected
**Task Set:**
Iterate blocks and recompute prev_hash chain verification
Verify Merkle roots and count ballot entries deterministically
Generate replay report including tip hash and manifest hash
Support cross-node comparison by tip hash

---

**US-65**
**User Story:** As a citizen, I want an election transparency dashboard, so that turnout/progress is visible without exposing individuals.
**Acceptance Criteria:**
Given dashboard is public
When it is viewed
Then only aggregate metrics are displayed
**Task Set:**
Define safe aggregate metrics (turnout count, ledger height, status)
Compute metrics from token-used counts and ledger state
Serve via cached read-only API with rate limits
Ensure no drill-down that enables targeting
**Constraints:**
Aggregate-only (no per-region micro-slices if risky)

---

**US-66**
**User Story:** As an auditor, I want an end-to-end evidence package, so that verification can be reproduced offline.
**Acceptance Criteria:**
Given the evidence package is downloaded
When hashes are checked
Then tampering is detectable
**Task Set:**
Bundle ledger headers, snapshot hash, manifest hash, proof bundle, result signature, software hashes
Generate signed manifest with checksums
Publish immutable artifact for download
Provide verifier steps and expected outputs

---

**US-67**
**User Story:** As an operator, I want system event logging and monitoring, so that critical events are traceable.
**Acceptance Criteria:**
Given a critical event occurs
When monitoring is active
Then it is logged and alerts fire based on severity
**Task Set:**
Define event taxonomy and structured log schema
Centralize logs/metrics into monitoring stack
Create alert rules for security and availability
Hash-chain critical audit events for tamper evidence
**Constraints:**
Never log vote choices or decrypted ballots

---

**US-68**
**User Story:** As an auditor, I want threat simulation tools, so that resilience can be tested against tampering attempts.
**Acceptance Criteria:**
Given a replay/malformed-ballot scenario is simulated
When the tool runs
Then defenses trigger and evidence is recorded
**Task Set:**
Define attack scenarios and expected defensive outcomes
Inject replay/oversize/invalid-proof and consensus-stall events in test mode
Capture logs, alerts, and rejection evidence hashes
Generate simulation report artifact
**Constraints:**
Must run only in test environment (no real election data)

---

**US-69**
**User Story:** As a security team member, I want an attack detection dashboard, so that anomalies are visible in real time.
**Acceptance Criteria:**
Given anomaly thresholds are exceeded
When the dashboard updates
Then an incident alert appears with evidence context
**Task Set:**
Define detection signals (replay spikes, auth brute force, node lag, stalled commits)
Stream security events into dashboard backend
Deduplicate and correlate events by time window/correlation ID
Link alerts to incident records and evidence hashes

---

**US-70**
**User Story:** As an investigator, I want incident response logs, so that all response actions are traceable.
**Acceptance Criteria:**
Given an incident is opened
When responders take actions
Then each action is recorded immutably
**Task Set:**
Implement incident workflow store (OPEN→TRIAGE→MITIGATE→RESOLVE)
Append-only action log with actor, timestamp, evidence links
Export signed incident report
Restrict access by RBAC
**Constraints:**
Incident logs must be append-only

---

**US-71**
**User Story:** As an election official, I want a dispute resolution workflow, so that claims can be investigated consistently.
**Acceptance Criteria:**
Given a dispute is filed
When it is processed
Then evidence and resolution notes are recorded with audit trace
**Task Set:**
Implement case lifecycle and role-based access controls
Attach receipts, replay reports, proof verifications as evidence artifacts
Require justification for closure decisions
Audit-log all case state transitions
**Constraints:**
Must not expose voter choices

---

**US-72**
**User Story:** As an authority reviewer, I want compliance reporting, so that controls are evidenced against standards.
**Acceptance Criteria:**
Given a compliance report is generated
When reviewed
Then each claim references verifiable evidence
**Task Set:**
Map controls to measurable evidence artifacts (hashes/logs/proofs/configs)
Generate report with evidence references and signatures
Highlight missing controls and risks
Export versioned report artifact
**Constraints:**
Do not claim real-world certification (academic project)

---

**US-73**
**User Story:** As an auditor, I want anomaly detection on voting patterns, so that abnormal spikes are flagged early.
**Acceptance Criteria:**
Given abnormal spikes occur
When analytics runs
Then alerts are generated with evidence windows
**Task Set:**
Compute aggregate time-series metrics from turnout + ledger height
Apply threshold-based detection and smoothing to reduce noise
Emit alerts with time windows and associated block ranges
Export anomaly report
**Constraints:**
Aggregate-only analytics (no deanonymization risk)

---

**US-74**
**User Story:** As an investigator, I want an election replay simulator, so that the full election timeline can be reconstructed.
**Acceptance Criteria:**
Given logs and ledger events exist
When replay simulation runs
Then a chronological “what happened when” timeline is produced
**Task Set:**
Correlate audit logs + ledger event stream using timestamps/correlation IDs
Order events deterministically into a timeline view
Filter timeline by subsystem (auth/ledger/tally/admin)
Export signed replay bundle (timeline + hashes)
**Constraints:**
Timeline must not contain identity→token linkage

---

**US-75**
**User Story:** As an observer, I want read-only observer mode, so that I can monitor without risking modification.
**Acceptance Criteria:**
Given an observer role is used
When write actions are attempted
Then they are denied and logged
**Task Set:**
Define observer role with read-only permissions
Enforce RBAC on all endpoints and UI controls
Disable mutation features in UI routes for observer sessions
Log denied write attempts as security events

---

**US-76**
**User Story:** As a citizen observer, I want a one-click public verification portal, so that I can verify results easily.
**Acceptance Criteria:**
Given public evidence is published
When verification is executed
Then the portal outputs deterministic verified/not-verified with reasons
**Task Set:**
Fetch evidence bundle (headers, snapshot, proof, result signature)
Verify ledger integrity, tally proof, and result signature in one pipeline
Cache large artifacts and stream progress to avoid timeouts
Export verification report artifact
**Constraints:**
Uses only public artifacts (no private keys/shares)