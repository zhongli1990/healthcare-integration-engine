"""
Messaging module for healthcare integration engine.

This module provides message routing and processing capabilities using Neo4j.
"""

import logging
from .neo4j_client import Neo4jClient
from .message_router import Message, MessageRouter, router as message_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_messaging():
    """Initialize the messaging system with sample data."""
    try:
        logger.info("Initializing messaging system...")
        
        # Create Neo4j client and initialize schema
        neo4j_client = Neo4jClient()
        
        # Initialize schema and create sample data
        neo4j_client.initialize_schema()
        neo4j_client.create_sample_data()
        
        logger.info("Messaging system initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize messaging system: {str(e)}", exc_info=True)
        return False

# Initialize on import
init_messaging()

__all__ = [
    'Message',
    'MessageRouter',
    'router',
    'init_messaging'
]
