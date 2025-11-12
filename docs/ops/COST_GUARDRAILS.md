# Cost Guardrails — DeltaCrown Operations

**Last Updated**: 2025-11-13  
**Owner**: Platform SRE + FinOps Team

---

## Overview

This document defines cost control mechanisms for DeltaCrown infrastructure:
- **S3 lifecycle policies** (STANDARD → IA → Glacier)
- **Query cost checks** (EXPLAIN thresholds, seq scan warnings)
- **Performance baseline budgets** (p95 envelopes per endpoint)
- **CI policy** (PR fails if regression >15% or cost threshold exceeded)

---

## S3 Lifecycle Policies

### Object Storage Tiers

| **Tier** | **Use Case** | **Cost** | **Transition Rule** |
|----------|--------------|----------|---------------------|
| **STANDARD** | Active data (recent uploads, hot media) | $$$ | Immediate on upload |
| **STANDARD_IA** | Infrequent access (>30 days old) | $$ | After 30 days |
| **GLACIER** | Archival (>90 days old) | $ | After 90 days |
| **DEEP_ARCHIVE** | Long-term retention (>1 year) | ¢ | After 365 days |

### Lifecycle Rules (Terraform example)

```hcl
resource "aws_s3_bucket_lifecycle_configuration" "deltacrown_media" {
  bucket = aws_s3_bucket.deltacrown_media.id

  rule {
    id     = "transition_to_ia_30d"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 730  # Delete after 2 years
    }

    filter {
      prefix = "user_avatars/"
    }
  }

  rule {
    id     = "transition_team_logos_90d"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    filter {
      prefix = "team_logos/"
    }
  }

  rule {
    id     = "delete_temp_files_7d"
    status = "Enabled"

    expiration {
      days = 7
    }

    filter {
      prefix = "temp/"
    }
  }
}
```

### Object Count & Size Budgets

| **Bucket/Prefix** | **Max Objects** | **Max Size (GB)** | **Alert Threshold** |
|-------------------|-----------------|-------------------|---------------------|
| `user_avatars/` | 100,000 | 50 GB | 80% (80k objects, 40 GB) |
| `team_logos/` | 10,000 | 10 GB | 80% (8k objects, 8 GB) |
| `tournament_media/` | 50,000 | 200 GB | 80% (40k objects, 160 GB) |
| `temp/` | 1,000 | 5 GB | **90%** (900 objects, 4.5 GB) |

**Monitoring**:
- CloudWatch metric: `s3_bucket_size_bytes`
- Alert if threshold exceeded: Slack #infra-alerts, PagerDuty (low priority)

### Cost Optimization Checklist

- [ ] Lifecycle policies active on all production buckets
- [ ] No objects older than 730 days (auto-delete configured)
- [ ] `temp/` prefix cleaned up after 7 days
- [ ] Media files compressed (JPEG quality 85%, PNG optimized)
- [ ] CloudFront CDN caching enabled (80% cache hit rate target)

---

## Query Cost Checks

### EXPLAIN Thresholds

**Goal**: Prevent expensive queries from reaching production.

| **Metric** | **Yellow Threshold** | **Red Threshold (CI Fail)** | **Action** |
|------------|----------------------|-----------------------------|------------|
| **Sequential Scan** | Table >10k rows | Table >100k rows | Add index, rewrite query |
| **Rows Examined** | >10,000 | >100,000 | Add WHERE clause, limit results |
| **Execution Time** | >500ms | >2000ms | Add index, optimize JOIN |
| **Temp Disk Usage** | >100 MB | >1 GB | Reduce result set, add index |

### CI Policy: Query Cost Validation

Add to `.github/workflows/query-cost-check.yml`:

```yaml
name: Query Cost Validation

on:
  pull_request:
    paths:
      - 'apps/**/models.py'
      - 'apps/**/views.py'
      - 'apps/**/services.py'

jobs:
  query-cost-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install django psycopg2-binary django-debug-toolbar
      
      - name: Run EXPLAIN analysis on test queries
        run: |
          python manage.py test --settings=deltacrown.settings_test_pg --verbosity=2 --debug-sql
          # Parse output for seq scans on large tables
          python scripts/check_query_costs.py
      
      - name: Fail PR if regression >15%
        run: |
          # Compare query costs with baseline (baseline.json)
          # Fail if any query has >15% increase in rows examined or execution time
          python scripts/compare_query_baselines.py --threshold 0.15
```

### Index Hints Playbook

**Common Slow Queries**:

1. **User wallet balance lookup** (was sequential scan):
   ```sql
   -- Before (slow):
   SELECT * FROM economy_wallet WHERE user_id = 12345;
   
   -- After (fast, indexed):
   CREATE INDEX idx_economy_wallet_user_id ON economy_wallet (user_id);
   SELECT * FROM economy_wallet WHERE user_id = 12345;
   ```

2. **Tournament registrations by status** (was table scan):
   ```sql
   -- Before (slow):
   SELECT * FROM tournaments_registration WHERE status = 'PENDING';
   
   -- After (fast, composite index):
   CREATE INDEX idx_tournaments_registration_status_created 
   ON tournaments_registration (status, created_at DESC);
   SELECT * FROM tournaments_registration 
   WHERE status = 'PENDING' 
   ORDER BY created_at DESC LIMIT 100;
   ```

3. **Match results with tournament filter** (was nested loop):
   ```sql
   -- Before (slow):
   SELECT * FROM tournaments_match m
   JOIN tournaments_result r ON r.match_id = m.id
   WHERE m.tournament_id = 456;
   
   -- After (fast, covering index):
   CREATE INDEX idx_tournaments_result_match_tournament 
   ON tournaments_result (match_id) INCLUDE (winner_id, score_home, score_away);
   SELECT * FROM tournaments_match m
   JOIN tournaments_result r ON r.match_id = m.id
   WHERE m.tournament_id = 456;
   ```

### No Seq Scan Policy

**Disallow in production** (enforced via pgBadger analysis):

```sql
-- Forbidden pattern (no WHERE clause on large table):
SELECT * FROM economy_transaction;  -- ❌ Table has 1M+ rows

-- Allowed (filtered, indexed):
SELECT * FROM economy_transaction 
WHERE created_at > NOW() - INTERVAL '7 days';  -- ✅ Indexed on created_at
```

**CI Check**:
```bash
# Add to scripts/check_query_costs.py
def detect_seq_scans_on_large_tables(explain_output, table_sizes):
    for line in explain_output:
        if "Seq Scan on" in line:
            table_name = extract_table_name(line)
            if table_sizes[table_name] > 100000:  # >100k rows
                raise ValueError(f"Sequential scan on large table: {table_name} ({table_sizes[table_name]} rows)")
```

---

## Performance Baseline Budgets

### P95 Latency Envelopes (per endpoint)

| **Endpoint** | **Green** | **Yellow** | **Red (Alert)** | **Notes** |
|--------------|-----------|------------|-----------------|-----------|
| `/health` | <50ms | 50-100ms | >100ms | No DB queries, cache-only |
| `/api/transactions` | <200ms | 200-400ms | >400ms | Indexed query, cache enabled |
| `/api/shop/items` | <150ms | 150-300ms | >300ms | Paginated (limit 50), cache enabled |
| `/api/moderation/enforcement/ping` | <100ms | 100-200ms | >200ms | Cache hit expected (TTL 60s) |
| `/api/tournaments/list` | <300ms | 300-600ms | >600ms | Paginated (limit 20), JOIN optimized |
| `/api/match/live` (WebSocket) | <200ms | 200-400ms | >400ms | Redis pub/sub, no DB writes |

**Monitoring**:
- Prometheus histogram: `http_request_duration_seconds_bucket`
- Alert rule: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.4`

### Green/Yellow/Red Bands

**Color-Coded Dashboards** (Grafana panels):

- **Green**: Within budget, no action needed
- **Yellow**: Approaching threshold, investigate proactively
- **Red**: Exceeds threshold, immediate investigation required

**Example Alert Rule** (Prometheus):

```yaml
groups:
  - name: latency_budgets
    interval: 30s
    rules:
      - alert: TransactionsLatencyYellow
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{endpoint="/api/transactions"}[5m])) > 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Transactions API p95 latency exceeds 200ms"
          description: "Current p95: {{ $value }}s. Check DB query costs, cache hit rate."
      
      - alert: TransactionsLatencyRed
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{endpoint="/api/transactions"}[5m])) > 0.4
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Transactions API p95 latency exceeds 400ms (RED)"
          description: "Current p95: {{ $value }}s. IMMEDIATE action required. Check RUNBOOKS/ONCALL_HANDOFF.md."
```

### Regression Detection (CI)

**Baseline File**: `ci/baseline/performance_budgets.json`

```json
{
  "endpoints": {
    "/health": {
      "p95_latency_ms": 30,
      "rps_capacity": 1000
    },
    "/api/transactions": {
      "p95_latency_ms": 150,
      "rps_capacity": 200
    },
    "/api/shop/items": {
      "p95_latency_ms": 120,
      "rps_capacity": 300
    }
  }
}
```

**CI Check** (fail PR if regression >15%):

```bash
# scripts/compare_query_baselines.py
def check_latency_regression(baseline, current, threshold=0.15):
    for endpoint, metrics in current.items():
        baseline_p95 = baseline[endpoint]["p95_latency_ms"]
        current_p95 = metrics["p95_latency_ms"]
        
        if current_p95 > baseline_p95 * (1 + threshold):
            raise ValueError(
                f"Latency regression detected for {endpoint}: "
                f"baseline={baseline_p95}ms, current={current_p95}ms "
                f"(+{((current_p95 / baseline_p95) - 1) * 100:.1f}%)"
            )
```

---

## CI Policy: Cost Threshold Enforcement

### PR Fail Conditions

A pull request **must fail CI** if any of these conditions are met:

1. **Query Cost Regression**:
   - Any query has >15% increase in rows examined OR execution time
   - Sequential scan detected on table >100k rows
   - Temp disk usage >1 GB for any query

2. **Latency Regression**:
   - Any endpoint p95 latency increases by >15% from baseline
   - Any endpoint falls into RED band (see table above)

3. **Storage Cost Spike**:
   - Test run generates >1 GB of temp files
   - S3 upload simulation exceeds 100 MB (per test suite run)

4. **Query Count Explosion**:
   - Any endpoint generates >50 queries per request (N+1 query problem)
   - Test suite total queries >10,000 (sign of inefficiency)

### Enforcement Scripts

Add to `.github/workflows/cost-guardrails.yml`:

```yaml
name: Cost Guardrails Check

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  cost-guardrails:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Compare with baseline
        run: |
          python scripts/compare_query_baselines.py --threshold 0.15
          python scripts/check_storage_usage.py --max-temp-size 1GB
          python scripts/detect_n_plus_one.py --max-queries 50
      
      - name: Post comment on PR
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '🚨 **Cost Guardrails Failed** 🚨\n\nThis PR introduces performance regressions or cost increases. See CI logs for details.\n\n**Common Fixes**:\n- Add database indexes\n- Reduce query result sets (add LIMIT)\n- Optimize N+1 queries (use select_related, prefetch_related)\n- Compress uploaded files\n\nSee docs/ops/COST_GUARDRAILS.md for details.'
            })
```

---

## Cost Monitoring Dashboard

**Grafana Dashboard**: `grafana/cost_monitoring.json` (to be created in Phase 11)

**Panels**:
1. **S3 storage costs** (by bucket, stacked area chart)
2. **RDS query costs** (by endpoint, sorted by execution time)
3. **CloudFront bandwidth** (egress costs, GB/day)
4. **Redis memory usage** (eviction rate, cache hit rate)
5. **Lambda invocations** (if applicable, cost per function)

**Estimated Monthly Costs** (baseline):
- S3 storage: $50/month (STANDARD), $10/month (IA + Glacier)
- RDS (db.t3.medium): $150/month
- CloudFront: $30/month (10 GB/day egress)
- **Total**: ~$240/month

**Budget Alert**: Trigger if monthly spend exceeds $300 (25% over budget).

---

## References

- **RELEASE_CHECKLIST_V1.md**: Pre-deploy cost validation steps
- **RUNBOOKS/ONCALL_HANDOFF.md**: Performance degradation playbook
- **MODULE_8.3_OBSERVABILITY_NOTES.md**: Cache metrics, sampling costs
- **PHASE_9_SMOKE_AND_ALERTING.md**: Latency alert thresholds

---

**Last Updated**: 2025-11-13  
**Next Review**: After Phase 10 deployment (within 1 week)
