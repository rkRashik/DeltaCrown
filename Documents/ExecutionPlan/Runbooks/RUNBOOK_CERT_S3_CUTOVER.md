# Certificate S3 Storage Cutover - Operations Runbook

**Module**: 6.5 - S3 Certificate Storage Migration  
**Owner**: DevOps Team  
**Approved By**: [Pending]  
**Last Updated**: 2025-11-12

---

## Overview

This runbook provides step-by-step procedures for:
1. **Go-Live**: Safe rollout of S3 storage with zero downtime
2. **Rollback**: Instant revert to local-only mode
3. **Monitoring**: Key metrics and alerts
4. **Troubleshooting**: Common failure scenarios

---

## Prerequisites

### Infrastructure
- [x] S3 bucket created: `deltacrown-certificates-prod` (or staging equivalent)
- [x] IAM role with S3 permissions (PutObject, GetObject, DeleteObject, ListBucket)
- [x] Lifecycle policy applied (`ops/s3/lifecycle-policy.json`)
- [x] boto3 installed: `pip install boto3`
- [x] django-storages installed: `pip install django-storages[s3]`

### Configuration
- [x] `AWS_STORAGE_BUCKET_NAME` set in environment
- [x] `AWS_S3_REGION_NAME` set (default: us-east-1)
- [x] AWS credentials configured (IAM role or env vars)
- [x] Feature flags added to settings (all default OFF)

### Validation
- [x] Run test suite: `pytest tests/certificates/test_s3_storage_module_6_5.py` (31+ pass)
- [x] Apply migration: `python manage.py migrate tournaments`
- [x] Verify S3 connectivity: `aws s3 ls s3://deltacrown-certificates-prod/`

---

## Go-Live Procedure (10 Steps)

### Phase 1: Staging Validation (Day 1-3)

#### Step 1: Enable Dual-Write in Staging
```bash
# /etc/deltacrown/staging.env
export CERT_S3_DUAL_WRITE=true
export CERT_S3_READ_PRIMARY=false
export CERT_S3_BACKFILL_ENABLED=true

# Restart Django workers
systemctl restart deltacrown-uwsgi
```

**Success Criteria**:
- No 500 errors in application logs
- `cert.s3.save.success` metrics emitted
- Local + S3 copies verified for new uploads

**Validation**:
```bash
# Upload test certificate via admin
# Verify both copies exist:
ls -lh /var/www/deltacrown/media/certificates/pdf/
aws s3 ls s3://deltacrown-certificates-staging/pdf/
```

---

#### Step 2: Run Backfill Dry-Run
```bash
python manage.py backfill_certificates_to_s3 \
    --dry-run \
    --limit 100 \
    --verify-hash

# Review output:
# - Total certificates found: X
# - Would migrate: Y
# - Would skip (already migrated): Z
```

**Success Criteria**:
- Dry-run completes without errors
- Hash verification passes
- Resume token generated correctly

---

#### Step 3: Backfill 10% Sample
```bash
# Backfill first 10% of certificates
python manage.py backfill_certificates_to_s3 \
    --limit 100 \
    --batch-size 10 \
    --verify-hash \
    | tee backfill_phase1.log

# Monitor progress
tail -f logs/app.log | grep "BACKFILL"
```

**Success Criteria**:
- 100 certificates migrated successfully
- ETag/SHA-256 verification passes
- `migrated_to_s3_at` timestamps set
- No data corruption (spot check 5 random files)

**Rollback Trigger**: >5% upload failures → STOP, investigate

---

#### Step 4: Enable S3 Reads for Migrated Certs
```bash
# Enable read-primary for migrated certs only
export CERT_S3_READ_PRIMARY=true
systemctl restart deltacrown-uwsgi
```

**Success Criteria**:
- Migrated certs served from S3
- Non-migrated certs served from local
- Presigned URLs generated correctly
- p95 latency <100ms for URL generation

**Validation**:
```bash
# Test presigned URL
curl -I "$(python manage.py shell -c 'from apps.tournaments.models import Certificate; print(Certificate.objects.filter(migrated_to_s3_at__isnull=False).first().file_pdf.url)')"
# Expect: HTTP/1.1 200 OK
```

---

#### Step 5: Run Consistency Checker
```bash
# Run daily consistency check manually
python manage.py shell << EOF
from apps.tournaments.tasks.certificate_consistency import check_certificate_consistency
result = check_certificate_consistency()
print(f"DB count: {result['db_count']}, S3 count: {result['s3_count']}")
EOF
```

**Success Criteria**:
- DB count == S3 count (for migrated certs)
- No count mismatches logged
- Spot check (1% SHA-256) passes

**Rollback Trigger**: Count mismatch >5% → STOP, run integrity audit

---

### Phase 2: Production Canary (Day 4-10)

#### Step 6: Enable Production Dual-Write (10% Traffic)
```bash
# Production environment
export CERT_S3_DUAL_WRITE=true
export CERT_S3_READ_PRIMARY=false  # Keep reads local for now
export CERT_S3_BACKFILL_ENABLED=true

# Rolling restart (10% of workers)
systemctl restart deltacrown-uwsgi@worker1
# Wait 30 minutes, monitor metrics
```

**Success Criteria**:
- Dual-write success rate >99.5%
- Upload p95 <400ms
- No customer-facing errors
- Local fallback never triggered

**Monitoring** (30-minute soak):
```bash
# Watch metrics
watch -n 30 'tail -100 logs/app.log | grep "METRIC: cert.s3"'

# Alert on:
# - cert.s3.save.fail > 0.5% of total saves
# - cert.s3.read.fallback > 1% of total reads
```

---

#### Step 7: Backfill Full Dataset (Batched)
```bash
# Run backfill in 1000-cert batches
for i in {0..10}; do
    START_ID=$((i * 1000))
    python manage.py backfill_certificates_to_s3 \
        --start-id $START_ID \
        --limit 1000 \
        --batch-size 50 \
        --verify-hash \
        | tee backfill_batch_$i.log
    
    sleep 300  # 5-minute cooldown between batches
done

# Final resume if interrupted
python manage.py backfill_certificates_to_s3 \
    --resume-token $(tail -1 backfill_batch_*.log | grep "RESUME_TOKEN")
```

**Success Criteria**:
- 100% of certificates migrated
- Zero hash verification failures
- Backfill completes within 24 hours

---

#### Step 8: Enable S3 Reads (100% Traffic)
```bash
# Enable read-primary for all traffic
export CERT_S3_READ_PRIMARY=true
systemctl restart deltacrown-uwsgi

# Monitor fallback rate
watch -n 60 'tail -200 logs/app.log | grep "cert.s3.read.fallback" | wc -l'
```

**Success Criteria**:
- Fallback rate <0.1% (rare S3 transient errors only)
- Presigned URL p95 <100ms
- No 404 errors for migrated certs
- Local storage still available for fallback

**Rollback Trigger**: Fallback rate >5% → Execute Emergency Rollback

---

#### Step 9: Soak Period (7 Days)
Monitor for 7 days before deprecating local storage:

**Daily Checks**:
- [ ] Run consistency checker: DB count == S3 count
- [ ] Spot check 10 random certificates: local + S3 match
- [ ] Review metrics: success rate >99.9%
- [ ] Check S3 costs: within budget ($X/month)

**Alerts** (configure in monitoring system):
```yaml
- name: S3 Upload Failure Rate High
  condition: cert.s3.save.fail / cert.s3.save.total > 0.01  # 1%
  severity: critical
  action: Page on-call engineer

- name: S3 Read Fallback Spike
  condition: cert.s3.read.fallback rate > 5/min
  severity: warning
  action: Investigate S3 connectivity

- name: Consistency Mismatch
  condition: DB count != S3 count
  severity: critical
  action: Run integrity audit script
```

---

#### Step 10: Deprecate Local Storage (Day 30+)
After 30-day grace period with zero issues:

```bash
# Optional: Archive local copies to cold storage
tar -czf certificates_local_backup_$(date +%Y%m%d).tar.gz /var/www/deltacrown/media/certificates/
aws s3 cp certificates_local_backup_*.tar.gz s3://deltacrown-backups/

# Delete local copies (IRREVERSIBLE - ensure S3 verified first!)
# rm -rf /var/www/deltacrown/media/certificates/pdf/
# (Uncomment only after explicit approval)
```

---

## Emergency Rollback Procedure

**RTO Target**: <1 minute  
**Data Loss Risk**: ZERO (local shadow copies retained)

### Scenario 1: S3 Upload Failures Spike

**Trigger**: `cert.s3.save.fail` rate >5% for >5 minutes

```bash
# IMMEDIATE ACTION (30 seconds)
export CERT_S3_DUAL_WRITE=false
systemctl restart deltacrown-uwsgi

# Verify local-only mode active
tail -f logs/app.log | grep "CERT_S3_DUAL_WRITE"
# Expect: "Feature flag OFF, using local storage only"
```

**Validation**:
- New uploads write to local only
- No S3 API calls logged
- Application functioning normally

---

### Scenario 2: S3 Read Errors Spike

**Trigger**: `cert.s3.read.fallback` rate >10% for >2 minutes

```bash
# IMMEDIATE ACTION (20 seconds)
export CERT_S3_READ_PRIMARY=false
systemctl reload deltacrown-uwsgi  # Graceful reload

# Verify reads from local
tail -f logs/app.log | grep "CERT_S3_READ_PRIMARY"
# Expect: "Feature flag OFF, reading from local storage"
```

**Validation**:
- All reads served from local
- Presigned URLs disabled
- No customer-facing errors

---

### Scenario 3: Data Inconsistency Detected

**Trigger**: Consistency checker reports DB count != S3 count (>5% mismatch)

```bash
# STOP BACKFILL IMMEDIATELY
export CERT_S3_BACKFILL_ENABLED=false
pkill -f backfill_certificates_to_s3  # Kill running backfill

# Disable S3 reads (safety)
export CERT_S3_READ_PRIMARY=false
systemctl restart deltacrown-uwsgi

# Run integrity audit
python manage.py shell << EOF
from apps.tournaments.models import Certificate
db_migrated = Certificate.objects.filter(migrated_to_s3_at__isnull=False).count()
print(f"DB reports {db_migrated} migrated")

# TODO: Add S3 list_objects_v2 count comparison
EOF
```

**Resolution**:
1. Identify divergence root cause (partial upload? deletion bug?)
2. Re-run backfill with `--verify-hash` for affected certs
3. Run spot integrity check (100% sample, not 1%)
4. Re-enable flags only after 100% verification

---

## Monitoring & Alerts

### Key Metrics

| Metric | Target | Alert Threshold | Action |
|--------|--------|-----------------|--------|
| `cert.s3.save.success` rate | >99.5% | <99% | Investigate S3 connectivity |
| `cert.s3.save.fail` rate | <0.5% | >1% | Page on-call engineer |
| Upload latency (p95) | <400ms | >500ms | Check S3 region/network |
| Presigned URL latency (p95) | <100ms | >150ms | Investigate IAM/signing |
| `cert.s3.read.fallback` rate | <0.1% | >1% | Check S3 availability |
| Consistency check | 100% match | <95% | Run integrity audit |

### Log Queries

**CloudWatch Logs Insights** (or equivalent):
```
# S3 upload failures in last hour
fields @timestamp, @message
| filter @message like /cert.s3.save.fail/
| stats count() by bin(1m)

# Fallback activations
fields @timestamp, @message
| filter @message like /cert.s3.read.fallback/
| sort @timestamp desc
| limit 100
```

---

## Troubleshooting

### Issue: Presigned URLs Return 403 Forbidden

**Symptoms**:
- S3 URLs fail with "Access Denied"
- Local URLs work fine

**Root Cause**: IAM permissions or bucket policy misconfigured

**Resolution**:
```bash
# Verify IAM role permissions
aws iam get-role-policy --role-name deltacrown-s3-access --policy-name S3CertificateAccess

# Required permissions:
# - s3:GetObject
# - s3:PutObject
# - s3:DeleteObject
# - s3:ListBucket

# Test presigned URL generation
python manage.py shell -c "
from apps.tournaments.storage import CertificateS3Storage
storage = CertificateS3Storage()
print(storage.s3_storage.bucket.name)  # Should print bucket name
"
```

---

### Issue: Backfill Command Hangs

**Symptoms**:
- Backfill progress stops
- No log output for >5 minutes

**Root Cause**: S3 rate limiting or network timeout

**Resolution**:
```bash
# Kill hung process
pkill -f backfill_certificates_to_s3

# Resume with smaller batch size
python manage.py backfill_certificates_to_s3 \
    --resume-token <LAST_KNOWN_TOKEN> \
    --batch-size 10 \
    --limit 100
```

---

### Issue: Local-S3 Hash Mismatch

**Symptoms**:
- Spot integrity check fails
- SHA-256 hashes don't match

**Root Cause**: File modified after upload, or upload corruption

**Resolution**:
```bash
# Re-upload affected certificate
python manage.py shell << EOF
from apps.tournaments.models import Certificate
cert = Certificate.objects.get(id=<CERT_ID>)

# Clear migration flag
cert.migrated_to_s3_at = None
cert.save()

# Re-run backfill for this cert only
EOF

python manage.py backfill_certificates_to_s3 \
    --tournament-id <TOURNAMENT_ID> \
    --verify-hash
```

---

## Contact & Escalation

| Role | Contact | Escalation Path |
|------|---------|-----------------|
| DevOps On-Call | ops@example.com | PagerDuty incident |
| Backend Lead | backend-lead@example.com | Slack #backend-alerts |
| AWS Support | AWS Premium Support | Open ticket (TAM) |

---

## Appendix

### A. S3 Lifecycle Policy
Located at: `ops/s3/lifecycle-policy.json`

Apply with:
```bash
aws s3api put-bucket-lifecycle-configuration \
    --bucket deltacrown-certificates-prod \
    --lifecycle-configuration file://ops/s3/lifecycle-policy.json
```

### B. Feature Flag Reference

| Flag | Default | Purpose | Set To |
|------|---------|---------|--------|
| `CERT_S3_DUAL_WRITE` | False | Enable S3 writes | `true` in Phase 1 |
| `CERT_S3_READ_PRIMARY` | False | Switch reads to S3 | `true` in Phase 2 (after backfill) |
| `CERT_S3_BACKFILL_ENABLED` | False | Gate backfill command | `true` during migration window |

### C. Cost Estimate

**Monthly S3 Costs** (10,000 certificates, avg 500KB each):
- Storage (Standard): 5GB × $0.023/GB = $0.12/month
- Requests (PUT): 100/day × $0.005/1000 = $0.015/month
- Requests (GET): 10,000/day × $0.0004/1000 = $0.12/month
- Data transfer (out): 50GB × $0.09/GB = $4.50/month
- **Total**: ~$5/month (scales linearly with certificate count)

### D. Dry-Run Example Output
```
=== Certificate S3 Backfill (DRY-RUN) ===
Start ID: 1
Limit: 100
Batch size: 10
Verify hash: True

[INFO] Found 87 certificates to migrate
[INFO] Batch 1/9: Processing certificates 1-10...
[DRY-RUN] Would upload: pdf/2025/11/cert_uuid1.pdf (ETag: abc123...)
[DRY-RUN] Would upload: pdf/2025/11/cert_uuid2.pdf (ETag: def456...)
...
[INFO] Progress: 10/87 (11.5%) - ETA: 2 minutes

=== Summary ===
Total found: 87
Would migrate: 87
Would skip (already migrated): 0
Errors: 0
Duration: 3.2 seconds

Resume token: eyJzdGFydF9pZCI6IDEwfQ==
```

---

**Document Version**: 1.0  
**Last Reviewed**: 2025-11-12  
**Next Review**: 2025-12-12
