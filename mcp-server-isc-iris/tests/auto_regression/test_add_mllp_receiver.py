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

    async def add_mllp_receiver_service(self, production_name: str, service_name: str, port: int):
        print(f"\n🔍 Adding MLLP Receiver service '{service_name}' to production '{production_name}'...")
        try:
            result = await self.session.call_tool(
                "add_mllp_receiver_service",
                {
                    "production_name": production_name,
                    "service_name": service_name,
                    "port": port,
                    "message_schema_category": "2.3.1",
                    "framing": "MLLP",
                    "target_config_names": "HL7Router",
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
        
        # Test adding a new MLLP receiver service
        production_name = "Demo.ADTProduction"
        service_name = "HL7MLLPReceiver"
        port = 8777
        
        await client.add_mllp_receiver_service(production_name, service_name, port)
        
        print("\nTest completed!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
