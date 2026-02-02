# vNext Documentation Archive

Historical documentation from the vNext migration and database investigation.

---

## Important Documents

### Current / Active

**[cleanup-and-db-normalization.md](cleanup-and-db-normalization.md)**  
*Date: 2026-02-02*  
**Read this first!** Final cleanup and simplified database configuration. Explains the current production-like setup.

---

## Historical / Reference

**[db-env-fix-schema-repair.md](db-env-fix-schema-repair.md)**  
Investigation of database environment selection issues and schema problems. Shows the complex auto-switching logic that was simplified in the cleanup.

**[db-fix-summary.md](db-fix-summary.md)**  
Quick before/after summary of the database fixes. Good for understanding what changed and why.

**[phase3a-e5-migration-fix.md](phase3a-e5-migration-fix.md)**  
Phase 3A-E5 migration truth and fixes. Competition app migration dependencies and table name corrections.

**[incident-neon-assessment.md](incident-neon-assessment.md)**  
Neon database incident assessment. Investigation of unexpected behavior and migration issues.

---

## What's in docs/ops/

**[../ops/neon-reset.md](../ops/neon-reset.md)**  
Step-by-step guide to reset Neon database and re-seed. Use when you need a fresh start.

---

## Timeline

1. **Phase 3A-E5** - Competition app implementation, migration issues discovered
2. **Incident Response** - Neon database assessment, table mismatches found
3. **Investigation** - Complex database selection logic created to solve issues
4. **Cleanup (2026-02-02)** - Simplified to production-like config, removed temporary files

---

## Key Takeaways

### What We Learned

1. **Keep it simple** - Production should use one DATABASE_URL for everything
2. **Tests separate** - Always use local postgres (DATABASE_URL_TEST)
3. **Clean as you go** - Don't let temporary scripts accumulate
4. **Document the why** - Future you will thank present you

### What Was Fixed

- ✅ Simplified database configuration (no more auto-switching)
- ✅ Tests hardened to refuse remote databases
- ✅ Repository cleaned (40+ temporary files removed)
- ✅ Migration guard simplified (single clean message)
- ✅ Seed commands created and verified idempotent

### What Changed

**Before:**
- Complex DATABASE_URL_DEV auto-switching
- Temporary scripts everywhere
- Root directory cluttered with reports
- Tests could accidentally run on Neon

**After:**
- DATABASE_URL for everything (Neon)
- DATABASE_URL_TEST for tests (local postgres)
- Clean repository structure
- Tests refuse remote databases

---

## Archive Policy

Keep only:
- Final summaries (cleanup-and-db-normalization.md)
- Major incident reports
- Architectural decision records

Move to archive/ or delete:
- Temporary investigation notes
- Duplicate reports
- WIP documents

---

Last updated: 2026-02-02
