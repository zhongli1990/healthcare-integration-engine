import logging
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from starlette.middleware.sessions import SessionMiddleware
from starlette_prometheus import metrics, PrometheusMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.api import router as v1_router, register_startup_events, register_shutdown_events
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.core.exceptions import APIException
from app.db.base import Base
from app.db.session import engine

app = FastAPI(
    title="Healthcare Integration Engine",
    description="Enterprise-grade healthcare integration engine supporting multiple protocols",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(PrometheusMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Error handling
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# Register startup/shutdown events
register_startup_events(app)
register_shutdown_events(app)

# API routes
app.include_router(api_router, prefix="/api/v1")
app.include_router(v1_router, prefix="/api/v1")  # Legacy API routes

# Prometheus metrics
app.add_route("/metrics", metrics)

# Custom OpenAPI schema for better documentation
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Healthcare Integration Engine",
        version="1.0.0",
        description="Enterprise-grade healthcare integration engine supporting multiple protocols",
        routes=app.routes,
    )
    
    # Add custom documentation here if needed
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create database tables (in development)
if settings.DEBUG:
    Base.metadata.create_all(bind=engine)
