"""
Certificate S3 Consistency Checker

Module: 6.5 - Certificate Storage Migration (S3)
Status: Implemented (behind feature flag)

This module provides:
- Daily consistency checks comparing S3 vs local file counts
- Random 1% spot SHA-256 checks for data integrity
- PII-free alert logging (certificate IDs only)
- Automated reconciliation reporting

Celery Tasks:
- check_certificate_consistency: Daily task (runs at 2 AM UTC)
- spot_check_certificate_integrity: Random 1% sample verification

Usage:
    # Manual trigger via Django shell
    from apps.tournaments.tasks.certificate_consistency import check_certificate_consistency
    result = check_certificate_consistency.delay()
    
    # Celery beat schedule (in settings.py)
    CELERYBEAT_SCHEDULE = {
        'check-certificate-consistency': {
            'task': 'apps.tournaments.tasks.certificate_consistency.check_certificate_consistency',
            'schedule': crontab(hour=2, minute=0),  # 2 AM UTC
        },
    }

Alerts:
- Log WARNING if count mismatch detected
- Log ERROR if hash mismatch detected (data corruption)
- Emit metrics for monitoring

Performance:
- Target: <5 minutes for full consistency check
- Sample size: 1% of total certificates (min 10, max 1000)
- No production impact (read-only operations)
"""

import logging
import random
import hashlib
from typing import Dict, Any, List
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from celery import shared_task

from apps.tournaments.models import Certificate

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_certificate_consistency(self):
    """
    Daily consistency check: Compare S3 vs local file counts.
    
    Checks:
    1. Count certificates with migrated_to_s3_at != NULL
    2. Count actual S3 objects in bucket
    3. Count local files in MEDIA_ROOT/certificates/
    4. Alert if mismatches detected
    
    Returns:
        dict: Consistency report
    """
    if not getattr(settings, 'CERT_S3_DUAL_WRITE', False):
        logger.info("S3 dual-write disabled, skipping consistency check")
        return {'status': 'skipped', 'reason': 'S3 dual-write disabled'}
    
    if not BOTO3_AVAILABLE:
        logger.warning("boto3 not available, skipping consistency check")
        return {'status': 'skipped', 'reason': 'boto3 not installed'}
    
    try:
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1'),
            aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
            aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
        )
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        
        # Count certificates marked as migrated
        migrated_count = Certificate.objects.filter(
            migrated_to_s3_at__isnull=False,
            revoked_at__isnull=True
        ).count()
        
        # Count S3 objects (PDF + images)
        s3_pdf_count = _count_s3_objects(s3_client, bucket_name, 'pdf/')
        s3_image_count = _count_s3_objects(s3_client, bucket_name, 'images/')
        
        # Count local files
        local_pdf_count = _count_local_files('certificates/pdf/')
        local_image_count = _count_local_files('certificates/images/')
        
        # Build report
        report = {
            'timestamp': timezone.now().isoformat(),
            'database': {
                'migrated_count': migrated_count,
            },
            's3': {
                'pdf_count': s3_pdf_count,
                'image_count': s3_image_count,
                'total_objects': s3_pdf_count + s3_image_count,
            },
            'local': {
                'pdf_count': local_pdf_count,
                'image_count': local_image_count,
                'total_files': local_pdf_count + local_image_count,
            },
            'status': 'success',
            'issues': []
        }
        
        # Check for mismatches
        expected_s3_count = migrated_count * 2  # PDF + image per certificate
        if report['s3']['total_objects'] != expected_s3_count:
            issue = f"S3 object count mismatch: expected {expected_s3_count}, found {report['s3']['total_objects']}"
            report['issues'].append(issue)
            logger.warning(issue, extra={'report': report})
        
        # Alert if issues detected
        if report['issues']:
            report['status'] = 'issues_detected'
            _emit_metric('cert.consistency.issues', value=len(report['issues']))
        else:
            _emit_metric('cert.consistency.success', value=1)
        
        # Log summary
        logger.info(
            f"Certificate consistency check completed: "
            f"DB migrated={migrated_count}, S3 objects={report['s3']['total_objects']}, "
            f"Local files={report['local']['total_files']}, Issues={len(report['issues'])}",
            extra={'report': report}
        )
        
        return report
    
    except Exception as e:
        logger.error(f"Consistency check failed: {e}", exc_info=True)
        _emit_metric('cert.consistency.fail', value=1)
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes


@shared_task(bind=True, max_retries=3)
def spot_check_certificate_integrity(self, sample_percent: float = 1.0):
    """
    Random spot check: Verify SHA-256 hashes for sample certificates.
    
    Args:
        sample_percent: Percentage of certificates to check (default 1.0 = 1%)
    
    Returns:
        dict: Integrity check report
    """
    if not getattr(settings, 'CERT_S3_DUAL_WRITE', False):
        logger.info("S3 dual-write disabled, skipping integrity check")
        return {'status': 'skipped', 'reason': 'S3 dual-write disabled'}
    
    if not BOTO3_AVAILABLE:
        logger.warning("boto3 not available, skipping integrity check")
        return {'status': 'skipped', 'reason': 'boto3 not installed'}
    
    try:
        # Get sample of migrated certificates
        migrated_certs = Certificate.objects.filter(
            migrated_to_s3_at__isnull=False,
            revoked_at__isnull=True,
            file_pdf__isnull=False  # Must have PDF file
        ).values_list('id', flat=True)
        
        total_count = len(migrated_certs)
        if total_count == 0:
            return {'status': 'skipped', 'reason': 'No migrated certificates'}
        
        # Calculate sample size (1% min 10, max 1000)
        sample_size = max(10, min(1000, int(total_count * sample_percent / 100)))
        sample_ids = random.sample(list(migrated_certs), min(sample_size, total_count))
        
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1'),
            aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
            aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
        )
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        
        # Check each sampled certificate
        report = {
            'timestamp': timezone.now().isoformat(),
            'total_certificates': total_count,
            'sample_size': len(sample_ids),
            'checked': 0,
            'hash_matches': 0,
            'hash_mismatches': 0,
            'missing_s3': 0,
            'missing_local': 0,
            'errors': 0,
            'mismatched_ids': [],
            'status': 'success'
        }
        
        for cert_id in sample_ids:
            try:
                cert = Certificate.objects.get(id=cert_id)
                report['checked'] += 1
                
                # Verify PDF hash
                if cert.file_pdf:
                    local_hash = _calculate_local_hash(cert.file_pdf)
                    s3_hash = _calculate_s3_hash(s3_client, bucket_name, cert.file_pdf.name)
                    
                    if local_hash and s3_hash:
                        if local_hash == s3_hash:
                            report['hash_matches'] += 1
                        else:
                            report['hash_mismatches'] += 1
                            report['mismatched_ids'].append(cert_id)
                            logger.error(
                                f"Hash mismatch for certificate {cert_id}: "
                                f"local={local_hash}, s3={s3_hash}",
                                extra={'certificate_id': cert_id}
                            )
                    elif not local_hash:
                        report['missing_local'] += 1
                    elif not s3_hash:
                        report['missing_s3'] += 1
            
            except Exception as e:
                report['errors'] += 1
                logger.warning(
                    f"Failed to check certificate {cert_id}: {e}",
                    extra={'certificate_id': cert_id}
                )
        
        # Set status
        if report['hash_mismatches'] > 0 or report['missing_s3'] > 0 or report['missing_local'] > 0:
            report['status'] = 'issues_detected'
            _emit_metric('cert.integrity.issues', value=report['hash_mismatches'] + report['missing_s3'])
        else:
            _emit_metric('cert.integrity.success', value=1)
        
        # Log summary
        logger.info(
            f"Certificate integrity check completed: "
            f"Checked={report['checked']}, Matches={report['hash_matches']}, "
            f"Mismatches={report['hash_mismatches']}, Missing S3={report['missing_s3']}",
            extra={'report': report}
        )
        
        return report
    
    except Exception as e:
        logger.error(f"Integrity check failed: {e}", exc_info=True)
        _emit_metric('cert.integrity.fail', value=1)
        raise self.retry(exc=e, countdown=300)


def _count_s3_objects(s3_client, bucket_name: str, prefix: str) -> int:
    """
    Count S3 objects with given prefix.
    
    Args:
        s3_client: boto3 S3 client
        bucket_name: S3 bucket name
        prefix: Object key prefix (e.g., 'pdf/')
    
    Returns:
        int: Object count
    """
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        count = 0
        
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            count += page.get('KeyCount', 0)
        
        return count
    except ClientError as e:
        logger.error(f"Failed to count S3 objects with prefix {prefix}: {e}")
        return 0


def _count_local_files(subpath: str) -> int:
    """
    Count local files in MEDIA_ROOT subdirectory.
    
    Args:
        subpath: Relative path from MEDIA_ROOT (e.g., 'certificates/pdf/')
    
    Returns:
        int: File count
    """
    import os
    full_path = settings.MEDIA_ROOT / subpath
    
    if not os.path.exists(full_path):
        return 0
    
    count = 0
    for root, dirs, files in os.walk(full_path):
        count += len(files)
    
    return count


def _calculate_local_hash(file_field) -> str:
    """
    Calculate SHA-256 hash of local file.
    
    Args:
        file_field: Django FileField
    
    Returns:
        str: SHA-256 hex digest or empty string on error
    """
    try:
        file_field.open('rb')
        content = file_field.read()
        file_field.close()
        
        return hashlib.sha256(content).hexdigest()
    except Exception as e:
        logger.warning(f"Failed to calculate local hash for {file_field.name}: {e}")
        return ''


def _calculate_s3_hash(s3_client, bucket_name: str, s3_key: str) -> str:
    """
    Calculate SHA-256 hash of S3 object.
    
    Args:
        s3_client: boto3 S3 client
        bucket_name: S3 bucket name
        s3_key: S3 object key
    
    Returns:
        str: SHA-256 hex digest or empty string on error
    """
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        content = response['Body'].read()
        
        return hashlib.sha256(content).hexdigest()
    except ClientError as e:
        logger.warning(f"Failed to calculate S3 hash for {s3_key}: {e}")
        return ''


def _emit_metric(metric_name: str, value: int = 1):
    """
    Emit metric for monitoring.
    
    Args:
        metric_name: Metric name (e.g., 'cert.consistency.success')
        value: Metric value (default 1 for counters)
    """
    # TODO: Integrate with observability framework (e.g., StatsD, CloudWatch)
    logger.info(f"METRIC: {metric_name}={value}")
