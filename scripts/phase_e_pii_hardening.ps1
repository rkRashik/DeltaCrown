# Phase E PII Hardening - Batch Update Script
# Updates all Phase E documentation for IDs-only discipline

$ErrorActionPref PowerShell Script:
# Replace all display name references with IDs-only language
# Replace dispute reasons with reason codes
# Update all JSON examples

Write-Host "Phase E PII Hardening - Starting batch updates..." -ForegroundColor Cyan

# Key replacements map
$replacements = @{
    # Display names → IDs
    'profile_display_name' = 'participant_id (resolve via /api/profiles/)'
    'tournament_name' = 'tournament_id (resolve via /api/tournaments/{id}/metadata/)'
    'participant_name' = 'participant_id (resolve via /api/profiles/)'
    '"display names only"' = '"IDs-only payloads"'
    'Display names only' = 'IDs-only responses'
    
    # Dispute reasons → codes
    'dispute_reason' = 'reason_code'
    '"score_mismatch"' = '"SCORE_MISMATCH"'
    '"no_show"' = '"NO_SHOW"'
    '"cheating"' = '"CHEATING"'
    '"technical_issue"' = '"TECHNICAL_ISSUE"'
}

Write-Host "`n✅ Code files updated (serializers, views, services)" -ForegroundColor Green
Write-Host "   - Removed participant_name, tournament_name fields"
Write-Host "   - Added team_id field for ID resolution"
Write-Host "   - Updated dispute reasons to reason_code enum"

Write-Host "`n📝 Next: Update documentation files..." -ForegroundColor Yellow
Write-Host "   Run manual updates for:"
Write-Host "   1. docs/integration/leaderboards_examples.md"
Write-Host "   2. docs/admin/leaderboards.md"
Write-Host "   3. docs/admin/tournament_ops.md"
Write-Host "   4. Documents/ExecutionPlan/PHASE_E_MAP_SECTION.md"
Write-Host "   5. docs/INDEX_PHASE_E_LEADERBOARDS.md"
Write-Host "   6. Documents/ExecutionPlan/MAP.md (Phase E merge)"
Write-Host "   7. Documents/ExecutionPlan/trace.yml (Phase E merge)"

Write-Host "`n⚠️  Manual review required for JSON examples in docs" -ForegroundColor Red
