from fastapi import FastAPI
from .services.neo4j_service import neo4j_service

app = FastAPI()

# Initialize Neo4j connection when the app starts
@app.on_event("startup")
async def startup_event():
    print("Initializing Neo4j connection...")
    if not neo4j_service.connect():
        print("Failed to connect to Neo4j. Please check your connection settings.")
    else:
        print("Successfully connected to Neo4j")

# Close Neo4j connection when the app shuts down
@app.on_event("shutdown")
def shutdown_event():
    print("Closing Neo4j connection...")
    if hasattr(neo4j_service, 'close'):
        neo4j_service.close()
    print("Neo4j connection closed")
