import asyncio
from mcp import ClientSession, StdioServerParameters
from contextlib import AsyncExitStack
import sys

class MCPClient:
    def __init__(self):
        self.session = None
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
        response = await self.session.call_tool(
            "execute_sql",
            {"query": query, "params": []}
        )
        return response.content

    async def cleanup(self):
        await self.exit_stack.aclose()

async def test_sql_operations():
    client = MCPClient()
    try:
        await client.connect_to_server()
        
        # Test 1: Basic SELECT
        print("\n--- Testing SELECT ---")
        result = await client.execute_sql("SELECT $namespace, $zversion")
        print(f"SELECT Result: {result}")
        
        # Test 2: Create a test table
        print("\n--- Creating Test Table ---")
        await client.execute_sql("""
        CREATE TABLE Test.MCPTest (
            ID INT PRIMARY KEY,
            Name VARCHAR(50),
            Value VARCHAR(100),
            CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        print("Created Test.MCPTest table")
        
        # Test 3: INSERT data
        print("\n--- Testing INSERT ---")
        for i in range(1, 4):
            await client.execute_sql(f"""
            INSERT INTO Test.MCPTest (ID, Name, Value)
            VALUES ({i}, 'Test {i}', 'Value {i}')""")
        print("Inserted test data")
        
        # Test 4: SELECT inserted data
        print("\n--- Verifying Data ---")
        result = await client.execute_sql("SELECT * FROM Test.MCPTest")
        print(f"Test data: {result}")
        
        # Test 5: UPDATE data
        print("\n--- Testing UPDATE ---")
        await client.execute_sql("""
        UPDATE Test.MCPTest 
        SET Value = 'Updated Value' 
        WHERE ID = 1""")
        print("Updated record with ID=1")
        
        # Verify update
        result = await client.execute_sql("""
        SELECT * FROM Test.MCPTest WHERE ID = 1""")
        print(f"Updated record: {result}")
        
        # Test 6: DELETE data
        print("\n--- Testing DELETE ---")
        await client.execute_sql("""
        DELETE FROM Test.MCPTest WHERE ID = 3""")
        print("Deleted record with ID=3")
        
        # Verify delete
        result = await client.execute_sql("""
        SELECT * FROM Test.MCPTest""")
        print(f"Remaining records: {result}")
        
        # Cleanup: Drop test table
        print("\n--- Cleaning Up ---")
        await client.execute_sql("DROP TABLE Test.MCPTest")
        print("Dropped Test.MCPTest table")
        
    finally:
        await client.cleanup()

if __name__ == "__main__":
    from mcp.client.stdio import stdio_client
    asyncio.run(test_sql_operations())
