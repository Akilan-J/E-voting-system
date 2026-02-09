"""
FastAPI Main Application
EPIC 4: Privacy-Preserving Tallying & Result Verification
EPIC 5: Verification & Audit Ops
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
from datetime import datetime, timedelta
# Monkeypatch time.clock for passlib compatibility on Python 3.8+
if not hasattr(time, 'clock'):
    time.clock = time.time


from app.models.database import engine, Base, get_db
from app.models import auth_models
from app.routers import (
    tallying, 
    trustees, 
    results, 
    mock_data, 
    ops, 
    verification, 
    security,
    ledger,
    auth,
    voter
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_demo_data():
    """Sync initialization of demo data"""
    db = next(get_db())
    try:
        from app.models.database import Election
        from app.models.auth_models import Citizen, User
        import uuid
        import hashlib
        
        # 1. Ensure Demo Election exists
        demo_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        election = db.query(Election).filter(Election.election_id == demo_id).first()
        if not election:
            logger.info("Creating demo election...")
            now = datetime.utcnow()
            election = Election(
                election_id=demo_id,
                title="National General Election 2026",
                description="Secure, multi-trustee e-voting demonstration",
                candidates=[
                    {"id": 1, "name": "Alice Johnson", "party": "Progressive"},
                    {"id": 2, "name": "Bob Smith", "party": "Conservative"},
                    {"id": 3, "name": "Charlie Davis", "party": "Independent"}
                ],
                start_time=now,
                end_time=now + timedelta(days=1),
                status="active"
            )
            db.add(election)
            db.commit()

        # 2. Ensure Demo Citizens exist (Aadhaar Sim)
        test_credentials = ["123456789012", "987654321098", "555566667777"]
        for cred in test_credentials:
            ident_hash = hashlib.sha256(cred.encode()).hexdigest()
            if not db.query(Citizen).filter(Citizen.identity_hash == ident_hash).first():
                db.add(Citizen(
                    identity_hash=ident_hash,
                    full_name_hashed=hashlib.sha256(f"Citizen {cred}".encode()).hexdigest(),
                    is_eligible_voter=True
                ))
        
        # 3. Ensure Admin/Trustee Users exist (RBAC)
        # Admin
        admin_cred = "admin123"
        admin_hash = hashlib.sha256(admin_cred.encode()).hexdigest()
        if not db.query(User).filter(User.identity_hash == admin_hash).first():
            db.add(User(identity_hash=admin_hash, role="admin"))
            
        # Trustees (trustee1..5)
        for i in range(1, 6):
            t_cred = f"trustee{i}"
            t_hash = hashlib.sha256(t_cred.encode()).hexdigest()
            if not db.query(User).filter(User.identity_hash == t_hash).first():
                db.add(User(identity_hash=t_hash, role="trustee"))

        db.commit()
    except Exception as e:
        logger.error(f"Failed to initialize demo data: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting E-Voting System - EPIC 4 & 5")
    
    # Initialize DB tables and data
    try:
        logger.info("📊 Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("🌱 Seeding demo data...")
        init_demo_data()
        
        logger.info("✅ Database ready")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        # We don't raise here to allow the app to start (though DB endpoints will fail)
    logger.info("🔐 Cryptography services ready")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down E-Voting System")


app = FastAPI(
    title="E-Voting System API",
    description="Privacy-Preserving Tallying & Verification Ops",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )


# Include Routers
app.include_router(trustees.router, prefix="/api/trustees", tags=["trustees"])
app.include_router(mock_data.router, prefix="/api/mock", tags=["mock"])
app.include_router(tallying.router, prefix="/api/tally", tags=["tallying"])
app.include_router(results.router, prefix="/api/results", tags=["results"])
app.include_router(ops.router, prefix="/api/ops", tags=["ops"])
app.include_router(verification.router, prefix="/api/verify", tags=["verification"])
app.include_router(security.router, prefix="/api/security", tags=["security"])
app.include_router(ledger.router, prefix="/api/ledger", tags=["Ledger"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(voter.router, prefix="/api/voter", tags=["Voter"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "E-Voting System API - EPIC 4 & 5",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "epic": "Privacy-Preserving Tallying & Result Verification"
    }




# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint for Docker"""
    try:
        # Test database connection
        from sqlalchemy import text
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


# API Info endpoint
@app.get("/api/info")
async def api_info():
    """Get API information"""
    return {
        "api_name": "E-Voting System",
        "epic": "EPIC 4 - Privacy-Preserving Tallying",
        "version": "1.0.0",
        "endpoints": {
            "trustees": "/api/trustees",
            "tallying": "/api/tally",
            "results": "/api/results",
            "mock_data": "/api/mock"
        },
        "features": [
            "Homomorphic encryption aggregation",
            "Threshold decryption (3-of-5)",
            "Zero-knowledge proof verification",
            "Public result publishing",
            "Audit trail logging"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)