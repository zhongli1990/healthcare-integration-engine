from fastapi import APIRouter, HTTPException, status, UploadFile, File, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.core.hl7.processor import HL7Processor
from app.core.hl7.file_watcher import HL7FileWatcher
from ..deps import get_hl7_processor, get_hl7_watcher

logger = logging.getLogger(__name__)
router = APIRouter()

class HL7ProcessRequest(BaseModel):
    """Request model for processing HL7 content"""
    content: str = Field(..., description="Raw HL7 message content")

class HL7ProcessResponse(BaseModel):
    """Response model for processed HL7 message"""
    message_id: str
    message_type: str
    status: str = "processed"
    details: Optional[Dict[str, Any]] = None

class HL7StatsResponse(BaseModel):
    """Response model for HL7 processing statistics"""
    processed: int = 0
    errors: int = 0

@router.post(
    "/process",
    response_model=HL7ProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Process HL7 Message",
    description="Process a single HL7 message"
)
async def process_hl7_message(
    request: HL7ProcessRequest,
    processor: HL7Processor = Depends(get_hl7_processor)
) -> HL7ProcessResponse:
    """Process an HL7 message from request body"""
    try:
        # In a real implementation, we would process the message here
        # For now, we'll just return a mock response
        return HL7ProcessResponse(
            message_id="MSG12345",
            message_type="ADT^A01",
            status="processed",
            details={"segments_processed": 5}
        )
    except Exception as e:
        logger.error(f"Error processing HL7 message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process HL7 message: {str(e)}"
        )

@router.post(
    "/upload",
    response_model=HL7ProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload HL7 File",
    description="Upload an HL7 file for processing"
)
async def upload_hl7_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    processor: HL7Processor = Depends(get_hl7_processor)
) -> HL7ProcessResponse:
    """Upload and process an HL7 file"""
    if not file.filename.endswith('.hl7'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .hl7 files are accepted"
        )
    
    try:
        # In a real implementation, we would save and process the file here
        # For now, we'll just return a mock response
        return HL7ProcessResponse(
            message_id=f"FILE_{hash(file.filename)}",
            message_type="ADT^A01",
            status="queued",
            details={"filename": file.filename}
        )
    except Exception as e:
        logger.error(f"Error processing uploaded file {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process file: {str(e)}"
        )

@router.get(
    "/stats",
    response_model=HL7StatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get HL7 Processing Statistics",
    description="Get statistics about processed HL7 messages"
)
async def get_hl7_stats(
    processor: HL7Processor = Depends(get_hl7_processor)
) -> HL7StatsResponse:
    """Get HL7 processing statistics"""
    stats = processor.get_stats()
    return HL7StatsResponse(**stats)
