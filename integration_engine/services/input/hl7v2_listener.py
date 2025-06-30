import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple, Union

import aiofiles
import aiofiles.os
import paramiko
from pydantic import BaseModel, Field

from integration_engine.core.models.message import MessageEnvelope, MessageHeader, MessageBody
from integration_engine.core.queues.queue_manager import QueueManager, QueueConfig
from integration_engine.core.services.base_service import BaseService

logger = logging.getLogger(__name__)


class MLLPConfig(BaseModel):
    """Configuration for MLLP listener."""
    host: str = "0.0.0.0"
    port: int = 2575
    buffer_size: int = 4096
    start_block: bytes = b"\x0B"  # VT (vertical tab)
    end_block: bytes = b"\x1C\r"  # FS (file separator) + CR
    
    class Config:
        extra = "forbid"


class FileWatcherConfig(BaseModel):
    """Configuration for file watcher."""
    input_dir: str = "./input/hl7v2"
    processed_dir: str = "./processed/hl7v2"
    file_pattern: str = "*.hl7"
    poll_interval: float = 1.0
    
    class Config:
        extra = "forbid"


class SFTPConfig(BaseModel):
    """Configuration for SFTP client."""
    host: str = "localhost"
    port: int = 22
    username: str = "user"
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    remote_path: str = "/incoming/hl7v2"
    local_path: str = "./sftp/hl7v2"
    poll_interval: float = 60.0
    file_pattern: str = "*.hl7"
    
    class Config:
        extra = "forbid"


class HL7v2ListenerService(BaseService):
    """Service for receiving HL7 v2.x messages from various sources."""
    
    def __init__(
        self,
        queue_manager: QueueManager,
        output_queue: str = "raw_messages",
        mllp_config: Optional[Dict[str, Any]] = None,
        file_watcher_config: Optional[Dict[str, Any]] = None,
        sftp_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(name="hl7v2_listener", **kwargs)
        
        # Initialize queue manager
        self.queue_manager = queue_manager
        
        # Initialize configurations
        self.mllp_config = MLLPConfig(**(mllp_config or {}))
        self.file_watcher_config = FileWatcherConfig(**(file_watcher_config or {}))
        self.sftp_config = SFTPConfig(**(sftp_config or {}))
        
        self.output_queue_name = output_queue
        self.output_queue = None
        
        # Track processed files for file watcher and SFTP
        self._processed_files: Set[str] = set()
        self._sftp_client = None
    
    async def on_start(self) -> None:
        """Start the HL7 v2 listener service."""
        try:
            # Create output queue
            logger.info(f"Initializing output queue: {self.output_queue_name}")
            self.output_queue = await self.queue_manager.get_queue(
                self.output_queue_name
            )
            logger.info(f"Successfully initialized output queue: {self.output_queue_name}")
            
            # Start all enabled listeners
            tasks = []
            
            # Start MLLP listener if enabled
            if self.config.get("enable_mllp", True):
                logger.info("Starting MLLP listener")
                tasks.append(self._start_mllp_listener())
            
            # Start file watcher if enabled
            if self.config.get("enable_file_watcher", False):
                logger.info("Starting file watcher")
                tasks.append(self._start_file_watcher())
            
            # Start SFTP client if enabled
            if self.config.get("enable_sftp", False):
                logger.info("Starting SFTP client")
                tasks.append(self._start_sftp_client())
            
            if not tasks:
                logger.warning("No HL7 v2 listeners enabled in configuration")
            else:
                for task in tasks:
                    logger.debug(f"Creating task: {task}")
                    self.create_task(task)
                    
        except Exception as e:
            logger.error(f"Failed to start HL7v2ListenerService: {e}")
            raise
    
    async def _start_mllp_listener(self) -> None:
        """Start the MLLP listener server."""
        server = await asyncio.start_server(
            self._handle_mllp_connection,
            host=self.mllp_config.host,
            port=self.mllp_config.port
        )
        
        addr = server.sockets[0].getsockname()
        logger.info(f"HL7 MLLP listener serving on {addr}")
        
        async with server:
            await server.serve_forever()
    
    async def _handle_mllp_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle an incoming MLLP connection."""
        addr = writer.get_extra_info('peername')
        logger.info(f"New MLLP connection from {addr}")
        
        try:
            while True:
                # Read until start block
                start_block = await reader.readuntil(self.mllp_config.start_block)
                if not start_block:
                    break
                
                # Read message content
                message_data = await reader.readuntil(self.mllp_config.end_block)
                if not message_data:
                    logger.warning("Unexpected end of message")
                    break
                
                # Remove end block
                message_data = message_data[:-len(self.mllp_config.end_block)]
                
                # Process the HL7 message
                try:
                    await self._process_hl7_message(message_data, source=f"mllp://{addr[0]}:{addr[1]}")
                    # Send ACK
                    ack_msg = b"MSH|^~\\&|ACK|||||ACK^A01|00001|P|2.5.1\rMSA|AA|00001\r"
                    writer.write(self.mllp_config.start_block + ack_msg + self.mllp_config.end_block)
                    await writer.drain()
                except Exception as e:
                    logger.error(f"Error processing HL7 message: {e}")
                    # Send NAK
                    writer.write(b"\x15")  # NAK character
                    await writer.drain()
        
        except (asyncio.IncompleteReadError, ConnectionResetError):
            logger.info(f"Connection closed by {addr}")
        except Exception as e:
            logger.error(f"Error in MLLP connection: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def _start_file_watcher(self) -> None:
        """Start watching a directory for new HL7 files."""
        # Create directories if they don't exist
        input_dir = Path(self.file_watcher_config.input_dir)
        processed_dir = Path(self.file_watcher_config.processed_dir)
        
        input_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Watching directory for HL7 files: {input_dir}")
        
        while not self._stop_event.is_set():
            try:
                # Scan for new files
                for file_path in input_dir.glob(self.file_watcher_config.file_pattern):
                    if str(file_path) in self._processed_files:
                        continue
                    
                    try:
                        # Read file content
                        async with aiofiles.open(file_path, 'rb') as f:
                            content = await f.read()
                        
                        # Process the HL7 message
                        await self._process_hl7_message(
                            content,
                            source=f"file://{file_path}",
                            file_path=file_path,
                            processed_dir=processed_dir
                        )
                        
                        # Mark as processed
                        self._processed_files.add(str(file_path))
                        
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {e}")
                
                # Clean up processed files
                await self._cleanup_processed_files()
                
            except Exception as e:
                logger.error(f"Error in file watcher: {e}")
            
            # Wait before next poll
            await asyncio.sleep(self.file_watcher_config.poll_interval)
    
    async def _start_sftp_client(self) -> None:
        """Start the SFTP client to download HL7 files."""
        # Create local directory if it doesn't exist
        local_path = Path(self.sftp_config.local_path)
        local_path.mkdir(parents=True, exist_ok=True)
        
        # Connect to SFTP server
        transport = paramiko.Transport((self.sftp_config.host, self.sftp_config.port))
        
        try:
            if self.sftp_config.private_key_path:
                private_key = paramiko.RSAKey.from_private_key_file(self.sftp_config.private_key_path)
                transport.connect(username=self.sftp_config.username, pkey=private_key)
            else:
                transport.connect(username=self.sftp_config.username, password=self.sftp_config.password)
            
            sftp = transport.open_sftp()
            self._sftp_client = sftp
            
            logger.info(f"Connected to SFTP server {self.sftp_config.host}:{self.sftp_config.port}")
            
            while not self._stop_event.is_set():
                try:
                    # List remote files
                    remote_files = sftp.listdir_attr(self.sftp_config.remote_path)
                    
                    for file_attr in remote_files:
                        if file_attr.filename in self._processed_files:
                            continue
                        
                        if not file_attr.filename.endswith('.hl7'):
                            continue
                        
                        remote_file = f"{self.sftp_config.remote_path}/{file_attr.filename}"
                        local_file = local_path / file_attr.filename
                        
                        try:
                            # Download file
                            sftp.get(remote_file, str(local_file))
                            
                            # Read file content
                            async with aiofiles.open(local_file, 'rb') as f:
                                content = await f.read()
                            
                            # Process the HL7 message
                            await self._process_hl7_message(
                                content,
                                source=f"sftp://{self.sftp_config.host}{remote_file}",
                                file_path=local_file,
                                delete_after_process=True
                            )
                            
                            # Mark as processed
                            self._processed_files.add(file_attr.filename)
                            
                            # Delete remote file if configured
                            if self.sftp_config.get('delete_after_download', True):
                                sftp.remove(remote_file)
                            
                        except Exception as e:
                            logger.error(f"Error processing SFTP file {file_attr.filename}: {e}")
                    
                    # Clean up processed files
                    await self._cleanup_processed_files()
                    
                except Exception as e:
                    logger.error(f"Error in SFTP client: {e}")
                
                # Wait before next poll
                await asyncio.sleep(self.sftp_config.poll_interval)
                
        except Exception as e:
            logger.error(f"SFTP connection error: {e}")
            raise
        finally:
            if hasattr(self, '_sftp_client') and self._sftp_client:
                self._sftp_client.close()
            transport.close()
    
    async def _process_hl7_message(
        self,
        content: bytes,
        source: str,
        file_path: Optional[Union[str, Path]] = None,
        processed_dir: Optional[Union[str, Path]] = None,
        delete_after_process: bool = False
    ) -> None:
        """Process an HL7 message and send it to the output queue."""
        try:
            # Ensure output queue is initialized
            if self.output_queue is None:
                logger.warning("Output queue not initialized, attempting to initialize now")
                try:
                    self.output_queue = await self.queue_manager.get_queue(self.output_queue_name)
                    logger.info(f"Successfully initialized output queue: {self.output_queue_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize output queue: {e}")
                    raise RuntimeError(f"Output queue {self.output_queue_name} is not available") from e

            # Extract message type (MSH-9)
            lines = content.decode('utf-8', errors='replace').split('\r')
            msh_segment = next((line for line in lines if line.startswith('MSH|')), None)
            
            if not msh_segment:
                raise ValueError("Invalid HL7 message: MSH segment not found")
            
            msh_fields = msh_segment.split('|')
            if len(msh_fields) < 9:
                raise ValueError("Invalid HL7 message: MSH segment too short")
            
            message_type = msh_fields[8]
            message_control_id = msh_fields[9] if len(msh_fields) > 9 else str(uuid.uuid4())
            
            # Create message envelope
            message = MessageEnvelope(
                header=MessageHeader(
                    message_id=message_control_id,
                    message_type=message_type,
                    source=source,
                    metadata={
                        "received_at": datetime.utcnow().isoformat(),
                        "content_length": len(content)
                    }
                ),
                body=MessageBody(
                    content_type="application/hl7-v2+er7",
                    raw_content=content,
                    metadata={
                        "original_filename": str(file_path) if file_path else None,
                        "source": source
                    }
                )
            )
            
            # Send to output queue
            try:
                await self.output_queue.publish(message)
                logger.info(f"Processed HL7 message {message_control_id} ({message_type}) from {source}")
            except Exception as e:
                logger.error(f"Failed to publish message {message_control_id} to queue: {e}")
                raise
            
            # Move or delete the file if needed
            if file_path and processed_dir and not delete_after_process:
                processed_file = Path(processed_dir) / f"{Path(file_path).stem}_{int(time.time())}{Path(file_path).suffix}"
                await aiofiles.os.rename(str(file_path), str(processed_file))
            elif file_path and delete_after_process:
                await aiofiles.os.remove(str(file_path))
                
        except Exception as e:
            logger.error(f"Error processing HL7 message from {source}: {e}")
            raise
    
    async def _process_file(self, file_path: Union[str, Path]) -> None:
        """Process a single HL7 file.
        
        Args:
            file_path: Path to the HL7 file to process
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return
            
        try:
            # Read file content
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
            
            # Process the HL7 message
            await self._process_hl7_message(
                content,
                source=f"file://{file_path}",
                file_path=file_path,
                processed_dir=self.file_watcher_config.processed_dir
            )
            
            # Mark as processed
            self._processed_files.add(str(file_path))
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            raise
    
    async def _cleanup_processed_files(self) -> None:
        """Clean up the set of processed files to prevent memory leaks."""
        # Keep only files that were processed recently (last hour)
        current_time = time.time()
        self._processed_files = {
            f for f in self._processed_files
            if current_time - os.path.getmtime(f) < 3600  # 1 hour
        }


# Alias for backward compatibility
HL7v2Listener = HL7v2ListenerService
