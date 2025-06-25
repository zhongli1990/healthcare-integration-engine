from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Neo4jService:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "healthcare123")
        self.driver = None

    def connect(self):
        """Establish a connection to the Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            print(f"Error connecting to Neo4j: {e}")
            return False

    def close(self):
        """Close the Neo4j driver connection"""
        if self.driver:
            self.driver.close()

    def execute_query(self, query: str, parameters: Dict = None) -> List[Dict[str, Any]]:
        """Execute a read query and return the results"""
        if not self.driver:
            self.connect()
        
        with self.driver.session() as session:
            try:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
            except Exception as e:
                print(f"Error executing query: {e}")
                return []

    def get_production_graph(self) -> Dict[str, List[Dict]]:
        """
        Get the production graph data for visualization
        Returns a dictionary with 'nodes' and 'links' keys
        """
        try:
            # Ensure we have a connection
            if not self.driver:
                self.connect()
                if not self.driver:
                    print("Failed to connect to Neo4j")
                    return {"nodes": [], "links": []}
            
            # First, get all nodes
            nodes_query = """
            MATCH (n)
            RETURN {
                id: elementId(n),
                label: n.name,
                type: n.type,
                properties: properties(n)
            } as node
            """
            
            nodes_result = self.execute_query(nodes_query)
            nodes = [r["node"] for r in nodes_result] if nodes_result else []
            
            # Then get all relationships
            links_query = """
            MATCH (source)-[r]->(target)
            RETURN {
                source: elementId(source),
                target: elementId(target),
                type: type(r),
                properties: properties(r)
            } as link
            """
            
            links_result = self.execute_query(links_query)
            links = [r["link"] for r in links_result] if links_result else []
            
            print(f"Retrieved {len(nodes)} nodes and {len(links)} links from Neo4j")
            return {"nodes": nodes, "links": links}
            
        except Exception as e:
            print(f"Error in get_production_graph: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"nodes": [], "links": []}

    def get_components(self) -> List[Dict[str, Any]]:
        """Get a list of all components in the production"""
        try:
            query = """
            MATCH (n)
            RETURN {
                id: elementId(n),
                name: n.name,
                type: n.type,
                className: n.className,
                properties: properties(n),
                status: 'Active'
            } as component
            ORDER BY n.name
            """
            results = self.execute_query(query)
            print(f"Retrieved {len(results)} components from Neo4j")
            return [r["component"] for r in results]
        except Exception as e:
            print(f"Error in get_components: {str(e)}")
            return []

    def get_relationships(self) -> List[Dict[str, Any]]:
        """
        Get all relationships with their properties
        Returns a list of relationship objects with source, target, type, and properties
        """
        try:
            query = """
            MATCH (source)-[r]->(target)
            RETURN {
                id: elementId(r),
                source: {
                    id: elementId(source),
                    name: source.name,
                    type: source.type
                },
                target: {
                    id: elementId(target),
                    name: target.name,
                    type: target.type
                },
                type: type(r),
                properties: properties(r)
            } as relationship
            ORDER BY type(r), source.name, target.name
            """
            results = self.execute_query(query)
            print(f"Retrieved {len(results)} relationships from Neo4j")
            return [r["relationship"] for r in results]
        except Exception as e:
            print(f"Error in get_relationships: {str(e)}")
            return []

    def get_routes(self) -> List[Dict[str, str]]:
        """Get a list of all message routes in the production"""
        return self.get_relationships()

# Create a singleton instance
neo4j_service = Neo4jService()
