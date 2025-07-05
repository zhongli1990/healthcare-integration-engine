import asyncio
import sys
from contextlib import AsyncExitStack
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self):
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
        
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )
        
        await self.session.initialize()
        print("✅ Connected to MCP server")

    async def list_tools(self):
        response = await self.session.list_tools()
        return [tool.name for tool in response.tools]

    async def add_file_reader_service(self, production_name: str, service_name: str, base_path: str):
        print(f"\n🔍 Adding File Reader service '{service_name}' to production '{production_name}'...")
        try:
            result = await self.session.call_tool(
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
            print(f"✅ Success! {result.content[0].text}")
            return True
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()
    try:
        # Connect to the MCP server
        print("Connecting to MCP server...")
        await client.connect_to_server()
        
        # List available tools to verify our new tool is available
        tools = await client.list_tools()
        print("\n🔧 Available tools:", ", ".join(tools))
        
        # Test adding a new file reader service to our test production
        production_name = "Demo.ADTProduction2"
        service_name = "HL7FileReader"
        base_path = "/tmp/epr_inbound"
        
        # Create necessary directories in the container
        print(f"\n📂 Creating directory structure in {base_path}...")
        for subdir in ['in', 'out', 'archive', 'error', 'backup', 'work', 'processed']:
            await client.session.call_tool(
                "execute_sql",
                {"query": f"do ##class(%File).CreateDirectory(\"{base_path}/{subdir}\")"}
            )
        
        # Set permissions (assuming IRIS user has sufficient permissions)
        await client.session.call_tool(
            "execute_sql",
            {"query": f"do ##class(%File).SetDirectoryPermissions(\"{base_path}\", \"RWXRWXRWX\")"}
        )
        
        # Add the file reader service
        success = await client.add_file_reader_service(production_name, service_name, base_path)
        
        if success:
            # Restart the production to apply changes
            print("\n🔄 Restarting production to apply changes...")
            await client.session.call_tool(
                "interoperability_production_stop",
                {"name": production_name}
            )
            await client.session.call_tool(
                "interoperability_production_start",
                {"name": production_name}
            )
            
            # Verify the service was added
            status = await client.session.call_tool(
                "interoperability_production_status",
                {"name": production_name, "full_status": True}
            )
            print(f"\n📊 Production status after adding service:")
            print(status.content[0].text)
        
        print("\nTest completed!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
