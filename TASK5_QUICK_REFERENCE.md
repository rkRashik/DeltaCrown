# Task 5: Tournament & Ranking Integration - Quick Reference

## 🚀 Quick Start

### Setup Steps

```bash
# 1. Generate and apply migration
python manage.py makemigrations teams
python manage.py migrate teams

# 2. Create initial ranking criteria
python manage.py shell
>>> from apps.teams.models import RankingCriteria
>>> RankingCriteria.objects.create(is_active=True)
>>> exit()

# 3. Recalculate existing rankings
python manage.py shell
>>> from apps.teams.services.ranking_calculator import TeamRankingCalculator
>>> result = TeamRankingCalculator.recalculate_all_teams()
>>> print(f"Updated: {result['updated']} teams")
>>> exit()

# 4. Collect static files
python manage.py collectstatic --noinput

# 5. Restart server
# Ctrl+C to stop, then:
python manage.py runserver
```

---

## 📋 Common Tasks

### Captain: Register Team for Tournament

**URL:** `/teams/<team-slug>/tournaments/<tournament-slug>/register/`

**Steps:**
1. Visit tournament page
2. Click "Register Team"
3. Review roster validation
4. Enter payment reference
5. Submit registration
6. Check status at `/teams/<team-slug>/registration/<id>/`

**Validation Checks:**
- ✅ Minimum roster size met
- ✅ No pending invites (warning)
- ✅ No duplicate participation
- ✅ Captain exists
- ✅ Game matches tournament

---

### Admin: Approve Tournament Registration

**URL:** `/admin/teams/teamtournamentregistration/`

**Steps:**
1. Filter by Status = "Pending"
2. Select registrations to approve
3. Choose Action → "Approve selected registrations"
4. Click "Go"
5. System validates and approves

**Or manually:**
1. Click registration ID
2. Review roster snapshot
3. Check validation passed
4. Click "Save" with status = "approved"

---

### Admin: Verify Payment & Confirm

**Steps:**
1. Open registration in admin
2. Enter/update `payment_reference`
3. Click action: "Confirm selected registrations"
4. Or change status to "confirmed" manually
5. System marks `payment_verified = True`

---

### Admin: Lock Rosters for Tournament

**Bulk Action:**
1. Admin → Team Tournament Registrations
2. Filter: Status = "Confirmed", Roster Locked = No
3. Select all
4. Action → "Lock selected rosters"
5. Click "Go"

**Or from service:**
```python
from apps.teams.services.tournament_registration import TournamentRegistrationService
from apps.tournaments.models import Tournament

tournament = Tournament.objects.get(slug='summer-valorant')
service = TournamentRegistrationService(None, tournament)
result = service.lock_tournament_rosters()
print(f"Locked {result['locked_count']} rosters")
```

---

### Admin: Add Tournament Points for Winner

**Option 1: Create Achievement (auto-calculates)**
```python
from apps.teams.models import TeamAchievement, Team
from apps.tournaments.models import Tournament

team = Team.objects.get(slug='my-team')
tournament = Tournament.objects.get(slug='summer-valorant')

# Create achievement - ranking auto-updates if signals enabled
achievement = TeamAchievement.objects.create(
    team=team,
    tournament=tournament,
    title="Summer Valorant 2025 Champion",
    placement='WINNER',
    year=2025
)
```

**Option 2: Manual Points Addition**
```python
from apps.teams.services.ranking_calculator import TeamRankingCalculator

calculator = TeamRankingCalculator(team)
result = calculator.add_tournament_points(
    tournament=tournament,
    placement='WINNER',  # or 'RUNNER_UP', 'THIRD', 'FOURTH'
    reason="Tournament completed - manual entry"
)

print(f"Added {result['points_added']} points")
print(f"New total: {result['new_total']}")
```

---

### Admin: Manual Point Adjustment

```python
from apps.teams.models import Team
from apps.teams.services.ranking_calculator import TeamRankingCalculator

team = Team.objects.get(slug='my-team')
calculator = TeamRankingCalculator(team)

# Add bonus points
result = calculator.add_manual_adjustment(
    points=100,
    reason="Community engagement bonus",
    admin_user=request.user,
    source='manual_adjustment'
)

# Subtract points (penalty)
result = calculator.add_manual_adjustment(
    points=-50,
    reason="Code of conduct violation",
    admin_user=request.user,
    source='manual_adjustment'
)
```

---

### View Team's Ranking Breakdown

**URL:** `/teams/<team-slug>/ranking/`

**Shows:**
- Current rank and percentile
- Point breakdown by category
- Recent point changes (last 10)
- Full history timeline
- Achievement list

---

### View Global Leaderboard

**URL:** `/teams/rankings/?game=valorant&region=Bangladesh`

**Filters:**
- Game (valorant, efootball, etc.)
- Region (Bangladesh, India, etc.)
- Pagination (25 per page)

---

## 🔧 Configuration

### Ranking Criteria Values

**Edit:** Admin → Teams → Ranking Criteria

**Default Values:**
```
Tournament Participation: 50 points
Tournament Winner: 500 points
Tournament Runner-up: 300 points
Tournament Top 4: 150 points
Points per Member: 10 points
Points per Month Age: 30 points
Achievement Points: 100 points
```

**To Change:**
1. Admin → Teams → Ranking Criteria
2. Click active criteria
3. Update values
4. Save
5. Optionally trigger bulk recalculation

---

## 📊 Key URLs

| Purpose | URL Pattern | Method |
|---------|------------|--------|
| Register for Tournament | `/teams/<slug>/tournaments/<tournament_slug>/register/` | GET/POST |
| Registration Status | `/teams/<slug>/registration/<id>/` | GET |
| Cancel Registration | `/teams/<slug>/registration/<id>/cancel/` | POST |
| Team Tournaments List | `/teams/<slug>/tournaments/` | GET |
| Team Ranking Detail | `/teams/<slug>/ranking/` | GET |
| Trigger Recalculation | `/teams/<slug>/ranking/recalculate/` | POST |
| Global Leaderboard | `/teams/rankings/` | GET |
| Admin Registrations | `/admin/teams/teamtournamentregistration/` | GET |
| Admin Ranking Criteria | `/admin/teams/rankingcriteria/` | GET |

---

## 🐛 Troubleshooting

### Registration Validation Fails

**Error:** "Roster has only X players, but game requires minimum Y"

**Fix:**
1. Check team roster: `/teams/<slug>/dashboard/`
2. Add more players until minimum met
3. Accept pending invites
4. Try registration again

---

### Duplicate Participation Error

**Error:** "Player X is already registered with team Y"

**Fix:**
1. Player can only be in ONE team per tournament
2. Player must leave other team first
3. Or other team must cancel registration
4. Then retry registration

---

### Ranking Points Not Updating

**Check:**
```python
# 1. Verify active criteria exists
from apps.teams.models import RankingCriteria
criteria = RankingCriteria.objects.filter(is_active=True).first()
print(criteria)  # Should not be None

# 2. Manually trigger recalculation
from apps.teams.services.ranking_calculator import TeamRankingCalculator
calculator = TeamRankingCalculator(team)
result = calculator.update_ranking(reason="Manual fix")
print(result)
```

---

### Roster Won't Lock

**Check:**
1. Registration status must be "confirmed"
2. Payment must be verified
3. Try bulk lock action in admin
4. Or manually:
```python
registration.lock_roster()
```

---

## 📱 Frontend Integration

### Show Registration Button in Tournament Page

```django
{% load teams_tags %}

{% if request.user.is_authenticated %}
    {% get_user_teams request.user tournament.game as user_teams %}
    
    {% for team in user_teams %}
        {% if team.captain == request.user.profile %}
            <a href="{% url 'teams:tournament_register' team.slug tournament.slug %}" 
               class="btn btn-primary">
                Register {{ team.name }}
            </a>
        {% endif %}
    {% endfor %}
{% endif %}
```

---

### Show Team Rank Badge

```django
{% load teams_tags %}

<div class="team-rank-badge">
    {% get_team_rank team as rank_info %}
    
    <span class="rank-position">#{{ rank_info.rank }}</span>
    <span class="rank-points">{{ rank_info.points }} pts</span>
    <span class="rank-percentile">Top {{ rank_info.percentile }}%</span>
</div>
```

---

### Show Registration Status

```django
{% if registration %}
<div class="registration-status status-{{ registration.status }}">
    <h4>Tournament Registration</h4>
    
    <div class="status-badge">
        {{ registration.get_status_display }}
    </div>
    
    {% if registration.validation_passed %}
        <div class="validation-status success">
            ✅ Roster validation passed
        </div>
    {% else %}
        <div class="validation-status error">
            ❌ Validation errors:
            <ul>
                {% for error in registration.validation_errors %}
                <li>{{ error }}</li>
                {% endfor %}
            </ul>
        </div>
    {% endif %}
    
    {% if registration.is_roster_locked %}
        <div class="roster-lock">
            🔒 Roster locked since {{ registration.locked_at }}
        </div>
    {% endif %}
</div>
{% endif %}
```

---

## 🧪 Testing Commands

### Test Registration Flow

```python
python manage.py shell

from django.contrib.auth import get_user_model
from apps.teams.models import Team
from apps.tournaments.models import Tournament
from apps.teams.services.tournament_registration import TournamentRegistrationService

User = get_user_model()

# Get test data
team = Team.objects.filter(captain__isnull=False).first()
tournament = Tournament.objects.filter(registration_open=True).first()
captain = team.captain

# Test registration
service = TournamentRegistrationService(team, tournament)

# Check eligibility
eligibility = service.can_register()
print(f"Can register: {eligibility['allowed']}")
print(f"Reasons: {eligibility['reasons']}")

# Register
if eligibility['allowed']:
    result = service.register_team(
        captain_profile=captain,
        payment_reference="TEST123"
    )
    print(f"Success: {result['success']}")
    print(f"Registration ID: {result['registration'].id}")
```

---

### Test Ranking Calculation

```python
python manage.py shell

from apps.teams.models import Team
from apps.teams.services.ranking_calculator import TeamRankingCalculator

# Get test team
team = Team.objects.first()

# Calculate ranking
calculator = TeamRankingCalculator(team)
result = calculator.calculate_full_ranking()

# Print breakdown
print(f"\n=== {team.name} Ranking Breakdown ===")
for category, points in result['breakdown'].items():
    print(f"{category}: {points} points")
print(f"\nTotal: {result['final_total']} points")

# Update database
update_result = calculator.update_ranking(reason="Test calculation")
print(f"\nUpdated: {update_result['success']}")
print(f"Points change: {update_result['points_change']}")
```

---

### Bulk Recalculate All Rankings

```python
python manage.py shell

from apps.teams.services.ranking_calculator import TeamRankingCalculator

result = TeamRankingCalculator.recalculate_all_teams()

print(f"Processed: {result['processed']} teams")
print(f"Updated: {result['updated']} teams")
print(f"Unchanged: {result['unchanged']} teams")
print(f"Errors: {len(result['errors'])}")

if result['errors']:
    for error in result['errors']:
        print(f"Error in {error['team_name']}: {error['error']}")
```

---

## 📈 Analytics Queries

### Top 10 Teams by Points

```python
from apps.teams.models import Team

top_teams = Team.objects.filter(
    is_active=True,
    total_points__gt=0
).select_related('captain').order_by('-total_points')[:10]

for i, team in enumerate(top_teams, 1):
    print(f"{i}. {team.name} - {team.total_points} points")
```

---

### Tournament Registrations Summary

```python
from apps.teams.models import TeamTournamentRegistration
from django.db.models import Count

summary = TeamTournamentRegistration.objects.values(
    'tournament__name',
    'status'
).annotate(
    count=Count('id')
).order_by('tournament__name', 'status')

for entry in summary:
    print(f"{entry['tournament__name']}: {entry['status']} = {entry['count']}")
```

---

### Teams Needing Roster Lock

```python
from apps.teams.models import TeamTournamentRegistration

pending_locks = TeamTournamentRegistration.objects.filter(
    status='confirmed',
    is_roster_locked=False,
    tournament__status='RUNNING'
).select_related('team', 'tournament')

print(f"Teams needing roster lock: {pending_locks.count()}")
for reg in pending_locks:
    print(f"- {reg.team.name} in {reg.tournament.name}")
```

---

## 🔐 Permissions

### Required for Registration

- User must be authenticated
- User must be team captain
- Team must meet minimum roster requirements
- Tournament registration must be open

### Required for Admin Actions

- User must have `staff` or `superuser` status
- Specific permissions:
  - `teams.change_teamtournamentregistration` - Approve/reject
  - `teams.can_verify_payment` - Verify payments (custom)
  - `teams.can_unlock_roster` - Emergency unlock (custom)

---

## 📞 Support

**Common Questions:**

**Q: Can I register multiple teams for same tournament?**
A: Yes, if you're captain of multiple teams for that game.

**Q: Can same player be in two teams for same tournament?**
A: No, system prevents duplicate participation.

**Q: Can I change roster after registration?**
A: Only if roster is not locked. Once tournament starts, roster locks automatically.

**Q: How are ranking points calculated?**
A: Based on tournament performance, team size, team age, and achievements. See `/teams/<slug>/ranking/` for breakdown.

**Q: Can admin manually adjust points?**
A: Yes, admins can add/subtract points with reason via `TeamRankingCalculator.add_manual_adjustment()`.

---

*Quick Reference Guide for Task 5 - Tournament & Ranking Integration*
