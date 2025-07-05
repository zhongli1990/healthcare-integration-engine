#!/usr/bin/env python3
"""
Setup DEMO_TIE Namespace and Create Production with Business Service - Fixed Version
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

    async def execute_sql(self, query: str, params: list = None):
        """Helper method to execute SQL queries"""
        if params is None:
            params = []
        return await self.session.call_tool("execute_sql", {"query": query, "params": params})

    async def create_namespace_if_not_exists(self):
        """Create DEMO_TIE namespace if it doesn't exist"""
        print(f"\n🔧 Checking/Creating namespace: {self.namespace}")
        
        # Check if namespace exists
        result = await self.execute_sql(
            "SELECT Name FROM %SYS.Namespace WHERE Name = ?", 
            [self.namespace]
        )
        
        # If namespace doesn't exist, create it
        if not result.content[0].text.strip():
            print(f"  Creating namespace: {self.namespace}")
            await self.execute_sql(
                f"do ##class(%%SYS.Namespace).Create(\"{self.namespace}\")"
            )
            print(f"  Namespace {self.namespace} created")
        else:
            print(f"  Namespace {self.namespace} already exists")

    async def create_production_class(self):
        """Create the production class in DEMO_TIE namespace"""
        print(f"\n🔧 Creating production class: {self.production_name}")
        
        # Switch to DEMO_TIE namespace
        await self.execute_sql(f"ZN \"{self.namespace}\"")
        
        # Create a simple production class
        class_name = self.production_name
        class_definition = f'''Class {class_name} Extends Ens.Production
{{
XData ProductionDefinition
{{
<Production Name="{class_name.split('.')[-1]}" LogGeneralTraceEvents="false">
</Production>
}}
}}'''
        
        # Create the class using ObjectScript
        create_class = f'''
        Set sc = ##class(%Dictionary.ClassDefinition).%New(\"{class_name}\")
        Set sc.Super = \"Ens.Production\"
        Set sc.ProcedureBlock = 1
        
        // Add XData block
        Set xdata = ##class(%Dictionary.XDataDefinition).%New()
        Set xdata.Name = \"ProductionDefinition\"
        Set xdata.XMLNamespace = \"http://www.intersystems.com/ProductionDefinition\"
        Do xdata.Data.WriteLine(\"<Production Name=\\\"DemoTIE\\\" LogGeneralTraceEvents=\\\"false\\\">\")
        Do xdata.Data.WriteLine(\"</Production>\")
        Do sc.XDatas.Insert(xdata)
        
        // Save the class
        Set sc = sc.%Save()
        Write $System.Status.GetErrorText(sc)
        '''
        
        # Execute the class creation
        result = await self.execute_sql(create_class)
        print(f"  Production class created: {result}")
        
        # Enable the namespace for Ensemble
        await self.execute_sql(
            f"do ##class(%%Library.EnsembleMgr).EnableNamespace(\"{self.namespace}\")"
        )
        print("  Namespace enabled for Ensemble")

    async def add_business_service(self):
        """Add a business service to the production"""
        print(f"\n🔧 Adding business service to production")
        
        # Create the business service class
        service_class = "DemoTIE.Service.FileService"
        service_definition = f'''Class {service_class} Extends Ens.BusinessService
{{
Parameter ADAPTER = "EnsLib.File.InboundAdapter";

Parameter SETTINGS = "TargetConfigName:Basic:selector?context={{##class(Ens.Config.ContextSearch).productionSettingsFind(\\"Ens.BusinessProcess\\",.cont)}},ArchivePath,FileSpec,FilePath";

Property TargetConfigName As %String(MAXLEN = 1000);

Method OnProcessInput(pInput As %RegisteredObject, Output pOutput As %RegisteredObject) As %Status
{{
    Set tSC = ..SendRequestAsync(..TargetConfigName, pInput)
    Quit tSC
}}
}}'''
        
        # Create the service class using ObjectScript
        create_service = f'''
        Set sc = ##class(%Dictionary.ClassDefinition).%New(\"{service_class}\")
        Set sc.Super = \"Ens.BusinessService\"
        Set sc.ProcedureBlock = 1
        
        // Add ADAPTER parameter
        Set param = ##class(%Dictionary.ParameterDefinition).%New()
        Set param.Name = \"ADAPTER\"
        Set param.Default = \"EnsLib.File.InboundAdapter\"
        Do sc.Parameters.Insert(param)
        
        // Add SETTINGS parameter
        Set param = ##class(%Dictionary.ParameterDefinition).%New()
        Set param.Name = \"SETTINGS\"
        Set param.Default = \"TargetConfigName:Basic:selector?context={{##class(Ens.Config.ContextSearch).productionSettingsFind(\\\\\\\"Ens.BusinessProcess\\\\\\\",.cont)}},ArchivePath,FileSpec,FilePath\"
        Do sc.Parameters.Insert(param)
        
        // Add TargetConfigName property
        Set prop = ##class(%Dictionary.PropertyDefinition).%New()
        Set prop.Name = \"TargetConfigName\"
        Set prop.Type = \"%String\"
        Set prop.Parameters.SetAt(\"1000\", \"MAXLEN\")
        Do sc.Properties.Insert(prop)
        
        // Add OnProcessInput method
        Set method = ##class(%Dictionary.MethodDefinition).%New()
        Set method.Name = \"OnProcessInput\"
        Set method.ReturnType = \"%Status\"
        Set method.FormalSpec = \"pInput:%RegisteredObject,&pOutput:%RegisteredObject\"
        Do method.Implementation.WriteLine(\"    Set tSC = ..SendRequestAsync(..TargetConfigName, pInput)\")
        Do method.Implementation.WriteLine(\"    Quit tSC\")
        Do sc.Methods.Insert(method)
        
        // Save the class
        Set sc = sc.%Save()
        Write $System.Status.GetErrorText(sc)
        '''
        
        # Execute the service class creation
        result = await self.execute_sql(create_service)
        print(f"  Service class created: {result}")
        
        # Add the service to the production
        add_service = f'''
        // Switch to the DEMO_TIE namespace
        ZN \"{self.namespace}\"
        
        // Get the production class
        Set prod = ##class({self.production_name}).%New()
        
        // Create a new production item
        Set item = ##class(Ens.Config.Item).%New()
        Set item.ClassName = \"{service_class}\"
        Set item.Name = \"{self.service_name}\"
        
        // Add the item to the production
        Do prod.Items.Insert(item)
        
        // Save the production
        Set sc = prod.%Save()
        Write $System.Status.GetErrorText(sc)
        '''
        
        result = await self.execute_sql(add_service)
        print(f"  Service added to production: {result}")

    async def enable_production(self):
        """Enable the production"""
        print(f"\n🚀 Starting production")
        
        # Start the production
        result = await self.execute_sql(
            f"set sc = ##class(Ens.Director).StartProduction(\"{self.production_name}\")"
        )
        
        # Check production status
        status = await self.execute_sql(
            f"select Status, State from Ens_Config.Production where Name = ?",
            [self.production_name.split('.')[-1]]
        )
        
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
            import traceback
            traceback.print_exc()
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
