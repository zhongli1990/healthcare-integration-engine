# Developer Guide

## Project Structure

```
backend/
├── app/                    # Main application package
│   ├── api/                # API routes
│   ├── core/               # Core functionality
│   ├── db/                 # Database configuration
│   ├── models/             # Database models
│   ├── schemas/            # Pydantic schemas
│   └── services/           # Business logic
├── tests/                  # Test files
│   ├── api/                # API tests
│   ├── conftest.py         # Test configuration
│   └── test_database.py    # Database tests
├── requirements.txt        # Main dependencies
└── requirements-test.txt   # Test dependencies
```

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend development)

### Environment Variables

Create a `.env` file in the backend directory with the following variables:

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:8852/healthcare_integration
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:8852/healthcare_integration_test

# Redis
REDIS_URL=redis://localhost:8853

# Neo4j
NEO4J_URI=bolt://localhost:8854
NEO4J_USER=neo4j
NEO4J_PASSWORD=healthcare123

# App
SECRET_KEY=your-secret-key
DEBUG=true
```

## Testing

### Running Tests

#### Option 1: Using Docker Compose (Recommended)

```bash
# Start test services
make test-up

# Run all tests
make test

# Run a specific test file
make test tests/path/to/test_file.py

# Run tests with coverage
make test-cov

# Stop test services
make test-down
```

#### Option 2: Local Testing

1. Start required services:
   ```bash
   docker-compose up -d db redis neo4j
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt -r requirements-test.txt
   ```

4. Run tests:
   ```bash
   # Run all tests
   pytest
   
   # Run tests with coverage
   pytest --cov=app --cov-report=term-missing
   
   # Run a specific test file
   pytest tests/path/to/test_file.py
   
   # Run a specific test function
   pytest tests/path/to/test_file.py::test_function_name
   ```

## Test Database

The test suite uses a separate PostgreSQL schema (`test_schema`) to isolate test data. The test database is automatically created and dropped for each test session.

## Debugging Tests

To debug tests in VS Code:

1. Add this configuration to your `launch.json`:
   ```json
   {
       "name": "Python: Current Test",
       "type": "python",
       "request": "launch",
       "program": "${file}",
       "purpose": ["debug-test"],
       "console": "integratedTerminal",
       "justMyCode": false
   }
   ```

2. Set breakpoints in your test or application code.
3. Open the test file and press F5 to start debugging.

## Code Style

- Follow PEP 8 for Python code
- Use type hints for all function parameters and return values
- Write docstrings for all public functions and classes
- Keep lines under 100 characters

## Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Example:
```
feat(api): add user registration endpoint

- Add POST /api/v1/auth/register endpoint
- Add email verification flow
- Update API documentation

Closes #123
```
