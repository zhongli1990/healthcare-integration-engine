import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

async def update_file_reader():
    """Update the file reader service configuration"""
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
        
        production_name = "Demo.ADTProduction2"
        service_name = "HL7FileReader"
        base_path = "/tmp/epr_inbound"
        
        try:
            # First, stop the production
            print("🛑 Stopping the production...")
            await session.call_tool(
                "interoperability_production_stop",
                {"name": production_name}
            )
            
            # Update the file reader service configuration
            print(f"\n🔄 Updating {service_name} configuration...")
            update_result = await session.call_tool(
                "add_file_reader_service",
                {
                    "production_name": production_name,
                    "service_name": service_name,
                    "file_path": f"{base_path}/in",
                    "file_spec": "*.hl7",
                    "target_config_names": "HL7Router",
                    "archive_path": f"{base_path}/archive",
                    "error_path": f"{base_path}/error",
                    "work_path": f"{base_path}/work",
                    "enabled": True
                }
            )
            print(f"Update result: {update_result.content[0].text}")
            
            # Start the production again
            print("\n🚀 Starting the production...")
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
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

if __name__ == "__main__":
    print("Updating file reader service configuration...")
    asyncio.run(update_file_reader())
