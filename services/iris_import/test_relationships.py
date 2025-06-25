import os
import sys
from pathlib import Path
from app.services.graph_extractor import GraphExtractor
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_relationship_extraction():
    """Test relationship extraction from production and routing rule files."""
    try:
        # Get the directory of this script
        script_dir = Path(__file__).parent
        
        # Define file paths - using the same file for both production and routing rules
        # as BHR_ADT_Production contains both component definitions and routing rules
        # Using absolute paths that work in the container
        production_file = Path("/app/samples/BHR_ADT_Production.cls")
        routing_rule_file = Path("/app/samples/BHR_ADT_Production.cls")
        
        # Convert to absolute paths
        production_file = production_file.resolve()
        routing_rule_file = routing_rule_file.resolve()
        
        logger.info(f"Testing with production file: {production_file}")
        logger.info(f"Testing with routing rule file: {routing_rule_file}")
        
        # Initialize the graph extractor
        extractor = GraphExtractor()
        
        # Extract graph data
        result = extractor.extract_from_files(str(production_file), str(routing_rule_file))
        
        # Print summary
        logger.info(f"Extracted {len(result['nodes'])} nodes and {len(result['relationships'])} relationships")
        
        # Print nodes
        logger.info("\nNodes:")
        for node in result['nodes'][:5]:  # Show first 5 nodes
            logger.info(f"  - {node['name']} ({node.get('type', 'Unknown')})")
        if len(result['nodes']) > 5:
            logger.info(f"  ... and {len(result['nodes']) - 5} more")
        
        # Print relationships
        if result['relationships']:
            logger.info("\nRelationships:")
            for rel in result['relationships']:
                logger.info(f"  - {rel['source']} --[{rel['type']}]--> {rel['target']} (Rule: {rel['properties'].get('rule_name', 'unnamed')})")
        else:
            logger.warning("No relationships were extracted!")
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing relationship extraction: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    test_relationship_extraction()
