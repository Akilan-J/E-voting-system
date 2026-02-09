import sqlalchemy as sa
from sqlalchemy import text
from app.models.database import engine

# This script adds trustee_vote_limit and trustee_votes_verified columns to the users table if not present
# and ensures the role column supports 'security_engineer'.

def column_exists(table, column):
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='{table}' AND column_name='{column}'
        """))
        return result.first() is not None

def add_column_if_missing():
    with engine.connect() as conn:
        if not column_exists('users', 'trustee_vote_limit'):
            conn.execute(text('ALTER TABLE users ADD COLUMN trustee_vote_limit INTEGER'))
        if not column_exists('users', 'trustee_votes_verified'):
            conn.execute(text('ALTER TABLE users ADD COLUMN trustee_votes_verified INTEGER DEFAULT 0'))
        # No need to alter 'role' column for enum, as it's a string

if __name__ == "__main__":
    add_column_if_missing()
    print("Migration complete.")
