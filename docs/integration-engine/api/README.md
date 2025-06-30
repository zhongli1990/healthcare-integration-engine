# API Reference

## REST API

### Base URL
```
https://api.your-integration-engine.com/v1
```

### Authentication
```http
Authorization: Bearer <your_api_key>
```

## Endpoints

### Health Check

#### GET /health

Check the health of the integration engine.

**Response**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "connected",
    "message_queue": "connected",
    "storage": "connected"
  }
}
```

### Messages

#### POST /messages

Send a message to the integration engine.

**Request**
```http
POST /messages
Content-Type: application/json

{
  "content_type": "application/hl7-v2",
  "message": "MSH|^~\&|SENDING_APP|SENDING_FACILITY|...",
  "metadata": {
    "source": "emr-system",
    "destination": ["lis-system", "archive"]
  }
}
```

**Response**
```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "timestamp": "2025-06-29T21:00:00Z"
}
```

### Message Status

#### GET /messages/{message_id}

Get the status of a message.

**Response**
```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processed",
  "timestamp": "2025-06-29T21:00:01Z",
  "processing_time_ms": 250,
  "destinations": [
    {
      "system": "lis-system",
      "status": "delivered",
      "timestamp": "2025-06-29T21:00:01Z"
    },
    {
      "system": "archive",
      "status": "delivered",
      "timestamp": "2025-06-29T21:00:01Z"
    }
  ]
}
```

## Message Queue API

### Publish a Message

```python
import redis.asyncio as redis
import json

async def publish_message(stream: str, message: dict):
    r = await redis.Redis()
    message_id = await r.xadd(stream, {"data": json.dumps(message)})
    return message_id
```

### Consume Messages

```python
import redis.asyncio as redis
import json

async def consume_messages(stream: str, consumer_group: str, consumer_name: str):
    r = await redis.Redis()
    
    # Create consumer group if it doesn't exist
    try:
        await r.xgroup_create(stream, consumer_group, id="0", mkstream=True)
    except Exception:
        print(f"Consumer group {consumer_group} already exists")
    
    last_id = "0"
    
    while True:
        try:
            # Read messages from the stream
            messages = await r.xreadgroup(
                groupname=consumer_group,
                consumername=consumer_name,
                streams={stream: ">"},
                count=10,
                block=5000
            )
            
            if not messages:
                continue
                
            for stream_name, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    # Process the message
                    message = json.loads(message_data[b'data'])
                    print(f"Processing message: {message_id}")
                    
                    # Acknowledge the message
                    await r.xack(stream_name, consumer_group, message_id)
                    last_id = message_id
                    
        except Exception as e:
            print(f"Error processing message: {e}")
            await asyncio.sleep(5)
```

## Error Handling

### Error Responses

#### 400 Bad Request
```json
{
  "error": {
    "code": "invalid_request",
    "message": "Invalid request body",
    "details": {
      "field": "message",
      "issue": "required field missing"
    }
  }
}
```

#### 401 Unauthorized
```json
{
  "error": {
    "code": "unauthorized",
    "message": "Invalid or missing API key"
  }
}
```

#### 429 Too Many Requests
```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded",
    "retry_after": 60
  }
}
```

## Rate Limiting

- **Rate Limit**: 1000 requests per minute per API key
- **Response Headers**:
  - `X-RateLimit-Limit`: Request limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Time when limit resets (UTC)

## Webhooks

### Webhook Payload

```json
{
  "event": "message.processed",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processed",
  "timestamp": "2025-06-29T21:00:01Z",
  "details": {
    "processing_time_ms": 250,
    "destinations": ["lis-system", "archive"]
  }
}
```

### Webhook Headers

```
X-Integration-Event: message.processed
X-Integration-Delivery: d3b0f8c7-1a2b-4c3d-4e5f-6a7b8c9d0e1f
X-Integration-Signature: sha256=...
```

## SDKs

### Python SDK

```python
from integration_engine import IntegrationClient

client = IntegrationClient(api_key="your_api_key")

# Send a message
response = client.send_message(
    content_type="application/hl7-v2",
    message="MSH|^~\&|...",
    metadata={"source": "emr-system"}
)

# Get message status
status = client.get_message_status(response.message_id)
```

## WebSocket API

### Connect

```
wss://api.your-integration-engine.com/v1/ws
```

### Subscribe to Events

```json
{
  "action": "subscribe",
  "events": ["message.processed", "message.failed"]
}
```

### Receive Events

```json
{
  "event": "message.processed",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-06-29T21:00:01Z"
}
```

## Versioning

API versioning is done through the URL path. The current version is `v1`.

Example: `https://api.your-integration-engine.com/v1/messages`

## Deprecation Policy

- Endpoints will be supported for at least 12 months after deprecation
- Deprecated endpoints will return a `Deprecation` header
- Breaking changes will only be introduced in new API versions
