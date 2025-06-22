"""Dependency injection for API endpoints"""
from typing import Dict, Any
from fastapi import Depends

from app.core.config import get_settings
from app.core.hl7.processor import HL7Processor
from app.core.hl7.file_watcher import HL7FileWatcher

# Global instances
_hl7_processor = None
_hl7_watcher = None

def get_hl7_config() -> Dict[str, Any]:
    """Get HL7 processing configuration"""
    settings = get_settings()
    return {
        'watch_dir': settings.HL7_WATCH_DIR,
        'processed_dir': settings.HL7_PROCESSED_DIR,
        'error_dir': settings.HL7_ERROR_DIR,
    }

def get_hl7_processor() -> HL7Processor:
    """Get the HL7 processor instance"""
    global _hl7_processor
    if _hl7_processor is None:
        config = get_hl7_config()
        _hl7_processor = HL7Processor(config)
    return _hl7_processor

def get_hl7_watcher() -> HL7FileWatcher:
    """Get the HL7 file watcher instance"""
    global _hl7_watcher
    if _hl7_watcher is None:
        config = get_hl7_config()
        _hl7_watcher = HL7FileWatcher(config)
    return _hl7_watcher

async def start_hl7_services():
    """Start all HL7 services"""
    watcher = get_hl7_watcher()
    processor = get_hl7_processor()
    
    # Set up the callback for processing files
    async def process_file_callback(file_path):
        try:
            await processor.process_file(file_path)
        except Exception as e:
            # Log the error but don't crash the watcher
            import logging
            logging.error(f"Error processing file {file_path}: {e}")
    
    watcher.set_callback(process_file_callback)
    await watcher.start()
    return watcher

async def stop_hl7_services():
    """Stop all HL7 services"""
    global _hl7_watcher
    if _hl7_watcher:
        await _hl7_watcher.stop()
        _hl7_watcher = None
