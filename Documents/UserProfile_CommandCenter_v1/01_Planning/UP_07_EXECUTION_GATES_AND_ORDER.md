# UP-07: Execution Gates & Order

**Status:** Planning Document  
**Owner:** Development Team  
**Last Updated:** 2025-12-22

---

## 1. Preconditions (Must Be True Before Starting)

**Development Environment:**
- [ ] Local dev environment running (PostgreSQL, Redis, Django dev server)
- [ ] Test database isolated (not production, not staging)
- [ ] Migrations applied cleanly on fresh database
- [ ] All existing tests passing (no broken baseline)
- [ ] Git branch created from main (`feature/user-profile-modernization`)

**Code Baseline:**
- [ ] Current User and UserProfile models documented
- [ ] All referencing apps identified (teams, tournaments, economy, etc.)
- [ ] Audit report reviewed (USER_PROFILE_AUDIT_REPORT.md current)
- [ ] No critical P0 bugs in production blocking work

**Team Readiness:**
- [ ] Architecture documents (UP-01 through UP-06) reviewed by team
- [ ] Execution plan agreed upon (phase order, responsibilities)
- [ ] QA resources available for testing
- [ ] Staging environment ready for deployment testing

**Stakeholder Alignment:**
- [ ] Tournament Phase 1 paused (acknowledged by product owner)
- [ ] User Profile stability prioritized over new features
- [ ] Timeline expectations set (2-3 weeks for core work)

---

## 2. Safety Gates (Must-Pass Checks)

### Per-Commit Gates (CI Pipeline)

**Test Coverage:**
- All existing tests pass (pytest exit code 0)
- No new failing tests introduced
- Code coverage ≥ 75% for modified files
- Critical paths (profile creation, privacy checks) have integration tests

**Privacy Grep Audit:**
- No `{{ profile.email }}` in templates (PII leak pattern)
- No `logger.info(.*email)` in code (log PII pattern)
- No `profile.phone` direct access (privacy bypass pattern)
- No `model_to_dict(profile)` without privacy filter
- CI fails on match (prevent merge)

**Security Checks:**
- No hardcoded secrets (SECRET_KEY, API keys, passwords)
- No encryption keys in repository
- No SQL injection patterns (raw queries audited)
- Bandit security linter passes

**Migration Safety:**
- Migrations apply cleanly on empty database
- Migrations are reversible (no data loss on rollback)
- No migrations alter critical tables without backup plan

### Per-Phase Gates (Manual Review)

**UP-1 Gate (Profile Invariant):**
- [ ] Signal creates profile on User creation (100% success rate in tests)
- [ ] All code paths use safety accessor (`get_or_create_profile()`)
- [ ] Zero `UserProfile.DoesNotExist` exceptions in logs after deployment
- [ ] 47+ locations updated to use safe access pattern

**UP-2 Gate (Public ID):**
- [ ] PublicIDCounter model created and migrated
- [ ] Public ID generation tested (concurrency, year rollover)
- [ ] All existing users backfilled with sequential IDs
- [ ] Public profile URLs use public_id (not username or PK)
- [ ] Enumeration rate limiting active

**UP-3 Gate (Privacy Enforcement):**
- [ ] PrivacySettings model has sensible defaults
- [ ] Privacy-aware serializers enforce settings
- [ ] Template tags block PII unless authorized
- [ ] Privacy bypass tests pass (negative testing)
- [ ] Grep audit passes (no direct PII access)

**UP-4 Gate (Economy Sync):**
- [ ] Signal updates profile balance on transaction completion
- [ ] Reconciliation command detects drift
- [ ] Balance integrity tests pass (concurrent transactions)
- [ ] Nightly reconciliation scheduled
- [ ] Drift rate <1% in staging

**UP-5 Gate (Stats & History):**
- [ ] TournamentParticipation model created
- [ ] Match model populated on game completion
- [ ] UserActivity model tracks major events
- [ ] Cached stats updated via signals
- [ ] Activity timeline respects privacy

**UP-6 Gate (Audit & Security):**
- [ ] AuditEvent model immutable (DB trigger enforced)
- [ ] All sensitive actions logged automatically
- [ ] KYC fields encrypted at rest
- [ ] Rate limiting active on profile endpoints
- [ ] Security penetration test completed

---

## 3. Execution Order (Phase by Phase)

| Phase | Focus | Dependencies | Duration | Deploy to Staging | Gate Check |
|-------|-------|--------------|----------|-------------------|------------|
| **UP-0** | Safety Net | None | 2 days | No | Tests pass |
| **UP-1** | Profile Invariant | UP-0 | 3 days | Yes | Zero DoesNotExist errors |
| **UP-2** | Public ID | UP-1 | 2 days | Yes | Backfill complete |
| **UP-3** | Privacy Enforcement | UP-1 | 4 days | Yes | Grep audit passes |
| **UP-4** | Economy Sync | UP-1, UP-3 | 3 days | Yes | Drift <1% |
| **UP-5** | Stats & History | UP-1, UP-4 | 4 days | Yes | Stats accurate |
| **UP-6** | Audit & Security | All above | 3 days | Yes | Pen test passes |

**Total Estimated Duration:** 21 days (3 weeks)

### UP-0: Safety Net (Precursor)
**Goal:** Make current system safe to modify

**Tasks:**
- Write comprehensive tests for existing behavior
- Add safety accessors (get_or_create_profile)
- Document all integration points
- Create rollback plan

**Deployment:** None (test-only changes)

### UP-1: Profile Invariant
**Goal:** Guarantee every User has UserProfile

**Tasks:**
- Strengthen signal handler (atomic, handles edge cases)
- Add middleware safety net
- Update all 47+ locations to use safe access
- Backfill any missing profiles

**Deployment:** Staged rollout (monitor for 24h)

### UP-2: Public ID
**Goal:** Non-PII, human-friendly identifier

**Tasks:**
- Create PublicIDCounter model
- Add public_id field to UserProfile
- Implement generation logic (atomic, year rollover)
- Backfill existing users
- Update URLs to use public_id

**Deployment:** Staged (backfill in maintenance window)

### UP-3: Privacy Enforcement
**Goal:** 4-layer privacy protection

**Tasks:**
- Create PrivacyAwareProfileSerializer
- Build template tags ({% privacy_check %})
- Implement service layer privacy methods
- Add QuerySet filter (visible_to)
- Grep audit and fix violations

**Deployment:** Staged (test privacy flags thoroughly)

### UP-4: Economy Sync
**Goal:** Profile balance always matches ledger

**Tasks:**
- Add signal handlers (transaction → profile update)
- Build reconciliation command
- Schedule nightly reconciliation
- Test concurrent transactions

**Deployment:** Staged (monitor drift rate)

### UP-5: Stats & History
**Goal:** Track tournaments, matches, activity

**Tasks:**
- Create TournamentParticipation model
- Extend TournamentResult model
- Populate Match model on game completion
- Create UserActivity model
- Wire signals for stat updates

**Deployment:** Staged (backfill historical data)

### UP-6: Audit & Security
**Goal:** Immutable audit trail, KYC encryption

**Tasks:**
- Create AuditEvent model (immutable)
- Encrypt KYC sensitive fields
- Add access logging for KYC views
- Implement rate limiting
- Penetration testing

**Deployment:** Requires security review approval

---

## 4. "Stop-the-Line" Rules

**Development MUST PAUSE if:**

1. **Test Pass Rate Drops Below 95%**
   - Fix broken tests before continuing
   - Do not accumulate technical debt

2. **Privacy Grep Audit Fails**
   - Any direct PII access found → fix immediately
   - Cannot merge PR with privacy violations

3. **Critical Bug Discovered in Production**
   - P0 bugs take priority over User Profile work
   - Resume User Profile after hotfix deployed

4. **Migration Fails on Staging**
   - Do not proceed to next phase
   - Fix migration before continuing

5. **Audit Log Immutability Violated**
   - If AuditEvent records can be modified → halt
   - Security incident, requires investigation

6. **Drift Rate Exceeds 5%**
   - If economy reconciliation finds >5% drift → halt
   - Investigate root cause before continuing

7. **Security Penetration Test Fails**
   - Cannot deploy to production
   - Fix vulnerabilities before resuming

**Escalation Path:**
- Blocker identified → notify team lead immediately
- Team lead assesses severity and impact
- If cannot resolve in 4 hours → escalate to engineering manager
- Engineering manager decides: fix now vs defer vs abort phase

---

## 5. Resume Conditions for Tournament Phase 1

**Tournament Phase 1 CAN RESUME when:**

1. **User Profile Core Complete:**
   - [ ] UP-1 through UP-3 deployed to production (invariant, public ID, privacy)
   - [ ] Zero profile-related errors in logs for 48 hours
   - [ ] All safety gates passed

2. **Economy Integration Stable:**
   - [ ] UP-4 deployed to production (economy sync)
   - [ ] Drift rate <1% for 7 consecutive days
   - [ ] Reconciliation command running successfully

3. **Stats Foundation Ready:**
   - [ ] TournamentParticipation model created and migrated
   - [ ] Tournament services can record participation
   - [ ] Stats update signals wired (even if UI not complete)

4. **Quality Metrics:**
   - [ ] Test coverage ≥75% for user_profile app
   - [ ] No P1+ bugs in User Profile system
   - [ ] Privacy enforcement verified (grep audit passes)

5. **Performance Validated:**
   - [ ] Profile page load <300ms
   - [ ] Tournament registration flow <500ms end-to-end
   - [ ] No N+1 query issues introduced

**Minimum Safe Subset:**
- UP-1 (Invariant) is non-negotiable → MUST be complete
- UP-2 (Public ID) is optional → can defer if needed
- UP-3 (Privacy) is non-negotiable → MUST be complete
- UP-4 (Economy) is critical → MUST be stable (not necessarily 100% complete)
- UP-5 (Stats) can be partially complete → must support tournament participation tracking

**Decision Authority:** Engineering Manager in consultation with Product Owner

---

## 6. Required Tracker Updates (Each Milestone)

**After Each Phase Gate Passes:**

### Status Tracker Update (IMPLEMENTATION_STATUS.md)
- Mark phase as "Completed" with completion date
- Update progress percentage (calculate based on phases complete)
- Log any blockers encountered and resolved
- Update "Next Steps" section

### Decisions Tracker Update (DECISIONS.md)
- Add ADR for any significant design decisions made during phase
- Example ADRs:
  - "Why we chose atomic F() updates for counters"
  - "Why reconciliation runs at 3 AM UTC"
  - "Why activity timeline excludes match results"
- Include context, decision, and consequences

### Backlog Update (IMPLEMENTATION_BACKLOG.md)
- Mark completed backlog items as DONE
- Add any new items discovered during implementation
- Re-prioritize remaining items if needed
- Update dependencies (if implementation order changed)

**Update Frequency:**
- Status Tracker: Daily (during active development)
- Decisions Tracker: As decisions are made (real-time)
- Backlog: After each phase completion (weekly)

**Commit Message Format:**
```
[UP-X] Phase X complete: [short description]

- Gate checks passed
- Tests passing (coverage X%)
- Deployed to staging
- Updated trackers

Closes #[issue-number]
```

---

## 7. Rollback Plan

**If Major Issue Discovered After Deployment:**

**Immediate Actions:**
1. Assess severity (data loss? user impact? security breach?)
2. If P0 → revert deployment immediately
3. If P1 → evaluate fix-forward vs rollback

**Rollback Steps:**
1. Revert code deployment (Git revert + redeploy)
2. Roll back migrations (if reversible)
3. Restore profile data from backup (if data corruption)
4. Notify users if data loss occurred

**Post-Rollback:**
- Root cause analysis (RCA document)
- Fix issue in development environment
- Re-test thoroughly before re-deploy
- Update safety gates to prevent recurrence

**Non-Reversible Changes:**
- Profile backfill (cannot un-create profiles)
- Public ID assignment (cannot un-assign)
- Audit log entries (immutable by design)

---

## Final Checklist (Before Production Deploy)

- [ ] All phases (UP-1 through UP-6) complete
- [ ] All safety gates passed
- [ ] Security penetration test signed off
- [ ] Staging environment stable for 48 hours
- [ ] Rollback plan tested
- [ ] Monitoring dashboards configured
- [ ] Alerts configured (drift, privacy bypass, rate limits)
- [ ] Documentation updated (README, runbooks)
- [ ] Team trained on new architecture
- [ ] Product owner approves deployment

---

**End of Document**
