import asyncio
import logging
from pathlib import Path
from typing import Callable, Dict, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

logger = logging.getLogger(__name__)

class HL7FileHandler(FileSystemEventHandler):
    """Handle file system events for HL7 files"""
    
    def __init__(self, callback: Callable[[Path], None], pattern: str = "*.hl7"):
        self.callback = callback
        self.pattern = pattern
    
    def on_created(self, event: FileSystemEvent) -> None:
        """Called when a file is created"""
        if not event.is_directory and Path(event.src_path).match(self.pattern):
            logger.info(f"New HL7 file detected: {event.src_path}")
            self.callback(Path(event.src_path))

class HL7FileWatcher:
    """Watch for new HL7 files in a directory"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with watch configuration"""
        self.config = config
        self.observer = Observer()
        self.running = False
        self.callback = None
        
        # Ensure watch directory exists
        self.watch_dir = Path(config.get('watch_dir', './data/incoming'))
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        
        # Create processed and error directories
        self.processed_dir = Path(config.get('processed_dir', './data/processed'))
        self.error_dir = Path(config.get('error_dir', './data/errors'))
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.error_dir.mkdir(parents=True, exist_ok=True)
    
    def set_callback(self, callback: Callable[[Path], None]) -> None:
        """Set the callback for new files"""
        self.callback = callback
    
    async def start(self) -> None:
        """Start watching for files"""
        if self.running:
            return
            
        logger.info(f"Starting HL7 file watcher on {self.watch_dir}")
        
        # Set up the file system observer
        event_handler = HL7FileHandler(self._process_file, "*.hl7")
        self.observer.schedule(
            event_handler,
            path=str(self.watch_dir),
            recursive=False
        )
        
        self.running = True
        self.observer.start()
        
        # Process any existing files
        await self._process_existing_files()
    
    async def stop(self) -> None:
        """Stop watching for files"""
        if not self.running:
            return
            
        logger.info("Stopping HL7 file watcher")
        self.observer.stop()
        self.observer.join()
        self.running = False
    
    async def _process_existing_files(self) -> None:
        """Process any existing files in the watch directory"""
        for file_path in self.watch_dir.glob("*.hl7"):
            await self._process_file(file_path)
    
    async def _process_file(self, file_path: Path) -> None:
        """Process a single file"""
        if not file_path.exists():
            return
            
        if self.callback:
            try:
                await self.callback(file_path)
                self._move_file(file_path, self.processed_dir)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                self._move_file(file_path, self.error_dir)
    
    def _move_file(self, src_path: Path, dest_dir: Path) -> None:
        """Move a file to the specified directory"""
        try:
            dest_path = dest_dir / src_path.name
            src_path.rename(dest_path)
            logger.debug(f"Moved {src_path} to {dest_path}")
        except Exception as e:
            logger.error(f"Error moving file {src_path}: {e}")
