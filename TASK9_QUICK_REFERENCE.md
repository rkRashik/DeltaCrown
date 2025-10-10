# Task 9: Quick Reference Guide

## 🚀 Getting Started (5 Minutes)

### 1. Start Redis
```bash
redis-server
```

### 2. Start Celery Worker
```bash
celery -A deltacrown worker --loglevel=info --pool=solo
```

### 3. Start Celery Beat (Scheduler)
```bash
celery -A deltacrown beat --loglevel=info
```

### 4. Configure Discord (Optional)
```bash
# Add to .env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN
```

---

## 📋 Common Commands

### Management Commands
```bash
# Recompute rankings
python manage.py recompute_rankings
python manage.py recompute_rankings --tournament-id=123

# Distribute payouts
python manage.py distribute_payouts 123

# Send daily digests
python manage.py send_digests

# Cleanup old notifications
python manage.py cleanup_notifications --days=90

# Process sponsorships
python manage.py process_sponsorships
python manage.py process_sponsorships --sponsors-only
python manage.py process_sponsorships --promotions-only
```

### Celery Commands
```bash
# Check active tasks
celery -A deltacrown inspect active

# Check scheduled tasks
celery -A deltacrown inspect scheduled

# Purge all tasks
celery -A deltacrown purge

# Monitor with Flower
celery -A deltacrown flower
# Visit: http://localhost:5555
```

---

## 🔔 Notification Types

| Type | Default Channels | Description |
|------|-----------------|-------------|
| `invite_sent` | in_app, email | Team invite sent to player |
| `invite_accepted` | in_app, email | Player accepted invite |
| `roster_changed` | in_app | Team roster modified |
| `tournament_registered` | in_app, email | Team registered for tournament |
| `match_result` | in_app, email | Match result posted |
| `ranking_changed` | in_app | Team ranking updated |
| `sponsor_approved` | in_app, email | Sponsor application approved |
| `promotion_started` | in_app | Team promotion activated |
| `payout_received` | in_app, email | Tournament payout distributed |
| `achievement_earned` | in_app, email | Team earned achievement |

---

## ⏰ Scheduled Tasks

| Task | Schedule | Purpose |
|------|----------|---------|
| `recompute-rankings-daily` | 2:00 AM daily | Recalculate team rankings |
| `send-digest-emails-daily` | 8:00 AM daily | Send notification digests |
| `clean-expired-invites` | Every 6 hours | Expire old invites |
| `expire-sponsors-daily` | 3:00 AM daily | Process sponsor expiration |
| `process-scheduled-promotions` | Hourly | Activate/expire promotions |
| `check-tournament-wrapup` | Hourly at :15 | Process completed tournaments |

---

## 🐍 Python API

### Send Notification
```python
from apps.notifications.services import NotificationService

# Invite notification
NotificationService.notify_invite_sent(invite)

# Roster change
NotificationService.notify_roster_change(team, 'added', user)

# Tournament registration
NotificationService.notify_tournament_registration(tournament, team)

# Match result
NotificationService.notify_match_result(match)

# Payout
NotificationService.notify_payout_received(team, 1000, 'Tournament Win')

# Achievement
NotificationService.notify_achievement_earned(team, achievement)
```

### Trigger Tasks
```python
from apps.teams.tasks import recompute_team_rankings, distribute_tournament_payouts

# Async
result = recompute_team_rankings.delay()
result = distribute_tournament_payouts.delay(tournament_id=123)

# Sync (for testing)
result = recompute_team_rankings(tournament_id=123)
```

### Check User Preferences
```python
from apps.notifications.models import NotificationPreference

prefs = NotificationPreference.get_or_create_for_user(user)
channels = prefs.get_channels_for_type('match_result')
# Returns: ['in_app', 'email']

# Update
prefs.match_result_channels = ['in_app']
prefs.opt_out_email = False
prefs.enable_daily_digest = True
prefs.save()
```

---

## 🔧 Troubleshooting

### Tasks Not Running
```bash
# 1. Check Redis
redis-cli ping  # Should return PONG

# 2. Check worker status
celery -A deltacrown inspect active

# 3. Check Beat scheduler
celery -A deltacrown inspect scheduled

# 4. Check logs
tail -f celery-worker.log
tail -f celery-beat.log
```

### Notifications Not Sending
```python
# Check user preferences
from apps.notifications.models import NotificationPreference
prefs = NotificationPreference.objects.get(user=user)
print(prefs.get_channels_for_type('invite_sent'))

# Check opt-outs
print(prefs.opt_out_email)
print(prefs.opt_out_in_app)
print(prefs.opt_out_discord)

# Check digest settings
print(prefs.enable_daily_digest)
print(prefs.digest_time)
```

### Duplicate Payouts
```python
# Check for duplicates
from apps.economy.models import CoinTransaction
from django.db.models import Count

CoinTransaction.objects.filter(
    metadata__has_key='dedup_key'
).values('metadata__dedup_key').annotate(
    count=Count('id')
).filter(count__gt=1)
# Should be empty
```

### Discord Not Working
```bash
# 1. Check webhook URL
echo $DISCORD_WEBHOOK_URL

# 2. Test webhook manually
curl -X POST $DISCORD_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"content": "Test from DeltaCrown"}'

# 3. Check settings
python manage.py shell
>>> from django.conf import settings
>>> print(settings.DISCORD_NOTIFICATIONS_ENABLED)
>>> print(settings.DISCORD_WEBHOOK_URL)
```

---

## 📊 Monitoring

### Key Metrics
```python
# Total notifications sent today
from apps.notifications.models import Notification
from django.utils import timezone

today = timezone.now().date()
count = Notification.objects.filter(
    created_at__date=today
).count()
print(f"Notifications today: {count}")

# Pending digests
from apps.notifications.models import NotificationDigest

pending = NotificationDigest.objects.filter(
    is_sent=False
).count()
print(f"Pending digests: {pending}")

# Task success rate (via Celery)
celery -A deltacrown inspect stats
```

### Health Check Endpoints
```python
# views.py
def celery_health(request):
    from deltacrown.celery import app
    
    inspector = app.control.inspect()
    active = inspector.active()
    
    if active:
        return JsonResponse({'status': 'healthy', 'workers': len(active)})
    else:
        return JsonResponse({'status': 'unhealthy'}, status=503)
```

---

## 🎯 Testing Scenarios

### Test Tournament Payout
```python
# 1. Create tournament
tournament = Tournament.objects.create(
    name="Test Tournament",
    game="valorant",
    status="completed"
)

# 2. Create teams
team1 = Team.objects.create(name="Winners", game="valorant")
team2 = Team.objects.create(name="Runners Up", game="valorant")

# 3. Create matches with winners
# ... (create match records)

# 4. Trigger payout
from apps.teams.tasks import distribute_tournament_payouts
result = distribute_tournament_payouts(tournament.id)
print(result)

# 5. Verify
from apps.economy.models import CoinTransaction
payouts = CoinTransaction.objects.filter(
    transaction_type='tournament_payout',
    metadata__tournament_id=tournament.id
)
print(f"Payouts distributed: {payouts.count()}")
```

### Test Notification Flow
```python
# 1. Create invite
from apps.teams.models import TeamInvite

invite = TeamInvite.objects.create(
    team=team,
    inviter=captain_user,
    invitee=player_user,
    status='pending'
)
# Signal automatically sends notification

# 2. Check notification
from apps.notifications.models import Notification

notif = Notification.objects.filter(
    recipient=player_user,
    type='invite_sent'
).last()
print(notif.title)

# 3. Check email queued
from apps.notifications.tasks import send_email_notification
# Celery task should be queued
```

### Test Daily Digest
```python
# 1. Create multiple notifications
from apps.notifications.services import NotificationService

for i in range(5):
    NotificationService._send_notification_multi_channel(
        users=[user],
        notification_type='announcement',
        title=f'Test {i}',
        body=f'Message {i}',
        url='/test/'
    )

# 2. Run digest task
from apps.notifications.tasks import send_daily_digest
result = send_daily_digest()
print(result)

# 3. Verify digest created
from apps.notifications.models import NotificationDigest

digest = NotificationDigest.objects.filter(
    user=user,
    is_sent=True
).last()
print(f"Notifications in digest: {digest.notifications.count()}")
```

---

## 📁 File Locations

### Core Files
```
deltacrown/
├── celery.py              # Celery app & Beat schedule
├── __init__.py            # Celery app import
└── settings.py            # Celery & notification config

apps/teams/
├── tasks.py               # Ranking, payout tasks
├── signals.py             # Team notification signals
└── management/commands/
    ├── recompute_rankings.py
    ├── distribute_payouts.py
    └── process_sponsorships.py

apps/tournaments/
├── tasks.py               # Tournament wrap-up tasks
└── signals.py             # Tournament notification signals

apps/notifications/
├── models.py              # NotificationPreference, NotificationDigest
├── services.py            # NotificationService with 12 methods
├── tasks.py               # Email, Discord, digest tasks
└── management/commands/
    ├── send_digests.py
    └── cleanup_notifications.py

templates/notifications/email/
├── daily_digest.html
├── daily_digest.txt
├── single_notification.html
└── single_notification.txt
```

---

## 🔗 Useful Links

- **Celery Docs**: https://docs.celeryproject.org/
- **Redis Docs**: https://redis.io/docs/
- **Flower (Monitoring)**: https://flower.readthedocs.io/
- **Discord Webhooks**: https://discord.com/developers/docs/resources/webhook

---

## 📞 Support

### Check System Status
```bash
python manage.py check
```

### View Logs
```bash
# Django logs
tail -f logs/django.log

# Celery worker
tail -f logs/celery-worker.log

# Celery beat
tail -f logs/celery-beat.log
```

### Emergency Stop
```bash
# Stop all Celery workers
pkill -9 celery

# Purge all queued tasks
celery -A deltacrown purge

# Restart Redis
redis-cli shutdown
redis-server
```

---

**Quick Reference Version:** 1.0  
**Last Updated:** January 2024  
**Status:** Production Ready
