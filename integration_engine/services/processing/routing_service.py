import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable, Awaitable

from core.models.message import MessageEnvelope, MessageHeader, MessageBody
from core.queues.queue_manager import QueueConfig
from core.services.base_service import BaseService
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class RouteCondition(BaseModel):
    """Represents a condition for a routing rule."""
    field: str
    operator: str  # ==, !=, >, <, >=, <=, contains, regex, in, not_in
    value: Any
    
    class Config:
        extra = "forbid"


class RouteAction(BaseModel):
    """Represents an action to take when a route matches."""
    type: str  # forward, transform, drop, log, etc.
    target: Optional[str] = None  # queue name, transformation name, etc.
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        extra = "forbid"


class RouteRule(BaseModel):
    """Represents a routing rule."""
    name: str
    description: Optional[str] = None
    priority: int = 100  # Lower numbers are evaluated first
    conditions: List[RouteCondition] = Field(default_factory=list)
    actions: List[RouteAction] = Field(default_factory=list)
    enabled: bool = True
    
    class Config:
        extra = "forbid"
    
    @validator('priority')
    def validate_priority(cls, v):
        if v < 0 or v > 1000:
            raise ValueError("Priority must be between 0 and 1000")
        return v


class RoutingResult(BaseModel):
    """Represents the result of a routing decision."""
    matched_rule: Optional[str] = None
    actions_taken: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    
    def add_action(self, action_type: str, target: Optional[str] = None, **kwargs) -> None:
        """Add an action that was taken."""
        action = {"type": action_type}
        if target:
            action["target"] = target
        action.update(kwargs)
        self.actions_taken.append(action)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary."""
        return {
            "matched_rule": self.matched_rule,
            "actions_taken": self.actions_taken,
            "error": self.error
        }


class RoutingService(BaseService):
    """Service for routing messages to different queues based on rules."""
    
    def __init__(
        self,
        input_queue: str = "transformed_messages",
        default_route: str = "unrouted_messages",
        error_queue: str = "routing_errors",
        **kwargs
    ):
        super().__init__(name="routing_service", **kwargs)
        
        self.input_queue_name = input_queue
        self.default_route = default_route
        self.error_queue_name = error_queue
        
        self.routing_rules: List[RouteRule] = []
        self.queues: Dict[str, Any] = {}
        
        # Load default routing rules
        self._load_default_rules()
    
    def _load_default_rules(self) -> None:
        """Load default routing rules."""
        # Route HL7 v2 ADT messages to the ADT processor
        self.add_route_rule(
            RouteRule(
                name="route-hl7v2-adt",
                description="Route HL7 v2 ADT messages to ADT processor",
                priority=10,
                conditions=[
                    RouteCondition(
                        field="header.content_type",
                        operator="contains",
                        value="hl7-v2"
                    ),
                    RouteCondition(
                        field="header.message_type",
                        operator="regex",
                        value=r"^ADT_"
                    )
                ],
                actions=[
                    RouteAction(
                        type="forward",
                        target="adt_processor"
                    )
                ]
            )
        )
        
        # Route FHIR Patient resources to the patient registry
        self.add_route_rule(
            RouteRule(
                name="route-fhir-patient",
                description="Route FHIR Patient resources to patient registry",
                priority=10,
                conditions=[
                    RouteCondition(
                        field="body.content_type",
                        operator="contains",
                        value="fhir+json"
                    ),
                    RouteCondition(
                        field="body.content.resourceType",
                        operator="==",
                        value="Patient"
                    )
                ],
                actions=[
                    RouteAction(
                        type="forward",
                        target="patient_registry"
                    )
                ]
            )
        )
        
        # Route FHIR Observation resources to the clinical data processor
        self.add_route_rule(
            RouteRule(
                name="route-fhir-observation",
                description="Route FHIR Observation resources to clinical data processor",
                priority=10,
                conditions=[
                    RouteCondition(
                        field="body.content_type",
                        operator="contains",
                        value="fhir+json"
                    ),
                    RouteCondition(
                        field="body.content.resourceType",
                        operator="==",
                        value="Observation"
                    )
                ],
                actions=[
                    RouteAction(
                        type="forward",
                        target="clinical_data_processor"
                    )
                ]
            )
        )
        
        # Default route for unmatched messages
        self.add_route_rule(
            RouteRule(
                name="default-route",
                description="Default route for all unmatched messages",
                priority=1000,
                conditions=[],
                actions=[
                    RouteAction(
                        type="forward",
                        target=self.default_route
                    )
                ]
            )
        )
    
    def add_route_rule(self, rule: RouteRule) -> None:
        """Add a routing rule."""
        # Check for duplicate rule names
        if any(r.name == rule.name for r in self.routing_rules):
            raise ValueError(f"Routing rule with name '{rule.name}' already exists")
        
        self.routing_rules.append(rule)
        # Keep rules sorted by priority (lower numbers first)
        self.routing_rules.sort(key=lambda r: r.priority)
    
    def remove_route_rule(self, rule_name: str) -> bool:
        """Remove a routing rule by name."""
        initial_count = len(self.routing_rules)
        self.routing_rules = [r for r in self.routing_rules if r.name != rule_name]
        return len(self.routing_rules) < initial_count
    
    async def on_start(self) -> None:
        """Start the routing service."""
        # Initialize queues
        self.input_queue = await self.queue_manager.get_queue(self.input_queue_name)
        self.error_queue = await self.queue_manager.get_queue(self.error_queue_name)
        
        # Start the message processing loop
        self.create_task(self._process_messages())
    
    async def _process_messages(self) -> None:
        """Process messages from the input queue."""
        try:
            async for message_id, message in self.input_queue.consume():
                try:
                    # Route the message
                    routing_result = await self.route_message(message)
                    
                    # Update message metadata with routing info
                    if "routing" not in message.header.metadata:
                        message.header.metadata["routing"] = {}
                    message.header.metadata["routing"].update(routing_result.to_dict())
                    
                    # Process the routing actions
                    await self._process_routing_actions(message, routing_result)
                    
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
            logger.exception("Error in routing processing loop")
            raise
    
    async def route_message(self, message: MessageEnvelope) -> RoutingResult:
        """
        Route a message based on the configured rules.
        
        Args:
            message: The message to route
            
        Returns:
            RoutingResult: The result of the routing decision
        """
        result = RoutingResult()
        
        try:
            # Evaluate each rule in priority order
            for rule in self.routing_rules:
                if not rule.enabled:
                    continue
                
                # Check if all conditions match
                if self._evaluate_conditions(message, rule.conditions):
                    result.matched_rule = rule.name
                    
                    # Execute all actions for this rule
                    for action in rule.actions:
                        await self._execute_action(message, action, result)
                    
                    # Stop after the first matching rule (unless it's the default route)
                    if rule.priority < 1000:  # Default route has priority 1000
                        break
            
            return result
            
        except Exception as e:
            logger.exception("Error in route_message")
            result.error = f"Error in route_message: {str(e)}"
            return result
    
    def _evaluate_conditions(
        self,
        message: MessageEnvelope,
        conditions: List[RouteCondition]
    ) -> bool:
        """Evaluate if all conditions are met for the given message."""
        if not conditions:
            return True
        
        for condition in conditions:
            try:
                # Get the field value using dot notation
                value = self._get_nested_value(message, condition.field)
                
                # Apply the operator
                if not self._evaluate_condition(value, condition.operator, condition.value):
                    return False
                
            except (KeyError, AttributeError, IndexError, TypeError) as e:
                # If the field doesn't exist or can't be accessed, the condition fails
                logger.debug(f"Condition evaluation failed for field '{condition.field}': {e}")
                return False
        
        return True
    
    def _evaluate_condition(
        self,
        actual_value: Any,
        operator: str,
        expected_value: Any
    ) -> bool:
        """Evaluate a single condition."""
        try:
            if operator == "==":
                return actual_value == expected_value
            elif operator == "!=":
                return actual_value != expected_value
            elif operator == ">":
                return actual_value > expected_value
            elif operator == ">=":
                return actual_value >= expected_value
            elif operator == "<":
                return actual_value < expected_value
            elif operator == "<=":
                return actual_value <= expected_value
            elif operator == "contains":
                if isinstance(actual_value, str) and isinstance(expected_value, str):
                    return expected_value in actual_value
                elif isinstance(actual_value, (list, tuple, set)):
                    return expected_value in actual_value
                elif actual_value is not None:
                    return expected_value in str(actual_value)
                return False
            elif operator == "regex":
                if not isinstance(actual_value, str):
                    actual_value = str(actual_value)
                return bool(re.search(expected_value, actual_value, re.IGNORECASE))
            elif operator == "in":
                if isinstance(expected_value, (list, tuple, set)):
                    return actual_value in expected_value
                return actual_value == expected_value
            elif operator == "not_in":
                if isinstance(expected_value, (list, tuple, set)):
                    return actual_value not in expected_value
                return actual_value != expected_value
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
        except Exception as e:
            logger.warning(f"Error evaluating condition: {e}")
            return False
    
    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """Get a nested value from an object using dot notation."""
        if not path:
            return obj
        
        parts = path.split('.')
        current = obj
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, (list, tuple)) and part.isdigit():
                index = int(part)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    raise IndexError(f"Index {index} out of range")
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                raise KeyError(f"No such attribute or key: {part}")
            
            if current is None:
                break
        
        return current
    
    async def _execute_action(
        self,
        message: MessageEnvelope,
        action: RouteAction,
        result: RoutingResult
    ) -> None:
        """Execute a routing action."""
        try:
            if action.type == "forward":
                await self._forward_message(message, action.target, result)
            elif action.type == "transform":
                await self._transform_message(message, action.target, action.parameters, result)
            elif action.type == "drop":
                self._drop_message(message, result)
            elif action.type == "log":
                self._log_message(message, action.parameters, result)
            else:
                logger.warning(f"Unknown action type: {action.type}")
                result.error = f"Unknown action type: {action.type}"
        except Exception as e:
            logger.exception(f"Error executing action {action.type}")
            result.error = f"Error executing action {action.type}: {str(e)}"
    
    async def _forward_message(
        self,
        message: MessageEnvelope,
        target_queue: str,
        result: RoutingResult
    ) -> None:
        """Forward a message to another queue."""
        try:
            # Get or create the target queue
            if target_queue not in self.queues:
                self.queues[target_queue] = await self.queue_manager.get_queue(target_queue)
            
            # Publish the message to the target queue
            await self.queues[target_queue].publish(message)
            
            # Update the result
            result.add_action("forward", target_queue, success=True)
            logger.debug(f"Forwarded message {message.header.message_id} to {target_queue}")
            
        except Exception as e:
            logger.exception(f"Error forwarding message to {target_queue}")
            result.add_action("forward", target_queue, success=False, error=str(e))
            raise
    
    async def _transform_message(
        self,
        message: MessageEnvelope,
        transformation_name: str,
        parameters: Dict[str, Any],
        result: RoutingResult
    ) -> None:
        """Transform a message using a named transformation."""
        try:
            # In a real implementation, this would call a transformation service
            # For now, we'll just log the transformation
            logger.info(
                f"Transforming message {message.header.message_id} "
                f"using transformation '{transformation_name}' with parameters {parameters}"
            )
            
            # Update the result
            result.add_action("transform", transformation_name, success=True, parameters=parameters)
            
        except Exception as e:
            logger.exception(f"Error transforming message with {transformation_name}")
            result.add_action(
                "transform",
                transformation_name,
                success=False,
                error=str(e),
                parameters=parameters
            )
            raise
    
    def _drop_message(
        self,
        message: MessageEnvelope,
        result: RoutingResult
    ) -> None:
        """Drop a message (no-op)."""
        logger.info(f"Dropping message {message.header.message_id}")
        result.add_action("drop", success=True)
    
    def _log_message(
        self,
        message: MessageEnvelope,
        parameters: Dict[str, Any],
        result: RoutingResult
    ) -> None:
        """Log a message."""
        level = parameters.get("level", "info").lower()
        message_text = parameters.get("message", "")
        
        log_method = getattr(logger, level, logger.info)
        log_method(f"[ROUTING] {message_text}")
        
        result.add_action("log", success=True, level=level, message=message_text)
