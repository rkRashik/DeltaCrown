# Task 4 Setup Script
# Run this after completing Task 4 implementation

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Task 4: Team Dashboard & Profile Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️  Warning: Virtual environment not detected" -ForegroundColor Yellow
    Write-Host "   Please activate your virtual environment first" -ForegroundColor Yellow
    Write-Host "   Example: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y") {
        exit
    }
}

Write-Host "Step 1: Collecting static files..." -ForegroundColor Green
python manage.py collectstatic --noinput
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Static files collected successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to collect static files" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "Step 2: Running system check..." -ForegroundColor Green
python manage.py check
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ System check passed" -ForegroundColor Green
} else {
    Write-Host "✗ System check failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "Step 3: Checking migrations..." -ForegroundColor Green
python manage.py showmigrations teams | Select-String "\[ \]" -Quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "⚠️  Unapplied migrations detected" -ForegroundColor Yellow
    $runMigrations = Read-Host "Run migrations now? (Y/n)"
    if ($runMigrations -ne "n") {
        python manage.py migrate teams
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Migrations applied successfully" -ForegroundColor Green
        } else {
            Write-Host "✗ Migration failed" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "✓ All migrations applied" -ForegroundColor Green
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Task 4 Setup Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "✅ Files Created:" -ForegroundColor Green
Write-Host "   - apps/teams/views/dashboard.py (560 lines)"
Write-Host "   - templates/teams/team_dashboard.html (850 lines)"
Write-Host "   - templates/teams/team_profile.html (900 lines)"
Write-Host "   - static/teams/css/team-dashboard.css (1,200 lines)"
Write-Host "   - static/teams/css/team-profile.css (1,200 lines)"
Write-Host "   - static/teams/js/team-dashboard.js (240 lines)"
Write-Host "   - static/teams/js/team-profile.js (250 lines)"
Write-Host ""

Write-Host "📚 Documentation:" -ForegroundColor Green
Write-Host "   - TASK4_IMPLEMENTATION_COMPLETE.md"
Write-Host "   - TEAM_DASHBOARD_QUICK_REFERENCE.md"
Write-Host ""

Write-Host "🔗 New URLs Available:" -ForegroundColor Green
Write-Host "   Dashboard: /teams/<slug>/dashboard/"
Write-Host "   Profile:   /teams/<slug>/"
Write-Host "   Follow:    /teams/<slug>/follow/"
Write-Host "   Unfollow:  /teams/<slug>/unfollow/"
Write-Host ""

Write-Host "🧪 Test the Implementation:" -ForegroundColor Yellow
Write-Host "   1. Start the development server:"
Write-Host "      python manage.py runserver"
Write-Host ""
Write-Host "   2. Create or navigate to a team:"
Write-Host "      http://localhost:8000/teams/<team-slug>/"
Write-Host ""
Write-Host "   3. Access dashboard (as captain):"
Write-Host "      http://localhost:8000/teams/<team-slug>/dashboard/"
Write-Host ""
Write-Host "   4. Test features:"
Write-Host "      • Drag-and-drop roster ordering"
Write-Host "      • Toggle team settings"
Write-Host "      • Follow/unfollow team"
Write-Host "      • Browse tabs on profile"
Write-Host "      • Test on mobile (DevTools)"
Write-Host ""

Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Review TASK4_IMPLEMENTATION_COMPLETE.md for full details"
Write-Host "   2. Test dashboard and profile pages"
Write-Host "   3. Customize colors in CSS if needed"
Write-Host "   4. Add team data for testing"
Write-Host "   5. Test on mobile devices"
Write-Host ""

Write-Host "⚠️  Important Notes:" -ForegroundColor Yellow
Write-Host "   • Dashboard requires captain/manager permissions"
Write-Host "   • Profile visibility depends on is_public setting"
Write-Host "   • Follow feature requires user authentication"
Write-Host "   • Drag-and-drop works on desktop and touch devices"
Write-Host ""

Write-Host "For detailed documentation, see:" -ForegroundColor Cyan
Write-Host "   TASK4_IMPLEMENTATION_COMPLETE.md"
Write-Host ""

$startServer = Read-Host "Start development server now? (Y/n)"
if ($startServer -ne "n") {
    Write-Host ""
    Write-Host "Starting development server..." -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host ""
    python manage.py runserver
}
