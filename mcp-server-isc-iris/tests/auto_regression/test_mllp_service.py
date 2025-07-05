import asyncio
import socket
import time
from contextlib import AsyncExitStack
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
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
                "IRIS_PASSWORD": "SYS",
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
        print("✅ Connected to MCP server")

    async def start_production(self, production_name: str):
        print(f"\n🚀 Starting production '{production_name}'...")
        try:
            result = await self.session.call_tool(
                "interoperability_production_start",
                {"name": production_name}
            )
            print(f"✅ {result.content[0].text}")
            return True
        except Exception as e:
            print(f"❌ Error starting production: {str(e)}")
            return False

    async def stop_production(self, production_name: str):
        print(f"\n🛑 Stopping production '{production_name}'...")
        try:
            result = await self.session.call_tool(
                "interoperability_production_stop",
                {"name": production_name}
            )
            print(f"✅ {result.content[0].text}")
            return True
        except Exception as e:
            print(f"❌ Error stopping production: {str(e)}")
            return False

    async def get_production_status(self, production_name: str):
        try:
            result = await self.session.call_tool(
                "interoperability_production_status",
                {"name": production_name, "full_status": True}
            )
            return result.content[0].text
        except Exception as e:
            print(f"❌ Error getting status: {str(e)}")
            return None
            
    async def get_production_logs(self, production_name: str, limit: int = 10):
        try:
            result = await self.session.call_tool(
                "interoperability_production_logs",
                {"name": production_name, "limit": limit}
            )
            return result.content[0].text
        except Exception as e:
            print(f"❌ Error getting logs: {str(e)}")
            return None

    async def cleanup(self):
        await self.exit_stack.aclose()

def create_hl7_message():
    """Create a sample ADT^A01 HL7 message"""
    return (
        "MSH|^~\\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEVING_FACILITY|"
        "20230705000000||ADT^A01|MSG00001|P|2.3.1\r"
        "EVN|A01|20230705000000|||SENDER_ID^SENDER^NAME^MD^^^L|20230705000000\r"
        "PID|1||12345||Doe^John^A^^Mr.||19700101|M||2106-3|123 MAIN ST^^ANYTOWN^CA^12345^USA\r"
        "PV1|1|O|CLINIC^CLINIC^1^1^^^1|U|||||12345^Doe^John^A^^MD|67890^Smith^Jane^B^^MD|"
        "|||||||||12345^Doe^John^A^^MD|1234567|1234567890|||||||||||||||||||||||||20230705000000\r"
    )

def send_hl7_message(host: str, port: int, message: str) -> str:
    """Send an HL7 message over MLLP to the specified host and port"""
    # MLLP framing characters
    START_BLOCK = '\x0b'  # VT (vertical tab)
    END_BLOCK = '\x1c'    # File separator
    CARRIAGE_RETURN = '\x0d'  # CR
    
    # Create the MLLP frame
    mllp_message = f"{START_BLOCK}{message}{END_BLOCK}{CARRIAGE_RETURN}"
    
    try:
        # Create a TCP/IP socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Connect to the MLLP listener
            sock.connect((host, port))
            print(f"📤 Connected to {host}:{port}")
            
            # Send the message
            print("📨 Sending HL7 message...")
            print("--- Message Start ---")
            print(message)
            print("--- Message End ---")
            
            sock.sendall(mllp_message.encode('utf-8'))
            
            # Wait for the ACK
            print("⏳ Waiting for ACK...")
            data = sock.recv(4096)
            
            # Extract the ACK message (remove MLLP framing)
            ack = data.decode('utf-8').strip()
            if ack.startswith('\x0b') and '\x1c' in ack:
                ack = ack[1:ack.index('\x1c')]
            
            print(f"📥 Received ACK:\n{ack}")
            return ack
            
    except Exception as e:
        print(f"❌ Error sending HL7 message: {str(e)}")
        raise

async def main():
    client = MCPClient()
    production_name = "Demo.ADTProduction"
    
    try:
        # Connect to MCP server
        print("🔌 Connecting to MCP server...")
        await client.connect_to_server()
        
        # Start the production
        if not await client.start_production(production_name):
            print("❌ Failed to start production")
            return
        
        # Give it a moment to start
        print("⏳ Waiting for production to start...")
        await asyncio.sleep(5)
        
        # Get production status
        status = await client.get_production_status(production_name)
        print(f"\n📊 Production Status:\n{status}")
        
        # Get production logs to check for errors
        print("\n📋 Checking production logs...")
        logs = await client.get_production_logs(production_name)
        print(f"\n📜 Production Logs:\n{logs}")
        
        # Send test HL7 message
        print("\n🧪 Sending test HL7 message...")
        host = "192.168.144.2"  # Docker container IP
        port = 8777             # MLLP service port
        
        hl7_message = create_hl7_message()
        ack = send_hl7_message(host, port, hl7_message)
        
        # Verify ACK
        if ack and "MSA|AA" in ack:
            print("✅ Success! Message was acknowledged")
        else:
            print("❌ Message was not acknowledged correctly")
        
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
    finally:
        # Stop the production
        await client.stop_production(production_name)
        await client.cleanup()
        print("\n🏁 Test completed")

if __name__ == "__main__":
    import sys
    asyncio.run(main())
