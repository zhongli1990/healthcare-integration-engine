"""
Command Line Interface for the Integration Engine.

This module provides a command-line interface for starting, stopping, and managing
the Integration Engine and its components.
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional, Dict, Any

import yaml

from integration_engine.orchestrator import IntegrationEngine, create_engine
from integration_engine.core.config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variable to hold the engine instance
engine: Optional[IntegrationEngine] = None


async def start_engine(config_path: Optional[str] = None) -> None:
    """
    Start the integration engine with the specified configuration.
    
    Args:
        config_path: Path to the configuration file
    """
    global engine
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = {}
        
        if config_path:
            logger.info(f"Loading configuration from {config_path}")
            config = load_config(config_path)
        else:
            logger.info("Using default configuration")
            config = load_config()
        
        # Create and initialize the engine
        logger.info("Initializing Integration Engine...")
        engine = create_engine(config)
        await engine.initialize()
        
        # Start the engine
        logger.info("Starting Integration Engine...")
        await engine.start()
        
    except Exception as e:
        logger.exception("Failed to start Integration Engine")
        if engine:
            await engine.shutdown("Error during startup")
        raise


def signal_handler(sig, frame):
    """Handle termination signals."""
    logger.info("Shutdown signal received. Shutting down gracefully...")
    if engine:
        asyncio.create_task(engine.shutdown("Received termination signal"))
    else:
        sys.exit(0)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Integration Engine - A flexible and scalable healthcare integration platform"
    )
    
    # Global options
    parser.add_argument(
        "-c", "--config",
        type=str,
        help="Path to configuration file (YAML)",
        default=None
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the integration engine")
    start_parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as a daemon process"
    )
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check the status of the integration engine")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop a running integration engine")
    
    # Version command
    version_parser = subparsers.add_parser("version", help="Show version information")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_command", help="Configuration command")
    
    # Config show command
    config_show_parser = config_subparsers.add_parser("show", help="Show current configuration")
    config_show_parser.add_argument(
        "--format",
        type=str,
        choices=["yaml", "json"],
        default="yaml",
        help="Output format"
    )
    
    # Config validate command
    config_validate_parser = config_subparsers.add_parser("validate", help="Validate configuration file")
    config_validate_parser.add_argument(
        "config_file",
        type=str,
        help="Path to configuration file to validate"
    )
    
    return parser.parse_args()


def print_banner() -> None:
    """Print the application banner."""
    banner = """
    ╔══════════════════════════════════════════════════╗
    ║             INTEGRATION ENGINE                  ║
    ║  A flexible and scalable healthcare integration  ║
    ║  platform for HL7 v2, FHIR, and other standards  ║
    ╚══════════════════════════════════════════════════╝
    """
    print(banner)



def main() -> int:
    """Main entry point for the CLI."""
    # Parse command line arguments
    args = parse_args()
    
    # Configure logging
    log_level = getattr(logging, args.log_level.upper())
    logging.getLogger().setLevel(log_level)
    
    # Print banner
    if args.command != "version":
        print_banner()
    
    # Handle commands
    if args.command == "start":
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start the engine
        try:
            asyncio.run(start_engine(args.config))
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        except Exception as e:
            logger.exception("Error running integration engine")
            return 1
            
    elif args.command == "status":
        # TODO: Implement status check
        print("Status command is not yet implemented")
        return 0
        
    elif args.command == "stop":
        # TODO: Implement stop command
        print("Stop command is not yet implemented")
        return 0
        
    elif args.command == "version":
        # TODO: Get version from package metadata
        print("Integration Engine v0.1.0")
        return 0
        
    elif args.command == "config":
        if args.config_command == "show":
            # Load and display the configuration
            try:
                config = load_config(args.config)
                if args.format == "yaml":
                    import yaml
                    print(yaml.dump(config.dict(), default_flow_style=False))
                else:  # json
                    import json
                    print(json.dumps(config.dict(), indent=2))
            except Exception as e:
                logger.error(f"Failed to load configuration: {e}")
                return 1
                
        elif args.config_command == "validate":
            # Validate the configuration file
            try:
                load_config(args.config_file)
                print(f"✅ Configuration file is valid: {args.config_file}")
            except Exception as e:
                logger.error(f"❌ Invalid configuration file: {e}")
                return 1
                
    else:
        # No command provided, show help
        parse_args().print_help()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
