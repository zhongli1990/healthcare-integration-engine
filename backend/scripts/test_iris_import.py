#!/usr/bin/env python3
"""Test script for IRIS production parser and Neo4j importer."""

import os
import sys
import json
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.iris_parser import (
    ProductionParser,
    RoutingRuleParser,
    Neo4jImporter
)

def read_file(file_path: str) -> str:
    """Read file content."""
    with open(file_path, 'r') as f:
        return f.read()

def parse_args():
    parser = argparse.ArgumentParser(description='Import IRIS production data into Neo4j')
    parser.add_argument('--neo4j-uri', default=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
                        help='Neo4j connection URI (default: bolt://localhost:7687)')
    parser.add_argument('--neo4j-user', default=os.getenv('NEO4J_USER', 'neo4j'),
                        help='Neo4j username (default: neo4j)')
    parser.add_argument('--neo4j-password', default=os.getenv('NEO4J_PASSWORD', 'healthcare123'),
                        help='Neo4j password (default: healthcare123)')
    parser.add_argument('--production-file', default='/app/tests/iris_import/Production.cls',
                        help='Path to Production.cls file')
    parser.add_argument('--routing-rule-file', default='/app/tests/iris_import/RoutingRule.cls',
                        help='Path to RoutingRule.cls file')
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Paths to sample files
    production_file = Path(args.production_file)
    routing_rule_file = Path(args.routing_rule_file)
    
    if not production_file.exists() or not routing_rule_file.exists():
        print(f"Error: Sample files not found. Looking for:")
        print(f"- Production file: {production_file}")
        print(f"- Routing rule file: {routing_rule_file}")
        if production_file.parent.exists():
            print(f"Files in {production_file.parent}:", list(production_file.parent.glob('*')))
        sys.exit(1)
    
    # Read files
    print(f"Reading production file: {production_file}")
    production_content = read_file(production_file)
    
    print(f"Reading routing rule file: {routing_rule_file}")
    routing_rule_content = read_file(routing_rule_file)
    
    # Parse production
    print("\nParsing production...")
    prod_parser = ProductionParser()
    production = prod_parser.parse_production(production_content)
    
    # Parse routing rule
    print("Parsing routing rule...")
    rule_parser = RoutingRuleParser()
    routing_rule = rule_parser.parse_routing_rule(routing_rule_content)
    
    if routing_rule:
        production.routing_rules.append(routing_rule)
    
    # Print parsed data
    print("\nParsed Production:")
    print(f"- Name: {production.name}")
    print(f"- Description: {production.description}")
    print(f"- Components: {len(production.components)}")
    print(f"- Routing Rules: {len(production.routing_rules)}")
    
    print("\nSample Component:")
    if production.components:
        comp = production.components[0]
        print(f"  - Name: {comp.name}")
        print(f"  - Type: {comp.type}")
        print(f"  - Class: {comp.class_name}")
    
    print("\nSample Routing Rule:")
    if production.routing_rules:
        rule = production.routing_rules[0]
        print(f"  - Name: {rule.name}")
        print(f"  - Conditions: {len(rule.conditions)}")
        print(f"  - Actions: {len(rule.actions)}")
    
    # Import to Neo4j
    print("\nImporting to Neo4j...")
    print(f"Connecting to Neo4j at {args.neo4j_uri} as user {args.neo4j_user}")
    
    try:
        importer = Neo4jImporter(
            uri=args.neo4j_uri,
            user=args.neo4j_user,
            password=args.neo4j_password
        )
        importer.connect()
        
        result = importer.import_production(production)
        
        print("\nImport Results:")
        print(f"- Production: {result['production']['name'] if result['production'] else 'Failed'}")
        print(f"- Components imported: {result['components']}")
        print(f"- Routing rules imported: {result['routing_rules']}")
        print(f"- Relationships created: {result['relationships']}")
        
        print("\nImport completed successfully!")
        
    except Exception as e:
        print(f"\nError importing to Neo4j: {str(e)}")
        print("Make sure Neo4j is running and the connection details are correct.")
    finally:
        if 'importer' in locals():
            importer.close()

if __name__ == "__main__":
    main()
