"""Integration tests for the Healthcare Integration Engine."""
import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

import pytest
import yaml

from core.engine import IntegrationEngine
from core.interfaces.input_adapter import InputAdapter
from core.interfaces.output_adapter import OutputAdapter
from core.interfaces.processor import Processor
from core.models.message import MessageEnvelope, MessageHeader, MessageBody, MessageStatus
from core.queues.queue_manager import QueueManager

# Test configuration
TEST_CONFIG = {
    "inputs": {
        "file": {
            "enabled": True,
            "class": "inputs.file_input.FileInputAdapter",
            "config": {
                "input_dir": "test_data/inputs",
                "processed_dir": "test_data/processed",
                "error_dir": "test_data/errors",
                "file_pattern": "*.hl7",
                "poll_interval": 0.1
            }
        }
    },
    "outputs": {
        "file": {
            "enabled": True,
            "class": "outputs.file_output.FileOutputAdapter",
            "config": {
                "output_dir": "test_data/outputs",
                "file_extension": ".hl7",
                "file_naming": "{message_id}",
                "create_subdirs": True
            }
        }
    },
    "processing": {
        "validation": {
            "enabled": True,
            "class": "processing.validation.ValidationProcessor",
            "config": {
                "schemas": {
                    "hl7": {
                        "type": "hl7",
                        "message_types": ["ADT^A01", "ADT^A04", "ORU^R01"]
                    }
                }
            }
        },
        "routing": {
            "enabled": True,
            "class": "processing.routing.RoutingProcessor",
            "config": {
                "default_destinations": ["file"],
                "rules": []
            }
        }
    },
    "queues": {
        "default": "memory"
    },
    "logging": {
        "level": "DEBUG"
    }
}

# Sample HL7 message for testing
SAMPLE_HL7 = r"""MSH|^~\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|20230629123045||ADT^A01|MSG00001|P|2.3
EVN|A01|20230629123045
PID|1||12345||Doe^John^^^Mr.||19700101|M||2106-3|123 Main St^^Anytown^CA^12345^USA
PV1|1|O|OPD||||2000000001^Smith^John^^^Dr.|||||||||||V01|||||||||||||||||||123456"""

@pytest.fixture(scope="module")
def test_dirs():
    """Create and clean up test directories."""
    base_dir = Path("test_data")
    dirs = {
        "base": base_dir,
        "inputs": base_dir / "inputs",
        "outputs": base_dir / "outputs",
        "processed": base_dir / "processed",
        "errors": base_dir / "errors",
    }
    
    # Clean up and create test directories
    for d in dirs.values():
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    
    yield dirs
    
    # Clean up after tests
    shutil.rmtree(base_dir, ignore_errors=True)

@pytest.fixture
def test_config(test_dirs):
    """Return a test configuration with updated paths."""
    config = TEST_CONFIG.copy()
    
    # Update paths in config
    config["inputs"]["file"]["config"]["input_dir"] = str(test_dirs["inputs"])
    config["inputs"]["file"]["config"]["processed_dir"] = str(test_dirs["processed"])
    config["inputs"]["file"]["config"]["error_dir"] = str(test_dirs["errors"])
    config["outputs"]["file"]["config"]["output_dir"] = str(test_dirs["outputs"])
    
    return config

@pytest.fixture
async def engine(test_config):
    """Create and start an integration engine for testing."""
    # Create engine with test config
    engine = IntegrationEngine(config=test_config)
    
    # Start the engine
    await engine.start()
    
    yield engine
    
    # Stop the engine
    await engine.stop()

@pytest.mark.asyncio
async def test_file_processing(engine, test_dirs):
    """Test end-to-end file processing."""
    # Create a test HL7 file
    input_file = test_dirs["inputs"] / "test.hl7"
    input_file.write_text(SAMPLE_HL7)
    
    # Wait for processing (with timeout)
    max_wait = 5  # seconds
    wait_interval = 0.5
    waited = 0
    
    while waited < max_wait:
        # Check if output file was created
        output_files = list(test_dirs["outputs"].glob("*.hl7"))
        if output_files:
            break
        await asyncio.sleep(wait_interval)
        waited += wait_interval
    
    # Verify output file exists
    assert len(output_files) > 0, "No output file was created"
    
    # Verify input file was moved to processed
    processed_files = list(test_dirs["processed"].glob("*.hl7"))
    assert len(processed_files) == 1, "Input file was not moved to processed"
    
    # Verify file contents
    with open(output_files[0], 'r') as f:
        content = f.read()
        assert "ADT^A01" in content, "Output file doesn't contain expected content"
        assert "Doe^John" in content, "Output file is missing expected patient data"

@pytest.mark.asyncio
async def test_invalid_message(engine, test_dirs):
    """Test handling of invalid messages."""
    # Create an invalid HL7 file (missing MSH segment)
    input_file = test_dirs["inputs"] / "invalid.hl7"
    input_file.write_text("INVALID|MESSAGE|FORMAT")
    
    # Wait for processing (with timeout)
    max_wait = 3  # seconds
    wait_interval = 0.5
    waited = 0
    
    while waited < max_wait:
        # Check if error file was created
        error_files = list(test_dirs["errors"].glob("*.hl7"))
        if error_files:
            break
        await asyncio.sleep(wait_interval)
        waited += wait_interval
    
    # Verify error file exists
    assert len(error_files) > 0, "No error file was created"
    
    # Verify input file was moved to errors
    assert "invalid" in error_files[0].name.lower(), "Invalid file was not moved to errors"

@pytest.mark.asyncio
async def test_multiple_messages(engine, test_dirs):
    """Test processing multiple messages."""
    # Create multiple test files
    num_messages = 5
    for i in range(num_messages):
        input_file = test_dirs["inputs"] / f"test_{i}.hl7"
        input_file.write_text(SAMPLE_HL7.replace("MSG00001", f"MSG{i:05d}"))
    
    # Wait for processing (with timeout)
    max_wait = 10  # seconds
    wait_interval = 0.5
    waited = 0
    
    while waited < max_wait:
        # Check if all output files were created
        output_files = list(test_dirs["outputs"].glob("*.hl7"))
        if len(output_files) >= num_messages:
            break
        await asyncio.sleep(wait_interval)
        waited += wait_interval
    
    # Verify all messages were processed
    assert len(output_files) == num_messages, f"Expected {num_messages} output files, got {len(output_files)}"
    
    # Verify all input files were moved to processed
    processed_files = list(test_dirs["processed"].glob("*.hl7"))
    assert len(processed_files) == num_messages, f"Expected {num_messages} processed files, got {len(processed_files)}"

if __name__ == "__main__":
    # Run tests
    import sys
    sys.exit(pytest.main(["-v", __file__]))
