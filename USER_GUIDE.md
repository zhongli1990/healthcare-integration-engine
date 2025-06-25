# User Guide

## Prerequisites

- Docker and Docker Compose
- Make (optional but recommended)

## Quick Start

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd healthcare-integration-engine
   ```

2. Start the application:
   ```bash
   # Copy and configure environment variables
   cp .env.example .env
   
   # Start all services
   docker-compose up -d
   ```

3. Access the application:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8850
   - API Documentation: http://localhost:8850/docs

## Running Tests

### Using Make Commands (Recommended)

```bash
# Start test containers and run all tests
make test

# Run tests with coverage report
make test-cov

# Stop test containers
make test-down
```

### Using Docker Compose Directly

```bash
# Run all tests
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Run specific test file
docker-compose -f docker-compose.test.yml run --rm backend pytest tests/path/to/test_file.py

# Run with coverage
docker-compose -f docker-compose.test.yml run --rm backend pytest --cov=app --cov-report=term-missing
```

## Environment Variables

Configure the application using these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://postgres:postgres@db:5432/healthcare_integration` |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379` |
| `NEO4J_URI` | Neo4j connection URI | `bolt://neo4j:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `healthcare123` |
| `DEBUG` | Enable debug mode | `false` |

## Common Tasks

### Database Migrations

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"
```

### Viewing Logs

```bash
# View all logs
docker-compose logs -f

# View backend logs
docker-compose logs -f backend

# View database logs
docker-compose logs -f db
```

### Stopping the Application

```bash
# Stop all containers
docker-compose down

# Stop and remove all containers, volumes, and networks
docker-compose down -v --remove-orphans
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: If you get port binding errors, check if ports 8850, 5173, 8852, 8853, or 8854 are already in use.

2. **Database connection issues**: Ensure the database container is running and healthy:
   ```bash
   docker-compose ps
   docker-compose logs db
   ```

3. **Missing environment variables**: Make sure all required environment variables are set in your `.env` file.

4. **Test failures**: If tests fail, try rebuilding the test containers:
   ```bash
   docker-compose -f docker-compose.test.yml build --no-cache
   docker-compose -f docker-compose.test.yml up
   ```

## Getting Help

For additional support, please contact the development team or open an issue in the repository.
