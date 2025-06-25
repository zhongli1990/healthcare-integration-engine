#!/bin/bash

# Set default values
NEO4J_URI=${NEO4J_URI:-"bolt://neo4j:7687"}
NEO4J_USER=${NEO4J_USER:-"neo4j"}
NEO4J_PASSWORD=${NEO4J_PASSWORD:-"healthcare123"}

# Run the import script
cd /app/backend
python -m scripts.test_iris_import --neo4j-uri "$NEO4J_URI" --neo4j-user "$NEO4J_USER" --neo4j-password "$NEO4J_PASSWORD"
