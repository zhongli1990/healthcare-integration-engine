# MCP Testing Guide

This document provides a comprehensive guide to testing the MCP (Management and Control Protocol) tools for InterSystems IRIS Health Connect. It includes step-by-step instructions for testing each MCP tool.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Test Environment Setup](#test-environment-setup)
3. [MCP Tool Testing](#mcp-tool-testing)
   - [1. SQL Execution](#1-sql-execution)
   - [2. Production Management](#2-production-management)
   - [3. Business Services](#3-business-services)
   - [4. Production Monitoring](#4-production-monitoring)
4. [Test Scripts](#test-scripts)
5. [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker and Docker Compose installed
- Access to the MCP server Docker container
- Python 3.7+ with required packages (installed in the container)

## Test Environment Setup

1. **Start the test environment**:
   ```bash
   docker-compose up -d
   ```

2. **Verify containers are running**:
   ```bash
   docker-compose ps
   ```

## MCP Tool Testing

### 1. SQL Execution

**Tool**: `execute_sql`

**Description**: Execute SQL queries on the IRIS database.

**Test Commands**:

1. **Basic SQL Query**:
   ```bash
   docker exec -it mcp-server-iris python -c "
   from mcp import ClientSession, StdioServerParameters
   from mcp.client.stdio import stdio_client
   import asyncio
   
   async def test_sql():
       async with stdio_client(StdioServerParameters(
           command='python',
           args=['-m', 'mcp_server_iris']
       )) as (r, w):
           async with ClientSession(r, w) as session:
               await session.initialize()
               result = await session.call_tool('execute_sql', {'query': 'SELECT $namespace, $zversion'})
               print(result.content)
   
   asyncio.run(test_sql())
   ""
   ```

### 2. Production Management

#### 2.1 Create a Production

**Tool**: `interoperability_production_create`

**Test Command**:
```bash
docker exec -it mcp-server-iris python tests/auto_regression/create_adt_production.py --name Demo.TestProduction
```

#### 2.2 Start a Production

**Tool**: `interoperability_production_start`

**Test Command**:
```bash
docker exec -it mcp-server-iris python -c "
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio

async def start_prod():
    async with stdio_client(StdioServerParameters(
        command='python',
        args=['-m', 'mcp_server_iris']
    )) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool('interoperability_production_start', {'name': 'Demo.TestProduction'})
            print(result.content)

asyncio.run(start_prod())
"
```

#### 2.3 Check Production Status

**Tool**: `interoperability_production_status`

**Test Command**:
```bash
docker exec -it mcp-server-iris python -c "
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio

async def check_status():
    async with stdio_client(StdioServerParameters(
        command='python',
        args=['-m', 'mcp_server_iris']
    )) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool('interoperability_production_status', 
                                          {'name': 'Demo.TestProduction', 'full_status': True})
            print(result.content)

asyncio.run(check_status())
"
```

### 3. Business Services

#### 3.1 Add File Reader Service

**Tool**: `add_file_reader_service`

**Test Command**:
```bash
docker exec -it mcp-server-iris python -c "
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio

async def add_file_reader():
    async with stdio_client(StdioServerParameters(
        command='python',
        args=['-m', 'mcp_server_iris']
    )) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool('add_file_reader_service', {
                'production_name': 'Demo.TestProduction',
                'service_name': 'TestFileReader',
                'file_path': '/tmp/epr_inbound/in',
                'file_spec': '*.hl7',
                'target_config_names': 'HL7Router',
                'archive_path': '/tmp/epr_inbound/archive',
                'error_path': '/tmp/epr_inbound/error',
                'work_path': '/tmp/epr_inbound/work',
                'enabled': True
            })
            print(result.content)

asyncio.run(add_file_reader())
"
```

### 4. Production Monitoring

#### 4.1 View Production Logs

**Tool**: `interoperability_production_logs`

**Test Command**:
```bash
docker exec -it mcp-server-iris python -c "
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio

async def view_logs():
    async with stdio_client(StdioServerParameters(
        command='python',
        args=['-m', 'mcp_server_iris']
    )) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool('interoperability_production_logs', {
                'limit': 10,
                'log_type_info': True,
                'log_type_error': True,
                'log_type_warning': True
            })
            print(result.content)

asyncio.run(view_logs())
"
```

## Test Scripts

The following test scripts are available in the `tests/auto_regression` directory:

1. `example.py` - Basic MCP tool testing
2. `test_all_tools.py` - Comprehensive test of all MCP tools
3. `create_adt_production.py` - Create and start a production
4. `test_add_file_reader.py` - Test adding a file reader service
5. `test_add_mllp_receiver.py` - Test adding an MLLP receiver service
6. `test_mllp_service.py` - Test MLLP service functionality

## Troubleshooting

1. **Connection Issues**:
   - Verify Docker containers are running: `docker-compose ps`
   - Check container logs: `docker-compose logs mcp-server-iris`

2. **Production Not Starting**:
   - Check IRIS logs: `docker exec -it iris-database iris session iris -U%SYS "##class(%SYSTEM.OBJ).ShowLog(\"IRIS_Startup_log.\")"`

3. **Permission Issues**:
   - Ensure file paths exist and have correct permissions
   - Check IRIS user permissions

4. **Debugging**:
   - Set log level to debug: `await session.set_logging_level("debug")`
   - Check MCP server logs for detailed error messages
