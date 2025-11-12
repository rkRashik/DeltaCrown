#!/usr/bin/env python3
"""
S3 Backfill Validator Script

Nightly validation of S3 backfill integrity:
- Sample 1% of objects from local storage
- Re-hash and compare with S3 versions
- Emit JSON report with pass/fail counts
- Alert on mismatches >0.5%

Usage:
    python scripts/s3_backfill_validator.py --sample-rate 0.01 --output artifacts/backfill_report.json

Schedule (cron):
    0 3 * * * cd /app && python scripts/s3_backfill_validator.py >> logs/backfill_validation.log 2>&1
"""

import os
import sys
import json
import hashlib
import random
import argparse
from datetime import datetime
from pathlib import Path

# Django setup
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
import django
django.setup()

from django.conf import settings
from apps.tournaments.storage import CertificateS3Storage


class BackfillValidator:
    """Validates S3 backfill integrity by sampling and re-hashing."""
    
    def __init__(self, sample_rate=0.01, output_path=None):
        self.sample_rate = sample_rate
        self.output_path = output_path or "artifacts/backfill_report.json"
        self.storage = CertificateS3Storage()
        
        self.total_sampled = 0
        self.matches = 0
        self.mismatches = 0
        self.errors = 0
        self.mismatch_details = []
    
    def compute_hash(self, file_obj):
        """Compute SHA256 hash of file content."""
        hasher = hashlib.sha256()
        for chunk in iter(lambda: file_obj.read(8192), b''):
            hasher.update(chunk)
        return hasher.hexdigest()
    
    def list_local_objects(self):
        """List all objects in local storage (media/certificates/)."""
        local_root = Path(settings.MEDIA_ROOT) / "certificates"
        if not local_root.exists():
            return []
        
        return [
            str(p.relative_to(settings.MEDIA_ROOT))
            for p in local_root.rglob('*')
            if p.is_file()
        ]
    
    def sample_objects(self, object_list):
        """Sample N% of objects randomly."""
        sample_size = max(1, int(len(object_list) * self.sample_rate))
        return random.sample(object_list, sample_size)
    
    def validate_object(self, object_key):
        """
        Validate a single object by comparing local vs S3 hashes.
        
        Returns:
            (status: str, local_hash: str, s3_hash: str)
        """
        try:
            # Read local file
            with self.storage.local_storage.open(object_key, 'rb') as local_file:
                local_hash = self.compute_hash(local_file)
            
            # Read S3 file
            if not self.storage.s3_storage.exists(object_key):
                return ('missing_s3', local_hash, None)
            
            with self.storage.s3_storage.open(object_key, 'rb') as s3_file:
                s3_hash = self.compute_hash(s3_file)
            
            # Compare hashes
            if local_hash == s3_hash:
                return ('match', local_hash, s3_hash)
            else:
                return ('mismatch', local_hash, s3_hash)
        
        except Exception as e:
            return ('error', None, str(e))
    
    def run_validation(self):
        """Run full validation sweep."""
        print(f"[{datetime.now().isoformat()}] Starting S3 backfill validation")
        print(f"Sample rate: {self.sample_rate * 100}%")
        
        # List all local objects
        all_objects = self.list_local_objects()
        print(f"Total objects in local storage: {len(all_objects)}")
        
        if not all_objects:
            print("No objects found in local storage. Exiting.")
            return self.generate_report()
        
        # Sample objects
        sampled_objects = self.sample_objects(all_objects)
        print(f"Sampled {len(sampled_objects)} objects for validation")
        
        # Validate each sampled object
        for i, object_key in enumerate(sampled_objects, 1):
            status, local_hash, s3_hash = self.validate_object(object_key)
            self.total_sampled += 1
            
            if status == 'match':
                self.matches += 1
            elif status == 'mismatch':
                self.mismatches += 1
                self.mismatch_details.append({
                    'object_key': object_key,
                    'local_hash': local_hash,
                    's3_hash': s3_hash
                })
                print(f"  [MISMATCH] {object_key}: local={local_hash[:8]} s3={s3_hash[:8]}")
            elif status == 'missing_s3':
                self.errors += 1
                self.mismatch_details.append({
                    'object_key': object_key,
                    'error': 'Object missing in S3'
                })
                print(f"  [MISSING S3] {object_key}")
            elif status == 'error':
                self.errors += 1
                print(f"  [ERROR] {object_key}: {s3_hash}")
            
            # Progress
            if i % 100 == 0:
                print(f"  Progress: {i}/{len(sampled_objects)} validated")
        
        print(f"\nValidation complete:")
        print(f"  Matches: {self.matches}")
        print(f"  Mismatches: {self.mismatches}")
        print(f"  Errors: {self.errors}")
        
        # Generate report
        return self.generate_report()
    
    def generate_report(self):
        """Generate JSON report."""
        mismatch_rate = (self.mismatches / self.total_sampled * 100) if self.total_sampled > 0 else 0.0
        error_rate = (self.errors / self.total_sampled * 100) if self.total_sampled > 0 else 0.0
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'sample_rate_percent': self.sample_rate * 100,
            'total_sampled': self.total_sampled,
            'matches': self.matches,
            'mismatches': self.mismatches,
            'errors': self.errors,
            'mismatch_rate_percent': round(mismatch_rate, 2),
            'error_rate_percent': round(error_rate, 2),
            'status': 'PASS' if mismatch_rate <= 0.5 else 'FAIL',
            'mismatch_details': self.mismatch_details[:10]  # Limit to 10 for report size
        }
        
        # Write to file
        output_dir = Path(self.output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nReport written to: {self.output_path}")
        print(f"Status: {report['status']}")
        
        return report


def main():
    parser = argparse.ArgumentParser(description='Validate S3 backfill integrity')
    parser.add_argument('--sample-rate', type=float, default=0.01,
                        help='Sample rate (0.01 = 1%%)')
    parser.add_argument('--output', type=str, default='artifacts/backfill_report.json',
                        help='Output JSON report path')
    
    args = parser.parse_args()
    
    validator = BackfillValidator(sample_rate=args.sample_rate, output_path=args.output)
    report = validator.run_validation()
    
    # Exit with error code if validation fails
    if report['status'] == 'FAIL':
        print("\n❌ Validation FAILED: Mismatch rate exceeds 0.5%")
        sys.exit(1)
    else:
        print("\n✅ Validation PASSED")
        sys.exit(0)


if __name__ == '__main__':
    main()
