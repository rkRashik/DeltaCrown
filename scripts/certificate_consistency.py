"""
Certificate Consistency Checker

Validates consistency between S3 and local storage:
- Object counts match
- ETags/MD5 hashes match
- Identifies orphaned/missing files

Usage:
    python scripts/certificate_consistency.py --check-hashes
    python scripts/certificate_consistency.py --fix-orphans --dry-run

Exit codes:
    0: All checks passed (OK)
    1: Warnings (count mismatch but correctable)
    2: Errors (hash mismatches or corruption detected)
"""

import os
import sys
import argparse
import hashlib
import logging
from pathlib import Path
from collections import defaultdict

# Django setup
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.conf import settings
from apps.tournaments.storage import CertificateS3Storage

logger = logging.getLogger(__name__)


def compute_md5(file_path):
    """Compute MD5 hash of file."""
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def check_consistency(check_hashes=False, fix_orphans=False, dry_run=False):
    """
    Check consistency between S3 and local storage.
    
    Args:
        check_hashes: Validate MD5/ETag for each file
        fix_orphans: Delete orphaned files (local-only or S3-only)
        dry_run: Don't modify files, just report
    
    Returns:
        dict: Status and findings
    """
    storage = CertificateS3Storage()
    media_root = Path(settings.MEDIA_ROOT)
    
    results = {
        'status': 'OK',
        'local_count': 0,
        's3_count': 0,
        'matched_count': 0,
        'orphaned_local': [],
        'orphaned_s3': [],
        'hash_mismatches': [],
        'errors': []
    }
    
    # Get local files
    local_files = {
        str(p.relative_to(media_root)).replace('\\', '/'): p
        for p in media_root.rglob('*.pdf')
    }
    results['local_count'] = len(local_files)
    logger.info(f"Found {results['local_count']} local files")
    
    # Get S3 files
    s3_files = set()
    if storage.s3_storage:
        try:
            # List all S3 objects
            from storages.backends.s3boto3 import S3Boto3Storage
            s3_bucket = storage.s3_storage.bucket
            for obj in s3_bucket.objects.all():
                s3_files.add(obj.key)
        except Exception as e:
            logger.error(f"Failed to list S3 objects: {e}")
            results['errors'].append(f"S3 list error: {e}")
            results['status'] = 'ERROR'
            return results
    elif storage.s3_client:
        # Use direct client (testing)
        try:
            response = storage.s3_client.list_objects_v2(Bucket=storage.bucket_name)
            s3_files = {obj['Key'] for obj in response.get('Contents', [])}
        except Exception as e:
            logger.error(f"Failed to list S3 objects: {e}")
            results['errors'].append(f"S3 list error: {e}")
            results['status'] = 'ERROR'
            return results
    
    results['s3_count'] = len(s3_files)
    logger.info(f"Found {results['s3_count']} S3 objects")
    
    # Find matched and orphaned files
    local_keys = set(local_files.keys())
    results['matched_count'] = len(local_keys & s3_files)
    results['orphaned_local'] = list(local_keys - s3_files)
    results['orphaned_s3'] = list(s3_files - local_keys)
    
    # Count mismatch → WARNING
    if results['local_count'] != results['s3_count']:
        results['status'] = 'WARNING'
        logger.warning(
            f"Count mismatch: local={results['local_count']}, s3={results['s3_count']}"
        )
    
    # Hash validation (if requested)
    if check_hashes:
        logger.info("Validating hashes...")
        for key in (local_keys & s3_files):
            try:
                local_path = local_files[key]
                local_md5 = compute_md5(local_path)
                
                # Get S3 ETag
                if storage.s3_client:
                    response = storage.s3_client.head_object(
                        Bucket=storage.bucket_name,
                        Key=key
                    )
                    s3_etag = response['ETag'].strip('"')
                elif storage.s3_storage:
                    s3_obj = storage.s3_storage.connection.meta.client.head_object(
                        Bucket=storage.bucket_name,
                        Key=key
                    )
                    s3_etag = s3_obj['ETag'].strip('"')
                else:
                    continue
                
                if local_md5 != s3_etag:
                    mismatch = {
                        'key': key,
                        'local_md5': local_md5,
                        's3_etag': s3_etag
                    }
                    results['hash_mismatches'].append(mismatch)
                    logger.error(f"HASH MISMATCH: {key}")
            
            except Exception as e:
                logger.error(f"Hash check failed for {key}: {e}")
                results['errors'].append(f"Hash check error: {key} - {e}")
    
    # Hash mismatch → ERROR
    if results['hash_mismatches']:
        results['status'] = 'ERROR'
    
    # Fix orphans (if requested)
    if fix_orphans and not dry_run:
        logger.info("Fixing orphans...")
        
        # Delete orphaned local files
        for key in results['orphaned_local']:
            local_path = local_files[key]
            try:
                local_path.unlink()
                logger.info(f"DELETED local orphan: {key}")
            except Exception as e:
                logger.error(f"Failed to delete local orphan {key}: {e}")
                results['errors'].append(f"Delete error: {key}")
        
        # Delete orphaned S3 objects
        for key in results['orphaned_s3']:
            try:
                if storage.s3_client:
                    storage.s3_client.delete_object(Bucket=storage.bucket_name, Key=key)
                elif storage.s3_storage:
                    storage.s3_storage.delete(key)
                logger.info(f"DELETED S3 orphan: {key}")
            except Exception as e:
                logger.error(f"Failed to delete S3 orphan {key}: {e}")
                results['errors'].append(f"Delete error: {key}")
    
    return results


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Check certificate storage consistency')
    parser.add_argument('--check-hashes', action='store_true', help='Validate MD5/ETag hashes')
    parser.add_argument('--fix-orphans', action='store_true', help='Delete orphaned files')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no modifications)')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    # Run check
    results = check_consistency(
        check_hashes=args.check_hashes,
        fix_orphans=args.fix_orphans,
        dry_run=args.dry_run
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("CONSISTENCY CHECK RESULTS")
    print("=" * 60)
    print(f"Status: {results['status']}")
    print(f"Local files: {results['local_count']}")
    print(f"S3 objects: {results['s3_count']}")
    print(f"Matched: {results['matched_count']}")
    print(f"Orphaned (local-only): {len(results['orphaned_local'])}")
    print(f"Orphaned (S3-only): {len(results['orphaned_s3'])}")
    
    if args.check_hashes:
        print(f"Hash mismatches: {len(results['hash_mismatches'])}")
        if results['hash_mismatches']:
            print("\nHASH MISMATCHES:")
            for mismatch in results['hash_mismatches'][:10]:
                print(f"  {mismatch['key']}")
                print(f"    Local: {mismatch['local_md5']}")
                print(f"    S3:    {mismatch['s3_etag']}")
    
    if results['errors']:
        print(f"\nErrors: {len(results['errors'])}")
        for error in results['errors'][:10]:
            print(f"  - {error}")
    
    # Exit code
    if results['status'] == 'OK':
        print("\n✓ All checks passed")
        sys.exit(0)
    elif results['status'] == 'WARNING':
        print("\n⚠ Warnings detected (count mismatch)")
        sys.exit(1)
    else:  # ERROR
        print("\n✗ Errors detected (hash mismatches or failures)")
        sys.exit(2)


if __name__ == '__main__':
    main()
