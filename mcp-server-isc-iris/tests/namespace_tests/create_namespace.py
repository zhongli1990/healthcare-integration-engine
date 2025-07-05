#!/usr/bin/env python3
"""
Create DEMO_TIE Namespace using MCP Tools
"""

import asyncio
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def create_namespace():
    """Create DEMO_TIE namespace if it doesn't exist"""
    server_params = StdioServerParameters(
        command=sys.executable, 
        args=["-m", "mcp_server_iris"],
        env={
            "IRIS_HOSTNAME": "database",
            "IRIS_PORT": "1972",
            "IRIS_NAMESPACE": "%SYS",  # Connect to %SYS for namespace operations
            "IRIS_USERNAME": "_SYSTEM",
            "IRIS_PASSWORD": "password",
        }
    )

    async with AsyncExitStack() as exit_stack:
        # Connect to MCP server
        stdio_transport = await exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio, write = stdio_transport
        session = await exit_stack.enter_async_context(
            ClientSession(stdio, write)
        )
        
        await session.initialize()
        print("✅ Successfully connected to MCP server")
        
        # Enable debug logging
        await session.set_logging_level("debug")
        
        # Check if namespace exists
        print("\n🔍 Checking if DEMO_TIE namespace exists...")
        check_ns = await session.call_tool(
            "execute_sql",
            {
                "query": "SELECT Name FROM %SYS.Namespace WHERE Name = ?",
                "params": ["DEMO_TIE"]
            }
        )
        
        # Check the response
        if check_ns.is_error or not check_ns.content[0].text.strip():
            print("  Namespace DEMO_TIE does not exist. Creating...")
            
            # Create the namespace
            create_ns = await session.call_tool(
                "execute_sql",
                {
                    "query": "do ##class(%%SYS.Namespace).Create(\"DEMO_TIE\")",
                    "params": []
                }
            )
            
            if create_ns.is_error:
                print(f"❌ Failed to create namespace: {create_ns}")
                return False
                
            print("✅ Namespace DEMO_TIE created successfully")
            
            # Enable Ensemble for the namespace
            enable_ens = await session.call_tool(
                "execute_sql",
                {
                    "query": "do ##class(%%Library.EnsembleMgr).EnableNamespace(\"DEMO_TIE\")",
                    "params": []
                }
            )
            
            if enable_ens.is_error:
                print(f"⚠️ Warning: Could not enable Ensemble for DEMO_TIE: {enable_ens}")
            else:
                print("✅ Enabled Ensemble for DEMO_TIE namespace")
        else:
            print("ℹ️  Namespace DEMO_TIE already exists")
        
        return True

async def main():
    """Main function"""
    try:
        success = await create_namespace()
        if success:
            print("\n✅ DEMO_TIE namespace setup completed successfully!")
        else:
            print("\n❌ Failed to setup DEMO_TIE namespace")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
