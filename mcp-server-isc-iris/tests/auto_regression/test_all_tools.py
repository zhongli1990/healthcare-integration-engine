import asyncio
import sys
from contextlib import AsyncExitStack
from typing import Optional, Dict, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPTester:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.test_results = {}

    async def connect_to_server(self):
        """Connect to the MCP server"""
        server_params = StdioServerParameters(
            command=sys.executable, 
            args=["-m", "mcp_server_iris"], 
            env={
                "IRIS_HOSTNAME": "database",
                "IRIS_PORT": "1972",
                "IRIS_NAMESPACE": "USER",
                "IRIS_USERNAME": "_SYSTEM",
                "IRIS_PASSWORD": "password",
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
        print("✅ Successfully connected to MCP server")

    async def test_tool(self, tool_name: str, params: Dict[str, Any] = None, expected_type=None):
        """Test a single tool and record the result"""
        print(f"\n🔧 Testing tool: {tool_name}")
        print(f"   Parameters: {params or 'None'}")
        
        try:
            if params is not None:
                result = await self.session.call_tool(tool_name, params)
            else:
                result = await self.session.call_tool(tool_name, {})
                
            success = True
            if expected_type and not isinstance(result, expected_type):
                success = False
                print(f"   ❌ Unexpected result type: {type(result)}, expected {expected_type}")
            
            print(f"   ✅ Success! Result: {result}")
            self.test_results[tool_name] = {"status": "✅ PASSED", "result": str(result)[:200] + ("..." if len(str(result)) > 200 else "")}
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            self.test_results[tool_name] = {"status": "❌ FAILED", "error": str(e)}

    async def run_all_tests(self):
        """Run all available tool tests"""
        print("🚀 Starting MCP Server Tool Tests")
        print("=" * 50)
        
        # 1. List all available tools first
        response = await self.session.list_tools()
        tool_names = [tool.name for tool in response.tools]
        print(f"\n🔍 Found {len(tool_names)} tools: {', '.join(tool_names)}\n")
        
        # 2. Test each tool
        
        # SQL Execution
        await self.test_tool(
            "execute_sql",
            {"query": "SELECT TOP 5 * FROM %Dictionary.ClassDefinition"},
            list
        )
        
        # Production Management
        test_production = "Test.Production"
        
        # Create a test production
        await self.test_tool(
            "interoperability_production_create",
            {"name": test_production}
        )
        
        # Start production
        await self.test_tool(
            "interoperability_production_start",
            {"name": test_production}
        )
        
        # Check production status
        await self.test_tool(
            "interoperability_production_status",
            {"name": test_production, "full_status": True}
        )
        
        # Check if production needs update
        await self.test_tool("interoperability_production_needsupdate")
        
        # Get production logs
        await self.test_tool("interoperability_production_logs")
        
        # Get production queues
        await self.test_tool("interoperability_production_queues")
        
        # Stop production
        await self.test_tool("interoperability_production_stop")
        
        # Clean up (delete test production)
        try:
            await self.session.call_tool("execute_sql", {
                "query": f"DO ##class(%%Dictionary.ClassDefinition).%DeleteId(\"{test_production}\")"
            })
            print(f"\n🧹 Cleaned up test production: {test_production}")
        except Exception as e:
            print(f"\n⚠️ Failed to clean up test production: {str(e)}")
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        for tool, result in self.test_results.items():
            status = result["status"]
            details = result.get("result", result.get("error", "No details"))
            print(f"{status} - {tool}: {details}")
        
        passed = sum(1 for r in self.test_results.values() if r["status"] == "✅ PASSED")
        total = len(self.test_results)
        print(f"\n✅ {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    tester = MCPTester()
    try:
        await tester.connect_to_server()
        await tester.session.set_logging_level("debug")
        await tester.run_all_tests()
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
