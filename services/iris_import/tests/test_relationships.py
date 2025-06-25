import os
import sys
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, basic_auth
from datetime import datetime

# Configure logging to show all levels and output to console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Get logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class RelationshipExtractor:
    """Extract relationships from IRIS production files."""
    
    def __init__(self):
        # Compile regex patterns for parsing
        self.patterns = {
            'item': re.compile(r'<Item\s+Name="([^"]+)"[^>]*>([\s\S]*?)</Item>', re.IGNORECASE),
            'setting': re.compile(r'<Setting\s+Target="([^"]+)"\s+Name="([^"]+)"[^>]*>([^<]+)</Setting>', re.IGNORECASE),
            'rule': re.compile(r'<Rule\s+Name="([^"]+)"[^>]*>([\s\S]*?)</Rule>', re.IGNORECASE),
            'send': re.compile(r'<send[^>]+target=["\']([^"\']+)["\']', re.IGNORECASE),
            'target_config': re.compile(r'<Setting\s+Target="Host"\s+Name="TargetConfigNames"[^>]*>([^<]+)</Setting>', re.IGNORECASE),
        }
    
    def extract_relationships(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract relationships from production file content.
        
        Args:
            content: The content of the production file
            
        Returns:
            List of relationship dictionaries with 'source', 'target', and 'type' keys
        """
        logger.info("Starting relationship extraction...")
        relationships = []
        
        # Track components and their settings
        components = {}
        
        # First pass: Extract all components and their settings
        for item_match in self.patterns['item'].finditer(content):
            item_name = item_match.group(1)
            item_content = item_match.group(2)
            
            # Extract component settings
            settings = {}
            for setting_match in self.patterns['setting'].finditer(item_content):
                target = setting_match.group(1)
                name = setting_match.group(2).lower()  # Convert to lowercase for case-insensitive comparison
                value = setting_match.group(3).strip()
                
                if target.lower() == 'host':  # Only process host settings
                    settings[name] = value
            
            # Also look for TargetConfigNames setting
            target_config_match = self.patterns['target_config'].search(item_content)
            if target_config_match:
                settings['targets'] = [t.strip() for t in target_config_match.group(1).split(',')]
            
            components[item_name] = settings
        
        # Extract routing rules and their relationships
        for comp_name, settings in components.items():
            # Check if this is a router with a BusinessRuleName
            if 'businessrulename' in settings:
                rule_name = settings['businessrulename']
                
                # Find all components that have this rule as their target
                for target_comp, target_settings in components.items():
                    if 'targets' in target_settings and comp_name in target_settings['targets']:
                        relationships.append({
                            'source': comp_name,
                            'target': target_comp,
                            'type': 'ROUTES_TO',
                            'properties': {
                                'rule': rule_name,
                                'source_type': 'router',
                                'target_type': target_settings.get('classname', 'unknown').split('.')[-1].lower()
                            }
                        })
                        logger.debug(f"Found routing relationship: {comp_name} -> {target_comp} (rule: {rule_name})")
            
            # Check for direct target configurations
            if 'targets' in settings:
                for target in settings['targets']:
                    if target in components:  # Only add if target exists
                        relationships.append({
                            'source': comp_name,
                            'target': target,
                            'type': 'SENDS_TO',
                            'properties': {
                                'source_type': 'service',
                                'target_type': components[target].get('classname', 'unknown').split('.')[-1].lower()
                            }
                        })
                        logger.debug(f"Found direct relationship: {comp_name} -> {target}")
        
        logger.info(f"Extracted {len(relationships)} relationships")
        return relationships

class Neo4jImporter:
    """Handles importing relationships into Neo4j."""
    
    def __init__(self, uri: str, user: str, password: str):
        """Initialize the Neo4j importer."""
        self.driver = GraphDatabase.driver(uri, auth=basic_auth(user, password))
    
    def close(self):
        """Close the Neo4j driver."""
        self.driver.close()
    
    def import_relationships(self, relationships: List[Dict]) -> int:
        """
        Import relationships into Neo4j.
        
        Args:
            relationships: List of relationship dictionaries
            
        Returns:
            Number of relationships successfully imported
        """
        imported = 0
        
        with self.driver.session() as session:
            # Clear existing relationships (but keep nodes)
            session.run("MATCH ()-[r]->() DELETE r")
            
            for rel in relationships:
                try:
                    source = rel['source']
                    target = rel['target']
                    rel_type = rel.get('type', 'CONNECTED_TO')
                    properties = rel.get('properties', {})
                    
                    # Add timestamp
                    properties['imported_at'] = datetime.utcnow().isoformat()
                    
                    # Create or update nodes and relationship
                    query = f"""
                    MERGE (source:Component {{name: $source_name}})
                    MERGE (target:Component {{name: $target_name}})
                    MERGE (source)-[r:{rel_type}]->(target)
                    SET r += $properties
                    RETURN id(r) as id
                    """
                    
                    result = session.run(
                        query,
                        source_name=source,
                        target_name=target,
                        properties=properties
                    )
                    
                    if result.single():
                        imported += 1
                        logger.debug(f"Imported relationship: {source} -[{rel_type}]-> {target}")
                    else:
                        logger.warning(f"Failed to import relationship: {source} -> {target}")
                        
                except Exception as e:
                    logger.error(f"Error importing relationship {rel}: {str(e)}")
        
        return imported

def main():
    """Main function to run relationship extraction and import."""
    try:
        # Path to the production file
        production_file = Path('/app/samples/BHR_ADT_Production.cls')
        
        if not production_file.exists():
            logger.error(f"Production file not found: {production_file}")
            return False
            
        logger.info(f"=== Starting relationship extraction ===")
        logger.info(f"Production file: {production_file}")
        
        # Read the file content
        with open(production_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract relationships
        extractor = RelationshipExtractor()
        relationships = extractor.extract_relationships(content)
        
        # Print summary
        logger.info(f"\n=== Relationship Extraction Results ===")
        logger.info(f"Total relationships found: {len(relationships)}")
        
        if relationships:
            logger.info("\nSample relationships (first 10):")
            for i, rel in enumerate(relationships[:10], 1):
                logger.info(f"{i}. {rel['source']} -> {rel['target']} ({rel['type']})")
                if 'properties' in rel and rel['properties']:
                    logger.info(f"   Properties: {rel['properties']}")
        
        # Import to Neo4j
        logger.info("\n=== Importing to Neo4j ===")
        neo4j_uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
        
        importer = Neo4jImporter(neo4j_uri, neo4j_user, neo4j_password)
        try:
            imported_count = importer.import_relationships(relationships)
            logger.info(f"Successfully imported {imported_count}/{len(relationships)} relationships to Neo4j")
            
            # Verify import
            with importer.driver.session() as session:
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                count = result.single()["count"]
                logger.info(f"Total relationships in Neo4j: {count}")
                
                # Get sample relationships from Neo4j
                result = session.run("""
                    MATCH (s)-[r]->(t)
                    RETURN s.name as source, type(r) as type, t.name as target
                    LIMIT 5
                """)
                
                logger.info("\nSample relationships from Neo4j:")
                for i, record in enumerate(result, 1):
                    logger.info(f"{i}. {record['source']} -[{record['type']}]-> {record['target']}")
            
            return imported_count > 0
            
        finally:
            importer.close()
        
    except Exception as e:
        logger.error(f"Error during relationship extraction/import: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
