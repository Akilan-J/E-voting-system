# E-Voting System — Testing Workflow Guide

> This document provides step-by-step instructions to test the complete voter login, 2FA/MFA, and voting flow.

---

## Prerequisites

1. All Docker containers are running:
   ```powershell
   docker-compose up -d
   ```
2. Frontend is accessible at **http://localhost:3000**
3. Backend is accessible at **http://localhost:8000**
4. Backend health check returns `healthy`:
   ```
   GET http://localhost:8000/health
   ```

---

## Test 1: Basic Voter Login (No MFA)

### Steps

1. Open **http://localhost:3000** in your browser.
2. On the login screen, select **Role → Voter**.
3. Enter credential: `voter1` (valid: voter1–voter5).
4. Click **Login**.

### Expected Results

- ✅ You are logged in immediately (no MFA prompt).
- ✅ Role shown in the top bar: `voter`.
- ✅ Available tabs: **Voter Access**, **Results**, **Ledger**, **Verification**.
- ✅ No "mfa_pending" should appear anywhere.

---

## Test 2: Voter Access Dashboard (No MFA)

### Steps

1. After logging in as `voter1` (Test 1), click the **👤 Voter Access** tab.
2. You should see the **Voter Access & Credentials** dashboard directly (no second login required).

### Expected Results

- ✅ Dashboard shows "Logged in as:" and Security Settings, Election Actions.
- ✅ No login screen appears — the existing auth is reused.
- ✅ "Enable 2FA Protection" button is visible in Security Settings.

---

## Test 3: Enable 2FA (MFA Setup)

### Steps

1. In the **Voter Access** dashboard, click **Enable 2FA Protection**.
2. A secret key and provisioning URI will appear.
3. **Copy the secret key** (e.g., `ABC123XYZ...`) — you'll need this for an authenticator app or command-line OTP generation.
4. Enter the 6-digit OTP code from your authenticator app (or generate via CLI: see below).
5. Click **Activate 2FA**.

#### Generating OTP via CLI (if no authenticator app)

```powershell
docker exec evoting_backend python -c "import pyotp; print(pyotp.TOTP('YOUR_SECRET_HERE').now())"
```

Replace `YOUR_SECRET_HERE` with the secret displayed in the UI.

### Expected Results

- ✅ Message: "MFA Setup Complete: MFA Enabled".
- ✅ You remain on the dashboard (not kicked out).
- ✅ A new auth token is issued automatically — no re-login needed.
- ✅ Activity log shows: "MFA Setup Complete: MFA Enabled".

---

## Test 4: Re-Login with 2FA (MFA Login Flow)

### Steps

1. Click **Logout** (top right in the App header) to log out completely.
2. On the login screen, select **Role → Voter**, enter `voter1`, click **Login**.
3. A **Two-Factor Authentication** screen should appear asking for the 6-digit code.
4. Enter the OTP code from your authenticator (or generate via CLI as above — use the same secret from Test 3).
5. Click **Verify**.

### Expected Results

- ✅ After entering credentials, you see the OTP verification screen (NOT the main app with "mfa_pending").
- ✅ After entering a valid OTP, you are logged in with role: `voter`.
- ✅ All voter tabs are available.
- ✅ No "mfa_pending" appears in the UI.

### What to Check if It Fails

| Symptom | Cause | Fix |
|---------|-------|-----|
| Shows "mfa_pending" as role | Old localStorage data | Clear browser localStorage and retry |
| "Invalid OTP" error | OTP expired (30-sec window) | Generate a fresh OTP and try immediately |
| Stuck on login screen | Backend not reachable | Check `docker-compose ps`, restart if needed |

---

## Test 5: Voter Access with 2FA Enabled

### Steps

1. After MFA login (Test 4), click **👤 Voter Access** tab.
2. Dashboard should load directly.

### Expected Results

- ✅ Dashboard loads immediately — no second login needed.
- ✅ Security Settings shows MFA is already active.

---

## Test 6: Full Voting Flow

### Steps

1. Log in as `voter1` (with or without MFA depending on state).
2. Go to **👤 Voter Access** tab.
3. Click **Check Eligibility** → confirm "Eligible" badge appears.
4. Click **Get Blind Credential** → credential issued message appears.
5. In the **Voting Booth** section, select a candidate (e.g., Alice Johnson).
6. Click **🔎 Review & Encrypt**.
7. Review the selection, then click **🔒 Confirm and Submit**.

### Expected Results

- ✅ Eligibility check returns "Eligible" with a green badge.
- ✅ Blind credential is issued (signature is displayed).
- ✅ Candidates are displayed in the voting booth.
- ✅ After submitting, the "Vote Submitted" confirmation appears with:
  - Receipt hash
  - Timestamp
- ✅ Activity log records all steps.

---

## Test 7: Admin Login

### Steps

1. Log out from voter account.
2. Select **Role → Admin**, enter credential: `admin`, click **Login**.

### Expected Results

- ✅ Logged in as `admin`.
- ✅ All tabs visible: Results, Ledger, Trustees, Testing, Ops & Audit, Verification, Security Lab.

---

## Test 8: Other Role Logins

| Role | Credential | Expected Tabs |
|------|------------|---------------|
| Trustee | `trustee` | Trustees, Results, Ledger, Verification |
| Auditor | `auditor` | Results, Ledger, Ops & Audit, Verification |
| Security Engineer | `security_engineer` | Security Lab, Ops & Audit, Ledger, Verification |

---

## Troubleshooting

### Reset MFA for All Voters
If MFA is causing issues during testing, reset it:
```powershell
docker exec evoting_postgres psql -U admin -d evoting -c "UPDATE users SET mfa_enabled = false, mfa_secret = NULL WHERE role = 'voter';"
```

### Clear Browser State
If you see stale "mfa_pending" roles:
1. Open browser DevTools → Application → Local Storage → http://localhost:3000
2. Delete `authRole` and `authToken` entries
3. Refresh the page

### Restart All Containers
```powershell
docker-compose down
docker-compose up -d
```

### Check Backend Logs
```powershell
docker logs evoting_backend --tail 50
```

### Check Frontend Logs
```powershell
docker logs evoting_frontend --tail 50
```

---

## Quick Verification Checklist

- [ ] voter1 can log in without MFA (fresh state)
- [ ] Voter Access tab loads directly after login (no double-login)
- [ ] 2FA can be enabled from Voter Access dashboard
- [ ] After enabling 2FA, re-login shows OTP screen (not mfa_pending)
- [ ] Valid OTP completes login with role: voter
- [ ] Full voting flow works (eligibility → credential → vote → receipt)
- [ ] Admin, trustee, auditor, security_engineer logins work
- [ ] Logout fully clears session
