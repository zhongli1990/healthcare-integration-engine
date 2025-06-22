# Healthcare Integration Engine - PoC Scope

## 1. Core Objective
Build a minimal but functional integration engine that can:
1. Read HL7 ADT messages from a local directory
2. Process and validate the messages
3. Route them to another directory
4. Provide a basic monitoring API

## 2. Features

### 2.1 Inbound Service
- **Source**: Local file system (watches a directory)
- **Protocol**: HL7 v2.x (ADT messages only)
- **File Format**: `.hl7` files with raw HL7 messages

### 2.2 Processing
- Message validation (basic HL7 structure)
- Simple routing based on message type
- Error handling with dead letter queue

### 2.3 Outbound Service
- **Target**: Local file system (writes to a directory)
- **File Naming**: `{timestamp}_{message_type}_{message_id}.hl7`
- **Error Handling**: Move failed messages to error directory

### 2.4 Monitoring API
- REST API with FastAPI
- Endpoints:
  - `GET /health` - Service health
  - `GET /metrics` - Basic metrics (messages processed, errors)
  - `GET /messages` - List recent messages

## 3. Technical Stack

### 3.1 Backend
- **Language**: Python 3.10+
- **Framework**: FastAPI
- **HL7 Parser**: `hl7apy` or `hl7`
- **File Watching**: `watchdog`
- **Configuration**: Pydantic + YAML

### 3.2 Development Environment
- **Containerization**: Docker + Docker Compose
- **Testing**: pytest
- **Linting**: black, isort, flake8

## 4. Project Structure

```
healthcare_integration_poc/
├── src/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Configuration
│   ├── services/
│   │   ├── __init__.py
│   │   ├── base.py            # Base service class
│   │   ├── file_watcher.py    # File system watcher
│   │   └── hl7_processor.py   # HL7 message processing
│   ├── models/
│   │   ├── __init__.py
│   │   ├── message.py         # Message model
│   │   └── config.py          # Config models
│   └── api/
│       ├── __init__.py
│       ├── endpoints.py       # API endpoints
│       └── models.py          # API models
├── config/
│   └── config.yaml          # Main configuration
├── tests/                     # Test files
├── requirements.txt
├── requirements-dev.txt
└── docker-compose.yml
```

## 5. Configuration (config.yaml)

```yaml
app:
  name: healthcare-integration-poc
  environment: development
  log_level: INFO

services:
  file_watcher:
    input_dir: ./data/input
    processed_dir: ./data/processed
    error_dir: ./data/errors
    file_pattern: "*.hl7"
    
  hl7_processor:
    validate_message_structure: true
    default_encoding: "utf-8"
    
  api:
    host: 0.0.0.0
    port: 8000
    debug: true
```

## 6. Implementation Steps

### 6.1 Setup (Day 1)
1. Create project structure
2. Set up development environment
3. Implement configuration loading

### 6.2 Core Services (Day 2-3)
1. Implement file watcher service
2. Create HL7 message processor
3. Build basic routing

### 6.3 API Layer (Day 3-4)
1. Implement health endpoint
2. Add metrics collection
3. Create message listing

### 6.4 Testing & Polish (Day 5)
1. Write unit tests
2. Create sample data
3. Document usage

## 7. Sample HL7 Message Flow

1. **Input File**: `data/input/ADT_A01_123.hl7`
```hl7
MSH|^~\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|20230620120000||ADT^A01|MSG00001|P|2.3|
EVN|A01|20230620120000|||
PID|1||12345||Doe^John^M||19800101|M||2106-3|123 Main St^^Anytown^CA^12345|GL|(555)555-5555|(555)555-5556|ENG|S||123-45-6789|123-45-6789||
```

2. **Processing**:
   - File is detected by watcher
   - HL7 message is parsed and validated
   - Message is routed based on type (ADT^A01)
   - File is moved to processed directory

3. **Output File**: `data/processed/20230620120000_ADT_A01_MSG00001.hl7`

## 8. API Examples

### Health Check
```http
GET /health
```
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "services": {
    "file_watcher": "running",
    "hl7_processor": "running"
  }
}
```

### Metrics
```http
GET /metrics
```
```json
{
  "messages_processed": 42,
  "messages_failed": 1,
  "processing_time_avg_ms": 25.5,
  "last_processed": "2023-06-20T12:00:00Z"
}
```

## 9. Success Criteria

1. **Functional**
   - Can process HL7 ADT messages from files
   - Moves processed files to correct directories
   - Provides basic monitoring via API

2. **Non-Functional**
   - Handles at least 10 messages per second
   - Logs all operations
   - Runs in a container

## 10. Future Iterations

### Iteration 2: Enhanced Processing
- Add more HL7 message types
- Implement message transformation
- Add database storage

### Iteration 3: Additional Protocols
- Add MLLP support
- Add SFTP support
- Add HTTP endpoints

### Iteration 4: Advanced Features
- Add authentication
- Implement retry logic
- Add monitoring dashboard
