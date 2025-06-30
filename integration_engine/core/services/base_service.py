import asyncio
import logging
import signal
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Type, TypeVar

from core.models.message import MessageEnvelope
from core.queues.queue_manager import QueueManager, QueueConfig
from core.utils.singleton import ABCSingletonMeta

logger = logging.getLogger(__name__)
ServiceT = TypeVar('ServiceT', bound='BaseService')


class ServiceState:
    """Represents the state of a service."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class BaseService(ABC, metaclass=ABCSingletonMeta):
    """Base class for all services in the integration engine."""
    
    def __init__(
        self,
        name: str,
        queue_manager: Optional[QueueManager] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.config = config or {}
        self.queue_manager = queue_manager or QueueManager()
        self.state = ServiceState.STOPPED
        self._tasks: Set[asyncio.Task] = set()
        self._stop_event = asyncio.Event()
        self._started = False
        
        # Register signal handlers for graceful shutdown
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self._handle_shutdown_signal, sig)
        except (NotImplementedError, RuntimeError):
            # Signals only work in the main thread
            pass
    
    def _handle_shutdown_signal(self, sig):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {sig.name}, shutting down {self.name}...")
        asyncio.create_task(self.stop())
    
    async def start(self) -> None:
        """Start the service."""
        if self.state != ServiceState.STOPPED:
            logger.warning(f"{self.name} is already running or starting")
            return
        
        self.state = ServiceState.STARTING
        logger.info(f"Starting {self.name} service...")
        
        try:
            await self.on_start()
            self.state = ServiceState.RUNNING
            self._started = True
            logger.info(f"{self.name} service started successfully")
        except Exception as e:
            self.state = ServiceState.ERROR
            logger.error(f"Failed to start {self.name} service: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """Stop the service gracefully."""
        if self.state != ServiceState.RUNNING:
            return
        
        self.state = ServiceState.STOPPING
        logger.info(f"Stopping {self.name} service...")
        
        # Signal all tasks to stop
        self._stop_event.set()
        
        # Wait for all tasks to complete
        if self._tasks:
            logger.debug(f"Waiting for {len(self._tasks)} tasks to complete...")
            _, pending = await asyncio.wait(
                self._tasks,
                timeout=self.config.get("shutdown_timeout", 30),
                return_when=asyncio.ALL_COMPLETED
            )
            
            # Cancel any remaining tasks
            for task in pending:
                task.cancel()
            
            # Wait for cancellation to complete
            if pending:
                await asyncio.wait(pending, timeout=5)
        
        try:
            await self.on_stop()
        except Exception as e:
            logger.error(f"Error during {self.name} service shutdown: {e}", exc_info=True)
        
        self.state = ServiceState.STOPPED
        self._started = False
        self._stop_event.clear()
        logger.info(f"{self.name} service stopped")
    
    def create_task(self, coro) -> asyncio.Task:
        """Create and track an asyncio task."""
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task
    
    async def wait_until_stopped(self) -> None:
        """Wait until the service is stopped."""
        while self.state != ServiceState.STOPPED:
            await asyncio.sleep(0.1)
    
    @abstractmethod
    async def on_start(self) -> None:
        """Called when the service is starting."""
        pass
    
    async def on_stop(self) -> None:
        """Called when the service is stopping."""
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, state={self.state})"
    
    def __repr__(self) -> str:
        return str(self)
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
    
    @classmethod
    def get_instance(cls: Type[ServiceT], *args, **kwargs) -> ServiceT:
        """Get or create a singleton instance of the service."""
        return cls(*args, **kwargs)  # type: ignore
