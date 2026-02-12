"""
Generate TOTP codes for MFA login
Run this to get your 6-digit authentication code
"""

import pyotp
import time

# Your MFA secret
SECRET = "6DUAONKNMSTR7M6I4K7QQX43KY7IORO7"

# Create TOTP object
totp = pyotp.TOTP(SECRET)

print("=" * 60)
print("E-VOTING SYSTEM - MFA CODE GENERATOR")
print("=" * 60)
print(f"\nSecret: {SECRET}")
print("\nGenerating codes (updates every 30 seconds)...")
print("Press Ctrl+C to stop\n")
print("-" * 60)

try:
    while True:
        # Get current code
        current_code = totp.now()
        
        # Calculate time remaining
        time_remaining = 30 - (int(time.time()) % 30)
        
        # Display
        print(f"\r🔑 Current Code: {current_code}  |  ⏱️  Valid for: {time_remaining:2d} seconds", end="", flush=True)
        
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\n\n✓ Stopped")
