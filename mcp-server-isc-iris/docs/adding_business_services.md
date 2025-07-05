# Adding Business Services to IRIS Production

This document provides a detailed guide on how to add business services to an InterSystems IRIS production using the MCP server tooling.

## Table of Contents
- [Overview](#overview)
- [Implementation Steps](#implementation-steps)
  - [1. Business Services Module](#1-business-services-module)
  - [2. Server Initialization](#2-server-initialization)
  - [3. File Reader Service Implementation](#3-file-reader-service-implementation)
  - [4. Testing the Implementation](#4-testing-the-implementation)
- [Usage Examples](#usage-examples)
- [Next Steps](#next-steps)

## Overview

The MCP server has been extended to support adding business services to IRIS productions programmatically. This document outlines the implementation details and provides usage examples.

## Implementation Steps

### 1. Business Services Module

Created a new module `business_services.py` with the following structure for file reader service:

```python
# src/mcp_server_iris/business_services.py

def init(server, logger):
    @server.tool(description="Add a File Reader business service to a production")
    async def add_file_reader_service(
        ctx: Context,
        production_name: str,
        service_name: str,
        file_path: str,
        file_spec: str = "*.txt",
        target_config_names: str = "",
        enabled: bool = True,
    ) -> str:
        # Implementation...

    @server.tool(description="Add an MLLP Receiver business service to a production")
    async def add_mllp_receiver_service(
        ctx: Context,
        production_name: str,
        service_name: str,
        port: int,
        target_config_names: str = "",
        message_schema_category: str = "2.3.1",
        framing: str = "MLLP",
        enabled: bool = True,
    ) -> str:
        # Implementation...
```

### 2. Server Initialization

Updated `server.py` to include the new business services module:

```python
# src/mcp_server_iris/server.py

# Added import
from mcp_server_iris.business_services import init as business_services_init

# In the server setup:
server = MCPServer(name=server_name, version=server_version, lifespan=server_lifespan)
interoperability(server, logger)
business_services_init(server, logger)  # Added this line
```

### 3. File Reader Service Implementation

The core implementation in `business_services.py` handles:

1. Opening the target production
2. Creating a new production item
3. Configuring settings (file path, file spec, targets)
4. Adding the item to the production
5. Saving and compiling the production

Key implementation details:
- Uses IRIS Native API for production manipulation
- Implements transaction support for data consistency
- Includes comprehensive error handling
- Supports all key FileService configuration options

### 4. MLLP Receiver Service Implementation

Added support for MLLP receiver services using `EnsLib.HL7.Service.TCPService`:

Key features:
- Listens on specified TCP port (default: 8777)
- Supports HL7 v2.3.1 message schema
- Uses MLLP framing by default
- Configurable target routing

### 5. Testing the Implementation

Created test scripts to verify functionality:

1. `tests/test_add_file_reader.py` - Adds a new file reader service
2. `tests/check_production_status.py` - Verifies service was added
3. `tests/test_add_mllp_receiver.py` - Adds a new MLLP receiver service

## Usage Examples

### Service Examples

#### Adding a File Reader Service

```python
# Example using the MCP client
await client.session.call_tool(
    "add_file_reader_service",
    {
        "production_name": "Demo.ADTProduction",
        "service_name": "HL7FileReader",
        "file_path": "/opt/irisbuild/",
        "file_spec": "*.hl7",
        "target_config_names": "HL7Router",
        "enabled": True
    }
)
```

#### Adding an MLLP Receiver Service

```python
# Example using the MCP client
await client.session.call_tool(
    "add_mllp_receiver_service",
    {
        "production_name": "Demo.ADTProduction",
        "service_name": "HL7MLLPReceiver",
        "port": 8777,
        "message_schema_category": "2.3.1",
        "framing": "MLLP",
        "target_config_names": "HL7Router",
        "enabled": True
    }
)
```

#### Verifying the Service

```python
# Check production status
auto client.session.call_tool(
    "interoperability_production_status",
    {"name": "Demo.ADTProduction", "full_status": True}
)
```

## Next Steps

1. **Start/Stop Production**
   - Implement production control in test scripts
   - Add proper error handling for production state

2. **MLLP Receiver Service**:
   - Implemented using `EnsLib.HL7.Service.TCPService`
   - Configured for port 8777
   - Set to HL7 v2.3.1 message schema
   - Uses MLLP framing by default

3. **Enhancements**
   - Add support for more service types
   - Implement service updates/deletion
   - Add validation for configuration parameters

4. **Documentation**
   - Document all available API endpoints
   - Add usage examples for common scenarios
   - Create troubleshooting guide

## Troubleshooting

- **Service not appearing**: Ensure the production is saved and compiled
- **Connection issues**: Verify IRIS connection settings in `server.py`
- **Permission errors**: Check that the IRIS user has required permissions

## See Also

- [InterSystems IRIS Documentation](https://docs.intersystems.com/)
- [Ensemble Production Configuration](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ECONFIG)
- [MCP Server Architecture](docs/architecture.md)
