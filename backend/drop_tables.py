from app.models.database import Base, engine
# Import all models to ensure they are registered with Base metadata
from app.models import auth_models, ledger_models
# database.py already defines Trustee, Election, EncryptedVote, etc.

if __name__ == "__main__":
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Tables dropped successfully.")
