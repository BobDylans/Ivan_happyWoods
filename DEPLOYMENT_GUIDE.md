# Production Deployment Guide - P0 Phase

This guide covers the production deployment of Voice Agent API with integrated distributed tracing (Jaeger), metrics (Prometheus), and visualization (Grafana).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Database Migration](#database-migration)
6. [Monitoring and Tracing](#monitoring-and-tracing)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- Docker & Docker Compose 2.0+ (for Docker deployment)
- kubectl 1.24+ (for Kubernetes deployment)
- PostgreSQL client tools (for database management)
- curl (for health checks)

### Required Credentials
- OpenAI API key (LLM provider)
- Tavily API key (search tool)
- At least 2 API keys for client authentication

### Infrastructure Requirements
- Minimum 2 vCPU, 4GB RAM per node
- 10GB persistent storage for PostgreSQL
- Network connectivity for all services
- TLS/HTTPS support (recommended)

---

## Pre-Deployment Checklist

- [ ] All environment variables configured in `.env.production`
- [ ] PostgreSQL password changed from default
- [ ] API keys are unique and secure
- [ ] Backup taken of existing database (if upgrading)
- [ ] Jaeger is accessible from API containers
- [ ] Resource limits verified for your infrastructure
- [ ] CORS origins updated for your domain
- [ ] Security scan completed on base images
- [ ] Load balancer/reverse proxy configured
- [ ] TLS/SSL certificates obtained

---

## Docker Deployment

### 1. Prepare Environment

```bash
# Copy and configure the production environment file
cp .env.production.template .env.production

# Edit and fill in all REQUIRED values
nano .env.production
```

### 2. Build Docker Image

```bash
# Build the Docker image
docker build -t voice-agent-api:latest .

# Optionally, tag for your registry
docker tag voice-agent-api:latest your-registry.com/voice-agent-api:latest
docker push your-registry.com/voice-agent-api:latest
```

### 3. Deploy with Docker Compose

```bash
# Start all services (PostgreSQL, Qdrant, Jaeger, Prometheus, Grafana, API)
docker-compose -f docker-compose.prod.yml up -d

# Verify all services are running
docker-compose -f docker-compose.prod.yml ps

# Check service health
curl http://localhost:8000/api/v1/health
```

### 4. Access Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Jaeger UI**: http://localhost:16686
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/password)

---

## Kubernetes Deployment

### 1. Prepare Kubernetes Cluster

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create ConfigMap
kubectl apply -f k8s/configmap.yaml

# Create Secrets (first edit secrets.yaml with real values)
cp k8s/secrets.yaml.template k8s/secrets.yaml
# Edit k8s/secrets.yaml with real credentials
kubectl apply -f k8s/secrets.yaml

# IMPORTANT: Delete the secrets.yaml file after applying
rm k8s/secrets.yaml  # Never commit secrets to git!
```

### 2. Deploy Database (PostgreSQL)

```bash
kubectl apply -f k8s/postgres-statefulset.yaml

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n voice-agent --timeout=300s

# Verify PostgreSQL is running
kubectl get pods -n voice-agent -l app=postgres
```

### 3. Deploy Distributed Tracing (Jaeger)

```bash
kubectl apply -f k8s/jaeger-deployment.yaml

# Wait for Jaeger to be ready
kubectl wait --for=condition=ready pod -l app=jaeger -n voice-agent --timeout=60s

# Port forward to access Jaeger UI
kubectl port-forward -n voice-agent svc/jaeger 16686:16686 &
# Access at http://localhost:16686
```

### 4. Deploy API Service

```bash
# First, build and push image to your registry
docker build -t your-registry.com/voice-agent-api:latest .
docker push your-registry.com/voice-agent-api:latest

# Update the image in api-deployment.yaml
sed -i 's|voice-agent-api:latest|your-registry.com/voice-agent-api:latest|g' k8s/api-deployment.yaml

# Deploy the API
kubectl apply -f k8s/api-deployment.yaml

# Wait for deployment to be ready
kubectl wait --for=condition=available --timeout=300s \
  deployment/voice-agent-api -n voice-agent

# Check the deployment status
kubectl get deployment -n voice-agent
kubectl get pods -n voice-agent -l app=voice-agent-api
```

### 5. Verify Deployment

```bash
# Port forward to the API service
kubectl port-forward -n voice-agent svc/voice-agent-api 8000:80 &

# Test health endpoint
curl http://localhost:8000/api/v1/health

# Check logs
kubectl logs -n voice-agent deployment/voice-agent-api --tail=50
kubectl logs -n voice-agent deployment/voice-agent-api --follow
```

---

## Database Migration

### Run Migrations Manually

```bash
# Connect to PostgreSQL container/pod
# Docker:
docker exec -it voice_agent_postgres_prod psql -U agent_user -d voice_agent

# Kubernetes:
kubectl exec -it -n voice-agent postgres-0 -- \
  psql -U agent_user -d voice_agent

# Inside psql, run the migration script:
\i /path/to/scripts/db_migration.sql

# Or pipe the script:
psql -U agent_user -d voice_agent -f scripts/db_migration.sql
```

### Verify Migration Status

```sql
SELECT version, description, installed_on, success
FROM schema_migrations
ORDER BY installed_on DESC;
```

### Expected Output

```
      version      |            description            |     installed_on      | success
-------------------+-----------------------------------+-----------------------+---------
 003_add_backup_tables  | Add backup tracking tables | 2024-01-15 10:30:00 | t
 002_add_metrics_tables | Add performance metrics tables | 2024-01-15 10:29:45 | t
 001_add_tracing_tables | Add tracing storage tables | 2024-01-15 10:29:30 | t
```

---

## Monitoring and Tracing

### Accessing Jaeger UI

1. **Local Port Forward**:
   ```bash
   kubectl port-forward -n voice-agent svc/jaeger 16686:16686
   ```

2. **Access**: http://localhost:16686

3. **View Traces**:
   - Select "voice-agent-api" service from the dropdown
   - Choose operation (e.g., "agent.process_message")
   - View detailed trace timeline

### Key Metrics to Monitor

- **HTTP Request Duration**: `http.server.duration_ms`
- **LLM API Response Time**: `agent.call_llm` span duration
- **Tool Execution Time**: `tool.execute` span duration
- **Error Rate**: Track spans with status="error"

### Grafana Dashboard

1. **Add Prometheus Data Source**:
   - URL: http://prometheus:9090
   - Save & Test

2. **Import Voice Agent Dashboard**:
   - Import from `grafana/provisioning/dashboards/voice-agent.yml`

3. **Key Panels**:
   - Request rate and latency
   - Error rate by endpoint
   - Tool execution success rate
   - Active sessions

---

## Rollback Procedures

### Docker Rollback

```bash
# 1. Stop the API service
docker-compose -f docker-compose.prod.yml stop api

# 2. Revert database (if schema changed)
docker exec voice_agent_postgres_prod psql -U agent_user -d voice_agent \
  -f /path/to/scripts/db_rollback.sql

# 3. Start with previous image version
docker-compose -f docker-compose.prod.yml up -d api

# 4. Verify
curl http://localhost:8000/api/v1/health
```

### Kubernetes Rollback

```bash
# 1. View rollout history
kubectl rollout history deployment/voice-agent-api -n voice-agent

# 2. Rollback to previous version
kubectl rollout undo deployment/voice-agent-api -n voice-agent

# 3. Verify the rollback
kubectl rollout status deployment/voice-agent-api -n voice-agent

# 4. If needed, rollback to a specific revision
kubectl rollout undo deployment/voice-agent-api -n voice-agent --to-revision=2
```

### Database Rollback

```sql
-- Connect to database and run rollback script
\i scripts/db_rollback.sql

-- Check archived data
SELECT COUNT(*) FROM trace_spans_archive;
SELECT COUNT(*) FROM performance_metrics_archive;
```

---

## Troubleshooting

### API Service Won't Start

**Symptoms**: Pod shows "CrashLoopBackOff" or "ImagePullBackOff"

**Solutions**:
```bash
# Check logs
kubectl logs -n voice-agent deployment/voice-agent-api

# Verify image exists
docker images | grep voice-agent-api

# Check events
kubectl describe pod -n voice-agent <pod-name>

# Verify environment variables
kubectl exec -it -n voice-agent <pod-name> -- env | grep VOICE_AGENT
```

### Database Connection Timeout

**Symptoms**: "could not connect to server" errors

**Solutions**:
```bash
# Check PostgreSQL is running
kubectl get pods -n voice-agent -l app=postgres

# Check PostgreSQL logs
kubectl logs -n voice-agent postgres-0

# Test connection from API pod
kubectl exec -it -n voice-agent <api-pod> -- \
  pg_isready -h postgres -p 5432 -U agent_user

# Verify PostgreSQL service DNS
kubectl exec -it -n voice-agent <api-pod> -- \
  nslookup postgres.voice-agent.svc.cluster.local
```

### Jaeger Not Receiving Traces

**Symptoms**: Jaeger UI shows no traces

**Solutions**:
```bash
# Check Jaeger is running
kubectl get pods -n voice-agent -l app=jaeger

# Check Jaeger logs
kubectl logs -n voice-agent deployment/jaeger

# Verify Jaeger is accessible from API
kubectl exec -it -n voice-agent <api-pod> -- \
  curl -v http://jaeger:6831

# Check API logs for tracing errors
kubectl logs -n voice-agent deployment/voice-agent-api | grep -i jaeger
```

### High Memory Usage

**Symptoms**: Pods being killed for OOMKilled

**Solutions**:
```bash
# Check current resource usage
kubectl top pods -n voice-agent

# Update resource limits in api-deployment.yaml
# Increase limits: memory: "2Gi"

# Reapply the deployment
kubectl apply -f k8s/api-deployment.yaml
```

---

## Performance Tuning

### For High Traffic

1. **Increase API Replicas**: Edit `replicas` in `api-deployment.yaml`
2. **Increase HPA Max Replicas**: Edit `maxReplicas` in `api-deployment.yaml`
3. **Increase Trace Sampling**: Set `TRACE_SAMPLE_RATE=0.1` to reduce overhead
4. **Use PostgreSQL Connection Pooling**: Configure PgBouncer

### For Low Latency

1. **Increase API Resources**: `requests: {cpu: "500m", memory: "1Gi"}`
2. **Enable Caching**: Redis session storage
3. **Optimize Jaeger**: Use probabilistic sampler
4. **Monitor Metrics**: Use Prometheus for insights

---

## Security Best Practices

1. **Secrets Management**:
   - Use Kubernetes Secrets (not .env files)
   - Consider HashiCorp Vault for secrets
   - Rotate API keys regularly

2. **Network Security**:
   - Use Network Policies to restrict traffic
   - Enable TLS/SSL for all endpoints
   - Use private container registries

3. **Container Security**:
   - Scan images for vulnerabilities
   - Use read-only root filesystem
   - Run containers as non-root user

4. **RBAC**:
   - Create specific service accounts
   - Apply principle of least privilege
   - Audit RBAC changes

---

## Support and Updates

For issues or questions:
1. Check logs: `kubectl logs -n voice-agent <pod-name>`
2. Review traces in Jaeger UI
3. Check metrics in Prometheus/Grafana
4. Consult troubleshooting section above

---

Last Updated: 2024-11-13
Version: 1.0.0 (P0 Phase)
