"""
FastAPI Main Application
EPIC 4: Privacy-Preserving Tallying & Result Verification
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time


from app.models.database import engine, Base, get_db
from app.routers import (
    tallying, 
    trustees, 
    results, 
    mock_data, 
    ops, 
    verification, 
    security
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting E-Voting System - EPIC 4")
    logger.info("📊 Initializing database tables...")
    
    # Create tables (if not exists)
    Base.metadata.create_all(bind=engine)
    
    logger.info("✅ Database initialized")
    logger.info("🔐 Cryptography services ready")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down E-Voting System")


app = FastAPI(
    title="E-Voting System API",
    description="Privacy-Preserving Tallying & Result Verification (EPIC 4)",
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


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "E-Voting System API - EPIC 4",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "epic": "Privacy-Preserving Tallying & Result Verification"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
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
