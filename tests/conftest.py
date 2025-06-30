"""Pytest configuration and fixtures for integration engine tests."""

import os
import shutil
from pathlib import Path
import pytest

# Test directory structure
TEST_BASE_DIR = Path("/app/tests/data")
TEST_INPUT_DIR = TEST_BASE_DIR / "inputs"
TEST_ARCHIVE_DIR = TEST_BASE_DIR / "archive"
TEST_OUTPUT_DIR = TEST_BASE_DIR / "outputs"
TEST_ERROR_DIR = TEST_BASE_DIR / "errors"

@pytest.fixture
def test_dirs():
    """Create and clean up test directories before each test."""
    # Clean up any existing test files
    for directory in [TEST_INPUT_DIR, TEST_ARCHIVE_DIR, TEST_OUTPUT_DIR, TEST_ERROR_DIR]:
        shutil.rmtree(directory, ignore_errors=True)
        directory.mkdir(parents=True, exist_ok=True)
    
    # Return the directory paths
    return {
        "input": TEST_INPUT_DIR,
        "archive": TEST_ARCHIVE_DIR,
        "output": TEST_OUTPUT_DIR,
        "error": TEST_ERROR_DIR
    }

@pytest.fixture
def file_processor(test_dirs, mocker):
    """Fixture that provides a configured FileProcessor instance."""
    # Mock the observer to avoid threading issues in tests
    mocker.patch('watchdog.observers.Observer')
    
    from integration_engine.processing.file_processor import FileProcessor
    
    processor = FileProcessor(
        input_dir=str(test_dirs["input"]),
        output_dir=str(test_dirs["output"]),
        archive_dir=str(test_dirs["archive"]),
        error_dir=str(test_dirs["error"])
    )
    
    # Don't start the observer in tests
    processor.observer = mocker.MagicMock()
    
    return processor
