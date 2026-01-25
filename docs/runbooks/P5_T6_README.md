# P5-T6: Staging Dual-Write Testing - Documentation Index

**Status:** Documentation Complete - Awaiting Manual Execution  
**Created:** 2026-01-25  
**Phase:** Phase 5 (Data Migration)  

---

## 📋 Overview

This directory contains all documentation needed to execute **P5-T6: Staging Testing / Enable Dual-Write**. The task enables dual-write functionality in staging and validates that vNext write operations correctly create legacy shadow rows.

**Objective:** Prove that dual-write hooks work correctly in staging before production enablement.

---

## 📚 Documentation Files

### 1. **Quick Start Guide** ⚡
**File:** [P5_T6_QUICK_START.md](./P5_T6_QUICK_START.md)  
**Use When:** You want the TL;DR version (commands only)  
**Duration:** 5 minutes to read  

Quick reference with:
- Essential commands (copy-paste ready)
- Pre-flight checklist
- Test flow summary
- Emergency rollback (5-minute procedure)
- Troubleshooting table

**Start Here if:** You've done this before or need quick reference.

---

### 2. **Comprehensive Runbook** 📖
**File:** [P5_T6_STAGING_DUAL_WRITE_TESTING.md](./P5_T6_STAGING_DUAL_WRITE_TESTING.md)  
**Use When:** First-time execution or detailed guidance needed  
**Duration:** 2-3 hours to execute  

Complete step-by-step guide with:
- **Phase 1:** Baseline validation report (before testing)
- **Phase 2:** Enable dual-write flags (Kubernetes/Docker/env methods)
- **Phase 3:** End-to-end smoke tests (5 test flows + verification)
- **Phase 4:** After validation report + delta analysis
- **Phase 5:** Performance validation (query counts, latency)
- **Phase 6:** Failure simulation (optional, strict mode behavior)
- **Phase 7:** Rollback procedures
- **Phase 8:** Documentation & handoff

Includes:
- ✅ Success criteria checklist
- 🔍 SQL queries for manual verification
- 🐛 Troubleshooting guide
- 📊 Validation report interpretation
- 📞 Emergency contacts

**Start Here if:** This is your first time or you need detailed instructions.

---

### 3. **Rollback Procedures** 🚨
**File:** [DUAL_WRITE_ROLLBACK.md](./DUAL_WRITE_ROLLBACK.md)  
**Use When:** Emergency issues detected, need to revert changes  
**Duration:** < 5 minutes per scenario  

Emergency procedures for:
- **Scenario 1:** Disable dual-write (fastest, <5 minutes)
- **Scenario 2:** Disable strict mode (partial rollback)
- **Scenario 3:** Cleanup test data (transaction-safe SQL)
- **Scenario 4:** Restore from backup (nuclear option)
- **Scenario 5:** Block all legacy writes (emergency enforcement)

Includes:
- 🚦 Rollback decision matrix (symptom → action → urgency)
- ✅ Verification checklist
- 📢 Communication template
- 📞 Emergency contacts

**Start Here if:** Something went wrong and you need to rollback quickly.

---

### 4. **Automation Script** 🤖
**File:** [../../scripts/staging_validation_test.py](../../scripts/staging_validation_test.py)  
**Use When:** Automating validation report generation and comparison  
**Duration:** 5 minutes setup + manual testing time  

Python script that:
- Generates baseline validation report
- Prompts for manual testing execution
- Generates after validation report
- Compares before/after with delta analysis
- Generates markdown summary report

**Usage:**
```bash
python scripts/staging_validation_test.py --env=staging-k8s
```

Options:
- `--env`: Environment type (`staging-k8s`, `staging-docker`, `local`)
- `--output-dir`: Report output directory (default: `./logs`)
- `--skip-before`: Skip baseline report (use existing file)

**Start Here if:** You want automated report generation and comparison.

---

## 🎯 Execution Workflow

```
┌─────────────────────────────────────────────────┐
│ 1. PRE-FLIGHT                                   │
│    □ Read Quick Start Guide                     │
│    □ Verify staging access                      │
│    □ Review rollback procedures                 │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 2. BASELINE                                     │
│    □ Run validation report (before)             │
│    □ Save baseline metrics                      │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 3. ENABLE DUAL-WRITE                            │
│    □ Set TEAM_VNEXT_DUAL_WRITE_ENABLED=true     │
│    □ Set TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=false│
│    □ Restart pods                               │
│    □ Verify flags active                        │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 4. EXECUTE TESTS                                │
│    □ Create team (API/UI)                       │
│    □ Add member                                 │
│    □ Update member role                         │
│    □ Update team settings                       │
│    □ Remove member                              │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 5. VERIFY                                       │
│    □ Check logs (dual_write_scheduled)          │
│    □ Verify database shadow rows                │
│    □ Check TeamMigrationMap entries             │
│    □ Confirm no performance regression          │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 6. VALIDATE                                     │
│    □ Run validation report (after)              │
│    □ Compare before/after                       │
│    □ Analyze delta (coverage %, mappings)       │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 7. DOCUMENT                                     │
│    □ Generate summary report                    │
│    □ Fill in manual sections                    │
│    □ Update tracker                             │
│    □ Notify team                                │
└─────────────────────────────────────────────────┘
```

---

## 🔑 Key Environment Variables

| Variable | Staging Value | Purpose |
|----------|---------------|---------|
| `TEAM_VNEXT_DUAL_WRITE_ENABLED` | `true` | Enable dual-write to legacy |
| `TEAM_VNEXT_DUAL_WRITE_STRICT_MODE` | `false` | Log-only failures (safe) |
| `TEAM_VNEXT_LEGACY_WRITE_BLOCKED` | `true` | Block direct legacy writes |
| `TEAM_VNEXT_ADAPTER_ENABLED` | `true` | Enable vNext routing |
| `TEAM_VNEXT_ROUTING_MODE` | `vnext_primary` | Route to vNext by default |

---

## 📊 Success Criteria

- [ ] Dual-write flags enabled in staging
- [ ] All 5 test flows executed successfully
- [ ] Logs show `dual_write_scheduled` events for each operation
- [ ] Legacy shadow rows exist in database (TeamMigrationMap + legacy tables)
- [ ] Validation report shows increased mapping coverage
- [ ] Dual-write health section appears in report (was null before)
- [ ] No performance regressions detected (query count, latency)
- [ ] Zero inline legacy writes detected (all in on_commit hooks)
- [ ] Rollback procedures tested and documented
- [ ] Tracker updated with complete results

---

## ⚠️ Important Notes

1. **Staging Only:** This task is for staging environment ONLY. Do NOT run in production.
2. **Strict Mode OFF:** Start with `STRICT_MODE=false` for safety. Failures log but don't crash.
3. **Rollback Ready:** Review rollback procedures BEFORE starting. Quick disable is < 5 minutes.
4. **Manual Execution:** AI cannot execute this task. Human team member required.
5. **No Scope Creep:** Follow runbook exactly. Don't add extra testing or changes.

---

## 🆘 Emergency Rollback (5-Minute Procedure)

**If anything goes wrong:**

```bash
# 1. Disable dual-write immediately
kubectl set env deployment/deltacrown-web \
  TEAM_VNEXT_DUAL_WRITE_ENABLED=false \
  -n deltacrown

# 2. Restart pods
kubectl rollout restart deployment/deltacrown-web -n deltacrown

# 3. Verify disabled
kubectl exec -it <pod> -n deltacrown -- \
  python manage.py shell -c "
from django.conf import settings
print(f'Dual-Write: {getattr(settings, \"TEAM_VNEXT_DUAL_WRITE_ENABLED\", False)}')
"
# Expected: False

# 4. Notify team
# Post in #team-vnext-migration: "Dual-write disabled in staging due to [REASON]"
```

**Full rollback procedures:** See [DUAL_WRITE_ROLLBACK.md](./DUAL_WRITE_ROLLBACK.md)

---

## 📞 Support & Contacts

- **Questions:** Slack #team-vnext-migration
- **Issues:** Create ticket in Jira (project: VNEXT)
- **On-Call:** @oncall-engineering (Slack)
- **DevOps:** @devops-lead (Slack)
- **Documentation Issues:** Update this README and notify team

---

## 📅 Execution Tracking

**Planned Execution Date:** [TO BE SCHEDULED]  
**Assigned To:** [TEAM MEMBER NAME]  
**Status:** Documentation Complete - Awaiting Execution  

**Execution Log:**
- [ ] Baseline report captured
- [ ] Flags enabled
- [ ] Tests executed
- [ ] Verification complete
- [ ] After report captured
- [ ] Summary report generated
- [ ] Tracker updated

---

## 🔄 Related Tasks

- **Previous:** P5-T5 - Hook Integration (✅ Completed 2026-01-25)
- **Current:** P5-T6 - Staging Testing (📋 Documentation Complete)
- **Next:** Phase 6 Unblock Preparation (⏸️ Awaiting P5-T6 completion)

---

## 📝 Documentation Updates

| Date | Author | Change |
|------|--------|--------|
| 2026-01-25 | AI Assistant | Initial documentation created |
| [Date] | [Name] | Execution results added |

---

**Ready to Execute?** Start with [P5_T6_QUICK_START.md](./P5_T6_QUICK_START.md) for quick reference or [P5_T6_STAGING_DUAL_WRITE_TESTING.md](./P5_T6_STAGING_DUAL_WRITE_TESTING.md) for comprehensive guide.

**Questions?** Review [DUAL_WRITE_ROLLBACK.md](./DUAL_WRITE_ROLLBACK.md) for emergency procedures or contact team in Slack.

**Good luck! 🚀**
