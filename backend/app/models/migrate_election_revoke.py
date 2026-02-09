from sqlalchemy import text
from app.models.database import engine

# Adds revoke_all column to elections table if missing

def column_exists(table, column):
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name=:table AND column_name=:column"
        ), {"table": table, "column": column})
        return result.first() is not None

def add_column_if_missing():
    with engine.connect() as conn:
        if not column_exists('elections', 'revoke_all'):
            conn.execute(text('ALTER TABLE elections ADD COLUMN revoke_all BOOLEAN DEFAULT FALSE'))

if __name__ == "__main__":
    add_column_if_missing()
    print("Migration complete.")
