from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase, basic_auth
import os
from ...config import settings
from ..models.base import Production, Component, RoutingRule

class Neo4jImporter:
    """Imports IRIS production data into Neo4j."""
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "healthcare123")
        self.driver = None
    
    def connect(self):
        """Establish connection to Neo4j."""
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=basic_auth(self.user, self.password)
        )
    
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
    
    def import_production(self, production: Production) -> Dict[str, Any]:
        """Import a complete production into Neo4j."""
        if not self.driver:
            self.connect()
        
        result = {
            'production': None,
            'components': 0,
            'relationships': 0,
            'routing_rules': 0
        }
        
        with self.driver.session() as session:
            # Create or update production node
            query = """
            MERGE (p:Production {name: $name})
            SET p.description = $description,
                p.actor_pool_size = $actor_pool_size,
                p.log_general_trace_events = $log_general_trace_events
            RETURN p
            """
            
            prod_result = session.run(query, {
                'name': production.name,
                'description': production.description,
                'actor_pool_size': production.actor_pool_size,
                'log_general_trace_events': production.log_general_trace_events
            }).single()
            
            if prod_result:
                result['production'] = prod_result['p']
            
            # Import components
            for component in production.components:
                self._import_component(session, production.name, component)
                result['components'] += 1
            
            # Import routing rules
            for rule in production.routing_rules:
                self._import_routing_rule(session, production.name, rule)
                result['routing_rules'] += 1
            
            # Create relationships
            result['relationships'] = self._create_relationships(session, production.name)
            
        return result
    
    def _import_component(self, session, production_name: str, component: Component):
        """Import a single component into Neo4j."""
        query = """
        MATCH (p:Production {name: $production_name})
        MERGE (c:Component {name: $name, class_name: $class_name})
        SET c.type = $type,
            c.pool_size = $pool_size,
            c.enabled = $enabled,
            c.comment = $comment,
            c += $settings
        WITH p, c
        MERGE (p)-[:HAS_COMPONENT]->(c)
        """
        
        session.run(query, {
            'production_name': production_name,
            'name': component.name,
            'class_name': component.class_name,
            'type': component.type,
            'pool_size': component.pool_size,
            'enabled': component.enabled,
            'comment': component.comment,
            'settings': component.settings
        })
    
    def _import_routing_rule(self, session, production_name: str, rule: RoutingRule):
        """Import a routing rule into Neo4j."""
        # Create rule node
        query = """
        MATCH (p:Production {name: $production_name})
        MERGE (r:RoutingRule {name: $name})
        SET r.description = $description,
            r.conditions = $conditions,
            r.actions = $actions
        WITH p, r
        MERGE (p)-[:HAS_ROUTING_RULE]->(r)
        """
        
        session.run(query, {
            'production_name': production_name,
            'name': rule.name,
            'description': rule.description,
            'conditions': rule.conditions,
            'actions': rule.actions
        })
    
    def _create_relationships(self, session, production_name: str) -> int:
        """Create relationships between components based on message flow."""
        # This is a simplified example - in a real implementation, you would analyze
        # the routing rules and component configurations to create accurate relationships
        
        # For now, we'll create a simple relationship based on naming conventions
        # In a real implementation, you would parse the routing rules to create accurate relationships
        
        query = """
        MATCH (c1:Component)-[:BELONGS_TO]->(p:Production {name: $production_name})
        WHERE c1.name STARTS WITH 'from' AND NOT c1.name CONTAINS 'Route'
        WITH c1, p
        MATCH (router:Component)-[:BELONGS_TO]->(p)
        WHERE router.name CONTAINS 'Route' OR router.type = 'Router'
        MERGE (c1)-[:SENDS_TO]->(router)
        WITH router, p
        MATCH (c2:Component)-[:BELONGS_TO]->(p)
        WHERE c2.name STARTS WITH 'to' AND c2 <> router
        MERGE (router)-[:ROUTES_TO]->(c2)
        RETURN count(*) as count
        """
        
        result = session.run(query, {'production_name': production_name}).single()
        return result['count'] if result else 0
