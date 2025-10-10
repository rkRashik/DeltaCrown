# Task 5 Setup Script - Tournament & Ranking Integration
# Run this script to set up the tournament integration and ranking system

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Task 5: Tournament & Ranking Integration" -ForegroundColor Cyan
Write-Host "Setup Script" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️  Warning: No virtual environment detected!" -ForegroundColor Yellow
    Write-Host "Please activate your virtual environment first.`n" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') {
        exit
    }
}

Write-Host "`n1️⃣  Checking Django Installation..." -ForegroundColor Green
python -c "import django; print(f'Django version: {django.get_version()}')" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Django not found! Please install Django first." -ForegroundColor Red
    exit 1
}

Write-Host "`n2️⃣  Generating Database Migration..." -ForegroundColor Green
python manage.py makemigrations teams
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Migration generation failed!" -ForegroundColor Red
    Write-Host "Check for model syntax errors in apps/teams/models/" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n3️⃣  Applying Database Migration..." -ForegroundColor Green
python manage.py migrate teams
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Migration failed!" -ForegroundColor Red
    Write-Host "Check database connection and migration dependencies" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n4️⃣  Running Django System Check..." -ForegroundColor Green
python manage.py check
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ System check found issues!" -ForegroundColor Red
    Write-Host "Please fix the issues above before continuing" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n5️⃣  Creating Initial Ranking Criteria..." -ForegroundColor Green
python -c @"
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.teams.models import RankingCriteria

# Check if criteria already exists
if RankingCriteria.objects.filter(is_active=True).exists():
    print('✅ Active ranking criteria already exists')
else:
    criteria = RankingCriteria.objects.create(
        tournament_participation=50,
        tournament_winner=500,
        tournament_runner_up=300,
        tournament_top_4=150,
        points_per_member=10,
        points_per_month_age=30,
        achievement_points=100,
        is_active=True
    )
    print(f'✅ Created ranking criteria with ID: {criteria.id}')
"@ 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Ranking criteria initialized" -ForegroundColor Green
} else {
    Write-Host "⚠️  Could not create ranking criteria (may already exist)" -ForegroundColor Yellow
}

Write-Host "`n6️⃣  Recalculating Existing Team Rankings..." -ForegroundColor Green
$recalc = Read-Host "Do you want to recalculate rankings for existing teams? (y/n)"
if ($recalc -eq 'y') {
    python -c @"
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.teams.services.ranking_calculator import TeamRankingCalculator

print('Recalculating rankings for all teams...')
result = TeamRankingCalculator.recalculate_all_teams()

print(f'\n=== Recalculation Results ===')
print(f'Processed: {result["processed"]} teams')
print(f'Updated: {result["updated"]} teams')
print(f'Unchanged: {result["unchanged"]} teams')
print(f'Errors: {len(result["errors"])}')

if result['errors']:
    print('\nErrors:')
    for error in result['errors']:
        print(f'  - {error["team_name"]}: {error["error"]}')
else:
    print('\n✅ All teams recalculated successfully!')
"@ 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Rankings recalculated" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Recalculation encountered issues" -ForegroundColor Yellow
    }
}

Write-Host "`n7️⃣  Collecting Static Files..." -ForegroundColor Green
$collectStatic = Read-Host "Run collectstatic? (y/n)"
if ($collectStatic -eq 'y') {
    python manage.py collectstatic --noinput
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Static files collected" -ForegroundColor Green
    } else {
        Write-Host "⚠️  collectstatic had issues (may not be configured)" -ForegroundColor Yellow
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "📁 Files Created:" -ForegroundColor Cyan
Write-Host "  Backend Models:" -ForegroundColor White
Write-Host "    - apps/teams/models/tournament_integration.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  Services:" -ForegroundColor White
Write-Host "    - apps/teams/services/ranking_calculator.py" -ForegroundColor Gray
Write-Host "    - apps/teams/services/tournament_registration.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  Views:" -ForegroundColor White
Write-Host "    - apps/teams/views/tournaments.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  Admin:" -ForegroundColor White
Write-Host "    - apps/teams/admin/tournament_integration.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  Documentation:" -ForegroundColor White
Write-Host "    - TASK5_IMPLEMENTATION_COMPLETE.md" -ForegroundColor Gray
Write-Host "    - TASK5_QUICK_REFERENCE.md" -ForegroundColor Gray

Write-Host "`n📚 Documentation:" -ForegroundColor Cyan
Write-Host "  Full Guide: TASK5_IMPLEMENTATION_COMPLETE.md" -ForegroundColor White
Write-Host "  Quick Ref:  TASK5_QUICK_REFERENCE.md" -ForegroundColor White

Write-Host "`n🔗 New URLs Available:" -ForegroundColor Cyan
Write-Host "  Tournament Registration:" -ForegroundColor White
Write-Host "    /teams/<slug>/tournaments/<tournament-slug>/register/" -ForegroundColor Gray
Write-Host ""
Write-Host "  Registration Status:" -ForegroundColor White
Write-Host "    /teams/<slug>/registration/<id>/" -ForegroundColor Gray
Write-Host ""
Write-Host "  Team Tournaments List:" -ForegroundColor White
Write-Host "    /teams/<slug>/tournaments/" -ForegroundColor Gray
Write-Host ""
Write-Host "  Ranking Leaderboard:" -ForegroundColor White
Write-Host "    /teams/rankings/?game=valorant" -ForegroundColor Gray
Write-Host ""
Write-Host "  Team Ranking Detail:" -ForegroundColor White
Write-Host "    /teams/<slug>/ranking/" -ForegroundColor Gray
Write-Host ""
Write-Host "  Admin Interface:" -ForegroundColor White
Write-Host "    /admin/teams/teamtournamentregistration/" -ForegroundColor Gray
Write-Host "    /admin/teams/rankingcriteria/" -ForegroundColor Gray

Write-Host "`n🧪 Testing:" -ForegroundColor Cyan
Write-Host "  To test the system, run:" -ForegroundColor White
Write-Host "    python manage.py shell" -ForegroundColor Gray
Write-Host ""
Write-Host "  Then try:" -ForegroundColor White
Write-Host @"
    from apps.teams.models import Team
    from apps.teams.services.ranking_calculator import TeamRankingCalculator
    
    team = Team.objects.first()
    calculator = TeamRankingCalculator(team)
    result = calculator.calculate_full_ranking()
    print(result)
"@ -ForegroundColor Gray

Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Configure ranking point values in Admin" -ForegroundColor White
Write-Host "     → /admin/teams/rankingcriteria/" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Test tournament registration flow" -ForegroundColor White
Write-Host "     → Captain registers team for tournament" -ForegroundColor Gray
Write-Host "     → Admin approves registration" -ForegroundColor Gray
Write-Host "     → Admin verifies payment" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Add tournament results and check ranking updates" -ForegroundColor White
Write-Host "     → Create TeamAchievement with tournament" -ForegroundColor Gray
Write-Host "     → Verify points automatically update" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. View leaderboard and ranking breakdowns" -ForegroundColor White
Write-Host "     → /teams/rankings/" -ForegroundColor Gray

Write-Host "`n⚠️  Important Notes:" -ForegroundColor Yellow
Write-Host "  • Only team captains can register for tournaments" -ForegroundColor White
Write-Host "  • Roster validation runs automatically on registration" -ForegroundColor White
Write-Host "  • Rosters lock automatically when tournament starts" -ForegroundColor White
Write-Host "  • Rankings recalculate automatically on achievement add" -ForegroundColor White
Write-Host "  • Admin can manually adjust points with audit trail" -ForegroundColor White

Write-Host "`n🚀 Ready to start development server?" -ForegroundColor Cyan
$startServer = Read-Host "Start server now? (y/n)"
if ($startServer -eq 'y') {
    Write-Host "`nStarting development server..." -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow
    python manage.py runserver
} else {
    Write-Host "`nTo start the server manually, run:" -ForegroundColor White
    Write-Host "  python manage.py runserver`n" -ForegroundColor Gray
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Task 5 Setup Complete! 🎉" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan
