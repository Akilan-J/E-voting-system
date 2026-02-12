"""
Quick MFA Code Generator
Run this to get your current 6-digit code
"""

import pyotp

# Your MFA secret
SECRET = "OUINEERXLDSSO6QM7HFNZ4G55FU56MN2"

# Generate current code
totp = pyotp.TOTP(SECRET)
code = totp.now()

print("\n" + "=" * 50)
print("  E-VOTING SYSTEM - MFA CODE")
print("=" * 50)
print(f"\n  🔑 Your 6-digit code: {code}")
print("\n  ⏱️  Valid for ~30 seconds")
print("\n" + "=" * 50)
print("\nUse this code to login with MFA")
print("Run this script again if the code expires\n")
