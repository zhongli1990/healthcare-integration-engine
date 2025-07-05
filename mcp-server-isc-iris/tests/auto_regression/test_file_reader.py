import asyncio
import os
import shutil
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

    async def restart_production(self, production_name: str):
        print(f"\n🔄 Restarting production '{production_name}'...")
        try:
            # Stop the production
            await self.session.call_tool(
                "interoperability_production_stop",
                {"name": production_name}
            )
            
            # Start the production
            result = await self.session.call_tool(
                "interoperability_production_start",
                {"name": production_name}
            )
            print(f"✅ {result.content[0].text}")
            return True
        except Exception as e:
            print(f"❌ Error restarting production: {str(e)}")
            return False

    async def get_production_status(self, production_name: str):
        try:
            result = await self.session.call_tool(
                "interoperability_production_status",
                {"name": production_name, "full_status": True}
            )
            return result.content[0].text
        except Exception as e:
            print(f"❌ Error getting status: {str(e)}")
            return None

    async def cleanup(self):
        await self.exit_stack.aclose()

def copy_test_file():
    """Copy the sample HL7 file to the input directory"""
    source = "/app/tests/sample.hl7"
    dest = "/tmp/epr_inbound/in/"
    
    # Clear any existing test files
    for f in os.listdir(dest):
        if f.endswith('.hl7'):
            os.remove(os.path.join(dest, f))
    
    # Copy the test file
    shutil.copy(source, dest)
    print(f"📄 Copied test file to {dest}")
    return os.path.join(dest, os.path.basename(source))

def check_archive():
    """Check if the file was archived"""
    archive_dir = "/tmp/epr_inbound/archive/"
    files = [f for f in os.listdir(archive_dir) if f.endswith('.hl7')]
    if files:
        print(f"✅ Found {len(files)} file(s) in archive")
        for f in files:
            print(f"   - {f}")
        return True
    else:
        print("❌ No files found in archive")
        return False

async def main():
    client = MCPClient()
    production_name = "Demo.ADTProduction"
    
    try:
        # Connect to MCP server
        print("🔌 Connecting to MCP server...")
        await client.connect_to_server()
        
        # Restart the production to apply new settings
        if not await client.restart_production(production_name):
            print("❌ Failed to restart production")
            return
        
        # Get production status
        status = await client.get_production_status(production_name)
        print(f"\n📊 Production Status After Restart:\n{status}")
        
        # Copy test file to input directory
        print("\n📤 Copying test file to input directory...")
        test_file = copy_test_file()
        print(f"   - Test file: {test_file}")
        
        # Wait a moment for the file to be processed
        print("\n⏳ Waiting for file processing... (10 seconds)")
        await asyncio.sleep(10)
        
        # Check if file was archived
        print("\n🔍 Checking archive directory...")
        check_archive()
        
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
    finally:
        await client.cleanup()
        print("\n🏁 Test completed")

if __name__ == "__main__":
    import sys
    asyncio.run(main())
