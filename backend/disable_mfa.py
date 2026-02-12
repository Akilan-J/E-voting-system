"""
Disable MFA for all users
Run this to turn off MFA so you can login with just username
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import get_db
from app.models.auth_models import User

def disable_all_mfa():
    db = next(get_db())
    
    try:
        # Get all users with MFA enabled
        users_with_mfa = db.query(User).filter(User.mfa_enabled == True).all()
        
        if not users_with_mfa:
            print("✓ No users have MFA enabled")
            return
        
        print(f"Found {len(users_with_mfa)} users with MFA enabled:")
        for user in users_with_mfa:
            print(f"  - {user.identity_hash[:16]}... (role: {user.role})")
        
        # Disable MFA for all
        for user in users_with_mfa:
            user.mfa_enabled = False
            user.mfa_secret = None
        
        db.commit()
        
        print(f"\n✓ Disabled MFA for {len(users_with_mfa)} users")
        print("\nYou can now login with just:")
        print("  - Username: admin")
        print("  - No OTP required!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("DISABLE MFA FOR ALL USERS")
    print("=" * 60)
    print()
    
    disable_all_mfa()
    
    print("\n" + "=" * 60)
    print("✓ Done! You can now login without OTP")
    print("=" * 60)
