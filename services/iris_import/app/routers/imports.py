import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.import_service import ImportService
from app.services.neo4j_service import neo4j_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

router = APIRouter()

class ImportRequest(BaseModel):
    production_file: str
    routing_rule_file: str
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "healthcare123"

class ImportResponse(BaseModel):
    success: bool
    message: str
    import_id: Optional[str] = None
    details: Optional[dict] = None

# In-memory storage for imports (replace with database in production)
imports_db = {}

def _get_import_status(import_id: str) -> Dict[str, Any]:
    """Get the status of an import by ID.
    
    Args:
        import_id: The ID of the import to check
        
    Returns:
        Dict containing the import status and details
    """
    if import_id not in imports_db:
        return {
            "status": "not_found",
            "message": f"Import with ID {import_id} not found"
        }
    
    return imports_db[import_id]

def _save_uploaded_file(upload_file: UploadFile, upload_dir: Path) -> str:
    """Save an uploaded file and return its path."""
    try:
        # Create upload directory if it doesn't exist
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate a unique filename
        file_ext = Path(upload_file.filename).suffix
        file_name = f"{uuid.uuid4()}{file_ext}"
        file_path = upload_dir / file_name
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
            
        logger.info(f"Saved uploaded file to {file_path}")
        return str(file_path)
        
    except Exception as e:
        logger.error(f"Error saving uploaded file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving uploaded file: {str(e)}"
        )

@router.post("", response_model=ImportResponse)
async def import_production(
    request: ImportRequest,
    background_tasks: BackgroundTasks
):
    """
    Import an IRIS production into Neo4j.
    
    This endpoint starts an asynchronous import process and returns immediately with a task ID.
    Use the GET /imports/{import_id} endpoint to check the status.
    """
    import_id = f"import_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    # Initialize the import status
    imports_db[import_id] = {
        "status": "pending",
        "start_time": datetime.utcnow(),
        "end_time": None,
        "details": {
            "production_file": request.production_file,
            "routing_rule_file": request.routing_rule_file,
            "neo4j_uri": request.neo4j_uri,
            "progress": 0,
            "message": "Starting import..."
        },
        "result": None
    }
    
    # Start the import in the background
    background_tasks.add_task(
        _process_import,
        import_id=import_id,
        production_file=request.production_file,
        routing_rule_file=request.routing_rule_file,
        neo4j_uri=request.neo4j_uri,
        neo4j_user=request.neo4j_user,
        neo4j_password=request.neo4j_password
    )
    
    return ImportResponse(
        success=True,
        message="Import started successfully. Use the import_id to check status.",
        import_id=import_id,
        details=imports_db[import_id]["details"]
    )

def _process_import(
    import_id: str,
    production_file: str,
    routing_rule_file: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str
):
    """Process the import in the background."""
    try:
        # Update status to in-progress
        imports_db[import_id]["status"] = "in_progress"
        imports_db[import_id]["details"]["message"] = "Import in progress..."
        imports_db[import_id]["details"]["progress"] = 10
        
        # Initialize the import service
        import_service = ImportService(neo4j_uri, neo4j_user, neo4j_password)
        
        try:
            # Run the import
            result = import_service.import_production(production_file, routing_rule_file)
            
            # Update status based on result
            if result.get("success", False):
                imports_db[import_id]["status"] = "completed"
                imports_db[import_id]["details"]["message"] = "Import completed successfully"
                imports_db[import_id]["details"]["progress"] = 100
                imports_db[import_id]["details"].update(result)
                imports_db[import_id]["result"] = result
            else:
                imports_db[import_id]["status"] = "failed"
                imports_db[import_id]["details"]["message"] = f"Import failed: {result.get('message', 'Unknown error')}"
                imports_db[import_id]["details"]["progress"] = 0
                imports_db[import_id]["result"] = result
                
        except Exception as e:
            logger.error(f"Error during import processing: {str(e)}", exc_info=True)
            imports_db[import_id]["status"] = "failed"
            imports_db[import_id]["details"]["message"] = f"Error during import: {str(e)}"
            imports_db[import_id]["details"]["progress"] = 0
            imports_db[import_id]["result"] = {"error": str(e)}
            
    except Exception as e:
        logger.error(f"Unexpected error in background task: {str(e)}", exc_info=True)
        if import_id in imports_db:
            imports_db[import_id]["status"] = "failed"
            imports_db[import_id]["details"]["message"] = f"Unexpected error: {str(e)}"
            imports_db[import_id]["details"]["progress"] = 0
    finally:
        if import_id in imports_db and imports_db[import_id]["end_time"] is None:
            imports_db[import_id]["end_time"] = datetime.utcnow()
        
        # Ensure the Neo4j driver is closed
        if 'import_service' in locals():
            import_service.close()

@router.post("/upload", response_model=Dict[str, str])
async def upload_files(
    production_file: UploadFile = File(..., description="IRIS Production .cls file"),
    routing_rule_file: UploadFile = File(..., description="IRIS Routing Rule .cls file")
):
    """
    Upload IRIS production and routing rule files.
    
    Returns the paths to the saved files which can be used with the import endpoint.
    """
    try:
        logger.info(f"Received file upload request for {production_file.filename} and {routing_rule_file.filename}")
        
        # Create upload directory if it doesn't exist
        upload_dir = Path("uploads")
        
        # Save uploaded files
        production_path = _save_uploaded_file(production_file, upload_dir)
        routing_rule_path = _save_uploaded_file(routing_rule_file, upload_dir)
        
        logger.info(f"Files saved successfully: {production_path}, {routing_rule_path}")
        
        return {
            "production_file": production_path,
            "routing_rule_file": routing_rule_path,
            "message": "Files uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading files: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading files: {str(e)}"
        )

@router.get("/{import_id}", response_model=dict)
async def get_import_status(import_id: str):
    """
    Get the status of a specific import.
    
    Returns the current status, progress, and any results or errors.
    """
    # Get the import status
    status_info = _get_import_status(import_id)
    
    if status_info["status"] == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Import with ID {import_id} not found"
        )
    
    # Get Neo4j stats if the import is completed
    graph_stats = {}
    if status_info.get("status") == "completed":
        try:
            with neo4j_service.driver.session() as session:
                # Get node counts by type
                node_counts = session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] as label, count(*) as count
                    ORDER BY count DESC
                """).data()
                
                # Get relationship counts by type
                rel_counts = session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) as type, count(*) as count
                    ORDER BY count DESC
                """).data()
                
                graph_stats = {
                    "node_counts": node_counts,
                    "relationship_counts": rel_counts
                }
        except Exception as e:
            logger.warning(f"Could not get Neo4j stats: {str(e)}")
            graph_stats = {"error": f"Could not get Neo4j stats: {str(e)}"}
    
    # Prepare the response
    response = {
        "import_id": import_id,
        "status": status_info["status"],
        "message": status_info.get("details", {}).get("message", ""),
        "progress": status_info.get("details", {}).get("progress", 0),
        "details": status_info.get("details", {}),
        "start_time": status_info.get("start_time"),
        "end_time": status_info.get("end_time"),
        "graph_stats": graph_stats
    }
    
    # Add result if available
    if "result" in status_info and status_info["result"] is not None:
        response["result"] = status_info["result"]
    
    return response
