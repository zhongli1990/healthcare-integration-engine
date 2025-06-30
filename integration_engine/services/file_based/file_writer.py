"""
File Writer Service

Writes processed messages to files in a specified output directory.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from integration_engine.core.models.message import Message
from integration_engine.core.queues.queue_manager import QueueManager

logger = logging.getLogger(__name__)


class FileWriter:
    """Writes messages to files in a specified output directory."""
    
    def __init__(self, queue_manager: QueueManager, output_dir: str):
        """Initialize the file writer.
        
        Args:
            queue_manager: Queue manager for receiving messages
            output_dir: Base directory for writing output files
        """
        self.queue_manager = queue_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different message types
        self.hl7_dir = self.output_dir / "hl7"
        self.fhir_dir = self.output_dir / "fhir"
        self.error_dir = self.output_dir / "errors"
        
        for directory in [self.hl7_dir, self.fhir_dir, self.error_dir]:
            directory.mkdir(exist_ok=True)
    
    async def start(self):
        """Start listening for messages to write to files."""
        await self.queue_manager.subscribe("file.write", self._write_message)
        logger.info("File writer service started")
    
    async def _write_message(self, message_data: Dict[str, Any]):
        """Write a message to a file.
        
        Args:
            message_data: Message data to write
        """
        try:
            message = Message.from_dict(message_data)
            
            # Determine output directory based on message type
            if message.metadata.get("error"):
                output_dir = self.error_dir
            elif message.message_type == "HL7v2":
                output_dir = self.hl7_dir
            elif message.message_type == "FHIR":
                output_dir = self.fhir_dir
            else:
                output_dir = self.output_dir
            
            # Generate filename
            source_file = message.metadata.get("source_file", "output")
            timestamp = int(message.metadata.get("processed_at", 0))
            file_ext = "hl7" if message.message_type == "HL7v2" else "json"
            filename = f"{source_file.rsplit('.', 1)[0]}_{timestamp}.{file_ext}"
            
            # Write the file
            output_path = output_dir / filename
            
            if isinstance(message.content, dict) and file_ext == "json":
                content = json.dumps(message.content, indent=2)
            else:
                content = str(message.content)
            
            with open(output_path, 'w') as f:
                f.write(content)
            
            logger.info(f"Wrote {message.message_type} message to {output_path}")
            
            # Update message with output file path
            message.metadata["output_file"] = str(output_path)
            
            # Publish to next step in pipeline if needed
            if "next_steps" in message.metadata:
                for step in message.metadata["next_steps"]:
                    await self.queue_manager.publish(step, message.to_dict())
            
        except Exception as e:
            logger.error(f"Error writing message to file: {e}")
            
            # Try to write error to error directory
            try:
                error_file = self.error_dir / f"error_{int(time.time())}.txt"
                with open(error_file, 'w') as f:
                    f.write(f"Error processing message: {e}\n\n")
                    f.write(f"Message data: {message_data}")
            except Exception as inner_e:
                logger.error(f"Failed to write error file: {inner_e}")
