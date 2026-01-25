# P5-T6 Quick Start Guide

**Task:** Staging Dual-Write Testing  
**Time Required:** 2-3 hours  
**Risk Level:** Low (staging only)  

---

## 🚀 Quick Start (TL;DR)

```bash
# 1. Capture baseline
kubectl exec -it <pod> -- python manage.py vnext_validation_report --format=json > baseline.json

# 2. Enable dual-write
kubectl set env deployment/deltacrown-web TEAM_VNEXT_DUAL_WRITE_ENABLED=true -n deltacrown
kubectl rollout restart deployment/deltacrown-web -n deltacrown

# 3. Test (create team, add member, update settings)
curl -X POST https://staging.deltacrown.gg/api/vnext/teams/create/ -H "Authorization: Bearer $TOKEN" -d '{"name":"Test Team","game_id":1,"region":"NA"}'

# 4. Verify logs
kubectl logs -f deployment/deltacrown-web | grep dual_write

# 5. Check database
psql $DB_URL -c "SELECT * FROM organizations_teammigrationmap ORDER BY id DESC LIMIT 5;"

# 6. Capture after state
kubectl exec -it <pod> -- python manage.py vnext_validation_report --format=json > after.json

# 7. Compare & update tracker
python scripts/staging_validation_test.py --env=staging-k8s
```

---

## 📚 Full Documentation

- **Comprehensive Runbook:** [docs/runbooks/P5_T6_STAGING_DUAL_WRITE_TESTING.md](../runbooks/P5_T6_STAGING_DUAL_WRITE_TESTING.md)
- **Rollback Procedures:** [docs/runbooks/DUAL_WRITE_ROLLBACK.md](../runbooks/DUAL_WRITE_ROLLBACK.md)
- **Automation Script:** [scripts/staging_validation_test.py](../../scripts/staging_validation_test.py)

---

## ✅ Pre-Flight Checklist

- [ ] Staging environment healthy
- [ ] Database backups current
- [ ] SSH/kubectl access verified
- [ ] Auth tokens ready for API testing
- [ ] Rollback plan reviewed

---

## 🧪 Test Flows

1. **Create Team** → Verify TeamMigrationMap + legacy Team row created
2. **Add Member** → Verify legacy TeamMembership row created
3. **Update Role** → Verify legacy membership role updated
4. **Update Settings** → Verify legacy team settings updated
5. **Remove Member** → Verify legacy membership inactivated

---

## 🔍 What to Look For

**Logs (Success):**
```
INFO ... event_type=team_created team_id=123
INFO ... event_type=dual_write_scheduled operation=sync_team_created team_id=123
INFO ... Dual-write scheduled for team creation: 123
```

**Logs (Failure - Expected with strict mode OFF):**
```
ERROR ... event_type=dual_write_failed operation=sync_team_created exception_type=...
```

**Database:**
```sql
-- Should have matching rows
SELECT * FROM organizations_team WHERE id = 123;
SELECT * FROM organizations_teammigrationmap WHERE vnext_team_id = 123;
SELECT * FROM teams_team WHERE id = (SELECT legacy_team_id FROM organizations_teammigrationmap WHERE vnext_team_id = 123);
```

---

## 🚨 Emergency Rollback (< 5 minutes)

```bash
# Disable dual-write
kubectl set env deployment/deltacrown-web TEAM_VNEXT_DUAL_WRITE_ENABLED=false -n deltacrown
kubectl rollout restart deployment/deltacrown-web -n deltacrown

# Verify
kubectl exec -it <pod> -- python manage.py shell -c "from django.conf import settings; print(getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_ENABLED', False))"
# Expected: False
```

---

## 📊 Expected Results

**Before Testing:**
- Legacy Teams: ~100
- vNext Teams: ~5
- Mapped Teams: ~0
- Coverage: ~0%

**After Testing:**
- vNext Teams: +5 (new test teams)
- Mapped Teams: +5 (dual-write created mappings)
- Coverage: Should increase or stay at 100%
- Dual-Write Health: Section should appear (was null before)

---

## 📝 After Testing

1. Run: `python scripts/staging_validation_test.py --env=staging-k8s`
2. Review generated summary report
3. Fill in manual sections (issues, performance)
4. Update tracker with results
5. Cleanup test data (optional, see rollback runbook)

---

## ❓ Troubleshooting

| Issue | Quick Fix |
|-------|-----------|
| Flags not working | `kubectl rollout restart deployment/deltacrown-web` |
| No shadow rows | Check logs for `dual_write_failed`, verify bypass context |
| Requests failing | `kubectl set env deployment/deltacrown-web TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=false` |
| Performance slow | Disable dual-write, investigate separately |

---

## 📞 Need Help?

- **Full Runbook:** See [P5_T6_STAGING_DUAL_WRITE_TESTING.md](../runbooks/P5_T6_STAGING_DUAL_WRITE_TESTING.md) for detailed procedures
- **Rollback:** See [DUAL_WRITE_ROLLBACK.md](../runbooks/DUAL_WRITE_ROLLBACK.md) for emergency procedures
- **Questions:** Slack #team-vnext-migration

---

**Good luck! 🎉**
