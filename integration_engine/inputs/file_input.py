"""File-based input adapter."""
import asyncio
import logging
import os
from pathlib import Path
from typing import AsyncGenerator, Optional

from core.interfaces.input_adapter import InputAdapter
from core.models.message import MessageEnvelope, MessageHeader, MessageBody

logger = logging.getLogger(__name__)


class FileInputAdapter(InputAdapter):
    """Input adapter that reads messages from files in a directory."""

    def __init__(
        self,
        input_dir: str,
        processed_dir: str,
        error_dir: str,
        file_pattern: str = "*.hl7",
        poll_interval: float = 1.0,
    ):
        """Initialize the file input adapter.
        
        Args:
            input_dir: Directory to watch for new files
            processed_dir: Directory to move processed files to
            error_dir: Directory to move files with errors to
            file_pattern: File pattern to watch for (e.g., "*.hl7")
            poll_interval: How often to check for new files (seconds)
        """
        self.input_dir = Path(input_dir)
        self.processed_dir = Path(processed_dir)
        self.error_dir = Path(error_dir)
        self.file_pattern = file_pattern
        self.poll_interval = poll_interval
        
        # Create directories if they don't exist
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.error_dir.mkdir(parents=True, exist_ok=True)
        
        self.running = False
        self._process_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the file watcher."""
        if self.running:
            return
            
        self.running = True
        self._process_task = asyncio.create_task(self._process_files())
        logger.info(f"Started file input adapter watching {self.input_dir}")
    
    async def stop(self) -> None:
        """Stop the file watcher."""
        if not self.running:
            return
            
        self.running = False
        if self._process_task and not self._process_task.done():
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped file input adapter")
    
    async def receive(self) -> AsyncGenerator[MessageEnvelope, None]:
        """Receive messages from files.
        
        Yields:
            MessageEnvelope: Messages read from files
        """
        while self.running:
            # Get list of matching files
            files = list(self.input_dir.glob(self.file_pattern))
            
            for file_path in files:
                try:
                    # Read file content
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    # Create message envelope
                    message = MessageEnvelope(
                        header=MessageHeader(
                            source=f"file://{file_path}",
                            metadata={
                                "file_path": str(file_path),
                                "file_name": file_path.name,
                            }
                        ),
                        body=MessageBody(
                            content_type="application/hl7-v2",
                            raw_content=content,
                            metadata={
                                "file_size": len(content),
                                "file_mtime": os.path.getmtime(file_path),
                            }
                        )
                    )
                    
                    yield message
                    
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    # Move to error directory
                    await self._move_file(file_path, self.error_dir)
            
            # Wait before checking for new files
            await asyncio.sleep(self.poll_interval)
    
    async def acknowledge(self, message: MessageEnvelope) -> None:
        """Acknowledge successful processing of a file.
        
        Args:
            message: The message to acknowledge
        """
        file_path = Path(message.header.metadata.get("file_path", ""))
        if file_path.exists():
            await self._move_file(file_path, self.processed_dir)
    
    async def nacknowledge(self, message: MessageEnvelope, reason: str) -> None:
        """Handle failed processing of a file.
        
        Args:
            message: The message that failed
            reason: Reason for the failure
        """
        file_path = Path(message.header.metadata.get("file_path", ""))
        if file_path.exists():
            # Add error info to filename
            error_file = file_path.with_name(
                f"{file_path.stem}.error{file_path.suffix}"
            )
            await self._move_file(file_path, self.error_dir, error_file.name)
            
            # Log the error
            logger.error(
                f"Failed to process file {file_path.name}: {reason}"
            )
    
    async def _process_files(self) -> None:
        """Process files in the input directory."""
        try:
            async for _ in self.receive():
                pass
        except asyncio.CancelledError:
            logger.info("File processing cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in file processing: {e}")
            raise
    
    async def _move_file(
        self,
        src_path: Path,
        dest_dir: Path,
        new_name: Optional[str] = None
    ) -> None:
        """Move a file to a destination directory.
        
        Args:
            src_path: Path to the source file
            dest_dir: Destination directory
            new_name: New filename (optional)
        """
        try:
            if not src_path.exists():
                return
                
            dest_path = dest_dir / (new_name or src_path.name)
            
            # Handle filename conflicts
            counter = 1
            while dest_path.exists():
                name_parts = src_path.stem.split('.')
                if name_parts[-1].isdigit() and len(name_parts) > 1:
                    name_parts[-1] = str(int(name_parts[-1]) + 1)
                else:
                    name_parts.append(str(counter))
                
                new_stem = '.'.join(name_parts)
                dest_path = dest_dir / f"{new_stem}{src_path.suffix}"
                counter += 1
            
            # Move the file
            src_path.rename(dest_path)
            logger.debug(f"Moved {src_path} to {dest_path}")
            
        except Exception as e:
            logger.error(f"Error moving file {src_path}: {e}")
            raise
