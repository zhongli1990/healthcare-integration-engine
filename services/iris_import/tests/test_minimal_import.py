import os
import sys
import json
import logging
from pathlib import Path
from neo4j import GraphDatabase
from app.services.graph_extractor import GraphExtractor
from app.services.import_service import ImportService

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

def test_minimal_production_import():
    """Test parsing and importing a minimal production file."""
    try:
        # Path to the minimal test file
        test_file = Path('/app/samples/MinimalTestProduction.cls')
        if not test_file.exists():
            logger.error(f"Test file not found: {test_file}")
            return False
            
        logger.info(f"=== Starting test with file: {test_file} ===")
        
        # Initialize the extractor
        extractor = GraphExtractor()
        
        # Get Neo4j connection details from environment variables
        neo4j_uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD', 'healthcare123')
        
        logger.info(f"Connecting to Neo4j at {neo4j_uri} as user {neo4j_user}")
        
        try:
            # Initialize the import service with Neo4j connection details
            import_service = ImportService(
                neo4j_uri=neo4j_uri,
                neo4j_user=neo4j_user,
                neo4j_password=neo4j_password
            )
            
            # Test the connection
            with import_service.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                test_result = result.single()[0]
                logger.info(f"Neo4j connection test successful: {test_result}")
                
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            logger.error("Please ensure the Neo4j service is running and accessible")
            logger.error(f"URI: {neo4j_uri}, User: {neo4j_user}")
            return False
        
        # Import the production file directly using import_production
        logger.info("Importing production file...")
        import_result = import_service.import_production(test_file, test_file)
        
        if not import_result or not import_result.get('success', False):
            logger.error(f"Failed to import production: {import_result.get('message', 'Unknown error')}")
            return False
            
        # Get the import statistics
        stats = import_result.get('stats', {})
        logger.info(f"Import completed: {stats.get('nodes_created', 0)} nodes created, "
                   f"{stats.get('relationships_created', 0)} relationships created")
        
        # Get the verification results
        verification = import_result.get('verification', {})
        if not verification.get('success', False):
            logger.warning(f"Verification failed: {verification.get('message', 'Unknown error')}")
        
        # Query and log the imported nodes
        with import_service.driver.session() as session:
            result = session.run("MATCH (n) RETURN n.name as name, labels(n) as labels, properties(n) as props")
            for i, record in enumerate(result, 1):
                logger.info(f"Imported Node {i}: {record['name']} - Labels: {record['labels']}")
                logger.info(f"  Properties: {json.dumps(dict(record['props']), indent=2)}")
        
        created = stats.get('nodes_created', 0)
        failed = stats.get('nodes_failed', 0)
        
        if created > 0 and failed == 0:
            logger.info(f"Successfully imported {created} components")
            # Query Neo4j to verify the import
            with import_service.driver.session() as session:
                result = session.run("MATCH (n) RETURN n.name as name, labels(n) as labels, properties(n) as props")
                for record in result:
                    logger.info(f"Node in Neo4j: {record['name']} - Labels: {record['labels']}")
                    logger.info(f"  Properties: {json.dumps(dict(record['props']), indent=2)}")
            return True
        else:
            logger.error(f"Import completed with {created} created, {failed} failed")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_minimal_production_import()
    sys.exit(0 if success else 1)
