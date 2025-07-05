import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

async def add_adt_components():
    """Add HL7 file reader and MLLP receiver services to ADT production"""
    async with AsyncExitStack() as exit_stack:
        # Connect to the MCP server
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
        
        # Set up the client connection
        stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        
        # Create a session
        session = await exit_stack.enter_async_context(ClientSession(stdio, write))
        await session.initialize()
        
        # Set log level to debug for more detailed output
        await session.set_logging_level("debug")
        
        # Production name
        production_name = "Demo.ADTProduction"
        
        try:
            # 1. Create necessary directories first
            print("\nCreating necessary directories...")
            mkdir_sql = """
            DO ##class(%File).CreateDirectory("/usr/irissys/mgr/HL7/In")
            DO ##class(%File).CreateDirectory("/usr/irissys/mgr/HL7/Out")
            DO ##class(%File).CreateDirectory("/usr/irissys/mgr/HL7/Archive")
            """
            mkdir_result = await session.call_tool(
                "execute_sql",
                {"query": mkdir_sql}
            )
            
            # 2. Add HL7 File Service
            print("\nAdding HL7 File Service...")
            file_service_sql = """
            INSERT INTO Ens_Config.Item(
                Name, ClassName, Production, Enabled, PoolSize, 
                Comment, Foreground, 
                Settings
            ) VALUES (
                'HL7FileService', 'EnsLib.HL7.Service.FileService', 'Demo.ADTProduction', 1, 1,
                'HL7 File Service to read ADT messages from files', 1,
                'FilePath=/usr/irissys/mgr/HL7/In,FileSpec=*.hl7,ArchivePath=/usr/irissys/mgr/HL7/Archive'
            )
            """
            
            file_service_result = await session.call_tool(
                "execute_sql",
                {"query": file_service_sql}
            )
            print(f"File Service added: {file_service_result.content}")
            
            # 3. Add HL7 MLLP Service for Cerner
            print("\nAdding HL7 MLLP Service for Cerner...")
            mllp_service_sql = """
            INSERT INTO Ens_Config.Item(
                Name, ClassName, Production, Enabled, PoolSize, 
                Comment, Foreground, 
                Settings
            ) VALUES (
                'CernerHL7Service', 'EnsLib.HL7.Service.TCPService', 'Demo.ADTProduction', 1, 5,
                'HL7 MLLP Service to receive ADT messages from Cerner', 1,
                'Port=5000,MessageSchemaCategory=2.3.1,DefCharEncoding=Latin1,TargetConfigNames=HL7FileOperation'
            )
            """
            
            mllp_service_result = await session.call_tool(
                "execute_sql",
                {"query": mllp_service_sql}
            )
            print(f"MLLP Service added: {mllp_service_result.content}")
            
            # 4. Add a simple file operation to handle the messages
            print("\nAdding File Operation...")
            file_op_sql = """
            INSERT INTO Ens_Config.Item(
                Name, ClassName, Production, Enabled, PoolSize, 
                Comment, Foreground,
                Settings
            ) VALUES (
                'HL7FileOperation', 'EnsLib.HL7.Operation.FileOperation', 'Demo.ADTProduction', 1, 1,
                'Operation to write HL7 messages to file', 1,
                'FilePath=/usr/irissys/mgr/HL7/Out,FileSpec=ADT_%Q_%U_%P.hl7'
            )
            """
            
            file_op_result = await session.call_tool(
                "execute_sql",
                {"query": file_op_sql}
            )
            print(f"File Operation added: {file_op_result.content}")
            
            # 4. Update the production
            print("\nUpdating production configuration...")
            update_result = await session.call_tool(
                "interoperability_production_update",
                {}
            )
            print(f"Production update result: {update_result.content}")
            
            # 5. Restart the production to apply changes
            print("\nRestarting production...")
            restart_result = await session.call_tool(
                "interoperability_production_stop",
                {}
            )
            print(f"Stop result: {restart_result.content}")
            
            start_result = await session.call_tool(
                "interoperability_production_start",
                {}
            )
            print(f"Start result: {start_result.content}")
            
            # 6. Verify the production status
            print("\nVerifying production status...")
            status_result = await session.call_tool(
                "interoperability_production_status",
                {"name": production_name, "full_status": True}
            )
            print(f"Production status: {status_result.content}")
            
        except Exception as e:
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(add_adt_components())
