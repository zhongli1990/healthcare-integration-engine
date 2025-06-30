"""
Test script for the file-based HL7 processing workflow.

This script:
1. Starts the integration engine with test configuration
2. Copies test HL7 files to the input directory
3. Monitors the output directories for processed files
4. Prints the results
"""
import asyncio
import logging
import shutil
import sys
import time
from pathlib import Path

# Add the current directory to the Python path
sys.path.append(str(Path(__file__).parent))

from integration_engine.app import IntegrationEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
TEST_CONFIG = {
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_db": 0,
    "input_dir": "test_data/input",
    "processed_dir": "test_data/processed",
    "output_dir": "test_data/output"
}

def setup_test_environment():
    """Set up the test environment."""
    # Create test directories if they don't exist
    for dir_path in [
        TEST_CONFIG["input_dir"],
        TEST_CONFIG["processed_dir"],
        f"{TEST_CONFIG['output_dir']}/hl7",
        f"{TEST_CONFIG['output_dir']}/fhir",
        f"{TEST_CONFIG['output_dir']}/errors"
    ]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # Clear any existing test files
    for file_path in Path(TEST_CONFIG["input_dir"]).glob("*"):
        if file_path.is_file():
            file_path.unlink()
    
    for file_path in Path(TEST_CONFIG["processed_dir"]).glob("*"):
        if file_path.is_file():
            file_path.unlink()
    
    for output_dir in ["hl7", "fhir", "errors"]:
        for file_path in Path(f"{TEST_CONFIG['output_dir']}/{output_dir}").glob("*"):
            if file_path.is_file():
                file_path.unlink()

def copy_test_file():
    """Copy the test HL7 file to the input directory."""
    test_file = Path("test_data/input/sample_adt_a01.hl7")
    if not test_file.exists():
        logger.error("Test file not found. Please create it first.")
        return False
    
    # Create a copy with a timestamp to avoid conflicts
    timestamp = int(time.time())
    dest_file = Path(TEST_CONFIG["input_dir"]) / f"test_{timestamp}.hl7"
    shutil.copy2(test_file, dest_file)
    logger.info(f"Copied test file to {dest_file}")
    return dest_file

async def run_test():
    """Run the test workflow."""
    # Set up the test environment
    setup_test_environment()
    
    # Create and start the integration engine
    engine = IntegrationEngine(TEST_CONFIG)
    
    try:
        # Start the engine in the background
        engine_task = asyncio.create_task(engine.start())
        
        # Wait a moment for the engine to start
        await asyncio.sleep(2)
        
        # Copy the test file to the input directory
        test_file = copy_test_file()
        if not test_file:
            return
        
        logger.info("Monitoring for processed files...")
        
        # Monitor the output directories for processed files
        processed = False
        start_time = time.time()
        timeout = 30  # seconds
        
        while not processed and (time.time() - start_time) < timeout:
            # Check if the file was processed
            processed_files = list(Path(TEST_CONFIG["processed_dir"]).glob("*.hl7"))
            if processed_files:
                logger.info(f"Found processed files: {[f.name for f in processed_files]}")
                processed = True
                break
                
            # Check output directories
            for output_type in ["hl7", "fhir", "errors"]:
                output_dir = Path(f"{TEST_CONFIG['output_dir']}/{output_type}")
                output_files = list(output_dir.glob("*.*"))
                if output_files:
                    for f in output_files:
                        logger.info(f"Found output file in {output_type}: {f.name}")
                    processed = True
            
            await asyncio.sleep(1)
        
        if not processed:
            logger.warning("Test timed out waiting for file processing")
        else:
            logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        # Clean up
        logger.info("Stopping integration engine...")
        await engine.stop()
        if 'engine_task' in locals():
            engine_task.cancel()
            try:
                await engine_task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    asyncio.run(run_test())
