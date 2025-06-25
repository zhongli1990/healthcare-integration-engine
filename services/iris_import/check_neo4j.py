#!/usr/bin/env python3
"""
Script to check the contents of the Neo4j database after import.
"""
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

def print_header(text):
    print(f"\n{'='*50}")
    print(f"{text.upper()}")
    print(f"{'='*50}")

def check_neo4j():
    # Load environment variables
    load_dotenv()
    
    # Get Neo4j connection details
    uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'healthcare123')
    
    try:
        # Connect to Neo4j
        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            print_header("connected to neo4j")
            
            with driver.session() as session:
                # Check node counts
                print_header("node counts")
                result = session.run("""
                    MATCH (n)
                    RETURN count(n) as total_nodes
                """)
                print(f"Total nodes: {result.single()['total_nodes']}")
                
                # Check node labels
                print_header("node labels")
                result = session.run("""
                    MATCH (n)
                    RETURN DISTINCT labels(n) as labels, count(*) as count
                    ORDER BY count DESC
                """)
                for record in result:
                    print(f"Labels: {record['labels']}: {record['count']} nodes")
                
                # Get sample nodes
                print_header("sample nodes")
                result = session.run("""
                    MATCH (n)
                    RETURN n.name as name, labels(n) as labels, properties(n) as props
                    LIMIT 5
                """)
                for i, record in enumerate(result, 1):
                    print(f"\nNode {i}:")
                    print(f"  Name: {record['name']}")
                    print(f"  Labels: {record['labels']}")
                    print("  Properties:")
                    for key, value in record['props'].items():
                        print(f"    {key}: {value}")
                
                # Check relationships
                print_header("relationship types")
                result = session.run("""
                    MATCH ()-[r]->()
                    RETURN DISTINCT type(r) as rel_type, count(*) as count
                    ORDER BY count DESC
                """)
                for record in result:
                    print(f"{record['rel_type']}: {record['count']} relationships")
                
                # Check relationship details
                print_header("sample relationships")
                result = session.run("""
                    MATCH (a)-[r]->(b)
                    RETURN a.name as source, type(r) as rel_type, b.name as target
                    LIMIT 5
                """)
                for record in result:
                    print(f"{record['source']} -[{record['rel_type']}]-> {record['target']}")
                
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    check_neo4j()
