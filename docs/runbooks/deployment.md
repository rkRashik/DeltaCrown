# DeltaCrown Deployment Runbook

## Overview

Operational procedures for deploying, monitoring, and maintaining the DeltaCrown backend in production.

---

## Pre-Deployment Checklist

### Code Quality
- [ ] All tests passing (`pytest`)
- [ ] No linting errors (`flake8`)
- [ ] Code formatted (`black`)
- [ ] Type hints validated (if using mypy)
- [ ] Coverage meets threshold (>80%)

### Database
- [ ] All migrations created (`python manage.py makemigrations --check`)
- [ ] Migrations tested in staging
- [ ] Backup strategy confirmed
- [ ] Rollback plan documented

### Configuration
- [ ] `.env` file configured for production
- [ ] `DEBUG=False` set
- [ ] `SECRET_KEY` rotated and secured
- [ ] `ALLOWED_HOSTS` configured
- [ ] Database credentials secured
- [ ] Redis connection string configured
- [ ] Email backend configured

### Infrastructure
- [ ] PostgreSQL running and accessible
- [ ] Redis running and accessible
- [ ] Celery workers configured
- [ ] SSL certificates valid
- [ ] Static files collected
- [ ] Media storage configured

### Monitoring
- [ ] Sentry configured (error tracking)
- [ ] Prometheus metrics enabled
- [ ] Grafana dashboards created
- [ ] Health check endpoints tested
- [ ] Alerting rules configured

---

## Deployment Procedure

### 1. Pre-Deployment Backup

```bash
# Backup database
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup media files
tar -czf media_backup_$(date +%Y%m%d_%H%M%S).tar.gz media/

# Store backups securely
aws s3 cp backup_*.sql s3://deltacrown-backups/
aws s3 cp media_backup_*.tar.gz s3://deltacrown-backups/
```

### 2. Pull Latest Code

```bash
# On production server
cd /var/www/deltacrown
git fetch origin
git checkout main
git pull origin main

# Verify version
git log -1 --oneline
```

### 3. Update Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Update packages
pip install -r requirements.txt --upgrade

# Verify installations
pip check
```

### 4. Run Database Migrations

```bash
# Check pending migrations
python manage.py showmigrations | grep "\[ \]"

# Apply migrations
python manage.py migrate

# Verify migration status
python manage.py showmigrations
```

### 5. Collect Static Files

```bash
# Collect static files
python manage.py collectstatic --noinput

# Verify static files
ls -la staticfiles/
```

### 6. Restart Services

```bash
# Restart Gunicorn (Django app)
sudo systemctl restart gunicorn

# Restart Celery workers
sudo systemctl restart celery-worker
sudo systemctl restart celery-beat

# Restart nginx (if config changed)
sudo systemctl reload nginx
```

### 7. Verify Deployment

```bash
# Check service status
sudo systemctl status gunicorn
sudo systemctl status celery-worker
sudo systemctl status celery-beat

# Check health endpoints
curl https://deltacrown.com/healthz/
curl https://deltacrown.com/readiness/

# Check logs
tail -f /var/log/deltacrown/django.log
tail -f /var/log/deltacrown/celery.log
```

### 8. Post-Deployment Tests

```bash
# Run smoke tests
pytest tests/smoke/ -v

# Check critical endpoints
curl -H "Authorization: Bearer $TOKEN" https://deltacrown.com/api/tournaments/

# Monitor error rates
# → Check Sentry dashboard
# → Check Prometheus metrics
```

---

## Rollback Procedure

### Quick Rollback (Code Only)

```bash
# Find previous commit
git log --oneline -10

# Rollback code
git checkout <previous-commit-hash>

# Restart services
sudo systemctl restart gunicorn
sudo systemctl restart celery-worker

# Verify
curl https://deltacrown.com/healthz/
```

### Full Rollback (With Database)

```bash
# Stop services
sudo systemctl stop gunicorn
sudo systemctl stop celery-worker

# Restore database
psql -h $DB_HOST -U $DB_USER -d $DB_NAME < backup_YYYYMMDD_HHMMSS.sql

# Rollback code
git checkout <previous-commit-hash>

# Rollback migrations (if needed)
python manage.py migrate app_name previous_migration_name

# Restart services
sudo systemctl start gunicorn
sudo systemctl start celery-worker

# Verify
curl https://deltacrown.com/healthz/
```

---

## Zero-Downtime Deployment (Blue-Green)

### Setup

```bash
# Two environments running simultaneously
# Blue: Current production (port 8000)
# Green: New version (port 8001)
```

### Procedure

```bash
# 1. Deploy to green environment
cd /var/www/deltacrown-green
git pull origin main
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput

# 2. Start green environment
gunicorn deltacrown.wsgi:application --bind 0.0.0.0:8001 --daemon

# 3. Verify green is healthy
curl http://localhost:8001/healthz/

# 4. Switch nginx to green
# Edit /etc/nginx/sites-available/deltacrown
# Change: proxy_pass http://localhost:8000
# To: proxy_pass http://localhost:8001

sudo nginx -t
sudo systemctl reload nginx

# 5. Monitor for 5 minutes
tail -f /var/log/nginx/access.log

# 6. If successful, stop blue environment
# If issues, revert nginx config and reload
```

---

## Monitoring & Alerting

### Health Checks

```bash
# Automated health checks (every 30s)
*/30 * * * * curl -f https://deltacrown.com/healthz/ || alert

# Readiness checks (every 1m)
* * * * * curl -f https://deltacrown.com/readiness/ || alert
```

### Metrics to Monitor

**Application Metrics**:
- HTTP request rate
- HTTP error rate (4xx, 5xx)
- Response latency (p50, p95, p99)
- WebSocket connection count
- Active tournaments count
- Registration rate

**Infrastructure Metrics**:
- CPU usage
- Memory usage
- Database connections
- Redis memory usage
- Disk I/O
- Network bandwidth

**Business Metrics**:
- User registrations per day
- Tournament creations per day
- Match completions per day
- Transaction volume

### Alert Rules (Prometheus)

```yaml
# High error rate
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m
  annotations:
    summary: "High 5xx error rate"

# Database connection issues
- alert: DatabaseDown
  expr: up{job="postgres"} == 0
  for: 1m
  annotations:
    summary: "PostgreSQL is down"

# Redis connection issues
- alert: RedisDown
  expr: up{job="redis"} == 0
  for: 1m
  annotations:
    summary: "Redis is down"

# High response latency
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
  for: 5m
  annotations:
    summary: "95th percentile latency > 2s"
```

---

## Troubleshooting Guide

### Issue: 500 Internal Server Error

**Diagnosis**:
```bash
# Check Django logs
tail -f /var/log/deltacrown/django.log

# Check Gunicorn logs
sudo journalctl -u gunicorn -n 100

# Check Sentry dashboard
```

**Common Causes**:
- Database connection failure
- Missing environment variable
- Migration not applied
- Syntax error in code

**Solution**:
```bash
# Verify database connection
python manage.py dbshell

# Check environment variables
env | grep DB_

# Verify migrations
python manage.py showmigrations

# Run Django check
python manage.py check
```

### Issue: Database Connection Timeout

**Diagnosis**:
```bash
# Check database status
sudo systemctl status postgresql

# Check connection
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1;"

# Check connection pool
python manage.py dbshell -c "SELECT count(*) FROM pg_stat_activity;"
```

**Solution**:
```bash
# Increase connection pool
# In settings.py:
DATABASES = {
    'default': {
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Restart Gunicorn
sudo systemctl restart gunicorn
```

### Issue: Celery Tasks Not Processing

**Diagnosis**:
```bash
# Check Celery worker status
sudo systemctl status celery-worker

# Check Celery logs
sudo journalctl -u celery-worker -n 100

# Check Redis connection
redis-cli ping

# List active tasks
celery -A deltacrown inspect active
```

**Solution**:
```bash
# Restart Celery workers
sudo systemctl restart celery-worker

# Purge stuck tasks (if needed)
celery -A deltacrown purge

# Check for dead workers
celery -A deltacrown inspect stats
```

### Issue: WebSocket Connections Failing

**Diagnosis**:
```bash
# Check Channels layer
python manage.py shell
>>> from channels.layers import get_channel_layer
>>> channel_layer = get_channel_layer()
>>> await channel_layer.send("test", {"type": "test.message"})

# Check Redis for channels
redis-cli keys "asgi:*"

# Check nginx WebSocket config
sudo nginx -t
```

**Solution**:
```bash
# Verify Channels configuration
# In settings.py:
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("localhost", 6379)],
        },
    },
}

# Restart services
sudo systemctl restart gunicorn
```

### Issue: High Memory Usage

**Diagnosis**:
```bash
# Check memory usage
free -h

# Check process memory
ps aux --sort=-%mem | head -10

# Check Django memory
python manage.py shell
>>> import psutil
>>> psutil.virtual_memory()
```

**Solution**:
```bash
# Reduce Gunicorn workers
# In gunicorn config:
workers = 4  # Reduce from 8

# Increase swap (if needed)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Restart Gunicorn
sudo systemctl restart gunicorn
```

---

## Maintenance Procedures

### Database Vacuum (Weekly)

```bash
# Run vacuum to reclaim space
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "VACUUM ANALYZE;"

# Check database size
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
SELECT pg_size_pretty(pg_database_size('$DB_NAME'));"
```

### Log Rotation (Daily)

```bash
# Configure logrotate
# /etc/logrotate.d/deltacrown
/var/log/deltacrown/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload gunicorn
    endscript
}
```

### Cache Cleanup (Weekly)

```bash
# Clear expired sessions
python manage.py clearsessions

# Clear expired cache keys
redis-cli FLUSHDB  # Be careful, this clears all Redis data
```

### Backup Verification (Weekly)

```bash
# Test restore in staging environment
psql -h staging-db -U postgres -d deltacrown_staging < latest_backup.sql

# Verify data integrity
python manage.py check --database default
```

---

## Performance Tuning

### Database Query Optimization

```bash
# Enable query logging
# In settings.py:
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
        }
    }
}

# Analyze slow queries
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
SELECT query, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;"

# Add indexes for slow queries
python manage.py dbshell
>>> CREATE INDEX idx_custom ON table_name (column);
```

### Redis Optimization

```bash
# Check Redis memory usage
redis-cli INFO memory

# Tune eviction policy
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Enable persistence (if needed)
redis-cli CONFIG SET save "900 1 300 10"
```

### Gunicorn Tuning

```bash
# Calculate optimal worker count
# workers = (2 * CPU_cores) + 1

# Configure worker class
# For CPU-bound: sync workers
# For I/O-bound: gevent workers

# In gunicorn config:
workers = 5
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 5
```

---

## Security Procedures

### SSL Certificate Renewal

```bash
# Renew Let's Encrypt certificate
sudo certbot renew

# Verify certificate
sudo certbot certificates

# Test SSL configuration
openssl s_client -connect deltacrown.com:443 -servername deltacrown.com
```

### Secret Key Rotation

```bash
# 1. Generate new key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 2. Update .env file
SECRET_KEY=new-secret-key-here

# 3. Restart services
sudo systemctl restart gunicorn

# 4. Verify
curl https://deltacrown.com/healthz/
```

### Database Password Rotation

```bash
# 1. Change PostgreSQL password
psql -h $DB_HOST -U postgres -c "ALTER USER deltacrown_user WITH PASSWORD 'new-password';"

# 2. Update .env file
DB_PASSWORD=new-password

# 3. Restart services
sudo systemctl restart gunicorn
sudo systemctl restart celery-worker

# 4. Verify connection
python manage.py dbshell
```

---

## Disaster Recovery

### Database Restore

```bash
# 1. Stop services
sudo systemctl stop gunicorn
sudo systemctl stop celery-worker

# 2. Drop existing database
psql -h $DB_HOST -U postgres -c "DROP DATABASE $DB_NAME;"

# 3. Create new database
psql -h $DB_HOST -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# 4. Restore from backup
psql -h $DB_HOST -U $DB_USER -d $DB_NAME < backup.sql

# 5. Run migrations (if needed)
python manage.py migrate

# 6. Restart services
sudo systemctl start gunicorn
sudo systemctl start celery-worker

# 7. Verify
curl https://deltacrown.com/healthz/
```

### Full System Restore

```bash
# 1. Provision new server
# 2. Install dependencies (Python, PostgreSQL, Redis, nginx)
# 3. Restore database from backup
# 4. Restore media files from backup
# 5. Clone repository
# 6. Configure environment variables
# 7. Run migrations
# 8. Collect static files
# 9. Start services
# 10. Update DNS (if needed)
```

---

## Contact Information

**On-Call Engineer**: [Phone/Email]  
**Database Admin**: [Phone/Email]  
**DevOps Lead**: [Phone/Email]  
**Sentry Dashboard**: [URL]  
**Grafana Dashboard**: [URL]  
**Status Page**: [URL]  

---

## Additional Resources

- **Setup Guide**: `docs/development/setup_guide.md`
- **API Documentation**: `docs/api/endpoint_catalog.md`
- **Architecture**: `docs/architecture/system_architecture.md`
- **Module Status**: `Documents/ExecutionPlan/MAP.md`

---

**Last Updated**: Module 9.6 (Backend V1 Finalization)
