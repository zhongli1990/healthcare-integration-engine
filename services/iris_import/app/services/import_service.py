"""
Service for importing IRIS production data into Neo4j.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

from neo4j import GraphDatabase, exceptions as neo4j_exceptions

from .graph_extractor import GraphExtractor
from ..parsers.production_parser import parse_production_file
from ..parsers.routing_rule_parser import parse_routing_rule_file

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Raised when validation of extracted data fails."""
    pass


def log_parsed_data(component_type: str, data: dict):
    """Log parsed data in a structured format."""
    logger.info(f"Parsed {component_type} data:")
    logger.info(json.dumps(data, indent=2, default=str)[:1000] + ("..." if len(json.dumps(data, default=str)) > 1000 else ""))


def log_cypher_query(query: str, params: dict = None):
    """Log Cypher query and parameters."""
    logger.debug("Executing Cypher query:")
    logger.debug(query)
    if params:
        logger.debug("With parameters:")
        logger.debug(json.dumps(params, indent=2, default=str))

class ImportService:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """Initialize the import service with Neo4j connection details."""
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
    
    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
    
    def _import_components(self, session, components: List[Dict]) -> Tuple[int, int]:
        """Import components into Neo4j and return (created, failed) counts."""
        created = 0
        failed = 0
        
        def flatten_dict(d: Dict, prefix: str = '') -> Dict:
            """Flatten a nested dictionary into a single level with dot notation.
            
            Args:
                d: Dictionary to flatten
                prefix: Prefix to add to all keys (for nested dictionaries)
                
            Returns:
                Flattened dictionary with string values
            """
            items = {}
            if not isinstance(d, dict):
                logger.warning(f"Expected dict, got {type(d).__name__}: {d}")
                return {prefix: str(d) if d is not None else ''}
                
            for k, v in d.items():
                if not isinstance(k, str):
                    k = str(k)
                    
                new_key = f"{prefix}{k}" if prefix else k
                
                # Skip empty or None keys
                if not k:
                    continue
                    
                try:
                    if isinstance(v, dict):
                        # Recursively flatten nested dictionaries
                        items.update(flatten_dict(v, f"{new_key}."))
                    elif isinstance(v, (list, tuple)):
                        # Convert lists/tuples to JSON strings
                        try:
                            items[new_key] = json.dumps(v, ensure_ascii=False)
                        except (TypeError, ValueError) as e:
                            logger.warning(f"Could not JSON serialize list/tuple: {e}")
                            items[new_key] = str(v)
                    elif v is None:
                        items[new_key] = ''
                    else:
                        # Convert all other types to string
                        items[new_key] = str(v)
                except Exception as e:
                    logger.error(f"Error processing {new_key}: {str(e)}", exc_info=True)
                    items[new_key] = f"[ERROR: {str(e)[:100]}]"
                    
            return items
        
        logger.info(f"Starting import of {len(components)} components")
        
        for i, component in enumerate(components, 1):
            component_id = component.get('id', f'component_{i}')
            try:
                logger.debug(f"Processing component {i}/{len(components)}: {component_id}")
                
                # Prepare base properties - ensure they are all strings
                properties = {
                    'id': str(component.get('id', '')),
                    'name': str(component.get('name', '')),
                    'type': str(component.get('type', '')),
                    'className': str(component.get('className', '')),
                    'enabled': str(component.get('enabled', 'true')).lower(),
                    'source': 'production'
                }
                
                # Flatten settings and attributes into individual properties
                settings = component.get('settings', {})
                attributes = component.get('attributes', {})
                
                # Add flattened settings and attributes with appropriate prefixes
                properties.update(flatten_dict(settings, 'setting_'))
                properties.update(flatten_dict(attributes, 'attr_'))
                
                # Ensure all values are strings and not empty
                for k, v in list(properties.items()):
                    if v is None:
                        properties[k] = ''
                    elif not isinstance(v, str):
                        properties[k] = str(v)
                
                # Log a sample of the properties for debugging
                sample_props = {k: v for i, (k, v) in enumerate(properties.items()) if i < 5}
                logger.debug(f"Sample properties for {component_id}: {sample_props}...")
                
                # Build the Cypher query
                prop_strings = [f"{k}: ${k}" for k in properties.keys()]
                query = f"""
                MERGE (c:Component {{id: $id}})
                SET c += {{{', '.join(f'{k}: ${k}' for k in properties.keys() if k != 'id')}}}
                RETURN id(c) as id
                """
                
                # Log the query without parameters for security
                log_cypher_query(query, properties if logger.isEnabledFor(logging.DEBUG) else {})
                
                # Execute the query
                result = session.run(query, parameters=properties)
                record = result.single()
                
                if record:
                    created += 1
                    logger.info(f"Created/updated component: {component_id} ({component.get('type', '')})")
                else:
                    failed += 1
                    logger.warning(f"No result when creating component: {component_id}")
                
            except Exception as e:
                failed += 1
                logger.error(f"Error creating component {component_id}: {str(e)}", exc_info=True)
                
                # Log detailed component info for debugging
                logger.debug(f"Problematic component data: {json.dumps(component, default=str, indent=2)}")
                
        logger.info(f"Completed import: {created} created/updated, {failed} failed")
        return created, failed
    
    def _import_relationships(self, session, relationships: List[Dict]) -> Tuple[int, int]:
        """Import relationships into Neo4j and return (created, failed) counts."""
        created = 0
        failed = 0
        
        for rel in relationships:
            try:
                # Prepare the relationship query
                query = """
                MATCH (source {id: $source_id}), (target {id: $target_id})
                CREATE (source)-[r:CONNECTED_TO {type: $rel_type}]->(target)
                RETURN id(r) as id
                """
                params = {
                    'source_id': rel['source'],
                    'target_id': rel['target'],
                    'rel_type': rel.get('type', 'CONNECTED_TO')
                }
                
                log_cypher_query(query, params)
                result = session.run(query, params)
                created += 1
                logger.info(f"Created relationship: {rel['source']} -> {rel['target']}")
                
            except Exception as e:
                logger.error(f"Error creating relationship {rel['source']} -> {rel['target']}: {str(e)}")
                failed += 1
                
        return created, failed
    
    def verify_import(self, session, expected_components: int, expected_relationships: int) -> Dict[str, Any]:
        """Verify the import by counting nodes and relationships."""
        try:
            # Count all nodes
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            
            # Count all relationships
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
            # Get component types distribution
            type_dist = session.run("""
                MATCH (n) 
                RETURN n.type as type, count(*) as count
                ORDER BY count DESC
            """).data()
            
            verification = {
                'nodes_imported': node_count,
                'relationships_imported': rel_count,
                'type_distribution': type_dist,
                'success': node_count > 0 and node_count >= expected_components * 0.9,  # At least 90% of expected
                'warnings': []
            }
            
            if node_count < expected_components:
                verification['warnings'].append(f'Expected {expected_components} components but found {node_count}')
                
            if rel_count < expected_relationships:
                verification['warnings'].append(f'Expected {expected_relationships} relationships but found {rel_count}')
                
            return verification
            
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_graph_data(self, graph_data: Dict) -> None:
        """Validate the extracted graph data.
        
        Args:
            graph_data: Dictionary containing 'nodes' and 'relationships' keys
            
        Raises:
            ValidationError: If the graph data is invalid
        """
        if not graph_data or 'nodes' not in graph_data or 'relationships' not in graph_data:
            raise ValidationError("Invalid graph data format: missing 'nodes' or 'relationships'")
        
        nodes = graph_data.get('nodes', [])
        relationships = graph_data.get('relationships', [])
        
        # Check for empty extraction
        if not nodes:
            raise ValidationError("No components were extracted from the files")
            
        if not relationships:
            logger.warning("No relationships were extracted from the files")
            
        # Check for duplicate node names
        node_names = [node['name'] for node in nodes]
        if len(node_names) != len(set(node_names)):
            raise ValidationError("Duplicate component names found in the extracted data")
        
        # Validate node structure
        for node in nodes:
            if 'name' not in node or 'type' not in node or 'label' not in node:
                raise ValidationError(f"Invalid node structure: {node}")
        
        # Validate relationship structure
        for rel in relationships:
            if 'source' not in rel or 'target' not in rel or 'type' not in rel:
                raise ValidationError(f"Invalid relationship structure: {rel}")
            
            # Check if source and target nodes exist
            if rel['source'] not in node_names or rel['target'] not in node_names:
                raise ValidationError(f"Relationship references non-existent node: {rel}")
    
    def _import_graph_data(self, graph_data: Dict) -> Dict[str, int]:
        """Import graph data into Neo4j.
        
        Args:
            graph_data: Dictionary containing 'nodes' and 'relationships' keys
            
        Returns:
            Dictionary with import statistics
        """
        stats = {
            'nodes_created': 0,
            'relationships_created': 0,
            'nodes_failed': 0,
            'relationships_failed': 0
        }
        
        logger.info(f"Starting import of {len(graph_data.get('nodes', []))} nodes and {len(graph_data.get('relationships', []))} relationships")
        
        with self.driver.session() as session:
            # Begin a transaction
            tx = session.begin_transaction()
            
            try:
                # Import nodes
                for i, node in enumerate(graph_data.get('nodes', []), 1):
                    node_name = node.get('name', f'unnamed_node_{i}')
                    logger.debug(f"Processing node {i}/{len(graph_data.get('nodes', []))}: {node_name}")
                    
                    try:
                        node_id = self._import_node(tx, node)
                        if node_id:
                            stats['nodes_created'] += 1
                            if stats['nodes_created'] % 10 == 0:  # Log progress every 10 nodes
                                logger.info(f"Imported {stats['nodes_created']} nodes so far...")
                        else:
                            stats['nodes_failed'] += 1
                            logger.warning(f"Failed to import node: {node_name}")
                    except Exception as e:
                        stats['nodes_failed'] += 1
                        logger.error(f"Error importing node {node_name}: {str(e)}", exc_info=True)
                
                logger.info(f"Completed node import: {stats['nodes_created']} created, {stats['nodes_failed']} failed")
                
                # Import relationships
                for i, rel in enumerate(graph_data.get('relationships', []), 1):
                    try:
                        if self._create_relationship(tx, rel):
                            stats['relationships_created'] += 1
                            if stats['relationships_created'] % 10 == 0:  # Log progress every 10 relationships
                                logger.info(f"Created {stats['relationships_created']} relationships so far...")
                        else:
                            stats['relationships_failed'] += 1
                            logger.warning(f"Failed to create relationship: {rel.get('source')} -> {rel.get('target')}")
                    except Exception as e:
                        stats['relationships_failed'] += 1
                        logger.error(f"Error creating relationship {rel.get('source')} -> {rel.get('target')}: {str(e)}", exc_info=True)
                
                logger.info(f"Completed relationship import: {stats['relationships_created']} created, {stats['relationships_failed']} failed")
                
                # Commit the transaction
                tx.commit()
                logger.info("Successfully committed transaction")
                
            except Exception as e:
                # Rollback on error
                logger.error(f"Error during import, rolling back transaction: {str(e)}", exc_info=True)
                if tx.closed() is False:
                    tx.rollback()
                    logger.info("Transaction rolled back")
                raise
            
            # Verify the import
            result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = result.single()["count"]
            logger.info(f"Verification: Found {node_count} nodes in the database")
            
            if node_count == 0:
                logger.error("No nodes found in the database after import!")
            else:
                # Log a sample of the imported nodes
                result = session.run("MATCH (n) RETURN n.name as name, labels(n) as labels LIMIT 5")
                logger.info("Sample of imported nodes:")
                for record in result:
                    logger.info(f"  - {record['name']} ({record['labels']})")
        
        return stats
    
    def _flatten_properties(self, props: Dict, prefix: str = '') -> Dict:
        """
        Flatten nested dictionaries into dot notation for Neo4j properties.
        Converts all values to strings to ensure compatibility.
        """
        flattened = {}
        if not isinstance(props, dict):
            return {prefix: str(props) if props is not None else ''} if prefix else {}
            
        for key, value in props.items():
            # Skip None values
            if value is None:
                continue
                
            # Create the full key with prefix if needed
            full_key = f"{prefix}.{key}" if prefix else key
            
            # Handle nested dictionaries recursively
            if isinstance(value, dict):
                flattened.update(self._flatten_properties(value, full_key))
            # Convert lists to JSON strings
            elif isinstance(value, (list, tuple)):
                flattened[full_key] = json.dumps(value)
            # Convert other types to strings
            else:
                flattened[full_key] = str(value)
                
        return flattened
    
    def _import_node(self, session, node: Dict) -> Optional[str]:
        """Import a single node into Neo4j."""
        try:
            node_name = node.get('name', 'unnamed_node')
            logger.debug(f"Starting import of node: {node_name}")
            
            # Get and flatten all properties
            node_props = node.get('properties', {})
            settings = node.get('settings', {})
            
            logger.debug(f"Node raw properties: {json.dumps(node_props, indent=2)}")
            logger.debug(f"Node settings: {json.dumps(settings, indent=2)}")
            
            # Flatten all properties
            flat_props = {}
            flat_props.update(self._flatten_properties(node_props, 'props'))
            flat_props.update(self._flatten_properties(settings, 'settings'))
            
            # Add required properties
            flat_props.update({
                'name': node.get('name', ''),
                'type': node.get('type', ''),
                'label': node.get('label', ''),
                'createdAt': datetime.utcnow().isoformat()
            })
            
            # Filter out None values and ensure all values are strings
            properties = {}
            for k, v in flat_props.items():
                if v is not None:
                    if isinstance(v, (dict, list)):
                        properties[k] = json.dumps(v)
                    else:
                        properties[k] = str(v)
            
            logger.debug(f"Flattened properties for {node_name}: {json.dumps(properties, indent=2)}")
            
            # Create or update node
            query = """
            MERGE (n:Component {name: $name})
            SET n += $properties
            RETURN id(n) as id
            """
            
            logger.info(f"Importing node: {node_name}")
            
            try:
                result = session.run(query, {
                    'name': node['name'],
                    'properties': properties
                })
                
                record = result.single()
                if not record:
                    logger.error(f"No result returned when creating node: {node_name}")
                    return None
                    
                node_id = record.get('id')
                if not node_id:
                    logger.error(f"No ID returned for node: {node_name}")
                    return None
                    
                logger.info(f"Successfully imported node {node_name} with ID {node_id}")
                return node_id
                
            except Exception as e:
                logger.error(f"Database error while importing node {node_name}: {str(e)}", exc_info=True)
                raise
            
        except Exception as e:
            logger.error(f"Failed to process node {node.get('name', 'unnamed_node')}: {str(e)}", exc_info=True)
            return None
    
    def _create_relationship(self, session, rel: Dict) -> bool:
        """Create a relationship between two nodes in Neo4j."""
        query = """
        MATCH (a {name: $source}), (b {name: $target})
        MERGE (a)-[r:%s]->(b)
        SET r += $properties
        RETURN type(r) as type
        """ % rel['type']
        
        try:
            result = session.run(
                query,
                source=rel['source'],
                target=rel['target'],
                properties=rel.get('properties', {})
            )
            return result.single() is not None
        except Exception as e:
            logger.error(f"Error creating relationship: {str(e)}")
            return False
    
    def import_production(self, production_file: str, routing_rule_file: str = None) -> Dict:
        """
        Import a production and its routing rules into Neo4j using GraphExtractor and RelationshipExtractor.
        
        Args:
            production_file: Path to the production .cls file
            routing_rule_file: Optional path to the routing rule .cls file (not needed for relationship extraction)
            
        Returns:
            Dict containing import statistics and verification results
        """
        logger.info(f"Starting import of production: {production_file}")
        
        try:
            # 1. Read the production file content
            with open(production_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 2. Extract components using GraphExtractor
            logger.info("Extracting components using GraphExtractor...")
            extractor = GraphExtractor()
            graph_data = extractor.extract_from_files(production_file, routing_rule_file or '')
            nodes = graph_data.get('nodes', [])
            
            # 3. Extract relationships using RelationshipExtractor
            logger.info("Extracting relationships using RelationshipExtractor...")
            from tests.test_relationships import RelationshipExtractor
            rel_extractor = RelationshipExtractor()
            relationships = rel_extractor.extract_relationships(content)
            
            # 4. Add relationships to graph_data
            graph_data['relationships'] = relationships
            
            # 5. Log extraction results
            logger.info(f"Extracted {len(nodes)} nodes and {len(relationships)} relationships")
            
            # 5. Clear existing data
            try:
                with self.driver.session() as session:
                    logger.info("Clearing existing data...")
                    result = session.run("MATCH (n) RETURN count(n) as count").single()
                    logger.info(f"Found {result['count']} existing nodes to delete")
                    
                    delete_result = session.run("MATCH (n) DETACH DELETE n")
                    logger.info("Existing data cleared")
                    
                    # Verify data was cleared
                    result = session.run("MATCH (n) RETURN count(n) as count").single()
                    if result['count'] > 0:
                        logger.warning(f"Failed to clear all data: {result['count']} nodes remain")
                    else:
                        logger.info("Successfully cleared all data")
                        
                    # Verify Neo4j is writable
                    test_node = session.run("CREATE (t:TestNode {test: true}) RETURN id(t)")
                    test_id = test_node.single()[0]
                    session.run(f"MATCH (t) WHERE id(t) = {test_id} DELETE t")
                    logger.info("Verified Neo4j is writable")
                    
            except Exception as e:
                logger.error(f"Failed to clear existing data: {str(e)}", exc_info=True)
                raise
            
            # 6. Import graph data
            logger.info("Importing graph data into Neo4j...")
            try:
                import_stats = self._import_graph_data(graph_data)
                logger.info(f"Import completed: {import_stats}")
            except Exception as e:
                logger.error(f"Failed to import graph data: {str(e)}", exc_info=True)
                raise
            
            # 7. Verify import
            logger.info("Verifying import...")
            verification = self.verify_import(
                self.driver.session(),
                expected_components=len(nodes),
                expected_relationships=len(relationships)
            )
            
            # 8. Prepare results
            result = {
                'success': verification['success'],
                'message': 'Import completed successfully',
                'statistics': {
                    'nodes_created': import_stats['nodes_created'],
                    'relationships_created': import_stats['relationships_created'],
                    'nodes_failed': import_stats['nodes_failed'],
                    'relationships_failed': import_stats['relationships_failed']
                },
                'verification': verification,
                'metadata': graph_data.get('metadata', {})
            }
            
            # Log verification results
            if verification['success']:
                logger.info("Import verification successful!")
            else:
                logger.warning("Import verification found issues!")
            
            for warning in verification.get('warnings', []):
                logger.warning(f"Verification warning: {warning}")
            
            # 9. Return results
            result = {
                'success': verification['success'],
                'message': 'Import completed with verification',
                'statistics': {
                    'nodes_created': import_stats['nodes_created'],
                    'nodes_failed': import_stats['nodes_failed'],
                    'relationships_created': import_stats['relationships_created'],
                    'relationships_failed': import_stats['relationships_failed']
                },
                'verification': verification,
                'metadata': graph_data.get('metadata', {})
            }
            
            logger.info(f"Import completed: {json.dumps(result, indent=2, default=str)}")
            return result
        
        except Exception as e:
            error_msg = f"Failed to import production: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'message': error_msg,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Error during import: {str(e)}", exc_info=True)
            raise
    
    def _import_components(self, session, components: List[Dict]) -> Tuple[int, int]:
        """
        Import production components into Neo4j.
        
        Args:
            session: Neo4j session
            components: List of component dictionaries to import
            
        Returns:
            Tuple of (created_count, failed_count)
        """
        created = 0
        failed = 0
        
        if not components:
            logger.info("No components to import")
            return created, failed
        
        for component in components:
            component_type = component.get('type', '').split('.').pop()
            
            # Create or update the component node
            query = """
            MERGE (c:Component {name: $name})
            SET c.type = $type,
                c.className = $className,
                c.settings = $settings,
                c.lastUpdated = datetime()
            """
            
            session.run(
                query,
                name=component.get('name'),
                type=component_type,
                className=component.get('type'),
                settings=component.get('settings', {})
            )
            
            # Add specific label based on component type
            if 'Service' in component_type:
                session.run(
                    "MATCH (c:Component {name: $name}) SET c:BusinessService",
                    name=component.get('name')
                )
            elif 'Operation' in component_type:
                session.run(
                    "MATCH (c:Component {name: $name}) SET c:BusinessOperation",
                    name=component.get('name')
                )
        
        return len(components)
    
    def _import_routing_rules(self, session, routing_rules_data: Dict) -> int:
        """Import routing rules into Neo4j."""
        rules = routing_rules_data.get('rules', [])
        
        for rule in rules:
            query = """
            MERGE (r:RoutingRule {name: $name})
            SET r.condition = $condition,
                r.actions = $actions,
                r.lastUpdated = datetime()
            """
            
            session.run(
                query,
                name=rule.get('name'),
                condition=rule.get('condition', ''),
                actions=rule.get('actions', [])
            )
        
        return len(rules)
    
    def _create_relationships(self, session, relationships: List[Dict]) -> int:
        """
        Create relationships between components in Neo4j.
        
        Args:
            session: Neo4j session
            relationships: List of relationship dictionaries with 'source', 'target', and 'type' keys
            
        Returns:
            Number of relationships created
        """
        relationships_created = 0
        
        for rel in relationships:
            source = rel['source']
            target = rel['target']
            rel_type = rel.get('type', 'CONNECTED_TO')
            properties = rel.get('properties', {})
            
            # Prepare the query
            query = f"""
            MATCH (source {{name: $source_name}}), (target {{name: $target_name}})
            MERGE (source)-[r:{rel_type}]->(target)
            SET r += $properties,
                r.lastUpdated = datetime()
            RETURN id(r) as id
            """
            
            try:
                result = session.run(
                    query,
                    source_name=source,
                    target_name=target,
                    properties=properties
                )
                
                if result.single():
                    relationships_created += 1
                    logger.debug(f"Created relationship: {source} -[{rel_type}]-> {target}")
                else:
                    logger.warning(f"Failed to create relationship: {source} -> {target}")
                    
            except Exception as e:
                logger.error(f"Error creating relationship {source} -> {target}: {str(e)}", exc_info=True)
        
        return relationships_created
