"""
Namespace Manager for IRIS

This script provides functionality to manage IRIS namespaces using MCP tools.
It allows creating namespaces, checking their existence, and managing productions.
"""
import sys
import asyncio
import json
from typing import Optional, Dict, Any, List
from contextlib import AsyncExitStack
from enum import Enum
from dataclasses import dataclass

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Constants
DEFAULT_IRIS_CONFIG = {
    "hostname": "database",
    "port": "1972",
    "username": "_SYSTEM",
    "password": "password"
}

class NamespaceStatus(Enum):
    """Status of a namespace"""
    EXISTS = "exists"
    CREATED = "created"
    ERROR = "error"
    NOT_FOUND = "not_found"

@dataclass
class NamespaceInfo:
    """Information about a namespace"""
    name: str
    status: NamespaceStatus
    details: Dict[str, Any] = None
    error: str = None


class IRISNamespaceManager:
    """Manager for IRIS namespaces using MCP tools"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.available_tools: List[str] = []
        self.iris_config = DEFAULT_IRIS_CONFIG.copy()

    async def connect(self, namespace: str = "USER") -> bool:
        """Connect to the MCP server with the specified namespace"""
        try:
            # Configure server parameters
            env = {
                "IRIS_HOSTNAME": self.iris_config["hostname"],
                "IRIS_PORT": str(self.iris_config["port"]),
                "IRIS_NAMESPACE": namespace,
                "IRIS_USERNAME": self.iris_config["username"],
                "IRIS_PASSWORD": self.iris_config["password"]
            }
            
            server_params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "mcp_server_iris"],
                env=env
            )

            # Connect to the server
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )

            await self.session.initialize()
            
            # Enable debug logging
            await self.session.set_logging_level("debug")
            
            # Get available tools
            response = await self.session.list_tools()
            self.available_tools = [tool.name for tool in response.tools]
            
            print(f"✅ Connected to IRIS at {self.iris_config['hostname']}:{self.iris_config['port']}")
            print(f"   Current namespace: {namespace}")
            print(f"   Available tools: {', '.join(self.available_tools)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to IRIS: {str(e)}")
            return False

    async def execute_sql(self, query: str, params: list = None, namespace: str = None) -> Dict:
        """Execute an SQL query in the specified namespace"""
        if params is None:
            params = []
            
        if namespace:
            # Switch to the target namespace
            await self.switch_namespace(namespace)
            
        try:
            response = await self.session.call_tool(
                "execute_sql",
                {
                    "query": query,
                    "params": params
                }
            )
            return {"success": True, "content": response.content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def switch_namespace(self, namespace: str) -> bool:
        """Switch to a different namespace"""
        try:
            await self.session.call_tool(
                "execute_sql",
                {"query": f"ZN \"{namespace}\""}
            )
            print(f"✅ Switched to namespace: {namespace}")
            return True
        except Exception as e:
            print(f"❌ Failed to switch to namespace {namespace}: {str(e)}")
            return False

    async def check_namespace_exists(self, namespace: str) -> NamespaceStatus:
        """Check if a namespace exists"""
        try:
            # Switch to %SYS to check namespaces
            await self.switch_namespace("%SYS")
            
            # Execute a query to check if namespace exists
            result = await self.execute_sql(
                "SELECT Name FROM %SYS.Namespace WHERE Name = ?",
                [namespace]
            )
            
            if result["success"] and result["content"] and result["content"][0].text.strip():
                return NamespaceStatus.EXISTS
            return NamespaceStatus.NOT_FOUND
            
        except Exception as e:
            print(f"❌ Error checking namespace: {str(e)}")
            return NamespaceStatus.ERROR

    async def create_namespace(self, namespace: str) -> NamespaceInfo:
        """Create a new namespace"""
        try:
            # Check if namespace already exists
            status = await self.check_namespace_exists(namespace)
            if status == NamespaceStatus.EXISTS:
                return NamespaceInfo(
                    name=namespace,
                    status=status,
                    details={"message": f"Namespace '{namespace}' already exists"}
                )
            
            # Create the namespace using ObjectScript
            result = await self.execute_sql(
                f"do ##class(%%SYS.Namespace).Create(\"{namespace}\")",
                namespace="%SYS"
            )
            
            if result["success"]:
                # Enable Ensemble for the namespace
                enable_result = await self.execute_sql(
                    f"do ##class(%%Library.EnsembleMgr).EnableNamespace(\"{namespace}\")",
                    namespace="%SYS"
                )
                
                details = {
                    "created": True,
                    "ensemble_enabled": enable_result["success"]
                }
                
                return NamespaceInfo(
                    name=namespace,
                    status=NamespaceStatus.CREATED,
                    details=details
                )
            else:
                return NamespaceInfo(
                    name=namespace,
                    status=NamespaceStatus.ERROR,
                    error=result.get("error", "Unknown error creating namespace")
                )
                
        except Exception as e:
            return NamespaceInfo(
                name=namespace,
                status=NamespaceStatus.ERROR,
                error=str(e)
            )

    async def cleanup(self):
        """Clean up resources"""
        try:
            await self.exit_stack.aclose()
            print("✅ Cleaned up resources")
        except Exception as e:
            print(f"❌ Error during cleanup: {str(e)}")


async def main():
    # Example usage
    manager = IRISNamespaceManager()
    
    try:
        # Connect to IRIS
        if not await manager.connect(namespace="%SYS"):
            return
        
        # Define the namespace to create
        target_namespace = "DEMO_TIE"
        
        # Check if namespace exists
        print(f"\n🔍 Checking if namespace '{target_namespace}' exists...")
        status = await manager.check_namespace_exists(target_namespace)
        
        if status == NamespaceStatus.EXISTS:
            print(f"ℹ️  Namespace '{target_namespace}' already exists")
        else:
            # Create the namespace
            print(f"\n🔧 Creating namespace '{target_namespace}'...")
            result = await manager.create_namespace(target_namespace)
            
            if result.status == NamespaceStatus.CREATED:
                print(f"✅ Successfully created namespace '{target_namespace}'")
                if result.details and result.details.get("ensemble_enabled"):
                    print("✅ Ensemble has been enabled for the namespace")
            else:
                print(f"❌ Failed to create namespace: {result.error}")
        
        # Verify by switching to the namespace
        print(f"\n🔍 Verifying namespace access...")
        if await manager.switch_namespace(target_namespace):
            # Get IRIS version info
            version_info = await manager.execute_sql("select $namespace, $zversion")
            print(f"✅ Successfully accessed namespace '{target_namespace}'")
            if version_info["success"]:
                print(f"   Version info: {version_info['content']}")
    
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
