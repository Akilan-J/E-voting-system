from sqlalchemy import text
from app.models.database import engine

# Adds receipt_hash column to encrypted_votes table if missing

def column_exists(table, column):
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name=:table AND column_name=:column"
        ), {"table": table, "column": column})
        return result.first() is not None

def add_column_if_missing():
    with engine.connect() as conn:
        if not column_exists('encrypted_votes', 'receipt_hash'):
            conn.execute(text('ALTER TABLE encrypted_votes ADD COLUMN receipt_hash VARCHAR(255)'))
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_encrypted_votes_receipt_hash ON encrypted_votes (receipt_hash)'))

if __name__ == "__main__":
    add_column_if_missing()
    print("Migration complete.")
