# UP-PHASE9A: Production Observability & Monitoring Plan

**Phase:** Post-Launch Readiness  
**Type:** Strategic Planning (No Implementation)  
**Date:** 2025-12-29  
**Status:** Planning Document

---

## Executive Summary

This document defines **observability requirements** for the user_profile system in production. It identifies critical monitoring points, error tracking strategies, privacy-specific alerts, and admin misuse detection without implementing any code.

**Goal:** Ensure user_profile system can be safely operated, debugged, and scaled in production.

---

## 1. Error Monitoring Strategy

### 1.1 Error Tracking Platform

**Recommended:** Sentry (or equivalent: Rollbar, Bugsnag)

**Rationale:**
- Django integration available (sentry-sdk)
- Automatic error aggregation
- User context (without PII leakage)
- Stack traces with source context
- Performance monitoring included

### 1.2 Critical Error Classes to Track

#### High Priority (Immediate Alert)

**Profile Page Errors:**
- `UserProfile.DoesNotExist` (indicates data integrity issue)
- `PrivacySettings.DoesNotExist` (privacy system failure)
- Template rendering errors in `public.html` (breaks user experience)
- `ProfilePermissionChecker` exceptions (privacy enforcement failure)

**Settings Page Errors:**
- Avatar/banner upload failures (storage issues)
- Privacy save failures (data corruption risk)
- CSRF token failures (security concern)
- Wallet settings save failures (economy integration issue)

**Admin Panel Errors:**
- Economy field edit attempts (should be blocked by readonly)
- Game Passport schema validation failures
- Bulk actions that skip validation

#### Medium Priority (Daily Review)

- Social link validation failures
- Game Passport creation errors
- Follow/unfollow failures
- Activity feed pagination errors

#### Low Priority (Weekly Review)

- Cache misses (if caching implemented)
- Slow query warnings (>500ms)
- Template tag deprecation warnings

### 1.3 Error Context Requirements

**DO Capture:**
- Request path and method
- User ID (for logged-in users)
- Username (for profile views)
- View function name
- Privacy settings state (as JSON)

**DO NOT Capture:**
- Email addresses
- Phone numbers
- Real names (KYC data)
- Wallet account numbers
- Emergency contact details
- Session tokens or passwords

**Sentry Configuration Example (Conceptual):**
```python
# deltacrown/settings.py (NOT IMPLEMENTED - REFERENCE ONLY)
SENTRY_DSN = env('SENTRY_DSN', default=None)
SENTRY_ENVIRONMENT = env('SENTRY_ENVIRONMENT', default='production')
SENTRY_TRACES_SAMPLE_RATE = 0.1  # 10% of transactions

# PII scrubbing
SENTRY_SEND_DEFAULT_PII = False
SENTRY_BEFORE_SEND = scrub_sensitive_data  # Custom function
```

---

## 2. Performance Metrics

### 2.1 Page Load Metrics

**Profile Public Page:**
- Target: <300ms server-side render (P50)
- Alert: >500ms (P95)
- Critical: >1000ms (P99)

**Metrics to Track:**
- Database query time
- Template rendering time
- Total request duration
- Memory usage per request

**Settings Page:**
- Target: <200ms server-side render (no complex queries)
- Alert: >400ms (P95)

**Admin Panel:**
- Target: <500ms (complex forms acceptable)
- Alert: >1000ms

### 2.2 API Endpoint Metrics

**Critical Endpoints:**
- `POST /me/settings/basic/` (profile updates)
- `POST /me/settings/privacy/save/` (privacy changes)
- `GET /me/settings/privacy/` (privacy state load)
- `POST /actions/follow-safe/<username>/` (follow actions)

**Metrics:**
- Request rate (requests/second)
- Error rate (%)
- Latency (P50, P95, P99)
- 4xx vs 5xx errors

### 2.3 Database Query Monitoring

**Query Budget Violations (see 9B for details):**
- Profile page: Alert if >25 queries
- Settings page: Alert if >15 queries
- Admin changelist: Alert if >50 queries

**Slow Query Detection:**
- Warn: >100ms
- Alert: >500ms
- Critical: >1000ms

**N+1 Detection:**
- Track queries per request
- Alert on missing `select_related`/`prefetch_related`

---

## 3. Privacy-Related Alerts

### 3.1 Privacy Enforcement Failures

**Critical Alerts (Immediate):**

**1. Permission Check Bypass:**
- Monitor: All `can_view_*` checks in `ProfilePermissionChecker`
- Alert if: Exception raised during permission check
- Risk: User sees content they shouldn't

**2. Template Bypass:**
- Monitor: Template rendering without `can_view_*` checks
- Alert if: Private sections rendered without permission flags
- Detection: Log template context keys for suspicious patterns

**3. Privacy Settings Corruption:**
- Monitor: `PrivacySettings.save()` failures
- Alert if: Save fails after user submits privacy form
- Risk: User thinks data is private but it's not

### 3.2 Privacy Misconfiguration Detection

**Daily Checks:**

**1. Profile Visibility Anomalies:**
- Query: Count profiles with `profile_visibility='PRIVATE'` but `show_social_links=True`
- Risk: Misconfiguration (private profile shouldn't show anything)
- Action: Admin review

**2. Missing Privacy Settings:**
- Query: Count `UserProfile` records without corresponding `PrivacySettings`
- Expected: 0 (should auto-create)
- Action: Create missing records

**3. Orphaned Data:**
- Query: Count `GameProfile` records without valid `user_profile_id`
- Expected: 0
- Action: Data cleanup

### 3.3 Privacy Event Logging

**Events to Log (Audit Trail):**
- Privacy setting changes (before/after values)
- Profile visibility changes
- Game Passport visibility changes
- Follow/unfollow actions
- Admin profile views

**Storage:** Separate audit log table (not Sentry)

---

## 4. Admin Misuse Detection

### 4.1 Economy Field Protection

**Risk:** Admin manually editing `deltacoin_balance` or `lifetime_earnings`

**Detection:**
- Monitor: All `UserProfile.save()` calls from admin interface
- Check: If `deltacoin_balance` or `lifetime_earnings` changed
- Alert: Email to tech lead + log to audit trail
- Action: Investigate if balance changed by admin

**Implementation Hook (Conceptual):**
```python
# apps/user_profile/admin.py (NOT IMPLEMENTED)
def save_model(self, request, obj, form, change):
    if change:  # Editing existing
        old_obj = UserProfile.objects.get(pk=obj.pk)
        if old_obj.deltacoin_balance != obj.deltacoin_balance:
            logger.critical(f"ADMIN_ECONOMY_EDIT: {request.user} changed balance for {obj.user}")
            # Send alert to Sentry with high priority
    super().save_model(request, obj, form, change)
```

### 4.2 Bulk Action Risks

**High-Risk Actions:**
- Bulk delete of UserProfile (data loss)
- Bulk privacy setting changes (privacy violation)
- Bulk Game Passport deletion (data loss)

**Detection:**
- Monitor: Admin action log for bulk operations
- Alert if: >10 records affected in single action
- Require: Confirmation dialog + audit log

### 4.3 Wallet Data Access Monitoring

**Risk:** Admin viewing sensitive wallet account numbers

**Detection:**
- Log: All admin views of `WalletSettings` records
- Track: Admin user, timestamp, profile viewed
- Review: Weekly audit of wallet access

**Justification:** WalletSettings contains Bkash/Nagad/Rocket account numbers (sensitive financial data)

### 4.4 KYC Data Access Monitoring

**Risk:** Admin viewing real names, birthdates, nationalities

**Detection:**
- Log: Admin views of profiles with `kyc_status='VERIFIED'`
- Track: Which fields were displayed
- Retention: 90 days (compliance requirement)

---

## 5. Real-Time Alerts

### 5.1 Alerting Thresholds

**P1 (Page Immediately):**
- Profile page 5xx error rate >5% over 5 minutes
- Privacy enforcement failure detected
- Economy field edited by admin
- Database connection lost

**P2 (Slack Alert):**
- Profile page latency P95 >500ms for 10 minutes
- Settings save error rate >10% over 5 minutes
- N+1 query detected in production

**P3 (Email Daily Digest):**
- Slow query warnings
- Missing privacy settings detected
- Admin bulk action performed

### 5.2 Alert Routing

**On-Call Engineer:** P1 alerts  
**Tech Lead:** P2 alerts + weekly P3 digest  
**Product Manager:** Monthly privacy audit report

---

## 6. Monitoring Dashboard

### 6.1 Real-Time Dashboard (Grafana/Datadog)

**Key Metrics:**

**Panel 1: Request Volume**
- Profile page views/hour
- Settings page views/hour
- API requests/hour

**Panel 2: Error Rates**
- 4xx errors (%)
- 5xx errors (%)
- Error breakdown by endpoint

**Panel 3: Performance**
- P50/P95/P99 latencies
- Database query count per request
- Slow query count

**Panel 4: Privacy System Health**
- Privacy settings coverage (%)
- Permission check failures
- Privacy save errors

**Panel 5: Admin Activity**
- Admin profile views
- Wallet settings accesses
- Bulk actions performed

### 6.2 Weekly Report (Automated)

**Sections:**
1. Traffic summary (page views, unique visitors)
2. Error summary (top 10 errors, resolution status)
3. Performance trends (latency over time)
4. Privacy incidents (none expected)
5. Admin activity review

---

## 7. Log Aggregation

### 7.1 Structured Logging

**Format:** JSON logs (for Elasticsearch/CloudWatch)

**Required Fields:**
```json
{
  "timestamp": "2025-12-29T10:30:00Z",
  "level": "ERROR",
  "logger": "apps.user_profile.views.fe_v2",
  "message": "Failed to load profile",
  "context": {
    "username": "johndoe",
    "viewer_id": 12345,
    "error": "UserProfile.DoesNotExist"
  },
  "request_id": "uuid-here"
}
```

### 7.2 Log Retention

- ERROR logs: 90 days
- INFO logs: 30 days
- DEBUG logs: 7 days (dev only)
- Audit logs: 1 year (compliance)

---

## 8. Health Checks

### 8.1 Application Health Endpoint

**Endpoint:** `/health/user_profile/`

**Checks:**
- Database connectivity (UserProfile table)
- Privacy settings integrity
- Media storage access (avatars/banners)
- Game Passport schema validity

**Response:**
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "privacy_settings": "ok",
    "media_storage": "ok",
    "game_passport_schema": "ok"
  },
  "timestamp": "2025-12-29T10:30:00Z"
}
```

### 8.2 Synthetic Monitoring

**Tests to Run Every 5 Minutes:**
- Load public profile (200 OK expected)
- Check profile returns valid HTML
- Verify privacy enforcement (private profile returns private page)

---

## 9. Incident Response

### 9.1 Privacy Breach Protocol

**If Private Data Leaked:**
1. Immediately disable affected endpoint (feature flag)
2. Audit logs to identify scope (who saw what)
3. Notify affected users within 24 hours
4. Fix root cause + deploy
5. Post-mortem within 48 hours

### 9.2 Data Corruption Protocol

**If Economy Fields Corrupted:**
1. Halt all admin saves to UserProfile
2. Identify last known good state (database backup)
3. Restore from economy app (source of truth)
4. Re-enable admin with readonly enforcement

---

## 10. Implementation Checklist

**Before Launch:**
- [ ] Install Sentry SDK (or equivalent)
- [ ] Configure PII scrubbing
- [ ] Set up error alerting (P1/P2/P3)
- [ ] Create Grafana/Datadog dashboard
- [ ] Implement health check endpoint
- [ ] Configure log aggregation (CloudWatch/ELK)
- [ ] Set up synthetic monitoring
- [ ] Document incident response procedures

**After Launch (First Week):**
- [ ] Review all error logs daily
- [ ] Validate alert thresholds (adjust if noisy)
- [ ] Confirm no privacy leaks in Sentry
- [ ] Verify query budgets are respected
- [ ] Test admin misuse detection

**After Launch (First Month):**
- [ ] Analyze performance trends
- [ ] Identify optimization opportunities
- [ ] Review admin activity audit logs
- [ ] Tune alerting thresholds based on real traffic

---

## 11. Success Metrics

**Observability Goals (First 3 Months):**
- Mean Time to Detection (MTTD): <5 minutes for P1 errors
- Mean Time to Resolution (MTTR): <1 hour for P1 errors
- False positive rate: <10% (alerts that aren't real issues)
- Privacy incidents: 0 (goal)
- Admin misuse incidents: 0 (goal)

---

## 12. Cost Considerations

**Estimated Monthly Costs:**
- Sentry (100k events): $50-100/month
- Grafana Cloud (or self-hosted): $0-50/month
- CloudWatch Logs (100GB): $50/month
- **Total:** ~$150-200/month for observability

**ROI:** Faster incident response, fewer user complaints, protected reputation.

---

## Final Recommendations

**Priority 1 (Launch Blockers):**
1. Install Sentry with PII scrubbing
2. Set up basic error alerting
3. Create health check endpoint

**Priority 2 (First Week):**
4. Set up performance monitoring dashboard
5. Implement admin misuse detection
6. Configure log aggregation

**Priority 3 (First Month):**
7. Tune alert thresholds based on real traffic
8. Set up synthetic monitoring
9. Create weekly reporting automation

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-29  
**Status:** Planning Document - No Implementation Required  
**Owner:** Platform Engineering Team
