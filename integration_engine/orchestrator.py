"""
Integration Engine Orchestrator

This module provides the main orchestrator service that coordinates all components
of the integration engine, including message ingestion, validation, transformation,
routing, and outbound delivery.
"""

import asyncio
import logging
import signal
from typing import Dict, List, Optional, Type, Any

from core.queues.queue_manager import QueueManager, QueueConfig, QueueType
from core.services.base_service import BaseService

# Import all the services we've created
from services.inbound.hl7v2_listener import HL7v2ListenerService
from services.inbound.fhir_listener import FHIRListenerService
from services.processing.validation_service import ValidationService
from services.processing.transformation_service import TransformationService
from services.processing.routing_service import RoutingService
from services.outbound.hl7v2_sender import HL7v2Sender
from services.outbound.fhir_sender import FHIROutboundSender, FHIRServerConfig
from services.outbound.file_sender import FileSender, FileOutputConfig

logger = logging.getLogger(__name__)


class IntegrationEngine:
    """
    Main orchestrator for the integration engine.
    
    This class is responsible for initializing, starting, and managing all the
    services that make up the integration engine.
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        queue_manager: Optional[QueueManager] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        """
        Initialize the integration engine.
        
        Args:
            config: Configuration dictionary
            queue_manager: Optional pre-configured QueueManager
            loop: Optional asyncio event loop
        """
        self.config = config or {}
        self.loop = loop or asyncio.get_event_loop()
        
        # Initialize queue manager
        self.queue_manager = queue_manager or QueueManager()
        
        # Services registry
        self.services: Dict[str, BaseService] = {}
        
        # Configure logging
        self._configure_logging()
        
        # Signal handlers
        self._setup_signal_handlers()
    
    def _configure_logging(self) -> None:
        """Configure logging based on the configuration."""
        log_level = self.config.get("log_level", "INFO").upper()
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        for sig in (signal.SIGINT, signal.SIGTERM):
            self.loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self.shutdown(f"Received signal {s.name}"))
            )
    
    async def initialize(self) -> None:
        """Initialize the integration engine and all its services."""
        logger.info("Initializing Integration Engine...")
        
        # Initialize queue manager
        await self.queue_manager.initialize()
        
        # Create and initialize all services
        await self._initialize_services()
        
        logger.info("Integration Engine initialized successfully")
    
    async def _initialize_services(self) -> None:
        """Initialize all services based on configuration."""
        # Get services configuration or use defaults
        services_config = self.config.get("services", {})
        
        # Initialize inbound services
        await self._initialize_inbound_services(services_config.get("inbound", {}))
        
        # Initialize processing services
        await self._initialize_processing_services(services_config.get("processing", {}))
        
        # Initialize outbound services
        await self._initialize_outbound_services(services_config.get("outbound", {}))
    
    async def _initialize_inbound_services(self, config: Dict[str, Any]) -> None:
        """Initialize all inbound services."""
        # HL7 v2 Listener
        if config.get("hl7v2_listener", {}).get("enabled", True):
            hl7_config = config.get("hl7v2_listener", {})
            hl7_service = HL7v2ListenerService(
                mllp_host=hl7_config.get("host", "0.0.0.0"),
                mllp_port=hl7_config.get("port", 2575),
                input_queue=hl7_config.get("input_queue", "inbound_hl7v2_messages"),
                queue_manager=self.queue_manager,
                **hl7_config.get("options", {})
            )
            await self._add_service("hl7v2_listener", hl7_service)
        
        # FHIR Listener
        if config.get("fhir_listener", {}).get("enabled", True):
            fhir_config = config.get("fhir_listener", {})
            fhir_service = FHIRListenerService(
                host=fhir_config.get("host", "0.0.0.0"),
                port=fhir_config.get("port", 8080),
                input_queue=fhir_config.get("input_queue", "inbound_fhir_messages"),
                queue_manager=self.queue_manager,
                **fhir_config.get("options", {})
            )
            await self._add_service("fhir_listener", fhir_service)
    
    async def _initialize_processing_services(self, config: Dict[str, Any]) -> None:
        """Initialize all processing services."""
        # Validation Service
        if config.get("validation", {}).get("enabled", True):
            val_config = config.get("validation", {})
            val_service = ValidationService(
                input_queue=val_config.get("input_queue", "inbound_messages"),
                output_queue=val_config.get("output_queue", "validated_messages"),
                error_queue=val_config.get("error_queue", "validation_errors"),
                queue_manager=self.queue_manager,
                **val_config.get("options", {})
            )
            await self._add_service("validation", val_service)
        
        # Transformation Service
        if config.get("transformation", {}).get("enabled", True):
            trans_config = config.get("transformation", {})
            trans_service = TransformationService(
                input_queue=trans_config.get("input_queue", "validated_messages"),
                output_queue=trans_config.get("output_queue", "transformed_messages"),
                error_queue=trans_config.get("error_queue", "transformation_errors"),
                queue_manager=self.queue_manager,
                **trans_config.get("options", {})
            )
            await self._add_service("transformation", trans_service)
        
        # Routing Service
        if config.get("routing", {}).get("enabled", True):
            route_config = config.get("routing", {})
            route_service = RoutingService(
                input_queue=route_config.get("input_queue", "transformed_messages"),
                default_route=route_config.get("default_route", "unrouted_messages"),
                error_queue=route_config.get("error_queue", "routing_errors"),
                queue_manager=self.queue_manager,
                **route_config.get("options", {})
            )
            
            # Add routes from config
            for route in route_config.get("routes", []):
                route_service.add_route_rule(route)
            
            await self._add_service("routing", route_service)
    
    async def _initialize_outbound_services(self, config: Dict[str, Any]) -> None:
        """Initialize all outbound services."""
        # HL7 v2 Sender
        if config.get("hl7v2_sender", {}).get("enabled", False):
            hl7_config = config.get("hl7v2_sender", {})
            hl7_sender = HL7v2Sender(
                host=hl7_config["host"],
                port=hl7_config["port"],
                input_queue=hl7_config.get("input_queue", "outbound_hl7v2_messages"),
                error_queue=hl7_config.get("error_queue", "outbound_hl7v2_errors"),
                queue_manager=self.queue_manager,
                **hl7_config.get("options", {})
            )
            await self._add_service("hl7v2_sender", hl7_sender)
        
        # FHIR Sender
        if config.get("fhir_sender", {}).get("enabled", False):
            fhir_config = config.get("fhir_sender", {})
            server_config = FHIRServerConfig(
                base_url=fhir_config["base_url"],
                **fhir_config.get("auth", {})
            )
            fhir_sender = FHIROutboundSender(
                server_config=server_config,
                input_queue=fhir_config.get("input_queue", "outbound_fhir_messages"),
                error_queue=fhir_config.get("error_queue", "outbound_fhir_errors"),
                queue_manager=self.queue_manager,
                **fhir_config.get("options", {})
            )
            await self._add_service("fhir_sender", fhir_sender)
        
        # File Sender
        if config.get("file_sender", {}).get("enabled", False):
            file_config = config.get("file_sender", {})
            output_config = FileOutputConfig(
                output_dir=file_config["output_dir"],
                **file_config.get("options", {})
            )
            file_sender = FileSender(
                config=output_config,
                input_queue=file_config.get("input_queue", "outbound_file_messages"),
                error_queue=file_config.get("error_queue", "outbound_file_errors"),
                queue_manager=self.queue_manager
            )
            await self._add_service("file_sender", file_sender)
    
    async def _add_service(self, name: str, service: BaseService) -> None:
        """Add and initialize a service."""
        if name in self.services:
            raise ValueError(f"Service with name '{name}' already exists")
        
        # Initialize the service
        await service.initialize()
        
        # Add to services registry
        self.services[name] = service
        logger.info(f"Added service: {name}")
    
    async def start(self) -> None:
        """Start all services."""
        logger.info("Starting Integration Engine...")
        
        try:
            # Start all services
            for name, service in self.services.items():
                logger.debug(f"Starting service: {name}")
                await service.start()
                logger.info(f"Started service: {name}")
            
            logger.info("Integration Engine started successfully")
            
            # Keep the service running
            while True:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info("Integration Engine shutdown requested")
        except Exception as e:
            logger.exception("Error in Integration Engine")
            raise
        finally:
            await self.shutdown("Service loop ended")
    
    async def shutdown(self, reason: str = "Shutdown requested") -> None:
        """Shutdown the integration engine and all services."""
        logger.info(f"Shutting down Integration Engine: {reason}")
        
        # Stop all services in reverse order
        for name in reversed(list(self.services.keys())):
            try:
                logger.debug(f"Stopping service: {name}")
                await self.services[name].stop()
                logger.info(f"Stopped service: {name}")
            except Exception as e:
                logger.exception(f"Error stopping service {name}")
        
        # Clear services
        self.services.clear()
        
        # Close queue manager
        await self.queue_manager.close()
        
        logger.info("Integration Engine shutdown complete")


def create_engine(config: Optional[Dict[str, Any]] = None) -> IntegrationEngine:
    """
    Create and configure an IntegrationEngine instance.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured IntegrationEngine instance
    """
    return IntegrationEngine(config=config)


async def run_engine(config: Optional[Dict[str, Any]] = None) -> None:
    """
    Create, initialize, and run the integration engine.
    
    This is the main entry point for running the integration engine.
    
    Args:
        config: Optional configuration dictionary
    """
    # Create and configure the engine
    engine = create_engine(config)
    
    try:
        # Initialize the engine
        await engine.initialize()
        
        # Start the engine (this will block until shutdown)
        await engine.start()
        
    except Exception as e:
        logger.exception("Fatal error in Integration Engine")
        raise
    finally:
        # Ensure clean shutdown
        await engine.shutdown("Application terminated")


if __name__ == "__main__":
    # Example configuration
    config = {
        "log_level": "INFO",
        "services": {
            "inbound": {
                "hl7v2_listener": {
                    "enabled": True,
                    "host": "0.0.0.0",
                    "port": 2575,
                    "input_queue": "inbound_hl7v2_messages",
                    "options": {
                        "buffer_size": 4096,
                        "max_connections": 10
                    }
                },
                "fhir_listener": {
                    "enabled": True,
                    "host": "0.0.0.0",
                    "port": 8080,
                    "input_queue": "inbound_fhir_messages"
                }
            },
            "processing": {
                "validation": {
                    "enabled": True,
                    "input_queue": "inbound_messages",
                    "output_queue": "validated_messages",
                    "error_queue": "validation_errors"
                },
                "transformation": {
                    "enabled": True,
                    "input_queue": "validated_messages",
                    "output_queue": "transformed_messages",
                    "error_queue": "transformation_errors"
                },
                "routing": {
                    "enabled": True,
                    "input_queue": "transformed_messages",
                    "default_route": "unrouted_messages",
                    "error_queue": "routing_errors",
                    "routes": [
                        {
                            "name": "route-hl7v2-adt",
                            "description": "Route HL7 v2 ADT messages to ADT processor",
                            "priority": 10,
                            "conditions": [
                                {
                                    "field": "header.content_type",
                                    "operator": "contains",
                                    "value": "hl7-v2"
                                },
                                {
                                    "field": "header.message_type",
                                    "operator": "regex",
                                    "value": "^ADT_"
                                }
                            ],
                            "actions": [
                                {
                                    "type": "forward",
                                    "target": "adt_processor"
                                }
                            ],
                            "enabled": True
                        }
                    ]
                }
            },
            "outbound": {
                "hl7v2_sender": {
                    "enabled": True,
                    "host": "localhost",
                    "port": 2576,
                    "input_queue": "outbound_hl7v2_messages",
                    "error_queue": "outbound_hl7v2_errors",
                    "options": {
                        "reconnect_interval": 5,
                        "timeout": 30
                    }
                },
                "fhir_sender": {
                    "enabled": True,
                    "base_url": "http://hapi.fhir.org/baseR4",
                    "input_queue": "outbound_fhir_messages",
                    "error_queue": "outbound_fhir_errors",
                    "auth": {
                        "auth_type": "none"
                    },
                    "options": {
                        "max_retries": 3,
                        "retry_delay": 5
                    }
                },
                "file_sender": {
                    "enabled": True,
                    "output_dir": "./output",
                    "input_queue": "outbound_file_messages",
                    "error_queue": "outbound_file_errors",
                    "options": {
                        "filename_pattern": "{timestamp}_{message_id}{ext}",
                        "timestamp_format": "%Y%m%d_%H%M%S",
                        "create_subdirs": True,
                        "mode": "w",
                        "encoding": "utf-8"
                    }
                }
            }
        }
    }
    
    # Run the engine
    asyncio.run(run_engine(config))
