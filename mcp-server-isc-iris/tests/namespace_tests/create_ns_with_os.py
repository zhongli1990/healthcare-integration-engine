#!/usr/bin/env python3
"""
Create DEMO_TIE Namespace using ObjectScript through MCP Tools
"""

import asyncio
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def create_namespace():
    """Create DEMO_TIE namespace using ObjectScript"""
    print("🚀 Starting DEMO_TIE namespace creation")
    
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
        print("  Connecting to MCP server...")
        try:
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
            
            # Check if namespace exists using ObjectScript
            print("\n🔍 Checking if DEMO_TIE namespace exists...")
            check_ns = await session.call_tool(
                "execute_os",
                {
                    "code": "Write ##class(%SYS.Namespace).Exists(\"DEMO_TIE\")"
                }
            )
            
            print(f"  Namespace exists check result: {check_ns}")
            
            if check_ns.content and check_ns.content[0].text.strip() == "0":
                print("  Creating DEMO_TIE namespace...")
                
                # Create the namespace using ObjectScript
                create_ns = await session.call_tool(
                    "execute_os",
                    {
                        "code": """
                        Set sc = ##class(%SYS.Namespace).Create("DEMO_TIE")
                        Write $System.Status.GetErrorText(sc)
                        """
                    }
                )
                
                print(f"  Create namespace result: {create_ns}")
                
                # Enable Ensemble for the namespace
                enable_ens = await session.call_tool(
                    "execute_os",
                    {
                        "code": """
                        Set sc = ##class(%Library.EnsembleMgr).EnableNamespace("DEMO_TIE")
                        Write $System.Status.GetErrorText(sc)
                        """
                    }
                )
                
                print(f"  Enable Ensemble result: {enable_ens}")
                
                # Verify namespace creation
                verify_ns = await session.call_tool(
                    "execute_os",
                    {
                        "code": "Write ##class(%SYS.Namespace).Exists(\"DEMO_TIE\")"
                    }
                )
                
                print(f"  Verify namespace exists: {verify_ns}")
                
                if verify_ns.content and verify_ns.content[0].text.strip() == "1":
                    print("\n✅ DEMO_TIE namespace created and configured successfully!")
                    return True
                else:
                    print("\n❌ Failed to verify DEMO_TIE namespace creation")
                    return False
            else:
                print("\nℹ️  DEMO_TIE namespace already exists")
                return True
                
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    try:
        result = asyncio.run(create_namespace())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
