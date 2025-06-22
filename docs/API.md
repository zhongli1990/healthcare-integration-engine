# API Documentation

## Base URL
```
https://api.healthcare-integration.example.com/v1
```

## Authentication
All API endpoints require authentication using JWT tokens.

```http
Authorization: Bearer <your_jwt_token>
```

## Rate Limiting
- 1000 requests per minute per API key
- 10000 requests per minute per IP address

## Error Handling

### Error Response Format
```json
{
  "detail": {
    "code": "error_code",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Common Error Codes
| Code | HTTP Status | Description |
|------|-------------|-------------|
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

## Message Endpoints

### Send Message
```http
POST /messages
```

**Request Body**
```json
{
  "protocol": "hl7",
  "destination": "hospital-a",
  "message": "MSH|^~\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|20230620120000||ADT^A01|MSG00001|P|2.3"
}
```

**Response**
```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "timestamp": "2023-06-20T12:00:00Z"
}
```

### Get Message Status
```http
GET /messages/{message_id}
```

**Response**
```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "delivered",
  "protocol": "hl7",
  "direction": "outbound",
  "created_at": "2023-06-20T12:00:00Z",
  "updated_at": "2023-06-20T12:00:01Z",
  "metadata": {}
}
```

## Workflow Endpoints

### List Workflows
```http
GET /workflows
```

**Response**
```json
{
  "workflows": [
    {
      "id": "workflow-123",
      "name": "Patient Admission",
      "description": "Process patient admission messages",
      "version": 1,
      "enabled": true,
      "created_at": "2023-01-01T00:00:00Z"
    }
  ]
}
```

### Execute Workflow
```http
POST /workflows/{workflow_id}/execute
```

**Request Body**
```json
{
  "input": {},
  "metadata": {}
}
```

**Response**
```json
{
  "execution_id": "exec-123",
  "status": "started",
  "workflow_id": "workflow-123",
  "started_at": "2023-06-20T12:00:00Z"
}
```

## Monitoring Endpoints

### Get System Health
```http
GET /health
```

**Response**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2023-06-20T12:00:00Z",
  "services": {
    "database": {
      "status": "ok",
      "latency_ms": 12
    },
    "message_broker": {
      "status": "ok",
      "latency_ms": 8
    },
    "cache": {
      "status": "ok",
      "latency_ms": 2
    }
  }
}
```

### Get Metrics
```http
GET /metrics
```

**Response**
```
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",status="200"} 1000
http_requests_total{method="POST",status="201"} 500

# HELP message_processing_duration_seconds Time spent processing messages
# TYPE message_processing_duration_seconds histogram
message_processing_duration_seconds_bucket{le="0.1"} 1000
message_processing_duration_seconds_bucket{le="0.5"} 1500
message_processing_duration_seconds_bucket{le="1"} 1600
```

## Webhook Endpoints

### Register Webhook
```http
POST /webhooks
```

**Request Body**
```json
{
  "url": "https://your-callback-url.com/events",
  "events": ["message.received", "message.delivered"],
  "secret": "your_webhook_secret"
}
```

**Response**
```json
{
  "id": "wh_123",
  "url": "https://your-callback-url.com/events",
  "events": ["message.received", "message.delivered"],
  "created_at": "2023-06-20T12:00:00Z"
}
```

## Webhook Payload Example
```json
{
  "event": "message.delivered",
  "data": {
    "message_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "delivered",
    "timestamp": "2023-06-20T12:00:01Z"
  },
  "webhook_id": "wh_123",
  "timestamp": "2023-06-20T12:00:02Z"
}
```
