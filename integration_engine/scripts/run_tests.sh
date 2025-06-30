#!/bin/bash

# Exit on any error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
INTEGRATION_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$INTEGRATION_DIR")"

# Set the path to the compose file
COMPOSE_FILE="${INTEGRATION_DIR}/docker/compose.integration-test.yml"

echo -e "${YELLOW}=== Starting Integration Test Environment ===${NC}"
echo -e "Project root: ${PROJECT_ROOT}"

# Create test data directories if they don't exist
mkdir -p "${INTEGRATION_DIR}/tests/data/{inputs,outputs,processed,errors}"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}=== Cleaning up test environment ===${NC}"
    docker-compose -f "$COMPOSE_FILE" down -v
}

# Trap EXIT to ensure cleanup runs
trap cleanup EXIT

# Build and start the test environment
echo -e "${YELLOW}Building and starting test containers...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d --build

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"

# Wait for Redis
until docker-compose -f "$COMPOSE_FILE" exec -T redis-test redis-cli ping > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "\n${GREEN}✓ Redis is ready${NC}"

# Wait for FHIR server
until curl -s -f http://localhost:8090/fhir/metadata > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "${GREEN}✓ FHIR Server is ready${NC}"

# Generate test data if needed
if [ ! -f "${INTEGRATION_DIR}/tests/data/inputs/test_hl7.hl7" ]; then
    echo -e "\n${YELLOW}Generating test data...${NC}"
    mkdir -p "${INTEGRATION_DIR}/tests/data/inputs"
    echo 'MSH|^~\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|20230629123045||ADT^A01|MSG00001|P|2.3
EVN|A01|20230629123045
PID|1||12345||Doe^John^^^Mr.||19700101|M||2106-3|123 Main St^^Anytown^CA^12345^USA
PV1|1|O|OPD||||2000000001^Smith^John^^^Dr.|||||||||||V01' > "${INTEGRATION_DIR}/tests/data/inputs/test_hl7.hl7"
    echo -e "${GREEN}✓ Test data generated${NC}"
fi

# Run the tests
echo -e "\n${YELLOW}=== Running Integration Tests ===${NC}"
if docker-compose -f "$COMPOSE_FILE" run --rm test-runner pytest tests/ -v; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}\n"
    # Clean up on success
    docker-compose -f "$COMPOSE_FILE" down -v
    exit 0
else
    echo -e "\n${RED}✗ Some tests failed${NC}"
    echo -e "\n${YELLOW}Leaving test environment up for debugging...${NC}"
    echo -e "Run ${GREEN}docker-compose -f $COMPOSE_FILE down -v${NC} to clean up\n"
    exit 1
fi
