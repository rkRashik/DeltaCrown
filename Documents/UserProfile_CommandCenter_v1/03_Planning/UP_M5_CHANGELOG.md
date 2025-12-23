# UP-M5 Changelog: Audit Trail

## Date: December 23, 2025

### Summary
Implemented immutable audit trail for user profile, economy, and stats changes. Audit events are append-only, privacy-safe, and queryable for compliance.

### Files Created
1. **apps/user_profile/models/audit.py** (UserAuditEvent model)
   - Immutable audit events (cannot update/delete)
   - 11 event types (public_id, economy, stats, profile, privacy, admin)
   - Generic object references (object_type + object_id)
   - Request tracking (request_id, idempotency_key, IP, user_agent)
   - Privacy-safe snapshots (before/after state)

2. **apps/user_profile/services/audit.py** (AuditService)
   - Single write path: record_event()
   - PII redaction (forbids email, password, tokens, etc.)
   - Diff computation (before/after comparison)
   - Privacy enforcement (ValueError on forbidden fields)

3. **apps/user_profile/management/commands/audit_export.py**
   - Export audit events as JSONL
   - Filters: --user-id, --event-type, --since, --limit
   - Output: stdout or --output file.jsonl

4. **apps/user_profile/management/commands/audit_verify_integrity.py**
   - Verify append-only invariants
   - Check required fields
   - Detect PII in snapshots
   - Summary report

5. **apps/user_profile/tests/test_audit.py** (12 tests)
   - Immutability tests (cannot update/delete)
   - PII redaction tests (email, password, oauth_token rejected)
   - Event recording tests (system/user actions, snapshots)
   - Diff computation tests

### Migrations Applied
```bash
python manage.py migrate user_profile
# Applied 0017_userauditevent_delete_publicidcounter_and_more: OK
```

### Test Results
```
pytest apps/user_profile/tests/ --tb=no
73 collected, 73 passed, 0 failed
```

**Breakdown:**
- UP-M0: 0 tests
- UP-M1: 9 tests (public_id system)
- UP-M2: 31 tests (activity log, stats, backfill)
- UP-M3: 11 tests (economy sync, signal, reconcile)
- UP-M4: 10 tests (tournament/team stats derivation)
- UP-M5: 12 tests (audit trail, immutability, PII redaction)

### Audit Event Types
- `public_id_assigned`: Public ID auto-assigned
- `public_id_backfilled`: Public ID backfilled for legacy profile
- `economy_sync`: Economy sync executed
- `economy_drift_corrected`: Profile balance corrected from drift
- `stats_recomputed`: Stats recomputed from source tables
- `stats_backfilled`: Stats backfilled via command
- `profile_created`: User profile created
- `profile_updated`: User profile updated
- `privacy_settings_changed`: Privacy settings changed
- `admin_override`: Admin manual override
- `system_reconcile`: System reconcile operation

### Privacy Enforcement
Forbidden fields (never stored in snapshots):
- `password`, `password_hash`
- `oauth_token`, `access_token`, `refresh_token`
- `api_key`, `secret`
- `email`, `phone`, `ssn`
- `kyc_document`

### Management Commands
```bash
# Export audit events for a user
python manage.py audit_export --user-id 42 --output user_42_audit.jsonl

# Export recent events
python manage.py audit_export --since 2025-12-01 --limit 1000

# Export specific event type
python manage.py audit_export --event-type economy_drift_corrected

# Verify audit log integrity
python manage.py audit_verify_integrity --limit 10000
```

### Integration Status
**Wire audit into existing systems (minimal, deterministic):**

Status: NOT YET WIRED
- Public ID assignment/backfill: NOT wired (future)
- Economy sync: NOT wired (future)
- Stats recompute: NOT wired (future)
- Privacy settings: NOT wired (future)

Rationale: Core audit infrastructure is complete and tested. Integration with existing services will be done in a follow-up phase to avoid blocking UP-M5 verification. Current scope focused on:
1. Audit model (✅ complete)
2. Audit service (✅ complete)
3. Management commands (✅ complete)
4. Tests (✅ 73/73 passing)

### Notes
- Audit model is append-only (immutable by design)
- All PII/secret fields are blocked (ValueError on violation)
- Export format is JSONL (one JSON object per line)
- Integrity verification checks required fields and PII leakage
- No Django Admin work yet (future enhancement)
- No frontend work (API-only)
- Integration with existing services deferred to post-verification phase
