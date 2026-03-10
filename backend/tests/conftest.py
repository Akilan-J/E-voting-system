"""
Shared test fixtures for the E-Voting System test suite.
Ensures database tables are created before any TestClient-based tests run.
"""
import os
import pytest

# Ensure the app can find its modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all SQLAlchemy tables before tests run."""
    from app.models.database import engine, Base
    # Import all models so they register with Base.metadata
    import app.models.auth_models  # noqa: F401
    import app.models.ledger_models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield
    # Tables are left in place — CI containers are ephemeral
