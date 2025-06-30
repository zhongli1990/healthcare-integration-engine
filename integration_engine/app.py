"""
Integration Engine Application

Main entry point for the file-based HL7 processing pipeline.
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path

from integration_engine.core.queues.queue_manager import QueueManager
from integration_engine.services.file_based.hl7_file_listener import HL7FileListener
from integration_engine.services.file_based.file_writer import FileWriter
from integration_engine.services.processing.hl7_validation_service import HL7ValidationService
from integration_engine.services.processing.transformation_service import TransformationService
from integration_engine.services.processing.hl7_routing_service import HL7RoutingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class IntegrationEngine:
    """Main integration engine application."""
    
    def __init__(self, config: dict):
        """Initialize the integration engine.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.running = False
        self.services = []
        
        # Initialize queue manager
        self.queue_manager = QueueManager(
            host=config.get("redis_host", "localhost"),
            port=config.get("redis_port", 6379),
            db=config.get("redis_db", 0)
        )
        
        # Initialize services
        self._init_services()
    
    def _init_services(self):
        """Initialize all services."""
        # File listener
        self.file_listener = HL7FileListener(
            queue_manager=self.queue_manager,
            input_dir=Path(self.config["input_dir"]),
            processed_dir=Path(self.config["processed_dir"])
        )
        
        # File writer
        self.file_writer = FileWriter(
            queue_manager=self.queue_manager,
            output_dir=Path(self.config["output_dir"])
        )
        
        # Processing services
        self.validation_service = HL7ValidationService(self.queue_manager)
        self.transformation_service = TransformationService(self.queue_manager)
        self.routing_service = HL7RoutingService(self.queue_manager)
        
        # Register services for cleanup
        self.services = [
            self.file_listener,
            self.file_writer,
            self.validation_service,
            self.transformation_service,
            self.routing_service
        ]
    
    async def start(self):
        """Start the integration engine."""
        if self.running:
            logger.warning("Integration engine is already running")
            return
        
        logger.info("Starting integration engine...")
        
        try:
            # Initialize queue manager
            await self.queue_manager.initialize()
            
            # Start services
            await self.file_writer.start()
            await self.validation_service.start()
            await self.transformation_service.start()
            await self.routing_service.start()
            
            # Start file listener last
            self.file_listener.start()
            
            self.running = True
            logger.info("Integration engine started")
            
            # Keep the application running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error starting integration engine: {e}")
            await self.stop()
    
    async def stop(self):
        """Stop the integration engine."""
        if not self.running:
            return
        
        logger.info("Stopping integration engine...")
        
        # Stop file listener
        if hasattr(self, 'file_listener'):
            self.file_listener.stop()
        
        # Stop queue manager
        if hasattr(self, 'queue_manager'):
            await self.queue_manager.close()
        
        self.running = False
        logger.info("Integration engine stopped")


def main():
    """Main entry point."""
    # Configuration
    config = {
        "redis_host": "localhost",
        "redis_port": 6379,
        "redis_db": 0,
        "input_dir": "data/input",
        "processed_dir": "data/processed",
        "output_dir": "data/output"
    }
    
    # Create data directories
    for dir_path in [config["input_dir"], config["processed_dir"], config["output_dir"]]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # Create and run the application
    engine = IntegrationEngine(config)
    
    # Handle graceful shutdown
    async def shutdown(signal, loop):
        """Handle shutdown signals."""
        logger.info(f"Received exit signal {signal.name}...")
        await engine.stop()
        loop.stop()
    
    loop = asyncio.get_event_loop()
    
    # Register signal handlers
    for sig in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(shutdown(s, loop))
        )
    
    try:
        loop.run_until_complete(engine.start())
    except Exception as e:
        logger.error(f"Error running integration engine: {e}")
    finally:
        loop.run_until_complete(engine.stop())
        loop.close()
        logger.info("Integration engine shutdown complete")


if __name__ == "__main__":
    main()
