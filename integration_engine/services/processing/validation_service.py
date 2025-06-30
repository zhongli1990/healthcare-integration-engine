import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel

from core.models.message import MessageEnvelope, MessageHeader, MessageBody
from core.queues.queue_manager import QueueConfig
from core.schemas.schema_registry import SchemaRegistry, SchemaValidationError
from core.services.base_service import BaseService

logger = logging.getLogger(__name__)


class ValidationRule(BaseModel):
    """Represents a validation rule for a message type."""
    name: str
    description: Optional[str] = None
    schema_id: str
    enabled: bool = True
    error_severity: str = "error"  # error, warning, info
    
    class Config:
        extra = "forbid"


class ValidationResult(BaseModel):
    """Represents the result of a validation."""
    valid: bool
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    info: List[Dict[str, Any]] = []
    validated_at: str
    
    def add_error(self, message: str, path: str = "", details: Any = None) -> None:
        """Add an error to the result."""
        self.valid = False
        self.errors.append({
            "message": message,
            "path": path,
            "details": details
        })
    
    def add_warning(self, message: str, path: str = "", details: Any = None) -> None:
        """Add a warning to the result."""
        self.warnings.append({
            "message": message,
            "path": path,
            "details": details
        })
    
    def add_info(self, message: str, path: str = "", details: Any = None) -> None:
        """Add an info message to the result."""
        self.info.append({
            "message": message,
            "path": path,
            "details": details
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "validated_at": self.validated_at
        }


class ValidationService(BaseService):
    """Service for validating messages against schemas and business rules."""
    
    def __init__(
        self,
        input_queue: str = "parsed_messages",
        output_queue: str = "validated_messages",
        error_queue: str = "validation_errors",
        schema_registry: Optional[SchemaRegistry] = None,
        **kwargs
    ):
        super().__init__(name="validation_service", **kwargs)
        
        self.input_queue_name = input_queue
        self.output_queue_name = output_queue
        self.error_queue_name = error_queue
        
        self.schema_registry = schema_registry or SchemaRegistry()
        self.validation_rules: Dict[str, List[ValidationRule]] = {}
        
        # Default validation rules by message type
        self._load_default_rules()
    
    def _load_default_rules(self) -> None:
        """Load default validation rules."""
        # HL7 v2 validation rules
        self.add_validation_rule(
            message_type="ADT_A01",
            rule=ValidationRule(
                name="required-fields",
                description="Required fields for ADT_A01",
                schema_id="hl7v2.ADT_A01"
            )
        )
        
        # FHIR Patient validation rules
        self.add_validation_rule(
            message_type="Patient",
            rule=ValidationRule(
                name="required-fields",
                description="Required fields for Patient",
                schema_id="fhir.Patient"
            )
        )
    
    def add_validation_rule(
        self,
        message_type: str,
        rule: ValidationRule
    ) -> None:
        """Add a validation rule for a message type."""
        if message_type not in self.validation_rules:
            self.validation_rules[message_type] = []
        
        # Check for duplicate rule names
        if any(r.name == rule.name for r in self.validation_rules[message_type]):
            raise ValueError(f"Rule with name '{rule.name}' already exists for message type '{message_type}'")
        
        self.validation_rules[message_type].append(rule)
    
    def remove_validation_rule(
        self,
        message_type: str,
        rule_name: str
    ) -> bool:
        """Remove a validation rule by name."""
        if message_type not in self.validation_rules:
            return False
        
        initial_count = len(self.validation_rules[message_type])
        self.validation_rules[message_type] = [
            r for r in self.validation_rules[message_type] if r.name != rule_name
        ]
        
        return len(self.validation_rules[message_type]) < initial_count
    
    async def on_start(self) -> None:
        """Start the validation service."""
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
                    validated_message = message.clone()
                    
                    # Validate the message
                    validation_result = await self.validate_message(validated_message)
                    
                    # Update message metadata with validation results
                    validated_message.header.metadata["validation"] = validation_result.to_dict()
                    
                    if not validation_result.valid:
                        logger.warning(
                            f"Message {validated_message.header.message_id} failed validation: "
                            f"{len(validation_result.errors)} errors, {len(validation_result.warnings)} warnings"
                        )
                        validated_message.header.status = "validation_failed"
                        await self.error_queue.publish(validated_message)
                    else:
                        if validation_result.warnings:
                            logger.info(
                                f"Message {validated_message.header.message_id} validated with "
                                f"{len(validation_result.warnings)} warnings"
                            )
                        else:
                            logger.debug(f"Message {validated_message.header.message_id} validated successfully")
                        
                        validated_message.header.status = "validated"
                        await self.output_queue.publish(validated_message)
                    
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
            logger.exception("Error in validation processing loop")
            raise
    
    async def validate_message(
        self,
        message: MessageEnvelope
    ) -> ValidationResult:
        """
        Validate a message against its schema and business rules.
        
        Args:
            message: The message to validate
            
        Returns:
            ValidationResult: The result of the validation
        """
        from datetime import datetime
        
        result = ValidationResult(
            valid=True,
            validated_at=datetime.utcnow().isoformat()
        )
        
        try:
            # Get message type from header or body
            message_type = message.header.message_type
            if not message_type and hasattr(message.body.content, 'get'):
                message_type = message.body.content.get('resourceType')
            
            if not message_type:
                result.add_error("Could not determine message type")
                return result
            
            # Get applicable validation rules
            rules = self._get_applicable_rules(message_type, message)
            if not rules:
                result.add_warning(f"No validation rules found for message type: {message_type}")
                return result
            
            # Apply each validation rule
            for rule in rules:
                if not rule.enabled:
                    continue
                
                try:
                    # Validate against schema if specified
                    if rule.schema_id:
                        self._validate_against_schema(
                            message=message,
                            schema_id=rule.schema_id,
                            result=result,
                            rule_name=rule.name
                        )
                    
                    # Apply custom validation logic based on rule name
                    self._apply_custom_validation(
                        message=message,
                        rule=rule,
                        result=result
                    )
                    
                except Exception as e:
                    result.add_error(
                        message=f"Error applying validation rule '{rule.name}': {str(e)}",
                        path="",
                        details={"rule": rule.dict() if hasattr(rule, 'dict') else str(rule)}
                    )
            
            return result
            
        except Exception as e:
            logger.exception("Unexpected error during validation")
            result.add_error(f"Unexpected error during validation: {str(e)}")
            return result
    
    def _get_applicable_rules(
        self,
        message_type: str,
        message: MessageEnvelope
    ) -> List[ValidationRule]:
        """Get all validation rules that apply to the message."""
        # First, get rules specifically for this message type
        rules = self.validation_rules.get(message_type, []).copy()
        
        # Add any wildcard rules (*)
        rules.extend(self.validation_rules.get("*", []))
        
        return rules
    
    def _validate_against_schema(
        self,
        message: MessageEnvelope,
        schema_id: str,
        result: ValidationResult,
        rule_name: str
    ) -> None:
        """Validate the message against a JSON schema."""
        try:
            # Get the schema from the registry
            schema = self.schema_registry.get(schema_id)
            if not schema:
                result.add_error(
                    f"Schema '{schema_id}' not found",
                    rule=rule_name
                )
                return
            
            # Validate the message content against the schema
            if not message.body.content:
                result.add_error(
                    "Message has no content to validate",
                    rule=rule_name
                )
                return
            
            # Validate against the schema
            try:
                schema.validate(message.body.content)
                result.add_info(
                    f"Validation against schema '{schema_id}' successful",
                    rule=rule_name
                )
            except SchemaValidationError as e:
                result.add_error(
                    f"Schema validation failed: {str(e)}",
                    rule=rule_name,
                    details={"schema_id": schema_id}
                )
                
        except Exception as e:
            result.add_error(
                f"Error during schema validation: {str(e)}",
                rule=rule_name,
                details={"schema_id": schema_id}
            )
    
    def _apply_custom_validation(
        self,
        message: MessageEnvelope,
        rule: ValidationRule,
        result: ValidationResult
    ) -> None:
        """Apply custom validation logic based on the rule name."""
        # This method can be extended with custom validation logic
        # based on the rule name or other rule attributes
        
        # Example: Check for required fields in HL7 v2 messages
        if rule.name == "required-fields" and message.body.content_type == "application/hl7-v2+er7":
            self._validate_hl7_required_fields(message, rule, result)
        
        # Example: Check for required fields in FHIR resources
        elif rule.name == "required-fields" and message.body.content_type == "application/fhir+json":
            self._validate_fhir_required_fields(message, rule, result)
    
    def _validate_hl7_required_fields(
        self,
        message: MessageEnvelope,
        rule: ValidationRule,
        result: ValidationResult
    ) -> None:
        """Validate required fields in an HL7 v2 message."""
        content = message.body.content
        if not isinstance(content, dict):
            return
        
        # Check for required segments
        required_segments = ["MSH", "EVN", "PID"]
        for segment in required_segments:
            if segment not in content:
                result.add_error(
                    f"Missing required segment: {segment}",
                    path=segment,
                    rule=rule.name
                )
        
        # Check for required fields in MSH segment
        if "MSH" in content:
            msh = content["MSH"]
            if not isinstance(msh, (list, tuple)) or len(msh) < 12:
                result.add_error(
                    "MSH segment is missing required fields",
                    path="MSH",
                    rule=rule.name
                )
    
    def _validate_fhir_required_fields(
        self,
        message: MessageEnvelope,
        rule: ValidationRule,
        result: ValidationResult
    ) -> None:
        """Validate required fields in a FHIR resource."""
        content = message.body.content
        if not isinstance(content, dict):
            return
        
        resource_type = content.get("resourceType")
        if not resource_type:
            result.add_error(
                "FHIR resource is missing 'resourceType'",
                path="resourceType",
                rule=rule.name
            )
            return
        
        # Check for required top-level fields
        required_fields = ["id"]
        for field in required_fields:
            if field not in content:
                result.add_warning(
                    f"Missing recommended field: {field}",
                    path=field,
                    rule=rule.name
                )
        
        # Resource-specific validation
        if resource_type == "Patient":
            if "name" not in content or not content["name"]:
                result.add_error(
                    "Patient resource must have at least one name",
                    path="name",
                    rule=rule.name
                )
        
        elif resource_type == "Observation":
            required_obs_fields = ["status", "code"]
            for field in required_obs_fields:
                if field not in content:
                    result.add_error(
                        f"Observation is missing required field: {field}",
                        path=field,
                        rule=rule.name
                    )
