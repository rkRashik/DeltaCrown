# UP-06: Audit & Security Foundation

**Status:** Target Architecture  
**Owner:** UserProfile + Moderation + Security Team  
**Last Updated:** 2025-12-22

---

## 1. Threat Model

**Primary Threats:**
- **PII Exposure** → Email, phone, DOB, real name leaked via API/template bypass
- **KYC Document Theft** → Passport/ID images accessed without authorization
- **Profile Enumeration** → Attacker scrapes all user profiles via sequential ID scanning
- **Account Takeover** → Attacker changes email/settings without proper verification
- **Economy Fraud** → Manual balance adjustments without audit trail
- **Privacy Bypass** → Hidden fields exposed via API/admin/query manipulation
- **Insider Threat** → Staff abuse access to view sensitive user data
- **Data Tampering** → Critical events (KYC approval, balance change) altered or deleted

**Attack Vectors:**
- Direct API calls bypassing privacy checks
- Template {{ profile.email }} exposing PII
- Admin panel bulk exports without logging
- SQL injection in custom queries
- Brute-force profile ID scanning
- CSRF on profile update endpoints
- Session hijacking to access other profiles

**Defense Layers:**
1. **Prevention** → Privacy enforcement (UP-03), rate limiting, access controls
2. **Detection** → Immutable audit logs, anomaly alerts
3. **Response** → Auto-lockout on abuse, admin alerts, forensic investigation

---

## 2. AuditEvent Requirements

### What MUST Be Logged (Immutable Records)

**Profile Changes:**
- Email change (old → new values, verification status)
- Display name change (old → new values)
- Real name change (old → new, requires explanation field)
- DOB change (old → new, requires admin approval)
- Phone change (old → new, SMS verification)
- Avatar/banner upload (file path, size, timestamp)
- Bio/social links edit (old → new values)

**Privacy Changes:**
- Any PrivacySettings field toggle (field name, old → new value)
- Visibility level change (public → private, etc.)
- Privacy policy acceptance (version, timestamp, IP)

**KYC Actions:**
- Document upload (document type, file hash, uploader IP)
- Verification status change (pending → approved/rejected, reviewer ID, reason)
- KYC document view (viewer ID, timestamp, purpose)
- KYC document download (viewer ID, timestamp, IP)
- Verification expiry (auto-logged when verification expires)

**Economy Actions (Critical Path):**
- Manual balance adjustment (old → new balance, admin ID, reason)
- Wallet freeze/unfreeze (admin ID, reason)
- Transaction reversal (original tx ID, reversal tx ID, reason)
- Lifetime earnings manual correction (old → new, reason)

**Admin Actions:**
- Profile impersonation (admin views as user, duration)
- Bulk data export (admin ID, filters used, row count, timestamp)
- Force logout (admin ID, reason)
- Account suspension (admin ID, reason, duration)
- Profile deletion (admin ID, reason, soft/hard delete)

**Security Events:**
- Login from new device/location (IP, user agent, geolocation)
- Failed login attempts (IP, username tried, count)
- Password change (initiated by user vs admin reset)
- Email verification (verification method, IP)
- 2FA enable/disable (method, timestamp)

### AuditEvent Model Schema (NEW)

**Required Fields:**
- user (ForeignKey: nullable for system events)
- actor (ForeignKey: who performed action, nullable for user self-actions)
- event_type (CharField: choices enum, indexed)
- entity_type (CharField: PROFILE / KYC / PRIVACY / ECONOMY / ADMIN)
- entity_id (IntegerField: ID of affected record)
- action (CharField: CREATE / UPDATE / DELETE / VIEW / DOWNLOAD / APPROVE)
- old_value (JSONField: before state)
- new_value (JSONField: after state)
- reason (TextField: required for sensitive actions)
- ip_address (GenericIPAddressField)
- user_agent (TextField)
- created_at (DateTimeField: indexed, immutable)

**Immutability Enforcement:**
- No UPDATE or DELETE allowed (database trigger prevents modification)
- Only INSERT permitted
- Foreign keys use on_delete=PROTECT (cannot delete referenced objects)
- Audit log table has no admin edit interface (read-only)

**Retention Policy:**
- **Critical events (KYC, economy, admin):** Retain forever
- **Profile edits:** Retain 7 years (regulatory compliance)
- **Security events:** Retain 1 year
- **Routine logs (views):** Retain 90 days
- Archive old logs to cold storage after retention period (NOT deleted)

---

## 3. KYC Handling Rules

### Encryption at Rest

**Sensitive Fields (Must Be Encrypted):**
- `real_full_name` → AES-256 encryption
- `date_of_birth` → AES-256 encryption
- `phone` → AES-256 encryption (if used for KYC)
- KYC document files (passport/ID images) → File-level encryption

**Implementation:**
- Use Django's `django-fernet-fields` or equivalent
- Encryption keys stored in environment variables (NOT in database)
- Key rotation policy: annual, with dual-key decryption during transition
- Encrypted fields not indexed (use hashed search columns for queries)

**Non-Encrypted Fields (Acceptable):**
- `display_name` → Public data, no encryption needed
- `bio` → User-controlled public content
- `country` / `region` → Low sensitivity, used for filters

### Access Controls (Who Can View/Download)

| Action | User (Self) | Authenticated User | Staff | Superuser | KYC Reviewer |
|--------|-------------|---------------------|-------|-----------|--------------|
| View own real name | ✅ | ❌ | ❌ | ✅ | ✅ |
| View own DOB | ✅ | ❌ | ❌ | ✅ | ✅ |
| View KYC documents | ✅ | ❌ | ❌ | ✅ | ✅ (assigned only) |
| Download KYC documents | ✅ | ❌ | ❌ | ✅ | ✅ (assigned only) |
| Approve/reject KYC | ❌ | ❌ | ❌ | ✅ | ✅ |
| View audit logs | ❌ | ❌ | ❌ | ✅ | ✅ (user's logs only) |

**Permission Enforcement:**
- Django permission `view_kyc_documents` required for staff access
- KYC reviewer role assigned per-user (ForeignKey to reviewer on VerificationRecord)
- Superusers have all access but ALL actions logged
- API endpoints check permissions before decrypting fields

### Access Logging Requirements

**Every KYC Access MUST Log:**
- Viewer ID and role
- User whose data was accessed
- Action (view / download / approve / reject)
- Timestamp and IP
- Purpose field (text explanation required for staff/superuser access)

**Alerts Triggered On:**
- Same user's KYC viewed >5 times in 1 hour by same staff member (anomaly)
- KYC document downloaded (always alert security team)
- Bulk KYC exports (>10 users in single query)
- Superuser accesses KYC of high-profile user (VIP list)

**Access Review:**
- Weekly report of all KYC accesses by staff
- Monthly audit of access patterns
- Quarterly access recertification (staff re-approved for KYC access)

---

## 4. Privacy Enforcement Hard Requirements

**Reference:** See UP-03 for full privacy architecture

**Non-Negotiable Rules:**
1. **All PII fields default to hidden** → Users opt-in to share
2. **4-layer enforcement required** → Templates, APIs, Services, QuerySets
3. **No direct field access** → Always use privacy-aware methods
4. **No PII in logs** → Grep audit required before release
5. **Privacy bypass = security incident** → Treat as critical bug

**Hard Blockers (Cannot Deploy Without):**
- [ ] PrivacyAwareProfileSerializer enforces privacy_settings checks
- [ ] Template tags `{% privacy_check %}` used for ALL PII fields
- [ ] Service layer methods (get_visible_fields) respect viewer relationship
- [ ] QuerySet method `.visible_to(viewer)` filters profiles by privacy
- [ ] Admin panel displays privacy warnings on sensitive fields

**Regression Prevention:**
- Pre-commit hook: grep for `{{ profile.email }}` and similar patterns (fails CI)
- Test suite: privacy bypass tests in every API/view test file
- Security review required for all UserProfile changes

---

## 5. Rate Limiting & Abuse Prevention

### Profile Endpoints (API + Web)

**Rate Limits:**
- Profile view (own): 60 requests/minute (high traffic expected)
- Profile view (others): 10 requests/minute (prevent scraping)
- Profile update: 5 requests/minute (prevent spam/abuse)
- KYC document upload: 3 requests/hour (legitimate use is infrequent)
- Privacy settings update: 10 requests/minute (allow multiple toggles)

**Implementation:**
- Django Ratelimit middleware with Redis backend
- Rate key: user ID for authenticated, IP for anonymous
- Response: 429 Too Many Requests with Retry-After header

### Public ID Enumeration Prevention

**Problem:** Sequential IDs (DC-25-000042) allow enumeration

**Mitigations:**
1. **Profile view rate limit** → 10/min prevents bulk scraping
2. **Randomized pagination** → Profile lists shuffle order
3. **CAPTCHA on anonymous access** → Public profile view requires CAPTCHA after 5 profiles
4. **Monitoring alerts** → Sequential access pattern detection (e.g., DC-25-000042, 000043, 000044 in quick succession)
5. **Honeypot profiles** → Fake profiles detect scraper behavior

**Acceptance:**
- Enumeration still possible but impractical at scale
- Trade-off: Human-friendly IDs vs absolute anti-enumeration
- Monitor and ban abusive IPs

### API Abuse Detection

**Automated Lockout Triggers:**
- 100 profile views in 10 minutes → Temporary IP ban (1 hour)
- 50 failed privacy checks in 1 hour → Account flagged for review
- 10 KYC document requests in 1 day (non-owner) → Permanent ban + alert
- Pattern match: sequential ID access → CAPTCHA challenge + alert

**Admin Dashboard Metrics:**
- Requests per user/IP per hour
- Privacy bypass attempt count
- Rate limit hit frequency
- Geographic anomalies (user in US suddenly requests from Russia)

---

## 6. Security Acceptance Criteria

### Implementation Complete
- [ ] AuditEvent model created with immutability enforced (DB trigger)
- [ ] All profile/privacy/KYC changes logged automatically (signal handlers)
- [ ] KYC sensitive fields encrypted at rest (Fernet fields)
- [ ] KYC access permissions enforced (decorator on views/APIs)
- [ ] KYC access logging active (every view/download logged)
- [ ] Rate limiting applied to all profile endpoints
- [ ] Public ID enumeration alerts configured

### Unit Tests Pass
- [ ] Audit log creation on profile edit (old → new values captured)
- [ ] Audit log immutability (UPDATE/DELETE raises error)
- [ ] KYC field encryption (plaintext not in database)
- [ ] KYC access denied for unauthorized roles
- [ ] KYC access logged on every successful view
- [ ] Privacy settings block field access for non-owner
- [ ] Rate limit returns 429 after threshold exceeded

### Integration Tests Pass
- [ ] Profile edit → audit log created → log contains IP and user agent
- [ ] KYC upload → audit log created → file hash matches
- [ ] Staff views KYC → audit log created → viewer ID logged
- [ ] Superuser downloads KYC → security alert triggered
- [ ] User toggles privacy → audit log created → old/new values match
- [ ] API exceeds rate limit → 429 response → retry after 60 seconds
- [ ] Sequential ID access → alert triggered → honeypot served

### Security Audit Checks
- [ ] No PII in application logs (grep audit passes)
- [ ] No PII in error messages (Sentry scrubbing configured)
- [ ] No direct field access in templates (grep audit passes)
- [ ] Admin panel requires 2FA for KYC access
- [ ] Encryption keys not in repository (environment variables only)
- [ ] Audit log retention policy documented and enforced

### Manual Penetration Tests
- [ ] Attempt to bypass privacy via API parameter manipulation (fails)
- [ ] Attempt to access other user's KYC documents (fails, logs attempt)
- [ ] Attempt to scrape 100 profiles (rate limited, CAPTCHA triggered)
- [ ] Attempt to enumerate IDs sequentially (alerted, slowed down)
- [ ] Attempt to modify audit log (database error, immutability enforced)
- [ ] Attempt to decrypt KYC fields without key (fails)

### Monitoring & Alerting Active
- [ ] Slack alert on KYC document download
- [ ] PagerDuty alert on bulk KYC export (>10 users)
- [ ] Email alert on sequential ID enumeration pattern
- [ ] Dashboard shows rate limit hits per endpoint
- [ ] Grafana panel displays audit log volume (should be steady)

---

## Blocked Until Implementation

**CANNOT deploy User Profile changes until:**
1. AuditEvent model live and logging all profile/KYC changes
2. KYC fields encrypted (no plaintext in database)
3. Privacy enforcement passing all bypass tests
4. Rate limiting active on all public endpoints
5. Security team completes penetration test

**Risk if deployed without:** Data breach, regulatory non-compliance, account takeover, fraud

---

**End of Document**
