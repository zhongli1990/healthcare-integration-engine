"""
Script to test importing the full BHR_ADT_Production.cls file into Neo4j.
"""
import os
import sys
import logging
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent / 'app'))

from services.import_service import ImportService
from services.graph_extractor import GraphExtractor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_full_production_import():
    """Test importing the full BHR_ADT_Production.cls file."""
    try:
        # Set up paths
        samples_dir = Path('/app/samples')
        production_file = samples_dir / 'BHR_ADT_Production.cls'
        
        if not production_file.exists():
            logger.error(f"Production file not found: {production_file}")
            return False
            
        logger.info(f"Testing import of production file: {production_file}")
        
        # Set up the import service
        neo4j_uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD', 'healthcare123')
        
        # Clear existing data
        import_service = ImportService(neo4j_uri, neo4j_user, neo4j_password)
        
        try:
            # Import the production
            logger.info("Starting import...")
            result = import_service.import_production(
                production_file=str(production_file),
                routing_rule_file=None  # Not using routing rules for now
            )
            
            logger.info("Import completed. Results:")
            logger.info(f"Success: {result.get('success')}")
            logger.info(f"Message: {result.get('message')}")
            
            if 'statistics' in result:
                stats = result['statistics']
                logger.info("Statistics:")
                logger.info(f"  Nodes created: {stats.get('nodes_created')}")
                logger.info(f"  Nodes failed: {stats.get('nodes_failed')}")
                logger.info(f"  Relationships created: {stats.get('relationships_created')}")
                logger.info(f"  Relationships failed: {stats.get('relationships_failed')}")
            
            if 'verification' in result:
                verif = result['verification']
                logger.info("Verification:")
                logger.info(f"  Nodes imported: {verif.get('nodes_imported')}")
                logger.info(f"  Relationships imported: {verif.get('relationships_imported')}")
                
                if 'type_distribution' in verif:
                    logger.info("  Type distribution:")
                    for item in verif['type_distribution']:
                        logger.info(f"    {item['type']}: {item['count']}")
            
            return result.get('success', False)
            
        except Exception as e:
            logger.error(f"Error during import: {str(e)}", exc_info=True)
            return False
            
        finally:
            import_service.close()
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_full_production_import()
    sys.exit(0 if success else 1)
