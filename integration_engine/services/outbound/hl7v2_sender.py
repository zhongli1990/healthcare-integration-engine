import asyncio
import logging
import socket
from typing import Dict, Optional, Tuple, Any

from core.models.message import MessageEnvelope
from core.queues.queue_manager import QueueConfig
from core.services.outbound.base_sender import BaseOutboundSender

logger = logging.getLogger(__name__)

# MLLP protocol constants
START_BLOCK = 0x0B  # 11, VT (vertical tab)
END_BLOCK = 0x1C    # 28, file separator
CARRIAGE_RETURN = 0x0D  # 13, \r


class HL7v2Sender(BaseOutboundSender):
    """
    Sends HL7 v2.x messages to an MLLP (Minimal Lower Layer Protocol) server.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        input_queue: str = "outbound_hl7v2_messages",
        error_queue: str = "outbound_hl7v2_errors",
        reconnect_interval: int = 5,
        timeout: int = 30,
        **kwargs
    ):
        """
        Initialize the HL7 v2.x sender.
        
        Args:
            host: The hostname or IP address of the MLLP server
            port: The port number of the MLLP server
            input_queue: The name of the input queue to consume messages from
            error_queue: The name of the error queue for failed messages
            reconnect_interval: Seconds to wait between reconnection attempts
            timeout: Socket timeout in seconds
            **kwargs: Additional keyword arguments for BaseOutboundSender
        """
        super().__init__(
            name=f"hl7v2_sender_{host}:{port}",
            input_queue=input_queue,
            error_queue=error_queue,
            **kwargs
        )
        self.host = host
        self.port = port
        self.reconnect_interval = reconnect_interval
        self.timeout = timeout
        self._reader = None
        self._writer = None
        self._lock = asyncio.Lock()
    
    async def on_start(self) -> None:
        """Initialize the sender service and connect to the MLLP server."""
        await super().on_start()
        
        # Start the connection manager
        self.create_task(self._manage_connection())
    
    async def _manage_connection(self) -> None:
        """Manage the connection to the MLLP server."""
        while self.running:
            try:
                if self._writer is None or self._writer.is_closing():
                    logger.info(f"Connecting to MLLP server at {self.host}:{self.port}")
                    
                    async with self._lock:
                        # Close existing connection if any
                        if self._writer is not None:
                            self._writer.close()
                            await self._writer.wait_closed()
                        
                        # Create new connection
                        try:
                            self._reader, self._writer = await asyncio.wait_for(
                                asyncio.open_connection(self.host, self.port),
                                timeout=10
                            )
                            logger.info(f"Connected to MLLP server at {self.host}:{self.port}")
                        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                            logger.error(f"Failed to connect to MLLP server: {e}")
                            self._reader = None
                            self._writer = None
                
                # Wait before next connection check
                await asyncio.sleep(self.reconnect_interval)
                
            except asyncio.CancelledError:
                logger.info("Connection manager cancelled")
                break
            except Exception as e:
                logger.exception("Error in connection manager")
                await asyncio.sleep(self.reconnect_interval)
    
    async def on_stop(self) -> None:
        """Clean up resources."""
        await super().on_stop()
        
        # Close the connection
        if self._writer is not None:
            self._writer.close()
            await self._writer.wait_closed()
    
    async def send_message(self, message: MessageEnvelope) -> Tuple[bool, Optional[str]]:
        """
        Send an HL7 v2.x message to the MLLP server.
        
        Args:
            message: The message to send
            
        Returns:
            A tuple of (success, error_message)
        """
        if not message.body.content:
            return False, "Message has no content"
        
        # Convert message content to bytes if it's not already
        if isinstance(message.body.content, dict):
            # If it's a parsed HL7 message, convert back to ER7 format
            hl7_message = self._dict_to_er7(message.body.content)
        elif isinstance(message.body.content, str):
            hl7_message = message.body.content
        else:
            return False, f"Unsupported message content type: {type(message.body.content).__name__}"
        
        # Ensure the message ends with a segment terminator
        if not hl7_message.endswith("\r"):
            hl7_message = hl7_message.rstrip("\n\r") + "\r"
        
        # Convert to bytes if needed
        if isinstance(hl7_message, str):
            hl7_bytes = hl7_message.encode('utf-8')
        else:
            hl7_bytes = hl7_message
        
        # Wrap in MLLP envelope
        mllp_message = bytearray()
        mllp_message.append(START_BLOCK)
        mllp_message.extend(hl7_bytes)
        mllp_message.append(END_BLOCK)
        mllp_message.append(CARRIAGE_RETURN)
        
        # Send the message
        try:
            if self._writer is None or self._writer.is_closing():
                return False, "Not connected to MLLP server"
            
            async with self._lock:
                if self._writer is None or self._writer.is_closing():
                    return False, "Connection lost while trying to send message"
                
                try:
                    # Set a write timeout
                    self._writer.transport.set_write_buffer_limits(high=0)
                    self._writer.transport.set_write_buffer_limits(high=65536)  # 64KB
                    
                    # Send the message
                    self._writer.write(bytes(mllp_message))
                    await asyncio.wait_for(self._writer.drain(), timeout=self.timeout)
                    
                    # Read the ACK/NAK response
                    ack = await asyncio.wait_for(
                        self._read_mllp_message(),
                        timeout=self.timeout
                    )
                    
                    # Check if it's an ACK or NAK
                    if not ack:
                        return False, "No response from server"
                    
                    # Parse the ACK/NAK
                    ack_lines = ack.decode('utf-8').split('\r')
                    if len(ack_lines) < 2:
                        return False, f"Invalid ACK/NAK format: {ack_lines}"
                    
                    msh_segment = ack_lines[0]
                    msa_segment = ack_lines[1] if len(ack_lines) > 1 else ""
                    
                    if not msa_segment.startswith("MSA"):
                        return False, f"Invalid MSA segment in response: {msa_segment}"
                    
                    msa_fields = msa_segment.split('|')
                    if len(msa_fields) < 2:
                        return False, f"Invalid MSA segment format: {msa_segment}"
                    
                    ack_code = msa_fields[1]
                    if ack_code == "AA" or ack_code == "CA":
                        # Application Accept / Application Accept with Commit
                        logger.debug(f"Message {message.header.message_id} acknowledged")
                        return True, None
                    else:
                        # Application Reject / Application Error
                        error_text = msa_fields[3] if len(msa_fields) > 3 else "Unknown error"
                        return False, f"Server rejected message: {error_text}"
                    
                except asyncio.TimeoutError:
                    return False, "Timeout waiting for ACK/NAK"
                except Exception as e:
                    return False, f"Error sending/receiving message: {str(e)}"
        
        except Exception as e:
            logger.exception("Error in send_message")
            return False, f"Failed to send message: {str(e)}"
    
    async def _read_mllp_message(self) -> bytes:
        """Read an MLLP message from the socket."""
        if self._reader is None:
            return b""
        
        try:
            # Read until we get the start block
            start_block = await self._reader.readexactly(1)
            if not start_block or start_block[0] != START_BLOCK:
                return b""
            
            # Read until we get the end block
            message = bytearray()
            while True:
                chunk = await self._reader.readexactly(1)
                if not chunk:
                    return b""
                
                if chunk[0] == END_BLOCK:
                    # Check for carriage return after end block
                    cr = await self._reader.readexactly(1)
                    if cr and cr[0] == CARRIAGE_RETURN:
                        return bytes(message)
                    else:
                        return b""
                else:
                    message.extend(chunk)
                
        except asyncio.IncompleteReadError:
            return b""
        except Exception:
            return b""
    
    def _dict_to_er7(self, message_dict: Dict[str, Any]) -> str:
        """
        Convert a dictionary representation of an HL7 message back to ER7 format.
        
        This is a simplified implementation. In a real application, you would want to use
        a proper HL7 library for this conversion.
        """
        segments = []
        
        # Get all segments in order
        for key, value in message_dict.items():
            if key.startswith("MSH"):
                segments.insert(0, (key, value))  # MSH should be first
            else:
                segments.append((key, value))
        
        # Convert each segment to ER7 format
        er7_segments = []
        for segment_name, fields in segments:
            if not fields:
                continue
                
            if not isinstance(fields, (list, tuple)):
                fields = [fields]
            
            segment_parts = [segment_name]
            
            for field in fields:
                if field is None:
                    segment_parts.append("")
                elif isinstance(field, (list, tuple)):
                    # Handle components
                    components = []
                    for component in field:
                        if component is None:
                            components.append("")
                        elif isinstance(component, (list, tuple)):
                            # Handle subcomponents
                            subcomponents = []
                            for subcomponent in component:
                                subcomponents.append(str(subcomponent) if subcomponent is not None else "")
                            components.append("^".join(subcomponents))
                        else:
                            components.append(str(component) if component is not None else "")
                    segment_parts.append("^".join(components))
                else:
                    segment_parts.append(str(field) if field is not None else "")
            
            er7_segments.append("|".join(segment_parts))
        
        # Join segments with CRLF
        return "\r\n".join(er7_segments) + "\r"
