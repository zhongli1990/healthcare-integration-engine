[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/def21561-5d36-4457-b4a8-ba819ac26918)

<a href="https://glama.ai/mcp/servers/@caretdev/mcp-server-iris">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@caretdev/mcp-server-iris/badge" />
</a>

[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/caretdev-mcp-server-iris-badge.png)](https://mseep.ai/app/caretdev-mcp-server-iris)

# MCP Server for InterSystems IRIS

A [Model Context Protocol](https://modelcontextprotocol.io/introduction) server for InterSystems IRIS database interaction and automation.

## Overview

This project provides an MCP server that enables natural language interaction with InterSystems IRIS databases. It allows you to:

- Execute SQL queries through natural language
- Manage IRIS interoperability productions
- Interact with IRIS programmatically through MCP

## Prerequisites

- Docker and Docker Compose
- Python 3.8+
- InterSystems IRIS (included in the Docker setup)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mcp-server-isc-iris.git
   cd mcp-server-isc-iris
   ```

2. Start the services:
   ```bash
   docker-compose up -d
   ```

3. Run the example client:
   ```bash
   docker exec -it mcp-server-iris python3 /app/example.py
   ```

## Configuration

The server can be configured using environment variables in the `docker-compose.yml` file:

```yaml
environment:
  - IRIS_HOSTNAME=database
  - IRIS_PORT=1972
  - IRIS_NAMESPACE=USER
  - IRIS_USERNAME=_SYSTEM
  - IRIS_PASSWORD=password
  - LOG_LEVEL=INFO
```

## Usage

### Example Client

The `example.py` script demonstrates how to connect to the MCP server and execute SQL queries:

```python
from mcp import ClientSession

async def main():
    async with ClientSession() as session:
        # List available tools
        tools = await session.list_tools()
        print("Available tools:", [tool.name for tool in tools])
        
        # Execute an SQL query
        result = await session.call_tool("execute_sql", {"query": "SELECT * FROM Sample.Person"})
        print("Query result:", result)
```

### Available Tools

- `execute_sql`: Execute SQL queries on the IRIS database
- `interoperability_production_create`: Create a new interoperability production
- `interoperability_production_start`: Start a production
- `interoperability_production_stop`: Stop a production
- `interoperability_production_status`: Get production status
- `interoperability_production_logs`: View production logs
- `interoperability_production_queues`: View production queues

## Development

### Building the Docker Image

```bash
docker-compose build
```

### Running Tests

```bash
docker-compose run --rm mcp-server-iris python -m pytest
```

## Security Note

For production use, please ensure to:

1. Change the default credentials
2. Use environment variables or a secrets manager for sensitive information
3. Enable proper authentication and authorization

## License

MIT

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
