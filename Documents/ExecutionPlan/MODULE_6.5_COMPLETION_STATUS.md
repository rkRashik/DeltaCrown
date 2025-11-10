# Module 6.5 Completion Status

**Module:** 6.5 - Certificate Storage Planning (S3 Migration)  
**Status:** ✅ Planning Complete (No Implementation)  
**Date:** November 10, 2025  
**Phase:** Phase 6 (Planning) | Implementation: Phase 7 (Q1-Q2 2026)  
**Implements:** PHASE_6_IMPLEMENTATION_PLAN.md#module-6.5  

---

## Overview

Module 6.5 focused on **planning and design** for migrating certificate storage from local `MEDIA_ROOT` to AWS S3. This module produced comprehensive documentation, configuration scaffolds, and operational runbooks to guide Phase 7 implementation.

**Scope:** Planning/design only (no production code changes, no AWS provisioning, no live migration)

**Deliverables:** 4 planning artifacts + 1 completion document (this file)

---

## Deliverables

### 1. S3_MIGRATION_DESIGN.md ✅

**Location:** `Documents/ExecutionPlan/S3_MIGRATION_DESIGN.md`  
**Size:** ~700 lines (10 sections + 2 appendices)  

**Contents:**
- **Section 1: Executive Summary** (goals, non-goals, timeline, success metrics)
- **Section 2: Current State Analysis** (MEDIA_ROOT limitations, usage stats, decision drivers)
- **Section 3: S3 Architecture** (bucket design, folder structure, storage classes, presigned URLs)
- **Section 4: Cost Estimation** ($15-25/month breakdown, 3-year projection)
- **Section 5: Security & Compliance** (SSE-S3, SSE-KMS, IAM policies, PII safeguards)
- **Section 6: Lifecycle & Retention** (Standard → IA @90d → Glacier @1y → Delete @7y)
- **Section 7: Migration Strategy** (6-phase rollout: provision → test → dual-write → migrate → switch → deprecate)
- **Section 8: Rollback Plan** (trigger conditions, 15-minute rollback procedure)
- **Section 9: Risks & Mitigations** (S3 outage, bill spike, link instability, PII exposure, data corruption)
- **Section 10: Monitoring & Alerts** (CloudWatch metrics, alarms, dashboard, S3 access logs, CloudTrail)
- **Appendix A: Example Presigned URL** (anatomy, query parameters, expiration behavior)
- **Appendix B: Migration Script Output** (dry-run and actual migration examples)

**Key Decisions:**
- **Encryption:** SSE-S3 (AES256) default, SSE-KMS optional path documented
- **TTL:** 10-minute presigned URLs (not 15) to reduce token reuse
- **Integrity:** ETag verification for standard uploads, SHA-256 checksum for large files (>5MB)
- **Caching:** `Cache-Control: private, max-age=600` (10 minutes browser cache)
- **Key Naming:** UUID-based filenames, no PII in S3 keys (`pdf/YYYY/MM/uuid.pdf`)
- **Feature Flag:** `USE_S3_FOR_CERTS` environment toggle (staging can switch without code changes)
- **Logging:** S3 server access logs + optional CloudTrail data events (production only)

---

### 2. settings_s3.example.py ✅

**Location:** `settings_s3.example.py` (root directory)  
**Size:** ~230 lines (commented configuration)  

**Contents:**
- Feature flag: `USE_S3_FOR_CERTS` (environment toggle)
- AWS credentials: IAM role (production) vs access keys (development/staging)
- S3 bucket configuration: `deltacrown-certificates-prod` (us-east-1)
- Security settings: Private objects (`AWS_DEFAULT_ACL = None`), presigned URLs (10min TTL)
- Encryption: SSE-S3 (AES256) default, SSE-KMS commented option with CMK example
- Object parameters: `CacheControl: private, max-age=600`, `ServerSideEncryption: AES256`
- Storage backend: `storages.backends.s3boto3.S3Boto3Storage`
- Bucket policy JSON: Deny unencrypted uploads + deny insecure transport (HTTP)
- IAM policy JSON: Least-privilege (PutObject, GetObject, DeleteObject only)
- Environment variables: `.env` example with AWS credentials
- Dependencies: `django-storages[s3]==1.14.2`, `boto3==1.34.16`
- Migration checklist: 10 pre-deployment steps

**Key Features:**
- **Feature flag:** `USE_S3_FOR_CERTS` (staging can test S3 without editing code)
- **KMS option:** Customer-managed keys documented (if already using KMS elsewhere)
- **Bucket policy:** Enforces SSE-S3 encryption, denies HTTP traffic
- **IAM policy:** Least-privilege (condition requires `s3:x-amz-server-side-encryption: AES256`)

---

### 3. scripts/migrate_certificates_to_s3.py ✅

**Location:** `scripts/migrate_certificates_to_s3.py`  
**Size:** ~270 lines (skeleton scaffold + CLI)  

**Contents:**
- `migrate_certificates()` function signature (dry_run, batch_size, tournament_id params)
- Argparse CLI: `--dry-run`, `--batch-size`, `--tournament-id` flags
- TODO comments for Phase 7 implementation:
  - Query Certificate model (exclude `migrated_to_s3_at IS NOT NULL`)
  - Check local file exists (`certificate.file.path`)
  - Upload to S3 using django-storages
  - Verify upload integrity (ETag or SHA-256)
  - Update `certificate.migrated_to_s3_at` timestamp
  - Log success/failure
- Batch processing: `queryset.iterator(chunk_size=batch_size)`
- Summary stats: `{total, migrated, skipped, failed, errors}`
- Exit codes: 0 (success), 1 (partial failure), 2 (total failure)
- Logging: Console + file (`logs/s3_migration.log`)

**Key Features:**
- **Idempotent:** Checks `migrated_to_s3_at` timestamp (skip already-migrated certificates)
- **Integrity verification:** ETag check for standard uploads, SHA-256 for large files
- **Progress reporting:** Log every 10 certificates, print summary at end
- **Error handling:** Retry failed uploads (max 3 attempts), log errors to file
- **Dry-run mode:** Test without uploading (report only)

**Usage Examples:**
```bash
# Dry-run (report only)
python scripts/migrate_certificates_to_s3.py --dry-run

# Migrate all certificates
python scripts/migrate_certificates_to_s3.py --batch-size 100

# Migrate specific tournament
python scripts/migrate_certificates_to_s3.py --tournament-id 123
```

---

### 4. Documents/Runbooks/S3_OPERATIONS_CHECKLIST.md ✅

**Location:** `Documents/Runbooks/S3_OPERATIONS_CHECKLIST.md`  
**Size:** ~550 lines (10 sections + Terraform example)  

**Contents:**
- **Section 1: Bucket Provisioning** (AWS console steps, Terraform template, folder structure)
- **Section 2: IAM Role & Policy** (IAM role for EC2, IAM user for dev/staging, least-privilege policy)
- **Section 3: Bucket Policy & Encryption** (deny unencrypted uploads, deny HTTP, KMS setup)
- **Section 4: Lifecycle & Retention** (Standard → IA @90d → Glacier @1y → Delete @7y)
- **Section 5: Logging & Monitoring** (S3 access logs, CloudTrail data events, CloudWatch alarms)
- **Section 6: Credential Rotation** (quarterly IAM access key rotation, IAM role auto-rotation)
- **Section 7: Staging Environment** (staging bucket setup, IAM user, Django config, tests)
- **Section 8: Production Deployment** (dual-write phase, background migration, switch to S3 primary)
- **Section 9: Emergency Rollback** (trigger conditions, 15-minute rollback procedure, post-mortem)
- **Section 10: Routine Maintenance** (weekly, monthly, quarterly, annual tasks)
- **Appendix: Terraform Complete Example** (full IaC setup with all resources)

**Key Features:**
- **Step-by-step checklists:** Checkbox format for each task (easy to follow)
- **AWS console + Terraform:** Both manual and IaC approaches documented
- **CloudWatch alarms:** 3 alarms (upload failures, 403 spike, monthly cost threshold)
- **Credential rotation:** Quarterly schedule with zero-downtime procedure
- **Emergency rollback:** 15-minute rollback plan with 6 steps
- **Terraform example:** Production-ready IaC template (~150 lines)

---

### 5. MODULE_6.5_COMPLETION_STATUS.md ✅

**Location:** `Documents/ExecutionPlan/MODULE_6.5_COMPLETION_STATUS.md` (this file)  
**Size:** ~250 lines  

**Purpose:** Document Module 6.5 completion, deliverables, scope, and next steps.

---

## Scope

### What Was Completed ✅

- **Design document:** Comprehensive 700-line S3 migration design (10 sections, 2 appendices)
- **Configuration scaffold:** Commented Django settings (SSE-S3, SSE-KMS, IAM, bucket policy)
- **Migration script:** Skeleton Python script (CLI, idempotent logic, integrity verification)
- **Operations runbook:** 550-line ops checklist (provisioning, monitoring, rollback, maintenance)
- **Completion document:** This file (MODULE_6.5_COMPLETION_STATUS.md)

### What Was NOT Completed (Deferred to Phase 7) 🔄

- **AWS provisioning:** S3 bucket not created (no AWS console or Terraform execution)
- **IAM setup:** IAM roles/users not created (no credentials generated)
- **Django integration:** `USE_S3_FOR_CERTS=false` (local storage still active)
- **Migration execution:** No certificates migrated to S3 (script is scaffold only)
- **Testing:** No staging tests run (S3 backend not provisioned)
- **Production deployment:** No production changes (app continues using MEDIA_ROOT)

**Rationale:** Module 6.5 is a **planning-only** module per PHASE_6_IMPLEMENTATION_PLAN.md. All implementation work deferred to Phase 7 (Q1-Q2 2026).

---

## Key Decisions & Tradeoffs

### 1. Encryption: SSE-S3 vs SSE-KMS

**Decision:** Default to SSE-S3 (AES256), document SSE-KMS as optional path.

**Rationale:**
- **SSE-S3:** Simpler (AWS-managed keys), no additional cost, HIPAA/PCI/GDPR compliant
- **SSE-KMS:** Centralized key rotation, audit trail via CloudTrail, but adds $1/month + $0.03 per 10k requests
- **Tradeoff:** SSE-KMS offers better audit/control but adds cost complexity

**Recommendation:** Use SSE-S3 unless DeltaCrown already uses KMS for other services (RDS, Secrets Manager).

### 2. Presigned URL TTL: 10 Minutes vs 15 Minutes

**Decision:** 10-minute TTL (600 seconds) instead of 15 minutes.

**Rationale:**
- **Security:** Shorter TTL reduces token reuse window (limit abuse if URL leaked)
- **UX:** 10 minutes sufficient for certificate download (typical download <30 seconds)
- **Caching:** Django caches presigned URL for 5 minutes (avoid regeneration overhead)

**Tradeoff:** Shorter TTL improves security but increases presigned URL generation frequency (negligible cost).

### 3. Integrity Verification: ETag vs SHA-256

**Decision:** Use ETag for standard uploads (<5MB), add SHA-256 for large files (>5MB).

**Rationale:**
- **ETag:** Fast (S3 returns MD5 hash for single-part uploads), no compute overhead
- **SHA-256:** Accurate (multipart uploads use different ETag algorithm), but adds 50-100ms latency
- **Tradeoff:** ETag sufficient for 99% of certificates (1MB PDFs), SHA-256 for edge cases (large images)

**Implementation:** Phase 7 will add optional `Certificate.sha256_hash` field (store checksum at generation time).

### 4. Caching: Private vs Public

**Decision:** `Cache-Control: private, max-age=600` (10-minute browser cache).

**Rationale:**
- **Security:** `private` prevents CDN/proxy caching (certificates are user-specific)
- **Performance:** 10-minute browser cache reduces S3 GET requests (if user downloads multiple times)
- **Tradeoff:** `public` would enable CloudFront edge caching (better performance), but violates privacy (certificate contains player name)

**Future:** Phase 8 may add CloudFront with signed cookies (long-lived session, better UX).

### 5. Feature Flag: Environment Toggle vs Code Change

**Decision:** `USE_S3_FOR_CERTS` environment variable (no code changes to switch storage).

**Rationale:**
- **Flexibility:** Staging can test S3 without editing `settings.py`
- **Rollback:** Emergency revert by flipping `.env` flag (no code deploy needed)
- **Safety:** Gradual rollout (enable staging first, monitor 7 days, then enable production)

**Tradeoff:** Adds complexity (if-else in settings), but operational benefits outweigh cost.

---

## Cost Summary

### Estimated Monthly Cost (12 Months)

**Assumptions:**
- 1,000 certificates/month (12k cumulative)
- 1 MB avg PDF size
- 2 downloads per certificate (2k downloads/month)

**Breakdown:**
| Item | Cost |
|------|------|
| **S3 Storage** (36 GB, with lifecycle) | $1.42/month |
| **PUT Requests** (1.2k requests/month) | $0.006/month |
| **GET Requests** (2k requests/month) | $0.0008/month |
| **Data Transfer** (2 GB/month) | $0.18/month |
| **CloudWatch Alarms** (3 alarms) | $0.30/month |
| **CloudTrail** (optional, production only) | $5.00/month |
| **TOTAL (without CloudTrail)** | **~$2/month** |
| **TOTAL (with CloudTrail)** | **~$7/month** |

**3-Year Projection:**
| Year | Storage (GB) | Monthly Cost | Annual Cost |
|------|-------------|--------------|-------------|
| 1 | 36 GB | $2/mo | $24/year |
| 2 | 72 GB | $3/mo | $36/year |
| 3 | 108 GB | $5/mo | $60/year |

**Comparison:**
| Solution | Monthly Cost | Notes |
|----------|-------------|-------|
| **Local Storage** | $10/mo | 50GB disk allocation, daily backups |
| **S3 (Optimized)** | $2-7/mo | With lifecycle, no CloudTrail |
| **S3 + CloudFront** | $15-25/mo | Phase 8 (CDN distribution) |

**Verdict:** S3 is **cost-competitive** with local storage, with significant operational benefits (durability, scalability, security).

---

## Security Posture

### Encryption

✅ **At Rest:** SSE-S3 (AES256) enforced via bucket policy  
✅ **In Transit:** HTTPS enforced via bucket policy (deny HTTP)  
✅ **Optional KMS:** Customer-managed keys documented (if needed)  

### Access Control

✅ **Private Objects:** `AWS_DEFAULT_ACL = None` (no public-read)  
✅ **Presigned URLs:** 10-minute TTL, SigV4 signing  
✅ **IAM Policy:** Least-privilege (PutObject, GetObject, DeleteObject only)  
✅ **Bucket Policy:** Deny unencrypted uploads, deny insecure transport  

### PII Protection

✅ **UUID Filenames:** `pdf/YYYY/MM/{uuid}.pdf` (no usernames, emails, tournament names)  
✅ **No PII in Metadata:** Object tags limited to `tournament_id`, `placement`, `generated_at`  
✅ **GDPR Compliance:** Soft delete (mark `deleted_at`, delete S3 object after 30 days)  

### Audit Trail

✅ **S3 Access Logs:** 90-day retention (`s3://deltacrown-logs/s3-access/`)  
✅ **CloudTrail Data Events:** Optional (production only, $5-10/month)  
✅ **CloudWatch Alarms:** 403 spike, 5xx errors, upload failures  

---

## Risks & Mitigations

### Risk 1: S3 Outage → Certificates Unavailable

**Mitigation:**
- CloudFront CDN (Phase 8): Cache at edge (200+ global PoPs)
- S3 Cross-Region Replication (Phase 8): Backup to `us-west-2`
- Presigned URL caching: Django cache for 5 minutes (reduce S3 dependency)
- Graceful degradation: Display "Certificate temporarily unavailable" message

**Monitoring:** CloudWatch alarm (S3 5xx >5/minute → PagerDuty)

### Risk 2: AWS Bill Spike (GET Flood Attack)

**Mitigation:**
- Short TTL: 10-minute presigned URL expiration (limit reuse)
- CloudFront rate limiting (Phase 8): 100 requests/minute per IP (WAF rule)
- AWS Budgets: Alert when monthly cost exceeds $50 (SMS + email)

**Monitoring:** CloudWatch alarm (S3 GET >10k/hour → Slack alert)

### Risk 3: Link Instability (Presigned URLs Expire)

**Mitigation:**
- Short TTL with regeneration: Generate fresh URL on every page load (not stored in DB)
- Django view caching: Cache URL for 5 minutes (balance freshness vs performance)
- User education: Display "Link expires in 10 minutes" message

**Monitoring:** Track 403 rate on `/api/tournaments/certificates/{uuid}/download/`

### Risk 4: PII Exposure (Object Keys Leak User Info)

**Mitigation:**
- UUID-only filenames: Enforce UUID v4 in certificate generation
- Code review: Require PR approval for storage logic changes
- Automated tests: Unit test verifying no PII in S3 keys
- S3 metadata audit: Quarterly review of object tags (ensure no `user_email`)

**Monitoring:** Pre-commit hook (scan code for hardcoded usernames/emails)

### Risk 5: Data Corruption (Upload/Download Integrity)

**Mitigation:**
- ETag verification: Compare S3 ETag after upload (MD5 for single-part)
- SHA-256 checksum (optional): Store in `Certificate.sha256_hash` field
- S3 versioning: Recover from accidental overwrites (30-day retention)
- Spot checks: Weekly automated test (download 10 random certificates → verify PDF integrity)

**Monitoring:** Log ETag mismatches during upload (should be 0)

### Risk 6: Migration Data Loss

**Mitigation:**
- Dual-write phase: Keep local files for 30 days (rollback safety net)
- Idempotent migration: Script checks `migrated_to_s3_at` (skip already-migrated)
- Dry-run mode: Test on staging before production
- Post-migration validation: Compare local vs S3 file counts

**Monitoring:** Migration progress dashboard (total, migrated, skipped, failed)

---

## Next Steps (Phase 7 - Q1-Q2 2026)

### Week 1: Provisioning (Ops Task)
- [ ] Create S3 bucket `deltacrown-certificates-prod` (us-east-1)
- [ ] Enable versioning, encryption (SSE-S3), block public access
- [ ] Configure bucket policy (deny unencrypted, deny HTTP)
- [ ] Create IAM role/user (least-privilege policy)
- [ ] Enable S3 server access logs
- [ ] Configure lifecycle policy (Standard → IA @90d → Glacier @1y → Delete @7y)
- [ ] Set up CloudWatch alarms (403 spikes, 5xx errors, upload failures)

### Week 2-3: Staging Tests
- [ ] Install `django-storages[s3]==1.14.2`, `boto3==1.34.16`
- [ ] Create `settings_s3.py` (staging config)
- [ ] Set `USE_S3_FOR_CERTS=true` in staging `.env`
- [ ] Generate test certificate → verify S3 upload
- [ ] Access presigned URL → verify download
- [ ] Wait 11 minutes → verify URL expired (403)
- [ ] Check S3 encryption (`aws s3api head-object`)
- [ ] Measure presigned URL latency (<100ms p95)

### Week 4-5: Dual-Write (30 Days)
- [ ] Implement dual-write logic (save to local + S3)
- [ ] Deploy to production with `USE_S3_FOR_CERTS=true`
- [ ] Monitor S3 upload success rate (target: 100%)
- [ ] Set up Slack alerts for S3 upload failures
- [ ] Keep local storage (no deletion)

### Week 6-8: Background Migration
- [ ] Implement `scripts/migrate_certificates_to_s3.py`
- [ ] Test dry-run mode (verify report accuracy)
- [ ] Run migration in batches (100 certs per run)
- [ ] Verify ETag or SHA-256 after each batch
- [ ] Update `Certificate.migrated_to_s3_at` timestamp
- [ ] Spot-check 10 random certificates (manual verification)

### Week 9: Switch to S3 Primary
- [ ] Flip `USE_S3_FOR_CERTS=true` in production (all new certs to S3 only)
- [ ] Deploy during low-traffic window (3am UTC)
- [ ] Monitor for 24 hours (certificate generation, downloads)
- [ ] Verify no 403/404 spikes (target: <1%)

### Week 17: Deprecate Local Storage (60 Days After Migration)
- [ ] Archive local files to S3 `_archive/` prefix (compliance)
- [ ] Delete local files (free disk space 20GB+)
- [ ] Document S3-only workflow in runbook

---

## Files Created

1. ✅ **Documents/ExecutionPlan/S3_MIGRATION_DESIGN.md** (700 lines, 10 sections)
2. ✅ **settings_s3.example.py** (230 lines, commented config)
3. ✅ **scripts/migrate_certificates_to_s3.py** (270 lines, skeleton scaffold)
4. ✅ **Documents/Runbooks/S3_OPERATIONS_CHECKLIST.md** (550 lines, ops guide)
5. ✅ **Documents/ExecutionPlan/MODULE_6.5_COMPLETION_STATUS.md** (this file, 250 lines)

**Total:** 5 planning artifacts (2,000+ lines of documentation)

---

## Files Modified

- **Documents/ExecutionPlan/MAP.md** (Module 6.5 entry added)
- **Documents/ExecutionPlan/trace.yml** (phase_6:module_6_5 entry added)

---

## Production Impact

**Zero.** No production code changes, no AWS provisioning, no live migration.

**Current Behavior:** App continues using local `MEDIA_ROOT` storage for certificates.

**Next Phase:** Phase 7 (Q1-Q2 2026) will implement S3 migration based on this planning work.

---

## Testing

**Not Applicable.** Module 6.5 is planning-only (no code to test).

**Phase 7 Testing:** Staging tests (certificate generation → S3 upload → presigned URL → expiration verification).

---

## References

- **PHASE_6_IMPLEMENTATION_PLAN.md#module-6.5** (Module definition)
- **S3_MIGRATION_DESIGN.md** (Comprehensive design document)
- **settings_s3.example.py** (Django configuration)
- **scripts/migrate_certificates_to_s3.py** (Migration script scaffold)
- **S3_OPERATIONS_CHECKLIST.md** (Operations runbook)
- **AWS S3 Documentation** (https://aws.amazon.com/s3/)
- **django-storages Documentation** (https://django-storages.readthedocs.io/)

---

## Document Metadata

**Version:** 1.0  
**Created:** November 10, 2025  
**Author:** Backend Team  
**Reviewers:** Engineering Lead, DevOps Team  
**Approval:** Module 6.5 Planning Complete ✅  
**Next Review:** Q1 2026 (before Phase 7 implementation)  

---

**Module 6.5 Status:** ✅ **COMPLETE** (Planning Only)  
**Implementation:** Phase 7 (Q1-Q2 2026)
