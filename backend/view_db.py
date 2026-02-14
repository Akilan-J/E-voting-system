import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
from datetime import datetime

# --- Configuration ---
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
    "database": os.getenv("POSTGRES_DB", "evoting"),
    "user": os.getenv("POSTGRES_USER", "admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "secure_password"),
    "port": os.getenv("POSTGRES_PORT", "5432")
}

def format_value(v):
    if v is None: return "NULL"
    if isinstance(v, (dict, list)): return json.dumps(v)[:30] + "..." if len(json.dumps(v)) > 30 else json.dumps(v)
    if isinstance(v, datetime): return v.strftime("%Y-%m-%d %H:%M")
    return str(v)

def view_table(cur, table_name, columns):
    print(f"\n>>> TABLE: {table_name.upper()} <<<")
    try:
        query = f"SELECT {', '.join(columns)} FROM {table_name}"
        cur.execute(query)
        rows = cur.fetchall()
        
        if not rows:
            print(f"  (No records found in {table_name})")
            return

        # Print Header
        header = " | ".join(f"{col:<20}" for col in columns)
        print("-" * len(header))
        print(header)
        print("-" * len(header))

        # Print Rows
        for row in rows:
            line = " | ".join(f"{format_value(row[col]):<20}" for col in columns)
            print(line)
            
    except Exception as e:
        print(f"  Error reading {table_name}: {e}")

def main():
    print("=" * 80)
    print("      E-VOTING SYSTEM - DATABASE INSPECTOR")
    print("=" * 80)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Identity & Access
        view_table(cur, "users", ["user_id", "identity_hash", "role", "mfa_enabled"])
        view_table(cur, "citizens", ["id", "identity_hash", "is_eligible_voter"])
        
        # 2. Election Metadata
        view_table(cur, "elections", ["election_id", "title", "status", "start_time"])
        
        # 3. Anonymized Tokens
        view_table(cur, "blind_tokens", ["token_hash", "status", "election_id", "used_at"])
        
        # 4. Votes & Ledger
        view_table(cur, "encrypted_votes", ["vote_id", "election_id", "receipt_hash", "timestamp"])
        
        # 5. Audit Trail
        view_table(cur, "audit_logs", ["log_id", "operation_type", "performed_by", "status"])

        cur.close()
        conn.close()
        print("\n" + "=" * 80)
        print("Done.")
        
    except Exception as e:
        print(f"\nFATAL ERROR: Could not connect to database.\n{e}")

if __name__ == "__main__":
    main()