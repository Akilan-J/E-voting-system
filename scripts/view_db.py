
import os
import sys
from sqlalchemy import create_engine, text, inspect

# Database Configuration
POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "secure_password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "evoting")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

def print_table(name, columns, rows):
    print(f"\n{'='*80}")
    print(f" TABLE: {name}")
    print(f"{'='*80}")
    
    if not rows:
        print("(No data)")
        return

    # Calculate column widths
    widths = [len(c) for c in columns]
    for row in rows:
        for i, val in enumerate(row):
            str_val = str(val)
            if len(str_val) > widths[i]:
                widths[i] = min(len(str_val), 50) # Cap width at 50 chars

    # Create format string
    fmt = " | ".join([f"{{:<{w}}}" for w in widths])
    
    # Print header
    print(fmt.format(*columns))
    print("-" * (sum(widths) + 3 * (len(columns) - 1)))
    
    # Print rows
    for row in rows:
        formatted_row = []
        for i, val in enumerate(row):
            str_val = str(val)
            if len(str_val) > 50:
                str_val = str_val[:47] + "..."
            formatted_row.append(str_val)
        print(fmt.format(*formatted_row))
    print(f"Total rows: {len(rows)}")

def main():
    print(f"Connecting to database: {DATABASE_URL}")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            
            if not table_names:
                print("No tables found in the database.")
                return

            print(f"Found {len(table_names)} tables: {', '.join(table_names)}")

            for table in table_names:
                # Get columns
                columns = [col['name'] for col in inspector.get_columns(table)]
                
                # Get data
                result = connection.execute(text(f"SELECT * FROM {table}"))
                rows = result.fetchall()
                
                print_table(table, columns, rows)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
