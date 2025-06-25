#!/bin/bash
set -e

echo "Building and starting test containers..."
docker-compose -f docker-compose.test.yml build
docker-compose -f docker-compose.test.yml up -d test-db

# Wait for the test database to be ready
echo "Waiting for test database to be ready..."
until docker-compose -f docker-compose.test.yml exec -T test-db pg_isready -U postgres -d test_healthcare_integration; do
  sleep 1
done

# Run migrations and tests
echo "Running tests..."
docker-compose -f docker-compose.test.yml run --rm test

# Stop containers after tests
echo "Tests completed. Stopping containers..."
docker-compose -f docker-compose.test.yml down

echo "Done!"
