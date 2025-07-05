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

    async def start_production(self, production_name: str):
        print(f"\n🚀 Starting production '{production_name}'...")
        try:
            result = await self.session.call_tool(
                "interoperability_production_start",
                {"name": production_name}
            )
            print(f"✅ {result.content[0].text}")
            return True
        except Exception as e:
            print(f"❌ Error starting production: {str(e)}")
            return False

    async def stop_production(self, production_name: str):
        print(f"\n🛑 Stopping production '{production_name}'...")
        try:
            result = await self.session.call_tool(
                "interoperability_production_stop",
                {"name": production_name}
            )
            print(f"✅ {result.content[0].text}")
            return True
        except Exception as e:
            print(f"❌ Error stopping production: {str(e)}")
            return False

    async def get_production_status(self, production_name: str):
        print(f"\n📊 Getting status for production '{production_name}'...")
        try:
            result = await self.session.call_tool(
                "interoperability_production_status",
                {"name": production_name, "full_status": True}
            )
            return result.content[0].text
        except Exception as e:
            print(f"❌ Error getting status: {str(e)}")
            return None
            
    async def get_production_logs(self, production_name: str, limit: int = 10):
        print(f"\n📋 Getting logs for production '{production_name}'...")
        try:
            result = await self.session.call_tool(
                "interoperability_production_logs",
                {"name": production_name, "limit": limit}
            )
            return result.content[0].text
        except Exception as e:
            print(f"❌ Error getting logs: {str(e)}")
            return None

    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()
    production_name = "Demo.ADTProduction"
    
    try:
        # Connect to MCP server
        print("🔌 Connecting to MCP server...")
        await client.connect_to_server()
        
        # Get initial status
        status = await client.get_production_status(production_name)
        print(f"\n📊 Initial Status:\n{status}")
        
        # Start the production
        if await client.start_production(production_name):
            # Give it a moment to start
            print("\n⏳ Waiting for production to start...")
            await asyncio.sleep(5)
            
            # Get status after starting
            status = await client.get_production_status(production_name)
            print(f"\n📊 Status After Start:\n{status}")
            
            # Get production logs
            logs = await client.get_production_logs(production_name)
            print(f"\n📜 Production Logs:\n{logs}")
        
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
    finally:
        # Don't stop the production automatically
        # await client.stop_production(production_name)
        await client.cleanup()
        print("\n🏁 Script completed. Production is still running.")
        print("   Run this script again with 'stop' argument to stop the production.")

if __name__ == "__main__":
    asyncio.run(main())
