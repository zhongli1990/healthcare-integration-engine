"""
HL7 Routing Service

Routes HL7 messages based on message type and content.
"""
import logging
import time
from typing import Dict, Any, List, Optional

from integration_engine.core.models.message import Message
from integration_engine.core.queues.queue_manager import QueueManager

logger = logging.getLogger(__name__)

class HL7RoutingService:
    """Service for routing HL7 messages based on rules."""
    
    def __init__(self, queue_manager: QueueManager):
        """Initialize the routing service.
        
        Args:
            queue_manager: Queue manager for receiving and publishing messages
        """
        self.queue_manager = queue_manager
        self.routes = self._load_routes()
    
    def _load_routes(self) -> List[Dict]:
        """Load routing rules.
        
        Returns:
            List of route definitions
        """
        # TODO: Load from configuration
        return [
            {
                "name": "hl7_to_file",
                "description": "Route HL7 messages to file writer",
                "conditions": [
                    {"field": "message_type", "op": "eq", "value": "HL7v2"},
                    {"field": "validation_status", "op": "eq", "value": "success"}
                ],
                "actions": [
                    {"type": "publish", "queue": "file.write"}
                ]
            },
            {
                "name": "error_to_file",
                "description": "Route error messages to error file writer",
                "conditions": [
                    {"field": "validation_status", "op": "eq", "value": "failed"}
                ],
                "actions": [
                    {"type": "publish", "queue": "file.write"}
                ]
            }
        ]
    
    async def start(self):
        """Start the routing service."""
        await self.queue_manager.subscribe("hl7.validated", self._route_message)
        await self.queue_manager.subscribe("hl7.transformed", self._route_message)
        logger.info("HL7 Routing Service started")
    
    async def _route_message(self, message_data: Dict[str, Any]):
        """Route a message based on its content.
        
        Args:
            message_data: Message data to route
        """
        try:
            message = Message.from_dict(message_data)
            
            # Apply routing rules
            for route in self.routes:
                if self._matches_conditions(message, route.get("conditions", [])):
                    logger.info(f"Message matched route: {route['name']}")
                    await self._apply_actions(message, route.get("actions", []))
                    return
            
            # Default action if no routes match
            logger.warning("No matching route found for message")
            
        except Exception as e:
            logger.error(f"Error routing message: {e}")
            
            # Send to error queue
            if 'message' in locals():
                message.metadata["error"] = str(e)
                await self.queue_manager.publish("hl7.routing_error", message.to_dict())
    
    def _matches_conditions(self, message: Message, conditions: List[Dict]) -> bool:
        """Check if a message matches all conditions.
        
        Args:
            message: Message to check
            conditions: List of conditions to check
            
        Returns:
            bool: True if all conditions match, False otherwise
        """
        for condition in conditions:
            field = condition.get("field")
            op = condition.get("op")
            value = condition.get("value")
            
            # Get field value from message
            if field == "message_type":
                field_value = message.message_type
            elif field in message.metadata:
                field_value = message.metadata[field]
            else:
                return False
            
            # Apply operator
            if op == "eq" and field_value != value:
                return False
            elif op == "ne" and field_value == value:
                return False
            elif op == "in" and field_value not in value:
                return False
            elif op == "not_in" and field_value in value:
                return False
            elif op == "contains" and value not in str(field_value):
                return False
            elif op == "not_contains" and value in str(field_value):
                return False
        
        return True
    
    async def _apply_actions(self, message: Message, actions: List[Dict]):
        """Apply actions to a message.
        
        Args:
            message: Message to apply actions to
            actions: List of actions to apply
        """
        for action in actions:
            action_type = action.get("type")
            
            if action_type == "publish":
                queue = action.get("queue")
                if queue:
                    await self.queue_manager.publish(queue, message.to_dict())
            elif action_type == "transform":
                transform_type = action.get("transform_type")
                if transform_type:
                    message.metadata["transform_type"] = transform_type
                    await self.queue_manager.publish("hl7.transform", message.to_dict())
