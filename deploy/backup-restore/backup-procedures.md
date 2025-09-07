# Backup and Disaster Recovery Procedures

## Overview

This document outlines the backup and disaster recovery procedures for the Panic System Platform, including database backups, file storage backups, and complete system recovery procedures.

## Backup Strategy

### 1. Database Backups

#### Automated Daily Backups

```bash
#!/bin/bash
# Database backup script - runs daily via cron

BACKUP_DIR="/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="panic_system"
DB_USER="panic_system_user"
DB_HOST="postgres-service"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database dump
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME \
  --format=custom \
  --compress=9 \
  --verbose \
  --file="$BACKUP_DIR/panic_system_$DATE.dump"

# Create SQL backup for easier inspection
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME \
  --format=plain \
  --verbose \
  --file="$BACKUP_DIR/panic_system_$DATE.sql"

# Compress SQL backup
gzip "$BACKUP_DIR/panic_system_$DATE.sql"

# Upload to cloud storage
aws s3 cp "$BACKUP_DIR/panic_system_$DATE.dump" \
  s3://panic-system-backups/database/daily/

aws s3 cp "$BACKUP_DIR/panic_system_$DATE.sql.gz" \
  s3://panic-system-backups/database/daily/

# Clean up local files older than 7 days
find $BACKUP_DIR -name "*.dump" -mtime +7 -delete
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Database backup completed: panic_system_$DATE"
```

#### Kubernetes CronJob for Database Backup

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
  namespace: panic-system
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15
            command:
            - /bin/bash
            - -c
            - |
              DATE=$(date +%Y%m%d_%H%M%S)
              pg_dump -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME \
                --format=custom --compress=9 \
                --file="/backup/panic_system_$DATE.dump"
              
              # Upload to S3
              aws s3 cp "/backup/panic_system_$DATE.dump" \
                "s3://panic-system-backups/database/daily/"
            env:
            - name: DATABASE_HOST
              valueFrom:
                configMapKeyRef:
                  name: panic-system-config
                  key: DATABASE_HOST
            - name: DATABASE_USER
              valueFrom:
                secretKeyRef:
                  name: panic-system-secrets
                  key: DATABASE_USER
            - name: DATABASE_NAME
              valueFrom:
                configMapKeyRef:
                  name: panic-system-config
                  key: DATABASE_NAME
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: panic-system-secrets
                  key: DATABASE_PASSWORD
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: aws-credentials
                  key: access-key-id
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: aws-credentials
                  key: secret-access-key
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            emptyDir: {}
          restartPolicy: OnFailure
```

### 2. Redis Backups

#### Redis Backup Script

```bash
#!/bin/bash
# Redis backup script

BACKUP_DIR="/backups/redis"
DATE=$(date +%Y%m%d_%H%M%S)
REDIS_HOST="redis-service"
REDIS_PORT="6379"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create Redis backup
redis-cli -h $REDIS_HOST -p $REDIS_PORT --rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Upload to cloud storage
aws s3 cp "$BACKUP_DIR/redis_$DATE.rdb" \
  s3://panic-system-backups/redis/daily/

# Clean up local files older than 7 days
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete

echo "Redis backup completed: redis_$DATE"
```

### 3. File Storage Backups

#### Upload Files Backup

```bash
#!/bin/bash
# File storage backup script

UPLOAD_DIR="/app/uploads"
BACKUP_DIR="/backups/uploads"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Create tar archive of uploads
tar -czf "$BACKUP_DIR/uploads_$DATE.tar.gz" -C $UPLOAD_DIR .

# Upload to cloud storage
aws s3 cp "$BACKUP_DIR/uploads_$DATE.tar.gz" \
  s3://panic-system-backups/uploads/daily/

# Sync uploads to S3 for real-time backup
aws s3 sync $UPLOAD_DIR s3://panic-system-uploads/ --delete

# Clean up local backup files older than 3 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +3 -delete

echo "File storage backup completed: uploads_$DATE"
```

### 4. Configuration Backups

#### Kubernetes Configuration Backup

```bash
#!/bin/bash
# Kubernetes configuration backup script

BACKUP_DIR="/backups/k8s-config"
DATE=$(date +%Y%m%d_%H%M%S)
NAMESPACE="panic-system"

# Create backup directory
mkdir -p $BACKUP_DIR

# Export all Kubernetes resources
kubectl get all,configmaps,secrets,pvc,ingress -n $NAMESPACE -o yaml > \
  "$BACKUP_DIR/k8s_resources_$DATE.yaml"

# Export cluster-wide resources
kubectl get clusterroles,clusterrolebindings,storageclasses -o yaml > \
  "$BACKUP_DIR/k8s_cluster_resources_$DATE.yaml"

# Create tar archive
tar -czf "$BACKUP_DIR/k8s_config_$DATE.tar.gz" \
  "$BACKUP_DIR/k8s_resources_$DATE.yaml" \
  "$BACKUP_DIR/k8s_cluster_resources_$DATE.yaml"

# Upload to cloud storage
aws s3 cp "$BACKUP_DIR/k8s_config_$DATE.tar.gz" \
  s3://panic-system-backups/k8s-config/daily/

# Clean up
rm "$BACKUP_DIR/k8s_resources_$DATE.yaml"
rm "$BACKUP_DIR/k8s_cluster_resources_$DATE.yaml"
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Kubernetes configuration backup completed: k8s_config_$DATE"
```

## Disaster Recovery Procedures

### 1. Database Recovery

#### Full Database Restore

```bash
#!/bin/bash
# Database restore script

BACKUP_FILE="$1"
DB_NAME="panic_system"
DB_USER="panic_system_user"
DB_HOST="postgres-service"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Download backup from S3 if needed
if [[ $BACKUP_FILE == s3://* ]]; then
    LOCAL_FILE="/tmp/$(basename $BACKUP_FILE)"
    aws s3 cp "$BACKUP_FILE" "$LOCAL_FILE"
    BACKUP_FILE="$LOCAL_FILE"
fi

# Stop application services
kubectl scale deployment panic-system-api --replicas=0 -n panic-system

# Drop and recreate database
psql -h $DB_HOST -U $DB_USER -c "DROP DATABASE IF EXISTS $DB_NAME;"
psql -h $DB_HOST -U $DB_USER -c "CREATE DATABASE $DB_NAME;"

# Restore database
pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME --verbose "$BACKUP_FILE"

# Restart application services
kubectl scale deployment panic-system-api --replicas=3 -n panic-system

echo "Database restore completed from: $BACKUP_FILE"
```

#### Point-in-Time Recovery

```bash
#!/bin/bash
# Point-in-time recovery script

TARGET_TIME="$1"
BASE_BACKUP="$2"

if [ -z "$TARGET_TIME" ] || [ -z "$BASE_BACKUP" ]; then
    echo "Usage: $0 <target_time> <base_backup>"
    echo "Example: $0 '2024-08-24 10:30:00' s3://panic-system-backups/database/daily/panic_system_20240824.dump"
    exit 1
fi

# Stop application services
kubectl scale deployment panic-system-api --replicas=0 -n panic-system

# Restore base backup
./restore-database.sh "$BASE_BACKUP"

# Apply WAL files up to target time
# (This requires WAL archiving to be configured)
pg_ctl -D /var/lib/postgresql/data recovery -t "$TARGET_TIME"

# Restart application services
kubectl scale deployment panic-system-api --replicas=3 -n panic-system

echo "Point-in-time recovery completed to: $TARGET_TIME"
```

### 2. Complete System Recovery

#### Full System Restore

```bash
#!/bin/bash
# Complete system recovery script

BACKUP_DATE="$1"

if [ -z "$BACKUP_DATE" ]; then
    echo "Usage: $0 <backup_date>"
    echo "Example: $0 20240824"
    exit 1
fi

echo "Starting complete system recovery for date: $BACKUP_DATE"

# 1. Restore Kubernetes configuration
echo "Restoring Kubernetes configuration..."
aws s3 cp "s3://panic-system-backups/k8s-config/daily/k8s_config_${BACKUP_DATE}.tar.gz" /tmp/
tar -xzf "/tmp/k8s_config_${BACKUP_DATE}.tar.gz" -C /tmp/
kubectl apply -f "/tmp/k8s_resources_${BACKUP_DATE}.yaml"

# 2. Wait for infrastructure to be ready
echo "Waiting for infrastructure to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n panic-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n panic-system --timeout=300s

# 3. Restore database
echo "Restoring database..."
./restore-database.sh "s3://panic-system-backups/database/daily/panic_system_${BACKUP_DATE}.dump"

# 4. Restore Redis data
echo "Restoring Redis data..."
kubectl exec -n panic-system deployment/redis -- redis-cli FLUSHALL
aws s3 cp "s3://panic-system-backups/redis/daily/redis_${BACKUP_DATE}.rdb" /tmp/
kubectl cp "/tmp/redis_${BACKUP_DATE}.rdb" panic-system/redis-pod:/data/dump.rdb
kubectl rollout restart deployment/redis -n panic-system

# 5. Restore file uploads
echo "Restoring file uploads..."
aws s3 sync s3://panic-system-uploads/ /tmp/uploads/
kubectl exec -n panic-system deployment/panic-system-api -- rm -rf /app/uploads/*
kubectl cp /tmp/uploads/ panic-system/api-pod:/app/uploads/

# 6. Start application services
echo "Starting application services..."
kubectl scale deployment panic-system-api --replicas=3 -n panic-system
kubectl rollout status deployment/panic-system-api -n panic-system

# 7. Verify system health
echo "Verifying system health..."
sleep 60
curl -f https://api.panicsystem.com/health || echo "Health check failed!"

echo "Complete system recovery completed for date: $BACKUP_DATE"
```

### 3. Monitoring and Alerting

#### Backup Monitoring Script

```bash
#!/bin/bash
# Backup monitoring script

BACKUP_BUCKET="panic-system-backups"
ALERT_WEBHOOK="$SLACK_WEBHOOK_URL"

# Check if daily backups exist
TODAY=$(date +%Y%m%d)
YESTERDAY=$(date -d "yesterday" +%Y%m%d)

# Check database backup
DB_BACKUP_TODAY=$(aws s3 ls s3://$BACKUP_BUCKET/database/daily/ | grep $TODAY | wc -l)
DB_BACKUP_YESTERDAY=$(aws s3 ls s3://$BACKUP_BUCKET/database/daily/ | grep $YESTERDAY | wc -l)

if [ $DB_BACKUP_TODAY -eq 0 ] && [ $DB_BACKUP_YESTERDAY -eq 0 ]; then
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 Database backup missing for the last 2 days!"}' \
        $ALERT_WEBHOOK
fi

# Check Redis backup
REDIS_BACKUP_TODAY=$(aws s3 ls s3://$BACKUP_BUCKET/redis/daily/ | grep $TODAY | wc -l)
REDIS_BACKUP_YESTERDAY=$(aws s3 ls s3://$BACKUP_BUCKET/redis/daily/ | grep $YESTERDAY | wc -l)

if [ $REDIS_BACKUP_TODAY -eq 0 ] && [ $REDIS_BACKUP_YESTERDAY -eq 0 ]; then
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 Redis backup missing for the last 2 days!"}' \
        $ALERT_WEBHOOK
fi

# Check backup sizes (detect corruption)
LATEST_DB_BACKUP=$(aws s3 ls s3://$BACKUP_BUCKET/database/daily/ | sort | tail -n 1 | awk '{print $4}')
if [ $LATEST_DB_BACKUP -lt 1000000 ]; then  # Less than 1MB
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 Database backup size is suspiciously small!"}' \
        $ALERT_WEBHOOK
fi

echo "Backup monitoring completed"
```

## Recovery Testing

### Monthly Recovery Test

```bash
#!/bin/bash
# Monthly recovery test script

TEST_NAMESPACE="panic-system-recovery-test"
BACKUP_DATE=$(date -d "7 days ago" +%Y%m%d)

echo "Starting monthly recovery test with backup from: $BACKUP_DATE"

# 1. Create test namespace
kubectl create namespace $TEST_NAMESPACE

# 2. Deploy test environment
sed "s/panic-system/$TEST_NAMESPACE/g" k8s/*.yaml | kubectl apply -f -

# 3. Restore data to test environment
./restore-database.sh "s3://panic-system-backups/database/daily/panic_system_${BACKUP_DATE}.dump"

# 4. Run basic functionality tests
kubectl run test-pod --image=curlimages/curl -n $TEST_NAMESPACE --rm -it -- \
    curl -f http://panic-system-api-service/health

# 5. Cleanup test environment
kubectl delete namespace $TEST_NAMESPACE

echo "Monthly recovery test completed successfully"
```

## Backup Retention Policy

### Retention Schedule

- **Daily Backups**: Retained for 30 days
- **Weekly Backups**: Retained for 12 weeks (3 months)
- **Monthly Backups**: Retained for 12 months (1 year)
- **Yearly Backups**: Retained for 7 years

### Automated Cleanup Script

```bash
#!/bin/bash
# Backup cleanup script

BACKUP_BUCKET="panic-system-backups"

# Clean up daily backups older than 30 days
aws s3 ls s3://$BACKUP_BUCKET/database/daily/ | \
    awk '$1 < "'$(date -d '30 days ago' '+%Y-%m-%d')'" {print $4}' | \
    xargs -I {} aws s3 rm s3://$BACKUP_BUCKET/database/daily/{}

# Clean up weekly backups older than 12 weeks
aws s3 ls s3://$BACKUP_BUCKET/database/weekly/ | \
    awk '$1 < "'$(date -d '12 weeks ago' '+%Y-%m-%d')'" {print $4}' | \
    xargs -I {} aws s3 rm s3://$BACKUP_BUCKET/database/weekly/{}

# Clean up monthly backups older than 12 months
aws s3 ls s3://$BACKUP_BUCKET/database/monthly/ | \
    awk '$1 < "'$(date -d '12 months ago' '+%Y-%m-%d')'" {print $4}' | \
    xargs -I {} aws s3 rm s3://$BACKUP_BUCKET/database/monthly/{}

echo "Backup cleanup completed"
```

## Emergency Contacts

### Escalation Matrix

| Severity | Contact | Response Time |
|----------|---------|---------------|
| Critical | On-call Engineer | 15 minutes |
| High | Team Lead | 1 hour |
| Medium | Development Team | 4 hours |
| Low | Support Team | 24 hours |

### Contact Information

- **On-call Engineer**: +1-800-PANIC-911
- **Team Lead**: lead@panicsystem.com
- **DevOps Team**: devops@panicsystem.com
- **Support Team**: support@panicsystem.com

This backup and disaster recovery plan ensures the Panic System Platform can be quickly restored in case of any system failure or data loss.