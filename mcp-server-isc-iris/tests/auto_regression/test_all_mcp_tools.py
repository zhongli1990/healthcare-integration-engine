import asyncio
import sys
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json

class MCPToolTester:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.test_results: Dict[str, Dict[str, Any]] = {}

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

    async def list_tools(self) -> List[str]:
        """List all available tools"""
        if not self.session:
            await self.connect_to_server()
        
        response = await self.session.list_tools()
        tool_names = [tool.name for tool in response.tools]
        print(f"\n🔧 Available tools: {', '.join(tool_names)}")
        return tool_names

    async def test_tool(self, tool_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Test a single tool with the given parameters"""
        if not self.session:
            await self.connect_to_server()
        
        if params is None:
            params = {}
            
        print(f"\n🔍 Testing tool: {tool_name}")
        print(f"   Parameters: {json.dumps(params, indent=4)}")
        
        try:
            result = await self.session.call_tool(tool_name, params)
            print(f"✅ Success! Result: {result.content}")
            self.test_results[tool_name] = {"status": "SUCCESS", "result": result.content}
            return {"status": "SUCCESS", "result": result.content}
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error: {error_msg}")
            self.test_results[tool_name] = {"status": "ERROR", "error": error_msg}
            return {"status": "ERROR", "error": error_msg}

    async def run_all_tests(self):
        """Run tests for all available tools"""
        print("🚀 Starting MCP Tool Testing Suite")
        print("=" * 50)
        
        # First, list all available tools
        tool_names = await self.list_tools()
        
        # Define test cases for each tool
        test_cases = {
            "execute_sql": {
                "query": "SELECT $namespace, $zversion"
            },
            "interoperability_production_create": {
                "name": "Demo.ADTProduction"
            },
            "interoperability_production_status": {
                "name": "Demo.ADTProduction",
                "full_status": True
            },
            "interoperability_production_start": {
                "name": "Demo.ADTProduction"
            },
            "interoperability_production_stop": {
                "name": "Demo.ADTProduction"
            },
            "interoperability_production_update": {},
            "interoperability_production_recover": {},
            "interoperability_production_needsupdate": {},
            "interoperability_production_logs": {
                "limit": 5
            },
            "interoperability_production_queues": {}
        }
        
        # Only test tools that are actually available
        test_cases = {k: v for k, v in test_cases.items() if k in tool_names}
        
        # Run each test case
        for tool_name, params in test_cases.items():
            await self.test_tool(tool_name, params)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print a summary of test results"""
        print("\n📊 Test Summary")
        print("=" * 50)
        
        success_count = sum(1 for r in self.test_results.values() if r["status"] == "SUCCESS")
        total = len(self.test_results)
        
        for tool, result in self.test_results.items():
            status = "✅" if result["status"] == "SUCCESS" else "❌"
            details = result.get("result", result.get("error", "No details"))
            print(f"{status} {tool}: {details}")
        
        print("\n" + "=" * 50)
        print(f"🎉 Test Results: {success_count}/{total} tests passed ({success_count/max(1, total)*100:.1f}%)")
        print("=" * 50)

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    tester = MCPToolTester()
    try:
        await tester.connect_to_server()
        await tester.run_all_tests()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
