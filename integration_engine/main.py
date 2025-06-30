"""Main entry point for the Integration Engine."""
import asyncio
import importlib
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

import yaml
from core.engine import IntegrationEngine
from core.interfaces.input_adapter import InputAdapter
from core.interfaces.output_adapter import OutputAdapter
from core.interfaces.processor import Processor
from core.queues.queue_manager import QueueManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IntegrationEngineApp:
    """Main application class for the Integration Engine."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the application.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config = self._load_config(config_path)
        self.engine = IntegrationEngine(
            config=self.config,
            queue_manager=QueueManager()
        )
        self.tasks: List[asyncio.Task] = []
    
    @staticmethod
    def _load_config(config_path: Optional[str] = None) -> dict:
        """Load configuration from file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            dict: Loaded configuration
        """
        # Default config paths
        default_paths = [
            Path("config/local.yaml"),
            Path("config/default.yaml"),
            Path("/etc/integration-engine/config.yaml"),
        ]
        
        # Try to find a config file
        config_path_obj = None
        if config_path:
            config_path_obj = Path(config_path)
            if not config_path_obj.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")
        else:
            for path in default_paths:
                if path.exists():
                    config_path_obj = path
                    break
            else:
                logger.warning("No configuration file found, using defaults")
                return {}
        
        # Load config
        try:
            with open(config_path_obj, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error loading config file {config_path_obj}: {e}")
            return {}
    
    def _get_class(self, class_path: str) -> type:
        """Dynamically import a class from a module path.
        
        Args:
            class_path: Full module path to the class (e.g., 'module.submodule.ClassName')
            
        Returns:
            type: The imported class
            
        Raises:
            ImportError: If the class cannot be imported
        """
        module_path, class_name = class_path.rsplit('.', 1)
        
        try:
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import class {class_path}: {e}")
            raise ImportError(f"Could not import class {class_path}") from e
    
    async def _initialize_inputs(self) -> None:
        """Initialize and register input adapters."""
        inputs_config = self.config.get('inputs', {})
        
        for name, adapter_config in inputs_config.items():
            if not adapter_config.get('enabled', True):
                logger.info(f"Skipping disabled input adapter: {name}")
                continue
            
            try:
                # Get adapter class
                adapter_class = self._get_class(adapter_config['class'])
                
                # Create adapter instance
                adapter = adapter_class(**adapter_config.get('config', {}))
                
                # Register with engine
                await self.engine.add_input_adapter(name, adapter)
                logger.info(f"Registered input adapter: {name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize input adapter {name}: {e}")
    
    async def _initialize_outputs(self) -> None:
        """Initialize and register output adapters."""
        outputs_config = self.config.get('outputs', {})
        
        for name, adapter_config in outputs_config.items():
            if not adapter_config.get('enabled', True):
                logger.info(f"Skipping disabled output adapter: {name}")
                continue
            
            try:
                # Get adapter class
                adapter_class = self._get_class(adapter_config['class'])
                
                # Create adapter instance
                adapter = adapter_class(**adapter_config.get('config', {}))
                
                # Register with engine
                await self.engine.add_output_adapter(name, adapter)
                logger.info(f"Registered output adapter: {name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize output adapter {name}: {e}")
    
    async def _initialize_processors(self) -> None:
        """Initialize and register processors."""
        processing_config = self.config.get('processing', {})
        
        for name, processor_config in processing_config.items():
            if not processor_config.get('enabled', True):
                logger.info(f"Skipping disabled processor: {name}")
                continue
            
            try:
                # Get processor class
                processor_class = self._get_class(processor_config['class'])
                
                # Create processor instance
                processor = processor_class(**processor_config.get('config', {}))
                
                # Register with engine
                await self.engine.add_processor(processor)
                logger.info(f"Registered processor: {name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize processor {name}: {e}")
    
    async def start(self) -> None:
        """Start the integration engine."""
        logger.info("Starting Integration Engine...")
        
        try:
            # Initialize components
            await self._initialize_inputs()
            await self._initialize_outputs()
            await self._initialize_processors()
            
            # Start the engine
            await self.engine.start()
            logger.info("Integration Engine started successfully")
            
            # Keep the application running
            while True:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info("Shutdown signal received")
        except Exception as e:
            logger.error(f"Error in Integration Engine: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Stop the integration engine."""
        logger.info("Stopping Integration Engine...")
        
        # Stop the engine
        await self.engine.stop()
        
        # Cancel any running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        logger.info("Integration Engine stopped")


def main() -> None:
    """Main entry point."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Integration Engine")
    parser.add_argument(
        "-c", "--config",
        help="Path to configuration file"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create and run the application
    app = IntegrationEngineApp(config_path=args.config)
    
    try:
        asyncio.run(app.start())
    except KeyboardInterrupt:
        logger.info("Shutdown requested, stopping...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
