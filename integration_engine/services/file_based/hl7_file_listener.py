"""
HL7 File Listener Service

Watches a directory for new HL7 files and processes them through the integration engine.
"""
import os
import time
import logging
from pathlib import Path
from typing import Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from integration_engine.core.models.message import Message
from integration_engine.core.queues.queue_manager import QueueManager

logger = logging.getLogger(__name__)


class HL7FileHandler(FileSystemEventHandler):
    """Handle file system events for HL7 files."""
    
    def __init__(self, input_dir: Path, callback: Callable):
        """Initialize with input directory and callback function."""
        self.input_dir = input_dir
        self.callback = callback
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and event.src_path.endswith('.hl7'):
            logger.info(f"New HL7 file detected: {event.src_path}")
            self.callback(Path(event.src_path))


class HL7FileListener:
    """Listens for new HL7 files in a directory and processes them."""
    
    def __init__(self, queue_manager: QueueManager, input_dir: str, processed_dir: str):
        """Initialize the file listener.
        
        Args:
            queue_manager: Queue manager for sending messages
            input_dir: Directory to watch for new HL7 files
            processed_dir: Directory to move processed files to
        """
        self.queue_manager = queue_manager
        self.input_dir = Path(input_dir)
        self.processed_dir = Path(processed_dir)
        
        # Create directories if they don't exist
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        self.observer = Observer()
        self.running = False
    
    def _process_file(self, file_path: Path):
        """Process a single HL7 file."""
        try:
            # Read the file content
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Create a message
            message = Message(
                message_type="HL7v2",
                content=content,
                metadata={
                    "source_file": str(file_path.name),
                    "received_at": time.time()
                }
            )
            
            # Send to processing queue
            self.queue_manager.publish("hl7.inbound", message.to_dict())
            
            # Move to processed directory
            processed_path = self.processed_dir / file_path.name
            file_path.rename(processed_path)
            logger.info(f"Processed and moved {file_path} to {processed_path}")
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    def start(self):
        """Start watching the input directory."""
        if self.running:
            logger.warning("HL7 file listener is already running")
            return
        
        # Process any existing files
        for file_path in self.input_dir.glob("*.hl7"):
            self._process_file(file_path)
        
        # Set up file system observer
        event_handler = HL7FileHandler(self.input_dir, self._process_file)
        self.observer.schedule(event_handler, str(self.input_dir), recursive=False)
        self.observer.start()
        self.running = True
        logger.info(f"Started watching {self.input_dir} for HL7 files")
    
    def stop(self):
        """Stop watching the input directory."""
        if not self.running:
            return
            
        self.observer.stop()
        self.observer.join()
        self.running = False
        logger.info("Stopped HL7 file listener")
