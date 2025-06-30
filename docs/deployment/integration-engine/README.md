# Integration Engine Deployment Guide

This guide provides comprehensive instructions for deploying the Integration Engine in various environments, including development, staging, and production.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Deployment Options](#deployment-options)
- [Configuration](#configuration)
- [Scaling](#scaling)
- [High Availability](#high-availability)
- [Backup and Recovery](#backup-and-recovery)
- [Monitoring](#monitoring)
- [Upgrades](#upgrades)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU Cores | 2       | 4+          |
| Memory    | 4GB     | 16GB+       |
| Storage   | 20GB    | 100GB+      |
| OS        | Linux   | Linux       |


### Dependencies
- Docker 20.10+
- Docker Compose 1.29+
- Kubernetes 1.20+ (for Kubernetes deployment)
- Helm 3.0+ (for Kubernetes deployment)

## Deployment Options

### 1. Docker Compose (Development/Testing)

#### Quick Start
```bash
# Clone the repository
git clone https://github.com/your-org/healthcare-integration-engine.git
cd healthcare-integration-engine

# Copy example environment file
cp .env.example .env

# Start services
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

#### Configuration Overrides
Create a `docker-compose.override.yml` for custom configurations:

```yaml
version: '3.8'

services:
  api:
    environment:
      - LOG_LEVEL=DEBUG
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config
```

### 2. Kubernetes (Production)

#### Helm Chart Installation

1. Add the Helm repository:
   ```bash
   helm repo add integration-engine https://charts.your-org.com/integration-engine
   helm repo update
   ```

2. Create a values file (`values-prod.yaml`):
   ```yaml
   replicaCount: 3
   
   image:
     repository: ghcr.io/your-org/integration-engine
     tag: v1.0.0
     pullPolicy: IfNotPresent
   
   resources:
     limits:
       cpu: 1000m
       memory: 2Gi
     requests:
       cpu: 500m
       memory: 1Gi
   
   autoscaling:
     enabled: true
     minReplicas: 3
     maxReplicas: 10
     targetCPUUtilizationPercentage: 70
   
   ingress:
     enabled: true
     className: nginx
     hosts:
       - host: integration.your-org.com
         paths:
           - path: /
             pathType: Prefix
     tls:
       - secretName: integration-tls
         hosts:
           - integration.your-org.com
   ```

3. Install the chart:
   ```bash
   helm install integration-engine integration-engine/integration-engine \
     -f values-prod.yaml \
     --namespace integration \
     --create-namespace
   ```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `development` | Environment name (development, staging, production) |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Redis connection URL |
| `DATABASE_URL` | Yes | `postgresql://user:pass@localhost:5432/integration` | Database connection URL |
| `API_KEY` | Yes | - | API key for authentication |
| `JWT_SECRET` | Yes | - | JWT secret for token generation |

### Configuration Files

#### `config/default.yaml`
```yaml
server:
  host: 0.0.0.0
  port: 8000
  debug: false
  workers: 4

logging:
  level: INFO
  format: json
  file: /var/log/integration-engine.log

redis:
  url: redis://redis:6379/0
  timeout: 5
  max_connections: 20

database:
  url: postgresql://user:pass@postgres:5432/integration
  pool_size: 10
  max_overflow: 20

security:
  jwt_secret: ${JWT_SECRET}
  api_key: ${API_KEY}
  cors_origins: 
    - http://localhost:3000
    - https://*.your-org.com
```

## Scaling

### Horizontal Scaling

1. **API Servers**:
   ```bash
   # Scale API service
   kubectl scale deployment integration-engine-api --replicas=5 -n integration
   ```

2. **Workers**:
   ```yaml
   # values-prod.yaml
   worker:
     replicaCount: 5
     resources:
       requests:
         cpu: 500m
         memory: 1Gi
       limits:
         cpu: 2000m
         memory: 4Gi
   ```

### Database Scaling

1. **Read Replicas**:
   ```yaml
   # values-prod.yaml
   postgresql:
     readReplicas:
       replicaCount: 2
       resources:
         requests:
           cpu: 500m
           memory: 1Gi
   ```

2. **Connection Pooling**:
   ```yaml
   # config/production.yaml
   database:
     pool_size: 20
     max_overflow: 40
     pool_timeout: 30
     pool_recycle: 3600
   ```

## High Availability

### Multi-AZ Deployment
```yaml
# values-prod.yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
            - key: app.kubernetes.io/name
              operator: In
              values:
                - integration-engine
        topologyKey: topology.kubernetes.io/zone
```

### Health Checks

1. **Liveness Probe**:
   ```yaml
   livenessProbe:
     httpGet:
       path: /healthz
       port: http
     initialDelaySeconds: 30
     periodSeconds: 10
     timeoutSeconds: 5
     failureThreshold: 3
   ```

2. **Readiness Probe**:
   ```yaml
   readinessProbe:
     httpGet:
       path: /readyz
       port: http
     initialDelaySeconds: 5
     periodSeconds: 5
     timeoutSeconds: 3
     successThreshold: 1
     failureThreshold: 3
   ```

## Backup and Recovery

### Database Backups

1. **Scheduled Backups**:
   ```yaml
   # values-prod.yaml
   backup:
     enabled: true
     schedule: "0 2 * * *"
     retention: 30d
     s3:
       bucket: your-backup-bucket
       region: us-west-2
   ```

2. **Manual Backup**:
   ```bash
   # Create backup
   kubectl exec -n integration postgres-0 -- pg_dump -U postgres integration > backup.sql
   
   # Restore from backup
   cat backup.sql | kubectl exec -i -n integration postgres-0 -- psql -U postgres integration
   ```

### Disaster Recovery

1. **ETCD Backup**:
   ```bash
   # Create etcd snapshot
   ETCDCTL_API=3 etcdctl --endpoints=127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key \
     snapshot save snapshot.db
   ```

2. **Restore Procedure**:
   ```bash
   # Stop API server
   mv /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/
   
   # Restore snapshot
   ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \
     --data-dir /var/lib/etcd-restored
   
   # Update etcd manifest
   # Start API server
   mv /tmp/kube-apiserver.yaml /etc/kubernetes/manifests/
   ```

## Monitoring

### Metrics Collection

1. **Prometheus Configuration**:
   ```yaml
   # prometheus-values.yaml
   server:
     global:
       scrape_interval: 15s
     scrape_configs:
       - job_name: 'integration-engine'
         metrics_path: '/metrics'
         static_configs:
           - targets: ['integration-engine:8000']
   ```

2. **Grafana Dashboard**:
   - Import dashboard ID: 12345
   - Configure alerts for critical metrics

### Logging

1. **ELK Stack**:
   ```yaml
   # filebeat-config.yaml
   filebeat.inputs:
     - type: container
       paths:
         - '/var/lib/docker/containers/*/*.log'
   output.elasticsearch:
     hosts: ['elasticsearch:9200']
   ```

## Upgrades

### Version Compatibility

| Current Version | Target Version | Breaking Changes | Upgrade Path |
|----------------|----------------|------------------|--------------|
| 1.0.x          | 1.1.0          | No               | Direct       |
| 1.1.x          | 2.0.0          | Yes              | 1.1 → 1.2 → 2.0 |

### Upgrade Procedure

1. **Pre-Upgrade Checklist**:
   - [ ] Backup databases
   - [ ] Review release notes
   - [ ] Test in staging
   - [ ] Notify stakeholders

2. **Helm Upgrade**:
   ```bash
   helm upgrade integration-engine integration-engine/integration-engine \
     --version 2.0.0 \
     -f values-prod.yaml \
     --namespace integration
   ```

3. **Database Migrations**:
   ```bash
   kubectl exec -n integration deployment/integration-engine-api -- \
     alembic upgrade head
   ```

## Troubleshooting

### Common Issues

1. **Connection Issues**:
   ```bash
   # Check network connectivity
   kubectl run -it --rm --image=nicolaka/netshoot debug \
     -- /bin/bash -c "ping redis; nc -zv redis 6379"
   ```

2. **Resource Constraints**:
   ```bash
   # Check resource usage
   kubectl top pods -n integration
   kubectl describe nodes | grep -A 10 "Allocated resources"
   ```

3. **Logs**:
   ```bash
   # View logs
   kubectl logs -n integration deployment/integration-engine-api -f
   
   # Previous container logs
   kubectl logs -n integration deployment/integration-engine-api --previous
   ```

### Support

1. **Gather Information**:
   ```bash
   # Get all resources
   kubectl get all -n integration
   
   # Describe failing pod
   kubectl describe pod -n integration integration-engine-api-xxxxx
   
   # Get events
   kubectl get events -n integration --sort-by='.metadata.creationTimestamp'
   ```

2. **Contact Support**:
   - Email: support@your-org.com
   - Slack: #integration-engine-support
   - On-call: #oncall-engineering

## Security

### Network Policies

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: integration-engine
  namespace: integration
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
        - podSelector:
            matchLabels:
              app: ingress-nginx
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
```

### Secrets Management

1. **Sealed Secrets**:
   ```bash
   # Install kubeseal
   kubeseal --fetch-cert \
     --controller-namespace=kube-system \
     > pub-cert.pem
   
   # Create sealed secret
   kubectl create secret generic api-keys \
     --from-literal=api-key=supersecret \
     --dry-run=client -o yaml | \
     kubeseal --cert pub-cert.pem \
     > sealed-secret.yaml
   ```

## Appendix

### Sample Values Files

#### `values-dev.yaml`
```yaml
replicaCount: 1

image:
  repository: ghcr.io/your-org/integration-engine
  tag: latest
  pullPolicy: Always

resources:
  limits:
    cpu: 500m
    memory: 1Gi
  requests:
    cpu: 100m
    memory: 256Mi

postgresql:
  enabled: true
  auth:
    username: postgres
    password: postgres
    database: integration

redis:
  enabled: true
  auth:
    enabled: false
```

### Useful Commands

```bash
# Port forward to localhost
kubectl port-forward -n integration svc/integration-engine 8000:8000

# Get pod status
kubectl get pods -n integration -w

# View logs with timestamps
kubectl logs -n integration deployment/integration-engine-api -f --timestamps

# Debug pod
kubectl debug -n integration -it pod/integration-engine-api-xxxxx -- /bin/bash

# Get resource usage
kubectl top pods -n integration --sort-by='cpu'

# Describe service
kubectl describe svc -n integration integration-engine
```

## Related Documents
- [Configuration Reference](../configuration/README.md)
- [Monitoring and Alerting](../monitoring/README.md)
- [Security Best Practices](../security/README.md)
