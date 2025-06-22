from fastapi import APIRouter
from app.api.v1.endpoints import (
    integration,
    message,
    protocol,
    health,
    auth
)

api_router = APIRouter()

# API Endpoints
api_router.include_router(
    integration.router,
    prefix="/integrations",
    tags=["integrations"]
)

api_router.include_router(
    message.router,
    prefix="/messages",
    tags=["messages"]
)

api_router.include_router(
    protocol.router,
    prefix="/protocols",
    tags=["protocols"]
)

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"]
)
