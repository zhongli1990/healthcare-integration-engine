"""Performance tests for the Integration Engine."""
import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Any
import statistics
import pytest
import aiohttp
from aiohttp import ClientSession

# Test configuration
MESSAGES_PER_TEST = 100
WARMUP_MESSAGES = 10
TEST_ITERATIONS = 3

@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for the test module."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

class TestPerformance:
    """Performance test suite for the Integration Engine."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_hl7_throughput(self):
        """Test HL7 message processing throughput."""
        # Warmup
        print("\n=== Warming up HL7 throughput test ===")
        await self._run_hl7_test_batch(WARMUP_MESSAGES)
        
        # Run test iterations
        results = []
        for i in range(TEST_ITERATIONS):
            print(f"\n=== HL7 Throughput Test Iteration {i+1}/{TEST_ITERATIONS} ===")
            duration = await self._run_hl7_test_batch(MESSAGES_PER_TEST)
            msg_per_sec = MESSAGES_PER_TEST / duration
            results.append(msg_per_sec)
            print(f"Iteration {i+1}: {msg_per_sec:.2f} messages/second")
        
        # Calculate and report statistics
        avg = statistics.mean(results)
        median = statistics.median(results)
        stdev = statistics.stdev(results) if len(results) > 1 else 0
        
        print("\n=== HL7 Throughput Results ===")
        print(f"Messages per test: {MESSAGES_PER_TEST}")
        print(f"Test iterations: {TEST_ITERATIONS}")
        print(f"Average: {avg:.2f} msg/sec")
        print(f"Median: {median:.2f} msg/sec")
        print(f"Std Dev: {stdev:.2f} msg/sec")
        
        # Assert performance meets minimum requirements
        assert avg > 50, "HL7 throughput below expected minimum of 50 msg/sec"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_fhir_throughput(self):
        """Test FHIR resource processing throughput."""
        # Warmup
        print("\n=== Warming up FHIR throughput test ===")
        await self._run_fhir_test_batch(WARMUP_MESSAGES)
        
        # Run test iterations
        results = []
        for i in range(TEST_ITERATIONS):
            print(f"\n=== FHIR Throughput Test Iteration {i+1}/{TEST_ITERATIONS} ===")
            duration = await self._run_fhir_test_batch(MESSAGES_PER_TEST)
            msg_per_sec = MESSAGES_PER_TEST / duration
            results.append(msg_per_sec)
            print(f"Iteration {i+1}: {msg_per_sec:.2f} messages/second")
        
        # Calculate and report statistics
        avg = statistics.mean(results)
        median = statistics.median(results)
        stdev = statistics.stdev(results) if len(results) > 1 else 0
        
        print("\n=== FHIR Throughput Results ===")
        print(f"Messages per test: {MESSAGES_PER_TEST}")
        print(f"Test iterations: {TEST_ITERATIONS}")
        print(f"Average: {avg:.2f} msg/sec")
        print(f"Median: {median:.2f} msg/sec")
        print(f"Std Dev: {stdev:.2f} msg/sec")
        
        # Assert performance meets minimum requirements
        assert avg > 30, "FHIR throughput below expected minimum of 30 msg/sec"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_mixed_workload(self):
        """Test mixed HL7 and FHIR message processing."""
        total_messages = MESSAGES_PER_TEST * 2  # HL7 + FHIR
        
        # Warmup
        print("\n=== Warming up mixed workload test ===")
        await asyncio.gather(
            self._run_hl7_test_batch(WARMUP_MESSAGES // 2),
            self._run_fhir_test_batch(WARMUP_MESSAGES // 2)
        )
        
        # Run test iterations
        results = []
        for i in range(TEST_ITERATIONS):
            print(f"\n=== Mixed Workload Test Iteration {i+1}/{TEST_ITERATIONS} ===")
            
            start_time = time.time()
            
            # Run HL7 and FHIR tests in parallel
            await asyncio.gather(
                self._run_hl7_test_batch(MESSAGES_PER_TEST),
                self._run_fhir_test_batch(MESSAGES_PER_TEST)
            )
            
            duration = time.time() - start_time
            msg_per_sec = total_messages / duration
            results.append(msg_per_sec)
            print(f"Iteration {i+1}: {msg_per_sec:.2f} messages/second")
        
        # Calculate and report statistics
        avg = statistics.mean(results)
        median = statistics.median(results)
        stdev = statistics.stdev(results) if len(results) > 1 else 0
        
        print("\n=== Mixed Workload Results ===")
        print(f"Messages per test: {total_messages} ({MESSAGES_PER_TEST} HL7 + {MESSAGES_PER_TEST} FHIR)")
        print(f"Test iterations: {TEST_ITERATIONS}")
        print(f"Average: {avg:.2f} msg/sec")
        print(f"Median: {median:.2f} msg/sec")
        print(f"Std Dev: {stdev:.2f} msg/sec")
        
        # Assert performance meets minimum requirements
        assert avg > 40, "Mixed workload throughput below expected minimum of 40 msg/sec"

    async def _run_hl7_test_batch(self, num_messages: int) -> float:
        """Run a batch of HL7 message tests and return the duration in seconds."""
        test_message = """MSH|^~\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|20230629120000||ADT^A01|MSG00001|P|2.3
EVN|A01|20230629120000
PID|1||12345||Doe^John^^^Mr.||19700101|M||2106-3|123 Main St^^Anytown^CA^12345^USA"""
        
        start_time = time.time()
        
        async with ClientSession() as session:
            tasks = []
            for i in range(num_messages):
                # Create unique message ID
                msg_id = f"PERF_TEST_{i}_{int(time.time())}"
                message = test_message.replace("MSG00001", msg_id)
                
                # Create task for sending message
                task = asyncio.create_task(
                    self._send_hl7_message(session, message)
                )
                tasks.append(task)
                
                # Add small delay to avoid overwhelming the system
                if i % 10 == 0:
                    await asyncio.sleep(0.01)
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
        
        return time.time() - start_time

    async def _run_fhir_test_batch(self, num_messages: int) -> float:
        """Run a batch of FHIR resource tests and return the duration in seconds."""
        base_patient = {
            "resourceType": "Patient",
            "name": [{"family": "PerfTest", "given": ["Patient"]}],
            "gender": "unknown",
            "birthDate": "2000-01-01"
        }
        
        start_time = time.time()
        
        async with ClientSession() as session:
            tasks = []
            for i in range(num_messages):
                # Create unique patient
                patient = base_patient.copy()
                patient["name"][0]["given"] = [f"Patient{i}"]
                
                # Create task for sending FHIR resource
                task = asyncio.create_task(
                    self._send_fhir_resource(session, "Patient", patient)
                )
                tasks.append(task)
                
                # Add small delay to avoid overwhelming the system
                if i % 10 == 0:
                    await asyncio.sleep(0.01)
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
        
        return time.time() - start_time

    async def _send_hl7_message(self, session: ClientSession, message: str) -> Dict[str, Any]:
        """Send an HL7 message via MLLP and return the response."""
        mllp_start = '\x0b'
        mllp_end = '\x1c\r'
        
        try:
            reader, writer = await asyncio.open_connection('localhost', 2575)
            
            # Send message
            writer.write(f"{mllp_start}{message}{mllp_end}".encode())
            await writer.drain()
            
            # Read response
            response = await reader.read(1024)
            
            # Cleanup
            writer.close()
            await writer.wait_closed()
            
            return {"status": "success", "response": response}
            
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _send_fhir_resource(self, session: ClientSession, resource_type: str, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Send a FHIR resource via REST API and return the response."""
        url = f"http://localhost:8000/fhir/{resource_type}"
        
        try:
            async with session.post(
                url,
                json=resource,
                headers={"Content-Type": "application/fhir+json"}
            ) as response:
                result = await response.json()
                return {
                    "status": "success",
                    "status_code": response.status,
                    "result": result
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
