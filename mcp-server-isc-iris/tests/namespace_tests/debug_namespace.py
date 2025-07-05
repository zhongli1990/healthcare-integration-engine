#!/usr/bin/env python3
"""
Debug namespace creation with MCP Tools
"""

import asyncio
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def debug_namespace():
    """Debug namespace creation"""
    print("🔍 Starting debug session...")
    
    server_params = StdioServerParameters(
        command=sys.executable, 
        args=["-m", "mcp_server_iris"],
        env={
            "IRIS_HOSTNAME": "database",
            "IRIS_PORT": "1972",
            "IRIS_NAMESPACE": "%SYS",
            "IRIS_USERNAME": "_SYSTEM",
            "IRIS_PASSWORD": "password",
        }
    )

    async with AsyncExitStack() as exit_stack:
        print("  Connecting to MCP server...")
        try:
            stdio_transport = await exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport
            session = await exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )
            
            print("  Initializing session...")
            await session.initialize()
            print("✅ Successfully connected to MCP server")
            
            # Test with a simple query first
            print("\n🔍 Testing simple query...")
            test_query = await session.call_tool(
                "execute_sql",
                {
                    "query": "SELECT TOP 1 Name FROM %SYS.Namespace",
                    "params": []
                }
            )
            print(f"  Test query result: {test_query}")
            
            # Check if DEMO_TIE exists
            print("\n🔍 Checking for DEMO_TIE namespace...")
            check_ns = await session.call_tool(
                "execute_sql",
                {
                    "query": "SELECT Name FROM %SYS.Namespace WHERE Name = ?",
                    "params": ["DEMO_TIE"]
                }
            )
            print(f"  Check namespace result: {check_ns}")
            
            # List all namespaces
            print("\n📋 Listing all namespaces...")
            list_ns = await session.call_tool(
                "execute_sql",
                {
                    "query": "SELECT Name FROM %SYS.Namespace",
                    "params": []
                }
            )
            print(f"  All namespaces: {list_ns}")
            
            # Try to create the namespace
            print("\n🔧 Attempting to create DEMO_TIE namespace...")
            create_ns = await session.call_tool(
                "execute_sql",
                {
                    "query": "do ##class(%%SYS.Namespace).Create(\"DEMO_TIE\")",
                    "params": []
                }
            )
            print(f"  Create namespace result: {create_ns}")
            
            # Verify if namespace was created
            print("\n🔍 Verifying namespace creation...")
            verify_ns = await session.call_tool(
                "execute_sql",
                {
                    "query": "SELECT Name FROM %SYS.Namespace WHERE Name = ?",
                    "params": ["DEMO_TIE"]
                }
            )
            print(f"  Verify namespace result: {verify_ns}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Main function"""
    print("🚀 Starting debug session for DEMO_TIE namespace creation")
    print("=" * 60)
    
    success = await debug_namespace()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Debug session completed successfully!")
    else:
        print("❌ Debug session encountered errors")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
