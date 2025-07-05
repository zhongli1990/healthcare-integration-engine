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

    async def get_production_status(self, production_name: str):
        print(f"\n🔍 Getting status for production '{production_name}'...")
        try:
            result = await self.session.call_tool(
                "interoperability_production_status",
                {
                    "name": production_name,
                    "full_status": True
                }
            )
            print(f"✅ Production status:\n{result.content[0].text}")
            return result.content[0].text
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return None

    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()
    try:
        # Connect to the MCP server
        print("Connecting to MCP server...")
        await client.connect_to_server()
        
        # Get production status
        production_name = "Demo.ADTProduction"
        status = await client.get_production_status(production_name)
        
        if status and "HL7FileReader" in status:
            print("\n✅ Success! The HL7FileReader service was added to the production.")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
