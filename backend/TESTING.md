# Testing Guide

This document provides instructions for running tests in the healthcare-integration-engine project.

## Prerequisites

- Docker and Docker Compose installed
- Access to the project root directory

## Running Tests

### 1. Start the Test Environment

First, ensure all services are running:

```bash
docker-compose up -d
```

### 2. Run All Tests

To run all tests inside the backend container:

```bash
docker-compose exec backend pytest /app/tests -v
```

### 3. Run Specific Test File

To run tests from a specific file (e.g., auth tests):

```bash
docker-compose exec backend pytest /app/tests/api/v1/test_auth.py -v
```

### 4. Run a Single Test

To run a specific test function:

```bash
docker-compose exec backend pytest /app/tests/api/v1/test_auth.py::test_login_success -v
```

### 5. Run Tests with Coverage

To generate a coverage report:

```bash
docker-compose exec backend pytest --cov=app /app/tests/
```

## Test User

The test suite uses the following test user:

- **Email**: Tester123@example.com
- **Password**: password123
- **Full Name**: Test User

## Adding New Tests

1. Place test files in the appropriate directory under `/app/tests/`
2. Follow the existing test patterns
3. Use the `test_` prefix for test files and functions
4. Leverage existing fixtures from `conftest.py` when possible

## Helper Scripts

### run_tests.sh

A convenience script is available in the project root to run tests with common options:

```bash
./run_tests.sh  # Runs all tests
./run_tests.sh tests/api/v1/test_auth.py  # Runs specific test file
```

### Common Test Options

- `-v`: Verbose output
- `-s`: Show output (print statements)
- `-x`: Stop after first failure
- `--pdb`: Drop into debugger on failure
- `-k "test_name"`: Run tests matching the expression

## Test Database

- Tests use a dedicated PostgreSQL schema (`test`) to isolate from development data
- The test database is automatically created and migrated
- Test data is cleaned up after each test run
