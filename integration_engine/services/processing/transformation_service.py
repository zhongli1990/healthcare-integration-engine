import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

from core.models.message import MessageEnvelope, MessageHeader, MessageBody
from core.queues.queue_manager import QueueConfig
from core.schemas.schema_registry import SchemaRegistry
from core.services.base_service import BaseService
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TransformationRule(BaseModel):
    """Represents a transformation rule for converting between formats."""
    name: str
    description: Optional[str] = None
    source_format: str  # e.g., "hl7v2", "fhir"
    target_format: str  # e.g., "hl7v2", "fhir"
    source_message_type: Optional[str] = None  # e.g., "ADT_A01", "Patient"
    target_message_type: Optional[str] = None  # e.g., "ADT_A05", "Encounter"
    mapping: Dict[str, Any] = Field(default_factory=dict)  # Transformation mapping
    enabled: bool = True
    
    class Config:
        extra = "forbid"


class TransformationResult(BaseModel):
    """Represents the result of a transformation."""
    success: bool
    message: str
    source_message_id: str
    target_message_id: Optional[str] = None
    transformation_time: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary."""
        return {
            "success": self.success,
            "message": self.message,
            "source_message_id": self.source_message_id,
            "target_message_id": self.target_message_id,
            "transformation_time": self.transformation_time,
            "metadata": self.metadata
        }


class TransformationService(BaseService):
    """Service for transforming messages between different formats."""
    
    def __init__(
        self,
        input_queue: str = "validated_messages",
        output_queue: str = "transformed_messages",
        error_queue: str = "transformation_errors",
        schema_registry: Optional[SchemaRegistry] = None,
        **kwargs
    ):
        super().__init__(name="transformation_service", **kwargs)
        
        self.input_queue_name = input_queue
        self.output_queue_name = output_queue
        self.error_queue_name = error_queue
        
        self.schema_registry = schema_registry or SchemaRegistry()
        self.transformation_rules: List[TransformationRule] = []
        
        # Load default transformation rules
        self._load_default_rules()
    
    def _load_default_rules(self) -> None:
        """Load default transformation rules."""
        # HL7 v2 ADT_A01 to FHIR Patient
        self.add_transformation_rule(
            TransformationRule(
                name="hl7v2-adt-a01-to-fhir-patient",
                description="Convert HL7 v2 ADT^A01 to FHIR Patient",
                source_format="hl7v2",
                target_format="fhir",
                source_message_type="ADT_A01",
                target_message_type="Patient",
                mapping={
                    "resourceType": "Patient",
                    "id": "{{PID.3.1}}",
                    "identifier": [
                        {
                            "use": "usual",
                            "type": {
                                "coding": [{
                                    "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                                    "code": "MR"
                                }]
                            },
                            "value": "{{PID.3.1}}"
                        }
                    ],
                    "name": [{
                        "use": "official",
                        "family": "{{PID.5.1.1}}",
                        "given": ["{{PID.5.2}}"]
                    }],
                    "gender": "{{% if PID.8 == 'M' %}male{% elif PID.8 == 'F' %}female{% else %}unknown{% endif %}}",
                    "birthDate": "{{PID.7.1 | date('%Y-%m-%d')}}",
                    "address": [{
                        "use": "home",
                        "line": ["{{PID.11.1.1}}"],
                        "city": "{{PID.11.3}}",
                        "state": "{{PID.11.4}}",
                        "postalCode": "{{PID.11.5}}",
                        "country": "{{PID.11.6}}"
                    }],
                    "telecom": [{
                        "system": "phone",
                        "value": "{{PID.13.1}}",
                        "use": "home"
                    }]
                }
            )
        )
        
        # Add more default transformation rules as needed
    
    def add_transformation_rule(self, rule: TransformationRule) -> None:
        """Add a transformation rule."""
        # Check for duplicate rule names
        if any(r.name == rule.name for r in self.transformation_rules):
            raise ValueError(f"Transformation rule with name '{rule.name}' already exists")
        
        self.transformation_rules.append(rule)
    
    def remove_transformation_rule(self, rule_name: str) -> bool:
        """Remove a transformation rule by name."""
        initial_count = len(self.transformation_rules)
        self.transformation_rules = [r for r in self.transformation_rules if r.name != rule_name]
        return len(self.transformation_rules) < initial_count
    
    async def on_start(self) -> None:
        """Start the transformation service."""
        # Initialize queues
        self.input_queue = await self.queue_manager.get_queue(
            self.input_queue_name
        )
        self.output_queue = await self.queue_manager.get_queue(
            self.output_queue_name
        )
        self.error_queue = await self.queue_manager.get_queue(
            self.error_queue_name
        )
        
        # Start the message processing loop
        self.create_task(self._process_messages())
    
    async def _process_messages(self) -> None:
        """Process messages from the input queue."""
        try:
            async for message_id, message in self.input_queue.consume():
                try:
                    # Clone the message to avoid modifying the original
                    transformed_message = message.clone()
                    
                    # Transform the message
                    transformation_results = await self.transform_message(transformed_message)
                    
                    # Update message metadata with transformation results
                    transformed_message.header.metadata["transformations"] = [
                        r.to_dict() for r in transformation_results
                    ]
                    
                    # Check if any transformation was successful
                    any_success = any(r.success for r in transformation_results)
                    
                    if not any_success and transformation_results:
                        logger.warning(
                            f"Message {message.header.message_id} could not be transformed: "
                            f"{', '.join(r.message for r in transformation_results if not r.success)}"
                        )
                        transformed_message.header.status = "transformation_failed"
                        await self.error_queue.publish(transformed_message)
                    else:
                        if any_success:
                            logger.info(
                                f"Message {message.header.message_id} transformed successfully: "
                                f"{', '.join(r.message for r in transformation_results if r.success)}"
                            )
                        else:
                            logger.debug(f"No transformations applied to message {message.header.message_id}")
                        
                        transformed_message.header.status = "transformed"
                        await self.output_queue.publish(transformed_message)
                    
                    # Acknowledge the message
                    await self.input_queue.ack(message_id)
                    
                except Exception as e:
                    logger.exception(f"Error processing message {message_id}: {e}")
                    # Forward to error queue and acknowledge to prevent blocking
                    message.header.metadata["error"] = str(e)
                    await self.error_queue.publish(message)
                    await self.input_queue.ack(message_id)
                    
        except asyncio.CancelledError:
            logger.info("Message processing cancelled")
            raise
        except Exception as e:
            logger.exception("Error in transformation processing loop")
            raise
    
    async def transform_message(
        self,
        message: MessageEnvelope,
        target_format: Optional[str] = None,
        target_message_type: Optional[str] = None
    ) -> List[TransformationResult]:
        """
        Transform a message to the target format and message type.
        
        Args:
            message: The message to transform
            target_format: Optional target format (e.g., "hl7v2", "fhir")
            target_message_type: Optional target message type (e.g., "ADT_A01", "Patient")
            
        Returns:
            List[TransformationResult]: Results of all applicable transformations
        """
        from datetime import datetime
        
        results = []
        
        try:
            # Get message type and format
            source_format = self._get_message_format(message)
            source_message_type = self._get_message_type(message)
            
            if not source_format or not source_message_type:
                result = TransformationResult(
                    success=False,
                    message=f"Could not determine source format/type: {source_format}/{source_message_type}",
                    source_message_id=message.header.message_id,
                    transformation_time=datetime.utcnow().isoformat()
                )
                results.append(result)
                return results
            
            # Find applicable transformation rules
            applicable_rules = self._get_applicable_rules(
                source_format=source_format,
                source_message_type=source_message_type,
                target_format=target_format,
                target_message_type=target_message_type
            )
            
            if not applicable_rules:
                result = TransformationResult(
                    success=False,
                    message=f"No transformation rules found for {source_format}/{source_message_type} -> "
                           f"{target_format or 'any'}/{target_message_type or 'any'}",
                    source_message_id=message.header.message_id,
                    transformation_time=datetime.utcnow().isoformat()
                )
                results.append(result)
                return results
            
            # Apply each transformation rule
            for rule in applicable_rules:
                if not rule.enabled:
                    continue
                
                result = await self._apply_transformation_rule(message, rule)
                results.append(result)
                
                # If the transformation was successful and we only needed one, we can stop
                if result.success and target_format and target_message_type:
                    break
            
            return results
            
        except Exception as e:
            logger.exception("Unexpected error during transformation")
            result = TransformationResult(
                success=False,
                message=f"Unexpected error during transformation: {str(e)}",
                source_message_id=message.header.message_id,
                transformation_time=datetime.utcnow().isoformat()
            )
            results.append(result)
            return results
    
    def _get_message_format(self, message: MessageEnvelope) -> Optional[str]:
        """Get the format of the message."""
        content_type = message.body.content_type or ""
        
        if "hl7-v2" in content_type:
            return "hl7v2"
        elif "fhir" in content_type:
            return "fhir"
        
        # Try to infer from content
        if isinstance(message.body.content, dict):
            if "resourceType" in message.body.content:
                return "fhir"
            elif any(key in message.body.content for key in ["MSH", "EVN", "PID"]):
                return "hl7v2"
        
        return None
    
    def _get_message_type(self, message: MessageEnvelope) -> Optional[str]:
        """Get the message type."""
        # First try the message header
        if message.header.message_type:
            return message.header.message_type
        
        # Then try to infer from content
        if not message.body.content:
            return None
        
        content = message.body.content
        
        # For HL7 v2
        if isinstance(content, dict) and "MSH" in content and "MSH.9" in content["MSH"]:
            return content["MSH"]["MSH.9"]
        
        # For FHIR
        if isinstance(content, dict) and "resourceType" in content:
            resource_type = content["resourceType"]
            # For Bundle, check the type
            if resource_type == "Bundle" and "type" in content:
                return f"Bundle/{content['type']}"
            return resource_type
        
        return None
    
    def _get_applicable_rules(
        self,
        source_format: str,
        source_message_type: str,
        target_format: Optional[str] = None,
        target_message_type: Optional[str] = None
    ) -> List[TransformationRule]:
        """Get all transformation rules that apply to the message."""
        applicable_rules = []
        
        for rule in self.transformation_rules:
            if not rule.enabled:
                continue
                
            # Check source format and message type
            if rule.source_format != source_format:
                continue
                
            if rule.source_message_type and rule.source_message_type != source_message_type:
                continue
            
            # Check target format and message type if specified
            if target_format and rule.target_format != target_format:
                continue
                
            if target_message_type and rule.target_message_type and rule.target_message_type != target_message_type:
                continue
            
            applicable_rules.append(rule)
        
        return applicable_rules
    
    async def _apply_transformation_rule(
        self,
        message: MessageEnvelope,
        rule: TransformationRule
    ) -> TransformationResult:
        """Apply a transformation rule to a message."""
        from datetime import datetime
        
        result = TransformationResult(
            success=False,
            message="",
            source_message_id=message.header.message_id,
            transformation_time=datetime.utcnow().isoformat(),
            metadata={
                "rule": rule.name,
                "source_format": rule.source_format,
                "target_format": rule.target_format,
                "source_message_type": rule.source_message_type or "*",
                "target_message_type": rule.target_message_type or "*"
            }
        )
        
        try:
            # Get the appropriate transformer based on the source and target formats
            transformer = self._get_transformer(rule.source_format, rule.target_format)
            if not transformer:
                result.message = f"No transformer available for {rule.source_format} -> {rule.target_format}"
                return result
            
            # Apply the transformation
            transformed_content = await transformer.transform(
                message=message,
                mapping=rule.mapping,
                rule=rule
            )
            
            if not transformed_content:
                result.message = "Transformation returned no content"
                return result
            
            # Create a new message with the transformed content
            transformed_message = message.clone()
            transformed_message.body.content = transformed_content
            transformed_message.body.content_type = f"application/{rule.target_format}+json"
            
            # Update message type if specified in the rule
            if rule.target_message_type:
                transformed_message.header.message_type = rule.target_message_type
            
            # Update the message ID to indicate it's a new message
            import uuid
            transformed_message.header.message_id = str(uuid.uuid4())
            
            # Add transformation metadata
            transformed_message.header.metadata["transformed_from"] = message.header.message_id
            transformed_message.header.metadata["transformation_rule"] = rule.name
            
            # Set the result
            result.success = True
            result.message = f"Transformed using rule '{rule.name}'"
            result.target_message_id = transformed_message.header.message_id
            result.metadata["target_message_id"] = transformed_message.header.message_id
            
            # Replace the original message with the transformed one
            message.body = transformed_message.body
            message.header = transformed_message.header
            
            return result
            
        except Exception as e:
            logger.exception(f"Error applying transformation rule '{rule.name}'")
            result.message = f"Error applying transformation: {str(e)}"
            return result
    
    def _get_transformer(
        self,
        source_format: str,
        target_format: str
    ) -> Optional['BaseTransformer']:
        """Get a transformer for the given source and target formats."""
        # For now, we'll use a simple if-else structure
        # In a real implementation, this would use a plugin system or registry
        
        if source_format == "hl7v2" and target_format == "fhir":
            return HL7v2ToFHIRTransformer()
        elif source_format == "fhir" and target_format == "hl7v2":
            return FHIRToHL7v2Transformer()
        # Add more transformers as needed
        
        return None


class BaseTransformer(ABC):
    """Base class for all transformers."""
    
    @abstractmethod
    async def transform(
        self,
        message: MessageEnvelope,
        mapping: Dict[str, Any],
        rule: TransformationRule
    ) -> Any:
        """
        Transform the message content according to the mapping.
        
        Args:
            message: The message to transform
            mapping: The transformation mapping
            rule: The transformation rule
            
        Returns:
            The transformed content
        """
        pass


class HL7v2ToFHIRTransformer(BaseTransformer):
    """Transforms HL7 v2.x messages to FHIR resources."""
    
    async def transform(
        self,
        message: MessageEnvelope,
        mapping: Dict[str, Any],
        rule: TransformationRule
    ) -> Any:
        """Transform HL7 v2.x to FHIR."""
        from jinja2 import Template
        import json
        
        # Convert the mapping to a JSON string and render it as a Jinja2 template
        template = Template(json.dumps(mapping))
        
        # Create a context with the message content
        context = self._create_context(message.body.content)
        
        # Render the template
        result = template.render(**context)
        
        # Parse the result back to a Python object
        return json.loads(result)
    
    def _create_context(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Create a context for template rendering."""
        context = {}
        
        # Flatten the HL7 v2.x structure for easier templating
        if isinstance(content, dict):
            for segment, fields in content.items():
                if not isinstance(fields, (list, dict)):
                    context[segment] = fields
                    continue
                
                # Handle segment fields (e.g., MSH, PID)
                for i, field in enumerate(fields, 1):
                    field_key = f"{segment}.{i}"
                    
                    if isinstance(field, (list, tuple)):
                        # Handle components and subcomponents
                        for j, component in enumerate(field, 1):
                            component_key = f"{field_key}.{j}"
                            
                            if isinstance(component, (list, tuple)):
                                for k, subcomponent in enumerate(component, 1):
                                    subcomponent_key = f"{component_key}.{k}"
                                    context[subcomponent_key] = subcomponent
                            else:
                                context[component_key] = component
                    else:
                        context[field_key] = field
        
        return context


class FHIRToHL7v2Transformer(BaseTransformer):
    """Transforms FHIR resources to HL7 v2.x messages."""
    
    async def transform(
        self,
        message: MessageEnvelope,
        mapping: Dict[str, Any],
        rule: TransformationRule
    ) -> Any:
        """Transform FHIR to HL7 v2.x."""
        # This is a simplified implementation
        # In a real implementation, you would handle the full FHIR to HL7 v2.x mapping
        
        fhir_resource = message.body.content
        if not isinstance(fhir_resource, dict):
            raise ValueError("FHIR resource must be a dictionary")
        
        resource_type = fhir_resource.get("resourceType")
        
        if resource_type == "Patient":
            return self._patient_to_hl7v2(fhir_resource, mapping)
        # Add more resource types as needed
        
        raise ValueError(f"Unsupported FHIR resource type: {resource_type}")
    
    def _patient_to_hl7v2(self, patient: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a FHIR Patient to an HL7 v2.x ADT_A01 message."""
        # This is a simplified implementation
        # In a real implementation, you would handle all the fields properly
        
        # Create a basic MSH segment
        msh = {
            "MSH.1": "|",
            "MSH.2": "^~\\&",
            "MSH.7": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            "MSH.9": "ADT^A01",
            "MSH.10": str(uuid.uuid4()),
            "MSH.11": "P",
            "MSH.12": "2.5.1"
        }
        
        # Create EVN segment
        evn = {
            "EVN.1": "A01",
            "EVN.2": datetime.utcnow().strftime("%Y%m%d%H%M%S")
        }
        
        # Create PID segment from Patient resource
        pid = {
            "PID.1": "1",
            "PID.3": [
                {
                    "PID.3.1": patient.get("id", ""),
                    "PID.3.5": "MR"
                }
            ],
            "PID.5": [
                {
                    "PID.5.1": self._get_family_name(patient),
                    "PID.5.2": self._get_given_name(patient)
                }
            ],
            "PID.7": self._get_birth_date(patient),
            "PID.8": self._get_gender(patient)
        }
        
        # Add address if available
        if "address" in patient and patient["address"]:
            address = patient["address"][0]  # Take the first address
            pid["PID.11"] = [
                {
                    "PID.11.1": address.get("line", [""])[0],
                    "PID.11.3": address.get("city", ""),
                    "PID.11.4": address.get("state", ""),
                    "PID.11.5": address.get("postalCode", ""),
                    "PID.11.6": address.get("country", "")
                }
            ]
        
        # Add telecom if available
        if "telecom" in patient and patient["telecom"]:
            for telecom in patient["telecom"]:
                system = telecom.get("system", "")
                value = telecom.get("value", "")
                use = telecom.get("use", "")
                
                if system == "phone" and use == "home":
                    pid["PID.13"] = [{"PID.13.1": value}]
                    break
        
        return {
            "MSH": msh,
            "EVN": evn,
            "PID": pid
        }
    
    def _get_family_name(self, patient: Dict[str, Any]) -> str:
        """Extract family name from a Patient resource."""
        if "name" in patient and patient["name"]:
            for name in patient["name"]:
                if "family" in name:
                    return name["family"]
        return ""
    
    def _get_given_name(self, patient: Dict[str, Any]) -> str:
        """Extract given name from a Patient resource."""
        if "name" in patient and patient["name"]:
            for name in patient["name"]:
                if "given" in name and name["given"]:
                    return name["given"][0]
        return ""
    
    def _get_birth_date(self, patient: Dict[str, Any]) -> str:
        """Extract birth date from a Patient resource."""
        birth_date = patient.get("birthDate", "")
        # Convert from FHIR date to HL7 v2.x format (YYYYMMDD)
        if birth_date:
            return birth_date.replace("-", "")
        return ""
    
    def _get_gender(self, patient: Dict[str, Any]) -> str:
        """Extract gender from a Patient resource."""
        gender = patient.get("gender", "").lower()
        if gender == "male":
            return "M"
        elif gender == "female":
            return "F"
        return "U"
