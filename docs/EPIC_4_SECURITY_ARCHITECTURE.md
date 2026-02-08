# System Architecture: Privacy-Preserving E-Voting (EPIC 4)

## 1. High-Level Architecture
The system follows a Zero-Knowledge / Blind-Signature based architecture ensuring absolute separation between **Identity Verification** and **Vote Casting**.

### Service Boundaries & Trust Zones
*   **Zone 1: Identity & Access (auth.py, citizens table)**
    *   **Trust Level**: High (Access to PII)
    *   **Function**: Verifies offline identity (OIDC/SAML), checks eligibility against `citizens` registry.
    *   **Output**: Authenticated User Session (JWT).
    *   **Constraint**: NEVER communicates with the Vote Storage directly.

*   **Zone 2: Credential Issuance (BlindSigner, voter.py)**
    *   **Trust Level**: Critical (Signing Authority)
    *   **Function**: Signs blinded tokens for eligible voters.
    *   **Protocol**: 
        1. User blinds a random token.
        2. Issuer signs the blinded token (Blind Signature).
        3. User unblinds to get a valid, signed token.
    *   **Constraint**: Cannot see the `token` value, only the `blinded_token`. cannot link signature to user.
    *   **Audit**: Logs "Credential Issued" event to Immutable Audit Chain (linked to User ID internally for deduplication, but Public Log is anonymous).

*   **Zone 3: Vote Casting (voter.py/cast_vote)**
    *   **Trust Level**: Public/Anonymous
    *   **Function**: Accepts `(Vote, UnblindedToken, Signature)`.
    *   **Verification**:
        1. Checks `Signature` is valid for `Token` using Issuer Public Key.
        2. Checks `Token` not in `UsedTokens` (Double Voting Check).
        3. Checks `Token` expiry.
    *   **Constraint**: No User ID required. Purely token-based authentication.

*   **Zone 4: Immutable Ledger (ledger_service)**
    *   **Trust Level**: Distributed / Verifiable
    *   **Function**: appends encrypted votes to a hash-chained, Merkle-tree backed ledger.
    *   **Consensus**: BFT-style block proposal and finalization.

## 2. Key Data Models

### BlindToken (Lifecycle Control)
| Field | Type | Purpose |
|-------|------|---------|
| `token_hash` | String (SHA256) | Hash of the unblinded token to prevent reuse. stored ONLY after vote is cast. |
| `status` | Enum | USED, REVOKED. |
| `expiry` | DateTime | Enforces election windows. |
| `signature` | - | NEVER stored. Only verified on ingress. |

### AuditLog (Immutable Chain)
| Field | Type | Purpose |
|-------|------|---------|
| `previous_hash` | SHA256 | Links to previous log entry. |
| `current_hash` | SHA256 | Hash(prev_hash + data). Tamper-evident. |
| `actor` | String | System, Trustee, or "ANONYMOUS" (for votes). |

### Trustee (Threshold Crypto - t-of-n)
| Field | Type | Purpose |
|-------|------|---------|
| `key_share_encrypted` | Blob | Encrypted share of the election private key. |
| `public_key` | PEM | Trustee's individual public key. |

## 3. Security Controls & Threat Mitigations

| Threat | Control | Implemented In |
|--------|---------|----------------|
| **Voter Coercion** | Blind Signatures (Issuer cannot link voter to ballot) | `security_core.BlindSigner` |
| **Double Voting** | Token Hash tracking (Atomic Check-and-Set) | `voter.py:cast_vote` |
| **Internal Fraud** | Immutable Audit Logs (Hash Chaining) | `security_core.ImmutableLogger` |
| **Key Theft** | Simulated HSM (Non-exportable keys) | `security_core.KeyManager` |
| **Sybil Attack** | Strict Eligibility + 1-Credential-Per-Voter | `voter.py:issue_credential` |
| **Replay Attacks** | Nonce in Token + Expiry | `voter.py:cast_vote` |

## 4. Failure Modes
1.  **HSM Failure**: Credential issuance halts. Voting continues for already issued creds.
2.  **Ledger Consensus Failure**: Votes queued locally (risky) or rejected (safer). Current config rejects.
3.  **Audit Chain Fork**: Detected immediately by `AuditLogger` verification. System halts critical ops.
