"""
Certificate S3 Backfill Migration Script

Migrates existing local certificate files to S3 storage.

Usage:
    python scripts/backfill_certificates_to_s3.py --limit 100 --verify-hash
    python scripts/backfill_certificates_to_s3.py --resume-token abc123 --limit 1000

Features:
- Batch processing with --limit
- Resume capability with --resume-token
- Hash verification (MD5/ETag matching)
- Progress tracking
- Dry-run mode (--dry-run)

Environment:
- Requires CERT_S3_BACKFILL_ENABLED=True
- Reads from local MEDIA_ROOT
- Uploads to S3 bucket (AWS_STORAGE_BUCKET_NAME)
"""

import os
import sys
import argparse
import hashlib
import logging
from pathlib import Path
from datetime import datetime

# Django setup
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.conf import settings
from django.core.files.base import ContentFile
from apps.tournaments.storage import CertificateS3Storage

logger = logging.getLogger(__name__)


def compute_md5(file_path):
    """Compute MD5 hash of file."""
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def backfill_certificates(limit=None, resume_token=None, verify_hash=False, dry_run=False):
    """
    Backfill certificates from local storage to S3.
    
    Args:
        limit: Maximum number of files to process
        resume_token: File path to resume from (for pagination)
        verify_hash: Verify MD5/ETag matches after upload
        dry_run: Don't actually upload, just count
    
    Returns:
        dict: Statistics (uploaded_count, verified_count, errors)
    """
    if not getattr(settings, 'CERT_S3_BACKFILL_ENABLED', False):
        logger.error("CERT_S3_BACKFILL_ENABLED is False. Aborting.")
        return {'error': 'Backfill disabled'}
    
    storage = CertificateS3Storage()
    media_root = Path(settings.MEDIA_ROOT)
    
    # Find all PDF files
    all_files = sorted(media_root.rglob('*.pdf'))
    
    # Resume from token if provided
    start_idx = 0
    if resume_token:
        try:
            start_idx = next(i for i, p in enumerate(all_files) if str(p).endswith(resume_token))
            logger.info(f"Resuming from index {start_idx} (token: {resume_token})")
        except StopIteration:
            logger.warning(f"Resume token '{resume_token}' not found. Starting from beginning.")
    
    # Apply limit
    files_to_process = all_files[start_idx:start_idx + limit] if limit else all_files[start_idx:]
    
    stats = {
        'uploaded_count': 0,
        'verified_count': 0,
        'errors': [],
        'skipped_count': 0
    }
    
    logger.info(f"Processing {len(files_to_process)} files (dry_run={dry_run})")
    
    for file_path in files_to_process:
        try:
            # Compute relative key
            relative_path = file_path.relative_to(media_root)
            key = str(relative_path).replace('\\', '/')
            
            # Check if already in S3
            if storage.s3_storage and storage.s3_storage.exists(key):
                logger.info(f"SKIP: {key} (already in S3)")
                stats['skipped_count'] += 1
                continue
            
            if dry_run:
                logger.info(f"DRY-RUN: Would upload {key}")
                stats['uploaded_count'] += 1
                continue
            
            # Upload to S3
            with open(file_path, 'rb') as f:
                content = ContentFile(f.read())
                storage.save(key, content)
            
            stats['uploaded_count'] += 1
            logger.info(f"UPLOADED: {key}")
            
            # Verify hash if requested
            if verify_hash:
                local_md5 = compute_md5(file_path)
                
                # Get ETag from S3
                if storage.s3_client:
                    response = storage.s3_client.head_object(Bucket=storage.bucket_name, Key=key)
                    s3_etag = response['ETag'].strip('"')
                elif storage.s3_storage:
                    # Use boto3 client from storage
                    from storages.backends.s3boto3 import S3Boto3Storage
                    s3_obj = storage.s3_storage.connection.meta.client.head_object(
                        Bucket=storage.bucket_name,
                        Key=key
                    )
                    s3_etag = s3_obj['ETag'].strip('"')
                else:
                    logger.warning(f"Cannot verify hash (no S3 client): {key}")
                    continue
                
                if local_md5 == s3_etag:
                    stats['verified_count'] += 1
                    logger.info(f"VERIFIED: {key} (MD5 match)")
                else:
                    error = f"HASH MISMATCH: {key} (local={local_md5}, s3={s3_etag})"
                    logger.error(error)
                    stats['errors'].append(error)
        
        except Exception as e:
            error = f"ERROR: {file_path} - {e}"
            logger.error(error, exc_info=True)
            stats['errors'].append(error)
    
    return stats


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Backfill certificates to S3')
    parser.add_argument('--limit', type=int, help='Max files to process')
    parser.add_argument('--resume-token', help='File name to resume from')
    parser.add_argument('--verify-hash', action='store_true', help='Verify MD5/ETag after upload')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no uploads)')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    # Run backfill
    start_time = datetime.now()
    stats = backfill_certificates(
        limit=args.limit,
        resume_token=args.resume_token,
        verify_hash=args.verify_hash,
        dry_run=args.dry_run
    )
    duration = (datetime.now() - start_time).total_seconds()
    
    # Print summary
    print("\n" + "=" * 60)
    print("BACKFILL SUMMARY")
    print("=" * 60)
    print(f"Duration: {duration:.2f}s")
    print(f"Uploaded: {stats.get('uploaded_count', 0)}")
    print(f"Verified: {stats.get('verified_count', 0)}")
    print(f"Skipped: {stats.get('skipped_count', 0)}")
    print(f"Errors: {len(stats.get('errors', []))}")
    
    if stats.get('errors'):
        print("\nERRORS:")
        for error in stats['errors'][:10]:  # Show first 10
            print(f"  - {error}")
    
    # Exit code
    if stats.get('errors'):
        sys.exit(1)
    else:
        print("\n✓ Backfill completed successfully")
        sys.exit(0)


if __name__ == '__main__':
    main()
