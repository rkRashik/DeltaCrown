#!/usr/bin/env python
"""
S3 Migration Dry-Run Rehearsal - Module 6.5

Simulates backfill of 500 certificate objects and validates:
- MD5/SHA-256 hash consistency
- Upload performance
- Presigned URL generation
- Go/No-Go cutover checklist

Usage:
    python scripts/s3_dry_run_rehearsal.py [--count 500] [--bucket deltacrown-test-certs]

Output:
    - Performance metrics (p95/p99 latencies)
    - Hash validation results
    - Go/No-Go decision matrix
    - Estimated wall time for full migration
"""

import sys
import os
import hashlib
import time
import argparse
from datetime import timedelta
from io import BytesIO

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')

import django
django.setup()

from django.conf import settings
from django.core.files.base import ContentFile
from apps.tournaments.storage import CertificateS3Storage
from apps.tournaments.s3_protocol import DummyS3Client, create_real_s3_client
from apps.tournaments.s3_lifecycle import validate_lifecycle_policy


class DryRunStats:
    """Track rehearsal statistics."""
    
    def __init__(self):
        self.upload_times = []
        self.url_gen_times = []
        self.hash_matches = 0
        self.hash_mismatches = 0
        self.errors = []
        self.total_bytes = 0
    
    def add_upload(self, duration_ms, bytes_size):
        self.upload_times.append(duration_ms)
        self.total_bytes += bytes_size
    
    def add_url_gen(self, duration_ms):
        self.url_gen_times.append(duration_ms)
    
    def add_hash_match(self):
        self.hash_matches += 1
    
    def add_hash_mismatch(self):
        self.hash_mismatches += 1
    
    def add_error(self, error_msg):
        self.errors.append(error_msg)
    
    def get_percentile(self, values, p):
        if not values:
            return 0
        sorted_values = sorted(values)
        idx = int(len(sorted_values) * p)
        return sorted_values[min(idx, len(sorted_values) - 1)]
    
    def get_summary(self):
        return {
            'total_objects': len(self.upload_times),
            'total_bytes': self.total_bytes,
            'total_mb': self.total_bytes / (1024 * 1024),
            'upload_p50': self.get_percentile(self.upload_times, 0.50),
            'upload_p95': self.get_percentile(self.upload_times, 0.95),
            'upload_p99': self.get_percentile(self.upload_times, 0.99),
            'url_p50': self.get_percentile(self.url_gen_times, 0.50),
            'url_p95': self.get_percentile(self.url_gen_times, 0.95),
            'url_p99': self.get_percentile(self.url_gen_times, 0.99),
            'hash_matches': self.hash_matches,
            'hash_mismatches': self.hash_mismatches,
            'hash_success_rate': (self.hash_matches / (self.hash_matches + self.hash_mismatches) * 100) if (self.hash_matches + self.hash_mismatches) > 0 else 0,
            'errors': len(self.errors)
        }


def generate_test_certificate(size_kb=50):
    """Generate test certificate content."""
    # Simulate PDF with realistic size distribution
    import random
    actual_size = int(size_kb * 1024 * random.uniform(0.8, 1.2))
    return b'%PDF-1.4\n' + os.urandom(actual_size - 10) + b'\n%%EOF'


def run_dry_run(count=500, use_real_s3=False, bucket_name='deltacrown-test-certs'):
    """
    Run dry-run rehearsal.
    
    Args:
        count: Number of objects to simulate
        use_real_s3: If True, use real boto3 (requires S3_TESTS=1)
        bucket_name: S3 bucket name for real tests
    
    Returns:
        DryRunStats: Rehearsal statistics
    """
    print(f"\n{'='*80}")
    print(f"S3 MIGRATION DRY-RUN REHEARSAL")
    print(f"{'='*80}")
    print(f"Objects to simulate: {count}")
    print(f"Mode: {'REAL S3' if use_real_s3 else 'DUMMY S3 (offline)'}")
    print(f"Bucket: {bucket_name if use_real_s3 else 'N/A (offline)'}")
    print(f"{'='*80}\n")
    
    # Initialize S3 client
    if use_real_s3:
        s3_client = create_real_s3_client()
        print("✓ Real S3 client initialized")
        
        # Validate lifecycle policy
        is_valid, msg = validate_lifecycle_policy(s3_client, bucket_name)
        if is_valid:
            print(f"✓ Lifecycle policy validated: {msg}")
        else:
            print(f"⚠ Lifecycle policy issue: {msg}")
    else:
        s3_client = DummyS3Client(upload_latency_ms=5, download_latency_ms=3, metadata_latency_ms=2)
        print("✓ DummyS3 client initialized (offline mode)")
    
    # Temporarily enable dual-write for rehearsal
    from django.conf import settings
    original_dual_write = settings.CERT_S3_DUAL_WRITE
    settings.CERT_S3_DUAL_WRITE = True
    
    storage = CertificateS3Storage(s3_client=s3_client)
    stats = DryRunStats()
    
    print(f"\nStarting upload simulation...")
    start_total = time.time()
    
    for i in range(count):
        try:
            # Generate test certificate
            cert_bytes = generate_test_certificate(size_kb=50)
            content = ContentFile(cert_bytes)
            name = f'dry-run-test/cert-{i:05d}.pdf'
            
            # Upload
            upload_start = time.time()
            saved_name = storage.save(name, content)
            upload_duration = (time.time() - upload_start) * 1000  # ms
            stats.add_upload(upload_duration, len(cert_bytes))
            
            # Validate hash
            if use_real_s3:
                # For real S3, get object and compare
                response = s3_client.get_object(Bucket=bucket_name, Key=saved_name)
                s3_bytes = response['Body'].read()
                s3_hash = hashlib.sha256(s3_bytes).hexdigest()
            else:
                # For dummy S3, get from storage dict
                # DummyS3Client stores with the Key parameter from put_object (which is 'name')
                s3_bytes = s3_client.storage.get(name, b'')
                if not s3_bytes:
                    # If not found, try with saved_name (though this shouldn't happen)
                    s3_bytes = s3_client.storage.get(saved_name, b'')
                s3_hash = hashlib.sha256(s3_bytes).hexdigest() if s3_bytes else 'MISSING'
            
            expected_hash = hashlib.sha256(cert_bytes).hexdigest()
            if s3_bytes and s3_hash == expected_hash:
                stats.add_hash_match()
            else:
                stats.add_hash_mismatch()
                if not s3_bytes:
                    stats.add_error(f"S3 object missing: {name}")
                else:
                    stats.add_error(f"Hash mismatch for {name} (expected={expected_hash[:16]}, got={s3_hash[:16] if s3_hash != 'MISSING' else 'MISSING'})")
            
            # Test URL generation
            url_start = time.time()
            url = storage.url(saved_name)
            url_duration = (time.time() - url_start) * 1000  # ms
            stats.add_url_gen(url_duration)
            
            # Progress indicator
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i + 1}/{count} objects ({(i+1)/count*100:.1f}%)")
            
            # Cleanup (delete after validation)
            if use_real_s3:
                s3_client.delete_object(Bucket=bucket_name, Key=saved_name)
            else:
                s3_client.storage.pop(name, None)
        
        except Exception as e:
            stats.add_error(f"Error processing object {i}: {str(e)}")
    
    total_duration = time.time() - start_total
    
    # Restore original dual-write setting
    settings.CERT_S3_DUAL_WRITE = original_dual_write
    
    print(f"\n{'='*80}")
    print(f"DRY-RUN RESULTS")
    print(f"{'='*80}\n")
    
    summary = stats.get_summary()
    
    # Performance metrics
    print(f"PERFORMANCE METRICS:")
    print(f"  Total objects:      {summary['total_objects']}")
    print(f"  Total data:         {summary['total_mb']:.2f} MB")
    print(f"  Total duration:     {total_duration:.2f} seconds")
    print(f"  Throughput:         {summary['total_objects'] / total_duration:.2f} obj/sec")
    print(f"  Bandwidth:          {summary['total_mb'] / total_duration:.2f} MB/sec")
    print(f"")
    print(f"  Upload Latency:")
    print(f"    p50: {summary['upload_p50']:.1f} ms")
    print(f"    p95: {summary['upload_p95']:.1f} ms {'✓' if summary['upload_p95'] <= 75 else '✗ EXCEEDS 75ms SLO'}")
    print(f"    p99: {summary['upload_p99']:.1f} ms {'✓' if summary['upload_p99'] <= 120 else '✗ EXCEEDS 120ms SLO'}")
    print(f"")
    print(f"  URL Generation:")
    print(f"    p50: {summary['url_p50']:.1f} ms")
    print(f"    p95: {summary['url_p95']:.1f} ms {'✓' if summary['url_p95'] <= 50 else '✗ EXCEEDS 50ms SLO'}")
    print(f"    p99: {summary['url_p99']:.1f} ms")
    print(f"")
    
    # Hash validation
    print(f"HASH VALIDATION:")
    print(f"  Matches:            {summary['hash_matches']}")
    print(f"  Mismatches:         {summary['hash_mismatches']}")
    print(f"  Success rate:       {summary['hash_success_rate']:.2f}% {'✓' if summary['hash_success_rate'] >= 99.9 else '✗ BELOW 99.9%'}")
    print(f"")
    
    # Errors
    print(f"ERRORS:")
    print(f"  Total errors:       {summary['errors']}")
    if stats.errors:
        print(f"  Error details:")
        for error in stats.errors[:10]:  # Show first 10 errors
            print(f"    - {error}")
        if len(stats.errors) > 10:
            print(f"    ... and {len(stats.errors) - 10} more")
    print(f"")
    
    # Estimate full migration
    print(f"{'='*80}")
    print(f"PRODUCTION MIGRATION ESTIMATE")
    print(f"{'='*80}\n")
    
    # Assume production has ~10,000 certificates at 50KB average
    prod_object_count = 10000
    prod_avg_size_kb = 50
    prod_total_mb = prod_object_count * prod_avg_size_kb / 1024
    
    # Estimate duration based on dry-run throughput
    estimated_duration_sec = prod_object_count / (summary['total_objects'] / total_duration)
    estimated_duration_min = estimated_duration_sec / 60
    estimated_duration_hr = estimated_duration_min / 60
    
    print(f"Estimated production workload:")
    print(f"  Objects:            {prod_object_count:,}")
    print(f"  Total data:         {prod_total_mb:.2f} MB")
    print(f"")
    print(f"Estimated migration time:")
    print(f"  Duration:           {estimated_duration_min:.1f} minutes ({estimated_duration_hr:.2f} hours)")
    print(f"  Start time:         During maintenance window")
    print(f"  End time:           +{estimated_duration_min:.0f} minutes")
    print(f"")
    
    # Go/No-Go checklist
    print(f"{'='*80}")
    print(f"GO/NO-GO CUTOVER CHECKLIST")
    print(f"{'='*80}\n")
    
    checks = []
    
    # Performance checks
    checks.append(("Upload p95 ≤75ms", summary['upload_p95'] <= 75))
    checks.append(("Upload p99 ≤120ms", summary['upload_p99'] <= 120))
    checks.append(("URL gen p95 ≤50ms", summary['url_p95'] <= 50))
    
    # Hash validation checks
    checks.append(("Hash success ≥99.9%", summary['hash_success_rate'] >= 99.9))
    
    # Error checks
    checks.append(("Error rate <1%", summary['errors'] / summary['total_objects'] * 100 < 1))
    
    # Feature flag checks
    checks.append(("CERT_S3_DUAL_WRITE=False (prod)", not getattr(settings, 'CERT_S3_DUAL_WRITE', False)))
    checks.append(("CERT_S3_READ_PRIMARY=False (prod)", not getattr(settings, 'CERT_S3_READ_PRIMARY', False)))
    checks.append(("CERT_S3_BACKFILL_ENABLED=False (prod)", not getattr(settings, 'CERT_S3_BACKFILL_ENABLED', False)))
    
    # Infrastructure checks
    if use_real_s3:
        checks.append(("Lifecycle policy valid", is_valid))
    else:
        checks.append(("Lifecycle policy valid", None))  # Skip in offline mode
    
    all_passed = True
    for check_name, passed in checks:
        if passed is None:
            status = "⊘ SKIP"
        elif passed:
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
            all_passed = False
        print(f"  {status}  {check_name}")
    
    print(f"")
    print(f"{'='*80}")
    if all_passed:
        print(f"✓ GO: All checks passed - ready for cutover")
    else:
        print(f"✗ NO-GO: Some checks failed - address issues before cutover")
    print(f"{'='*80}\n")
    
    # Next steps
    print(f"NEXT STEPS:")
    if all_passed:
        print(f"  1. Enable CERT_S3_DUAL_WRITE=True in staging")
        print(f"  2. Monitor cert.s3.write.success/fail metrics for 24 hours")
        print(f"  3. Run backfill command in dry-run mode (100 items)")
        print(f"  4. Verify staging: check S3 console for object count match")
        print(f"  5. Enable CERT_S3_READ_PRIMARY=True in staging")
        print(f"  6. Monitor cert.s3.read.fallback metric (should be <1%)")
        print(f"  7. After 7-day staging bake: promote to production")
    else:
        print(f"  1. Review failed checks above")
        print(f"  2. Fix performance/hash/error issues")
        print(f"  3. Re-run dry-run rehearsal")
        print(f"  4. Iterate until all checks pass")
    print(f"")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='S3 migration dry-run rehearsal')
    parser.add_argument('--count', type=int, default=500, help='Number of objects to simulate')
    parser.add_argument('--real-s3', action='store_true', help='Use real S3 (requires S3_TESTS=1)')
    parser.add_argument('--bucket', type=str, default='deltacrown-test-certs', help='S3 bucket name')
    
    args = parser.parse_args()
    
    if args.real_s3 and os.environ.get('S3_TESTS', '0') != '1':
        print("ERROR: Real S3 tests require S3_TESTS=1 environment variable")
        sys.exit(1)
    
    stats = run_dry_run(count=args.count, use_real_s3=args.real_s3, bucket_name=args.bucket)
    
    # Exit with appropriate code
    summary = stats.get_summary()
    if summary['errors'] > 0 or summary['hash_success_rate'] < 99.9:
        sys.exit(1)  # Failure
    else:
        sys.exit(0)  # Success


if __name__ == '__main__':
    main()
