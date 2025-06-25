# IRIS Import Documentation

## Overview
The IRIS Import feature allows users to upload InterSystems IRIS production and routing rule files (`.cls` files) to visualize the components and their relationships in a Neo4j graph database.

## Features
- Upload IRIS production and routing rule files
- Parse and extract components, settings, and routing rules
- Visualize the production components and their relationships
- Track import progress in real-time
- Handle large imports asynchronously

## API Endpoints

### 1. Upload Files
```
POST /api/imports/upload
Content-Type: multipart/form-data

Form Data:
- production_file: (required) The IRIS production .cls file
- routing_rule_file: (required) The IRIS routing rule .cls file
```

### 2. Start Import
```
POST /api/imports
Content-Type: application/json

{
  "production_file": "/path/to/production.cls",
  "routing_rule_file": "/path/to/routing_rule.cls",
  "neo4j_uri": "bolt://neo4j:7687",
  "neo4j_user": "neo4j",
  "neo4j_password": "password"
}
```

### 3. Check Import Status
```
GET /api/imports/{import_id}
```

## Data Model

### Nodes
- `Component`: Production components (Business Services, Business Operations, etc.)
  - Properties: name, type, className, settings
- `RoutingRule`: Routing rules and their conditions
  - Properties: name, condition, actions

### Relationships
- `SENDS_TO`: Represents message flow between components
  - Properties: rule (name of the routing rule)

## Setup

### Prerequisites
- Python 3.8+
- Neo4j 4.4+
- Docker (for containerized deployment)

### Installation
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables (see `.env.example`)

## Usage

### Running the Service
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Using the Web Interface
1. Open `http://localhost:8000` in your browser
2. Click on "Import" tab
3. Upload your production and routing rule files
4. Configure Neo4j connection details if needed
5. Click "Start Import"
6. Monitor the import progress
7. View the visualization once complete

### Using the API
1. Upload files using `/api/imports/upload`
2. Start import using `/api/imports` with the file paths
3. Poll `/api/imports/{import_id}` for status

## Error Handling
The API returns appropriate HTTP status codes and error messages in the following format:
```json
{
  "detail": "Error message"
}
```

## Troubleshooting

### Common Issues
1. **File Upload Fails**
   - Ensure files are valid IRIS .cls files
   - Check file permissions

2. **Import Stuck in Progress**
   - Check the service logs for errors
   - Verify Neo4j connection details

3. **Missing Components in Visualization**
   - Verify the production file includes all components
   - Check for parsing errors in the logs

## Development

### Adding New Parsers
1. Create a new parser in `app/parsers/`
2. Implement the required parsing logic
3. Update the import service to use the new parser

### Testing
Run the test suite:
```bash
pytest tests/
```

## License
[Your License Here]
