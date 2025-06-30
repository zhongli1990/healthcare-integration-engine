"""Message validation processor."""
import json
import logging
from typing import AsyncGenerator, Dict, Optional

from core.interfaces.processor import Processor
from core.models.message import MessageEnvelope, MessageStatus

logger = logging.getLogger(__name__)


class ValidationProcessor(Processor):
    """Processor for validating messages against schemas."""

    def __init__(self, schemas: Optional[Dict[str, dict]] = None):
        """Initialize the validation processor.
        
        Args:
            schemas: Dictionary of schema definitions
        """
        self.schemas = schemas or {}
        self.running = False
    
    async def start(self) -> None:
        """Start the processor."""
        self.running = True
        logger.info("Started validation processor")
    
    async def stop(self) -> None:
        """Stop the processor."""
        self.running = False
        logger.info("Stopped validation processor")
    
    async def process(self, message: MessageEnvelope) -> AsyncGenerator[MessageEnvelope, None]:
        """Process a message.
        
        Args:
            message: The message to process
            
        Yields:
            Processed message(s)
        """
        if not self.running:
            logger.warning("Validation processor is not running")
            return
        
        try:
            # Skip if already validated
            if message.header.status == MessageStatus.VALIDATED:
                yield message
                return
            
            # Update message status
            message.header.status = MessageStatus.VALIDATED
            
            # Get schema ID from message or content type
            schema_id = message.body.schema_id or message.body.content_type
            
            if not schema_id:
                raise ValueError("No schema ID or content type specified")
            
            # Get schema
            schema = self.schemas.get(schema_id)
            if not schema:
                logger.warning(f"No schema found for {schema_id}, skipping validation")
                yield message
                return
            
            # Validate message content
            self._validate_message(message, schema)
            
            # Add validation metadata
            if not message.body.metadata:
                message.body.metadata = {}
            
            message.body.metadata["validated"] = True
            message.body.metadata["schema_id"] = schema_id
            
            logger.debug(f"Successfully validated message {message.header.message_id}")
            yield message
            
        except Exception as e:
            await self.handle_error(e, message)
    
    def _validate_message(self, message: MessageEnvelope, schema: dict) -> None:
        """Validate a message against a schema.
        
        Args:
            message: The message to validate
            schema: The schema to validate against
            
        Raises:
            ValueError: If validation fails
        """
        # Simple validation based on schema type
        if schema.get("type") == "hl7":
            self._validate_hl7(message, schema)
        elif schema.get("type") == "json":
            self._validate_json(message, schema)
        else:
            logger.warning(f"Unknown schema type: {schema.get('type')}")
    
    def _validate_hl7(self, message: MessageEnvelope, schema: dict) -> None:
        """Validate an HL7 message.
        
        Args:
            message: The HL7 message to validate
            schema: The HL7 schema
            
        Raises:
            ValueError: If validation fails
        """
        if not message.body.raw_content:
            raise ValueError("No raw content to validate")
        
        # Convert to string if needed
        content = message.body.raw_content
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        # Basic HL7 validation
        lines = content.strip().split('\r')
        if not lines:
            raise ValueError("Empty HL7 message")
        
        # Check MSH segment
        if not lines[0].startswith('MSH|'):
            raise ValueError("Invalid HL7 message: missing MSH segment")
        
        # Check required fields in MSH segment
        msh_fields = lines[0].split('|')
        if len(msh_fields) < 12:
            raise ValueError("Invalid HL7 message: MSH segment too short")
        
        # Check message type
        if 'message_types' in schema:
            msg_type = f"{msh_fields[8]}^{msh_fields[9]}^{msh_fields[10]}^{msh_fields[11]}"
            if msg_type not in schema['message_types']:
                raise ValueError(f"Unsupported message type: {msg_type}")
    
    def _validate_json(self, message: MessageEnvelope, schema: dict) -> None:
        """Validate a JSON message.
        
        Args:
            message: The JSON message to validate
            schema: The JSON schema
            
        Raises:
            ValueError: If validation fails
        """
        # TODO: Implement JSON Schema validation
        pass
    
    async def handle_error(self, error: Exception, message: Optional[MessageEnvelope] = None) -> None:
        """Handle processing errors.
        
        Args:
            error: The exception that occurred
            message: The message being processed when the error occurred (if any)
        """
        error_msg = str(error)
        logger.error(f"Validation error: {error_msg}")
        
        if message:
            # Update message status
            message.header.status = MessageStatus.FAILED
            
            # Add error metadata
            if not message.body.metadata:
                message.body.metadata = {}
                
            if "errors" not in message.body.metadata:
                message.body.metadata["errors"] = []
                
            message.body.metadata["errors"].append({
                "type": "validation",
                "message": error_msg,
                "timestamp": message.header.timestamp.isoformat()
            })
