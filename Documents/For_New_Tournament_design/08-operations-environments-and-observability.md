# 08 - Operations, Environments, and Observability

**Document Version:** 2.0  
**Last Updated:** November 2, 2025  
**Status:** Current System Documentation (Post-Refactor)

---

## Table of Contents
- [Environment Configuration](#environment-configuration)
- [Deployment Procedures](#deployment-procedures)
- [Background Tasks (Celery)](#background-tasks-celery)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Recovery](#backup-and-recovery)
- [Performance Optimization](#performance-optimization)
- [Incident Runbooks](#incident-runbooks)

---

## Environment Configuration

### Environment Types

**1. Development (Local)**
- **Purpose:** Local development and testing
- **Database:** PostgreSQL (local instance) or SQLite
- **Cache:** Redis (local) or dummy cache
- **Storage:** Local filesystem
- **Debug:** Enabled
- **Settings File:** `deltacrown/settings.py` (with `DEBUG=True`)
- **Active Apps:** All 15 apps (teams, economy, ecommerce, community, etc.)

**2. Testing (CI/CD)**
- **Purpose:** Automated testing in CI pipeline
- **Database:** PostgreSQL (test database)
- **Settings File:** `deltacrown/settings_test_pg.py`
- **Test Runner:** Custom test runner (`deltacrown/test_runner.py`)
- **Active Apps:** All 15 apps

**3. Staging (Pre-Production)**
- **Purpose:** Production-like testing environment
- **Database:** PostgreSQL (separate instance)
- **Cache:** Redis
- **Storage:** S3-compatible (separate bucket)
- **Debug:** Disabled
- **Domain:** `staging.deltacrown.gg` (hypothetical)
- **Active Apps:** All 15 apps

**4. Production**
- **Purpose:** Live system
- **Database:** PostgreSQL (production instance)
- **Cache:** Redis
- **Storage:** S3-compatible (production bucket)
- **Debug:** Disabled
- **Domain:** `deltacrown.gg` (hypothetical)
- **Active Apps:** All 15 apps

**Removed Environment Features (November 2, 2025):**
- ~~Tournament scheduling automation~~ (tournament system in legacy)
- ~~Match coordination services~~ (tournament system in legacy)
- ~~Bracket generation processes~~ (tournament system in legacy)

**Code Reference:** `deltacrown/settings.py`, `deltacrown/settings_test_pg.py`

---

### Environment Variables

**`.env` File Structure:**
```bash
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,deltacrown.gg

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=deltacrown
DB_USER=dc_user
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@deltacrown.gg
EMAIL_HOST_PASSWORD=email_password

# Storage (S3)
USE_S3=False
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=us-east-1

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# External APIs
DISCORD_WEBHOOK_URL=
RIOT_API_KEY=  # For Valorant player verification (future)
PAYPAL_CLIENT_ID=  # For ecommerce payments (future)
PAYPAL_SECRET=

# Sentry (Error Tracking)
SENTRY_DSN=

# Logging
LOG_LEVEL=INFO
```

**Loading Environment Variables:**
```python
# deltacrown/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Django settings
DEBUG = os.getenv('DEBUG', 'False') == 'True'
SECRET_KEY = os.getenv('SECRET_KEY')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE'),
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}

# Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Celery
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
```

**Code Reference:** `deltacrown/settings.py`

---

### INSTALLED_APPS Configuration (15 Active Apps)

```python
# deltacrown/settings.py (lines 43-70)
INSTALLED_APPS = [
    # Django Core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sitemaps',
    
    # Third-Party Apps
    'rest_framework',
    'corsheaders',
    'channels',
    'celery',
    
    # DeltaCrown Apps (15 Active)
    'apps.core',
    'apps.common',
    'apps.corelib',
    'apps.accounts',
    'apps.user_profile',
    'apps.teams',
    'apps.notifications',
    'apps.economy',
    'apps.ecommerce',
    'apps.siteui',  # Includes Community features (5 models)
    'apps.dashboard',
    'apps.corepages',
    'apps.players',
    'apps.search',
    'apps.support',
    
    # Legacy Apps (Commented Out - November 2, 2025)
    # 'apps.tournaments',
    # 'apps.game_valorant',
    # 'apps.game_efootball',
]
```

**Code Reference:** `deltacrown/settings.py` lines 43-70

---

### Development Setup

**Initial Setup:**
```powershell
# Clone repository
git clone https://github.com/yourusername/DeltaCrown.git
cd DeltaCrown

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with local settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Run development server
python manage.py runserver
```

**Running Tests:**
```powershell
# Run all tests
pytest

# Run specific app tests
pytest tests/test_teams.py
pytest tests/test_economy.py
pytest tests/test_ecommerce.py

# Run with coverage
pytest --cov=apps --cov-report=html

# Run Django tests (legacy)
python manage.py test
```

**Test Files (Verified in `tests/` directory):**
- `test_part4_teams.py` - Team management tests
- `test_part5_coin.py` - DeltaCoin economy tests
- `test_part10_coins_polish.py` - DeltaCoin polish tests
- `test_part3_payments.py` - Ecommerce payment tests
- `test_notifications_basic.py` - Notification system tests
- `test_notifications_service.py` - Notification service layer tests
- ~~`test_part1_tournament_core.py`~~ - Legacy (tournament in legacy_backup/)
- ~~`test_admin_tournaments_select_related.py`~~ - Legacy

**Code Reference:** `tests/` directory

---

### Running Celery (Development)

**Terminal 1: Celery Worker**
```powershell
celery -A deltacrown worker --loglevel=info --pool=solo
```

**Terminal 2: Celery Beat (Periodic Tasks)**
```powershell
celery -A deltacrown beat --loglevel=info
```

**Terminal 3: Django Development Server**
```powershell
python manage.py runserver
```

**Code Reference:** `deltacrown/celery.py`

---

## Deployment Procedures

### Pre-Deployment Checklist

**1. Code Quality:**
- [ ] All tests passing (`pytest`)
- [ ] No linting errors (`flake8 .`)
- [ ] No security vulnerabilities (`pip-audit`)
- [ ] Code reviewed and approved

**2. Database:**
- [ ] Migrations generated (`python manage.py makemigrations`)
- [ ] Migrations tested locally
- [ ] Database backup created

**3. Configuration:**
- [ ] Environment variables updated
- [ ] `DEBUG=False` in production `.env`
- [ ] `ALLOWED_HOSTS` configured
- [ ] `SECRET_KEY` rotated (if needed)

**4. Static Files:**
- [ ] `collectstatic` run successfully
- [ ] Static files uploaded to S3 (if using)

**5. Services:**
- [ ] Redis running
- [ ] PostgreSQL running
- [ ] Celery worker running
- [ ] Celery beat running

---

### Deployment Steps (Manual)

**1. Pull Latest Code:**
```bash
cd /path/to/DeltaCrown
git pull origin main
```

**2. Activate Virtual Environment:**
```bash
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\Activate.ps1  # Windows
```

**3. Install Dependencies:**
```bash
pip install -r requirements.txt
```

**4. Run Migrations:**
```bash
python manage.py migrate --noinput
```

**5. Collect Static Files:**
```bash
python manage.py collectstatic --noinput
```

**6. Restart Services:**
```bash
# Restart Gunicorn (or uWSGI)
sudo systemctl restart deltacrown-gunicorn

# Restart Celery Worker
sudo systemctl restart deltacrown-celery-worker

# Restart Celery Beat
sudo systemctl restart deltacrown-celery-beat

# Restart Channels (Daphne)
sudo systemctl restart deltacrown-daphne
```

**7. Verify Deployment:**
```bash
# Check service status
sudo systemctl status deltacrown-gunicorn
sudo systemctl status deltacrown-celery-worker
sudo systemctl status deltacrown-celery-beat
sudo systemctl status deltacrown-daphne

# Check logs
tail -f /var/log/deltacrown/gunicorn.log
tail -f /var/log/deltacrown/celery.log

# Test health endpoint (if exists)
curl https://deltacrown.gg/health/
```

---

### Zero-Downtime Deployment (Blue-Green)

**Strategy:**
1. Deploy new version to "green" environment
2. Run smoke tests on green
3. Switch traffic from "blue" to "green" (load balancer)
4. Monitor for errors
5. Keep blue as rollback option

**Implementation (Hypothetical):**
- Use load balancer (Nginx, AWS ALB)
- Two identical server environments
- Database shared between environments
- Switch traffic at load balancer level

**Rollback Procedure:**
1. Switch traffic back to blue environment (instant)
2. Investigate green environment issues
3. Fix and redeploy

---

## Background Tasks (Celery)

### Overview

DeltaCrown uses **Celery** for asynchronous task processing with **Redis** as the message broker. 

**Active Periodic Tasks:** 5  
**Legacy Periodic Tasks:** 1 (disabled)

**Code Reference:** `deltacrown/celery.py`

---

### Celery Configuration

**File:** `deltacrown/celery.py`

```python
# deltacrown/celery.py
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')

app = Celery('deltacrown')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat Schedule (Periodic Tasks)
app.conf.beat_schedule = {
    # Daily ranking recalculation at 2 AM
    'recompute-rankings-daily': {
        'task': 'apps.teams.tasks.recompute_team_rankings',
        'schedule': crontab(hour=2, minute=0),
    },
    # Daily digest emails at 8 AM
    'send-digest-emails-daily': {
        'task': 'apps.notifications.tasks.send_daily_digest',
        'schedule': crontab(hour=8, minute=0),
    },
    # Clean expired invites every 6 hours
    'clean-expired-invites': {
        'task': 'apps.teams.tasks.clean_expired_invites',
        'schedule': crontab(hour='*/6', minute=0),
    },
    # Expire sponsors daily at 3 AM
    'expire-sponsors-daily': {
        'task': 'apps.teams.tasks.expire_sponsors_task',
        'schedule': crontab(hour=3, minute=0),
    },
    # Process scheduled promotions hourly
    'process-scheduled-promotions': {
        'task': 'apps.teams.tasks.process_scheduled_promotions_task',
        'schedule': crontab(minute=0),  # Every hour
    },
    # LEGACY: Tournament wrap-up check (DISABLED)
    # 'check-tournament-wrapup': {
    #     'task': 'apps.tournaments.tasks.check_tournament_wrapup',
    #     'schedule': crontab(minute=15),
    # },
}
```

**Configuration Settings:**
```python
# Task settings
task_serializer='json',
accept_content=['json'],
result_serializer='json',
timezone='UTC',
enable_utc=True,

# Task execution settings
task_track_started=True,
task_time_limit=30 * 60,  # 30 minutes
task_soft_time_limit=25 * 60,  # 25 minutes

# Retry settings
task_acks_late=True,
task_reject_on_worker_lost=True,

# Result backend
result_expires=3600,  # 1 hour

# Worker settings
worker_prefetch_multiplier=4,
worker_max_tasks_per_child=1000,
```

**Code Reference:** `deltacrown/celery.py`

---

### Active Periodic Tasks (5)

#### 1. **Recompute Team Rankings** (`recompute-rankings-daily`)

**Schedule:** Daily at 2:00 AM  
**Task:** `apps.teams.tasks.recompute_team_rankings`  
**Purpose:** Recalculate team ranking points based on criteria

**Implementation:**
```python
# apps/teams/tasks.py
@shared_task(bind=True, name='teams.recompute_team_rankings', max_retries=3)
def recompute_team_rankings(self, tournament_id=None):
    """
    Recompute team rankings based on tournament results.
    
    NOTE: Tournament system in legacy - task now recalculates
          based on team age, activity, and other metrics.
    """
    from apps.teams.services.ranking_service import ranking_service
    
    result = ranking_service.recalculate_all_teams(
        reason="Daily automated recalculation"
    )
    
    return result
```

**Output:**
```json
{
  "status": "success",
  "teams_processed": 150,
  "teams_updated": 45
}
```

**Code Reference:** `apps/teams/tasks.py` lines 200-300 (approx)

---

#### 2. **Send Daily Digest Emails** (`send-digest-emails-daily`)

**Schedule:** Daily at 8:00 AM  
**Task:** `apps.notifications.tasks.send_daily_digest`  
**Purpose:** Send batched notification emails to users with unread notifications

**Implementation:**
```python
# apps/notifications/tasks.py
@shared_task(bind=True, name='notifications.send_daily_digest', max_retries=3)
def send_daily_digest(self):
    """
    Send daily digest emails to users with unread notifications.
    """
    from apps.notifications.models import Notification, NotificationDigest
    from apps.accounts.models import User
    
    yesterday = timezone.now() - timedelta(days=1)
    
    users_with_notifications = User.objects.filter(
        notifications__is_read=False,
        notifications__created_at__gte=yesterday
    ).distinct()
    
    sent_count = 0
    
    for user in users_with_notifications:
        prefs = NotificationPreference.get_or_create_for_user(user)
        
        if not prefs.enable_daily_digest or prefs.opt_out_email:
            continue
        
        unread_notifications = Notification.objects.filter(
            recipient=user,
            is_read=False,
            created_at__gte=yesterday
        ).order_by('-created_at')[:50]
        
        if not unread_notifications:
            continue
        
        # Send digest email
        send_digest_email(user, unread_notifications)
        sent_count += 1
    
    return {'status': 'success', 'sent_count': sent_count}
```

**Output:**
```json
{
  "status": "success",
  "sent_count": 25
}
```

**Code Reference:** `apps/notifications/tasks.py` lines 1-100 (approx)

---

#### 3. **Clean Expired Invites** (`clean-expired-invites`)

**Schedule:** Every 6 hours  
**Task:** `apps.teams.tasks.clean_expired_invites`  
**Purpose:** Mark team invites older than 7 days as expired

**Implementation:**
```python
# apps/teams/tasks.py
@shared_task(bind=True, name='teams.clean_expired_invites', max_retries=3)
def clean_expired_invites(self):
    """
    Clean up expired team invites.
    Runs every 6 hours to remove stale invitations.
    """
    from apps.teams.models import TeamInvite
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=7)
    
    expired_invites = TeamInvite.objects.filter(
        status='pending',
        created_at__lt=cutoff_date
    )
    
    count = expired_invites.count()
    expired_invites.update(status='expired')
    
    return {'status': 'success', 'expired_count': count}
```

**Output:**
```json
{
  "status": "success",
  "expired_count": 12
}
```

**Code Reference:** `apps/teams/tasks.py` lines 450-480 (approx)

---

#### 4. **Expire Sponsors** (`expire-sponsors-daily`)

**Schedule:** Daily at 3:00 AM  
**Task:** `apps.teams.tasks.expire_sponsors_task`  
**Purpose:** Expire team sponsors that have passed their end date

**Implementation:**
```python
# apps/teams/tasks.py
@shared_task(bind=True, name='teams.expire_sponsors_task', max_retries=3)
def expire_sponsors_task(self):
    """
    Expire sponsors that have passed their end date.
    Runs daily at 3 AM.
    """
    from apps.teams.services import SponsorshipService
    
    expired_count = SponsorshipService.expire_sponsors()
    
    return {'status': 'success', 'expired_count': expired_count}
```

**Output:**
```json
{
  "status": "success",
  "expired_count": 3
}
```

**Code Reference:** `apps/teams/tasks.py` lines 520-540 (approx)

---

#### 5. **Process Scheduled Promotions** (`process-scheduled-promotions`)

**Schedule:** Every hour (top of the hour)  
**Task:** `apps.teams.tasks.process_scheduled_promotions_task`  
**Purpose:** Activate scheduled promotions and expire ended promotions

**Implementation:**
```python
# apps/teams/tasks.py
@shared_task(bind=True, name='teams.process_scheduled_promotions_task', max_retries=3)
def process_scheduled_promotions_task(self):
    """
    Process scheduled promotions (activate/expire).
    Runs hourly.
    """
    from apps.teams.services import PromotionService
    
    activated_count = PromotionService.activate_scheduled_promotions()
    expired_count = PromotionService.expire_promotions()
    
    return {
        'status': 'success',
        'activated_count': activated_count,
        'expired_count': expired_count
    }
```

**Output:**
```json
{
  "status": "success",
  "activated_count": 2,
  "expired_count": 1
}
```

**Code Reference:** `apps/teams/tasks.py` lines 550-580 (approx)

---

### Legacy Periodic Task (1 - DISABLED)

#### ~~**Check Tournament Wrap-up**~~ (`check-tournament-wrapup`)

**Schedule:** ~~Every hour at :15~~ (DISABLED)  
**Task:** ~~`apps.tournaments.tasks.check_tournament_wrapup`~~  
**Status:** **Disabled (Tournament system in legacy_backup/)**

**Reason:** Tournament system moved to legacy on November 2, 2025. Task commented out in `deltacrown/celery.py` line 50.

**Code Reference:** `deltacrown/celery.py` lines 45-52 (commented out)

---

### On-Demand Tasks (Non-Periodic)

#### **Team Notification Tasks**

**1. Send Roster Change Notification:**
```python
# apps/teams/tasks.py
@shared_task(bind=True, name='teams.send_roster_change_notification')
def send_roster_change_notification(self, team_id, change_type, user_id):
    """Send notification when roster changes occur"""
    # ... implementation ...
```

**2. Send Invite Notification:**
```python
# apps/teams/tasks.py
@shared_task(bind=True, name='teams.send_invite_notification')
def send_invite_notification(self, invite_id):
    """Send notification when team invite is sent"""
    # ... implementation ...
```

#### **Notification Delivery Tasks**

**1. Send Email Notification:**
```python
# apps/notifications/tasks.py
@shared_task(bind=True, name='notifications.send_email_notification')
def send_email_notification(self, notification_id):
    """Send individual email notification"""
    # ... implementation ...
```

**2. Send Discord Notification:**
```python
# apps/notifications/tasks.py
@shared_task(bind=True, name='notifications.send_discord_notification')
def send_discord_notification(self, notification_data):
    """Send notification to Discord webhook"""
    # ... implementation ...
```

**3. Batch Send Notifications:**
```python
# apps/notifications/tasks.py
@shared_task(bind=True, name='notifications.batch_send_notifications')
def batch_send_notifications(self, user_ids, notification_type, title, body, url='', **metadata):
    """Send the same notification to multiple users in batch"""
    # ... implementation ...
```

**Code Reference:** `apps/teams/tasks.py`, `apps/notifications/tasks.py`

---

### Monitoring Celery Tasks

**1. Celery Flower (Web-based Monitoring):**
```powershell
pip install flower
celery -A deltacrown flower --port=5555
```

Access at: `http://localhost:5555`

**2. CLI Monitoring:**
```powershell
# Active workers
celery -A deltacrown inspect active

# Scheduled tasks
celery -A deltacrown inspect scheduled

# Task stats
celery -A deltacrown inspect stats
```

**3. Logs:**
```powershell
# Celery worker logs
tail -f /var/log/deltacrown/celery.log

# Celery beat logs
tail -f /var/log/deltacrown/celery-beat.log
```

---

## Monitoring and Logging

### Logging Configuration

**Django Logging Setup:**
```python
# deltacrown/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/deltacrown/django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'celery_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/deltacrown/celery.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'celery_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

---

### Logging Best Practices

**1. Use Appropriate Log Levels:**
```python
import logging
logger = logging.getLogger(__name__)

# DEBUG - Detailed diagnostic information
logger.debug(f'User {user.id} requested profile')

# INFO - General informational messages
logger.info(f'Team {team.name} created successfully')

# WARNING - Warning messages
logger.warning(f'Invite {invite.id} expired')

# ERROR - Error messages (recoverable)
logger.error(f'Failed to send email: {e}')

# CRITICAL - Critical errors (non-recoverable)
logger.critical(f'Database connection lost')
```

**2. Include Context in Logs:**
```python
# Good: Includes user ID and team name
logger.info(f'User {user.id} joined team {team.name}')

# Bad: Vague message
logger.info('User joined team')
```

**3. Log Exceptions with Traceback:**
```python
try:
    # ... operation ...
    pass
except Exception as e:
    logger.error(f'Error processing order: {e}', exc_info=True)
```

**Example from Economy Service:**
```python
# apps/economy/services.py
def award(*, profile, amount, reason, ...):
    """Award DeltaCoin to user"""
    try:
        logger.info(f'Awarding {amount} DeltaCoin to {profile.user.username} for {reason}')
        
        # ... award logic ...
        
        logger.info(f'Successfully awarded {amount} DeltaCoin (tx_id={tx.id})')
        return tx
        
    except Exception as e:
        logger.error(f'Failed to award coins: {e}', exc_info=True)
        raise
```

**Code Reference:** `deltacrown/settings.py`, `apps/economy/services.py`

---

### Application Monitoring

**Key Metrics to Monitor:**

**1. System Metrics:**
- CPU usage
- Memory usage
- Disk space
- Network I/O

**2. Application Metrics:**
- Request rate (requests/second)
- Response time (avg, p50, p95, p99)
- Error rate (5xx responses)
- Active users (sessions)

**3. Business Metrics:**
- User registrations per day
- Team creations per day
- DeltaCoin transactions per day
- Orders per day (DeltaStore)
- Community posts per day

**4. Database Metrics:**
- Query count
- Slow queries (> 500ms)
- Connection pool usage
- Database size

**5. Celery Metrics:**
- Task success rate
- Task failure rate
- Task execution time (avg)
- Queue length

**Removed Metrics (November 2, 2025):**
- ~~Tournament registrations per day~~ (tournament system in legacy)
- ~~Match completion rate~~ (tournament system in legacy)
- ~~Bracket generation time~~ (tournament system in legacy)

---

### Error Tracking (Sentry)

**Configuration:**
```python
# deltacrown/settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

if os.getenv('SENTRY_DSN'):
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions
        send_default_pii=False,  # Don't send user info
        environment=os.getenv('ENVIRONMENT', 'development'),
    )
```

**Manual Error Reporting:**
```python
from sentry_sdk import capture_exception, capture_message

try:
    # ... operation ...
    pass
except Exception as e:
    capture_exception(e)
    logger.error(f'Error: {e}')
```

**Code Reference:** `deltacrown/settings.py`

---

### Performance Monitoring

**1. Django Debug Toolbar (Development):**
```python
# deltacrown/settings.py (development only)
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']
```

**2. Query Performance:**
```python
# Log slow queries
LOGGING['loggers']['django.db.backends'] = {
    'level': 'DEBUG',
    'handlers': ['console'],
}

# Find N+1 queries
from django.db import connection
print(connection.queries)  # List all queries
```

**3. Database Indexing:**
```sql
-- Active indexes (verified)
-- Team queries
CREATE INDEX idx_team_game ON teams_team(game);
CREATE INDEX idx_team_captain ON teams_team(captain_id);
CREATE INDEX idx_team_created_at ON teams_team(created_at);

-- Economy queries
CREATE INDEX idx_wallet_profile ON economy_deltacrown_wallet(profile_id);
CREATE INDEX idx_transaction_wallet ON economy_deltacrown_transaction(wallet_id);
CREATE INDEX idx_transaction_created ON economy_deltacrown_transaction(created_at);

-- Ecommerce queries
CREATE INDEX idx_order_user ON ecommerce_order(user_id);
CREATE INDEX idx_order_status ON ecommerce_order(status);
CREATE INDEX idx_order_created ON ecommerce_order(created_at);

-- Notification queries
CREATE INDEX idx_notification_recipient ON notifications_notification(recipient_id, read_at);
CREATE INDEX idx_notification_created ON notifications_notification(created_at);

-- REMOVED: Tournament indexes (legacy)
-- CREATE INDEX idx_tournament_game ON tournaments_tournament(game);
-- CREATE INDEX idx_tournament_status ON tournaments_tournament(status);
```

**Code Reference:** Database schema (verified via Django models)

---

## Backup and Recovery

### Database Backup

**1. Automated Backup Script:**
```bash
#!/bin/bash
# backup_database.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/deltacrown"
DB_NAME="deltacrown"
DB_USER="dc_user"

# Create backup directory
mkdir -p $BACKUP_DIR

# Dump database
pg_dump -U $DB_USER -d $DB_NAME -F c -f $BACKUP_DIR/deltacrown_$DATE.dump

# Compress backup
gzip $BACKUP_DIR/deltacrown_$DATE.dump

# Delete backups older than 30 days
find $BACKUP_DIR -name "*.dump.gz" -mtime +30 -delete

echo "Backup completed: deltacrown_$DATE.dump.gz"
```

**2. Cron Schedule:**
```bash
# Daily backup at 1 AM
0 1 * * * /path/to/backup_database.sh
```

**3. Offsite Backup (S3):**
```bash
#!/bin/bash
# backup_to_s3.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/deltacrown"
S3_BUCKET="s3://deltacrown-backups"

# Run database backup
/path/to/backup_database.sh

# Upload to S3
aws s3 cp $BACKUP_DIR/deltacrown_$DATE.dump.gz $S3_BUCKET/database/
```

---

### Database Restore

**1. Restore from Backup:**
```bash
# Decompress backup
gunzip deltacrown_20250101_120000.dump.gz

# Drop existing database (CAREFUL!)
dropdb -U dc_user deltacrown

# Create new database
createdb -U dc_user deltacrown

# Restore from backup
pg_restore -U dc_user -d deltacrown deltacrown_20250101_120000.dump

# Run migrations (to apply any new migrations)
python manage.py migrate
```

**2. Partial Restore (Specific Tables):**
```bash
# Restore only specific tables
pg_restore -U dc_user -d deltacrown -t teams_team -t economy_wallet deltacrown_backup.dump
```

---

### File Storage Backup

**1. Static Files:**
- Stored in S3 (if configured)
- S3 versioning enabled (keeps all versions)
- No manual backup needed

**2. User Uploads:**
- Team logos, profile pictures, product images
- Stored in S3 or local filesystem
- Backup via S3 versioning or rsync

**3. Backup User Uploads (Local Filesystem):**
```bash
#!/bin/bash
# backup_media.sh

DATE=$(date +%Y%m%d)
MEDIA_DIR="/path/to/DeltaCrown/media"
BACKUP_DIR="/backups/deltacrown/media"

# Create backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz $MEDIA_DIR

# Delete backups older than 30 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

---

## Performance Optimization

### Database Optimization

**1. Connection Pooling:**
```python
# deltacrown/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'deltacrown',
        'USER': 'dc_user',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'connect_timeout': 10,
        },
        'CONN_MAX_AGE': 600,  # Connection pooling (10 minutes)
    }
}
```

**2. Query Optimization:**
```python
# Bad: N+1 query problem
teams = Team.objects.all()
for team in teams:
    print(team.captain.user.username)  # Additional query per team

# Good: Use select_related
teams = Team.objects.select_related('captain__user').all()
for team in teams:
    print(team.captain.user.username)  # No additional queries

# Good: Use prefetch_related (for reverse FKs)
teams = Team.objects.prefetch_related('members').all()
for team in teams:
    print(team.members.count())  # No additional queries
```

**3. Database Indexing (Already Documented Above)**

---

### Caching Strategy

**1. Redis Cache Configuration:**
```python
# deltacrown/settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'deltacrown',
        'TIMEOUT': 300,  # 5 minutes default
    }
}
```

**2. View Caching:**
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache for 15 minutes
def team_leaderboard(request):
    """Team leaderboard - cached"""
    teams = Team.objects.order_by('-total_points')[:50]
    return render(request, 'teams/leaderboard.html', {'teams': teams})
```

**3. Template Fragment Caching:**
```html
{% load cache %}

{% cache 600 team_sidebar team.id %}
  <div class="sidebar">
    <h3>{{ team.name }}</h3>
    <p>{{ team.members.count }} members</p>
    <!-- ... more content ... -->
  </div>
{% endcache %}
```

**4. Low-Level Caching:**
```python
from django.core.cache import cache

# Set cache
team_stats = calculate_team_stats(team)
cache.set(f'team_stats_{team.id}', team_stats, timeout=300)

# Get cache
team_stats = cache.get(f'team_stats_{team.id}')
if not team_stats:
    team_stats = calculate_team_stats(team)
    cache.set(f'team_stats_{team.id}', team_stats, timeout=300)
```

---

### Static File Optimization

**1. Static File Compression:**
```python
# deltacrown/settings.py
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
```

**2. CDN for Static Files:**
```python
# Use S3 + CloudFront
if USE_S3:
    AWS_S3_CUSTOM_DOMAIN = 'cdn.deltacrown.gg'
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
```

**3. Image Optimization:**
- Use WebP format for images
- Compress images before upload
- Lazy load images (JavaScript)

---

## Incident Runbooks

### Common Issues and Resolutions

#### **Issue 1: High CPU Usage**

**Symptoms:**
- Server slow to respond
- Request timeouts
- High load average

**Diagnosis:**
```bash
# Check CPU usage
top
htop

# Check Django processes
ps aux | grep gunicorn

# Check Celery workers
ps aux | grep celery
```

**Resolution:**
1. Identify high-CPU process
2. If Celery worker: check for stuck tasks
3. If Gunicorn: restart workers
4. If database: check for slow queries

```bash
# Restart Gunicorn
sudo systemctl restart deltacrown-gunicorn

# Restart Celery
sudo systemctl restart deltacrown-celery-worker
```

---

#### **Issue 2: Database Connection Errors**

**Symptoms:**
- "too many connections" error
- "connection timeout" error
- 500 errors on website

**Diagnosis:**
```bash
# Check PostgreSQL connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check connection limit
sudo -u postgres psql -c "SHOW max_connections;"
```

**Resolution:**
1. Increase `max_connections` in `postgresql.conf`
2. Enable connection pooling (pgBouncer)
3. Check for connection leaks in code

```bash
# Restart PostgreSQL
sudo systemctl restart postgresql
```

---

#### **Issue 3: Celery Worker Not Processing Tasks**

**Symptoms:**
- Tasks stuck in queue
- Notifications not sent
- Ranking not updating

**Diagnosis:**
```bash
# Check Celery worker status
sudo systemctl status deltacrown-celery-worker

# Check Celery logs
tail -f /var/log/deltacrown/celery.log

# Check Redis connection
redis-cli ping
```

**Resolution:**
```bash
# Restart Celery worker
sudo systemctl restart deltacrown-celery-worker

# Restart Celery beat
sudo systemctl restart deltacrown-celery-beat

# Purge task queue (if stuck)
celery -A deltacrown purge
```

---

#### **Issue 4: Disk Space Full**

**Symptoms:**
- "No space left on device" error
- Unable to upload files
- Database write errors

**Diagnosis:**
```bash
# Check disk space
df -h

# Find large files
du -sh /var/log/deltacrown/*
du -sh /path/to/DeltaCrown/media/*
```

**Resolution:**
1. Delete old logs
2. Clean up old database backups
3. Archive old media files

```bash
# Delete old logs (keep last 7 days)
find /var/log/deltacrown -name "*.log" -mtime +7 -delete

# Delete old backups (keep last 30 days)
find /backups/deltacrown -name "*.dump.gz" -mtime +30 -delete
```

---

#### **Issue 5: Static Files Not Loading**

**Symptoms:**
- CSS not applied
- Images not showing
- JavaScript not working

**Diagnosis:**
```bash
# Check static files location
ls -la /path/to/DeltaCrown/staticfiles

# Check Nginx configuration
sudo nginx -t
```

**Resolution:**
```bash
# Collect static files
python manage.py collectstatic --noinput

# Restart Nginx
sudo systemctl restart nginx
```

---

## Summary

### Operations Overview

| Service | Purpose | Status | Monitoring |
|---------|---------|--------|------------|
| **Gunicorn** | Django WSGI server | ✅ Active | Systemd, Logs |
| **Daphne** | Django ASGI server (WebSocket) | ✅ Active | Systemd, Logs |
| **Celery Worker** | Background task processing | ✅ Active | Flower, Logs |
| **Celery Beat** | Periodic task scheduling | ✅ Active | Logs |
| **PostgreSQL** | Database | ✅ Active | pg_stat_activity |
| **Redis** | Cache + Celery broker | ✅ Active | redis-cli |
| **Nginx** | Reverse proxy | ✅ Active | Logs |

---

### Active Celery Tasks (5 Periodic + N On-Demand)

**Periodic Tasks:**
1. **recompute-rankings-daily** - Daily at 2 AM
2. **send-digest-emails-daily** - Daily at 8 AM
3. **clean-expired-invites** - Every 6 hours
4. **expire-sponsors-daily** - Daily at 3 AM
5. **process-scheduled-promotions** - Hourly

**Legacy Tasks (Disabled):**
- ~~check-tournament-wrapup~~ - DISABLED (tournament system in legacy)

---

### Key Operational Areas

| Area | Coverage | Status |
|------|----------|--------|
| **Environment Configuration** | 4 environments (dev, test, staging, prod) | ✅ Documented |
| **Deployment Procedures** | Manual + Zero-downtime strategies | ✅ Documented |
| **Background Tasks** | 5 active + N on-demand (Celery) | ✅ Verified |
| **Monitoring** | Logs, metrics, Sentry | ✅ Configured |
| **Backup & Recovery** | Database + file storage | ✅ Documented |
| **Performance Optimization** | Caching, indexing, query optimization | ✅ Documented |
| **Incident Runbooks** | 5+ common issues | ✅ Documented |

---

**Document Status:** Complete and accurate as of November 2, 2025 post-refactor state. Documents active operations for 15 apps. Legacy tournament operations removed.
