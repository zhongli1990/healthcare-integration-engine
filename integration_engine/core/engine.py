"""Main integration engine class."""
import asyncio
import logging
from typing import Dict, List, Optional, Type

from core.interfaces.input_adapter import InputAdapter
from core.interfaces.output_adapter import OutputAdapter
from core.interfaces.processor import Processor
from core.models.message import MessageEnvelope, MessageStatus
from core.queues.queue_manager import QueueManager, QueueConfig

logger = logging.getLogger(__name__)


class IntegrationEngine:
    """Main integration engine orchestrator."""

    def __init__(
        self,
        config: Optional[dict] = None,
        queue_manager: Optional[QueueManager] = None,
    ):
        """Initialize the integration engine.
        
        Args:
            config: Configuration dictionary
            queue_manager: Optional pre-configured queue manager
        """
        self.config = config or {}
        self.running = False
        
        # Initialize queue manager
        self.queue_manager = queue_manager or QueueManager()
        
        # Component registries
        self.input_adapters: Dict[str, InputAdapter] = {}
        self.output_adapters: Dict[str, OutputAdapter] = {}
        self.processors: List[Processor] = []
        
        # Task tracking
        self.tasks: List[asyncio.Task] = []
    
    async def add_input_adapter(
        self,
        name: str,
        adapter_class: Type[InputAdapter],
        **kwargs
    ) -> None:
        """Add an input adapter.
        
        Args:
            name: Unique name for the adapter
            adapter_class: InputAdapter class to instantiate
            **kwargs: Additional arguments to pass to the adapter
        """
        if name in self.input_adapters:
            raise ValueError(f"Input adapter '{name}' already exists")
        
        adapter = adapter_class(**kwargs)
        self.input_adapters[name] = adapter
        logger.info(f"Added input adapter: {name}")
    
    async def add_output_adapter(
        self,
        name: str,
        adapter_class: Type[OutputAdapter],
        **kwargs
    ) -> None:
        """Add an output adapter.
        
        Args:
            name: Unique name for the adapter
            adapter_class: OutputAdapter class to instantiate
            **kwargs: Additional arguments to pass to the adapter
        """
        if name in self.output_adapters:
            raise ValueError(f"Output adapter '{name}' already exists")
        
        adapter = adapter_class(**kwargs)
        self.output_adapters[name] = adapter
        logger.info(f"Added output adapter: {name}")
    
    async def add_processor(
        self,
        processor: Processor,
    ) -> None:
        """Add a processor.
        
        Args:
            processor: Processor instance to add
        """
        self.processors.append(processor)
        logger.info(f"Added processor: {processor.__class__.__name__}")
    
    async def start(self) -> None:
        """Start the integration engine."""
        if self.running:
            logger.warning("Integration engine is already running")
            return
        
        logger.info("Starting integration engine...")
        self.running = True
        
        try:
            # Start queue manager
            await self.queue_manager.initialize()
            
            # Start all components
            await self._start_components()
            
            # Start message processing
            await self._start_processing()
            
            logger.info("Integration engine started successfully")
            
        except Exception as e:
            logger.error(f"Error starting integration engine: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop the integration engine."""
        if not self.running:
            return
        
        logger.info("Stopping integration engine...")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Stop all components
        await self._stop_components()
        
        # Close queue manager
        await self.queue_manager.close()
        
        logger.info("Integration engine stopped")
    
    async def _start_components(self) -> None:
        """Start all registered components."""
        # Start input adapters
        for name, adapter in self.input_adapters.items():
            logger.info(f"Starting input adapter: {name}")
            await adapter.start()
        
        # Start output adapters
        for name, adapter in self.output_adapters.items():
            logger.info(f"Starting output adapter: {name}")
            await adapter.start()
        
        # Start processors
        for processor in self.processors:
            logger.info(f"Starting processor: {processor.__class__.__name__}")
            await processor.start()
    
    async def _stop_components(self) -> None:
        """Stop all registered components."""
        # Stop input adapters
        for name, adapter in self.input_adapters.items():
            try:
                logger.info(f"Stopping input adapter: {name}")
                await adapter.stop()
            except Exception as e:
                logger.error(f"Error stopping input adapter {name}: {e}")
        
        # Stop output adapters
        for name, adapter in self.output_adapters.items():
            try:
                logger.info(f"Stopping output adapter: {name}")
                await adapter.stop()
            except Exception as e:
                logger.error(f"Error stopping output adapter {name}: {e}")
        
        # Stop processors
        for processor in self.processors:
            try:
                logger.info(f"Stopping processor: {processor.__class__.__name__}")
                await processor.stop()
            except Exception as e:
                logger.error(f"Error stopping processor {processor.__class__.__name__}: {e}")
    
    async def _start_processing(self) -> None:
        """Start the main processing loop."""
        # Start input adapter tasks
        for name, adapter in self.input_adapters.items():
            task = asyncio.create_task(self._process_input(adapter, name))
            self.tasks.append(task)
        
        # Start processor tasks
        for processor in self.processors:
            task = asyncio.create_task(self._process_with_processor(processor))
            self.tasks.append(task)
    
    async def _process_input(self, adapter: InputAdapter, name: str) -> None:
        """Process messages from an input adapter."""
        try:
            async for message in adapter.receive():
                try:
                    # Update message status
                    message.header.status = MessageStatus.RECEIVED
                    
                    # Get the raw queue
                    queue = await self.queue_manager.get_queue("raw_messages")
                    
                    # Publish to raw queue
                    await queue.publish(message)
                    
                    # Acknowledge the message
                    await adapter.acknowledge(message)
                    
                except Exception as e:
                    logger.error(f"Error processing message from {name}: {e}")
                    await adapter.nacknowledge(message, str(e))
                    
        except asyncio.CancelledError:
            logger.info(f"Input processing for {name} cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in input processing for {name}: {e}")
            raise
    
    async def _process_with_processor(self, processor: Processor) -> None:
        """Process messages with a processor."""
        # TODO: Implement processor pipeline
        pass
