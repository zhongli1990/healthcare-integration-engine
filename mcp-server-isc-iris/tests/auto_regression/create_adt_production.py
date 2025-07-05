import asyncio
import sys
import argparse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

async def create_adt_production(production_name):
    """Create a production with the specified name using MCP tooling"""
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
        
        # Use the provided production name
        
        try:
            # Create the production
            print(f"Creating production: {production_name}")
            create_result = await session.call_tool(
                "interoperability_production_create",
                {"name": production_name}
            )
            print(f"Production creation result: {create_result.content}")
            
            # Verify the production was created by checking its status
            print("\nChecking production status...")
            status_result = await session.call_tool(
                "interoperability_production_status",
                {"name": production_name}
            )
            print(f"Production status: {status_result.content}")
            
            # Start the production
            print("\nStarting the production...")
            start_result = await session.call_tool(
                "interoperability_production_start",
                {"name": production_name}
            )
            print(f"Production start result: {start_result.content}")
            
            # Verify the production is running
            print("\nVerifying production is running...")
            verify_result = await session.call_tool(
                "interoperability_production_status",
                {"name": production_name, "full_status": True}
            )
            print(f"Production verification: {verify_result.content}")
            
        except Exception as e:
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Create an InterSystems IRIS Production')
    parser.add_argument('--name', type=str, default='Demo.ADTProduction',
                       help='Name of the production to create (e.g., Demo.ADTProduction2)')
    
    args = parser.parse_args()
    
    print(f"Creating production: {args.name}")
    asyncio.run(create_adt_production(args.name))
