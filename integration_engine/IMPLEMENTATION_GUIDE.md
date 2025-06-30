# Healthcare Integration Engine - Implementation Guide

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Configuration](#configuration)
4. [Running the Engine](#running-the-engine)
5. [Testing](#testing)
6. [Extending the Engine](#extending-the-engine)
7. [Troubleshooting](#troubleshooting)

## Overview

The Healthcare Integration Engine is a modular, event-driven system designed to process healthcare messages (HL7, FHIR) through a configurable pipeline. It supports multiple input and output adapters, with a flexible processing pipeline for validation, transformation, and routing.

## Getting Started

### Prerequisites

- Python 3.8+
- Redis (for persistent message queues)
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd healthcare-integration-engine
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The engine is configured using YAML files. A default configuration is provided in `config/default.yaml`.

### Key Configuration Sections

#### Input Adapters
```yaml
inputs:
  file:
    enabled: true
    class: inputs.file_input.FileInputAdapter
    config:
      input_dir: "/data/inputs"
      processed_dir: "/data/processed"
      error_dir: "/data/errors"
      file_pattern: "*.hl7"
      poll_interval: 1.0
```

#### Output Adapters
```yaml
outputs:
  file:
    enabled: true
    class: outputs.file_output.FileOutputAdapter
    config:
      output_dir: "/data/outputs"
      file_extension: ".hl7"
      file_naming: "{message_id}"
```

#### Processing Pipeline
```yaml
processing:
  validation:
    enabled: true
    class: processing.validation.ValidationProcessor
    config:
      schemas:
        hl7:
          type: "hl7"
          message_types: ["ADT^A01", "ADT^A04"]
  
  routing:
    enabled: true
    class: processing.routing.RoutingProcessor
    config:
      default_destinations: ["file"]
      rules: []
```

## Running the Engine

### Basic Usage

```bash
# Run with default configuration
python -m integration_engine.main

# Run with custom configuration
python -m integration_engine.main --config /path/to/config.yaml

# Enable debug logging
python -m integration_engine.main --verbose
```

### Environment Variables

- `INTEGRATION_ENV`: Set to "development" or "production" (default: "development")
- `LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `REDIS_URL`: Redis connection URL (default: "redis://localhost:6379/0")

## Testing

### Unit Tests

Run the test suite with pytest:

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run a specific test file
pytest tests/test_engine.py

# Run with coverage report
pytest --cov=integration_engine tests/
```

### Integration Test

1. Start the test environment:
   ```bash
   docker-compose -f docker-compose.integration-test.yml up -d
   ```

2. Run the integration tests:
   ```bash
   pytest tests/integration/
   ```

3. Check test coverage:
   ```bash
   pytest --cov=integration_engine tests/integration/
   ```

### Manual Testing

1. Create test directories:
   ```bash
   mkdir -p test/data/{inputs,outputs,processed,errors}
   ```

2. Create a test HL7 message:
   ```bash
   cat > test/data/inputs/test.hl7 << 'EOL'
   MSH|^~\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|20230629123045||ADT^A01|MSG00001|P|2.3
   EVN|A01|20230629123045
   PID|1||12345||Doe^John^^^Mr.||19700101|M||2106-3|123 Main St^^Anytown^CA^12345^USA
   PV1|1|O|OPD||||2000000001^Smith^John^^^Dr.|||||||||||V01
   EOL
   ```

3. Run the engine:
   ```bash
   python -m integration_engine.main --config test/config/test_config.yaml
   ```

4. Check the output in `test/data/outputs/`

## Extending the Engine

### Adding a New Input Adapter

1. Create a new file in `integration_engine/inputs/`

2. Implement the `InputAdapter` interface:
   ```python
   from core.interfaces.input_adapter import InputAdapter
   
   class MyInputAdapter(InputAdapter):
       async def start(self):
           # Initialize your input source
           pass
           
       async def stop(self):
           # Clean up resources
           pass
           
       async def receive(self):
           # Yield messages
           pass
           
       async def acknowledge(self, message):
           # Acknowledge successful processing
           pass
           
       async def nacknowledge(self, message, reason):
           # Handle processing failures
           pass
   ```

3. Update the configuration:
   ```yaml
   inputs:
     my_input:
       enabled: true
       class: inputs.my_input.MyInputAdapter
       config:
         # Your configuration here
   ```

### Adding a New Output Adapter

1. Create a new file in `integration_engine/outputs/`

2. Implement the `OutputAdapter` interface:
   ```python
   from core.interfaces.output_adapter import OutputAdapter
   
   class MyOutputAdapter(OutputAdapter):
       async def start(self):
           # Initialize your output destination
           pass
           
       async def stop(self):
           # Clean up resources
           pass
           
       async def send(self, message):
           # Send a single message
           return True
           
       async def batch_send(self, messages):
           # Send multiple messages
           return {"success": len(messages), "failed": 0, "errors": {}}
   ```

3. Update the configuration:
   ```yaml
   outputs:
     my_output:
       enabled: true
       class: outputs.my_output.MyOutputAdapter
       config:
         # Your configuration here
   ```

### Adding a New Processor

1. Create a new file in `integration_engine/processing/`

2. Implement the `Processor` interface:
   ```python
   from core.interfaces.processor import Processor
   
   class MyProcessor(Processor):
       async def start(self):
           # Initialize your processor
           pass
           
       async def stop(self):
           # Clean up resources
           pass
           
       async def process(self, message):
           # Process the message
           yield message
           
       async def handle_error(self, error, message=None):
           # Handle processing errors
           pass
   ```

3. Update the configuration:
   ```yaml
   processing:
     my_processor:
       enabled: true
       class: processing.my_processor.MyProcessor
       config:
         # Your configuration here
   ```

## Troubleshooting

### Common Issues

1. **Redis Connection Issues**
   - Ensure Redis server is running
   - Check Redis URL in configuration
   - Verify network connectivity

2. **File Permission Issues**
   - Check directory permissions
   - Ensure the engine has write access to output directories

3. **Message Processing Failures**
   - Check logs for error messages
   - Verify message format matches expected schema
   - Check for missing or invalid configuration

### Logging

Logs are written to the console by default. To enable file logging, update the logging configuration:

```yaml
logging:
  level: "INFO"
  file: "/var/log/integration_engine.log"
  max_size: 10485760  # 10MB
  backup_count: 5
```

### Debugging

To enable debug logging:

```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG

# Or run with --verbose
python -m integration_engine.main --verbose
```

## License

[Your License Here]
