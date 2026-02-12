# How to Get Your 6-Digit MFA Code

## 🎯 Quick Answer

Run this command in your backend folder:

```bash
python get_mfa_code.py
```

This will show your current 6-digit code (valid for ~30 seconds).

---

## 📱 Method 1: Using Python Script (Easiest for Testing)

### **Step 1: Generate Code**
```bash
cd backend
python get_mfa_code.py
```

### **Step 2: Copy the Code**
You'll see something like:
```
==================================================
  E-VOTING SYSTEM - MFA CODE
==================================================

  🔑 Your 6-digit code: 422869

  ⏱️  Valid for ~30 seconds

==================================================
```

### **Step 3: Use It to Login**
1. Go to `http://localhost:3000`
2. Enter your credential
3. When prompted for MFA code, enter: `422869`
4. Submit

**Note:** The code changes every 30 seconds. If it expires, run the script again!

---

## 📱 Method 2: Using Authenticator App (Recommended for Real Use)

### **Step 1: Install App**
Download any of these free apps:
- **Google Authenticator** (iOS/Android)
- **Microsoft Authenticator** (iOS/Android)
- **Authy** (iOS/Android/Desktop)

### **Step 2: Add Account**
1. Open the app
2. Tap "+" or "Add Account"
3. Choose "Enter Setup Key" or "Manual Entry"
4. Fill in:
   - **Account Name:** E-Voting System
   - **Your Key:** `6DUAONKNMSTR7M6I4K7QQX43KY7IORO7`
   - **Type of Key:** Time-based

### **Step 3: Get Code**
- The app will show a 6-digit code
- Code updates every 30 seconds automatically
- Use it whenever you need to login

---

## 🔄 Method 3: Live Code Generator (Continuous Updates)

If you want to see codes updating in real-time:

```bash
python generate_mfa_code.py
```

This will show:
```
🔑 Current Code: 422869  |  ⏱️  Valid for: 25 seconds
```

Press `Ctrl+C` to stop.

---

## 🚀 Complete Login Flow

### **Without MFA:**
1. Go to `http://localhost:3000`
2. Enter credential (e.g., `admin`, `trustee1`, or voter ID)
3. Click "Login"
4. ✓ You're in!

### **With MFA Enabled:**
1. Go to `http://localhost:3000`
2. Enter credential
3. Click "Login"
4. **MFA Prompt appears** 🔐
5. Run: `python get_mfa_code.py`
6. Copy the 6-digit code
7. Enter it in the MFA field
8. Submit
9. ✓ You're in!

---

## 🔧 Troubleshooting

### **"Invalid OTP" Error**
- ✅ Make sure your computer time is correct (TOTP depends on accurate time)
- ✅ Enter the code within 30 seconds
- ✅ Don't add spaces when entering the code
- ✅ Run the script again to get a fresh code

### **"MFA Not Setup" Error**
This account doesn't have MFA enabled. You can:
- Login normally without MFA
- Or enable MFA via the API: `POST /auth/mfa/setup`

### **Code Keeps Changing**
- This is normal! TOTP codes change every 30 seconds for security
- Just run `python get_mfa_code.py` again to get the current code

---

## 📋 Which Accounts Have MFA?

Check your database:

```bash
python -c "
from app.models.database import get_db
from app.models.auth_models import User

db = next(get_db())
users_with_mfa = db.query(User).filter(User.mfa_enabled == True).all()

print('Users with MFA enabled:')
for user in users_with_mfa:
    print(f'  - {user.identity_hash[:16]}... (role: {user.role})')
"
```

---

## 🎓 For Your Teacher Demo

### **Show MFA in Action:**

1. **Setup:**
   ```bash
   # Terminal 1: Run code generator
   python generate_mfa_code.py
   
   # Terminal 2: Keep it visible
   # Shows live updating codes
   ```

2. **Demo:**
   - Open browser to login page
   - Enter credential for MFA-enabled account
   - Point to the terminal showing the code
   - Enter the current code
   - Explain: "The code changes every 30 seconds for security"

3. **Explain:**
   - "This is TOTP (Time-based One-Time Password)"
   - "Same technology used by Google, Microsoft, GitHub"
   - "Adds second factor of authentication"
   - "Even if password is stolen, attacker needs the code"

---

## 🔐 Security Note

**For Production:**
- Users would use their own authenticator apps
- Secret keys are unique per user
- Stored encrypted in database
- Never share secrets in logs or UI

**For Demo/Testing:**
- We're using a hardcoded secret for convenience
- Real system would generate unique secrets per user
- Each user would scan their own QR code

---

## 📱 QR Code Alternative

If you want to use a QR code instead:

```python
import pyotp
import qrcode

secret = "6DUAONKNMSTR7M6I4K7QQX43KY7IORO7"
uri = pyotp.totp.TOTP(secret).provisioning_uri(
    name="demo@evoting",
    issuer_name="E-Voting System"
)

# Generate QR code
qr = qrcode.make(uri)
qr.save("mfa_qr.png")
print("QR code saved to mfa_qr.png")
print("Scan with your authenticator app!")
```

Then scan `mfa_qr.png` with your authenticator app.

---

## ✅ Quick Reference

| Task | Command |
|------|---------|
| Get current code | `python get_mfa_code.py` |
| Watch codes update | `python generate_mfa_code.py` |
| Check MFA users | See database query above |
| Enable MFA | `POST /auth/mfa/setup` |
| Verify MFA | `POST /auth/mfa/verify` |

---

**Remember:** The code is `422869` right now, but it will change in a few seconds! Run the script to get the current one. 🔐
