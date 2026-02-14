# MFA Code Guide

How to get the 6-digit MFA code for logging in with two-factor authentication enabled.

---

## Method 1: Python Script (quickest for testing)

```bash
cd backend
python get_mfa_code.py
```

This prints the current 6-digit code. It is valid for about 30 seconds. If it expires, run the script again.

---

## Method 2: Authenticator App

Install any TOTP-compatible authenticator app (Google Authenticator, Microsoft Authenticator, Authy, etc.).

1. Open the app and tap Add Account or the + button
2. Choose "Enter Setup Key" or "Manual Entry"
3. Enter the following:
   - Account Name: E-Voting System
   - Key: `6DUAONKNMSTR7M6I4K7QQX43KY7IORO7`
   - Type: Time-based
4. The app will display a 6-digit code that refreshes every 30 seconds
5. Use this code when prompted during login

---

## Method 3: Continuous Code Display

For testing, you can run a script that continuously shows the current code:

```bash
cd backend
python generate_mfa_code.py
```

This refreshes the displayed code every few seconds so you can grab it right before entering it.

---

## Method 4: Docker (if running with containers)

```bash
docker exec evoting_backend python -c "import pyotp; print(pyotp.TOTP('6DUAONKNMSTR7M6I4K7QQX43KY7IORO7').now())"
```

---

## Troubleshooting

**Code rejected / "Invalid OTP"** - The code is time-sensitive (30-second window). Generate a fresh one and enter it immediately.

**MFA locked out** - Reset MFA for all voters:
```bash
docker exec evoting_postgres psql -U admin -d evoting -c "UPDATE users SET mfa_enabled = false, mfa_secret = NULL WHERE role = 'voter';"
```

**Want to disable MFA entirely for a voter** - Run the disable script:
```bash
cd backend
python disable_mfa.py
```
