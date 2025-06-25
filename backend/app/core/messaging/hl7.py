"""HL7 message handling and processing."""
from typing import Dict, Any, Optional, List
import json
import logging
import re
from datetime import datetime
from pydantic import BaseModel, Field, validator
from hl7apy.parser import parse_message
from hl7apy.core import Message
from hl7apy.exceptions import UnsupportedVersion

logger = logging.getLogger(__name__)

class HL7MessageError(Exception):
    """Base exception for HL7 message processing errors."""
    pass

class HL7Message(BaseModel):
    """Represents an HL7 message with validation and parsing capabilities."""
    message_id: str = Field(..., description="Unique message identifier")
    raw_message: Optional[str] = Field(None, description="Raw HL7 message content")
    parsed_message: Optional[Dict[str, Any]] = Field(None, description="Parsed message structure")
    message_type: Optional[str] = Field(None, description="HL7 message type (e.g., ADT_A01)")
    sending_application: Optional[str] = Field(None, description="MSH-3")
    sending_facility: Optional[str] = Field(None, description="MSH-4")
    receiving_application: Optional[str] = Field(None, description="MSH-5")
    receiving_facility: Optional[str] = Field(None, description="MSH-6")
    message_control_id: Optional[str] = Field(None, description="MSH-10")
    processing_id: Optional[str] = Field(None, description="MSH-11")
    version_id: Optional[str] = Field(None, description="MSH-12")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field("received", description="Current processing status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }

    @validator('raw_message')
    def validate_hl7_message(cls, v):
        """Validate basic HL7 message structure."""
        if v is None:
            return v
            
        # Basic HL7 message validation
        if not v.startswith('MSH|'):
            raise ValueError("Invalid HL7 message: Must start with 'MSH|'")
        
        # Extract field separator (MSH.1)
        try:
            field_sep = v[3]
            component_sep = v[4]
            
            # Check if we have at least MSH-12 (version)
            fields = v.split(field_sep)
            if len(fields) < 13:
                raise ValueError("Invalid HL7 message: Missing required fields")
                
        except IndexError as e:
            raise ValueError(f"Invalid HL7 message format: {str(e)}")
            
        return v

    def parse(self) -> 'HL7Message':
        """Parse the raw HL7 message and populate fields."""
        if not self.raw_message:
            raise HL7MessageError("No raw message to parse")
            
        try:
            # Parse with python-hl7
            msg = hl7.parse(self.raw_message)
            
            # Extract standard fields
            self.message_type = f"{str(msg.segment('MSH')[9][0][0])}_{str(msg.segment('MSH')[9][0][1])}"
            self.sending_application = str(msg.segment('MSH')[3][0])
            self.sending_facility = str(msg.segment('MSH')[4][0])
            self.receiving_application = str(msg.segment('MSH')[5][0])
            self.receiving_facility = str(msg.segment('MSH')[6][0])
            self.message_control_id = str(msg.segment('MSH')[10][0])
            self.processing_id = str(msg.segment('MSH')[11][0])
            self.version_id = str(msg.segment('MSH')[12][0])
            
            # Store parsed message as dict
            self.parsed_message = self._convert_to_dict(msg)
            
            return self
            
        except Exception as e:
            raise HL7MessageError(f"Failed to parse HL7 message: {str(e)}")
    
    def _convert_to_dict(self, msg) -> Dict[str, Any]:
        """Convert HL7 message to a dictionary structure."""
        result = {}
        
        for segment in msg:
            seg_name = str(segment[0][0])
            seg_data = []
            
            for field in segment[1:]:
                if len(field) > 0:
                    if len(field) > 1:  # Has components
                        components = []
                        for comp in field:
                            if len(comp) > 1:  # Has subcomponents
                                components.append([str(c) for c in comp])
                            else:
                                components.append(str(comp[0]) if comp[0] else "")
                        seg_data.append(components if len(components) > 1 else components[0])
                    else:
                        seg_data.append(str(field[0]) if field[0] else "")
                else:
                    seg_data.append("")
            
            # Handle repeating segments
            if seg_name in result:
                if not isinstance(result[seg_name], list):
                    result[seg_name] = [result[seg_name]]
                result[seg_name].append(seg_data)
            else:
                result[seg_name] = seg_data
                
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, including parsed message."""
        result = self.dict(exclude={"raw_message"})
        result["raw_message"] = self.raw_message  # Include raw message in output
        return result

class HL7Processor:
    """Processes HL7 messages including validation and transformation."""
    
    def __init__(self, message_store=None):
        self.message_store = message_store
        self.validators = {
            "ADT_A01": self._validate_adt_a01,
            "ORU_R01": self._validate_oru_r01,
        }
        self.transformers = {
            "ADT_A01": self._transform_adt_a01,
            "ORU_R01": self._transform_oru_r01,
        }
    
    async def process_message(self, message: HL7Message) -> HL7Message:
        """Process an HL7 message through validation and transformation."""
        try:
            # Parse the message if not already parsed
            if not message.parsed_message:
                message.parse()
            
            # Validate the message
            await self.validate(message)
            
            # Apply transformations
            await self.transform(message)
            
            message.status = "processed"
            return message
            
        except Exception as e:
            message.status = f"error: {str(e)}"
            raise HL7MessageError(f"Failed to process message: {str(e)}") from e
    
    async def validate(self, message: HL7Message) -> bool:
        """Validate the HL7 message based on its type."""
        if not message.message_type:
            raise HL7MessageError("Message type not set")
        
        validator = self.validators.get(message.message_type)
        if not validator:
            logger.warning(f"No validator found for message type {message.message_type}")
            return True  # No validator, assume valid
            
        return await validator(message)
    
    async def transform(self, message: HL7Message) -> HL7Message:
        """Transform the HL7 message based on its type."""
        if not message.message_type:
            raise HL7MessageError("Message type not set")
        
        transformer = self.transformers.get(message.message_type)
        if not transformer:
            logger.warning(f"No transformer found for message type {message.message_type}")
            return message  # No transformer, return as-is
            
        return await transformer(message)
    
    # Validation methods for different message types
    async def _validate_adt_a01(self, message: HL7Message) -> bool:
        """Validate ADT^A01 message."""
        required_segments = ["MSH", "EVN", "PID", "PV1"]
        return self._validate_required_segments(message, required_segments)
    
    async def _validate_oru_r01(self, message: HL7Message) -> bool:
        """Validate ORU^R01 message."""
        required_segments = ["MSH", "PID", "OBR", "OBX"]
        return self._validate_required_segments(message, required_segments)
    
    def _validate_required_segments(self, message: HL7Message, segments: List[str]) -> bool:
        """Check if all required segments are present in the message."""
        if not message.parsed_message:
            raise HL7MessageError("Message not parsed")
            
        missing = [seg for seg in segments if seg not in message.parsed_message]
        if missing:
            raise HL7MessageError(f"Missing required segments: {', '.join(missing)}")
            
        return True
    
    # Transformation methods for different message types
    async def _transform_adt_a01(self, message: HL7Message) -> HL7Message:
        """Transform ADT^A01 message."""
        # Example: Add processing timestamp
        message.metadata["processed_at"] = datetime.utcnow().isoformat()
        return message
    
    async def _transform_oru_r01(self, message: HL7Message) -> HL7Message:
        """Transform ORU^R01 message."""
        # Example: Add processing timestamp
        message.metadata["processed_at"] = datetime.utcnow().isoformat()
        return message

# Singleton instance for easy import
hl7_processor = HL7Processor()
