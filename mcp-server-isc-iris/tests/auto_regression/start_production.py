import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

async def start_production(production_name):
    """Start a production and verify its status"""
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
        
        # Set log level to debug for more detailed output
        await session.set_logging_level("debug")
        
        try:
            # Start the production
            print(f"🚀 Starting production: {production_name}")
            start_result = await session.call_tool(
                "interoperability_production_start",
                {"name": production_name}
            )
            print(f"Start result: {start_result.content[0].text}")
            
            # Check production status
            print("\n📊 Checking production status...")
            status_result = await session.call_tool(
                "interoperability_production_status",
                {"name": production_name, "full_status": True}
            )
            print(f"Status: {status_result.content[0].text}")
            
            # Show recent logs
            print("\n📋 Recent logs:")
            logs_result = await session.call_tool(
                "interoperability_production_logs",
                {"limit": 5}
            )
            print(logs_result.content[0].text)
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

if __name__ == "__main__":
    production_name = "Demo.ADTProduction2"
    print(f"Starting production: {production_name}")
    asyncio.run(start_production(production_name))
