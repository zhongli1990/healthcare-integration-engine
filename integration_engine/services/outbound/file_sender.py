import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import aiofiles
import aiofiles.os
from pydantic import BaseModel, DirectoryPath, FilePath, validator

from core.models.message import MessageEnvelope
from core.queues.queue_manager import QueueConfig
from core.services.outbound.base_sender import BaseOutboundSender

logger = logging.getLogger(__name__)


class FileOutputConfig(BaseModel):
    """Configuration for file output."""
    output_dir: Union[str, DirectoryPath]
    filename_pattern: str = "{timestamp}_{message_id}{ext}"
    timestamp_format: str = "%Y%m%d_%H%M%S"
    create_subdirs: bool = True
    mode: str = "w"  # 'w' for write, 'a' for append
    encoding: str = "utf-8"
    file_extensions: Dict[str, str] = {
        "application/json": ".json",
        "application/fhir+json": ".json",
        "application/hl7-v2+er7": ".hl7",
        "text/plain": ".txt",
        "text/csv": ".csv",
        "application/xml": ".xml"
    }
    default_extension: str = ".dat"
    
    class Config:
        extra = "forbid"
    
    @validator('output_dir')
    def validate_output_dir(cls, v):
        """Ensure the output directory exists and is writable."""
        if isinstance(v, str):
            v = Path(v)
        
        # Try to create the directory if it doesn't exist
        try:
            v.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Failed to create output directory {v}: {e}")
        
        # Check if the directory is writable
        if not os.access(v, os.W_OK):
            raise ValueError(f"Output directory is not writable: {v}")
        
        return v
    
    @validator('mode')
    def validate_mode(cls, v):
        """Validate the file mode."""
        if v not in ('w', 'a'):
            raise ValueError("Mode must be 'w' (write) or 'a' (append)")
        return v


class FileOutputOperation(BaseModel):
    """Represents a file output operation."""
    output_dir: Optional[Union[str, DirectoryPath]] = None
    filename: Optional[str] = None
    mode: Optional[str] = None
    encoding: Optional[str] = None
    append_timestamp: bool = True
    overwrite: bool = False
    
    class Config:
        extra = "forbid"


class FileSender(BaseOutboundSender):
    """
    Writes messages to files on the local filesystem.
    """
    
    def __init__(
        self,
        config: Union[Dict[str, Any], FileOutputConfig],
        input_queue: str = "outbound_file_messages",
        error_queue: str = "outbound_file_errors",
        **kwargs
    ):
        """
        Initialize the file sender.
        
        Args:
            config: Configuration for file output
            input_queue: The name of the input queue to consume messages from
            error_queue: The name of the error queue for failed messages
            **kwargs: Additional keyword arguments for BaseOutboundSender
        """
        super().__init__(
            name=f"file_sender_{id(self)}",
            input_queue=input_queue,
            error_queue=error_queue,
            **kwargs
        )
        
        # Parse config
        if isinstance(config, dict):
            self.config = FileOutputConfig(**config)
        else:
            self.config = config
        
        # Ensure output directory exists
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        # Lock for file operations
        self._file_lock = asyncio.Lock()
    
    async def send_message(self, message: MessageEnvelope) -> Tuple[bool, Optional[str]]:
        """
        Write a message to a file.
        
        Args:
            message: The message to write
            
        Returns:
            A tuple of (success, error_message)
        """
        if not message.body.content:
            return False, "Message has no content"
        
        # Get the operation from message metadata or use defaults
        operation_data = message.header.metadata.get("file_operation", {})
        operation = FileOutputOperation(**operation_data) if operation_data else FileOutputOperation()
        
        try:
            # Determine the output directory
            output_dir = Path(operation.output_dir) if operation.output_dir else self.config.output_dir
            
            # Create the output directory if it doesn't exist
            if self.config.create_subdirs:
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate the filename
            filename = await self._generate_filename(message, operation, output_dir)
            
            # Determine the file extension
            file_ext = self._get_file_extension(message, operation)
            
            # Ensure the filename has the correct extension
            if not filename.suffix and file_ext:
                filename = filename.with_suffix(file_ext)
            
            # Get the full output path
            output_path = output_dir / filename
            
            # Check if the file exists and handle accordingly
            if output_path.exists():
                if not operation.overwrite and operation.mode != 'a':
                    return False, f"File already exists and overwrite is False: {output_path}"
                
                # If appending, ensure the file is writable
                if operation.mode == 'a' and not os.access(output_path, os.W_OK):
                    return False, f"File is not writable: {output_path}"
            
            # Prepare the content to write
            content = self._prepare_content(message)
            
            # Write the file
            success, error = await self._write_file(
                path=output_path,
                content=content,
                mode=operation.mode or self.config.mode,
                encoding=operation.encoding or self.config.encoding
            )
            
            if success:
                # Update message metadata with file info
                message.header.metadata.setdefault("file_output", {
                    "path": str(output_path),
                    "filename": filename.name,
                    "directory": str(output_dir),
                    "size": len(content) if isinstance(content, (str, bytes)) else None,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                logger.info(f"Successfully wrote message to {output_path}")
                return True, None
            else:
                return False, error
                
        except Exception as e:
            logger.exception(f"Error writing message to file: {e}")
            return False, f"Error writing to file: {str(e)}"
    
    async def _generate_filename(
        self,
        message: MessageEnvelope,
        operation: FileOutputOperation,
        output_dir: Path
    ) -> Path:
        """Generate a filename for the output file."""
        if operation.filename:
            # Use the provided filename
            filename = Path(operation.filename)
            
            # If it's a relative path, make it relative to the output directory
            if not filename.is_absolute():
                filename = output_dir / filename
            
            return filename
        
        # Generate a filename using the pattern
        timestamp = datetime.utcnow().strftime(self.config.timestamp_format)
        message_id = message.header.message_id or "message"
        
        # Get the base filename from the pattern
        filename = self.config.filename_pattern.format(
            timestamp=timestamp,
            message_id=message_id,
            message_type=message.header.message_type or "",
            content_type=message.body.content_type or ""
        )
        
        return Path(filename)
    
    def _get_file_extension(
        self,
        message: MessageEnvelope,
        operation: FileOutputOperation
    ) -> str:
        """Determine the appropriate file extension."""
        # If the filename already has an extension, use it
        if operation.filename and '.' in operation.filename:
            return ""
        
        # Try to determine from content type
        if message.body.content_type:
            # Check for exact match
            if message.body.content_type in self.config.file_extensions:
                return self.config.file_extensions[message.body.content_type]
            
            # Check for partial match (e.g., application/vnd.custom+json)
            for content_type, ext in self.config.file_extensions.items():
                if content_type in message.body.content_type:
                    return ext
        
        # Default extension
        return self.config.default_extension
    
    def _prepare_content(self, message: MessageEnvelope) -> Union[str, bytes]:
        """Prepare the content for writing to a file."""
        content = message.body.content
        
        # If content is already bytes, return as is
        if isinstance(content, bytes):
            return content
        
        # Convert to string if needed
        if not isinstance(content, str):
            if message.body.content_type and 'json' in message.body.content_type:
                content = json.dumps(content, indent=2, ensure_ascii=False)
            else:
                content = str(content)
        
        # Encode to bytes if needed
        if self.config.mode == 'wb':
            return content.encode(self.config.encoding)
        
        return content
    
    async def _write_file(
        self,
        path: Path,
        content: Union[str, bytes],
        mode: str = "w",
        encoding: str = "utf-8"
    ) -> Tuple[bool, Optional[str]]:
        """
        Write content to a file.
        
        Args:
            path: Path to the file
            content: Content to write
            mode: File mode ('w', 'a', 'wb', 'ab')
            encoding: File encoding (for text modes)
            
        Returns:
            A tuple of (success, error_message)
        """
        try:
            # Ensure the directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use aiofiles for async file I/O
            async with self._file_lock:
                if 'b' in mode:
                    # Binary mode
                    async with aiofiles.open(path, mode) as f:
                        await f.write(content if isinstance(content, bytes) else content.encode(encoding))
                else:
                    # Text mode
                    async with aiofiles.open(path, mode, encoding=encoding) as f:
                        await f.write(content if isinstance(content, str) else content.decode(encoding))
            
            return True, None
            
        except Exception as e:
            logger.exception(f"Error writing to file {path}")
            return False, f"Failed to write to file: {str(e)}"
