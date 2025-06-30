"""Message routing processor."""
import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

from core.interfaces.processor import Processor
from core.models.message import MessageEnvelope, MessageStatus

logger = logging.getLogger(__name__)


class RouteRule:
    """Rule for routing messages to destinations."""
    
    def __init__(
        self,
        name: str,
        condition: Union[dict, callable],
        destinations: List[str],
        priority: int = 0,
        **kwargs
    ):
        """Initialize a route rule.
        
        Args:
            name: Name of the rule
            condition: Condition to match messages (dict or callable)
            destinations: List of destination names to route to
            priority: Rule priority (higher = evaluated first)
            **kwargs: Additional rule metadata
        """
        self.name = name
        self.condition = condition
        self.destinations = destinations
        self.priority = priority
        self.metadata = kwargs
        
        # Compile regex patterns if condition is a dict with regex
        if isinstance(self.condition, dict):
            self._compile_patterns(self.condition)
    
    def _compile_patterns(self, condition: dict) -> None:
        """Compile regex patterns in the condition."""
        if isinstance(condition, dict):
            for key, value in list(condition.items()):
                if key == "$regex" and isinstance(value, str):
                    condition[key] = re.compile(value)
                elif isinstance(value, (dict, list)):
                    self._compile_patterns(value)
        elif isinstance(condition, list):
            for item in condition:
                if isinstance(item, (dict, list)):
                    self._compile_patterns(item)
    
    def matches(self, message: MessageEnvelope) -> bool:
        """Check if a message matches this rule.
        
        Args:
            message: The message to check
            
        Returns:
            bool: True if the message matches the rule
        """
        if callable(self.condition):
            return self.condition(message)
        elif isinstance(self.condition, dict):
            return self._matches_dict(self.condition, message)
        return False
    
    def _matches_dict(self, condition: dict, message: MessageEnvelope) -> bool:
        """Check if a message matches a condition dictionary.
        
        Args:
            condition: The condition to match against
            message: The message to check
            
        Returns:
            bool: True if the message matches all conditions
        """
        for key, value in condition.items():
            # Handle special operators
            if key.startswith('$'):
                if key == '$and':
                    if not all(self._matches_dict(item, message) for item in value):
                        return False
                elif key == '$or':
                    if not any(self._matches_dict(item, message) for item in value):
                        return False
                elif key == '$not':
                    if self._matches_dict(value, message):
                        return False
                elif key == '$regex':
                    if not self._match_regex(value, message):
                        return False
                elif key == '$in':
                    field, values = next(iter(value.items()))
                    if not self._get_field_value(message, field) in values:
                        return False
                else:
                    logger.warning(f"Unsupported operator: {key}")
                    return False
            else:
                # Simple field comparison
                field_value = self._get_field_value(message, key)
                if field_value != value:
                    return False
        
        return True
    
    def _match_regex(self, pattern: str, message: MessageEnvelope) -> bool:
        """Check if any field in the message matches a regex pattern.
        
        Args:
            pattern: Compiled regex pattern
            message: The message to check
            
        Returns:
            bool: True if any field matches the pattern
        """
        # Convert message to flat dict for regex search
        message_dict = self._flatten_message(message)
        message_json = json.dumps(message_dict, default=str)
        return bool(pattern.search(message_json))
    
    def _flatten_message(self, message: MessageEnvelope) -> dict:
        """Flatten a message into a dictionary for searching.
        
        Args:
            message: The message to flatten
            
        Returns:
            dict: Flattened message
        """
        result = {}
        
        # Add header fields
        header = message.header
        result['header'] = {
            'message_id': str(header.message_id),
            'correlation_id': str(header.correlation_id) if header.correlation_id else None,
            'message_type': header.message_type,
            'source': header.source,
            'destination': header.destination,
            'timestamp': header.timestamp.isoformat(),
            'status': header.status.value,
            'retry_count': header.retry_count,
            **header.metadata
        }
        
        # Add body fields
        body = message.body
        result['body'] = {
            'content_type': body.content_type,
            'content': body.content,
            'raw_content': body.raw_content.decode('utf-8') if isinstance(body.raw_content, bytes) else body.raw_content,
            'schema_id': body.schema_id,
            **body.metadata
        }
        
        return result
    
    def _get_field_value(self, message: MessageEnvelope, field_path: str) -> Any:
        """Get a value from a message using a dot-notation path.
        
        Args:
            message: The message to get the value from
            field_path: Dot-notation path to the field (e.g., 'header.message_type')
            
        Returns:
            The field value or None if not found
        """
        parts = field_path.split('.')
        value = None
        
        try:
            if parts[0] == 'header':
                value = message.header
                for part in parts[1:]:
                    value = getattr(value, part, None) or value.get(part)
            elif parts[0] == 'body':
                value = message.body
                for part in parts[1:]:
                    value = getattr(value, part, None) or value.get(part)
            elif parts[0] == 'metadata':
                value = message.body.metadata or {}
                for part in parts[1:]:
                    value = value.get(part)
            else:
                # Try to find in header or body
                value = getattr(message.header, parts[0], None) or \
                        getattr(message.body, parts[0], None)
                
                if value is not None and len(parts) > 1:
                    for part in parts[1:]:
                        value = getattr(value, part, None) or (value.get(part) if hasattr(value, 'get') else None)
        except (AttributeError, KeyError, IndexError):
            return None
            
        return value


class RoutingProcessor(Processor):
    """Processor for routing messages to different outputs."""
    
    def __init__(self, rules: Optional[List[dict]] = None, default_destinations: Optional[List[str]] = None):
        """Initialize the routing processor.
        
        Args:
            rules: List of route rule definitions
            default_destinations: Default destinations if no rules match
        """
        self.rules: List[RouteRule] = []
        self.default_destinations = default_destinations or []
        self.running = False
        
        # Add rules if provided
        if rules:
            for rule_def in rules:
                self.add_rule(rule_def)
    
    async def start(self) -> None:
        """Start the processor."""
        self.running = True
        logger.info("Started routing processor")
    
    async def stop(self) -> None:
        """Stop the processor."""
        self.running = False
        logger.info("Stopped routing processor")
    
    def add_rule(self, rule_def: dict) -> None:
        """Add a routing rule.
        
        Args:
            rule_def: Rule definition dictionary
        """
        rule = RouteRule(**rule_def)
        self.rules.append(rule)
        # Sort rules by priority (highest first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added routing rule: {rule.name}")
    
    async def process(self, message: MessageEnvelope) -> AsyncGenerator[MessageEnvelope, None]:
        """Process a message.
        
        Args:
            message: The message to process
            
        Yields:
            Processed message(s) with routing information
        """
        if not self.running:
            logger.warning("Routing processor is not running")
            return
        
        try:
            # Skip if already routed
            if message.header.status == MessageStatus.ROUTED:
                yield message
                return
            
            # Find matching rules
            destinations = set()
            for rule in self.rules:
                if rule.matches(message):
                    destinations.update(rule.destinations)
                    logger.debug(f"Message {message.header.message_id} matched rule: {rule.name}")
            
            # Add default destinations if no rules matched
            if not destinations and self.default_destinations:
                destinations.update(self.default_destinations)
                logger.debug(f"Using default destinations for message {message.header.message_id}")
            
            # Update message with routing information
            if not message.header.metadata:
                message.header.metadata = {}
                
            message.header.metadata["routing"] = {
                "destinations": list(destinations),
                "timestamp": message.header.timestamp.isoformat()
            }
            
            # Update message status
            message.header.status = MessageStatus.ROUTED
            
            logger.info(f"Routed message {message.header.message_id} to {len(destinations)} destinations")
            yield message
            
        except Exception as e:
            await self.handle_error(e, message)
    
    async def handle_error(self, error: Exception, message: Optional[MessageEnvelope] = None) -> None:
        """Handle processing errors.
        
        Args:
            error: The exception that occurred
            message: The message being processed when the error occurred (if any)
        """
        error_msg = str(error)
        logger.error(f"Routing error: {error_msg}")
        
        if message:
            # Update message status
            message.header.status = MessageStatus.FAILED
            
            # Add error metadata
            if not message.body.metadata:
                message.body.metadata = {}
                
            if "errors" not in message.body.metadata:
                message.body.metadata["errors"] = []
                
            message.body.metadata["errors"].append({
                "type": "routing",
                "message": error_msg,
                "timestamp": message.header.timestamp.isoformat()
            })
