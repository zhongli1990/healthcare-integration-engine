"""
Test suite for verifying service connectivity in the integration test environment.

This module contains tests that verify the basic connectivity to all required services
(PostgreSQL, Redis, Neo4j) that the integration tests depend on.
"""
import pytest
import psycopg2
import redis
from neo4j import GraphDatabase

# Test configuration
POSTGRES_CONFIG = {
    'host': 'test-db',
    'database': 'test_healthcare_integration',
    'user': 'postgres',
    'password': 'postgres'
}

REDIS_CONFIG = {
    'host': 'test-redis',
    'port': 6379,
    'db': 0
}

NEO4J_CONFIG = {
    'uri': 'bolt://host.docker.internal:7687',
    'auth': ('neo4j', 'healthcare123')
}

class TestServiceConnectivity:
    """Test cases for service connectivity."""

    def test_postgres_connection(self):
        """Test connection to PostgreSQL database."""
        try:
            conn = psycopg2.connect(**POSTGRES_CONFIG)
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
                result = cur.fetchone()
                assert result[0] == 1, "PostgreSQL query did not return expected result"
            conn.close()
        except Exception as e:
            pytest.fail(f"PostgreSQL connection failed: {str(e)}")

    def test_redis_connection(self):
        """Test connection to Redis."""
        try:
            r = redis.Redis(**REDIS_CONFIG)
            assert r.ping(), "Redis ping failed"
        except Exception as e:
            pytest.fail(f"Redis connection failed: {str(e)}")

    def test_neo4j_connection(self):
        """Test connection to Neo4j database."""
        try:
            with GraphDatabase.driver(NEO4J_CONFIG['uri'], 
                                   auth=NEO4J_CONFIG['auth']) as driver:
                with driver.session() as session:
                    result = session.run('RETURN 1 as result')
                    assert result.single()['result'] == 1, \
                        "Neo4j query did not return expected result"
        except Exception as e:
            pytest.fail(f"Neo4j connection failed: {str(e)}")

    @pytest.mark.integration
    def test_all_services_available(self):
        """Test that all required services are available.
        
        This is a convenience test that runs all connectivity tests.
        """
        self.test_postgres_connection()
        self.test_redis_connection()
        self.test_neo4j_connection()
