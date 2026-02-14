# Testing Workflow Guide

Step-by-step instructions to test the voter login, MFA, and voting flow.

---

## Prerequisites

1. All Docker containers running: `docker-compose up -d`
2. Frontend at http://localhost:3000
3. Backend at http://localhost:8000
4. Health check returns healthy: GET http://localhost:8000/health

---

## Test 1: Basic Voter Login (No MFA)

1. Open http://localhost:3000
2. Select Role as Voter
3. Enter credential: `voter1` (valid credentials: voter1 through voter5)
4. Click Login

Expected: Logged in immediately with no MFA prompt. Role shows as "voter" in the top bar. Available tabs: Voter Access, Results, Ledger, Verification.

---

## Test 2: Voter Access Dashboard

1. After logging in as voter1, click the Voter Access tab
2. Dashboard should load directly without a second login

Expected: Shows "Logged in as" with Security Settings and Election Actions sections. No separate login screen appears. The "Enable 2FA Protection" button is visible.

---

## Test 3: Enable 2FA

1. In the Voter Access dashboard, click Enable 2FA Protection
2. A secret key and provisioning URI will appear
3. Copy the secret key
4. Enter the 6-digit OTP from your authenticator app (or generate via CLI, see below)
5. Click Activate 2FA

To generate an OTP without an authenticator app:
```bash
docker exec evoting_backend python -c "import pyotp; print(pyotp.TOTP('YOUR_SECRET_HERE').now())"
```

Expected: Message says "MFA Setup Complete: MFA Enabled". You remain on the dashboard. A new token is issued automatically.

---

## Test 4: Re-Login with 2FA

1. Click Logout
2. Select Voter, enter `voter1`, click Login
3. An OTP verification screen should appear
4. Enter the 6-digit code from your authenticator or CLI
5. Click Verify

Expected: After entering credentials, you see the OTP screen (not the main app). After a valid OTP, you are logged in with role "voter" and all tabs are available.

If it fails:

| Problem | Cause | Fix |
|---------|-------|-----|
| Shows "mfa_pending" as role | Stale localStorage data | Clear browser localStorage and retry |
| "Invalid OTP" error | OTP expired (30-second window) | Generate a fresh OTP immediately |
| Stuck on login screen | Backend unreachable | Check docker-compose ps, restart if needed |

---

## Test 5: Voter Access with 2FA Active

1. After MFA login, click Voter Access tab
2. Dashboard should load directly

Expected: No second login needed. Security Settings shows MFA is already active.

---

## Test 6: Full Voting Flow

1. Log in as voter1 (with or without MFA depending on state)
2. Go to Voter Access tab
3. Click Check Eligibility - confirm "Eligible" badge appears
4. Click Get Blind Credential - credential issued message appears
5. In the Voting Booth section, select a candidate (e.g., Alice Johnson)
6. Click Review and Encrypt
7. Review the selection, then click Confirm and Submit

Expected: Eligibility check returns "Eligible". Blind credential is issued with a signature displayed. After submitting, a "Vote Submitted" confirmation appears with a receipt hash and timestamp.

---

## Test 7: Admin Login

1. Log out from voter account
2. Select Admin, enter credential: `admin`, click Login

Expected: Logged in as admin. All tabs visible: Results, Ledger, Trustees, Testing, Ops and Audit, Verification, Security Lab.

---

## Test 8: Other Role Logins

| Role | Credential | Expected Tabs |
|------|------------|---------------|
| Trustee | trustee | Trustees, Results, Ledger, Verification |
| Auditor | auditor | Results, Ledger, Ops and Audit, Verification |
| Security Engineer | security_engineer | Security Lab, Ops and Audit, Ledger, Verification |

---

## Troubleshooting

### Reset MFA for all voters
```bash
docker exec evoting_postgres psql -U admin -d evoting -c "UPDATE users SET mfa_enabled = false, mfa_secret = NULL WHERE role = 'voter';"
```

### Clear browser state
Open DevTools, go to Application, Local Storage, http://localhost:3000. Delete `authRole` and `authToken` entries. Refresh the page.

### Restart containers
```bash
docker-compose down
docker-compose up -d
```

### Check logs
```bash
docker logs evoting_backend --tail 50
docker logs evoting_frontend --tail 50
```

---

## Verification Checklist

- voter1 can log in without MFA (fresh state)
- Voter Access tab loads directly after login
- 2FA can be enabled from Voter Access dashboard
- After enabling 2FA, re-login shows OTP screen
- Valid OTP completes login with role: voter
- Full voting flow works (eligibility, credential, vote, receipt)
- Admin, trustee, auditor, security_engineer logins work
- Logout fully clears session
