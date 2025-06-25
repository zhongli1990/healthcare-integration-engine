"""HL7 Message Processor with Neo4j Routing Integration."""
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
import json
import re

from .hl7 import HL7Message, HL7MessageError, hl7_processor
from .message_router import router as message_router
from .message_store import message_store
from ..core.config import settings

logger = logging.getLogger(__name__)

class HL7MessageProcessor:
    """Processes HL7 messages with validation, transformation, and routing."""
    
    def __init__(self):
        self.transformers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {}
        self.validators: Dict[str, Callable[[Dict[str, Any]], Awaitable[bool]]] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default message handlers for common HL7 message types."""
        # Register default validators
        self.validators.update({
            'ADT_A01': self._validate_adt_a01,
            'ORU_R01': self._validate_oru_r01,
            'SIU_S12': self._validate_siu_s12,
            'VXU_V04': self._validate_vxu_v04,
        })
        
        # Register default transformers
        self.transformers.update({
            'ADT_A01': self._transform_adt_a01,
            'ORU_R01': self._transform_oru_r01,
            'SIU_S12': self._transform_siu_s12,
            'VXU_V04': self._transform_vxu_v04,
        })
    
    async def process_message(self, message: HL7Message) -> Dict[str, Any]:
        """
        Process an HL7 message through the complete pipeline:
        1. Parse and validate the message
        2. Store the original message
        3. Apply transformations
        4. Route to destinations
        5. Update status
        """
        try:
            # Parse the raw message
            message.parse()
            
            # Store the original message
            message_id = await self._store_message(message, 'received')
            
            try:
                # Validate the message
                await self.validate_message(message)
                
                # Apply transformations
                transformed_message = await self.transform_message(message)
                
                # Route the message
                routing_result = await self.route_message(transformed_message)
                
                # Update status to processed
                await self._update_message_status(
                    message_id,
                    'processed',
                    {
                        'processed_at': datetime.utcnow().isoformat(),
                        'destination_systems': routing_result.get('destinations', []),
                        'transformations': routing_result.get('transformations', [])
                    }
                )
                
                return {
                    'status': 'processed',
                    'message_id': message_id,
                    'message_type': message.message_type,
                    'destinations': routing_result.get('destinations', []),
                    'transformations': routing_result.get('transformations', [])
                }
                
            except HL7MessageError as e:
                error_status = f'validation_error: {str(e)}'
                await self._update_message_status(message_id, error_status, {'error': str(e)})
                raise
                
            except Exception as e:
                error_status = f'processing_error: {str(e)}'
                await self._update_message_status(message_id, error_status, {'error': str(e)})
                raise HL7MessageError(f"Message processing failed: {str(e)}")
                
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}", exc_info=True)
            raise
    
    async def validate_message(self, message: HL7Message) -> bool:
        """Validate an HL7 message based on its type."""
        if not message.message_type:
            raise HL7MessageError("Message type not determined")
            
        validator = self.validators.get(message.message_type)
        if not validator:
            logger.warning(f"No validator found for message type {message.message_type}")
            return True
            
        try:
            return await validator(message.parsed_message)
        except Exception as e:
            raise HL7MessageError(f"Validation failed: {str(e)}")
    
    async def transform_message(self, message: HL7Message) -> Dict[str, Any]:
        """Transform an HL7 message based on its type."""
        if not message.message_type:
            raise HL7MessageError("Message type not determined")
            
        transformer = self.transformers.get(message.message_type)
        if not transformer:
            logger.warning(f"No transformer found for message type {message.message_type}")
            return message.parsed_message
            
        try:
            transformed = await transformer(message.parsed_message)
            return transformed or message.parsed_message
        except Exception as e:
            raise HL7MessageError(f"Transformation failed: {str(e)}")
    
    async def route_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route the message to appropriate destinations using Neo4j routing rules.
        
        Returns:
            Dict containing 'destinations' list and 'transformations' applied
        """
        try:
            # In a real implementation, we would use the message_router to determine
            # the appropriate destinations based on the message type and content
            
            # For now, we'll return a mock response
            return {
                'destinations': ['ehr_system', 'analytics_warehouse'],
                'transformations': [
                    {'type': 'field_mapping', 'status': 'applied'},
                    {'type': 'data_enrichment', 'status': 'applied'}
                ]
            }
            
            # In a real implementation, we would do something like:
            # routing_result = await message_router.route_message(message)
            # return routing_result
            
        except Exception as e:
            logger.error(f"Routing failed: {str(e)}", exc_info=True)
            raise HL7MessageError(f"Failed to route message: {str(e)}")
    
    async def _store_message(self, message: HL7Message, status: str) -> str:
        """Store the original message in the database."""
        try:
            message_id = await message_store.store_message({
                'message_id': message.message_id,
                'message_type': message.message_type,
                'status': status,
                'source_system': message.source_system,
                'body': message.raw_message,
                'headers': {
                    'sending_application': message.sending_application,
                    'sending_facility': message.sending_facility,
                    'receiving_application': message.receiving_application,
                    'receiving_facility': message.receiving_facility,
                    'message_control_id': message.message_control_id,
                },
                'metadata': message.metadata
            })
            return message_id
        except Exception as e:
            logger.error(f"Failed to store message: {str(e)}", exc_info=True)
            raise HL7MessageError(f"Failed to store message: {str(e)}")
    
    async def _update_message_status(
        self, 
        message_id: str, 
        status: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update the status and metadata of a stored message."""
        try:
            return await message_store.update_message_status(
                message_id=message_id,
                status=status,
                metadata=metadata or {}
            )
        except Exception as e:
            logger.error(f"Failed to update message status: {str(e)}", exc_info=True)
            return False
    
    # Default Validators
    async def _validate_adt_a01(self, message: Dict[str, Any]) -> bool:
        """Validate ADT^A01 message structure."""
        required_segments = ['MSH', 'EVN', 'PID', 'PV1']
        return self._validate_required_segments(message, required_segments)
    
    async def _validate_oru_r01(self, message: Dict[str, Any]) -> bool:
        """Validate ORU^R01 message structure."""
        required_segments = ['MSH', 'PID', 'OBR', 'OBX']
        return self._validate_required_segments(message, required_segments)
    
    async def _validate_siu_s12(self, message: Dict[str, Any]) -> bool:
        """Validate SIU^S12 message structure."""
        required_segments = ['MSH', 'SCH', 'TQ1', 'PID']
        return self._validate_required_segments(message, required_segments)
    
    async def _validate_vxu_v04(self, message: Dict[str, Any]) -> bool:
        """Validate VXU^V04 message structure."""
        required_segments = ['MSH', 'PID', 'PD1', 'NK1', 'PV1', 'ORC', 'RXA', 'RXR']
        return self._validate_required_segments(message, required_segments)
    
    def _validate_required_segments(self, message: Dict[str, Any], segments: List[str]) -> bool:
        """Check if all required segments are present in the message."""
        missing = [seg for seg in segments if seg not in message]
        if missing:
            raise HL7MessageError(f"Missing required segments: {', '.join(missing)}")
        return True
    
    # Default Transformers
    async def _transform_adt_a01(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Transform ADT^A01 message."""
        # Example: Add processing timestamp
        if 'EVN' in message and len(message['EVN']) > 5:
            message['EVN'][5] = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        return message
    
    async def _transform_oru_r01(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Transform ORU^R01 message."""
        # Example: Add processing timestamp to OBR segment
        if 'OBR' in message and len(message['OBR']) > 7:
            message['OBR'][7] = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        return message
    
    async def _transform_siu_s12(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Transform SIU^S12 message."""
        # Example: Update processing timestamp in SCH segment
        if 'SCH' in message and len(message['SCH']) > 11:
            message['SCH'][11] = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        return message
    
    async def _transform_vxu_v04(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Transform VXU^V04 message."""
        # Example: Update processing timestamp in RXA segment
        if 'RXA' in message and len(message['RXA']) > 4:
            message['RXA'][4] = datetime.utcnow().strftime('%Y%m%d')
        return message

# Singleton instance
hl7_message_processor = HL7MessageProcessor()
