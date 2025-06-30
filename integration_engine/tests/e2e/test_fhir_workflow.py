"""End-to-end tests for FHIR workflow."""
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

import pytest
import aiohttp
from aiohttp import ClientSession, web

from integration_engine.core.queues.queue_manager import QueueManager
from integration_engine.core.models.message import MessageEnvelope, MessageHeader, MessageBody, MessageStatus

# Test configuration
TEST_DATA_DIR = Path(__file__).parent.parent / "data"
FHIR_RESOURCES_DIR = TEST_DATA_DIR / "fhir_resources"
OUTPUT_DIR = TEST_DATA_DIR / "outputs"
PROCESSED_DIR = TEST_DATA_DIR / "processed"
ERRORS_DIR = TEST_DATA_DIR / "errors"

# Ensure test directories exist
for directory in [OUTPUT_DIR, PROCESSED_DIR, ERRORS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for the test module."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def queue_manager():
    """Create a QueueManager instance for testing."""
    manager = QueueManager(redis_url="redis://localhost:6379/0")
    yield manager
    await manager.close()

class TestFHIRWorkflow:
    """Test suite for FHIR workflow scenarios."""

    @pytest.mark.asyncio
    async def test_fhir_rest_workflow(self, queue_manager):
        """Test end-to-end FHIR REST API workflow."""
        # Load test data
        patient_data = json.loads((FHIR_RESOURCES_DIR / "patient.json").read_text())
        
        # Send FHIR resource via REST API
        async with ClientSession() as session:
            async with session.post(
                "http://localhost:8000/fhir/Patient",
                json=patient_data,
                headers={"Content-Type": "application/fhir+json"}
            ) as response:
                assert response.status in (200, 201), f"Unexpected status code: {response.status}"
                result = await response.json()
                patient_id = result.get("id")
                assert patient_id is not None, "No patient ID in response"
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Verify output
        output_files = list(OUTPUT_DIR.glob("*.json"))
        assert len(output_files) > 0, "No output files found"
        
        # Verify message content
        output_content = json.loads(output_files[0].read_text())
        assert output_content["resourceType"] == "Patient"
        assert output_content["name"][0]["family"] == patient_data["name"][0]["family"]
        
        # Cleanup
        output_files[0].unlink()

    @pytest.mark.asyncio
    async def test_fhir_bundle_workflow(self, queue_manager):
        """Test processing a FHIR Bundle resource."""
        # Load test data
        bundle_data = json.loads((FHIR_RESOURCES_DIR / "bundle-transaction.json").read_text())
        
        # Send FHIR Bundle via REST API
        async with ClientSession() as session:
            async with session.post(
                "http://localhost:8000/fhir",
                json=bundle_data,
                headers={"Content-Type": "application/fhir+json"}
            ) as response:
                assert response.status in (200, 201), f"Unexpected status code: {response.status}"
                result = await response.json()
                assert result["resourceType"] == "Bundle"
                assert len(result.get("entry", [])) > 0
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Verify output (should have one file per entry in the bundle)
        output_files = list(OUTPUT_DIR.glob("bundle_*.json"))
        assert len(output_files) >= 1, "No output files found for bundle entries"
        
        # Cleanup
        for file in output_files:
            file.unlink()

    @pytest.mark.asyncio
    async def test_fhir_error_handling(self, queue_manager):
        """Test error handling for invalid FHIR resources."""
        # Send invalid FHIR resource
        invalid_resource = {"resourceType": "Patient", "invalidField": "value"}
        
        async with ClientSession() as session:
            async with session.post(
                "http://localhost:8000/fhir/Patient",
                json=invalid_resource,
                headers={"Content-Type": "application/fhir+json"}
            ) as response:
                assert response.status == 400, "Expected 400 for invalid resource"
                error = await response.json()
                assert "error" in error or "issue" in error
        
        # Verify error file was created
        error_files = list(ERRORS_DIR.glob("*.err"))
        assert len(error_files) > 0, "No error files found"
        
        # Verify error content
        error_content = error_files[0].read_text()
        assert "ValidationError" in error_content or "error" in error_content
        
        # Cleanup
        error_files[0].unlink()

    @pytest.mark.asyncio
    async def test_fhir_search(self, queue_manager):
        """Test FHIR search functionality."""
        # First create a test patient
        patient_data = {
            "resourceType": "Patient",
            "name": [{"family": "TestSearch", "given": ["John"]}],
            "gender": "male",
            "birthDate": "1970-01-01"
        }
        
        # Create patient
        async with ClientSession() as session:
            # Create
            async with session.post(
                "http://localhost:8000/fhir/Patient",
                json=patient_data,
                headers={"Content-Type": "application/fhir+json"}
            ) as response:
                assert response.status in (200, 201)
                result = await response.json()
                patient_id = result["id"]
            
            # Search
            async with session.get(
                f"http://localhost:8000/fhir/Patient?family=TestSearch",
                headers={"Accept": "application/fhir+json"}
            ) as response:
                assert response.status == 200
                bundle = await response.json()
                assert bundle["resourceType"] == "Bundle"
                assert any(
                    entry["resource"]["id"] == patient_id 
                    for entry in bundle.get("entry", [])
                    if "resource" in entry and "id" in entry["resource"]
                ), "Created patient not found in search results"
            
            # Cleanup
            async with session.delete(
                f"http://localhost:8000/fhir/Patient/{patient_id}",
                headers={"Accept": "application/fhir+json"}
            ) as response:
                assert response.status in (200, 204), f"Failed to delete test patient: {response.status}"

    @pytest.mark.asyncio
    async def test_fhir_high_volume(self, queue_manager):
        """Test processing of multiple FHIR resources."""
        # Create multiple patients
        num_patients = 10
        base_patient = {
            "resourceType": "Patient",
            "name": [{"family": "LoadTest", "given": ["Patient"]}],
            "gender": "unknown",
            "birthDate": "2000-01-01"
        }
        
        created_ids = []
        
        async with ClientSession() as session:
            # Create patients
            for i in range(num_patients):
                patient = base_patient.copy()
                patient["name"][0]["given"] = [f"Patient{i+1}"]
                
                async with session.post(
                    "http://localhost:8000/fhir/Patient",
                    json=patient,
                    headers={"Content-Type": "application/fhir+json"}
                ) as response:
                    assert response.status in (200, 201)
                    result = await response.json()
                    created_ids.append(result["id"])
            
            # Verify all patients were created
            assert len(created_ids) == num_patients
            
            # Wait for processing
            await asyncio.sleep(2)
            
            # Verify output files
            output_files = list(OUTPUT_DIR.glob("patient_*.json"))
            assert len(output_files) >= num_patients, \
                f"Expected at least {num_patients} output files, got {len(output_files)}"
            
            # Cleanup
            for patient_id in created_ids:
                async with session.delete(
                    f"http://localhost:8000/fhir/Patient/{patient_id}",
                    headers={"Accept": "application/fhir+json"}
                ) as response:
                    assert response.status in (200, 204)
