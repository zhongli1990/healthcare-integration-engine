from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
from app.core.config import get_settings
from app.models.message import Message
from app.models.integration import Integration
from app.utils.hl7 import HL7MessageHandler
from app.utils.dicom import DICOMMessageHandler
from app.utils.fhir import FHIRMessageHandler

settings = get_settings()

class ProtocolHandler:
    def __init__(self):
        self.handlers = {
            'hl7': HL7MessageHandler(),
            'dicom': DICOMMessageHandler(),
            'fhir': FHIRMessageHandler()
        }

    async def process_message(
        self,
        integration_id: int,
        protocol: str,
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process incoming message based on protocol
        """
        handler = self.handlers.get(protocol.lower())
        if not handler:
            raise ValueError(f"Unsupported protocol: {protocol}")

        try:
            # Validate and transform message
            processed_message = await handler.process_message(message)
            
            # Create message record
            msg = Message(
                integration_id=integration_id,
                protocol=protocol,
                original_message=message,
                processed_message=processed_message,
                status="processed",
                timestamp=datetime.utcnow()
            )
            
            # Save to database
            await msg.save()
            
            return {
                "status": "success",
                "message_id": msg.id,
                "processed_message": processed_message
            }
            
        except Exception as e:
            # Log error and update message status
            await self._handle_error(integration_id, message, str(e))
            raise

    async def _handle_error(
        self,
        integration_id: int,
        message: Dict[str, Any],
        error_message: str
    ) -> None:
        """
        Handle processing errors by logging and updating message status
        """
        msg = Message(
            integration_id=integration_id,
            protocol=message.get('protocol', 'unknown'),
            original_message=message,
            error=error_message,
            status="error",
            timestamp=datetime.utcnow()
        )
        await msg.save()

    async def get_message_status(self, message_id: int) -> Dict[str, Any]:
        """
        Get status of a processed message
        """
        msg = await Message.get(message_id)
        if not msg:
            raise ValueError(f"Message not found: {message_id}")
            
        return {
            "status": msg.status,
            "processed_at": msg.timestamp,
            "error": msg.error
        }
