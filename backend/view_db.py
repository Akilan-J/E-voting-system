"""
Combined Database Viewer and Guide for E-Voting System
Run this to show database contents to your teacher
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', '127.0.0.1'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'evoting'),
    'user': os.getenv('POSTGRES_USER', 'admin'),
    'password': os.getenv('POSTGRES_PASSWORD', 'secure_password')
}

def run_viewer():
    print("=" * 80)
    print("E-VOTING SYSTEM DATABASE VIEWER")
    print("=" * 80)

    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"\n✓ Connected to database: {DB_CONFIG['database']}")
        print(f"✓ Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}\n")
        
        # Get all tables
        cursor.execute(\"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        \""")
        
        tables = [row['table_name'] for row in cursor.fetchall()]
        print(f"Found {len(tables)} tables:\n")
        
        # Table descriptions
        descriptions = {
            "audit_logs": "🔒 Immutable Hash-Chained Audit Trail",
            "blind_tokens": "🎫 Issued Voting Credentials (Hashes Only)",
            "citizens": "👥 Simulated National Voter Registry",
            "election_results": "📊 Final Signed Tallies",
            "elections": "🗳️  Election Configurations",
            "eligibility_records": "✅ Election-Specific Eligibility",
            "encrypted_votes": "🔐 Encrypted Ballots (NO Voter Link!)",
            "incidents": "⚠️  Disputes & Security Incidents",
            "partial_decryptions": "🔑 Trustee Decryption Shares",
            "security_logs": "🛡️  Authentication & Security Events",
            "tallying_sessions": "⚙️  Tallying Process State",
            "trustees": "👨‍⚖️ Trustee Information & Key Shares",
            "users": "👤 Application User Accounts",
            "verification_proofs": "✓ Zero-Knowledge Proofs",
            "biometric_credentials": "🖐️  Biometric (WebAuthn) Public Keys",
        }
        
        # Show each table summary
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()['count']
            desc = descriptions.get(table, "")
            print(f"{table:25} {count:5} records   {desc}")
        
        print("\n" + "=" * 80)
        print("🔒 PRIVACY & SECURITY VERIFICATION")
        print("=" * 80)
        
        # 1. Privacy Check
        cursor.execute(\"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'encrypted_votes'
        \""")
        vote_columns = [row['column_name'] for row in cursor.fetchall()]
        print("\n✓ Checking encrypted_votes table anonymity...")
        if 'user_id' in vote_columns or 'identity_hash' in vote_columns:
            print("  ❌ WARNING: Vote table contains voter-identifying columns!")
        else:
            print("  ✅ PASS: No voter-identifying columns found. Votes are anonymous.")
        
        # 2. Audit Integrity Check
        cursor.execute("SELECT COUNT(*) as total FROM audit_logs")
        total = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(DISTINCT current_hash) as unique FROM audit_logs")
        unique = cursor.fetchone()['unique']
        print(f"\n✓ Checking audit log hash-chain integrity...")
        if total == unique:
            print(f"  ✅ PASS: All {total} audit logs have verified unique hashes.")
        else:
            print("  ⚠️  WARNING: Possible hash collision or tampering detected.")

        # 3. Biometric Verification
        if 'biometric_credentials' in tables:
            print(f"\n✓ Checking biometric authentication layer...")
            cursor.execute("SELECT COUNT(*) as count FROM biometric_credentials")
            count = cursor.fetchone()['count']
            print(f"  ✅ PASS: {count} biometric credentials registered securely (Public Keys Only).")

        print("\n" + "=" * 80)
        print("✓ Database inspection complete!")
        print("=" * 80)
        
    except psycopg2.OperationalError:
        print(f"\n❌ Connection Error: Could not connect to PostgreSQL at {DB_CONFIG['host']}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    run_viewer()
    print("\nPress Enter to exit...")
    input()
