from neo4j import GraphDatabase, basic_auth
from typing import Dict, List, Any, Optional
import os
from contextlib import contextmanager

class Neo4jClient:
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "healthcare123")
        self._driver = None

    def connect(self):
        """Establish a connection to the Neo4j database."""
        if not self._driver:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=basic_auth(self.user, self.password)
            )
        return self._driver

    def close(self):
        """Close the Neo4j driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    @contextmanager
    def session(self, **kwargs):
        """Provide a transactional scope around a series of operations."""
        driver = self.connect()
        session = driver.session(**kwargs)
        try:
            yield session
        finally:
            session.close()

    def execute_query(self, query: str, parameters: Dict = None, **kwargs) -> List[Dict[str, Any]]:
        """Execute a read query and return the results."""
        with self.session() as session:
            result = session.run(query, parameters or {}, **kwargs)
            return [dict(record) for record in result]

    def execute_write(self, query: str, parameters: Dict = None, **kwargs) -> Any:
        """Execute a write query and return the result summary."""
        with self.session() as session:
            result = session.run(query, parameters or {}, **kwargs)
            return result.consume()

    def initialize_schema(self):
        """Initialize the Neo4j schema with constraints and indexes."""
        constraints = [
            "CREATE CONSTRAINT system_id IF NOT EXISTS FOR (s:System) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT message_type_id IF NOT EXISTS FOR (m:MessageType) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT service_id IF NOT EXISTS FOR (s:BusinessService) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT operation_id IF NOT EXISTS FOR (o:BusinessOperation) REQUIRE o.id IS UNIQUE"
        ]
        
        for constraint in constraints:
            self.execute_write(constraint)

    def create_sample_data(self):
        """Create sample data for testing and development."""
        # List of individual Cypher statements to execute with MERGE for idempotency
        statements = [
            # Create or get sample systems
            """
            MERGE (ehr:System {id: 'ehr1'})
            ON CREATE SET ehr.name = 'EPIC', ehr.type = 'EHR', ehr.status = 'active'
            """,
            """
            MERGE (lis:System {id: 'lis1'})
            ON CREATE SET lis.name = 'LabSystem', lis.type = 'LIS', lis.status = 'active'
            """,
            
            # Create or get message types
            """
            MERGE (adt:MessageType {id: 'adt_a01'})
            ON CREATE SET adt.name = 'ADT_A01', adt.standard = 'HL7v2', adt.version = '2.5'
            """,
            """
            MERGE (oru:MessageType {id: 'oru_r01'})
            ON CREATE SET oru.name = 'ORU_R01', oru.standard = 'HL7v2', oru.version = '2.5'
            """,
            
            # Create or get services and operations
            """
            MERGE (svcHL7:BusinessService {id: 'svc_hl7'})
            ON CREATE SET svcHL7.name = 'HL7 Listener', svcHL7.type = 'HL7'
            """,
            """
            MERGE (opRest:BusinessOperation {id: 'op_rest'})
            ON CREATE SET opRest.name = 'REST Forwarder', opRest.type = 'REST'
            """,
            
            # Create relationships only if they don't exist
            """
            MATCH (ehr:System {id: 'ehr1'}), (svc:BusinessService {id: 'svc_hl7'})
            MERGE (ehr)-[r:PROVIDES]->(svc)
            """,
            
            """
            MATCH (svc:BusinessService {id: 'svc_hl7'}), (adt:MessageType {id: 'adt_a01'})
            MERGE (svc)-[r:HANDLES]->(adt)
            """,
            
            # Create or get routing rule
            """
            MERGE (rule1:RoutingRule {id: 'rule1'})
            ON CREATE SET 
                rule1.name = 'Route ADT to EHR',
                rule1.condition = 'messageType == \"ADT_A01\"',
                rule1.priority = 1
            """,
            
            # Create route relationship if it doesn't exist
            """
            MATCH (svc:BusinessService {id: 'svc_hl7'}), 
                  (op:BusinessOperation {id: 'op_rest'}),
                  (rule:RoutingRule {id: 'rule1'})
            MERGE (svc)-[r:ROUTES_TO]->(op)
            ON CREATE SET r.rule = rule.id
            """
        ]
        
        # Execute each statement individually
        for statement in statements:
            try:
                self.execute_write(statement.strip())
            except Exception as e:
                print(f"Error executing statement: {statement}")
                print(f"Error details: {str(e)}")
                raise
