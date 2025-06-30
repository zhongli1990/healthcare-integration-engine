"""
File processing module for the Integration Engine.

This module handles watching for new files, processing them according to their type,
and moving them to the appropriate output directory.
"""

import asyncio
import logging
import shutil
import time
from pathlib import Path
from typing import Dict, Optional, Callable, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

logger = logging.getLogger(__name__)

class FileProcessor:
    """Process files in a directory and move them to an output directory."""
    
    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        archive_dir: str,
        error_dir: str,
        handlers: Optional[Dict[str, Callable]] = None
    ):
        """Initialize the file processor.
        
        Args:
            input_dir: Directory to watch for new files
            output_dir: Directory to place processed files
            archive_dir: Directory to archive processed files
            error_dir: Directory to move files that failed processing
            handlers: Dictionary mapping file extensions to handler functions
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.archive_dir = Path(archive_dir)
        self.error_dir = Path(error_dir)
        
        # Create directories if they don't exist
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.error_dir.mkdir(parents=True, exist_ok=True)
        
        # Default handlers for different file types
        self.handlers = handlers or {
            '.hl7': self._process_hl7,
            '.json': self._process_fhir_json,
            '.xml': self._process_fhir_xml,
        }
        
        # Set up file system observer
        self.observer = Observer()
        self.event_handler = FileProcessingHandler(self)
    
    def start(self) -> None:
        """Start watching the input directory for new files."""
        logger.info(f"Starting file processor. Watching: {self.input_dir}")
        self.observer.schedule(
            self.event_handler,
            str(self.input_dir),
            recursive=False
        )
        self.observer.start()
    
    def stop(self) -> None:
        """Stop watching the input directory."""
        self.observer.stop()
        self.observer.join()
        logger.info("File processor stopped")
        
    def process_existing_files(self) -> None:
        """Process all files that already exist in the input directory.
        
        This is useful for processing files that were added before the watcher started.
        """
        logger.info(f"Processing existing files in {self.input_dir}")
        for file_path in self.input_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.handlers:
                asyncio.create_task(self.process_file(file_path))
                logger.debug(f"Scheduled processing for existing file: {file_path}")
    
    async def process_file(self, file_path: Path) -> bool:
        """Process a single file.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        try:
            # Get the appropriate handler based on file extension
            handler = self.handlers.get(file_path.suffix.lower())
            if not handler:
                logger.warning(f"No handler for file type: {file_path.suffix}")
                await self._move_to_error(file_path, "Unsupported file type")
                return False
            
            # Process the file
            logger.info(f"Processing file: {file_path}")
            
            # If the handler is async, await it, otherwise call it directly
            if hasattr(handler, '__await__'):
                success = await handler(file_path)
            else:
                success = handler(file_path)
            
            if success:
                # Move to archive on success
                await self._move_to_archive(file_path)
            else:
                # Move to error on failure
                await self._move_to_error(file_path, "Processing failed")
                
            return success
            
        except Exception as e:
            logger.exception(f"Error processing file {file_path}")
            await self._move_to_error(file_path, str(e))
            return False
    
    def _parse_hl7_message(self, content: str) -> Dict:
        """Parse an HL7 v2.x message into a structured format.
        
        Args:
            content: Raw HL7 message content
            
        Returns:
            Dictionary containing parsed message segments and fields
            
        Raises:
            ValueError: If the message is not a valid HL7 message
        """
        # Basic HL7 message validation
        if not content.startswith("MSH"):
            raise ValueError("Invalid HL7 message: Must start with MSH segment")
            
        # Extract field separator (4th character of MSH segment)
        field_sep = content[3] if len(content) > 3 else '|'
        
        # Parse MSH segment (header)
        # Handle different line endings (\r\n or \n)
        segments = []
        for line in content.replace('\r\n', '\n').split('\n'):
            line = line.strip('\r')
            if line:  # Only add non-empty lines
                segments.append(line)
                
        if not segments:
            raise ValueError("No segments found in HL7 message")
            
        # The first line must be the MSH segment
        if not segments[0].startswith('MSH'):
            raise ValueError("First segment must be MSH")
            
        msh_segment = segments[0].split(field_sep)
        if len(msh_segment) < 12:
            raise ValueError("MSH segment is too short")
            
        # Extract message type and control ID
        message_type = msh_segment[8].split('^')
        control_id = msh_segment[9]
        
        # Basic message structure
        message = {
            'msh': msh_segment,
            'segments': {},
            'message_type': message_type[0] if message_type else '',
            'trigger_event': message_type[1] if len(message_type) > 1 else '',
            'message_control_id': control_id,
            'processing_id': msh_segment[10] if len(msh_segment) > 10 else '',
            'version_id': msh_segment[11] if len(msh_segment) > 11 else '2.3'  # Default to 2.3 if not specified
        }
        
        # Parse remaining segments
        for segment in segments[1:]:
            if not segment:
                continue
                
            segment_id = segment[:3]
            if segment_id not in message['segments']:
                message['segments'][segment_id] = []
                
            fields = segment[3:].split(field_sep) if len(segment) > 3 else []
            message['segments'][segment_id].append(fields)
            
        return message
    
    def _validate_hl7_message(self, message: Dict) -> List[str]:
        """Validate an HL7 message structure.
        
        Args:
            message: Parsed HL7 message
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check MSH segment (stored at top level)
        if 'msh' not in message or not message['msh']:
            errors.append("Missing required segment: MSH")
        else:
            # Check MSH segment fields
            msh = message['msh']
            if len(msh) < 12:
                errors.append("MSH segment is missing required fields")
            
            # Check message type
            if not message.get('message_type'):
                errors.append("Message type is missing or invalid")
        
        # Check other required segments (stored in message['segments'])
        required_segments = ['EVN', 'PID']
        for seg in required_segments:
            if seg not in message.get('segments', {}) or not message['segments'][seg]:
                errors.append(f"Missing required segment: {seg}")
            
        return errors
    
    def _process_hl7(self, file_path: Path) -> bool:
        """Process an HL7v2 file.
        
        Args:
            file_path: Path to the HL7 file
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            logger.info(f"Processing HL7 file: {file_path}")
            
            # Read file content
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Parse HL7 message
            message = self._parse_hl7_message(content)
            
            # Validate message structure
            errors = self._validate_hl7_message(message)
            if errors:
                logger.error(f"HL7 validation failed for {file_path}: {', '.join(errors)}")
                return False
                
            # Log message type for test verification
            logger.info(f"Message type: {message.get('message_type')}")
            
            # Log successful processing
            logger.info(f"Successfully processed HL7 message: {message.get('message_control_id')}")
            
            # Don't move the file here - let process_file handle it
            return True
            
        except Exception as e:
            logger.exception(f"Error processing HL7 file {file_path}")
            return False
    
    def _process_fhir_json(self, file_path: Path) -> bool:
        """Process a FHIR JSON file."""
        # TODO: Implement actual FHIR JSON processing
        # For now, just log and return success
        logger.info(f"Processing FHIR JSON file: {file_path}")
        return True
    
    def _process_fhir_xml(self, file_path: Path) -> bool:
        """Process a FHIR XML file."""
        # TODO: Implement actual FHIR XML processing
        # For now, just log and return success
        logger.info(f"Processing FHIR XML file: {file_path}")
        return True
    
    async def _move_to_archive(self, file_path: Path) -> None:
        """Move a file to the archive directory."""
        target = self.archive_dir / file_path.name
        if target.exists():
            # Add timestamp to filename if it already exists
            timestamp = int(time.time())
            target = self.archive_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
        
        # Use aiofiles for async file operations in the future if needed
        # For now, we'll use run_in_executor to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, shutil.move, str(file_path), str(target))
        logger.debug(f"Moved to archive: {file_path} -> {target}")
    
    async def _move_to_error(self, file_path: Path, reason: str = "") -> None:
        """Move a file to the error directory."""
        target = self.error_dir / file_path.name
        if target.exists():
            # Add timestamp to filename if it already exists
            timestamp = int(time.time())
            target = self.error_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
        
        # Use aiofiles for async file operations in the future if needed
        # For now, we'll use run_in_executor to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, shutil.move, str(file_path), str(target))
        logger.error(f"Moved to error: {file_path} -> {target} ({reason})")


class FileProcessingHandler(FileSystemEventHandler):
    """Handler for file system events."""
    
    def __init__(self, processor: 'FileProcessor'):
        self.processor = processor
    
    def on_created(self, event: FileSystemEvent) -> None:
        """Called when a file or directory is created."""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        if file_path.suffix.lower() in self.processor.handlers:
            # Small delay to ensure the file is completely written
            time.sleep(0.5)
            self.processor.process_file(file_path)
