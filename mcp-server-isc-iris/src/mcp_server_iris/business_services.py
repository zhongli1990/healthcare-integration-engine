from typing import Dict, Any, Optional
from mcp_server_iris.mcpserver import Context
from mcp_server_iris.tools import transaction, raise_on_error
from iris import IRISReference
import logging

logger = logging.getLogger(__name__)

def init(server, logger):
    @server.tool(description="Add a File Reader business service to a production")
    async def add_file_reader_service(
        ctx: Context,
        production_name: str,
        service_name: str,
        file_path: str = "/tmp/epr_inbound/in",
        file_spec: str = "*.hl7",
        target_config_names: str = "HL7Router",
        archive_path: str = "/tmp/epr_inbound/archive",
        error_path: str = "/tmp/epr_inbound/error",
        work_path: str = "/tmp/epr_inbound/work",
        enabled: bool = True,
    ) -> str:
        """
        Add a File Reader business service to an existing production.
        
        Args:
            production_name: Name of the production (e.g., "Demo.ADTProduction")
            service_name: Name for the new service (e.g., "HL7FileReader")
            file_path: Directory path to watch for files
            file_spec: File pattern to watch (default: "*.txt")
            target_config_names: Comma-separated list of target configurations
            enabled: Whether the service should be enabled (default: True)
            
        Returns:
            str: Status message indicating success or failure
        """
        iris = ctx.iris
        logger.info(f"Adding File Reader service '{service_name}' to production '{production_name}'")
        
        try:
            with transaction(iris):
                # 1. Open the production
                prod = iris.classMethodObject("Ens.Config.Production", "%OpenId", production_name)
                if not prod:
                    raise ValueError(f"Production '{production_name}' not found")
                
                # 2. Create a new production item
                item = iris.classMethodObject("Ens.Config.Item", "%New")
                item.set("Name", service_name)
                item.set("ClassName", "EnsLib.HL7.Service.FileService")
                item.set("Enabled", enabled)
                
                # 3. Set the production item properties
                settings = iris.classMethodObject("%Library.ListOfDataTypes", "%New")
                
                # Add FilePath setting
                path_setting = iris.classMethodObject("Ens.Config.Setting", "%New")
                path_setting.set("Name", "FilePath")
                path_setting.set("Value", file_path)
                settings.invokeVoid("Insert", path_setting)
                
                # Add FileSpec setting
                spec_setting = iris.classMethodObject("Ens.Config.Setting", "%New")
                spec_setting.set("Name", "FileSpec")
                spec_setting.set("Value", file_spec)
                settings.invokeVoid("Insert", spec_setting)
                
                # Add ArchivePath setting
                archive_setting = iris.classMethodObject("Ens.Config.Setting", "%New")
                archive_setting.set("Name", "ArchivePath")
                archive_setting.set("Value", archive_path)
                settings.invokeVoid("Insert", archive_setting)
                
                # Add ErrorPath setting
                error_setting = iris.classMethodObject("Ens.Config.Setting", "%New")
                error_setting.set("Name", "ErrorPath")
                error_setting.set("Value", error_path)
                settings.invokeVoid("Insert", error_setting)
                
                # Add WorkPath setting
                work_setting = iris.classMethodObject("Ens.Config.Setting", "%New")
                work_setting.set("Name", "WorkPath")
                work_setting.set("Value", work_path)
                settings.invokeVoid("Insert", work_setting)
                
                # Add TargetConfigNames
                target_setting = iris.classMethodObject("Ens.Config.Setting", "%New")
                target_setting.set("Name", "TargetConfigNames")
                target_setting.set("Value", target_config_names)
                settings.invokeVoid("Insert", target_setting)
                
                # Add settings to the item
                item.set("Settings", settings)
                
                # 4. Add the item to the production
                items = prod.get("Items")
                items.invokeVoid("Insert", item)
                
                # 5. Save the production
                status = prod.invokeString("SaveToClass")
                if status != "1":
                    raise ValueError(f"Failed to save production: {status}")
                
                # 6. Compile the production
                status = iris.classMethodString("%SYSTEM.OBJ", "Compile", production_name, "ck-d")
                if status != "1":
                    raise ValueError(f"Failed to compile production: {status}")
                
                return f"Successfully added File Reader service '{service_name}' to production '{production_name}'"
                
        except Exception as e:
            logger.error(f"Error adding File Reader service: {str(e)}")
            raise ValueError(f"Failed to add File Reader service: {str(e)}")
    
    @server.tool(description="Add an MLLP Receiver business service to a production")
    async def add_mllp_receiver_service(
        ctx: Context,
        production_name: str,
        service_name: str,
        port: int,
        target_config_names: str = "",
        message_schema_category: str = "2.3.1",
        framing: str = "MLLP",
        enabled: bool = True,
    ) -> str:
        """
        Add an MLLP Receiver business service to an existing production.
        
        Args:
            production_name: Name of the production (e.g., "Demo.ADTProduction")
            service_name: Name for the new service (e.g., "HL7MLLPReceiver")
            port: TCP port to listen on (e.g., 8777)
            target_config_names: Comma-separated list of target configurations
            message_schema_category: HL7 message schema version (default: "2.3.1")
            framing: Message framing (default: "MLLP")
            enabled: Whether the service should be enabled (default: True)
            
        Returns:
            str: Status message indicating success or failure
        """
        iris = ctx.iris
        logger.info(f"Adding MLLP Receiver service '{service_name}' to production '{production_name}'")
        
        try:
            with transaction(iris):
                # 1. Open the production
                prod = iris.classMethodObject("Ens.Config.Production", "%OpenId", production_name)
                if not prod:
                    raise ValueError(f"Production '{production_name}' not found")
                
                # 2. Create a new production item
                item = iris.classMethodObject("Ens.Config.Item", "%New")
                item.set("Name", service_name)
                item.set("ClassName", "EnsLib.HL7.Service.TCPService")
                item.set("Enabled", enabled)
                
                # 3. Configure settings
                settings = iris.classMethodObject("%Library.ListOfDataTypes", "%New")
                
                # Add Port setting
                port_setting = iris.classMethodObject("Ens.Config.Setting", "%New")
                port_setting.set("Name", "Port")
                port_setting.set("Value", str(port))
                settings.invokeVoid("Insert", port_setting)
                
                # Add Message Schema Category
                schema_setting = iris.classMethodObject("Ens.Config.Setting", "%New")
                schema_setting.set("Name", "MessageSchemaCategory")
                schema_setting.set("Value", message_schema_category)
                settings.invokeVoid("Insert", schema_setting)
                
                # Add Framing
                framing_setting = iris.classMethodObject("Ens.Config.Setting", "%New")
                framing_setting.set("Name", "Framing")
                framing_setting.set("Value", framing)
                settings.invokeVoid("Insert", framing_setting)
                
                # Add TargetConfigNames if provided
                if target_config_names:
                    target_setting = iris.classMethodObject("Ens.Config.Setting", "%New")
                    target_setting.set("Name", "TargetConfigNames")
                    target_setting.set("Value", target_config_names)
                    settings.invokeVoid("Insert", target_setting)
                
                # Add settings to the item
                item.set("Settings", settings)
                
                # 4. Add the item to the production
                items = prod.get("Items")
                items.invokeVoid("Insert", item)
                
                # 5. Save the production
                status = item.invokeString("SaveToClass")
                if status != "1":
                    raise ValueError(f"Failed to save item: {status}")
                
                # 6. Compile the production
                status = iris.classMethodString("%SYSTEM.OBJ", "Compile", production_name, "ck-d")
                if status != "1":
                    raise ValueError(f"Failed to compile production: {status}")
                
                return f"Successfully added MLLP Receiver service '{service_name}' to production '{production_name}'"
                
        except Exception as e:
            logger.error(f"Error adding MLLP Receiver service: {str(e)}")
            raise ValueError(f"Failed to add MLLP Receiver service: {str(e)}")
    
    # Add more business service creation tools here as needed
    # For example: add_rest_service, etc.
