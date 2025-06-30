"""
Integration tests for the Integration Engine.

This module contains tests that verify the end-to-end functionality
of the integration engine with various message types and workflows.
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional

import pytest
import yaml
from pydantic import BaseModel

# Import the integration engine components
from integration_engine.orchestrator import IntegrationEngine, create_engine
from integration_engine.core.config import load_config
from integration_engine.core.queues.queue_manager import QueueManager
from integration_engine.core.models.message import MessageEnvelope, MessageHeader, MessageBody

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"

# Sample HL7 v2 message for testing
SAMPLE_HL7V2_MESSAGE = """MSH|^~\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|20230628120000||ADT^A01|MSG00001|P|2.3||||||UNICODE UTF-8
EVN|A01|20230628120000|||SENDER_ID^SENDER_NAME^SENDER_ROLE
PID|1||12345||Doe^John^M^Jr^Dr.^^^L|19900101|M||2106-3|123 Main St^^Anytown^CA^12345^USA^P||555-555-1234|555-555-5678|EN|S||123-45-6789|123-45-6789|||2186-5^Not Hispanic or Latino^CDCREC|N|1||||||N"""

# Sample FHIR Patient resource for testing
SAMPLE_FHIR_PATIENT = {
    "resourceType": "Patient",
    "id": "example",
    "meta": {
        "versionId": "1",
        "lastUpdated": "2023-06-28T12:00:00Z",
        "source": "#N4fPy5YPdZtEjUFUeR2RVA"
    },
    "text": {
        "status": "generated",
        "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\"><div class=\"hapiHeaderText\">John <b>DOE</b></div><table class=\"hapiPropertyTable\"><tbody><tr><td>Identifier</td><td>12345</td></tr></tbody></table></div>"
    },
    "identifier": [
        {
            "use": "usual",
            "type": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "MR"
                    }
                ]
            },
            "system": "urn:oid:1.2.36.146.595.217.0.1",
            "value": "12345",
            "period": {
                "start": "2001-05-06"
            },
            "assigner": {
                "display": "Acme Healthcare"
            }
        }
    ],
    "active": True,
    "name": [
        {
            "use": "official",
            "family": "Doe",
            "given": ["John"]
        }
    ],
    "telecom": [
        {
            "system": "phone",
            "value": "555-555-1234",
            "use": "home"
        },
        {
            "system": "email",
            "value": "john.doe@example.com",
            "use": "home"
        }
    ],
    "gender": "male",
    "birthDate": "1990-01-01",
    "address": [
        {
            "use": "home",
            "type": "both",
            "line": ["123 Main St"],
            "city": "Anytown",
            "state": "CA",
            "postalCode": "12345",
            "country": "USA"
        }
    ]
}


class TestIntegrationEngine:
    """Test suite for the Integration Engine."""
    
    @pytest.fixture
    def test_config_file(self, tmp_path):
        """Create a temporary test configuration file."""
        config = {
            "global": {
                "log_level": "DEBUG",
                "environment": "test",
                "instance_id": "test-engine-001"
            },
            "queues": {
                "type": "memory",
                "memory": {
                    "max_size": 1000
                }
            },
            "inbound": {
                "hl7v2_listener": {
                    "enabled": True,
                    "host": "0.0.0.0",
                    "port": 2575,
                    "input_queue": "test_inbound_hl7v2_messages"
                },
                "fhir_listener": {
                    "enabled": True,
                    "host": "0.0.0.0",
                    "port": 8080,
                    "input_queue": "test_inbound_fhir_messages"
                }
            },
            "processing": {
                "validation": {
                    "enabled": True,
                    "input_queue": "test_inbound_messages",
                    "output_queue": "test_validated_messages",
                    "error_queue": "test_validation_errors"
                },
                "transformation": {
                    "enabled": True,
                    "input_queue": "test_validated_messages",
                    "output_queue": "test_transformed_messages",
                    "error_queue": "test_transformation_errors"
                },
                "routing": {
                    "enabled": True,
                    "input_queue": "test_transformed_messages",
                    "default_route": "test_unrouted_messages",
                    "error_queue": "test_routing_errors"
                }
            },
            "outbound": {
                "hl7v2_sender": {
                    "enabled": True,
                    "host": "localhost",
                    "port": 2576,
                    "input_queue": "test_outbound_hl7v2_messages",
                    "error_queue": "test_outbound_hl7v2_errors"
                },
                "fhir_sender": {
                    "enabled": True,
                    "base_url": "http://hapi.fhir.org/baseR4",
                    "input_queue": "test_outbound_fhir_messages",
                    "error_queue": "test_outbound_fhir_errors"
                },
                "file_sender": {
                    "enabled": True,
                    "output_dir": str(tmp_path / "output"),
                    "input_queue": "test_outbound_file_messages",
                    "error_queue": "test_outbound_file_errors"
                }
            }
        }
        
        # Create the config file
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        return str(config_file)
    
    @pytest.fixture
    async def engine(self, test_config_file):
        """Create and initialize an integration engine for testing."""
        # Load the test config
        config = load_config(test_config_file)
        
        # Create and initialize the engine
        engine = create_engine(config.dict())
        await engine.initialize()
        
        yield engine
        
        # Cleanup
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_hl7v2_message_flow(self, engine, tmp_path):
        """Test the end-to-end flow of an HL7 v2 message through the engine."""
        # Get the queue manager
        queue_manager = engine.queue_manager
        
        # Create a test message
        message = MessageEnvelope(
            header=MessageHeader(
                message_id="test-msg-001",
                message_type="ADT_A01",
                content_type="application/hl7-v2+er7",
                source="test_source",
                destination="test_destination",
                timestamp=time.time(),
                metadata={
                    "test": True,
                    "test_case": "hl7v2_message_flow"
                }
            ),
            body=MessageBody(
                content=SAMPLE_HL7V2_MESSAGE,
                content_type="application/hl7-v2+er7",
                encoding="utf-8",
                is_compressed=False
            )
        )
        
        # Publish the message to the HL7 v2 input queue
        await queue_manager.publish("test_inbound_hl7v2_messages", message.model_dump_json())
        
        # TODO: Add assertions to verify the message flows through the system
        # This would typically involve:
        # 1. Subscribing to the relevant output queues
        # 2. Verifying the message is processed correctly at each step
        # 3. Checking the final output (e.g., file, HTTP response, etc.)
        
        # For now, just sleep to allow processing (in a real test, we'd use asyncio.wait_for with a timeout)
        await asyncio.sleep(1)
        
        # Verify the message was processed by checking the output queues
        # This is a simplified example - in a real test, you'd want to be more thorough
        processed_messages = await queue_manager.get_messages("test_outbound_file_messages", count=10)
        assert len(processed_messages) > 0, "No messages were processed"
    
    @pytest.mark.asyncio
    async def test_fhir_message_flow(self, engine, tmp_path):
        """Test the end-to-end flow of a FHIR message through the engine."""
        # Get the queue manager
        queue_manager = engine.queue_manager
        
        # Create a test message
        message = MessageEnvelope(
            header=MessageHeader(
                message_id="test-msg-002",
                message_type="Patient",
                content_type="application/fhir+json",
                source="test_source",
                destination="test_destination",
                timestamp=time.time(),
                metadata={
                    "test": True,
                    "test_case": "fhir_message_flow"
                }
            ),
            body=MessageBody(
                content=json.dumps(SAMPLE_FHIR_PATIENT),
                content_type="application/fhir+json",
                encoding="utf-8",
                is_compressed=False
            )
        )
        
        # Publish the message to the FHIR input queue
        await queue_manager.publish("test_inbound_fhir_messages", message.model_dump_json())
        
        # TODO: Add assertions to verify the message flows through the system
        # This would typically involve:
        # 1. Subscribing to the relevant output queues
        # 2. Verifying the message is processed correctly at each step
        # 3. Checking the final output (e.g., file, HTTP response, etc.)
        
        # For now, just sleep to allow processing (in a real test, we'd use asyncio.wait_for with a timeout)
        await asyncio.sleep(1)
        
        # Verify the message was processed by checking the output queues
        # This is a simplified example - in a real test, you'd want to be more thorough
        processed_messages = await queue_manager.get_messages("test_outbound_file_messages", count=10)
        assert len(processed_messages) > 0, "No messages were processed"
    
    @pytest.mark.asyncio
    async def test_message_transformation(self, engine):
        """Test message transformation between formats."""
        # TODO: Implement test for message transformation
        # This would test that messages can be converted between HL7 v2 and FHIR formats
        pass
    
    @pytest.mark.asyncio
    async def test_error_handling(self, engine):
        """Test error handling for invalid messages."""
        # TODO: Implement test for error handling
        # This would test that invalid messages are properly handled and routed to error queues
        pass
    
    @pytest.mark.asyncio
    async def test_performance(self, engine):
        """Test the performance of the integration engine."""
        # TODO: Implement performance testing
        # This would test the engine's ability to handle high message volumes
        pass


if __name__ == "__main__":
    # Run the tests
    import sys
    sys.exit(pytest.main(["-v", "-s", __file__]))
