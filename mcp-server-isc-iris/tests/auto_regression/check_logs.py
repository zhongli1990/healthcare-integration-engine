import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

async def check_logs(limit=10):
    """Check the production logs"""
    async with AsyncExitStack() as exit_stack:
        # Connect to the MCP server
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server_iris"],
            env={
                "IRIS_HOSTNAME": "database",
                "IRIS_PORT": "1972",
                "IRIS_NAMESPACE": "USER",
                "IRIS_USERNAME": "_SYSTEM",
                "IRIS_PASSWORD": "SYS",
            }
        )
        
        # Set up the client connection
        stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        
        # Create a session
        session = await exit_stack.enter_async_context(ClientSession(stdio, write))
        await session.initialize()
        
        # Get recent logs
        print(f"📋 Checking last {limit} log entries...")
        logs_result = await session.call_tool(
            "interoperability_production_logs",
            {"limit": limit}
        )
        
        if logs_result.content:
            print("\n=== Production Logs ===")
            print(logs_result.content[0].text)
        else:
            print("No log entries found.")
            
        # Check if the file was processed
        print("\n=== Checking file status ===")
        print("Input directory:")
        print("  - test_hl7.hl7" if "test_hl7.hl7" in ",".join(open("test_data/epr_inbound/in/test_hl7.hl7").readlines()) else "  - No test file found")
        
        print("\nArchive directory should contain the processed file")

if __name__ == "__main__":
    print("Checking production logs...")
    asyncio.run(check_logs(limit=10))
