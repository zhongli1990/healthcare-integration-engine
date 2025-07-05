#!/usr/bin/env python3
"""
Setup DEMO_TIE Namespace and Create Production with Business Service

This script demonstrates how to use the MCP tools to:
1. Create a new namespace (DEMO_TIE) if it doesn't exist
2. Create a production class
3. Add a business service to the production
4. Enable the production

Prerequisites:
- MCP server running in Docker
- IRIS instance accessible from the MCP server
"""

import asyncio
import sys
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPProductionManager:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.namespace = "DEMO_TIE"
        self.production_name = "DemoTIE.Production"
        self.service_name = "DemoService"

    async def connect_to_server(self):
        """Connect to the MCP server"""
        server_params = StdioServerParameters(
            command=sys.executable, 
            args=["-m", "mcp_server_iris"],
            env={
                "IRIS_HOSTNAME": "database",
                "IRIS_PORT": "1972",
                "IRIS_NAMESPACE": "USER",  # We'll switch to DEMO_TIE later
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

    async def create_namespace_if_not_exists(self):
        """Create DEMO_TIE namespace if it doesn't exist"""
        print(f"\n🔧 Checking/Creating namespace: {self.namespace}")
        
        # Check if namespace exists
        check_ns = await self.session.call_tool(
            "execute_sql",
            {
                "query": "SELECT Name FROM %SYS.Namespace WHERE Name = ?",
                "params": [self.namespace]
            }
        )
        
        # If namespace doesn't exist, create it
        if not check_ns.content[0].text.strip():
            print(f"  Creating namespace: {self.namespace}")
            create_ns = await self.session.call_tool(
                "execute_sql",
                {
                    "query": f"##class(%%SYS.Namespace).Create(\"{self.namespace}\")",
                    "params": []
                }
            )
            print(f"  Namespace created: {create_ns}")
        else:
            print(f"  Namespace {self.namespace} already exists")

    async def create_production_class(self):
        """Create the production class in DEMO_TIE namespace"""
        print(f"\n🔧 Creating production class: {self.production_name}")
        
        # Switch to DEMO_TIE namespace
        await self.session.call_tool("execute_sql", {"query": "ZN \"DEMO_TIE\""})
        
        # Create the production class
        class_definition = f"""Class {self.production_name} Extends Ens.Production
{{
XData ProductionDefinition
{{
<Production Name=\"{0}" LogGeneralTraceEvents="false">
</Production>
}}
}}""".format(self.production_name.split('.')[-1])
        
        # Compile the class
        result = await self.session.call_tool("execute_sql", {
            "query": f"do ##class(%%Compiler.UDL.TextServices).SetTextFromString(\"{self.production_name}\",\"{class_definition}\")"
        })
        
        compile_result = await self.session.call_tool("execute_sql", {
            "query": f"do ##class(%%Library.EnsembleMgr).EnableNamespace(\"{self.namespace}\")"
        })
        
        print(f"  Production class created and compiled")

    async def add_business_service(self):
        """Add a business service to the production"""
        print(f"\n🔧 Adding business service to production")
        
        # Create the business service class
        service_class = f"DemoTIE.Service.FileService"
        service_definition = f"""Class {service_class} Extends Ens.BusinessService
{{
Parameter ADAPTER = "EnsLib.File.InboundAdapter";

Parameter SETTINGS = "TargetConfigName:Basic:selector?context={{##class(Ens.Config.ContextSearch).productionSettingsFind(\"Ens.BusinessProcess\",.cont)}},ArchivePath,FileSpec,FilePath";

Property TargetConfigName As %String(MAXLEN = 1000);

Method OnProcessInput(pInput As %RegisteredObject, Output pOutput As %RegisteredObject) As %Status
{{
    Set tSC = ..SendRequestAsync(..TargetConfigName, pInput)
    Quit tSC
}}
}}"""
        
        # Create the service class
        await self.session.call_tool("execute_sql", {
            "query": f"do ##class(%%Compiler.UDL.TextServices).SetTextFromString(\"{service_class}\",\"{service_definition}\")"
        })
        
        # Add the service to the production
        update_prod = await self.session.call_tool("execute_sql", {
            "query": f"""
            set prod = ##class({self.production_name}).%New()
            set item = ##class(Ens.Config.Item).%New()
            set item.ClassName = \"{service_class}\"
            set item.Name = \"{self.service_name}\"
            do prod.Items.Insert(item)
            set sc = prod.%Save()
            write $System.Status.GetErrorText(sc)
            """
        })
        
        print(f"  Business service '{self.service_name}' added to production")

    async def enable_production(self):
        """Enable the production"""
        print(f"\n🚀 Starting production")
        
        # Start the production
        result = await self.session.call_tool("execute_sql", {
            "query": f"set sc = ##class(Ens.Director).StartProduction(\"{self.production_name}\")"
        })
        
        # Check production status
        status = await self.session.call_tool("execute_sql", {
            "query": "select Status, State from Ens_Config.Production"
        })
        
        print(f"  Production status: {status}")

    async def run(self):
        """Run the setup process"""
        try:
            await self.connect_to_server()
            await self.session.set_logging_level("debug")
            await self.create_namespace_if_not_exists()
            await self.create_production_class()
            await self.add_business_service()
            await self.enable_production()
            print("\n✅ Setup completed successfully!")
        except Exception as e:
            print(f"\n❌ Error during setup: {str(e)}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    manager = MCPProductionManager()
    await manager.run()

if __name__ == "__main__":
    asyncio.run(main())
