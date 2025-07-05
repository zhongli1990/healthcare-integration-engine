import asyncio
import sys
from pathlib import Path
from contextlib import AsyncExitStack

# Add the parent directory to the path so we can import from src
sys.path.append(str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    """Client for testing MCP server SQL operations."""
    
    def __init__(self):
        self.session = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self):
        """Connect to the MCP server."""
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

    async def execute_sql(self, query):
        """Execute an SQL query through the MCP server."""
        response = await self.session.call_tool(
            "execute_sql",
            {"query": query, "params": []}
        )
        return response.content

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()

async def test_sql_operations():
    """Test various SQL operations through the MCP server."""
    client = MCPClient()
    results = {"passed": 0, "failed": 0}
    
    try:
        print("\n=== Starting SQL Operations Test ===")
        await client.connect_to_session()
        
        # Test 1: Basic SELECT
        print("\n--- Testing SELECT ---")
        try:
            result = await client.execute_sql("SELECT $namespace, $zversion")
            print(f"✅ SELECT Result: {result}")
            results["passed"] += 1
        except Exception as e:
            print(f"❌ SELECT Failed: {e}")
            results["failed"] += 1
        
        # Test 2: Create a test table
        print("\n--- Testing CREATE TABLE ---")
        try:
            await client.execute_sql("""
            CREATE TABLE Test.MCPTest (
                ID INT PRIMARY KEY,
                Name VARCHAR(50),
                Value VARCHAR(100),
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            print("✅ Created Test.MCPTest table")
            results["passed"] += 1
        except Exception as e:
            print(f"❌ CREATE TABLE Failed: {e}")
            results["failed"] += 1
        
        # Run remaining tests only if table creation was successful
        if "MCPTest" in (await client.execute_sql("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'Test' AND TABLE_NAME = 'MCPTest'""")):
            
            # Test 3: INSERT data
            print("\n--- Testing INSERT ---")
            try:
                for i in range(1, 4):
                    await client.execute_sql(f"""
                    INSERT INTO Test.MCPTest (ID, Name, Value)
                    VALUES ({i}, 'Test {i}', 'Value {i}')""")
                print("✅ Inserted test data")
                results["passed"] += 1
            except Exception as e:
                print(f"❌ INSERT Failed: {e}")
                results["failed"] += 1
            
            # Test 4: SELECT inserted data
            print("\n--- Testing SELECT with data ---")
            try:
                result = await client.execute_sql("SELECT * FROM Test.MCPTest")
                print(f"✅ Retrieved test data: {result}")
                results["passed"] += 1
            except Exception as e:
                print(f"❌ SELECT with data Failed: {e}")
                results["failed"] += 1
            
            # Cleanup: Drop test table
            print("\n--- Cleaning Up ---")
            try:
                await client.execute_sql("DROP TABLE Test.MCPTest")
                print("✅ Dropped Test.MCPTest table")
                results["passed"] += 1
            except Exception as e:
                print(f"❌ DROP TABLE Failed: {e}")
                results["failed"] += 1
        
        print(f"\n=== Test Results ===")
        print(f"Tests Passed: {results['passed']}")
        print(f"Tests Failed: {results['failed']}")
        
    except Exception as e:
        print(f"\n❌ Test Error: {e}")
        results["failed"] += 1
    finally:
        await client.cleanup()
        return results

if __name__ == "__main__":
    test_results = asyncio.run(test_sql_operations())
    sys.exit(test_results["failed"])
