# File Processing Test Plan

## Overview
This document outlines the test cases and procedures for file-based message processing in the Integration Engine. The system should handle three types of input files: HL7v2, FHIR JSON, and FHIR XML, processing them and generating appropriate outputs.

## Test Environment Setup

### Directory Structure
```
tests/
├── data/
│   ├── inputs/           # Test input files
│   │   ├── hl7/          # HL7v2 test files
│   │   ├── fhir/         # FHIR test files
│   │   └── invalid/      # Invalid test files
│   ├── archive/          # Processed input files
│   ├── outputs/          # Generated output files
│   └── errors/           # Files that failed processing
└── e2e/
    └── test_file_processing.py  # Test scripts
```

### Sample Test Data

#### HL7v2 Test File
**File**: `tests/data/inputs/hl7/ADT_A01.hl7`
```hl7
MSH|^~\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|20230630120000||ADT^A01|MSG00001|P|2.3
EVN|A01|20230630120000
PID|1||12345||Doe^John||19700101|M||2106-3|123 Main St^^Anytown^CA^12345||555-555-1000|555-555-1001||S||123-45-6789|||N
PV1|1|O|OPD||||2000000001^Doctor^John^A^^^DRNBRH^L
```

#### FHIR JSON Test File
**File**: `tests/data/inputs/fhir/patient.json`
```json
{
  "resourceType": "Patient",
  "id": "example",
  "identifier": [{
    "system": "http://example.org/patient-ids",
    "value": "12345"
  }],
  "name": [{
    "family": "Doe",
    "given": ["John"]
  }],
  "gender": "male",
  "birthDate": "1970-01-01",
  "address": [{
    "line": ["123 Main St"],
    "city": "Anytown",
    "state": "CA",
    "postalCode": "12345"
  }]
}
```

## Test Cases

### TC-001: HL7v2 File Processing
**Description**: Verify that an HL7v2 file is properly processed

**Preconditions**:
- Input directory is empty
- Output and archive directories are empty

**Test Steps**:
1. Copy `ADT_A01.hl7` to the input directory
2. Wait for file processing to complete (up to 30 seconds)
3. Verify outputs

**Expected Results**:
- [ ] Input file is moved to archive directory
- [ ] HL7v3 output file is generated
- [ ] FHIR output file is generated
- [ ] Audit log shows successful processing

### TC-002: FHIR JSON File Processing
**Description**: Verify that a FHIR JSON file is properly processed

**Preconditions**:
- Input directory is empty
- Output and archive directories are empty

**Test Steps**:
1. Copy `patient.json` to the input directory
2. Wait for file processing to complete
3. Verify outputs

**Expected Results**:
- [ ] Input file is moved to archive directory
- [ ] HL7v3 output file is generated
- [ ] Audit log shows successful processing

### TC-003: Invalid File Handling
**Description**: Verify that invalid files are handled gracefully

**Preconditions**:
- Input and error directories are empty

**Test Steps**:
1. Copy a malformed file to the input directory
2. Wait for file processing to complete

**Expected Results**:
- [ ] File is moved to error directory
- [ ] Error is logged
- [ ] No output files are generated

## Test Execution

### Prerequisites
- Docker and Docker Compose installed
- Test environment configured

### Running Tests

1. Start the test environment:
   ```bash
   docker-compose -f docker-compose.test.yml up -d
   ```

2. Run the file processing tests:
   ```bash
   docker-compose -f docker-compose.test.yml run --rm test-runner \
     pytest tests/e2e/test_file_processing.py -v
   ```

3. View test results and logs:
   ```bash
   docker-compose logs -f test-runner
   ```

## Troubleshooting

### Common Issues
1. **File Permissions**
   - Ensure the test user has read/write access to test directories

2. **Test Timeouts**
   - Increase wait times in test cases if processing takes longer than expected

3. **Missing Dependencies**
   - Rebuild the test container if dependencies are missing:
     ```bash
     docker-compose -f docker-compose.test.yml build test-runner
     ```

## Test Data Management

### Adding New Test Cases
1. Add new test files to the appropriate input directory
2. Update expected output files if necessary
3. Add new test methods to `test_file_processing.py`

### Cleaning Up
To clean up test data and containers:
```bash
docker-compose -f docker-compose.test.yml down -v
rm -rf tests/data/{inputs,outputs,archive,errors}/*
```
