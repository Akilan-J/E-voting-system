import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Connect to the database
try:
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', '127.0.0.1'),
        database=os.getenv('POSTGRES_DB', 'evoting'),
        user=os.getenv('POSTGRES_USER', 'admin'),
        password=os.getenv('POSTGRES_PASSWORD', 'secure_password')
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Select user info and secrets
    cur.execute('SELECT identity_hash, role, mfa_secret FROM users WHERE mfa_enabled=True')
    rows = cur.fetchall()
    
    print("\n" + "=" * 60)
    print(f"  {'ROLE':<15} | {'IDENTITY (HASH)':<20} | {'MFA SECRET'}")
    print("-" * 60)
    
    if not rows:
        print("  No users found with MFA enabled.")
    else:
        for r in rows:
            ident = r['identity_hash'][:15] + "..."
            secret = r['mfa_secret'] if r['mfa_secret'] else "NOT SET"
            print(f"  {r['role']:<15} | {ident:<20} | {secret}")
    
    print("=" * 60 + "\n")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error connecting to database: {e}")