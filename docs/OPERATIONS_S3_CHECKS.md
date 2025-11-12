# S3 Storage Operations Checks — Runbook

**Purpose**: Procedures for interpreting S3 storage metrics, recovering from inconsistencies, and maintaining data integrity in production.

**Audience**: DevOps, SRE, Platform Engineering

---

## 📊 Monitoring Dashboard

### Key Metrics to Track

| Metric | Threshold | Alert Level | Action |
|--------|-----------|-------------|--------|
| `cert.s3.save.fail` | >5% over 10min | ⚠️ WARNING | Check S3 service status, review error logs |
| `cert.s3.read.fallback` | >10% over 10min | 🚨 CRITICAL | S3 outage likely, verify flag: `CERT_S3_READ_PRIMARY=true` |
| `cert.s3.delete.fail` | >2% over 10min | ⚠️ WARNING | Check S3 delete permissions, review IAM roles |
| `cert.s3.write.success` | <95% over 10min | 🚨 CRITICAL | Dual-write failing, review logs for network issues |
| Backfill mismatch rate | >0.5% daily | 🚨 CRITICAL | Run integrity sweep, review backfill logs |

### Grafana Queries (PromQL)

```promql
# S3 save failure rate (10min window)
rate(cert_s3_save_fail_total[10m]) / rate(cert_s3_save_total[10m]) > 0.05

# S3 read fallback rate (10min window)
rate(cert_s3_read_fallback_total[10m]) / rate(cert_s3_read_total[10m]) > 0.10

# Backfill mismatch rate (daily)
cert_backfill_mismatch_rate_percent > 0.5
```

---

## 🛠️ Recovery Procedures

### Scenario 1: S3 Outage (Complete Unavailability)

**Symptoms**:
- `cert.s3.save.fail` at 100%
- `cert.s3.read.fallback` at 100%
- Error logs: "503 Service Unavailable", "Connection timeout"

**Immediate Actions**:
1. **Verify S3 service status**: Check AWS Status Dashboard (https://status.aws.amazon.com/)
2. **Flip read flag OFF** (instant rollback to local-only):
   ```bash
   kubectl set env deployment/deltacrown CERT_S3_READ_PRIMARY=false
   ```
3. **Keep dual-write ON** (if S3 recovers, backlog will sync):
   ```bash
   kubectl set env deployment/deltacrown CERT_S3_DUAL_WRITE=true
   ```
4. **Monitor local storage capacity**:
   ```bash
   df -h /mnt/media/certificates
   ```
   Alert if <10% free space.

**Post-Recovery**:
1. Wait for S3 service recovery confirmation (AWS green status)
2. Run backfill validator (1% sample):
   ```bash
   python scripts/s3_backfill_validator.py --sample-rate 0.01
   ```
3. If mismatch rate <0.5%, flip read flag back:
   ```bash
   kubectl set env deployment/deltacrown CERT_S3_READ_PRIMARY=true
   ```
4. Monitor `cert.s3.read.fallback` — should drop to <1% within 5 minutes.

---

### Scenario 2: Partial S3 Degradation (5-20% Errors)

**Symptoms**:
- `cert.s3.save.fail` between 5-20%
- Intermittent 5xx errors (500, 503, 504)
- No AWS service dashboard alerts

**Immediate Actions**:
1. **Check retry configuration** (should be bounded to 3 attempts):
   ```python
   # apps/tournaments/storage.py
   # Verify: max_attempts=3 in boto3 config
   ```
2. **Enable verbose S3 logging** (temporary):
   ```bash
   kubectl set env deployment/deltacrown LOG_LEVEL=DEBUG
   ```
3. **Increase fallback timeout** (if network latency suspected):
   ```python
   # Temporarily increase boto3 timeout in storage.py
   config = Config(connect_timeout=10, read_timeout=30)
   ```
4. **Do NOT disable dual-write** — local fallback handles errors gracefully.

**Root Cause Analysis**:
- Review S3 access logs (look for specific error codes)
- Check IAM role permissions (verify `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`)
- Validate S3 bucket lifecycle policies (no unexpected archival rules)

**Post-Recovery**:
- Revert verbose logging:
  ```bash
  kubectl set env deployment/deltacrown LOG_LEVEL=INFO
  ```
- Run backfill validator:
  ```bash
  python scripts/s3_backfill_validator.py --sample-rate 0.05  # 5% sample
  ```

---

### Scenario 3: Data Inconsistency Detected (Mismatch Rate >0.5%)

**Symptoms**:
- Nightly backfill validator reports mismatch rate >0.5%
- `artifacts/backfill_report.json` shows specific object keys with hash mismatches

**Immediate Actions**:
1. **Review mismatch details**:
   ```bash
   cat artifacts/backfill_report.json | jq '.mismatch_details[]'
   ```
2. **Identify pattern**:
   - **Single object**: Likely corruption during upload → re-upload
   - **Multiple objects from same batch**: Batch upload issue → re-run backfill for that batch
   - **Random objects**: Potential S3 data corruption → contact AWS Support

3. **Re-upload mismatched objects** (manual script):
   ```python
   from apps.tournaments.storage import CertificateS3Storage
   from django.core.files.base import File
   
   storage = CertificateS3Storage()
   mismatched_keys = ['certificates/cert_123.pdf', 'certificates/cert_456.pdf']
   
   for key in mismatched_keys:
       with storage.local_storage.open(key, 'rb') as local_file:
           storage.s3_storage.save(key, File(local_file))
       print(f"Re-uploaded: {key}")
   ```

4. **Re-run validator** (verify fix):
   ```bash
   python scripts/s3_backfill_validator.py --sample-rate 0.10  # Higher sample rate
   ```

**Escalation**:
- If mismatch rate remains >0.5% after re-upload → **Page SRE on-call**
- Provide: backfill report JSON, S3 access logs, application logs for timeframe

---

### Scenario 4: High Read Fallback Rate (10-30%)

**Symptoms**:
- `cert.s3.read.fallback` between 10-30%
- Reads hitting local storage despite S3 being available
- No S3 outage reported

**Possible Causes**:
1. **S3 GET latency spike** (p95 >500ms)
2. **Network path degradation** (AWS Direct Connect, VPC peering)
3. **S3 bucket in wrong region** (cross-region reads)

**Diagnostic Commands**:
```bash
# Check S3 GET latency from app server
aws s3 cp s3://deltacrown-certificates/test.txt /tmp/test.txt --debug

# Verify bucket region
aws s3api get-bucket-location --bucket deltacrown-certificates

# Test network path to S3 endpoint
traceroute s3.us-east-1.amazonaws.com
```

**Mitigation**:
- If cross-region reads confirmed → **Migrate bucket to same region as app**
- If network path issues → **Review VPC routing, NAT gateway performance**
- If latency spike temporary → **Monitor and wait** (fallback is safe)

---

## 🔍 Integrity Sweep (Deep Validation)

### When to Run
- After major S3 outage (>30min downtime)
- After backfill of >10K objects
- Quarterly compliance check

### Procedure
1. **Stop writes** (maintenance window):
   ```bash
   kubectl scale deployment/deltacrown --replicas=0
   ```

2. **Run full validator** (10% sample, can take 1-2 hours):
   ```bash
   python scripts/s3_backfill_validator.py --sample-rate 0.10 --output artifacts/integrity_sweep.json
   ```

3. **Review results**:
   ```bash
   cat artifacts/integrity_sweep.json | jq '.status, .mismatch_rate_percent, .total_sampled'
   ```

4. **If PASS** (mismatch <0.5%):
   ```bash
   kubectl scale deployment/deltacrown --replicas=3  # Resume
   ```

5. **If FAIL**:
   - Collect all mismatch details: `jq '.mismatch_details[]' artifacts/integrity_sweep.json`
   - Open incident ticket
   - Page SRE + Engineering lead

---

## 🚨 Emergency Contacts

| Team | Slack Channel | PagerDuty Escalation |
|------|---------------|----------------------|
| SRE On-Call | `#sre-oncall` | PagerDuty → SRE rotation |
| Platform Engineering | `#platform-eng` | Direct Slack @platform-lead |
| AWS Support | TAM: John Doe | AWS Premium Support case |

---

## 📋 Checklist: Post-Incident Review

After resolving any S3 incident:
- [ ] Update incident log (Confluence/Notion)
- [ ] Run backfill validator (verify integrity)
- [ ] Review metric thresholds (adjust if needed)
- [ ] Document root cause + mitigation
- [ ] Update this runbook (if new scenario discovered)
- [ ] Post mortem (if downtime >15min or data loss occurred)

---

## 🔗 Related Documentation

- [MODULE_6.5_FINAL_PACKAGE.md](../Reports/FINAL_CLOSURE_BUNDLED.md) — Coverage & test results
- [MODULE_6.6_PERF_REPORT.md](../Reports/MODULE_6.6_PERF_REPORT.md) — Performance baselines
- [AWS S3 Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)
- [Django Storage Backends](https://django-storages.readthedocs.io/)

---

**Last Updated**: 2025-01-20  
**Maintained By**: Platform Engineering Team
