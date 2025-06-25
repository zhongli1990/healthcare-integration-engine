import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Import the app from __init__.py where FastAPI app is created
from . import app

# Import routers
from .routers import imports, visualizations

# Set up templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static"
)

# Include routers
app.include_router(imports.router, prefix="/api/imports", tags=["imports"])
app.include_router(visualizations.router, prefix="/api/visualizations", tags=["visualizations"])

# Root endpoint - serves the main UI
@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "IRIS Production Importer"}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static"
)

# Include routers
from .routers import imports, visualizations  # noqa: E402
app.include_router(imports.router, prefix="/api/imports", tags=["imports"])
app.include_router(visualizations.router, prefix="/api/visualizations", tags=["visualizations"])

# Root endpoint - serves the main UI
@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "IRIS Production Importer"}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
