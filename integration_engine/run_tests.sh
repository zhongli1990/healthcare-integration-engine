#!/bin/bash

# Exit on error
set -e

# Set environment variables
export PYTHONPATH=/app

# Run tests with coverage
pytest tests/ \
    --cov=integration_engine \
    --cov-report=term-missing \
    --cov-report=xml:coverage.xml \
    -v \
    --log-level=DEBUG \
    "$@"
