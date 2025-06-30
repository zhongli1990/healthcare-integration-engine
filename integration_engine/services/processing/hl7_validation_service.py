"""
HL7 Validation Service

Validates HL7 v2 messages against basic structural requirements.
"""
import re
import logging
from typing import Dict, Any, Tuple, Optional

from integration_engine.core.models.message import Message
from integration_engine.core.queues.queue_manager import QueueManager

logger = logging.getLogger(__name__)

class HL7ValidationService:
    """Service for validating HL7 v2 messages."""
    
    def __init__(self, queue_manager: QueueManager):
        """Initialize the validation service.
        
        Args:
            queue_manager: Queue manager for receiving and publishing messages
        """
        self.queue_manager = queue_manager
        self.required_segments = ['MSH', 'EVN', 'PID']
    
    async def start(self):
        """Start the validation service."""
        await self.queue_manager.subscribe("hl7.inbound", self._validate_message)
        logger.info("HL7 Validation Service started")
    
    async def _validate_message(self, message_data: Dict[str, Any]):
        """Validate an HL7 message.
        
        Args:
            message_data: Message data containing the HL7 content
        """
        try:
            message = Message.from_dict(message_data)
            
            if message.message_type != "HL7v2":
                logger.warning(f"Skipping non-HL7 message: {message.message_type}")
                return
            
            content = message.content
            if not content:
                raise ValueError("Empty message content")
            
            # Basic HL7 message validation
            lines = content.split('\r')
            if not lines:
                raise ValueError("No content in message")
            
            # Check MSH segment
            if not lines[0].startswith('MSH|'):
                raise ValueError("Missing or invalid MSH segment")
            
            # Extract delimiters from MSH segment
            try:
                field_delimiter = lines[0][3]
                component_delimiter = lines[0][4]
                
                # Validate delimiters
                if not all(c in '|^~\\&' for c in [field_delimiter, component_delimiter]):
                    raise ValueError("Invalid delimiters in MSH segment")
            except IndexError:
                raise ValueError("Malformed MSH segment")
            
            # Check for required segments
            segments_found = {}
            for line in lines:
                if '|' in line:  # Basic check for valid segment
                    segment_name = line.split('|')[0]
                    segments_found[segment_name] = segments_found.get(segment_name, 0) + 1
            
            missing_segments = [seg for seg in self.required_segments if seg not in segments_found]
            if missing_segments:
                raise ValueError(f"Missing required segments: {', '.join(missing_segments)}")
            
            # Add validation metadata
            message.metadata["validated_at"] = int(time.time())
            message.metadata["validation_status"] = "success"
            
            # Publish to next step
            await self.queue_manager.publish("hl7.validated", message.to_dict())
            logger.info(f"Successfully validated HL7 message")
            
        except Exception as e:
            error_msg = f"HL7 validation failed: {str(e)}"
            logger.error(error_msg)
            
            # Update message with error
            if 'message' in locals():
                message.metadata["validation_status"] = "failed"
                message.metadata["error"] = error_msg
                await self.queue_manager.publish("hl7.validation_error", message.to_dict())
            else:
                # Create error message if we couldn't parse the original
                error_message = Message(
                    message_type="HL7v2",
                    content=message_data.get("content", ""),
                    metadata={
                        **message_data.get("metadata", {}),
                        "validation_status": "failed",
                        "error": error_msg,
                        "source": "hl7_validation_service"
                    }
                )
                await self.queue_manager.publish("hl7.validation_error", error_message.to_dict())
