import os
from importlib.metadata import version
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import mcp.types as types
from irisnative._IRISNative import createConnection, createIris
from mcp_server_iris.mcpserver import MCPServer, Context, logger
from mcp_server_iris.interoperability import init as interoperability

logger.info("Starting InterSystems IRIS MCP Server")


def get_db_config() -> dict:
    """Get database configuration with hardcoded values for testing."""
    # Hardcoded connection parameters for testing
    config = {
        "hostname": "database",  # Docker service name
        "port": 1972,            # Default IRIS port
        "namespace": "USER",     # Default namespace
        "username": "_SYSTEM",   # Default admin user
        "password": "password",  # Hardcoded password for testing
    }
    
    logger.debug(f"Using hardcoded IRIS connection: {config}")
    logger.debug(f"Full connection string: iris://{config['username']}:{config['password']}@{config['hostname']}:{config['port']}/{config['namespace']}")

    # Check for missing required values
    missing = [k for k, v in config.items() if not v and k != "password"]
    if missing:
        error_msg = f"Missing required database configuration: {', '.join(missing)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    logger.info(f"Server configuration: iris://{config['username']}:{'*' * 8}@{config['hostname']}:{config['port']}/{config['namespace']}")
    logger.debug(f"Full connection details - Host: {config['hostname']}, Port: {config['port']}, Namespace: {config['namespace']}, Username: {config['username']}")

    return config


@asynccontextmanager
async def server_lifespan(server: MCPServer) -> AsyncIterator[dict]:
    """Manage server startup and shutdown lifecycle."""
    try:
        config = get_db_config()
        # Log the connection details (except password)
        logger.debug(f"Connecting to IRIS with config: {{'hostname': '{config['hostname']}', 'port': {config['port']}, 'namespace': '{config['namespace']}', 'username': '{config['username']}'}}")
        logger.debug(f"Full connection string: iris://{config['username']}:{'*' * 8}@{config['hostname']}:{config['port']}/{config['namespace']}")
    except ValueError as ve:
        logger.error(f"Error getting database configuration: {ve}")
        yield {"db": None, "iris": None}
        return
    
    try:
        logger.debug("Creating IRIS connection...")
        db = createConnection(sharedmemory=False, **config)
        logger.debug("IRIS connection created successfully")
        
        logger.debug("Creating IRIS instance...")
        iris = createIris(db)
        logger.debug("IRIS instance created successfully")
        
        # Test the connection
        try:
            version = iris.classMethodValue("%SYSTEM.Version", "GetVersion")
            logger.debug(f"Successfully connected to IRIS version: {version}")
        except Exception as e:
            logger.error(f"Failed to verify IRIS connection: {e}")
            raise
            
        yield {"db": db, "iris": iris}
    except Exception as ex:
        logger.error(f"Error connecting to IRIS: {ex}")
        db = None
        iris = None
        yield {"db": db, "iris": iris}
    finally:
        if db:
            db.close()


server_name = "InterSystems IRIS MCP Server"
server_version = version("mcp_server_iris")
server = MCPServer(name=server_name, version=server_version, lifespan=server_lifespan)
interoperability(server, logger)

# @server.list_resources()
# async def list_resources() -> list[types.Resource]:
#     """List SQL Server tables as resources."""
#     try:
#         ctx = server.request_context
#         conn = ctx.lifespan_context["db"]
#         with conn.cursor() as cursor:
#             # Query to get user tables from the current database
#             cursor.execute(
#                 """
#                 SELECT TABLE_SCHEMA || '.' || TABLE_NAME TABLE_NAME
#                 FROM INFORMATION_SCHEMA.TABLES
#                 WHERE TABLE_TYPE = 'BASE TABLE'
#                 AND   TABLE_SCHEMA NOT LIKE 'Ens%'
#                 AND   TABLE_SCHEMA NOT LIKE 'HS%'
#             """
#             )
#             tables = cursor.fetchall()
#             logger.info(f"Found tables: {tables}")

#             resources = []
#             for table in tables:
#                 resources.append(
#                     types.Resource(
#                         uri=f"iris://{table[0]}/schema",
#                         name=f"Table: {table[0]} columns",
#                         mimeType="application/json",
#                         description=f"Columns in table: {table[0]}",
#                     )
#                 )
#                 resources.append(
#                     types.Resource(
#                         uri=f"iris://{table[0]}/data",
#                         name=f"Table: {table[0]} data",
#                         mimeType="application/json",
#                         description=f"Data in table: {table[0]}",
#                     )
#                 )
#             return resources
#     except Exception as e:
#         logger.error(f"Failed to list resources: {str(e)}")
#         return []


# def read_table_schema(conn, table) -> list[ReadResourceContents]:
#     try:
#         with conn.cursor() as cursor:
#             (schema, table_name) = table.split(".")
#             cursor.execute(
#                 """
#                     SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
#                 """,
#                 (schema, table_name),
#             )
#             rows = cursor.fetchall()
#             return [ReadResourceContents(json.dumps(rows), "application/json")]
#             # [{"content": rows, "mime_type": "application/json"}]
#     except Exception as e:
#         logger.error(
#             f"Database error reading resource data for table {table}: {str(e)}"
#         )
#         raise RuntimeError(f"Database error: {str(e)}")


# def read_table_data(conn, table) -> list[ReadResourceContents]:
#     try:
#         with conn.cursor() as cursor:
#             cursor.execute(f"SELECT TOP 100 * FROM {table}")
#             rows = cursor.fetchall()
#             return [ReadResourceContents(json.dumps(rows), "application/json")]
#     except Exception as e:
#         logger.error(f"Database error reading table {table} columns: {str(e)}")
#         raise RuntimeError(f"Database error: {str(e)}")


# @server.read_resource()
# async def read_resource(uri: types.AnyUrl) -> str:
#     """Read table contents."""
#     uri_str = str(uri)
#     logger.info(f"Reading resource: {uri_str}")

#     if not uri_str.startswith("iris://"):
#         raise ValueError(f"Invalid URI scheme: {uri_str}")

#     (table, resource_type) = uri_str[7:].split("/")
#     logger.debug(f"Table: {table}, resource_type: {resource_type}; from url: {uri_str}")

#     ctx = server.request_context
#     conn = ctx.lifespan_context["db"]
#     if resource_type == "data":
#         return read_table_data(conn, table)
#     elif resource_type == "schema":
#         return read_table_schema(conn, table)
#     else:
#         raise RuntimeError(f"Unknown resource_type: {resource_type}")


@server.tool(description="Execute an SQL query on the Server")
async def execute_sql(
    query: str, ctx: Context, params: list[str] = []
) -> list[types.TextContent]:
    # params = arguments.get("params", [])
    logger.info(f"Executing SQL query: {query}")
    conn = ctx.db
    with conn.cursor() as cursor:
        cursor.execute(query, params)
        # limit by 100 rows
        rows = cursor.fetchall()[:100]
        return [types.TextContent(type="text", text=str(rows))]


def main():
    import argparse

    parser = argparse.ArgumentParser(description=server_name)
    parser.add_argument(
        "transport",
        nargs="?",
        default="stdio",
        choices=["stdio", "sse"],
        help="Transport type (stdio or sse)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3001,
        help="Port for SSE transport (default: 3001)",
    )
    parser.add_argument(
        "--debug",
        type=bool,
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Debug",
    )

    args = parser.parse_args()
    server.settings.port = args.port
    server.settings.debug = args.debug
    try:
        server.run(transport=args.transport)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    main()
