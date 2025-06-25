from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json
import logging
from .neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

class Message(BaseModel):
    """Represents a message in the integration engine."""
    message_id: str = Field(..., description="Unique message identifier")
    message_type: str = Field(..., description="Message type (e.g., ADT_A01, ORU_R01)")
    source_system: str = Field(..., description="Source system identifier")
    destination_systems: List[str] = Field(default_factory=list, description="List of target system IDs")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    status: str = Field("received", description="Current status of the message")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when message was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when message was last updated")

class MessageRouter:
    """Handles message routing using Neo4j graph database."""
    
    def __init__(self, neo4j_client: Optional[Neo4jClient] = None):
        self.neo4j = neo4j_client or Neo4jClient()
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Ensure the Neo4j schema is properly initialized."""
        self.neo4j.initialize_schema()
    
    async def route_message(self, message: Message) -> Message:
        """
        Route a message through the integration engine based on defined rules.
        
        Args:
            message: The message to route
            
        Returns:
            The updated message with routing information
        """
        try:
            # Update message status
            message.status = "routing"
            message.updated_at = datetime.utcnow()
            
            # Find applicable routes
            routes = self._find_routes_for_message(message)
            
            if not routes:
                message.status = "no_route"
                logger.warning(f"No routes found for message {message.message_id}")
                return message
            
            # Process routes in priority order
            processed_systems = set()
            for route in routes:
                target_system = route['target_system']
                
                # Skip if we've already processed this system for this message
                if target_system in processed_systems:
                    continue
                
                # Add to processed systems
                processed_systems.add(target_system)
                
                # Process the route (in a real system, this would be async)
                await self._process_route(message, route)
            
            # Update message with successful routing
            message.destination_systems = list(processed_systems)
            message.status = "routed"
            
            # Log the successful routing
            logger.info(f"Successfully routed message {message.message_id} to systems: {message.destination_systems}")
            
            return message
            
        except Exception as e:
            message.status = f"error: {str(e)}"
            logger.error(f"Error routing message {message.message_id}: {str(e)}", exc_info=True)
            raise
    
    def _find_routes_for_message(self, message: Message) -> List[Dict[str, Any]]:
        """
        Find all valid routes for the given message.
        
        Args:
            message: The message to find routes for
            
        Returns:
            List of route dictionaries containing routing information
        """
        query = """
        MATCH (source:System {id: $source_system})
        MATCH (mt:MessageType {id: $message_type})
        MATCH (source)-[:PROVIDES]->(svc:BusinessService)-[:HANDLES]->(mt)
        MATCH path = (svc)-[:ROUTES_TO*1..5]->(op:BusinessOperation)
        WHERE ALL(r IN relationships(path) WHERE 
                 (r.condition IS NULL OR 
                  (r.condition = 'messageType = "' + $message_type + '"')))
        WITH nodes(path) as nodes, relationships(path) as rels
        UNWIND range(0, size(rels)-1) as idx
        WITH nodes[idx] as source_node, nodes[idx+1] as target_node, rels[idx] as rel
        WHERE 'BusinessService' IN labels(source_node) AND 'BusinessOperation' IN labels(target_node)
        MATCH (target_sys:System)-[:PROVIDES]->(target_node)
        RETURN {
            source: source_node.id,
            target: target_node.id,
            target_system: target_sys.id,
            rule: rel.rule,
            priority: COALESCE(rel.priority, 99)
        } as route
        ORDER BY route.priority ASC
        """
        
        params = {
            'source_system': message.source_system,
            'message_type': message.message_type.lower()
        }
        
        try:
            routes = self.neo4j.execute_query(query, params)
            return [route['route'] for route in routes]
        except Exception as e:
            logger.error(f"Error finding routes: {str(e)}", exc_info=True)
            return []
    
    async def _process_route(self, message: Message, route: Dict[str, Any]) -> bool:
        """
        Process a single message route.
        
        Args:
            message: The message being routed
            route: The route to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # In a real implementation, this would:
            # 1. Apply any transformations
            # 2. Handle protocol-specific communication
            # 3. Update message status and logging
            
            logger.info(f"Processing route: {route['source']} -> {route['target']} for message {message.message_id}")
            
            # Simulate processing delay
            # await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing route {route.get('rule', 'unknown')} for message {message.message_id}: {str(e)}")
            return False
    
    def get_message_history(self, message_id: str) -> List[Dict[str, Any]]:
        """
        Get the processing history for a message.
        
        Args:
            message_id: The ID of the message
            
        Returns:
            List of processing events
        """
        # In a real implementation, this would query a message store
        return [{
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'retrieved',
            'details': f'Retrieved history for message {message_id}'
        }]

# Singleton instance for easy import
router = MessageRouter()
