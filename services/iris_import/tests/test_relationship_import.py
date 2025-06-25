"""
Test script for verifying relationship import functionality.
"""
import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def test_relationship_import():
    """Test relationship import functionality."""
    from app.services.import_service import ImportService
    from app.services.graph_extractor import GraphExtractor
    from test_relationships import RelationshipExtractor
    
    # Get the path to the test production file
    current_dir = Path(__file__).parent
    sample_dir = current_dir.parent.parent / 'samples'
    production_file = sample_dir / 'BHR_ADT_Production.cls'
    
    if not production_file.exists():
        logger.error(f"Production file not found: {production_file}")
        return False
    
    # Initialize services
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
    
    import_service = ImportService(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        # 1. Import the production file
        logger.info(f"Importing production file: {production_file}")
        result = import_service.import_production(str(production_file))
        
        if not result.get('success'):
            logger.error(f"Failed to import production: {result.get('message')}")
            return False
        
        logger.info("Successfully imported production file")
        
        # 2. Extract relationships using RelationshipExtractor
        logger.info("Extracting relationships...")
        with open(production_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        rel_extractor = RelationshipExtractor()
        relationships = rel_extractor.extract_relationships(content)
        
        if not relationships:
            logger.error("No relationships extracted")
            return False
        
        logger.info(f"Extracted {len(relationships)} relationships")
        
        # 3. Import relationships into Neo4j
        logger.info("Importing relationships into Neo4j...")
        with import_service.driver.session() as session:
            # Clear existing relationships
            session.run("MATCH ()-[r]->() DELETE r")
            
            # Import new relationships
            relationships_created = 0
            for rel in relationships:
                source = rel['source']
                target = rel['target']
                rel_type = rel.get('type', 'CONNECTED_TO')
                properties = rel.get('properties', {})
                
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
        
        logger.info(f"Successfully imported {relationships_created} relationships")
        
        # 4. Verify the import
        logger.info("Verifying import...")
        with import_service.driver.session() as session:
            # Count relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            
            # Get a sample of relationships
            result = session.run("""
                MATCH (source)-[r]->(target)
                RETURN 
                    source.name as source, 
                    type(r) as type, 
                    target.name as target
                LIMIT 10
            """)
            
            logger.info(f"Found {rel_count} relationships in the database")
            logger.info("Sample relationships:")
            for record in result:
                logger.info(f"  - {record['source']} -[{record['type']}]-> {record['target']}")
            
            if rel_count == 0:
                logger.error("No relationships found in the database")
                return False
            
            return True
                
    except Exception as e:
        logger.error(f"Error during test: {str(e)}", exc_info=True)
        return False
    finally:
        import_service.close()

if __name__ == "__main__":
    success = test_relationship_import()
    sys.exit(0 if success else 1)
