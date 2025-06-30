# Healthcare Integration Engine

A highly scalable, flexible, and decoupled enterprise integration engine designed to handle healthcare data exchange between different systems and protocols, with a focus on HL7 v2 and FHIR R4 standards.

## Features

- **Multi-protocol Support**: Native support for HL7 v2 (MLLP) and FHIR R4 (REST) protocols
- **Modular Architecture**: Pluggable components for message ingestion, validation, transformation, routing, and delivery
- **Schema-driven Validation**: JSON Schema validation for all message types
- **Flexible Routing**: Configurable routing rules with support for complex conditions and transformations
- **Multiple Output Destinations**: Support for sending messages to various destinations including HL7 v2, FHIR, and file systems
- **High Performance**: Asynchronous, event-driven architecture using Redis for message queuing
- **Extensible**: Easy to add new protocols, transformations, and destinations
- **Monitoring & Observability**: Built-in metrics, logging, and health checks
- **REST API**: Management and monitoring API for integration with existing systems

## Getting Started

### Prerequisites

- Python 3.9+
- Redis (for production use)
- Docker (optional, for containerized deployment)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/healthcare-integration-engine.git
   cd healthcare-integration-engine
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

1. Copy the example configuration file:
   ```bash
   cp config/sample_config.yaml config/config.yaml
   ```

2. Edit the configuration file to match your environment:
   ```yaml
   # config/config.yaml
   global:
     log_level: "INFO"
     environment: "development"
     instance_id: "integration-engine-01"
     timezone: "UTC"
   
   queues:
     type: "memory"  # Use 'redis' for production
     
   # ... rest of the configuration
   ```

### Running the Integration Engine

#### Using the CLI

```bash
# Start the integration engine
python -m integration_engine.cli start --config config/config.yaml

# Show help
python -m integration_engine.cli --help
```

#### Using Docker (Development)

```bash
# Build the Docker image
docker build -t healthcare-integration-engine .

# Run the container
docker run -p 8000:8000 -p 2575:2575 -p 8080:8080 -v $(pwd)/config:/app/config healthcare-integration-engine
```

## Architecture

The integration engine follows a modular, service-oriented architecture with the following key components:

1. **Inbound Services**: Handle incoming messages from various protocols (HL7 v2, FHIR, etc.)
2. **Processing Pipeline**:
   - **Validation**: Validates messages against schemas and business rules
   - **Transformation**: Converts messages between different formats
   - **Routing**: Routes messages based on configurable rules
3. **Outbound Services**: Deliver messages to various destinations (HL7 v2, FHIR, files, etc.)
4. **Core Services**:
   - **Queue Manager**: Manages message queues (Redis or in-memory)
   - **Schema Registry**: Manages message schemas and validation rules
   - **Configuration Manager**: Handles configuration loading and validation

## Configuration Reference

The integration engine is highly configurable through YAML configuration files. See the [Configuration Guide](docs/configuration.md) for detailed information about all available options.

## API Documentation

The integration engine provides a REST API for management and monitoring. The API documentation is available at `http://localhost:8000/docs` when the engine is running.

## Development

### Setting Up a Development Environment

1. Clone the repository and navigate to the project directory.
2. Create and activate a virtual environment.
3. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
4. Install the package in development mode:
   ```bash
   pip install -e .
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=integration_engine --cov-report=html
```

### Code Style

This project uses `black` for code formatting and `flake8` for linting.

```bash
# Format code
black .

# Lint code
flake8
```

## Deployment

### Docker Compose (Production)

```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  integration-engine:
    build: .
    ports:
      - "8000:8000"  # API
      - "2575:2575"  # HL7 v2 MLLP
      - "8080:8080"  # FHIR API
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    volumes:
      - ./config:/app/config
    depends_on:
      - redis
    restart: unless-stopped

volumes:
  redis_data:
```

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework for building APIs
- [Redis](https://redis.io/) - In-memory data structure store used as a message broker
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation and settings management
- [HL7](https://www.hl7.org/) - Health Level Seven International
- [FHIR](https://www.hl7.org/fhir/) - Fast Healthcare Interoperability Resources
