from fastapi import APIRouter, status, FastAPI, Depends
from typing import List, Dict, Any, Callable
from pydantic import BaseModel
import logging
from sqlalchemy.orm import Session

# Configure logger
logger = logging.getLogger(__name__)

from .endpoints import hl7 as hl7_endpoints
from .deps import start_hl7_services, stop_hl7_services

# Import endpoints from api_v1
from app.api.api_v1.endpoints import health as health_endpoints
auth_endpoints = __import__('app.api.api_v1.endpoints.auth', fromlist=['router'])
user_endpoints = __import__('app.api.api_v1.endpoints.users', fromlist=['router'])

# Import database session
try:
    from app.db.session import SessionLocal
except ImportError:
    # Fallback for testing
    SessionLocal = None

# Response Models
class HealthCheckResponse(BaseModel):
    status: str
    service: str
    version: str = "1.0.0"

class ProtocolListResponse(BaseModel):
    protocols: List[str]
    description: str = "List of supported healthcare data exchange protocols"

def create_api_router() -> APIRouter:
    # Create router without prefix since we'll add it in main.py
    router = APIRouter(
        tags=["API v1"],
        responses={
            status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Server Error"}
        }
    )
    
    # Include all endpoints under their respective prefixes
    router.include_router(hl7_endpoints.router, prefix="/hl7", tags=["HL7"])
    
    # Include health, auth, and user endpoints from api_v1
    if hasattr(health_endpoints, 'router'):
        router.include_router(health_endpoints.router, prefix="/health", tags=["health"])
    
    if hasattr(auth_endpoints, 'router'):
        router.include_router(auth_endpoints.router, prefix="/auth", tags=["auth"])
    
    if hasattr(user_endpoints, 'router'):
        router.include_router(user_endpoints.router, prefix="/users", tags=["users"])
    
    return router

# Create the router
router = create_api_router()

def register_startup_events(app: FastAPI) -> None:
    """Register startup event handlers"""
    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info("Starting up HL7 services...")
        try:
            await start_hl7_services()
            logger.info("HL7 services started successfully")
        except Exception as e:
            logger.error(f"Failed to start HL7 services: {e}")
            raise

def register_shutdown_events(app: FastAPI) -> None:
    """Register shutdown event handlers"""
    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info("Shutting down HL7 services...")
        try:
            await stop_hl7_services()
            logger.info("HL7 services stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping HL7 services: {e}")

@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check if the API is running and healthy"
)
async def health_check():
    """
    Health check endpoint that returns the current status of the API.
    """
    # TODO: Add actual health checks for services
    return {
        "status": "healthy",
        "service": "Healthcare Integration Engine",
        "version": "1.0.0",
        "services": {
            "hl7_processor": "running"
        }
    }

@router.get(
    "/protocols",
    response_model=ProtocolListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Supported Protocols",
    description="Returns a list of healthcare data exchange protocols supported by this API"
)
async def list_supported_protocols():
    """
    Retrieve all supported healthcare data exchange protocols.
    
    Returns:
        ProtocolListResponse: Object containing list of supported protocols
    """
    return {
        "protocols": [
            "HL7 - Health Level Seven International",
            "DICOM - Digital Imaging and Communications in Medicine",
            "FHIR - Fast Healthcare Interoperability Resources",
            "LDAP - Lightweight Directory Access Protocol",
            "REST - Representational State Transfer"
        ],
        "description": "Supported healthcare data exchange protocols"
    }
