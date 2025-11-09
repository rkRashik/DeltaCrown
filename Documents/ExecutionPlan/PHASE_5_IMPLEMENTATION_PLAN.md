# Phase 5: Tournament Post-Game - Implementation Plan

**Status:** 📋 PLANNED  
**Start Date:** TBD (after Phase 4 close-out)  
**Estimated Duration:** 2-3 weeks  
**Prerequisites:** Phase 4 complete ✅

---

## Executive Summary

Phase 5 handles the tournament lifecycle after matches are complete: winner determination, prize payouts, certificate generation, and analytics reporting. This phase closes the tournament loop and provides participants with outcomes, rewards, and achievements.

**Key Objectives:**
- Automatically determine tournament winners based on bracket results
- Process prize payouts to winners (integration with `apps.economy`)
- Generate achievement certificates (PDF/image) for winners and participants
- Provide tournament analytics and reports for organizers and participants

**Modules:** 4 (5.1-5.4)  
**Estimated Effort:** ~80 hours  
**Test Coverage Target:** ≥85%

---

## Table of Contents

1. [Module 5.1: Winner Determination & Verification](#module-51-winner-determination--verification)
2. [Module 5.2: Prize Payouts & Reconciliation](#module-52-prize-payouts--reconciliation)
3. [Module 5.3: Certificates & Achievement Proofs](#module-53-certificates--achievement-proofs)
4. [Module 5.4: Analytics & Reports](#module-54-analytics--reports)
5. [Dependencies & Prerequisites](#dependencies--prerequisites)
6. [Success Criteria](#success-criteria)
7. [Risks & Mitigation](#risks--mitigation)

---

## Module 5.1: Winner Determination & Verification

### Scope

Implement automated winner determination logic when all tournament matches are complete. Handle bracket resolution, tie-breaking rules, and audit logging.

### Objectives

1. **Bracket Resolution:**
   - Detect when tournament is complete (all matches in `COMPLETED` state)
   - Traverse bracket tree to determine final winner
   - Handle edge cases: forfeit chains, incomplete brackets

2. **Tie-Breaking Rules:**
   - Default: Highest bracket position wins
   - Custom rules (configurable per tournament):
     - Head-to-head record
     - Total score differential
     - Match completion time
     - Manual organizer decision

3. **Verification & Audit:**
   - Audit trail for winner determination
   - Organizer review step (optional, configurable)
   - Winner confirmation workflow
   - Dispute resolution integration (from Module 4.4)

### API Endpoints

No new public APIs (internal service method only):

**Internal Service:**
```python
# apps/tournaments/services/winner_service.py
class WinnerDeterminationService:
    def determine_winner(self, tournament_id: int) -> Optional[int]:
        """
        Determine tournament winner based on bracket results.
        Returns winner participant ID or None if incomplete.
        """
        
    def verify_tournament_completion(self, tournament_id: int) -> bool:
        """Check if all matches are complete and bracket is resolved."""
        
    def apply_tiebreaker_rules(
        self, 
        tournament_id: int, 
        tied_participants: List[int]
    ) -> int:
        """Apply configured tie-breaking rules to determine winner."""
        
    def create_audit_log(
        self, 
        tournament_id: int, 
        winner_id: int, 
        reasoning: str
    ) -> None:
        """Log winner determination reasoning for audit trail."""
```

**WebSocket Event:**
```python
# Event: tournament_completed
{
    "type": "tournament_completed",
    "data": {
        "tournament_id": 123,
        "winner_participant_id": 456,
        "winner_name": "Team Phoenix",
        "bracket_id": 789,
        "determined_at": "2025-11-09T15:30:00Z",
        "requires_organizer_review": false
    }
}
```

### Database Schema

**New Model: TournamentResult**

```python
# apps/tournaments/models/result.py
class TournamentResult(TimestampedModel, SoftDeleteModel):
    """Final tournament results and winner determination."""
    
    tournament = models.OneToOneField(
        'Tournament', 
        on_delete=models.CASCADE,
        related_name='result'
    )
    winner_participant = models.ForeignKey(
        'Registration',
        on_delete=models.PROTECT,
        related_name='won_tournaments'
    )
    final_bracket = models.ForeignKey(
        'Bracket',
        on_delete=models.SET_NULL,
        null=True
    )
    
    # Placement
    runner_up_participant = models.ForeignKey(
        'Registration',
        on_delete=models.PROTECT,
        related_name='runner_up_tournaments',
        null=True
    )
    third_place_participant = models.ForeignKey(
        'Registration',
        on_delete=models.PROTECT,
        related_name='third_place_tournaments',
        null=True
    )
    
    # Metadata
    determined_at = models.DateTimeField(auto_now_add=True)
    determination_method = models.CharField(
        max_length=50,
        choices=[
            ('bracket_resolution', 'Bracket Resolution'),
            ('manual_selection', 'Manual Organizer Selection'),
            ('tiebreaker', 'Tie-Breaking Rules'),
            ('forfeit_default', 'Forfeit/Default Win'),
        ]
    )
    reasoning = models.TextField(
        help_text="Explanation of how winner was determined"
    )
    
    # Verification
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='verified_tournament_results'
    )
    verified_at = models.DateTimeField(null=True)
    
    class Meta:
        db_table = 'tournament_engine_result_tournamentresult'
        verbose_name = 'Tournament Result'
        ordering = ['-determined_at']
```

### Testing Requirements

- **Unit Tests** (15 tests):
  - Winner determination for complete brackets (4 tests)
  - Incomplete bracket handling (3 tests)
  - Tie-breaking logic (3 tests)
  - Audit log creation (2 tests)
  - Edge cases: forfeit chains, bye matches (3 tests)

- **Integration Tests** (8 tests):
  - End-to-end winner determination (2 tests)
  - WebSocket event broadcasting (2 tests)
  - Organizer review workflow (2 tests)
  - Dispute resolution integration (2 tests)

- **Target Coverage:** ≥85%

### Dependencies

- ✅ Module 4.1 (Bracket Generation)
- ✅ Module 4.3 (Match Management)
- ✅ Module 4.4 (Result Submission)
- Phase 4 completion

### Success Criteria

- [ ] Winner automatically determined for complete tournaments
- [ ] Organizer can manually override winner (with audit log)
- [ ] Tie-breaking rules configurable per tournament
- [ ] WebSocket event broadcasts winner determination
- [ ] Audit trail persists for all winner selections
- [ ] Integration tests cover end-to-end flow
- [ ] ≥85% test coverage

### Estimated Effort

**~24 hours**  
- Service layer: 8 hours
- Database models: 4 hours
- Admin integration: 3 hours
- Testing: 6 hours
- Documentation: 3 hours

---

## Module 5.2: Prize Payouts & Reconciliation

### Scope

Integrate with `apps.economy` to automatically distribute prize pool to winners based on tournament configuration. Handle refunds for cancelled tournaments.

### Objectives

1. **Prize Distribution:**
   - Read `prize_pool` and `prize_distribution` (JSONB) from Tournament model
   - Calculate payout amounts for 1st/2nd/3rd place (or custom distribution)
   - Create `CoinTransaction` records in `apps.economy` for each winner
   - Handle partial payouts (e.g., runner-up, participation rewards)

2. **Reconciliation:**
   - Verify total payouts don't exceed prize pool
   - Audit trail for all prize transactions
   - Handle rounding errors (remainder goes to 1st place)
   - Refund entry fees for cancelled tournaments

3. **Payment Methods:**
   - Delta Coins (primary, via `apps.economy`)
   - External payouts (manual, tracked but not processed)
   - Mixed mode (coins + external prizes)

### API Endpoints

**Internal Service Only:**

```python
# apps/tournaments/services/payout_service.py
class PayoutService:
    def calculate_prize_distribution(
        self, 
        tournament_id: int
    ) -> Dict[str, Decimal]:
        """
        Calculate prize amounts based on prize_distribution JSONB.
        Returns: {"1st": Decimal("500.00"), "2nd": Decimal("300.00"), ...}
        """
        
    def process_payouts(self, tournament_id: int) -> List[int]:
        """
        Create CoinTransaction records for all winners.
        Returns list of transaction IDs.
        """
        
    def process_refunds(self, tournament_id: int) -> List[int]:
        """Refund entry fees for cancelled tournament."""
        
    def verify_payout_reconciliation(self, tournament_id: int) -> bool:
        """Verify total payouts == prize pool."""
```

### Database Schema

**New Model: PrizeTransaction**

```python
# apps/tournaments/models/prize.py
class PrizeTransaction(TimestampedModel):
    """Audit trail for prize payouts."""
    
    tournament = models.ForeignKey(
        'Tournament',
        on_delete=models.CASCADE,
        related_name='prize_transactions'
    )
    participant = models.ForeignKey(
        'Registration',
        on_delete=models.PROTECT,
        related_name='prize_transactions'
    )
    placement = models.CharField(
        max_length=20,
        choices=[
            ('1st', '1st Place'),
            ('2nd', '2nd Place'),
            ('3rd', '3rd Place'),
            ('participation', 'Participation Reward'),
        ]
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Economy integration
    coin_transaction = models.ForeignKey(
        'economy.CoinTransaction',
        on_delete=models.SET_NULL,
        null=True,
        related_name='prize_payouts'
    )
    
    # Metadata
    processed_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],
        default='pending'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'tournament_engine_prize_prizetransaction'
        verbose_name = 'Prize Transaction'
        ordering = ['-processed_at']
        indexes = [
            models.Index(fields=['tournament', 'status']),
            models.Index(fields=['participant']),
        ]
```

### Testing Requirements

- **Unit Tests** (12 tests):
  - Prize distribution calculation (3 tests)
  - Payout amount rounding (2 tests)
  - Refund calculation (2 tests)
  - Reconciliation verification (2 tests)
  - Edge cases: zero prize pool, single winner (3 tests)

- **Integration Tests** (6 tests):
  - End-to-end payout processing (2 tests)
  - `apps.economy` integration (2 tests)
  - Refund workflow (1 test)
  - WebSocket notification (1 test)

- **Target Coverage:** ≥85%

### Dependencies

- ✅ Module 5.1 (Winner Determination)
- ✅ `apps.economy` (CoinTransaction model)
- ✅ Module 3.2 (Payment Processing)

### Success Criteria

- [ ] Winners automatically receive prize coins
- [ ] Prize distribution matches tournament configuration
- [ ] Total payouts never exceed prize pool
- [ ] Refunds processed for cancelled tournaments
- [ ] Audit trail for all transactions
- [ ] Integration with `apps.economy` works
- [ ] ≥85% test coverage

### Estimated Effort

**~20 hours**  
- Service layer: 6 hours
- Database models: 3 hours
- `apps.economy` integration: 5 hours
- Testing: 4 hours
- Documentation: 2 hours

---

## Module 5.3: Certificates & Achievement Proofs

### Scope

Generate PDF/image certificates for tournament winners and participants. Provide download endpoint and verification system.

### Objectives

1. **Certificate Generation:**
   - PDF generation using ReportLab or WeasyPrint
   - Image generation using Pillow (PNG/JPEG)
   - Templates: Winner, Runner-up, Participant
   - Dynamic fields: Name, tournament, date, placement, verification code

2. **Template System:**
   - HTML/CSS templates for certificates
   - Support for custom tournament branding (logo, colors)
   - Responsive design (A4, Letter, 1920x1080px image)
   - Multi-language support (Bengali, English)

3. **Verification System:**
   - Unique verification code for each certificate (UUID)
   - Public verification endpoint: `/certificates/verify/<code>/`
   - QR code on certificate links to verification page
   - Tamper-proof: certificate hash stored in database

### API Endpoints

```python
# GET /api/tournaments/certificates/<id>/
# Download certificate PDF/image
# Permission: IsParticipant (can only download own certificates)

# GET /api/tournaments/certificates/verify/<uuid:code>/
# Verify certificate authenticity
# Permission: AllowAny (public)
```

### Database Schema

**New Model: Certificate**

```python
# apps/tournaments/models/certificate.py
class Certificate(TimestampedModel):
    """Tournament achievement certificates."""
    
    tournament = models.ForeignKey(
        'Tournament',
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    participant = models.ForeignKey(
        'Registration',
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    
    # Certificate details
    certificate_type = models.CharField(
        max_length=20,
        choices=[
            ('winner', 'Winner Certificate'),
            ('runner_up', 'Runner-up Certificate'),
            ('third_place', 'Third Place Certificate'),
            ('participant', 'Participation Certificate'),
        ]
    )
    placement = models.CharField(max_length=20, blank=True)
    
    # File storage
    file_pdf = models.FileField(
        upload_to='certificates/pdf/%Y/%m/',
        null=True,
        blank=True
    )
    file_image = models.ImageField(
        upload_to='certificates/images/%Y/%m/',
        null=True,
        blank=True
    )
    
    # Verification
    verification_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True
    )
    certificate_hash = models.CharField(
        max_length=64,
        help_text="SHA256 hash for tamper detection"
    )
    
    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    downloaded_at = models.DateTimeField(null=True)
    download_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'tournament_engine_certificate_certificate'
        verbose_name = 'Certificate'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['tournament', 'certificate_type']),
            models.Index(fields=['participant']),
        ]
```

### Testing Requirements

- **Unit Tests** (10 tests):
  - Certificate generation (PDF + image) (2 tests)
  - Template rendering (2 tests)
  - Verification code uniqueness (1 test)
  - Hash calculation (1 test)
  - Download counter increment (1 test)
  - Edge cases: missing participant name, long tournament title (3 tests)

- **Integration Tests** (5 tests):
  - End-to-end certificate generation (1 test)
  - Download endpoint (1 test)
  - Verification endpoint (1 test)
  - QR code generation (1 test)
  - Tamper detection (1 test)

- **Target Coverage:** ≥85%

### Dependencies

- ✅ Module 5.1 (Winner Determination)
- ✅ Module 5.2 (Prize Payouts) - certificates generated after payouts
- Python libraries: `reportlab` or `weasyprint`, `Pillow`, `qrcode`

### Success Criteria

- [ ] Certificates auto-generate for all winners/participants
- [ ] PDF and image formats supported
- [ ] Verification system works (public endpoint)
- [ ] QR code on certificate links to verification
- [ ] Tamper detection via hash comparison
- [ ] Download counter tracks usage
- [ ] Multi-language support (Bengali, English)
- [ ] ≥85% test coverage

### Estimated Effort

**~24 hours**  
- PDF generation (ReportLab/WeasyPrint): 8 hours
- Template design: 4 hours
- Verification system: 4 hours
- QR code integration: 2 hours
- Testing: 4 hours
- Documentation: 2 hours

---

## Module 5.4: Analytics & Reports

### Scope

Provide comprehensive analytics and reports for tournament organizers and participants. Dashboard visualizations and CSV exports.

### Objectives

1. **Organizer Analytics:**
   - Tournament summary: Participants, matches, completion rate
   - Revenue breakdown: Entry fees, prize pool, platform cut
   - Participation trends: Registration timeline, check-in rate
   - Match statistics: Average duration, dispute rate
   - Player demographics: Games, regions, skill levels

2. **Participant Reports:**
   - Personal tournament history
   - Win/loss record
   - Placement statistics (1st/2nd/3rd)
   - Prize winnings (total, by game, by tournament type)
   - Match performance: Average score, best win, worst loss

3. **Data Exports:**
   - CSV exports for all analytics
   - API endpoints for programmatic access
   - Scheduled reports (weekly organizer digest)

### API Endpoints

```python
# GET /api/tournaments/analytics/organizer/<tournament_id>/
# Organizer analytics for specific tournament
# Permission: IsOrganizerOrAdmin

# GET /api/tournaments/analytics/participant/<user_id>/
# Participant analytics across all tournaments
# Permission: IsSelfOrAdmin

# GET /api/tournaments/analytics/export/<tournament_id>/?format=csv
# Export tournament data as CSV
# Permission: IsOrganizerOrAdmin
```

### Database Schema

**No new models** (use existing data + aggregations)

**Denormalized Views** (optional, for performance):

```sql
-- Materialized view for participant statistics
CREATE MATERIALIZED VIEW tournament_participant_stats AS
SELECT 
    r.user_id,
    COUNT(DISTINCT r.tournament_id) AS total_tournaments,
    COUNT(CASE WHEN tr.winner_participant_id = r.id THEN 1 END) AS wins,
    COUNT(CASE WHEN tr.runner_up_participant_id = r.id THEN 1 END) AS runner_ups,
    SUM(pt.amount) AS total_prize_winnings,
    AVG(CASE WHEN m.winner_id = r.id THEN 1 ELSE 0 END) AS win_rate
FROM tournament_engine_registration_registration r
LEFT JOIN tournament_engine_result_tournamentresult tr 
    ON r.tournament_id = tr.tournament_id
LEFT JOIN tournament_engine_prize_prizetransaction pt 
    ON r.id = pt.participant_id
LEFT JOIN tournament_engine_match_match m 
    ON r.id IN (m.participant_1_id, m.participant_2_id)
GROUP BY r.user_id;

-- Refresh materialized view nightly (Celery task)
```

### Testing Requirements

- **Unit Tests** (8 tests):
  - Analytics calculation (3 tests)
  - CSV export formatting (2 tests)
  - Permission checks (2 tests)
  - Edge case: no tournaments (1 test)

- **Integration Tests** (4 tests):
  - End-to-end analytics retrieval (1 test)
  - CSV export (1 test)
  - Materialized view refresh (1 test)
  - Dashboard API integration (1 test)

- **Target Coverage:** ≥80%

### Dependencies

- ✅ All Phase 4 modules (data sources)
- ✅ Module 5.1 (Winner Determination)
- ✅ Module 5.2 (Prize Payouts)

### Success Criteria

- [ ] Organizer dashboard shows key tournament KPIs
- [ ] Participant dashboard shows personal statistics
- [ ] CSV exports work for all data tables
- [ ] Analytics API endpoints performant (<500ms)
- [ ] Materialized views refresh nightly
- [ ] Data accurate and up-to-date
- [ ] ≥80% test coverage

### Estimated Effort

**~16 hours**  
- Analytics service: 6 hours
- CSV export: 3 hours
- Materialized views: 3 hours
- Testing: 3 hours
- Documentation: 1 hour

---

## Dependencies & Prerequisites

### Technical Dependencies

| Dependency | Required By | Status |
|------------|-------------|--------|
| Phase 4 complete | All modules | ✅ Complete |
| `apps.economy` | Module 5.2 | ✅ Exists |
| `reportlab` / `weasyprint` | Module 5.3 | ⚠️ Need to install |
| `Pillow` | Module 5.3 | ⚠️ Need to install |
| `qrcode` | Module 5.3 | ⚠️ Need to install |

### Planning Documents

- ✅ PART_3.1_DATABASE_DESIGN_ERD.md (prize_pool, prize_distribution fields)
- ✅ PART_2.2_SERVICES_INTEGRATION.md (service layer patterns)
- ✅ PART_5.1_IMPLEMENTATION_ROADMAP_SPRINT_PLANNING.md (certificate generation tasks)
- ✅ 00_MASTER_EXECUTION_PLAN.md (Phase 5 module definitions)

### Data Requirements

- ✅ `Tournament.prize_pool` (Decimal field)
- ✅ `Tournament.prize_distribution` (JSONB field)
- ✅ `Tournament.status` = 'COMPLETED' trigger for winner determination
- ✅ `Match.state` = 'COMPLETED' for all matches in bracket

---

## Success Criteria

### Phase 5 Completion Checklist

**Functional:**
- [ ] Winners automatically determined for complete tournaments
- [ ] Prize payouts processed to `apps.economy`
- [ ] Certificates generated and downloadable
- [ ] Analytics dashboards functional
- [ ] CSV exports work for all data

**Quality:**
- [ ] ≥85% test coverage for Modules 5.1-5.3
- [ ] ≥80% test coverage for Module 5.4
- [ ] Zero P0/P1 bugs
- [ ] <5 P2 bugs
- [ ] All tests passing (100% pass rate)

**Documentation:**
- [ ] API documentation complete (all endpoints)
- [ ] Certificate template guide (for customization)
- [ ] Analytics schema documented
- [ ] Deployment runbook updated

**Integration:**
- [ ] `apps.economy` integration tested end-to-end
- [ ] WebSocket events for all Phase 5 actions
- [ ] Admin UI for manual overrides
- [ ] Audit trails for all financial transactions

---

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation Strategy |
|------|------------|--------|---------------------|
| **`apps.economy` API changes** | Medium | High | Pin API version, add integration tests |
| **PDF generation library issues** | Low | Medium | Evaluate both ReportLab and WeasyPrint, pick stable option |
| **Prize payout rounding errors** | Low | Critical | Use `Decimal` for all calculations, add reconciliation tests |
| **Certificate forgery** | Low | Medium | Implement SHA256 hash verification, QR code validation |
| **Analytics query performance** | Medium | Medium | Use materialized views, add database indexes |
| **Timezone handling in reports** | Low | Low | Store all timestamps in UTC, convert in UI layer |

---

## Next Steps

1. **Review Phase 5 plan with stakeholders**
2. **Install Python dependencies:** `reportlab`, `Pillow`, `qrcode`
3. **Create Phase 5 branch:** `git checkout -b phase/5-tournament-post-game`
4. **Start Module 5.1:** Winner determination service
5. **Update `trace.yml`** with Phase 5 module entries

---

**Prepared by:** GitHub Copilot  
**Date:** November 9, 2025  
**Review Status:** Ready for stakeholder approval  
**Next Review:** Before Module 5.1 kickoff

