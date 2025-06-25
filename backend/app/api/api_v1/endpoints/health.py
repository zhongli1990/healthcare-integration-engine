import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health", status_code=200, tags=["health"])
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint that verifies the API and database connectivity.
    Returns 200 if the API is running and can connect to the database.
    """
    try:
        # Test database connection with a simple query
        logger.info("Testing database connection...")
        result = db.execute(text("SELECT 1")).scalar()
        logger.info(f"Database connection test result: {result}")
        
        if result != 1:
            raise ValueError("Unexpected database response")
            
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
        
    except Exception as e:
        error_msg = f"Health check failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Try to get more detailed error information
        db_status = "unknown"
        try:
            # Try to get database version as an additional test
            db_version = db.execute(text("SELECT version()")).scalar()
            db_status = f"connected (version: {db_version})"
        except Exception as db_error:
            db_status = f"connection failed: {str(db_error)}"
        
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": db_status,
                "error": str(e),
                "type": type(e).__name__
            }
        )
