import json
import logging
from typing import Any, Dict, Optional, Tuple, Union

from core.models.message import MessageEnvelope, MessageHeader, MessageBody
from core.schemas.schema_registry import SchemaRegistry, SchemaValidationError
from core.services.base_service import BaseService
from core.queues.queue_manager import QueueConfig

logger = logging.getLogger(__name__)


class ParserService(BaseService):
    """Service for parsing and validating messages against schemas."""
    
    def __init__(
        self,
        input_queue: str = "raw_messages",
        output_queue: str = "parsed_messages",
        error_queue: str = "parser_errors",
        schema_registry: Optional[SchemaRegistry] = None,
        **kwargs
    ):
        super().__init__(name="parser_service", **kwargs)
        self.input_queue_name = input_queue
        self.output_queue_name = output_queue
        self.error_queue_name = error_queue
        self.schema_registry = schema_registry or SchemaRegistry()
        
        # Default message type to schema ID mapping
        self.message_type_mapping = {
            "hl7v2": {
                "ADT_A01": "hl7v2.ADT_A01",
                "ADT_A28": "hl7v2.ADT_A28",
                # Add more HL7 message types as needed
            },
            "fhir": {
                "Patient": "fhir.Patient",
                "Encounter": "fhir.Encounter",
                # Add more FHIR resource types as needed
            }
        }
    
    async def on_start(self) -> None:
        """Start the parser service."""
        # Initialize queues
        self.input_queue = await self.queue_manager.get_queue(self.input_queue_name)
        self.output_queue = await self.queue_manager.get_queue(self.output_queue_name)
        self.error_queue = await self.queue_manager.get_queue(self.error_queue_name)
        
        # Start the message processing loop
        self.create_task(self._process_messages())
    
    async def _process_messages(self) -> None:
        """Process messages from the input queue."""
        try:
            async for message_id, message in self.input_queue.consume():
                try:
                    # Clone the message to avoid modifying the original
                    parsed_message = message.clone()
                    
                    # Parse and validate the message
                    await self._parse_message(parsed_message)
                    
                    # Update message status
                    parsed_message.header.status = "parsed"
                    
                    # Forward to the output queue
                    await self.output_queue.publish(parsed_message)
                    await self.input_queue.ack(message_id)
                    
                except SchemaValidationError as e:
                    logger.error(f"Schema validation error: {e}")
                    message.header.metadata["error"] = str(e)
                    await self.error_queue.publish(message)
                    await self.input_queue.ack(message_id)
                    
                except Exception as e:
                    logger.exception(f"Error processing message: {e}")
                    message.header.metadata["error"] = str(e)
                    await self.error_queue.publish(message)
                    await self.input_queue.ack(message_id)
                    
        except asyncio.CancelledError:
            logger.info("Message processing cancelled")
            raise
        except Exception as e:
            logger.exception("Error in message processing loop")
            raise
    
    async def _parse_message(self, message: MessageEnvelope) -> None:
        """Parse and validate a message."""
        if not message.body.raw_content:
            raise ValueError("Message has no raw content to parse")
        
        # Determine message type and schema
        message_type = message.header.message_type
        schema_id = self._get_schema_id(message_type, message.body.content_type)
        
        if not schema_id:
            raise ValueError(f"No schema found for message type: {message_type}")
        
        # Parse the raw content based on content type
        if message.body.content_type == "application/hl7-v2+er7":
            parsed = self._parse_hl7v2(message.body.raw_content)
        elif message.body.content_type == "application/fhir+json":
            parsed = self._parse_fhir(message.body.raw_content)
        else:
            raise ValueError(f"Unsupported content type: {message.body.content_type}")
        
        # Validate against the schema
        self.schema_registry.validate(schema_id, parsed)
        
        # Update the message body with parsed content
        message.body.content = parsed
        message.body.schema_id = schema_id
    
    def _get_schema_id(self, message_type: str, content_type: str) -> str:
        """Get the schema ID for a message type and content type."""
        if content_type == "application/hl7-v2+er7":
            schema_type = "hl7v2"
            message_key = message_type.split("^")[0] if "^" in message_type else message_type
        elif content_type == "application/fhir+json":
            schema_type = "fhir"
            message_key = message_type
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
        
        # Get schema ID from mapping or use default
        schema_id = self.message_type_mapping.get(schema_type, {}).get(message_key)
        if not schema_id:
            # Try to find a schema with the same name as the message type
            schema_id = f"{schema_type}.{message_key}"
        
        return schema_id
    
    def _parse_hl7v2(self, raw_content: Union[bytes, str]) -> Dict[str, Any]:
        """Parse HL7 v2.x ER7 formatted message."""
        if isinstance(raw_content, bytes):
            raw_content = raw_content.decode('utf-8', errors='replace')
        
        # Simple HL7 v2.x parser - for production, consider using a library like hl7apy or hl7
        segments = raw_content.strip().split('\r')
        message = {}
        
        for segment in segments:
            if not segment.strip():
                continue
                
            fields = segment.split('|')
            segment_id = fields[0]
            
            # Parse fields and subcomponents
            parsed_fields = []
            for field in fields[1:]:
                if '^' in field:
                    components = field.split('^')
                    parsed_fields.append(components)
                else:
                    parsed_fields.append(field)
            
            # Handle repeating fields
            if segment_id in message:
                if not isinstance(message[segment_id], list):
                    message[segment_id] = [message[segment_id]]
                message[segment_id].append(parsed_fields[0] if len(parsed_fields) == 1 else parsed_fields)
            else:
                message[segment_id] = parsed_fields[0] if len(parsed_fields) == 1 else parsed_fields
        
        return message
    
    def _parse_fhir(self, raw_content: Union[bytes, str]) -> Dict[str, Any]:
        """Parse FHIR JSON message."""
        if isinstance(raw_content, bytes):
            raw_content = raw_content.decode('utf-8')
        
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
