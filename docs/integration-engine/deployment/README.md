# Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 1.29+
- 4 CPU cores
- 8GB RAM
- 50GB free disk space

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/integration-engine.git
cd integration-engine
```

### 2. Configure Environment

Copy the example environment file and update the values:

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Verify Installation

```bash
curl http://localhost:8080/health
```

## Configuration

### Core Configuration

```yaml
# config/config.yaml

# General settings
app:
  name: integration-engine
  environment: production
  log_level: info

# Message broker configuration
message_broker:
  type: redis  # or kafka, nats
  host: redis
  port: 6379
  username: ""
  password: ""
  tls: false

# Storage configuration
storage:
  type: filesystem  # or s3, azure-blob, gcs
  path: /data/storage

# API server configuration
server:
  host: 0.0.0.0
  port: 8080
  cors_allowed_origins:
    - "*"
  rate_limit: 1000
  
# Plugins configuration
plugins:
  directory: /app/plugins
  enabled:
    - hl7_validator
    - fhir_transformer
    - mllp_sender
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Application environment | `production` |
| `LOG_LEVEL` | Logging level | `info` |
| `MESSAGE_BROKER_URL` | Message broker connection URL | `redis://redis:6379` |
| `STORAGE_PATH` | Path for file storage | `/data/storage` |
| `API_KEY` | API key for authentication | |
| `TZ` | Timezone | `UTC` |

## Deployment Options

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    image: your-org/integration-engine:latest
    ports:
      - "8080:8080"
    environment:
      - APP_ENV=production
      - LOG_LEVEL=info
      - MESSAGE_BROKER_URL=redis://redis:6379
    depends_on:
      - redis
    volumes:
      - ./config:/app/config
      - ./data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

### Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: integration-engine
  labels:
    app: integration-engine
spec:
  replicas: 3
  selector:
    matchLabels:
      app: integration-engine
  template:
    metadata:
      labels:
        app: integration-engine
    spec:
      containers:
      - name: integration-engine
        image: your-org/integration-engine:latest
        ports:
        - containerPort: 8080
        env:
        - name: APP_ENV
          value: production
        - name: MESSAGE_BROKER_URL
          value: "redis://redis:6379"
        resources:
          requests:
            cpu: "1"
            memory: "1Gi"
          limits:
            cpu: "2"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: integration-engine
spec:
  selector:
    app: integration-engine
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

## High Availability

### Redis Sentinel

```yaml
# docker-compose.ha.yml
version: '3.8'

services:
  redis-sentinel:
    image: redis:7
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    volumes:
      - ./config/redis/sentinel.conf:/usr/local/etc/redis/sentinel.conf
    ports:
      - "26379:26379"
    environment:
      - SENTINEL_DOWN_AFTER=5000
      - SENTINEL_FAILOVER_TIMEOUT=10000

  redis-1:
    image: redis:7
    command: redis-server /usr/local/etc/redis/redis.conf
    volumes:
      - ./config/redis/redis-1.conf:/usr/local/etc/redis/redis.conf
    ports:
      - "6379:6379"

  # Add more Redis instances as needed
```

## Scaling

### Horizontal Scaling

1. **Stateless Services**
   - API servers
   - Processors
   - Connectors

2. **Stateful Services**
   - Redis (sharding/clustering)
   - Kafka (partitioning)
   - Database (read replicas)

### Resource Limits

```yaml
# Example resource limits for a processor
resources:
  requests:
    cpu: "1"
    memory: "2Gi"
  limits:
    cpu: "2"
    memory: "4Gi"
```

## Backup and Recovery

### Data Backup

```bash
# Backup Redis data
docker exec -it redis redis-cli save

# Backup configuration files
tar czf config-backup-$(date +%Y%m%d).tar.gz config/
```

### Recovery

1. Restore Redis data
2. Restore configuration files
3. Restart services

## Monitoring

### Prometheus Metrics

```yaml
# config/prometheus.yml
scrape_configs:
  - job_name: 'integration_engine'
    static_configs:
      - targets: ['localhost:8080']
```

### Logging

```yaml
# Logging configuration
logging:
  level: info
  format: json
  output: /var/log/integration-engine.log
  retention: 30d
```

## Security

### Network Security

- Use internal networks
- Enable TLS for all communications
- Restrict access with firewalls

### Secrets Management

```bash
# Use Docker secrets or Kubernetes secrets
# Example with Docker Compose
services:
  api:
    secrets:
      - api_key

secrets:
  api_key:
    file: ./secrets/api_key.txt
```

## Upgrading

1. Check the release notes
2. Backup your data
3. Update the Docker image
4. Apply migrations if needed
5. Restart services

## Troubleshooting

### Common Issues

1. **Connection Issues**
   - Check network connectivity
   - Verify credentials
   - Check firewall rules

2. **Performance Issues**
   - Check resource usage
   - Review logs for errors
   - Consider scaling

3. **Data Issues**
   - Validate input data
   - Check for schema changes
   - Verify storage permissions

### Getting Help

- Check the logs: `docker-compose logs -f`
- Check the documentation
- Open an issue on GitHub
- Contact support

## License

[Your License Here]
