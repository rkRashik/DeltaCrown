"""
S3 Storage Configuration for Certificate Storage

Status: EXAMPLE FILE - NOT ACTIVE
Module: 6.5 - Certificate Storage Planning (S3 Migration)
Phase: Phase 7 Implementation (Q1 2026)

This file contains example settings for migrating certificate storage from
local MEDIA_ROOT to AWS S3. These settings are NOT active in production yet.

Usage:
1. Copy settings to deltacrown/settings.py (Phase 7)
2. Set USE_S3_FOR_CERTS=true in .env
3. Configure AWS credentials (IAM role or access keys)
4. Test in staging before production deployment

Security:
- Private objects (no public-read ACL)
- Presigned URLs with 10-minute TTL
- Encryption at rest (SSE-S3 or SSE-KMS)
- Deny unencrypted uploads (bucket policy)
- Enforce SSL/TLS (bucket policy)

Cost: ~$15-25/month (see S3_MIGRATION_DESIGN.md for breakdown)
"""

# ==============================================================================
# S3 STORAGE CONFIGURATION (Phase 7 - Not Active Yet)
# ==============================================================================

# ------------------------------------------------------------------------------
# Feature Flag: Enable S3 for Certificate Storage
# ------------------------------------------------------------------------------
# Set to True in production .env to activate S3 storage
# Set to False to use local MEDIA_ROOT (current behavior)
USE_S3_FOR_CERTIFICATES = env.bool('USE_S3_FOR_CERTS', default=False)

if USE_S3_FOR_CERTIFICATES:
    
    # --------------------------------------------------------------------------
    # AWS Credentials
    # --------------------------------------------------------------------------
    # IMPORTANT: Use IAM role in production (EC2 instance profile or ECS task role)
    # Only use access keys for development/staging
    
    # Option 1: IAM Role (Recommended for Production)
    # - Attach IAM role to EC2 instance or ECS task
    # - Boto3 automatically uses instance metadata credentials
    # - No need to set AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY
    
    # Option 2: Access Keys (Development/Staging Only)
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
    
    # WARNING: Never commit access keys to version control
    # Rotate access keys every 90 days (see S3_OPERATIONS_CHECKLIST.md)
    
    # --------------------------------------------------------------------------
    # S3 Bucket Configuration
    # --------------------------------------------------------------------------
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='deltacrown-certificates-prod')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')
    
    # CloudFront CDN (Phase 8 - Optional)
    # AWS_S3_CUSTOM_DOMAIN = 'certificates.deltacrown.com'  # CloudFront distribution
    AWS_S3_CUSTOM_DOMAIN = None  # Use direct S3 URLs (Phase 7)
    
    # --------------------------------------------------------------------------
    # Security Settings
    # --------------------------------------------------------------------------
    
    # Private Objects (No Public Access)
    AWS_DEFAULT_ACL = None  # Do NOT set to 'public-read' (violates security policy)
    
    # Presigned URLs (Required for Private Objects)
    AWS_QUERYSTRING_AUTH = True  # Enable presigned URL generation
    AWS_QUERYSTRING_EXPIRE = 600  # 10 minutes (600 seconds)
    
    # Encryption at Rest
    # Option 1: SSE-S3 (AWS-Managed Keys - Recommended)
    AWS_S3_ENCRYPTION = 'AES256'  # Server-side encryption with AES-256
    
    # Option 2: SSE-KMS (Customer-Managed Keys - If Already Using KMS)
    # AWS_S3_ENCRYPTION = 'aws:kms'
    # AWS_S3_KMS_KEY_ID = env('AWS_S3_KMS_KEY_ID', default='')
    # Example: 'arn:aws:kms:us-east-1:123456789012:key/abcd1234-ab12-cd34-ef56-1234567890ab'
    
    # File Overwrite Protection
    AWS_S3_FILE_OVERWRITE = False  # Prevent accidental overwrites (UUID naming prevents collisions)
    
    # --------------------------------------------------------------------------
    # Object Parameters (Applied to All Uploads)
    # --------------------------------------------------------------------------
    AWS_S3_OBJECT_PARAMETERS = {
        # Cache Control (Client-Side Caching)
        'CacheControl': 'private, max-age=600',  # 10 minutes browser cache
        
        # Content Disposition (Display in Browser)
        'ContentDisposition': 'inline',  # Display PDF in browser, not download
        
        # Server-Side Encryption (Enforce Encryption)
        'ServerSideEncryption': AWS_S3_ENCRYPTION,  # 'AES256' or 'aws:kms'
    }
    
    # If using SSE-KMS, add KMS key ID to object parameters
    # if AWS_S3_ENCRYPTION == 'aws:kms':
    #     AWS_S3_OBJECT_PARAMETERS['SSEKMSKeyId'] = AWS_S3_KMS_KEY_ID
    
    # --------------------------------------------------------------------------
    # Storage Backend
    # --------------------------------------------------------------------------
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    # Custom Storage Class (Alternative Approach - Allows Multiple Storages)
    # CERTIFICATE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    # In models.py:
    #   file = models.FileField(upload_to='pdf/%Y/%m/', storage=get_storage_class(settings.CERTIFICATE_STORAGE)())
    
    # --------------------------------------------------------------------------
    # Advanced Settings (Optional)
    # --------------------------------------------------------------------------
    
    # S3 Endpoint URL (For AWS GovCloud or LocalStack Testing)
    # AWS_S3_ENDPOINT_URL = 'http://localhost:4566'  # LocalStack
    # AWS_S3_ENDPOINT_URL = 'https://s3-us-gov-west-1.amazonaws.com'  # GovCloud
    
    # S3 Signature Version (Default: s3v4)
    AWS_S3_SIGNATURE_VERSION = 's3v4'  # Use Signature Version 4 (required for SSE-KMS)
    
    # S3 Addressing Style (Default: auto)
    AWS_S3_ADDRESSING_STYLE = 'auto'  # 'virtual' (https://bucket.s3.region.com) or 'path' (https://s3.region.com/bucket)
    
    # S3 Transfer Config (For Large Files >5MB)
    AWS_S3_MAX_MEMORY_SIZE = 5242880  # 5 MB (use multipart upload for larger files)
    AWS_S3_USE_THREADS = True  # Enable concurrent uploads (faster for large files)
    
    # S3 Connection Timeout (Avoid Hanging Requests)
    AWS_S3_CONNECTION_TIMEOUT = 60  # 60 seconds (boto3 default)
    AWS_S3_MAX_POOL_CONNECTIONS = 10  # Max concurrent connections
    
    # --------------------------------------------------------------------------
    # Logging & Monitoring
    # --------------------------------------------------------------------------
    
    # Enable DEBUG logging for django-storages (Development Only)
    # LOGGING['loggers']['storages'] = {
    #     'handlers': ['console'],
    #     'level': 'DEBUG',
    # }
    
    # Track S3 upload success/failure metrics
    # See S3_MIGRATION_DESIGN.md Section 10 for CloudWatch metrics

else:
    # --------------------------------------------------------------------------
    # Local Storage (Current Behavior)
    # --------------------------------------------------------------------------
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_ROOT = BASE_DIR / 'media'
    MEDIA_URL = '/media/'

# ==============================================================================
# BUCKET POLICY (AWS Console or Terraform)
# ==============================================================================
"""
Apply this bucket policy to deltacrown-certificates-prod (Phase 7):

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
"""

# ==============================================================================
# IAM POLICY (Least Privilege)
# ==============================================================================
"""
Attach this IAM policy to EC2 role or IAM user (Phase 7):

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
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::deltacrown-certificates-prod",
        "arn:aws:s3:::deltacrown-certificates-prod/*"
      ],
      "Condition": {
        "StringEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    }
  ]
}
"""

# ==============================================================================
# ENVIRONMENT VARIABLES (.env)
# ==============================================================================
"""
Add these to .env (Phase 7):

# S3 Storage (Production)
USE_S3_FOR_CERTS=true
AWS_STORAGE_BUCKET_NAME=deltacrown-certificates-prod
AWS_S3_REGION_NAME=us-east-1

# AWS Credentials (Development/Staging Only - Use IAM Role in Production)
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# Optional: KMS Encryption (If Using Customer-Managed Keys)
# AWS_S3_KMS_KEY_ID=arn:aws:kms:us-east-1:123456789012:key/abcd1234
"""

# ==============================================================================
# DEPENDENCIES (requirements.txt)
# ==============================================================================
"""
Add these packages to requirements.txt (Phase 7):

django-storages[s3]==1.14.2
boto3==1.34.16
"""

# ==============================================================================
# MIGRATION CHECKLIST
# ==============================================================================
"""
Before enabling S3 in production:

1. ✅ Provision S3 bucket (see S3_OPERATIONS_CHECKLIST.md)
2. ✅ Configure bucket policy (deny unencrypted, deny HTTP)
3. ✅ Create IAM role/user with least-privilege policy
4. ✅ Enable S3 server access logs
5. ✅ Set lifecycle policy (Standard → IA @90d → Glacier @1y → delete @7y)
6. ✅ Test in staging (generate certificate → verify S3 upload)
7. ✅ Verify presigned URL expiration (wait 11 minutes → 403)
8. ✅ Verify encryption (aws s3api head-object → ServerSideEncryption: AES256)
9. ✅ Monitor for 30 days (dual-write phase)
10. ✅ Flip USE_S3_FOR_CERTS=true in production

See S3_MIGRATION_DESIGN.md for full migration strategy.
"""
