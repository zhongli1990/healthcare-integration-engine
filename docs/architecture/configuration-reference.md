# Configuration Reference

## 1. Service Configuration

### 1.1 Base Service Configuration

```yaml
# service.yaml
service:
  # Required
  id: unique-service-id  # Must be unique across all services
  name: Human-readable name  # Display name for the service
  type: inbound|outbound  # Service direction
  enabled: true  # Whether the service is active
  
  # Threading
  max_threads: 10  # Maximum number of worker threads
  thread_keepalive: 60s  # Thread keep-alive time
  
  # Retry behavior
  max_retries: 3  # Maximum retry attempts
  retry_delay: 5s  # Initial delay between retries
  backoff_multiplier: 2.0  # Exponential backoff multiplier
  
  # Timeouts
  connection_timeout: 30s  # Connection establishment timeout
  read_timeout: 60s  # Read operation timeout
  write_timeout: 60s  # Write operation timeout
  
  # Monitoring
  metrics_enabled: true  # Enable/disable metrics collection
  health_check_interval: 30s  # Health check frequency
  
  # Logging
  logging:
    level: INFO  # Log level (DEBUG, INFO, WARN, ERROR)
    format: json  # Log format (json, text)
    file: /var/log/service.log  # Log file path
    max_size: 100MB  # Max log file size
    max_backups: 5  # Number of log files to keep
```

### 1.2 Transport Protocols

#### TCP/MLLP
```yaml
transport:
  protocol: tcp|mllp
  
  # Network settings
  host: 0.0.0.0  # Bind address
  port: 2575  # Listen port
  
  # TLS configuration
  tls:
    enabled: false  # Enable/disable TLS
    cert_file: /path/to/cert.pem
    key_file: /path/to/key.pem
    ca_file: /path/to/ca.pem
    require_client_auth: false  # Require client certificate
    
  # MLLP specific
  mllp:
    start_block: '\x0B'  # Start block character
    end_block: '\x1C\r'  # End block characters
    charset: ISO-8859-1  # Character encoding
```

#### HTTP/HTTPS
```yaml
transport:
  protocol: http|https
  
  # Network settings
  host: 0.0.0.0
  port: 8080
  
  # HTTP specific
  context_path: /api  # Base path for all endpoints
  max_content_length: 10MB  # Max request size
  cors:  # CORS configuration
    enabled: true
    allowed_origins: ["*"]
    allowed_methods: ["GET", "POST"]
    
  # HTTPS specific
  tls:
    enabled: true
    cert_file: /path/to/cert.pem
    key_file: /path/to/key.pem
```

#### File System
```yaml
transport:
  protocol: file
  
  # Input configuration
  input_dir: /path/to/input  # Directory to watch
  file_pattern: '*.hl7'  # File pattern to match
  recursive: true  # Watch subdirectories
  
  # Processing
  delete_after_processing: false  # Delete files after processing
  error_dir: /path/to/errors  # Directory for failed files
  archive_dir: /path/to/archive  # Directory for processed files
  
  # Polling
  poll_interval: 5s  # Time between directory scans
  min_file_age: 1s  # Minimum file age before processing
```

### 1.3 Healthcare Protocols

#### HL7 v2
```yaml
protocol:
  type: hl7v2
  
  # HL7 version and encoding
  version: 2.5  # HL7 version (2.1-2.9)
  encoding: UTF-8  # Character encoding
  
  # Message handling
  validate_structure: true  # Validate HL7 message structure
  validate_values: true  # Validate field values
  
  # ACK generation
  generate_ack: true  # Generate ACK messages
  ack_mode: original  # original|enhanced|always
  
  # Segment handling
  segment_terminator: '\r'  # Segment terminator
  field_separator: '|'  # Field separator
  component_separator: '^'  # Component separator
  repetition_separator: '~'  # Repetition separator
  escape_character: '\\'  # Escape character
  subcomponent_separator: '&'  # Subcomponent separator
```

#### FHIR
```yaml
protocol:
  type: fhir
  
  # FHIR version
  version: R4  # STU3|R4|R5
  
  # Resource handling
  resource_type: Patient  # Default resource type
  pretty_print: true  # Pretty-print JSON output
  
  # Validation
  validate_resources: true  # Validate against FHIR schema
  validation_mode: strict  # strict|loose|none
  
  # Search parameters
  default_page_size: 20  # Default page size for searches
  max_page_size: 100  # Maximum page size
```

## 2. Message Processing

### 2.1 Pipeline Configuration

```yaml
pipeline:
  # Validation
  - name: message_validation
    enabled: true
    class: core.validators.MessageValidator
    config:
      max_message_size: 10MB
      allowed_message_types: [ADT, ORU, SIU]
  
  # Transformation
  - name: hl7_to_internal
    enabled: true
    class: core.transformers.HL7ToInternal
    config:
      map_patient_id: true
      normalize_timestamps: true
  
  # Routing
  - name: message_router
    enabled: true
    class: core.routers.TopicRouter
    config:
      default_topic: uncategorized
      rules:
        - condition: message.type == 'ADT' and message.event in ['A01', 'A04', 'A08']
          topic: patient-updates
          priority: high
        - condition: message.type == 'ORU'
          topic: lab-results
  
  # Persistence
  - name: message_store
    enabled: true
    class: core.storage.MessageStore
    config:
      retention_days: 30
      archive_enabled: true
```

### 2.2 Error Handling

```yaml
error_handling:
  # Retry policy
  retry_policy:
    max_attempts: 3
    initial_interval: 1s
    max_interval: 1m
    multiplier: 2.0
  
  # Error queue
  error_queue:
    enabled: true
    max_size: 10000
    retention_hours: 168  # 7 days
  
  # Dead letter queue
  dlq:
    enabled: true
    max_size: 5000
    retention_days: 30
  
  # Notification
  notifications:
    enabled: true
    email:
      recipients: [admin@example.com]
      on_error: true
      on_retry: false
    webhook:
      url: https://alerts.example.com/notify
      timeout: 5s
```

## 3. Security

### 3.1 Authentication

```yaml
security:
  authentication:
    enabled: true
    mode: required  # required|optional|none
    
    # JWT Authentication
    jwt:
      enabled: true
      issuer: https://auth.example.com
      audience: integration-engine
      jwks_uri: https://auth.example.com/.well-known/jwks.json
    
    # API Keys
    api_keys:
      enabled: true
      keys:
        - name: client-1
          key: abc123
          roles: [read, write]
        - name: client-2
          key: def456
          roles: [read]
    
    # IP Whitelisting
    ip_whitelist:
      enabled: true
      addresses:
        - 192.168.1.0/24
        - 10.0.0.0/8
```

### 3.2 Authorization

```yaml
authorization:
  enabled: true
  
  # Role-based access control
  rbac:
    roles:
      - name: admin
        permissions: ["*"]
      - name: operator
        permissions: ["read", "write"]
      - name: viewer
        permissions: ["read"]
  
  # Resource permissions
  resources:
    - name: messages
      actions: ["read", "write", "delete"]
    - name: configurations
      actions: ["read", "write"]
```

## 4. Monitoring

### 4.1 Metrics

```yaml
monitoring:
  # Prometheus metrics
  prometheus:
    enabled: true
    port: 9090
    path: /metrics
    
  # JMX
  jmx:
    enabled: true
    port: 1099
    
  # Health checks
  health_checks:
    - name: database
      class: core.health.DatabaseHealthCheck
      interval: 30s
      timeout: 5s
    - name: disk_space
      class: core.health.DiskSpaceHealthCheck
      threshold: 10%
```

### 4.2 Logging

```yaml
logging:
  # Console logging
  console:
    enabled: true
    level: INFO
    format: json
    
  # File logging
  file:
    enabled: true
    path: /var/log/integration-engine.log
    level: INFO
    max_size: 100MB
    max_backups: 5
    max_age: 30
    compress: true
    
  # Syslog
  syslog:
    enabled: false
    host: localhost
    port: 514
    facility: local0
    
  # Logging context
  mdc:
    enabled: true
    fields:
      - correlation_id
      - service_id
      - message_id
```

## 5. Complete Example

```yaml
# Example HL7 ADT Inbound Service
service:
  id: hl7-adt-inbound
  name: HL7 ADT Inbound
  type: inbound
  enabled: true
  max_threads: 10
  
transport:
  protocol: mllp
  host: 0.0.0.0
  port: 2575
  tls:
    enabled: true
    cert_file: /etc/ssl/certs/hl7-cert.pem
    key_file: /etc/ssl/private/hl7-key.pem
    
protocol:
  type: hl7v2
  version: 2.5
  encoding: UTF-8
  generate_ack: true
  
pipeline:
  - name: message_validation
    enabled: true
    class: core.validators.HL7Validator
  - name: transform_to_internal
    enabled: true
    class: core.transformers.HL7ToInternal
  - name: route_messages
    enabled: true
    class: core.routers.TopicRouter
    config:
      default_topic: uncategorized
      rules:
        - condition: message.type == 'ADT' and message.event in ['A01', 'A04', 'A08']
          topic: patient-updates
          
security:
  authentication:
    enabled: true
    mode: required
    jwt:
      enabled: true
      issuer: https://auth.example.com
      
monitoring:
  prometheus:
    enabled: true
    port: 9090
  health_checks:
    - name: database
      class: core.health.DatabaseHealthCheck
      interval: 30s
```

## 6. Configuration Management

### 6.1 Environment Variables
All configuration values can be overridden using environment variables:

```bash
# Example: Override service port
SERVICE_PORT=8080

# Example: Enable debug logging
LOGGING_LEVEL=DEBUG

# Example: Set database URL
DATABASE_URL=postgresql://user:pass@localhost:5432/db
```

### 6.2 Configuration Precedence
1. Command-line arguments (highest precedence)
2. Environment variables
3. Configuration files
4. Default values (lowest precedence)

### 6.3 Configuration Reloading
```yaml
config:
  watch: true  # Watch for configuration changes
  reload_interval: 30s  # Check for changes interval
  notify_on_reload: true  # Send notification on config reload
```
