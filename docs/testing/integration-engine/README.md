# Integration Engine Testing Guide

This document provides comprehensive guidelines for testing the Integration Engine components, including unit tests, integration tests, and end-to-end tests.

## Table of Contents
- [Test Plan](#test-plan)
- [Test Types](#test-types)
- [Prerequisites](#prerequisites)
- [Test Environment](#test-environment)
- [Running Tests](#running-tests)
- [Test Data](#test-data)
- [Writing Tests](#writing-tests)
- [Troubleshooting](#troubleshooting)
- [CI/CD Integration](#cicd-integration)

## Test Plan

For a comprehensive overview of the testing strategy, test cases, and expected outcomes, please refer to the [Integration Engine Test Plan](../../Integrations/IntegrationEngine/testing/TEST_PLAN.md). This document provides detailed information about the testing approach, including component validation, integration testing, end-to-end workflows, performance testing, and reliability testing.

## Test Types

### 1. Unit Tests
- Test individual components in isolation
- Use mocks for external dependencies
- Located in `tests/unit/`
- Fast execution, run frequently during development

### 2. Integration Tests
- Test interactions between components
- Use real services (Redis, databases) in Docker
- Located in `tests/integration/`
- Verify component integration

### 3. End-to-End Tests
- Test complete workflows
- Use real services with test configurations
- Located in `tests/e2e/`
- Validate complete system behavior

## Prerequisites

### System Requirements
- Docker and Docker Compose installed
- Python 3.11+
- At least 4GB of available RAM
- At least 2 CPU cores

### Test Dependencies
```bash
# Install test requirements
pip install -r test-requirements.txt
```

## Test Environment

The test environment consists of the following services:

- **Test Runner**: Runs the integration tests
- **Redis**: Used for message queuing
- **PostgreSQL**: Test database
- **Neo4j**: Graph database for relationship data
- **HAPI FHIR Server**: Mock FHIR server for testing FHIR operations

## Running Tests

### 1. Using the Test Script (Recommended)

```bash
# Make the script executable if not already
chmod +x run_integration_tests.sh

# Run all tests
./run_integration_tests.sh
```

### 2. Running Specific Test Types

#### Unit Tests
```bash
# Run all unit tests
pytest tests/unit -v

# Run a specific test file
pytest tests/unit/test_queue_manager.py -v

# Run with coverage report
pytest --cov=integration_engine --cov-report=term-missing tests/unit/
```

#### Integration Tests
```bash
# Start test services
make test-up

# Run integration tests
pytest tests/integration -v

# Stop test services when done
make test-down
```

#### End-to-End Tests
```bash
# Start full environment
make e2e-up

# Run end-to-end tests
pytest tests/e2e -v

# Stop environment when done
make e2e-down
```

### 3. Running in Docker

For consistent testing across environments, you can run tests in Docker:

```bash
# Build and start test containers
docker-compose -f docker-compose.test.yml up -d --build

# Run tests
docker-compose -f docker-compose.test.yml run --rm test-runner pytest tests/ -v

# View logs
docker-compose -f docker-compose.test.yml logs -f

# Clean up
docker-compose -f docker-compose.test.yml down -v
```

## Test Data

Test data is stored in the `test_data` directory with the following structure:

```
test_data/
├── hl7/                 # HL7 test messages
│   ├── adt/            # ADT messages
│   └── oru/             # ORU messages
├── fhir/                # FHIR test resources
│   ├── Patient/        # Patient resources
│   └── Observation/     # Observation resources
└── expected/            # Expected output for assertions
```

### Adding Test Data
1. Place test files in the appropriate directory
2. Name files descriptively (e.g., `patient_admit.hl7`)
3. Add corresponding expected output in the `expected` directory
4. Update test cases to use the new test data

## Writing Tests

### Test Structure
```python
def test_feature_description():
    # Arrange - Set up test data and environment
    test_data = load_test_data("test_data/hl7/adt/patient_admit.hl7")
    
    # Act - Perform the action being tested
    result = process_message(test_data)
    
    # Assert - Verify the results
    assert result.status == "success"
    assert "Patient" in result.data
```

### Best Practices
- Keep tests focused and independent
- Use descriptive test names
- Test both success and error cases
- Mock external dependencies in unit tests
- Use fixtures for common test setup
- Clean up after tests

## Troubleshooting

### Common Issues

#### Tests Failing
- Verify all required services are running
- Check test data paths and permissions
- Look for error messages in the test output

#### Docker Issues
- Make sure Docker is running
- Check for port conflicts
- Try rebuilding containers with `--no-cache`

#### Database Issues
- Ensure database containers are healthy
- Check for schema migrations that need to be applied
- Verify connection strings in test configuration

## CI/CD Integration

The test suite is integrated into the CI/CD pipeline. Tests are automatically run on:
- Pull requests
- Pushes to main branch
- Before deployment

### Customizing Test Execution

You can customize test execution using environment variables:

```bash
# Run a specific test marker
pytest -m "not slow"

# Run tests in parallel
pytest -n auto

# Show coverage report in HTML
pytest --cov=integration_engine --cov-report=html
```

## Performance Testing

For performance testing, use the `-k` flag to run specific tests:

```bash
# Run performance tests
pytest tests/performance -v

# Generate performance report
pytest tests/performance --benchmark-json=performance_report.json
```

## Security Testing

Security tests are located in `tests/security/` and include:
- Input validation
- Authentication and authorization
- Data protection
- API security

## License

This testing guide is part of the Healthcare Integration Engine project and is licensed under the MIT License.
