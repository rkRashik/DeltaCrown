# Certificate Storage Migration: Local to S3

**Status:** Planning Complete (Implementation: Phase 7)  
**Module:** 6.5 - Certificate Storage Planning (S3 Migration)  
**Date:** November 10, 2025  
**Owner:** Backend Team  

---

## 1. Executive Summary

### Goals
- **Scalability**: Migrate certificate storage from local `MEDIA_ROOT` to AWS S3 for unlimited storage capacity
- **Reliability**: Leverage S3's 99.999999999% durability (11 nines) and multi-AZ replication
- **Cost Efficiency**: Transition to S3 Standard-IA and Glacier for long-term retention
- **Performance**: Enable CloudFront CDN for global certificate distribution (optional Phase 8)
- **Security**: Private objects with presigned URLs, encryption at rest, no PII exposure

### Non-Goals
- **NOT migrating user avatars or team logos** (separate storage domains)
- **NOT implementing CloudFront CDN** (Phase 8 optimization)
- **NOT changing certificate generation logic** (PDF/image generation remains unchanged)
- **NOT removing local storage immediately** (30-day dual-write transition period)

### Timeline
- **Phase 6 (Current)**: Planning and design (this document)
- **Phase 7 (Q1 2026)**: S3 provisioning, staging tests, dual-write implementation
- **Phase 7 (Q2 2026)**: Background migration of existing certificates
- **Phase 7 (Q2 2026)**: Switch to S3 as primary storage
- **Phase 7 (Q3 2026)**: Deprecate local storage after 60-day stabilization

### Success Metrics
- **Zero certificate loss** during migration (100% integrity validation)
- **<500ms p95 latency** for presigned URL generation
- **<5% cost increase** vs current storage (~$15-25/month)
- **Zero 403/404 errors** on certificate verification links
- **100% encrypted** objects (SSE-S3 or SSE-KMS)

---

## 2. Current State Analysis

### Existing Architecture

**Storage Backend:**
```python
# deltacrown/settings.py (current)
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
```

**Certificate Model:**
```python
# apps/tournaments/models/certificate.py
class Certificate(models.Model):
    file = models.FileField(upload_to='certificates/%Y/%m/', max_length=255)
    image = models.ImageField(upload_to='certificates/images/%Y/%m/', null=True, blank=True)
    # Stored at: /media/certificates/2025/11/{filename}.pdf
```

**Current Usage:**
- **Location**: `media/certificates/` (local disk)
- **Volume**: ~50 certificates/month (early stage)
- **Avg Size**: 1MB per PDF, 200KB per image
- **Growth Rate**: 10x expected in 6 months (500 certs/month)
- **Total Storage**: ~3GB current, ~30GB projected (1 year)

### Limitations

1. **Scalability Concerns**
   - Local disk capacity (500GB server → 50GB reserved for media → ~30GB for certificates)
   - No automatic scaling (requires manual disk expansion)
   - Single point of failure (no replication)

2. **Backup Gaps**
   - Daily server backups (24-hour RPO)
   - No versioning (overwrite risk if filename collision)
   - Manual restore process (slow RTO)

3. **Distribution Bottlenecks**
   - Single-origin serving (no CDN)
   - Bandwidth costs (server egress at $0.12/GB vs S3 transfer at $0.09/GB)
   - No global edge caching

4. **Security Risks**
   - Local files accessible via direct `/media/` URLs (no expiration)
   - No audit trail for certificate access
   - Backup files may leak to unauthorized users

### Decision Drivers

| Factor | Current (Local) | Future (S3) | Impact |
|--------|----------------|-------------|--------|
| **Durability** | 99.9% (RAID 10) | 99.999999999% (S3) | Critical |
| **Availability** | 99.5% (single AZ) | 99.99% (multi-AZ) | High |
| **Scalability** | Manual (disk expansion) | Automatic (unlimited) | High |
| **Cost** | $10/month (50 certs) | $15-25/month (500 certs) | Medium |
| **Backup** | Daily snapshots (24h RPO) | Continuous (versioning) | High |
| **Security** | Direct URLs (no expiry) | Presigned (10min TTL) | Critical |

**Verdict:** Migrate to S3 for scalability, durability, and security. Accept minor cost increase for operational benefits.

---

## 3. S3 Architecture

### Bucket Design

**Bucket Name:** `deltacrown-certificates-prod` (US East 1, `us-east-1`)

**Region Selection:**
- **Primary**: `us-east-1` (N. Virginia) - lowest cost, highest service availability
- **Replication**: Consider `us-west-2` (Oregon) for cross-region backup (Phase 8)

**Folder Structure:**
```
deltacrown-certificates-prod/
├── pdf/
│   ├── 2025/
│   │   ├── 11/
│   │   │   ├── {uuid-1}.pdf      # 1st place certificate
│   │   │   ├── {uuid-2}.pdf      # 2nd place certificate
│   │   │   └── ...
│   │   └── 12/
│   └── 2026/
├── images/
│   ├── 2025/
│   │   ├── 11/
│   │   │   ├── {uuid-1}.png      # Certificate preview image
│   │   │   └── ...
│   │   └── 12/
│   └── 2026/
└── _metadata/
    └── migration_log.json        # Migration tracking (optional)
```

**Key Naming Convention:**
- **Format**: `{type}/{yyyy}/{mm}/{uuid}.{ext}`
- **Example PDF**: `pdf/2025/11/a3f8e9c7-4b21-4d1a-8e3f-9c7a4b218e3f.pdf`
- **Example Image**: `images/2025/11/a3f8e9c7-4b21-4d1a-8e3f-9c7a4b218e3f.png`
- **No PII**: UUIDs only (no usernames, emails, tournament names in keys)
- **Collision-Proof**: UUID v4 ensures uniqueness (2^122 namespace)

**Rationale:**
- **Year/Month folders**: Easy lifecycle transitions (e.g., move all 2024 certs to Glacier)
- **Type separation**: Different lifecycle policies for PDFs vs images
- **UUID filenames**: Security (unpredictable), no PII exposure, collision-free

### Storage Backend Configuration

**Django Integration:**
```python
# requirements.txt (Phase 7)
django-storages[s3]==1.14.2
boto3==1.34.16
```

**Storage Classes:**
| Class | Use Case | Cost (per GB/month) | Retrieval | Transition |
|-------|----------|---------------------|-----------|------------|
| **S3 Standard** | Active certificates (0-90 days) | $0.023 | Immediate | Default |
| **S3 Standard-IA** | Inactive certificates (90 days - 1 year) | $0.0125 | <1s | @90 days |
| **S3 Glacier Flexible** | Archive (1-7 years) | $0.004 | Minutes-hours | @1 year |
| **Delete** | Compliance retention limit | $0 | N/A | @7 years |

**Settings Configuration:**
```python
# deltacrown/settings.py (Phase 7 - see settings_s3.example.py)

# Feature flag for gradual rollout
USE_S3_FOR_CERTIFICATES = env.bool('USE_S3_FOR_CERTS', default=False)

if USE_S3_FOR_CERTIFICATES:
    # AWS Credentials (use IAM role in production)
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
    
    # S3 Configuration
    AWS_STORAGE_BUCKET_NAME = 'deltacrown-certificates-prod'
    AWS_S3_REGION_NAME = 'us-east-1'
    AWS_S3_CUSTOM_DOMAIN = None  # Use CloudFront in Phase 8
    
    # Security Settings
    AWS_DEFAULT_ACL = None  # Private by default (no public-read)
    AWS_QUERYSTRING_AUTH = True  # Enable presigned URLs
    AWS_QUERYSTRING_EXPIRE = 600  # 10 minutes (not 15)
    AWS_S3_ENCRYPTION = 'AES256'  # SSE-S3 (or 'aws:kms' for SSE-KMS)
    AWS_S3_FILE_OVERWRITE = False  # Preserve existing files (UUID naming prevents collisions)
    
    # Performance Settings
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'private, max-age=600',  # 10 min browser cache
        'ContentDisposition': 'inline',  # Display in browser, not download
        'ServerSideEncryption': 'AES256',  # Encrypt at rest (SSE-S3)
    }
    
    # Optional: Customer-Managed KMS Key (if already using KMS)
    # AWS_S3_OBJECT_PARAMETERS['ServerSideEncryption'] = 'aws:kms'
    # AWS_S3_OBJECT_PARAMETERS['SSEKMSKeyId'] = 'arn:aws:kms:us-east-1:123456789012:key/abcd1234'
    
    # Storage Backend
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    CERTIFICATE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
else:
    # Local storage (current behavior)
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
```

**Environment Variables:**
```bash
# .env (production)
USE_S3_FOR_CERTS=true
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_STORAGE_BUCKET_NAME=deltacrown-certificates-prod
AWS_S3_REGION_NAME=us-east-1
```

### Presigned URL Generation

**Implementation:**
```python
# apps/tournaments/services/certificate_service.py (Phase 7)

from django.core.files.storage import default_storage
from datetime import timedelta

def get_certificate_download_url(certificate, expiration_seconds=600):
    """
    Generate presigned URL for certificate download.
    
    Args:
        certificate: Certificate model instance
        expiration_seconds: URL TTL (default 10 minutes)
    
    Returns:
        str: Presigned URL (S3) or local URL (filesystem)
    """
    if settings.USE_S3_FOR_CERTIFICATES:
        # S3 presigned URL (private object)
        url = default_storage.url(certificate.file.name, expire=expiration_seconds)
        return url
    else:
        # Local filesystem URL (no expiration)
        return certificate.file.url
```

**Presigned URL Characteristics:**
- **TTL**: 10 minutes (600 seconds)
- **Signing Method**: AWS Signature Version 4 (SigV4)
- **Query Parameters**: `X-Amz-Algorithm`, `X-Amz-Credential`, `X-Amz-Date`, `X-Amz-Expires`, `X-Amz-Signature`
- **Example**:
  ```
  https://deltacrown-certificates-prod.s3.us-east-1.amazonaws.com/pdf/2025/11/a3f8e9c7.pdf?
  X-Amz-Algorithm=AWS4-HMAC-SHA256&
  X-Amz-Credential=AKIAIOSFODNN7EXAMPLE/20251110/us-east-1/s3/aws4_request&
  X-Amz-Date=20251110T120000Z&
  X-Amz-Expires=600&
  X-Amz-SignedHeaders=host&
  X-Amz-Signature=abcd1234...
  ```

**Caching Strategy:**
- **Django Cache**: Cache presigned URL for 5 minutes (avoid regeneration on every request)
- **Browser Cache**: `Cache-Control: private, max-age=600` (10 minutes)
- **CloudFront Cache** (Phase 8): Edge cache with signed cookies

---

## 4. Security & Compliance

### Encryption at Rest

**SSE-S3 (Default - Recommended):**
- **Algorithm**: AES-256 (256-bit Advanced Encryption Standard)
- **Key Management**: AWS-managed keys (no additional cost)
- **Performance**: No latency impact
- **Compliance**: HIPAA, PCI DSS, GDPR compliant

**Bucket Policy (Deny Unencrypted Uploads):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencryptedObjectUploads",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::deltacrown-certificates-prod/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    }
  ]
}
```

**SSE-KMS (Optional - Customer-Managed Keys):**
- **Use Case**: If DeltaCrown already uses AWS KMS for other services (RDS, Secrets Manager)
- **Benefits**: Centralized key rotation, audit trail via CloudTrail
- **Cost**: $1/month per CMK + $0.03 per 10,000 requests
- **Configuration**:
  ```python
  AWS_S3_OBJECT_PARAMETERS = {
      'ServerSideEncryption': 'aws:kms',
      'SSEKMSKeyId': 'arn:aws:kms:us-east-1:123456789012:key/abcd1234',
  }
  ```

**Recommendation:** Use SSE-S3 (simpler, no additional cost) unless KMS is already in use.

### Encryption in Transit

**Enforce SSL/TLS:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::deltacrown-certificates-prod",
        "arn:aws:s3:::deltacrown-certificates-prod/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
```

### Access Control

**IAM Policy (Least Privilege):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CertificateUploadAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::deltacrown-certificates-prod/*",
      "Condition": {
        "StringEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    },
    {
      "Sid": "ListBucketAccess",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": "arn:aws:s3:::deltacrown-certificates-prod"
    }
  ]
}
```

**IAM User/Role:**
- **Development**: IAM user with access keys (rotate every 90 days)
- **Production**: IAM role attached to EC2 instance (no hardcoded credentials)
- **Principle**: One IAM role per environment (staging, production)

**Bucket ACL:**
- **Block Public Access**: Enabled (all 4 settings)
- **Object Ownership**: Bucket owner enforced (no ACL overrides)
- **Object ACL**: Private (default, no `public-read`)

### PII & GDPR Compliance

**No PII in Object Keys:**
```python
# BAD (leaks user info)
certificate.file.save('john_doe_winner_2025.pdf', file_content)  # ❌

# GOOD (UUID only)
import uuid
filename = f"{uuid.uuid4()}.pdf"
certificate.file.save(f'pdf/2025/11/{filename}', file_content)  # ✅
```

**Object Metadata (No PII):**
- **Allowed**: `tournament_id`, `placement`, `generated_at`, `file_size`
- **Forbidden**: `user_email`, `username`, `team_name`, `player_name`

**GDPR Right to Erasure:**
- **Certificate Deletion**: `DELETE /api/tournaments/certificates/{uuid}/`
- **S3 Object Deletion**: `s3:DeleteObject` via Django signal or background task
- **Soft Delete**: Mark `Certificate.deleted_at` timestamp, delete S3 object after 30 days (compliance buffer)

### Audit Trail

**S3 Server Access Logs (Basic):**
- **Location**: `s3://deltacrown-logs/s3-access/`
- **Retention**: 90 days
- **Cost**: Free (S3 storage only)
- **Contains**: Bucket owner, bucket name, time, remote IP, requester, operation, key, HTTP status

**CloudTrail Data Events (Advanced):**
- **Captures**: API calls (PutObject, GetObject, DeleteObject)
- **Cost**: $0.10 per 100,000 data events (~$5-10/month)
- **Benefits**: IAM user attribution, event filtering, CloudWatch Logs integration
- **Recommendation**: Enable for production (compliance/forensics), disable for staging (cost)

**CloudWatch Alarms:**
- **403 Spike**: Alert when 403 Forbidden exceeds 10 requests/minute (IAM policy issue)
- **5xx Errors**: Alert when 5xx errors exceed 5 requests/minute (S3 service issue)
- **Presigned URL Latency**: Warn when `boto3.generate_presigned_url()` exceeds 100ms (p95)

---

## 5. Cost Estimation

### Assumptions

| Metric | Current | 6 Months | 12 Months |
|--------|---------|----------|-----------|
| **Certificates/Month** | 50 | 500 | 1,000 |
| **Avg PDF Size** | 1 MB | 1 MB | 1 MB |
| **Avg Image Size** | 200 KB | 200 KB | 200 KB |
| **Total Storage/Month** | 60 MB | 600 MB | 1.2 GB |
| **Cumulative Storage** | 3 GB | 18 GB | 36 GB |
| **Downloads/Certificate** | 2 | 2 | 2 |
| **Total Downloads/Month** | 100 | 1,000 | 2,000 |

### S3 Pricing (US East 1, as of Nov 2025)

**Storage Costs:**
| Storage Class | Monthly Cost (per GB) | 36 GB (12 months) |
|--------------|----------------------|-------------------|
| **S3 Standard** (0-90 days) | $0.023 | $0.83 |
| **S3 Standard-IA** (90 days - 1 year) | $0.0125 | $0.45 |
| **S3 Glacier Flexible** (1-7 years) | $0.004 | $0.14 |

**Request Costs:**
| Request Type | Cost (per 1,000) | Monthly Requests | Monthly Cost |
|-------------|------------------|------------------|--------------|
| **PUT** (uploads) | $0.005 | 1,200 (1k certs × 1.2 files) | $0.006 |
| **GET** (downloads) | $0.0004 | 2,000 | $0.0008 |

**Data Transfer Costs:**
| Transfer Type | Cost (per GB) | Monthly Transfer | Monthly Cost |
|--------------|---------------|------------------|--------------|
| **OUT to Internet** (first 10 TB) | $0.09 | 2 GB (2k × 1MB) | $0.18 |

**Total Monthly Cost (12 Months):**
```
Storage:         $0.83 (Standard) + $0.45 (IA) + $0.14 (Glacier) = $1.42
Requests:        $0.006 (PUT) + $0.0008 (GET) = $0.0068
Data Transfer:   $0.18
-------------------------------------------------------------------
TOTAL:           ~$1.61/month (with lifecycle optimization)
```

**Without Lifecycle (All S3 Standard):**
```
Storage:         36 GB × $0.023 = $0.83
Requests:        $0.0068
Data Transfer:   $0.18
-------------------------------------------------------------------
TOTAL:           ~$1.02/month (first year only)
```

**Cost Projection (3-Year):**
| Year | Storage (GB) | S3 Cost | Lifecycle Savings | Total Cost |
|------|-------------|---------|-------------------|------------|
| **1** | 36 GB | $1.02/mo | $0 (all Standard) | $12.24/year |
| **2** | 72 GB | $1.61/mo | $0.41/mo (IA transition) | $19.32/year |
| **3** | 108 GB | $2.15/mo | $1.23/mo (IA + Glacier) | $25.80/year |

**Cost Comparison:**
| Solution | Monthly Cost | Annual Cost | Notes |
|----------|-------------|-------------|-------|
| **Local Storage** | $10 | $120 | 50GB disk allocation, daily backups |
| **S3 (No Lifecycle)** | $15 | $180 | All Standard storage |
| **S3 (With Lifecycle)** | $20 | $240 | Standard → IA → Glacier |
| **S3 + CloudFront** | $30 | $360 | Phase 8 (CDN distribution) |

**Verdict:** S3 with lifecycle is **$10-20/month** (within acceptable range), with significant operational benefits (durability, scalability, security).

### Cost Optimization Strategies

1. **Lifecycle Policies**: Transition to S3-IA after 90 days (50% cost reduction)
2. **Compression**: Gzip PDFs before upload (20-30% size reduction for text-heavy certificates)
3. **Intelligent-Tiering**: Auto-transition based on access patterns (Phase 8)
4. **CloudFront**: Cache at edge to reduce S3 GET requests and data transfer (Phase 8)
5. **Request Batching**: Bulk upload certificates (reduce PUT requests)

---

## 6. Lifecycle & Retention

### Lifecycle Policy Configuration

**Policy JSON:**
```json
{
  "Rules": [
    {
      "Id": "TransitionToIA",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "pdf/"
      },
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"
        }
      ]
    },
    {
      "Id": "TransitionToGlacier",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "pdf/"
      },
      "Transitions": [
        {
          "Days": 365,
          "StorageClass": "GLACIER"
        }
      ]
    },
    {
      "Id": "DeleteAfterRetention",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "pdf/"
      },
      "Expiration": {
        "Days": 2555
      }
    }
  ]
}
```

**Transition Timeline:**
```
Day 0:    Upload to S3 Standard (active certificates)
Day 90:   Auto-transition to S3 Standard-IA (inactive certificates)
Day 365:  Auto-transition to S3 Glacier Flexible (archive)
Day 2555: Auto-delete (7-year retention limit)
```

**Retention Justification:**
- **0-90 Days**: Active verification period (tournament winners share certificates)
- **90 Days - 1 Year**: Reference period (dispute resolution, portfolio evidence)
- **1-7 Years**: Compliance/archive (legal hold for tax/audit purposes)
- **7 Years**: Standard business record retention (IRS, GDPR, CCPA compliance)

### Versioning Strategy

**S3 Versioning**: Enabled

**Use Cases:**
- **Accidental Deletion**: Recover deleted certificates via version history
- **Certificate Reissue**: Preserve original certificate if regenerated with corrections
- **Audit Trail**: Track certificate modifications over time

**Version Lifecycle:**
```json
{
  "Rules": [
    {
      "Id": "DeleteOldVersions",
      "Status": "Enabled",
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 30
      }
    }
  ]
}
```

**Rationale:** Keep non-current versions for 30 days (rollback window), then delete to reduce storage costs.

---

## 7. Migration Strategy

### Phase 1: Provisioning (Week 1, Ops Task)

**Steps:**
1. **Create S3 Bucket**
   - Name: `deltacrown-certificates-prod`
   - Region: `us-east-1`
   - Versioning: Enabled
   - Encryption: SSE-S3 (AES256)
   - Block Public Access: Enabled (all 4 settings)

2. **Configure Bucket Policy**
   - Deny unencrypted uploads
   - Deny insecure transport (HTTP)
   - Restrict to IAM role/user

3. **Create IAM Role/User**
   - Attach least-privilege policy (PutObject, GetObject, DeleteObject)
   - Generate access keys (development) or assign EC2 role (production)

4. **Enable Lifecycle Policy**
   - Transition to S3-IA after 90 days
   - Transition to Glacier after 1 year
   - Delete after 7 years

5. **Configure Logging**
   - S3 server access logs → `s3://deltacrown-logs/s3-access/`
   - CloudTrail data events (production only)

**Checklist:** See `Documents/Runbooks/S3_OPERATIONS_CHECKLIST.md`

### Phase 2: Staging Tests (Week 2-3, Phase 7)

**Environment:**
- **Staging**: `deltacrown-certificates-staging` (separate bucket)
- **Settings**: `USE_S3_FOR_CERTS=true` in `.env.staging`

**Tests:**
1. **Certificate Generation**: Generate new certificate → verify S3 upload
2. **Presigned URL**: Access certificate via presigned URL → verify download
3. **Expiration**: Wait 11 minutes → verify URL expired (403)
4. **Encryption**: `aws s3api head-object` → verify `ServerSideEncryption: AES256`
5. **Integrity**: Compare ETag or SHA-256 checksum → verify no corruption
6. **Performance**: Measure presigned URL generation latency (<100ms p95)

**Acceptance:** All tests pass, no 403/404 errors, latency within SLA.

### Phase 3: Dual-Write (Week 4-5, Phase 7)

**Strategy:**
```python
# apps/tournaments/services/certificate_service.py (Phase 7)

def save_certificate(certificate, file_content):
    """
    Save certificate to both local and S3 storage (dual-write).
    
    Rollback-safe: Keep local storage as backup during transition.
    """
    # Save to local storage (existing behavior)
    local_path = default_storage.save(certificate.file.name, file_content)
    
    if settings.USE_S3_FOR_CERTIFICATES:
        # Save to S3 (new behavior)
        s3_storage = S3Boto3Storage()
        s3_path = s3_storage.save(certificate.file.name, file_content)
        
        # Verify S3 upload (ETag check)
        s3_etag = s3_storage.bucket.Object(s3_path).e_tag
        if not s3_etag:
            logger.error(f"S3 upload failed for {certificate.uuid}: missing ETag")
            # Continue with local storage (fallback)
        else:
            logger.info(f"S3 upload successful for {certificate.uuid}: {s3_path}")
    
    return local_path
```

**Duration:** 30 days (monitor for issues, allow rollback)

**Monitoring:**
- S3 upload success rate (target: 100%)
- S3 upload failures → Slack alert
- Disk usage (should stabilize, not increase)

### Phase 4: Background Migration (Week 6-8, Phase 7)

**Script:** `scripts/migrate_certificates_to_s3.py`

**Algorithm:**
1. Query all `Certificate` objects with `file` stored locally
2. For each certificate:
   - Check if already migrated (`migrated_to_s3_at IS NOT NULL`)
   - If not, upload to S3 using presigned PUT
   - Verify upload (ETag or SHA-256)
   - Update `Certificate.migrated_to_s3_at = now()`
   - Log success/failure
3. Batch process (100 certificates per run, idempotent)
4. Report summary (total, migrated, skipped, failed)

**Execution:**
```bash
# Dry-run (report only)
python scripts/migrate_certificates_to_s3.py --dry-run

# Migrate all certificates
python scripts/migrate_certificates_to_s3.py --batch-size 100

# Migrate specific tournament
python scripts/migrate_certificates_to_s3.py --tournament-id 123
```

**Duration:** 1-2 weeks (background task, avoid peak hours)

**Validation:**
- Spot-check 10 random certificates → verify S3 access
- Compare local vs S3 file sizes → verify integrity
- Test presigned URLs → verify downloads work

### Phase 5: Switch to S3 Primary (Week 9, Phase 7)

**Change:**
```python
# deltacrown/settings.py (Phase 7)
USE_S3_FOR_CERTIFICATES = True  # Flip flag (production only)
```

**Deployment:**
- Deploy during low-traffic window (3am UTC)
- Monitor for 24 hours (certificate generation, downloads)
- Rollback if 403/404 rate exceeds 1%

**Validation:**
- Generate 10 test certificates → verify S3 storage
- Access 100 random certificates → verify presigned URLs work
- Check CloudWatch metrics → verify no 403 spikes

### Phase 6: Deprecate Local Storage (Week 17, Phase 7)

**Cleanup:**
- Keep local storage for 60 days post-migration (safety buffer)
- Archive local files to S3 `_archive/` prefix (compliance)
- Delete local files after 60 days (free disk space)

**Final Checklist:**
- ✅ All certificates accessible via S3 presigned URLs
- ✅ No 403/404 errors on production for 60 days
- ✅ Local files archived to S3
- ✅ Disk space reclaimed (20GB+)

---

## 8. Rollback Plan

### Trigger Conditions

1. **403 Forbidden Spike**: >5% of certificate downloads fail with 403 (IAM policy issue)
2. **5xx Errors**: S3 service outage or latency >1s (p95)
3. **Cost Overrun**: AWS bill exceeds $50/month (budget alert)
4. **Data Loss**: Certificate missing from S3 (integrity validation failure)

### Rollback Procedure

**Step 1: Revert Settings Flag (5 minutes)**
```python
# deltacrown/settings.py (emergency revert)
USE_S3_FOR_CERTIFICATES = False  # Switch back to local storage
```

**Step 2: Deploy (10 minutes)**
- Deploy revert commit to production
- Verify app restarts successfully
- Test certificate generation → verify local storage active

**Step 3: Restore Local Files (if needed, 30 minutes)**
- If local files were deleted prematurely:
  ```bash
  # Download all S3 objects back to local storage
  aws s3 sync s3://deltacrown-certificates-prod/pdf/ media/certificates/
  aws s3 sync s3://deltacrown-certificates-prod/images/ media/certificates/images/
  ```

**Step 4: Monitor (24 hours)**
- Verify certificate downloads work (local URLs)
- Check disk space (ensure local storage sufficient)
- Investigate S3 failure root cause (IAM policy, bucket policy, AWS outage)

### Dual-Write Safety Net

**During 30-day transition:**
- All certificates saved to both local and S3
- Rollback: Simply flip `USE_S3_FOR_CERTS=false` (no data loss)
- Local files remain intact (no deletion during dual-write)

**After 60-day stabilization:**
- Local files archived to S3 `_archive/` prefix (backup)
- Rollback: Restore from S3 archive (30-minute RTO)

---

## 9. Risks & Mitigations

### Risk 1: S3 Outage → Certificates Unavailable

**Likelihood:** Low (S3 SLA: 99.99% uptime = 4.38 minutes/month)

**Impact:** High (users cannot download certificates, tournament winners unable to share)

**Mitigations:**
1. **CloudFront CDN** (Phase 8): Cache certificates at edge locations (200+ global PoPs)
2. **S3 Cross-Region Replication** (Phase 8): Backup to `us-west-2` (auto-failover)
3. **Presigned URL Caching**: Cache Django-generated URLs for 5 minutes (reduce S3 dependency)
4. **Graceful Degradation**: Display "Certificate temporarily unavailable" message, retry after 5 minutes

**Monitoring:**
- CloudWatch alarm: S3 5xx errors >5/minute → PagerDuty alert
- Status page: Display AWS S3 status (https://status.aws.amazon.com/)

### Risk 2: AWS Bill Spike (GET Flood Attack)

**Likelihood:** Medium (public presigned URLs could be scraped/abused)

**Impact:** Medium ($100-500/month if 10M requests/month)

**Mitigations:**
1. **Short TTL**: 10-minute presigned URL expiration (limit reuse window)
2. **CloudFront Rate Limiting** (Phase 8): 100 requests/minute per IP (WAF rule)
3. **AWS Budgets**: Alert when monthly cost exceeds $50 (SMS + email)
4. **IP Allowlist** (optional): Restrict presigned URL generation to DeltaCrown IPs only (extreme measure)

**Monitoring:**
- CloudWatch alarm: S3 GET requests >10k/hour (anomaly detection)
- AWS Cost Explorer: Daily cost tracking, alert on 50% week-over-week increase

### Risk 3: Link Instability (Presigned URLs Expire)

**Likelihood:** Medium (users may bookmark or share expired URLs)

**Impact:** Low (403 errors, but regeneratable)

**Mitigations:**
1. **Short TTL with Regeneration**: Generate fresh presigned URL on every page load (not stored in DB)
2. **Django View Caching**: Cache presigned URL for 5 minutes (balance freshness vs performance)
3. **User Education**: Display "Link expires in 10 minutes" message on certificate page
4. **CloudFront Signed Cookies** (Phase 8): Long-lived signed cookies (1-hour session) for better UX

**Monitoring:**
- Track 403 rate on `/api/tournaments/certificates/{uuid}/download/` endpoint
- Log expired URL access attempts (analytics for TTL tuning)

### Risk 4: PII Exposure (Object Keys Leak User Info)

**Likelihood:** Low (if guidelines followed)

**Impact:** Critical (GDPR violation, user privacy breach)

**Mitigations:**
1. **UUID-Only Filenames**: Enforce UUID v4 in certificate generation (no usernames, emails, tournament names)
2. **Code Review**: Require PR approval for any changes to certificate storage logic
3. **Automated Tests**: Unit test verifying no PII in S3 keys (`test_certificate_filename_no_pii()`)
4. **S3 Metadata Audit**: Quarterly review of object metadata (ensure no `user_email` tags)

**Monitoring:**
- Pre-commit hook: Scan code for hardcoded usernames/emails in S3 keys
- Quarterly compliance audit: Sample 100 S3 keys → verify UUID format

### Risk 5: Data Corruption (Upload/Download Integrity)

**Likelihood:** Very Low (S3 data integrity: 99.999999999%)

**Impact:** High (corrupted certificates unusable, tournament reputation damage)

**Mitigations:**
1. **ETag Verification**: Compare S3 ETag after upload (MD5 hash for single-part uploads)
2. **SHA-256 Checksum** (optional): Store checksum in `Certificate.sha256_hash` field, verify on download
3. **S3 Versioning**: Recover from accidental overwrites (30-day version retention)
4. **Spot Checks**: Weekly automated test downloading 10 random certificates → verify PDF integrity

**Monitoring:**
- Log ETag mismatches during upload (should be 0)
- Alert on corrupted PDF errors (PDF parse failure during download)

**Trade-offs:**
- **ETag**: Fast (no compute), but multipart uploads use different algorithm (not MD5)
- **SHA-256**: Accurate (compute hash before upload), but adds 50-100ms latency per certificate

**Recommendation:** Use ETag for standard uploads (<5MB), add SHA-256 for large certificates (>5MB).

### Risk 6: Migration Data Loss

**Likelihood:** Low (if dual-write + validation implemented)

**Impact:** Critical (lost certificates unrecoverable)

**Mitigations:**
1. **Dual-Write Phase**: Keep local files for 30 days (rollback safety net)
2. **Idempotent Migration**: Script checks `migrated_to_s3_at` timestamp (skip already-migrated certificates)
3. **Dry-Run Mode**: Test migration script on staging (validate logic before production)
4. **Post-Migration Validation**: Compare local vs S3 file counts, spot-check 100 random certificates

**Monitoring:**
- Migration progress dashboard (total, migrated, skipped, failed)
- Alert on migration failure rate >1%

---

## 10. Monitoring & Alerts

### CloudWatch Metrics

**S3 Bucket Metrics (Enhanced Monitoring):**
| Metric | Threshold | Action |
|--------|-----------|--------|
| `NumberOfObjects` | <1000 (unexpected drop) | Alert: Potential mass deletion |
| `BucketSizeBytes` | >100GB (unexpected growth) | Alert: Investigate storage spike |
| `AllRequests` | >10k/hour (anomaly) | Alert: Potential abuse or attack |
| `4xxErrors` | >5% of requests | Alert: IAM policy or bucket policy issue |
| `5xxErrors` | >1% of requests | Alert: S3 service issue |
| `FirstByteLatency` | >500ms (p95) | Warn: S3 slow response |

**Application Metrics (Django):**
| Metric | Threshold | Action |
|--------|-----------|--------|
| `certificate_upload_success_rate` | <99% | Alert: S3 upload failures |
| `presigned_url_generation_latency` | >100ms (p95) | Warn: Boto3 slow |
| `certificate_download_403_rate` | >1% | Alert: Presigned URL issues |
| `certificate_download_404_rate` | >0.5% | Alert: Missing certificates |

### CloudWatch Alarms

**Example Alarm (Terraform):**
```hcl
resource "aws_cloudwatch_metric_alarm" "s3_upload_failures" {
  alarm_name          = "deltacrown-certificates-upload-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "certificate_upload_failures"
  namespace           = "DeltaCrown/Tournaments"
  period              = 300  # 5 minutes
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alert when S3 certificate uploads fail"
  alarm_actions       = [aws_sns_topic.ops_alerts.arn]
}
```

**Alert Destinations:**
- **Slack**: `#ops-alerts` channel (low-priority: warnings)
- **PagerDuty**: On-call engineer (high-priority: 403 spikes, 5xx errors)
- **Email**: Engineering lead (budget alerts, compliance issues)

### Logging

**S3 Server Access Logs:**
- **Format**: Apache-style log (space-delimited)
- **Fields**: Bucket owner, bucket, time, remote IP, requester, operation, key, HTTP status, error code, bytes sent
- **Retention**: 90 days (lifecycle policy)
- **Query**: AWS Athena (SQL queries on logs)

**Example Query (Find 403 Errors):**
```sql
SELECT time, remote_ip, requester, key, http_status
FROM s3_access_logs
WHERE http_status = '403'
  AND date >= '2025-11-01'
ORDER BY time DESC
LIMIT 100;
```

**CloudTrail Data Events (Optional):**
- **Enable**: Production only (cost: ~$5-10/month)
- **Events**: PutObject, GetObject, DeleteObject
- **Benefits**: IAM user attribution, API call details, CloudWatch Logs integration
- **Query**: CloudWatch Logs Insights (filter by IAM user, time range)

**Example Query (Find Uploads by User):**
```cloudwatch-insights
fields @timestamp, userIdentity.principalId, requestParameters.key
| filter eventName = "PutObject"
| filter requestParameters.bucketName = "deltacrown-certificates-prod"
| sort @timestamp desc
| limit 100
```

### Dashboard

**CloudWatch Dashboard (Example):**
```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "S3 Upload Success Rate",
        "metrics": [
          ["DeltaCrown/Tournaments", "certificate_upload_success_rate"]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "yAxis": {"left": {"min": 0, "max": 100}}
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Presigned URL Generation Latency (p95)",
        "metrics": [
          ["DeltaCrown/Tournaments", "presigned_url_latency", {"stat": "p95"}]
        ],
        "period": 300,
        "region": "us-east-1",
        "yAxis": {"left": {"min": 0, "max": 200}}
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Certificate Download Errors (403 + 404)",
        "metrics": [
          ["AWS/S3", "4xxErrors", {"stat": "Sum"}],
          [".", "5xxErrors", {"stat": "Sum"}]
        ],
        "period": 300,
        "region": "us-east-1"
      }
    }
  ]
}
```

---

## 11. Implementation Checklist

### Phase 7 (Q1-Q2 2026)

**Week 1: Provisioning**
- [ ] Create S3 bucket `deltacrown-certificates-prod` (us-east-1)
- [ ] Enable versioning
- [ ] Configure bucket policy (deny unencrypted, deny HTTP)
- [ ] Create IAM role/user with least-privilege policy
- [ ] Generate access keys (dev) or assign EC2 role (prod)
- [ ] Enable S3 server access logs
- [ ] Configure lifecycle policy (Standard → IA @90d → Glacier @1y → delete @7y)
- [ ] Set up CloudWatch alarms (403 spikes, 5xx errors)

**Week 2-3: Staging Tests**
- [ ] Install `django-storages[s3]==1.14.2` and `boto3==1.34.16`
- [ ] Create `settings_s3.py` (staging config)
- [ ] Set `USE_S3_FOR_CERTS=true` in staging `.env`
- [ ] Generate test certificate → verify S3 upload
- [ ] Access certificate via presigned URL → verify download
- [ ] Wait 11 minutes → verify URL expired (403)
- [ ] Run `aws s3api head-object` → verify encryption (SSE-S3)
- [ ] Compare ETag or SHA-256 → verify integrity
- [ ] Measure presigned URL latency (<100ms p95)

**Week 4-5: Dual-Write**
- [ ] Implement dual-write logic (save to local + S3)
- [ ] Deploy to production with `USE_S3_FOR_CERTS=true`
- [ ] Monitor S3 upload success rate (target: 100%)
- [ ] Set up Slack alerts for S3 upload failures
- [ ] Keep local storage (no deletion)
- [ ] Run for 30 days (stability validation)

**Week 6-8: Background Migration**
- [ ] Implement `scripts/migrate_certificates_to_s3.py`
- [ ] Test dry-run mode (verify report accuracy)
- [ ] Run migration in batches (100 certs per run)
- [ ] Verify ETag or SHA-256 after each batch
- [ ] Update `Certificate.migrated_to_s3_at` timestamp
- [ ] Log summary (total, migrated, skipped, failed)
- [ ] Spot-check 10 random certificates (manual verification)

**Week 9: Switch to S3 Primary**
- [ ] Flip `USE_S3_FOR_CERTS=true` in production (all new certs to S3 only)
- [ ] Deploy during low-traffic window (3am UTC)
- [ ] Monitor for 24 hours (certificate generation, downloads)
- [ ] Verify no 403/404 spikes (target: <1%)
- [ ] Test rollback procedure (flip flag back to local)

**Week 17: Deprecate Local Storage**
- [ ] Archive local files to S3 `_archive/` prefix (compliance)
- [ ] Delete local files after 60-day stabilization period
- [ ] Reclaim disk space (20GB+)
- [ ] Document S3-only workflow in runbook
- [ ] Update onboarding docs (new developers use S3 from day 1)

---

## 12. References

### AWS Documentation
- [S3 Storage Classes](https://aws.amazon.com/s3/storage-classes/)
- [S3 Lifecycle Policies](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html)
- [S3 Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html)
- [S3 Encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingEncryption.html)
- [IAM Policies for S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-policies-s3.html)

### Django Integration
- [django-storages Documentation](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

### Cost Calculators
- [AWS Pricing Calculator](https://calculator.aws/)
- [S3 Cost Estimator](https://aws.amazon.com/s3/pricing/)

### DeltaCrown Planning Docs
- `PHASE_6_IMPLEMENTATION_PLAN.md` (Module 6.5 scope)
- `02_TECHNICAL_STANDARDS.md` (security standards, PII guidelines)
- `PROPOSAL_PART_2_TECHNICAL_ARCHITECTURE.md` (storage architecture decisions)

---

## Appendix A: Example Presigned URL

**Request:**
```python
from django.core.files.storage import default_storage

url = default_storage.url('pdf/2025/11/a3f8e9c7-4b21-4d1a-8e3f-9c7a4b218e3f.pdf', expire=600)
```

**Generated URL:**
```
https://deltacrown-certificates-prod.s3.us-east-1.amazonaws.com/pdf/2025/11/a3f8e9c7-4b21-4d1a-8e3f-9c7a4b218e3f.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAIOSFODNN7EXAMPLE%2F20251110%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20251110T120000Z&X-Amz-Expires=600&X-Amz-SignedHeaders=host&X-Amz-Signature=abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab
```

**URL Components:**
- **Bucket**: `deltacrown-certificates-prod.s3.us-east-1.amazonaws.com`
- **Key**: `pdf/2025/11/a3f8e9c7-4b21-4d1a-8e3f-9c7a4b218e3f.pdf`
- **Algorithm**: AWS4-HMAC-SHA256 (Signature Version 4)
- **Credential**: IAM access key ID + date + region + service
- **Date**: ISO 8601 format (20251110T120000Z)
- **Expires**: 600 seconds (10 minutes)
- **Signature**: HMAC-SHA256 signature (prevents tampering)

**Expiration Behavior:**
- **Before 10 minutes**: HTTP 200 OK (file download)
- **After 10 minutes**: HTTP 403 Forbidden (`Request has expired`)

---

## Appendix B: Migration Script Output (Example)

**Dry-Run:**
```bash
$ python scripts/migrate_certificates_to_s3.py --dry-run

[INFO] Starting migration (dry-run mode)
[INFO] Found 150 certificates to migrate

[DRY-RUN] Would upload: media/certificates/2025/11/cert_001.pdf → s3://...pdf/2025/11/a3f8e9c7.pdf
[DRY-RUN] Would upload: media/certificates/2025/11/cert_002.pdf → s3://...pdf/2025/11/b4d9f8a1.pdf
...
[INFO] Migration summary (dry-run):
  Total certificates: 150
  Would migrate: 150
  Would skip (already in S3): 0
  Errors: 0
```

**Actual Migration:**
```bash
$ python scripts/migrate_certificates_to_s3.py --batch-size 100

[INFO] Starting migration (batch size: 100)
[INFO] Found 150 certificates to migrate

[SUCCESS] Uploaded: cert_001.pdf → s3://...pdf/2025/11/a3f8e9c7.pdf (ETag: "abc123...")
[SUCCESS] Uploaded: cert_002.pdf → s3://...pdf/2025/11/b4d9f8a1.pdf (ETag: "def456...")
...
[SKIP] Already migrated: cert_050.pdf (migrated_to_s3_at: 2025-11-05)
...
[ERROR] Upload failed: cert_099.pdf (Boto3Error: Network timeout)
[RETRY] Retrying: cert_099.pdf (attempt 2/3)
[SUCCESS] Uploaded: cert_099.pdf → s3://...pdf/2025/11/c5e0g9b2.pdf (ETag: "ghi789...")

[INFO] Migration complete
  Total certificates: 150
  Migrated: 149
  Skipped (already in S3): 0
  Failed: 1 (see logs for details)
```

---

## 13. Future Enhancements (Phase 8+)

### Versioned Key Prefix (v1/)

**Use Case:** Support future migrations or storage schema changes without breaking existing certificates.

**Implementation:**
```python
# Current key structure (Phase 7)
pdf/2025/11/a3f8e9c7-4b21-4d1a-8e3f-9c7a4b218e3f.pdf

# Future versioned structure (Phase 8+)
v1/pdf/2025/11/a3f8e9c7-4b21-4d1a-8e3f-9c7a4b218e3f.pdf
v2/pdf/2025/11/a3f8e9c7-4b21-4d1a-8e3f-9c7a4b218e3f.pdf  # New format
```

**Benefits:**
- Gradual rollout of new certificate formats (e.g., v2 with watermarks, digital signatures)
- Parallel operation during migration (v1 and v2 coexist)
- Clear deprecation path (lifecycle policy targets `v1/` prefix after cutover)

**Tradeoffs:**
- Adds complexity to key generation logic
- Increases key length (4 bytes per object)
- Requires version-aware presigned URL generation

**Recommendation:** Defer to Phase 8 unless multiple certificate formats are planned within 12 months.

### PDF Hash in S3 Object Metadata

**Use Case:** Independent integrity verification without database access (e.g., AWS Lambda spot-check script).

**Implementation:**
```python
# Upload with metadata
s3_client.put_object(
    Bucket='deltacrown-certificates-prod',
    Key='pdf/2025/11/uuid.pdf',
    Body=file_content,
    Metadata={
        'sha256': 'abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab',
        'tournament_id': '123',
        'placement': '1',
        'generated_at': '2025-11-10T12:00:00Z'
    }
)

# Verify without database
response = s3_client.head_object(Bucket='...', Key='...')
s3_sha256 = response['Metadata']['sha256']
# Compare against freshly computed hash
```

**Benefits:**
- Spot-check integrity without Certificate model query
- Audit trail preserved in S3 (survives database restore)
- AWS Lambda can run weekly integrity checks (compute hash from S3 object, compare metadata)

**Tradeoffs:**
- Increases PUT request size (~100 bytes metadata per object)
- Metadata immutable after upload (cannot fix without re-upload)
- Redundant with Certificate.sha256_hash DB field (adds storage cost)

**Recommendation:** Add in Phase 7 if weekly integrity spot-checks are required (low operational overhead).

### CloudFront CDN Adoption Thresholds

**When to Add CloudFront:**

| Metric | Threshold | Action |
|--------|-----------|--------|
| **Avg Latency (p50)** | >200ms globally | Add CloudFront (cache at edge, <50ms p50) |
| **Download Volume** | >1M requests/month | CloudFront reduces S3 GET costs (cache hit ratio 80%+) |
| **Geographic Distribution** | >30% users outside US-East-1 | CloudFront edge locations (200+ global PoPs) |
| **Bandwidth Cost** | >$100/month S3 transfer | CloudFront cheaper ($0.085/GB vs $0.09/GB S3) |
| **Availability SLA** | >99.99% required | CloudFront multi-region failover + S3 replication |

**Implementation Considerations:**
- **Signed URLs vs Signed Cookies**: Signed cookies better UX (1-hour session vs 10-min URLs), but requires session management
- **Cache Invalidation**: Manual invalidation costs $0.005 per path (batch invalidations recommended)
- **Origin Failover**: Primary origin S3 us-east-1, failover origin S3 us-west-2 (cross-region replication)
- **WAF Integration**: Rate limiting (100 req/min per IP), geo-blocking (if needed)

**Cost Model (1M requests/month):**
- S3 Direct: $0.40 GET + $90 transfer = **$90.40/month**
- CloudFront: $0.08 GET (20% cache miss) + $85 transfer (80% cache hit) = **$85.08/month**
- Savings: ~6% ($5/month), but adds operational complexity

**Recommendation:** Add CloudFront when monthly download volume exceeds 1M requests OR p50 latency >200ms for >30% users.

### Multi-Region Retention & Compliance

**Jurisdictional Requirements:**

| Region | Retention Period | Regulation | Notes |
|--------|------------------|------------|-------|
| **US** | 7 years | IRS (tax records) | Default retention policy |
| **EU** | 6 years | GDPR (Art. 17) | Right to erasure (soft delete 30d buffer) |
| **UK** | 7 years | HMRC (VAT records) | Post-Brexit alignment with IRS |
| **Canada** | 6 years | CRA (business records) | Shorter retention |
| **Australia** | 7 years | ATO (tax records) | Alignment with IRS |

**Multi-Region Strategy:**

**Option A: Single Bucket with Regional Tagging**
```python
# Tag objects by user jurisdiction
s3_client.put_object_tagging(
    Bucket='deltacrown-certificates-prod',
    Key='pdf/2025/11/uuid.pdf',
    Tagging={'TagSet': [{'Key': 'jurisdiction', 'Value': 'EU'}]}
)

# Lifecycle policy per jurisdiction
{
  "Rules": [
    {
      "Id": "DeleteEU6Years",
      "Filter": {"Tag": {"Key": "jurisdiction", "Value": "EU"}},
      "Expiration": {"Days": 2190}  # 6 years
    },
    {
      "Id": "DeleteUS7Years",
      "Filter": {"Tag": {"Key": "jurisdiction", "Value": "US"}},
      "Expiration": {"Days": 2555}  # 7 years
    }
  ]
}
```

**Option B: Regional Buckets**
- `deltacrown-certificates-us-prod` (us-east-1, 7-year retention)
- `deltacrown-certificates-eu-prod` (eu-west-1, 6-year retention)
- `deltacrown-certificates-ap-prod` (ap-southeast-2, 7-year retention)

**Tradeoffs:**
- **Option A**: Simpler (1 bucket), but requires tagging discipline and complex lifecycle rules
- **Option B**: Regional compliance isolation, but adds operational overhead (3 buckets, 3 IAM policies, 3 monitoring dashboards)

**Recommendation:** Use Option A (single bucket with tagging) unless GDPR data residency requirements mandate EU data in eu-west-1 (then use Option B for EU only).

**GDPR Right to Erasure:**
- Soft delete: Mark `Certificate.deleted_at` timestamp, keep S3 object for 30 days (compliance buffer for audits)
- Hard delete: After 30 days, delete S3 object (via lifecycle policy or Lambda trigger)
- Audit trail: Log deletion events in CloudTrail (7-year retention for audit compliance)

---

## Document Metadata

**Version:** 1.1  
**Last Updated:** November 10, 2025  
**Authors:** Backend Team  
**Reviewers:** Engineering Lead, DevOps Team  
**Approval Status:** Planning Complete (Implementation: Phase 7)  

**Change Log:**
- 2025-11-10: Initial version (Module 6.5 planning)
- 2025-11-10: Added Section 13 - Future Enhancements (versioned keys, hash metadata, CloudFront thresholds, multi-region compliance)

**Next Review:** Q1 2026 (before Phase 7 implementation)
