# S3 Operations Checklist

**Status:** Planning Artifact (Phase 7 Implementation)  
**Module:** 6.5 - Certificate Storage Planning (S3 Migration)  
**Owner:** DevOps Team  
**Last Updated:** November 10, 2025  

---

## Table of Contents

1. [Bucket Provisioning](#1-bucket-provisioning)
2. [IAM Role & Policy Configuration](#2-iam-role--policy-configuration)
3. [Bucket Policy & Encryption](#3-bucket-policy--encryption)
4. [Lifecycle & Retention](#4-lifecycle--retention)
5. [Logging & Monitoring](#5-logging--monitoring)
6. [Credential Rotation](#6-credential-rotation)
7. [Staging Environment Setup](#7-staging-environment-setup)
8. [Production Deployment](#8-production-deployment)
9. [Emergency Rollback](#9-emergency-rollback)
10. [Routine Maintenance](#10-routine-maintenance)

---

## 1. Bucket Provisioning

### AWS Console Method

**Step 1: Create Bucket**
- [ ] Sign in to AWS Management Console
- [ ] Navigate to **S3** service
- [ ] Click **Create bucket**
- [ ] Bucket name: `deltacrown-certificates-prod` (must be globally unique)
- [ ] AWS Region: **US East (N. Virginia) - us-east-1**
- [ ] Object Ownership: **Bucket owner enforced** (disable ACLs)
- [ ] Block Public Access: **Enable all 4 settings** (block all public access)
  - [ ] ✅ Block public access to buckets and objects granted through new access control lists (ACLs)
  - [ ] ✅ Block public access to buckets and objects granted through any access control lists (ACLs)
  - [ ] ✅ Block public access to buckets and objects granted through new public bucket or access point policies
  - [ ] ✅ Block public access to buckets and objects granted through any public bucket or access point policies
- [ ] Bucket Versioning: **Enable**
- [ ] Default encryption: **SSE-S3 (AES-256)** or **SSE-KMS** (if using customer-managed keys)
- [ ] Bucket Key: **Enable** (reduce KMS request costs if using SSE-KMS)
- [ ] Click **Create bucket**

**Step 2: Verify Bucket Created**
```bash
aws s3 ls s3://deltacrown-certificates-prod/
```
Expected: Empty bucket (no objects yet)

**Step 3: Create Folder Structure (Optional)**
```bash
aws s3api put-object --bucket deltacrown-certificates-prod --key pdf/
aws s3api put-object --bucket deltacrown-certificates-prod --key images/
aws s3api put-object --bucket deltacrown-certificates-prod --key _metadata/
```

### Terraform Method (Infrastructure as Code)

**File:** `infrastructure/terraform/s3.tf`

```hcl
# S3 Bucket for Certificate Storage
resource "aws_s3_bucket" "certificates" {
  bucket = "deltacrown-certificates-prod"
  
  tags = {
    Name        = "DeltaCrown Certificates"
    Environment = "Production"
    ManagedBy   = "Terraform"
  }
}

# Block Public Access (All 4 Settings)
resource "aws_s3_bucket_public_access_block" "certificates" {
  bucket = aws_s3_bucket.certificates.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Versioning
resource "aws_s3_bucket_versioning" "certificates" {
  bucket = aws_s3_bucket.certificates.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-Side Encryption (SSE-S3)
resource "aws_s3_bucket_server_side_encryption_configuration" "certificates" {
  bucket = aws_s3_bucket.certificates.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"  # Or "aws:kms" with kms_master_key_id
    }
    bucket_key_enabled = true
  }
}
```

**Deploy:**
```bash
cd infrastructure/terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

**Verify:**
```bash
terraform state show aws_s3_bucket.certificates
```

---

## 2. IAM Role & Policy Configuration

### Option A: IAM Role (Production - Recommended)

**Step 1: Create IAM Policy**
- [ ] Sign in to AWS Management Console
- [ ] Navigate to **IAM** service
- [ ] Click **Policies** → **Create policy**
- [ ] Select **JSON** tab
- [ ] Paste policy JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CertificateStorageAccess",
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

- [ ] Click **Next: Tags**
- [ ] Add tags (optional): `Environment=Production`, `ManagedBy=DevOps`
- [ ] Click **Next: Review**
- [ ] Policy name: `DeltaCrownCertificateStoragePolicy`
- [ ] Click **Create policy**

**Step 2: Create IAM Role (EC2)**
- [ ] Navigate to **IAM** → **Roles** → **Create role**
- [ ] Trusted entity type: **AWS service**
- [ ] Use case: **EC2**
- [ ] Click **Next**
- [ ] Attach policy: **DeltaCrownCertificateStoragePolicy**
- [ ] Click **Next**
- [ ] Role name: `DeltaCrownEC2CertificateStorageRole`
- [ ] Click **Create role**

**Step 3: Attach Role to EC2 Instance**
- [ ] Navigate to **EC2** → **Instances**
- [ ] Select production instance
- [ ] **Actions** → **Security** → **Modify IAM role**
- [ ] Select **DeltaCrownEC2CertificateStorageRole**
- [ ] Click **Update IAM role**

**Step 4: Verify Role Attached**
```bash
# SSH into EC2 instance
ssh ec2-user@deltacrown-prod

# Check IAM role
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/

# Expected: DeltaCrownEC2CertificateStorageRole
```

### Option B: IAM User (Development/Staging)

**Step 1: Create IAM User**
- [ ] Navigate to **IAM** → **Users** → **Create user**
- [ ] User name: `deltacrown-s3-dev`
- [ ] Access type: **Programmatic access** (access key & secret)
- [ ] Click **Next: Permissions**
- [ ] Attach policy: **DeltaCrownCertificateStoragePolicy** (created above)
- [ ] Click **Next: Tags** → **Next: Review** → **Create user**

**Step 2: Download Credentials**
- [ ] Download `.csv` with access key ID and secret access key
- [ ] **IMPORTANT**: Store securely (1Password, AWS Secrets Manager)
- [ ] **DO NOT** commit to version control

**Step 3: Configure Django `.env`**
```bash
# .env.staging
USE_S3_FOR_CERTS=true
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_STORAGE_BUCKET_NAME=deltacrown-certificates-staging
AWS_S3_REGION_NAME=us-east-1
```

**Step 4: Test Access**
```bash
python scripts/migrate_certificates_to_s3.py --dry-run
```
Expected: No IAM permission errors

---

## 3. Bucket Policy & Encryption

### Bucket Policy (Deny Unencrypted Uploads + Insecure Transport)

**Step 1: Create Bucket Policy**
- [ ] Navigate to **S3** → **deltacrown-certificates-prod** → **Permissions**
- [ ] Scroll to **Bucket policy** → **Edit**
- [ ] Paste policy JSON:

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
    },
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

- [ ] Click **Save changes**

**Step 2: Verify Bucket Policy**
```bash
aws s3api get-bucket-policy --bucket deltacrown-certificates-prod --query Policy --output text | jq .
```
Expected: See both `DenyUnencryptedObjectUploads` and `DenyInsecureTransport` statements

**Step 3: Test Encryption Enforcement**
```bash
# Try to upload without encryption (should fail)
echo "test" > test.txt
aws s3 cp test.txt s3://deltacrown-certificates-prod/test.txt --no-server-side-encryption

# Expected: Access Denied error (403)

# Upload with encryption (should succeed)
aws s3 cp test.txt s3://deltacrown-certificates-prod/test.txt --server-side-encryption AES256

# Verify encryption
aws s3api head-object --bucket deltacrown-certificates-prod --key test.txt --query ServerSideEncryption

# Expected: "AES256"
```

### KMS Encryption (Optional - Customer-Managed Keys)

**Step 1: Create KMS Key**
- [ ] Navigate to **KMS** → **Customer managed keys** → **Create key**
- [ ] Key type: **Symmetric**
- [ ] Key usage: **Encrypt and decrypt**
- [ ] Alias: `deltacrown/certificates`
- [ ] Key administrators: Add IAM users/roles (admin access)
- [ ] Key users: Add IAM role `DeltaCrownEC2CertificateStorageRole`
- [ ] Click **Finish**

**Step 2: Update Bucket Policy (KMS)**
```json
{
  "Sid": "DenyUnencryptedObjectUploads",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:PutObject",
  "Resource": "arn:aws:s3:::deltacrown-certificates-prod/*",
  "Condition": {
    "StringNotEquals": {
      "s3:x-amz-server-side-encryption": "aws:kms"
    }
  }
}
```

**Step 3: Update Django Settings**
```python
AWS_S3_ENCRYPTION = 'aws:kms'
AWS_S3_KMS_KEY_ID = 'arn:aws:kms:us-east-1:123456789012:key/abcd1234-ab12-cd34-ef56-1234567890ab'
```

**Step 4: Test KMS Encryption**
```bash
aws s3 cp test.txt s3://deltacrown-certificates-prod/test.txt --server-side-encryption aws:kms --ssekms-key-id alias/deltacrown/certificates
aws s3api head-object --bucket deltacrown-certificates-prod --key test.txt --query ServerSideEncryption

# Expected: "aws:kms"
```

---

## 4. Lifecycle & Retention

### Lifecycle Policy Configuration

**Step 1: Create Lifecycle Rule**
- [ ] Navigate to **S3** → **deltacrown-certificates-prod** → **Management** → **Lifecycle rules**
- [ ] Click **Create lifecycle rule**
- [ ] Rule name: `TransitionCertificatesToArchive`
- [ ] Scope: **Apply to all objects in the bucket** (or prefix filter `pdf/`, `images/`)
- [ ] Lifecycle rule actions:
  - [ ] ✅ **Transition current versions of objects between storage classes**
  - [ ] ✅ **Permanently delete previous versions of objects**
- [ ] Transition current versions:
  - [ ] Transition to **Standard-IA** after **90 days**
  - [ ] Transition to **Glacier Flexible Retrieval** after **365 days** (1 year)
- [ ] Expire current versions:
  - [ ] **Delete objects** after **2555 days** (7 years)
- [ ] Delete previous versions:
  - [ ] **Delete noncurrent versions** after **30 days**
- [ ] Click **Create rule**

**Step 2: Verify Lifecycle Policy**
```bash
aws s3api get-bucket-lifecycle-configuration --bucket deltacrown-certificates-prod
```

Expected JSON:
```json
{
  "Rules": [
    {
      "ID": "TransitionCertificatesToArchive",
      "Status": "Enabled",
      "Filter": {},
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 365,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 2555
      },
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 30
      }
    }
  ]
}
```

### Terraform Lifecycle Policy

```hcl
resource "aws_s3_bucket_lifecycle_configuration" "certificates" {
  bucket = aws_s3_bucket.certificates.id

  rule {
    id     = "TransitionCertificatesToArchive"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555  # 7 years
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}
```

---

## 5. Logging & Monitoring

### S3 Server Access Logs

**Step 1: Create Logs Bucket**
- [ ] Create bucket: `deltacrown-logs` (same region as certificates bucket)
- [ ] Block public access: **Enable all 4 settings**
- [ ] Versioning: **Disabled** (not needed for logs)

**Step 2: Enable Server Access Logging**
- [ ] Navigate to **S3** → **deltacrown-certificates-prod** → **Properties**
- [ ] Scroll to **Server access logging** → **Edit**
- [ ] Enable: **Yes**
- [ ] Target bucket: `deltacrown-logs`
- [ ] Target prefix: `s3-access/deltacrown-certificates-prod/`
- [ ] Click **Save changes**

**Step 3: Verify Logging**
```bash
# Wait 15-30 minutes for first logs
aws s3 ls s3://deltacrown-logs/s3-access/deltacrown-certificates-prod/

# Expected: Log files (format: YYYY-MM-DD-HH-MM-SS-UniqueString)
```

**Step 4: Query Logs (AWS Athena)**
```sql
-- Create table for S3 access logs
CREATE EXTERNAL TABLE IF NOT EXISTS s3_access_logs (
  bucket_owner STRING,
  bucket STRING,
  request_time STRING,
  remote_ip STRING,
  requester STRING,
  operation STRING,
  key STRING,
  http_status STRING,
  error_code STRING,
  bytes_sent BIGINT
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.RegexSerDe'
WITH SERDEPROPERTIES (
  'serialization.format' = '1',
  'input.regex' = '([^ ]*) ([^ ]*) \\[(.*?)\\] ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) "([^ ]*) ([^ ]*) ([^ ]*)" ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) "([^"]*)" "([^"]*)"'
)
LOCATION 's3://deltacrown-logs/s3-access/deltacrown-certificates-prod/';

-- Query 403 errors
SELECT request_time, remote_ip, requester, key, http_status
FROM s3_access_logs
WHERE http_status = '403'
  AND request_time >= '2025-11-01'
ORDER BY request_time DESC
LIMIT 100;
```

### CloudTrail Data Events (Optional - Production Only)

**Step 1: Enable CloudTrail**
- [ ] Navigate to **CloudTrail** → **Trails** → **Create trail**
- [ ] Trail name: `deltacrown-s3-data-events`
- [ ] Storage location: Create new S3 bucket or use existing `deltacrown-logs`
- [ ] Log file SSE-KMS encryption: **Enabled** (recommended)
- [ ] Click **Next**
- [ ] Management events: **Disabled** (focus on S3 data events only)
- [ ] Data events:
  - [ ] ✅ **S3**
  - [ ] Bucket: `deltacrown-certificates-prod`
  - [ ] Event types: **All** (Read + Write)
- [ ] Click **Next** → **Create trail**

**Step 2: Verify CloudTrail**
```bash
aws cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::S3::Object --max-results 10
```

**Cost:** ~$0.10 per 100,000 data events (~$5-10/month for 1M requests)

### CloudWatch Alarms

**Alarm 1: S3 Upload Failures**
- [ ] Navigate to **CloudWatch** → **Alarms** → **Create alarm**
- [ ] Metric: **Custom** → Namespace: `DeltaCrown/Tournaments` → Metric: `certificate_upload_failures`
- [ ] Statistic: **Sum**
- [ ] Period: **5 minutes**
- [ ] Threshold: **Greater than 5**
- [ ] Evaluation periods: **2** (5 failures in 10 minutes)
- [ ] Action: SNS topic → `ops-alerts` (Slack integration)
- [ ] Alarm name: `deltacrown-s3-upload-failures`
- [ ] Click **Create alarm**

**Alarm 2: 403 Forbidden Spike**
- [ ] Metric: **AWS/S3** → `NumberOf4xxErrors` → Bucket: `deltacrown-certificates-prod`
- [ ] Statistic: **Sum**
- [ ] Period: **5 minutes**
- [ ] Threshold: **Greater than 10**
- [ ] Alarm name: `deltacrown-s3-403-spike`

**Alarm 3: Monthly Cost Threshold**
- [ ] Navigate to **AWS Budgets** → **Create budget**
- [ ] Budget type: **Cost budget**
- [ ] Name: `DeltaCrown-S3-Monthly-Budget`
- [ ] Budget amount: **$50/month**
- [ ] Alert threshold: **80%** (alert at $40/month)
- [ ] Email: `devops@deltacrown.com`
- [ ] Click **Create budget**

---

## 6. Credential Rotation

### IAM Access Key Rotation (Development/Staging)

**Schedule:** Every 90 days (quarterly)

**Step 1: Generate New Access Key**
- [ ] Navigate to **IAM** → **Users** → `deltacrown-s3-dev`
- [ ] **Security credentials** tab
- [ ] Click **Create access key**
- [ ] Download `.csv` with new credentials

**Step 2: Update Django `.env` (Staging)**
```bash
# .env.staging (OLD - backup before changing)
# AWS_ACCESS_KEY_ID=AKIAIOSFODNN7OLDKEY
# AWS_SECRET_ACCESS_KEY=old-secret-key

# .env.staging (NEW)
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7NEWKEY
AWS_SECRET_ACCESS_KEY=new-secret-key
```

**Step 3: Test New Credentials**
```bash
# Restart Django (staging)
sudo systemctl restart deltacrown-staging

# Test S3 access
python scripts/migrate_certificates_to_s3.py --dry-run

# Expected: No IAM errors
```

**Step 4: Deactivate Old Access Key**
- [ ] Navigate to **IAM** → **Users** → `deltacrown-s3-dev` → **Security credentials**
- [ ] Find old access key → **Actions** → **Deactivate**
- [ ] Monitor for 7 days (ensure no errors)
- [ ] After 7 days → **Actions** → **Delete**

### IAM Role Rotation (Production)

**No rotation needed** (IAM roles use temporary credentials via STS, auto-rotated every 15 minutes)

**Verify Role Active:**
```bash
# SSH into EC2 instance
ssh ec2-user@deltacrown-prod

# Check STS credentials
aws sts get-caller-identity

# Expected: RoleId with session name
```

---

## 7. Staging Environment Setup

**Step 1: Create Staging Bucket**
- [ ] Bucket name: `deltacrown-certificates-staging`
- [ ] Region: `us-east-1`
- [ ] Settings: Same as production (encryption, versioning, block public access)

**Step 2: Create IAM User (Staging)**
- [ ] User name: `deltacrown-s3-staging`
- [ ] Attach policy: `DeltaCrownCertificateStoragePolicy` (update Resource ARN to staging bucket)

**Step 3: Configure Django (Staging)**
```bash
# .env.staging
USE_S3_FOR_CERTS=true
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7STAGING
AWS_SECRET_ACCESS_KEY=staging-secret-key
AWS_STORAGE_BUCKET_NAME=deltacrown-certificates-staging
AWS_S3_REGION_NAME=us-east-1
```

**Step 4: Run Staging Tests**
- [ ] Generate test certificate (staging)
- [ ] Verify S3 upload (check AWS console)
- [ ] Access presigned URL (download certificate)
- [ ] Wait 11 minutes → verify URL expired (403)
- [ ] Check S3 encryption (`aws s3api head-object`)

---

## 8. Production Deployment

**Prerequisites:**
- [ ] ✅ Staging tests passed (7 days stable)
- [ ] ✅ Bucket policy configured (deny unencrypted)
- [ ] ✅ IAM role attached to EC2 instance
- [ ] ✅ Lifecycle policy configured
- [ ] ✅ CloudWatch alarms created
- [ ] ✅ S3 access logs enabled

**Step 1: Enable S3 (Dual-Write Phase)**
```bash
# .env.production
USE_S3_FOR_CERTS=true  # Enable S3 (keep local storage)
```

**Step 2: Deploy Django**
```bash
git pull origin master
sudo systemctl restart deltacrown-production
```

**Step 3: Monitor (30 Days)**
- [ ] Check S3 upload success rate (target: 100%)
- [ ] Monitor CloudWatch alarms (no 403/5xx spikes)
- [ ] Verify disk usage stable (not increasing)

**Step 4: Background Migration**
```bash
# Migrate existing certificates to S3
python scripts/migrate_certificates_to_s3.py --batch-size 100
```

**Step 5: Switch to S3 Primary (After 30 Days)**
```bash
# .env.production (no change - already using S3)
# Local storage kept as backup
```

**Step 6: Deprecate Local Storage (After 60 Days)**
```bash
# Archive local files to S3
aws s3 sync media/certificates/ s3://deltacrown-certificates-prod/_archive/

# Delete local files (free disk space)
rm -rf media/certificates/*
```

---

## 9. Emergency Rollback

### Trigger Conditions
- [ ] 403 Forbidden rate >5% (IAM policy issue)
- [ ] 5xx errors >1% (S3 service issue)
- [ ] Monthly cost >$50 (unexpected bill spike)
- [ ] Certificate missing from S3 (data loss)

### Rollback Procedure (15 Minutes)

**Step 1: Revert Settings Flag**
```bash
# .env.production
USE_S3_FOR_CERTS=false  # Switch back to local storage
```

**Step 2: Deploy**
```bash
git revert HEAD  # Revert S3 settings commit
sudo systemctl restart deltacrown-production
```

**Step 3: Verify Local Storage Active**
```bash
# Generate test certificate
python manage.py shell
>>> from apps.tournaments.services import generate_certificate
>>> certificate = generate_certificate(tournament_id=123)
>>> print(certificate.file.path)
# Expected: /media/certificates/YYYY/MM/uuid.pdf (local path)
```

**Step 4: Restore Local Files (If Deleted)**
```bash
# Download all S3 objects back to local storage
aws s3 sync s3://deltacrown-certificates-prod/pdf/ media/certificates/
aws s3 sync s3://deltacrown-certificates-prod/images/ media/certificates/images/
```

**Step 5: Monitor (24 Hours)**
- [ ] Verify certificate downloads work (local URLs)
- [ ] Check disk space (ensure sufficient)
- [ ] Investigate S3 failure root cause

**Step 6: Post-Mortem**
- [ ] Document failure cause (IAM policy, bucket policy, AWS outage)
- [ ] Update runbook with lessons learned
- [ ] Fix underlying issue before retrying S3 migration

---

## 10. Routine Maintenance

### Weekly Tasks
- [ ] Check S3 upload success rate (CloudWatch dashboard)
- [ ] Verify no 403/404 spikes (CloudWatch alarms)
- [ ] Review S3 access logs (anomalies, abuse)

### Monthly Tasks
- [ ] Review AWS bill (S3 costs vs budget)
- [ ] Check S3 storage growth (GB/month trend)
- [ ] Verify lifecycle transitions (Standard → IA → Glacier)

### Quarterly Tasks
- [ ] Rotate IAM access keys (development/staging)
- [ ] Audit S3 bucket policy (no unauthorized changes)
- [ ] Review IAM role permissions (least-privilege compliance)
- [ ] Test emergency rollback procedure (staging)

### Annual Tasks
- [ ] Review lifecycle policy (adjust retention if needed)
- [ ] Audit S3 object metadata (no PII in keys)
- [ ] Review cost optimization strategies (Intelligent-Tiering, CloudFront)
- [ ] Update KMS key rotation policy (if using SSE-KMS)

---

## Appendix: Terraform Complete Example

```hcl
# S3 Bucket
resource "aws_s3_bucket" "certificates" {
  bucket = "deltacrown-certificates-prod"
  
  tags = {
    Name        = "DeltaCrown Certificates"
    Environment = "Production"
  }
}

# Block Public Access
resource "aws_s3_bucket_public_access_block" "certificates" {
  bucket = aws_s3_bucket.certificates.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Versioning
resource "aws_s3_bucket_versioning" "certificates" {
  bucket = aws_s3_bucket.certificates.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Encryption (SSE-S3)
resource "aws_s3_bucket_server_side_encryption_configuration" "certificates" {
  bucket = aws_s3_bucket.certificates.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Bucket Policy (Deny Unencrypted + HTTP)
resource "aws_s3_bucket_policy" "certificates" {
  bucket = aws_s3_bucket.certificates.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyUnencryptedObjectUploads"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.certificates.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "AES256"
          }
        }
      },
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.certificates.arn,
          "${aws_s3_bucket.certificates.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Lifecycle Policy
resource "aws_s3_bucket_lifecycle_configuration" "certificates" {
  bucket = aws_s3_bucket.certificates.id

  rule {
    id     = "TransitionToArchive"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555  # 7 years
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# IAM Policy
resource "aws_iam_policy" "certificate_storage" {
  name        = "DeltaCrownCertificateStoragePolicy"
  description = "Allow S3 access for certificate storage"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CertificateStorageAccess"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.certificates.arn,
          "${aws_s3_bucket.certificates.arn}/*"
        ]
        Condition = {
          StringEquals = {
            "s3:x-amz-server-side-encryption" = "AES256"
          }
        }
      }
    ]
  })
}

# IAM Role (EC2)
resource "aws_iam_role" "ec2_certificate_storage" {
  name = "DeltaCrownEC2CertificateStorageRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Attach Policy to Role
resource "aws_iam_role_policy_attachment" "ec2_certificate_storage" {
  role       = aws_iam_role.ec2_certificate_storage.name
  policy_arn = aws_iam_policy.certificate_storage.arn
}

# Instance Profile
resource "aws_iam_instance_profile" "ec2_certificate_storage" {
  name = "DeltaCrownEC2CertificateStorageProfile"
  role = aws_iam_role.ec2_certificate_storage.name
}
```

---

## Document Metadata

**Version:** 1.0  
**Last Updated:** November 10, 2025  
**Author:** DevOps Team  
**Reviewers:** Backend Team, Engineering Lead  
**Next Review:** Q1 2026 (before Phase 7 implementation)  

**Related Documents:**
- `S3_MIGRATION_DESIGN.md` (Migration strategy)
- `settings_s3.example.py` (Django configuration)
- `scripts/migrate_certificates_to_s3.py` (Migration script)
