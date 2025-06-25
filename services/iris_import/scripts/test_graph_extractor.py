#!/usr/bin/env python3
"""
Test script for GraphExtractor with sample files.
"""
import os
import sys
import json
import logging
import argparse
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the GraphExtractor
try:
    from app.services.graph_extractor import GraphExtractor
except ImportError:
    # Fallback for local testing
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.services.graph_extractor import GraphExtractor

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test GraphExtractor with sample files')
    parser.add_argument('--production-file', 
                        default='samples/TestProduction.cls',
                        help='Path to Production.cls file')
    parser.add_argument('--routing-rule-file', 
                        default='samples/TestRoutingRule.cls',
                        help='Path to RoutingRule.cls file')
    parser.add_argument('--output', 
                        default=None,
                        help='Output file for the graph data (JSON)')
    return parser.parse_args()

def validate_graph_data(graph_data):
    """Validate the extracted graph data."""
    if not graph_data:
        raise ValueError("No graph data extracted")
    
    nodes = graph_data.get('nodes', [])
    relationships = graph_data.get('relationships', [])
    
    if not nodes:
        raise ValueError("No nodes extracted from the files")
    
    logger.info(f"Extracted {len(nodes)} nodes and {len(relationships)} relationships")
    
    # Log node types
    node_types = {}
    for node in nodes:
        node_type = node.get('type', 'Unknown')
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    logger.info("Node types extracted:")
    for node_type, count in node_types.items():
        logger.info(f"  - {node_type}: {count}")
    
    # Log relationship types
    rel_types = {}
    for rel in relationships:
        rel_type = rel.get('type', 'UNKNOWN')
        rel_types[rel_type] = rel_types.get(rel_type, 0) + 1
    
    logger.info("Relationship types extracted:")
    for rel_type, count in rel_types.items():
        logger.info(f"  - {rel_type}: {count}")
    
    return True

def main():
    """Main function to test GraphExtractor."""
    args = parse_args()
    
    # Resolve file paths
    base_dir = Path(__file__).parent.parent
    production_file = (base_dir / args.production_file).resolve()
    routing_rule_file = (base_dir / args.routing_rule_file).resolve()
    
    logger.info(f"Using production file: {production_file}")
    logger.info(f"Using routing rule file: {routing_rule_file}")
    
    # Check if files exist
    if not production_file.exists():
        logger.error(f"Production file not found: {production_file}")
        return 1
    if not routing_rule_file.exists():
        logger.error(f"Routing rule file not found: {routing_rule_file}")
        return 1
    
    try:
        # Initialize GraphExtractor
        extractor = GraphExtractor()
        
        # Extract graph data
        logger.info("Extracting graph data...")
        graph_data = extractor.extract_from_files(
            str(production_file),
            str(routing_rule_file)
        )
        
        # Validate the extracted data
        logger.info("Validating extracted data...")
        validate_graph_data(graph_data)
        
        # Save output if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(graph_data, f, indent=2, default=str)
            logger.info(f"Graph data saved to: {output_path}")
        
        logger.info("Test completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Error during extraction: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
