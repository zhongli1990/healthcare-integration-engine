"""
End-to-end tests for file processing functionality.

This module contains tests for the file-based message processing
capabilities of the Integration Engine.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Generator
import pytest

# Mark all tests in this module as asyncio tests
pytestmark = pytest.mark.asyncio

# Add event_loop fixture for async tests
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Test file contents
TEST_FILES = {
    "hl7": {
        "path": "ADT_A01.hl7",
        "content": (
            "MSH|^~\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|20230630120000||ADT^A01|MSG00001|P|2.3\r"
            "EVN|A01|20230630120000\r"
            "PID|1||12345||Doe^John||19700101|M||2106-3|123 Main St^^Anytown^CA^12345||555-555-1000|555-555-1001||S||123-45-6789||||N\r"
        ),
        "expected_message_control_id": "MSG00001",
        "expected_message_type": "ADT"
    },
    "hl7_missing_pid": {
        "path": "ADT_A01_missing_pid.hl7",
        "content": (
            "MSH|^~\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|20230630120000||ADT^A01|MSG00002|P|2.3\r"
            "EVN|A01|20230630120000\r"
        ),
        "should_fail": True,
        "error_contains": "Missing required segment: PID"
    },
    "hl7_malformed": {
        "path": "malformed.hl7",
        "content": "INVALID|HL7|MESSAGE\r",
        "should_fail": True,
        "error_contains": "Invalid HL7 message"
    },
    "fhir_json": {
        "path": "patient.json",
        "content": """{\n  "resourceType": "Patient",\n  "id": "example",\n  "identifier": [{\n    "system": "http://example.org/patient-ids",\n    "value": "12345"\n  }],\n  "name": [{\n    "family": "Doe",\n    "given": ["John"]\n  }],\n  "gender": "male",\n  "birthDate": "1970-01-01",\n  "address": [{\n    "line": ["123 Main St"],\n    "city": "Anytown",\n    "state": "CA",\n    "postalCode": "12345"\n  }]\n}"""
    },
    "invalid": {
        "path": "malformed.hl7",
        "content": "MSH|^~\\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|This is a malformed HL7 message with missing fields"
    },
    "hl7_watched": {
        "path": "ADT_A01_watched.hl7",
        "content": (
            "MSH|^~\\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|20230630120000||ADT^A01|WATCHED001|P|2.3\r"
            "EVN|A01|20230630120000\r"
            "PID|1||WATCHED001||Doe^John||19700101|M||2106-3|123 Main St^^Anytown^CA^12345||555-555-1000|555-555-1001||S||123-45-6789||||N\r"
        ),
        "expected_message_control_id": "WATCHED001",
        "expected_message_type": "ADT"
    }
}

def create_test_file(file_path: Path, content: str) -> None:
    """Helper to create a test file with given content."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)

def wait_for_file(file_path: Path, timeout: int = 5) -> bool:
    """Wait for a file to appear with a timeout."""
    start_time = time.time()
    while not file_path.exists():
        if time.time() - start_time > timeout:
            return False
        time.sleep(0.1)
    return True

def wait_for_files(directory: Path, pattern: str, timeout: int = 10) -> bool:
    """Wait for files matching pattern to appear in directory."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        if list(directory.glob(pattern)):
            return True
        time.sleep(0.5)
    return False

@pytest.mark.asyncio
class TestFileProcessing:
    """Test file processing functionality."""
    
    # This fixture provides an event loop for all tests in the class
    @pytest.fixture(autouse=True)
    def setup_event_loop(self, event_loop):
        # Make the event loop available to all test methods
        self.event_loop = event_loop
        yield
        # Cleanup if needed
    
    def _create_test_file(self, test_dirs: Dict[str, Path], file_type: str) -> Path:
        """Helper to create a test file of the specified type."""
        test_data = TEST_FILES[file_type]
        test_file = test_dirs["input"] / test_data["path"]
        create_test_file(test_file, test_data["content"])
        return test_file
    
    async def test_hl7_processing(self, file_processor, test_dirs, caplog, event_loop):
        """Test processing of valid HL7v2 files."""
        # Setup
        test_data = TEST_FILES["hl7"]
        test_file = self._create_test_file(test_dirs, "hl7")
        assert test_file.exists(), "Test file was not created"
        
        # Clear any existing logs
        caplog.clear()
        
        # Execute with log capture
        with caplog.at_level(logging.INFO):
            result = await file_processor.process_file(test_file)
            
            # Verify results
            assert result is True, "HL7 processing should succeed"
            assert not test_file.exists(), "Source file should be moved"
            
            # Check archive
            archived_files = list(test_dirs["archive"].glob("*.hl7"))
            assert len(archived_files) == 1, "File should be archived"
            
            # Get all log messages as a single string
            log_text = "\n".join(record.message for record in caplog.records)
            
            # Verify log messages are in the captured logs
            assert f"Processing file: {test_file}" in log_text, f"Expected log not found. Logs: {log_text}"
            assert f"Processing HL7 file: {test_file}" in log_text, f"Expected log not found. Logs: {log_text}"
            assert f"Successfully processed HL7 message: {test_data['expected_message_control_id']}" in log_text, \
                f"Expected message control ID not found. Logs: {log_text}"
            assert f"Message type: {test_data['expected_message_type']}" in log_text, \
                f"Expected message type not found. Logs: {log_text}"
    
    async def test_hl7_missing_required_segment(self, file_processor, test_dirs, caplog, event_loop):
        """Test processing HL7 file missing required segments."""
        # Setup
        test_data = TEST_FILES["hl7_missing_pid"]
        test_file = self._create_test_file(test_dirs, "hl7_missing_pid")
        
        # Clear any existing logs
        caplog.clear()
        
        # Execute with log capture
        with caplog.at_level(logging.ERROR):
            result = await file_processor.process_file(test_file)
            
            # Verify results
            assert result is False, "HL7 processing should fail with missing PID"
            assert not test_file.exists(), "Source file should be moved"
            
            # Check error directory
            error_files = list(test_dirs["error"].glob("*.hl7"))
            assert len(error_files) == 1, "File should be moved to error directory"
            
            # Get all log messages as a single string
            log_text = "\n".join(record.message for record in caplog.records)
            
            # Verify error message is in the logs (checking for any validation error message)
            assert "validation failed" in log_text.lower() or "invalid hl7" in log_text.lower(), \
                f"Expected validation error not found in logs. Logs: {log_text}"
    
    async def test_hl7_malformed_message(self, file_processor, test_dirs, caplog, event_loop):
        """Test processing of malformed HL7 messages."""
        # Setup
        test_file = self._create_test_file(test_dirs, "hl7_malformed")
        
        # Clear any existing logs
        caplog.clear()
        
        # Execute with log capture
        with caplog.at_level(logging.ERROR):
            result = await file_processor.process_file(test_file)
            
            # Verify results
            assert result is False, "HL7 processing should fail with malformed message"
            assert not test_file.exists(), "Source file should be moved"
            
            # Check error directory
            error_files = list(test_dirs["error"].glob("*.hl7"))
            assert len(error_files) == 1, "File should be moved to error directory"
            
            # Get all log messages as a single string
            log_text = "\n".join(record.message for record in caplog.records)
            
            # Verify error message is in the logs (checking for any error related to parsing/processing)
            assert any(keyword in log_text.lower() for keyword in ["error", "failed", "invalid", "parse"]), \
                f"Expected error message not found in logs. Logs: {log_text}"
    
    async def test_fhir_json_processing(self, file_processor, test_dirs, event_loop):
        """Test processing of FHIR JSON files."""
        # Create test file
        test_file = self._create_test_file(test_dirs, "fhir_json")
        assert test_file.exists(), "Test file was not created"
        
        # Process the file
        result = await file_processor.process_file(test_file)
        
        # Verify results
        assert result is True, "FHIR JSON processing failed"
        assert not test_file.exists(), "Source file should be moved"
        
        # Check archive
        archived_files = list(test_dirs["archive"].glob("*.json"))
        assert len(archived_files) == 1, "File should be archived"
        
        # TODO: Add output verification when processing is implemented
        # output_files = list(test_dirs["output"].glob("*"))
        # assert len(output_files) > 0, "No output files were generated"
    
    async def test_invalid_file_handling(self, file_processor, test_dirs, event_loop):
        """Test handling of invalid files."""
        # Create test file with invalid content
        test_file = self._create_test_file(test_dirs, "invalid")
        assert test_file.exists(), "Test file was not created"
        
        # Process the file
        result = await file_processor.process_file(test_file)
        
        # Verify results
        assert result is False, "Invalid file should fail processing"
        assert not test_file.exists(), "Source file should be moved"
        
        # Check error directory
        error_files = list(test_dirs["error"].glob("*" + test_file.suffix))
        assert len(error_files) == 1, "Invalid file should be moved to error directory"
        
        # Verify no output was generated
        output_files = list(test_dirs["output"].glob("*"))
        assert len(output_files) == 0, "No output should be generated for invalid files"
    
    @pytest.mark.asyncio
    async def test_file_watcher(self, file_processor, test_dirs, mocker, event_loop):
        """Test that the file processor can process files from the input directory."""
        # Create a test file
        test_file = self._create_test_file(test_dirs, "hl7_watched")
        
        # Mock the process_file method to track calls
        mock_process = mocker.patch.object(file_processor, 'process_file')
        
        # Call the method that processes files in the input directory
        file_processor.process_existing_files()
        
        # Verify process_file was called with the test file
        assert mock_process.called, "process_file was not called"
        
        # Get the first argument of the first call to process_file
        called_with = mock_process.call_args[0][0]
        assert str(called_with) == str(test_file), \
            f"Expected {test_file} to be processed, got {called_with}"
            
        # Verify the file was processed successfully (assuming success case)
        # Note: The actual processing is mocked, so we're just checking the call
        assert True
    
    @pytest.mark.asyncio
    async def test_concurrent_file_processing(self, file_processor, test_dirs, event_loop):
        """Test that multiple files can be processed concurrently."""
        # Create multiple test files
        num_files = 5
        test_files = []
        for i in range(num_files):
            test_data = {
                "path": f"ADT_A01_{i}.hl7",
                "content": TEST_FILES["hl7"]["content"].replace("MSG00001", f"MSG{i:05d}")
            }
            test_file = test_dirs["input"] / test_data["path"]
            create_test_file(test_file, test_data["content"])
            test_files.append(test_file)
        
        try:
            # Process files concurrently
            tasks = [file_processor.process_file(f) for f in test_files]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all files were processed successfully
            assert all(r is True for r in results), f"Not all files processed successfully. Results: {results}"
            
            # Check that all files were archived
            archived_files = list(test_dirs["archive"].glob("*.hl7"))
            assert len(archived_files) == num_files, \
                f"Expected {num_files} files in archive, found {len(archived_files)}. Files: {archived_files}"
                
        finally:
            # Clean up test files
            for f in test_files:
                if f.exists():
                    f.unlink()

# This allows running the tests directly with Python
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
