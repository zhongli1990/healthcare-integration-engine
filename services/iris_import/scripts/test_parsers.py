"""
Test script for IRIS production and routing rule parsers.
"""
import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('parser_test.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main function to test the parsers."""
    # Get the directory where the sample files are located
    sample_dir = Path(__file__).parent.parent / 'sample_data'
    
    # Define the sample files
    production_file = sample_dir / 'BHR_ADT_Production.cls'
    routing_rule_file = sample_dir / 'BHR_ADT_Production.cls'  # Same file for now
    
    # Check if the files exist
    if not production_file.exists():
        logger.error(f"Production file not found: {production_file}")
        return
    
    if not routing_rule_file.exists():
        logger.error(f"Routing rule file not found: {routing_rule_file}")
        return
    
    # Import the parsers
    from app.parsers.production_parser import parse_production_file
    from app.parsers.routing_rule_parser import parse_routing_rule_file
    
    # Test the production parser
    logger.info("=" * 50)
    logger.info("TESTING PRODUCTION PARSER")
    logger.info("=" * 50)
    
    try:
        production_data = parse_production_file(str(production_file))
        logger.info("\nParsed Production Data:")
        logger.info(f"- Name: {production_data['name']}")
        logger.info(f"- Description: {production_data['description']}")
        logger.info(f"- Components found: {len(production_data['components'])}")
        
        for i, component in enumerate(production_data['components'], 1):
            logger.info(f"\nComponent {i}:")
            logger.info(f"  Name: {component['name']}")
            logger.info(f"  Type: {component['type']}")
            logger.info(f"  Settings ({len(component['settings'])}):")
            for key, value in component['settings'].items():
                logger.info(f"    {key} = {value}")
        
        # Save the parsed data to a file
        import json
        with open('parsed_production.json', 'w') as f:
            json.dump(production_data, f, indent=2)
        logger.info("\nSaved parsed production data to 'parsed_production.json'")
        
    except Exception as e:
        logger.error(f"Error parsing production file: {str(e)}", exc_info=True)
    
    # Test the routing rule parser
    logger.info("\n" + "=" * 50)
    logger.info("TESTING ROUTING RULE PARSER")
    logger.info("=" * 50)
    
    try:
        routing_rule_data = parse_routing_rule_file(str(routing_rule_file))
        logger.info("\nParsed Routing Rule Data:")
        logger.info(f"- Name: {routing_rule_data['name']}")
        logger.info(f"- Description: {routing_rule_data['description']}")
        logger.info(f"- Rules found: {len(routing_rule_data['rules'])}")
        
        for i, rule in enumerate(routing_rule_data['rules'], 1):
            logger.info(f"\nRule {i}:")
            logger.info(f"  Name: {rule['name']}")
            logger.info(f"  Condition: {rule['condition']}")
            logger.info(f"  Actions ({len(rule['actions'])}):")
            for j, action in enumerate(rule['actions'], 1):
                logger.info(f"    {j}. {action}")
        
        # Save the parsed data to a file
        with open('parsed_routing_rules.json', 'w') as f:
            json.dump(routing_rule_data, f, indent=2)
        logger.info("\nSaved parsed routing rule data to 'parsed_routing_rules.json'")
        
    except Exception as e:
        logger.error(f"Error parsing routing rule file: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
