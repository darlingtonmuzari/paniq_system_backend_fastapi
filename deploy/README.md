# Panic System Platform Deployment Guide

This directory contains all deployment configurations, scripts, and documentation for the Panic System Platform.

## Directory Structure

```
deploy/
├── README.md                          # This file
├── environments/                      # Environment-specific configurations
│   ├── production.env                # Production environment variables
│   ├── staging.env                   # Staging environment variables
│   └── development.env               # Development environment variables
├── scripts/                          # Deployment scripts
│   ├── deploy.sh                     # Main deployment script
│   ├── rollback.sh                   # Rollback script
│   └── health-check.sh               # Health check script
├── backup-restore/                   # Backup and disaster recovery
│   ├── backup-procedures.md          # Backup procedures documentation
│   ├── backup-scripts/               # Automated backup scripts
│   └── restore-scripts/              # Disaster recovery scripts
└── monitoring/                       # Monitoring configurations
    ├── prometheus/                   # Prometheus configuration
    ├── grafana/                      # Grafana dashboards
    └── alertmanager/                 # Alert configurations
```

## Quick Start

### Prerequisites

1. **Docker** - For building and running containers
2. **kubectl** - For Kubernetes cluster management
3. **Helm** (optional) - For package management
4. **AWS CLI** - For cloud storage and services

### Environment Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/panicsystem/panic-system-platform.git
   cd panic-system-platform
   ```

2. **Configure kubectl** for your target cluster:
   ```bash
   kubectl config use-context your-cluster-context
   ```

3. **Create Kubernetes secrets**:
   ```bash
   # Copy and modify the secrets template
   cp k8s/secrets.yaml k8s/secrets-local.yaml
   # Edit secrets-local.yaml with actual values
   kubectl apply -f k8s/secrets-local.yaml
   ```

### Deployment Commands

#### Development Environment
```bash
# Start local development environment
docker-compose up -d

# Or deploy to development Kubernetes cluster
./deploy/scripts/deploy.sh development latest
```

#### Staging Environment
```bash
# Deploy to staging
./deploy/scripts/deploy.sh staging v1.2.3

# Check deployment status
kubectl get pods -n panic-system-staging
```

#### Production Environment
```bash
# Deploy to production (requires approval)
./deploy/scripts/deploy.sh production v1.2.3

# Verify deployment
curl -f https://api.panicsystem.com/health
```

## Deployment Environments

### Development
- **Purpose**: Local development and testing
- **Infrastructure**: Docker Compose or local Kubernetes
- **Database**: Local PostgreSQL with test data
- **External Services**: Mock/test endpoints
- **Monitoring**: Basic logging only

### Staging
- **Purpose**: Pre-production testing and validation
- **Infrastructure**: Kubernetes cluster (staging)
- **Database**: Staging PostgreSQL with sanitized production data
- **External Services**: Sandbox/test endpoints
- **Monitoring**: Full monitoring stack
- **URL**: https://staging-api.panicsystem.com

### Production
- **Purpose**: Live production environment
- **Infrastructure**: Kubernetes cluster (production)
- **Database**: Production PostgreSQL with full data
- **External Services**: Live production endpoints
- **Monitoring**: Full monitoring with alerting
- **URL**: https://api.panicsystem.com

## Infrastructure Components

### Core Services

#### PostgreSQL Database
- **Image**: `postgis/postgis:15-3.3`
- **Storage**: 100GB persistent volume
- **Backup**: Daily automated backups to S3
- **High Availability**: Master-slave replication

#### Redis Cache
- **Image**: `redis:7-alpine`
- **Storage**: 20GB persistent volume
- **Configuration**: Optimized for caching and sessions
- **Persistence**: AOF and RDB snapshots

#### API Application
- **Image**: Custom FastAPI application
- **Replicas**: 3 (production), 2 (staging), 1 (development)
- **Resources**: 1GB RAM, 500m CPU per pod
- **Auto-scaling**: HPA based on CPU and memory

### Supporting Services

#### Monitoring Stack
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert routing and notification

#### Load Balancing
- **Ingress Controller**: NGINX Ingress
- **SSL/TLS**: Let's Encrypt certificates
- **Rate Limiting**: Per-endpoint rate limits

## Configuration Management

### Environment Variables

Environment-specific configurations are managed through:

1. **ConfigMaps**: Non-sensitive configuration
2. **Secrets**: Sensitive data (passwords, API keys)
3. **Environment Files**: Local development overrides

### Secret Management

Secrets are managed using Kubernetes Secrets with the following structure:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: panic-system-secrets
type: Opaque
stringData:
  DATABASE_PASSWORD: "secure_password"
  JWT_SECRET_KEY: "jwt_secret_key"
  TWILIO_AUTH_TOKEN: "twilio_token"
  # ... other secrets
```

### Configuration Validation

Before deployment, configurations are validated for:
- Required environment variables
- Secret availability
- External service connectivity
- Database schema compatibility

## Deployment Process

### Automated CI/CD Pipeline

The deployment process is automated through GitHub Actions:

1. **Code Quality Checks**
   - Linting and formatting
   - Unit tests with coverage
   - Security scanning

2. **Build and Test**
   - Docker image building
   - Integration tests
   - Performance tests

3. **Deployment**
   - Staging deployment (automatic on develop branch)
   - Production deployment (manual approval required)
   - Database migrations
   - Health checks

### Manual Deployment

For manual deployments, use the deployment script:

```bash
# Deploy specific version to staging
./deploy/scripts/deploy.sh staging v1.2.3

# Deploy latest to development
./deploy/scripts/deploy.sh development latest

# Rollback last deployment
./deploy/scripts/deploy.sh --rollback production
```

### Deployment Verification

After deployment, the following checks are performed:

1. **Health Check**: `/health` endpoint responds with 200
2. **API Check**: `/api/v1/` endpoint returns expected response
3. **Database Check**: Database connectivity and migrations
4. **External Services**: Third-party service connectivity

## Monitoring and Observability

### Metrics Collection

- **Application Metrics**: Custom business metrics
- **Infrastructure Metrics**: CPU, memory, disk, network
- **Database Metrics**: Query performance, connections
- **External Service Metrics**: Response times, error rates

### Logging

- **Structured Logging**: JSON format with correlation IDs
- **Log Aggregation**: Centralized logging with ELK stack
- **Log Retention**: 30 days for application logs, 90 days for audit logs

### Alerting

Critical alerts are configured for:
- Application downtime
- High error rates
- Database connectivity issues
- Resource exhaustion
- Security incidents

### Dashboards

Grafana dashboards provide visibility into:
- System overview and health
- API performance metrics
- Database performance
- Business metrics (emergency requests, response times)

## Security Considerations

### Network Security
- **Private Subnets**: Database and cache in private subnets
- **Security Groups**: Restrictive firewall rules
- **VPN Access**: Administrative access through VPN

### Application Security
- **Container Security**: Regular image scanning
- **Secret Management**: Encrypted secrets at rest
- **RBAC**: Role-based access control for Kubernetes
- **TLS**: End-to-end encryption

### Compliance
- **Data Protection**: GDPR and CCPA compliance
- **Audit Logging**: All administrative actions logged
- **Access Control**: Multi-factor authentication required

## Backup and Disaster Recovery

### Backup Strategy
- **Database**: Daily full backups, continuous WAL archiving
- **Files**: Real-time sync to S3
- **Configuration**: Version-controlled infrastructure as code

### Recovery Procedures
- **RTO**: 4 hours for complete system recovery
- **RPO**: 15 minutes maximum data loss
- **Testing**: Monthly disaster recovery drills

### Business Continuity
- **Multi-Region**: Active-passive setup across regions
- **Failover**: Automated failover for critical services
- **Communication**: Incident response procedures

## Troubleshooting

### Common Issues

#### Deployment Failures
```bash
# Check deployment status
kubectl rollout status deployment/panic-system-api -n panic-system

# View pod logs
kubectl logs -f deployment/panic-system-api -n panic-system

# Describe pod for events
kubectl describe pod <pod-name> -n panic-system
```

#### Database Connection Issues
```bash
# Test database connectivity
kubectl exec -it deployment/panic-system-api -n panic-system -- \
  python -c "from app.core.database import test_connection; test_connection()"

# Check database pod status
kubectl get pods -l app=postgres -n panic-system
```

#### Performance Issues
```bash
# Check resource usage
kubectl top pods -n panic-system

# View metrics in Grafana
# Navigate to https://grafana.panicsystem.com
```

### Emergency Procedures

#### Immediate Response
1. **Assess Impact**: Determine scope and severity
2. **Communicate**: Notify stakeholders and users
3. **Mitigate**: Implement immediate fixes or rollback
4. **Monitor**: Watch for resolution and side effects

#### Escalation Matrix
- **Level 1**: On-call engineer (15 minutes)
- **Level 2**: Team lead (1 hour)
- **Level 3**: Engineering manager (4 hours)
- **Level 4**: CTO (24 hours)

## Support and Maintenance

### Regular Maintenance
- **Security Updates**: Monthly security patches
- **Dependency Updates**: Quarterly dependency updates
- **Performance Tuning**: Ongoing optimization
- **Capacity Planning**: Quarterly capacity reviews

### Support Channels
- **Documentation**: https://docs.panicsystem.com
- **Internal Wiki**: Confluence space
- **Chat**: #panic-system-ops Slack channel
- **Tickets**: JIRA service desk

### Contact Information
- **DevOps Team**: devops@panicsystem.com
- **On-call Engineer**: +1-800-PANIC-OPS
- **Emergency Escalation**: emergency@panicsystem.com

This deployment guide provides comprehensive information for deploying and maintaining the Panic System Platform across all environments.