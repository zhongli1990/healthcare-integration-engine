from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging
from ..services.neo4j_service import neo4j_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = {}

class GraphLink(BaseModel):
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = {}

class GraphData(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]

@router.get("/graph", response_model=GraphData)
async def get_production_graph():
    """
    Get the production graph data for visualization from Neo4j
    """
    try:
        # Get graph data from Neo4j
        graph_data = neo4j_service.get_production_graph()
        
        # Transform nodes to match GraphNode model
        nodes = [
            GraphNode(
                id=node.get("id", ""),
                label=node.get("label", ""),
                type=node.get("type", ""),
                properties=node.get("properties", {})
            )
            for node in graph_data.get("nodes", [])
        ]
        
        # Transform links to match GraphLink model
        links = [
            GraphLink(
                source=link.get("source", ""),
                target=link.get("target", ""),
                type=link.get("type", ""),
                properties=link.get("properties", {})
            )
            for link in graph_data.get("links", [])
            if link.get("source") and link.get("target")
        ]
        
        return GraphData(nodes=nodes, links=links)
        
    except Exception as e:
        logger.error(f"Error getting production graph: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving production graph: {str(e)}"
        )

@router.get("/components", response_model=Dict[str, Any])
async def list_components():
    """
    List all components and their relationships from Neo4j
    Returns a dictionary with 'components' and 'relationships' keys
    """
    try:
        components = neo4j_service.get_components()
        relationships = neo4j_service.get_relationships()
        return {
            "components": components,
            "relationships": relationships
        }
    except Exception as e:
        logger.error(f"Error listing components and relationships: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving components and relationships: {str(e)}"
        )

@router.get("/relationships", response_model=List[Dict[str, Any]])
async def list_relationships():
    """
    List all relationships in the production from Neo4j
    """
    try:
        relationships = neo4j_service.get_relationships()
        return relationships
    except Exception as e:
        logger.error(f"Error listing relationships: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving relationships: {str(e)}"
        )

@router.get("/routes", response_model=List[Dict[str, Any]])
async def list_routes():
    """
    List all message routes in the production from Neo4j
    """
    try:
        routes = neo4j_service.get_routes()
        return routes
    except Exception as e:
        logger.error(f"Error listing routes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving routes: {str(e)}"
        )
