# Integration Engine Scenarios

This document describes the key integration scenarios supported by the Integration Engine.

## Scenario 1: HL7 over MLLP

### Description
Process an HL7v2 message received via MLLP and route it to the appropriate destination.

### Flow
1. HL7 message received via MLLP on port 2575
2. Message validated and parsed
3. Transformed to internal format
4. Routed based on message type
5. Sent to destination system

### Test Data
```hl7
MSH|^~\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|20230629120000||ADT^A01|MSG00001|P|2.3
EVN|A01|20230629120000
PID|1||12345||Doe^John^^^Mr.||19700101|M||2106-3|123 Main St^^Anytown^CA^12345^USA
```

### Test Command
```bash
# Start the MLLP listener
python -m integration_engine.services.input.hl7v2_listener \
  --output-queue raw_messages \
  --mllp-host 0.0.0.0 \
  --mllp-port 2575

# Send test message (in a separate terminal)
python tests/integration/scripts/send_hl7_mllp.py tests/data/hl7_messages/adt_a01.hl7
```

## Scenario 2: HL7v2 from File

### Description
Process an HL7v2 message from a file and route it to the appropriate destination.

### Flow
1. File detected in watched directory
2. File content validated as HL7
3. Message processed through pipeline
4. File moved to processed directory
5. Output generated based on routing rules

### Test Data
Create a file `test.hl7` in the watched directory with HL7 content.

### Test Command
```bash
# Start the file watcher
python -m integration_engine.services.input.hl7v2_listener \
  --output-queue raw_messages \
  --file-watcher-dir /path/to/watch \
  --file-pattern "*.hl7"

# Copy test file to watched directory
cp tests/data/hl7_messages/adt_a01.hl7 /path/to/watch/
```

## Scenario 3: FHIR over REST

### Description
Process a FHIR resource received via REST API and route it to the appropriate destination.

### Flow
1. FHIR resource received via REST API
2. Resource validated against FHIR schema
3. Processed through transformation pipeline
4. Routed based on resource type
5. Sent to destination system

### Test Data
```json
{
  "resourceType": "Patient",
  "name": [{"use": "official", "family": "Doe", "given": ["John"]}],
  "gender": "male",
  "birthDate": "1970-01-01"
}
```

### Test Command
```bash
# Start the FHIR listener
python -m integration_engine.services.input.fhir_listener \
  --output-queue fhir_messages \
  --host 0.0.0.0 \
  --port 8000

# Send test resource (in a separate terminal)
curl -X POST http://localhost:8000/fhir/Patient \
  -H "Content-Type: application/fhir+json" \
  -d @tests/data/fhir_resources/patient.json
```

## Scenario 4: End-to-End Processing

### Description
Complete end-to-end test of the integration pipeline with all components.

### Flow
1. Message received via any input method
2. Processed through validation
3. Transformed as needed
4. Routed to appropriate output
5. Output verified

### Test Command
```bash
# Start all services
docker-compose -f docker-compose.test.yml up -d

# Run end-to-end tests
pytest tests/e2e/test_hl7_workflow.py -v
pytest tests/e2e/test_fhir_workflow.py -v

# View logs
docker-compose -f docker-compose.test.yml logs -f
```

## Scenario 5: Error Handling

### Description
Test error handling and recovery scenarios.

### Test Cases
1. **Invalid Message**
   - Send malformed HL7/FHIR message
   - Verify error is logged
   - Verify error response is returned

2. **Service Unavailable**
   - Stop a downstream service
   - Send message
   - Verify retry mechanism
   - Verify message is not lost

3. **Network Issues**
   - Block network access to Redis
   - Verify queue manager handles disconnection
   - Verify reconnection when network is restored

### Test Command
```bash
# Run error handling tests
pytest tests/integration/test_error_handling.py -v
```

## Performance Testing

### Description
Test the system under load to verify performance characteristics.

### Test Cases
1. **Throughput Test**
   - Send 1000 messages
   - Measure messages/second
   - Verify no message loss

2. **Latency Test**
   - Measure end-to-end processing time
   - Identify bottlenecks

### Test Command
```bash
# Run performance tests
pytest tests/performance/test_throughput.py -v
pytest tests/performance/test_latency.py -v
```

## Monitoring and Observability

### Metrics
- Message processing rate
- Error rates
- Queue lengths
- Processing latency

### Logging
- Structured JSON logs
- Correlation IDs for tracing
- Log levels (DEBUG, INFO, WARNING, ERROR)

### Monitoring
- Prometheus metrics endpoint
- Grafana dashboards
- Alerting rules

### Commands
```bash
# View metrics
curl http://localhost:9090/metrics

# View logs
docker-compose logs -f

# Access Grafana
open http://localhost:3000
```
