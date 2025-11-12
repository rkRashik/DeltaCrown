"""
S3 Protocol Quick-Win Coverage Tests

Targets uncovered lines in s3_protocol.py:
- DummyS3Client pagination (list_objects_v2 continuation)
- Error handling branches
- Lifecycle policy validator negative cases
"""

import pytest
from apps.tournaments.s3_protocol import DummyS3Client
from apps.tournaments.s3_lifecycle import validate_policy_structure


# ============================================================================
# PAGINATION TESTS
# ============================================================================

def test_list_objects_v2_pagination():
    """
    Test: DummyS3Client list_objects_v2 with pagination.
    
    Validates:
    - ContinuationToken handling
    - NextContinuationToken generation
    - IsTruncated flag
    - MaxKeys limit
    
    Coverage: s3_protocol.py pagination logic
    """
    client = DummyS3Client()
    bucket = 'test-bucket'
    
    # Upload 5 objects
    for i in range(5):
        client.put_object(Bucket=bucket, Key=f'obj-{i:03d}.txt', Body=b'data')
    
    # List with MaxKeys=2 (should paginate)
    page1 = client.list_objects_v2(Bucket=bucket, MaxKeys=2)
    
    assert page1['KeyCount'] == 2
    assert page1['IsTruncated'] is True
    assert 'NextContinuationToken' in page1
    assert len(page1['Contents']) == 2
    
    # Get next page
    page2 = client.list_objects_v2(
        Bucket=bucket,
        MaxKeys=2,
        ContinuationToken=page1['NextContinuationToken']
    )
    
    assert page2['KeyCount'] == 2
    assert page2['IsTruncated'] is True
    
    # Get final page
    page3 = client.list_objects_v2(
        Bucket=bucket,
        MaxKeys=2,
        ContinuationToken=page2['NextContinuationToken']
    )
    
    assert page3['KeyCount'] == 1
    assert page3['IsTruncated'] is False
    assert 'NextContinuationToken' not in page3


def test_list_objects_v2_prefix_filtering():
    """
    Test: DummyS3Client list_objects_v2 with Prefix filtering.
    
    Coverage: s3_protocol.py prefix filter logic
    """
    client = DummyS3Client()
    bucket = 'test-bucket'
    
    # Upload objects with different prefixes
    client.put_object(Bucket=bucket, Key='certs/2024/file1.pdf', Body=b'data1')
    client.put_object(Bucket=bucket, Key='certs/2025/file2.pdf', Body=b'data2')
    client.put_object(Bucket=bucket, Key='logs/2025/log.txt', Body=b'data3')
    
    # List with prefix
    result = client.list_objects_v2(Bucket=bucket, Prefix='certs/2025/')
    
    assert result['KeyCount'] == 1
    assert result['Contents'][0]['Key'] == 'certs/2025/file2.pdf'


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

def test_get_object_key_not_found():
    """
    Test: DummyS3Client get_object raises error for missing key.
    
    Coverage: s3_protocol.py error branch for get_object
    """
    from botocore.exceptions import ClientError
    
    client = DummyS3Client()
    bucket = 'test-bucket'
    
    # Try to get non-existent object
    with pytest.raises(ClientError) as exc_info:
        client.get_object(Bucket=bucket, Key='missing.pdf')
    
    assert exc_info.value.response['Error']['Code'] == 'NoSuchKey'


def test_head_object_key_not_found():
    """
    Test: DummyS3Client head_object raises error for missing key.
    
    Coverage: s3_protocol.py error branch for head_object
    """
    from botocore.exceptions import ClientError
    
    client = DummyS3Client()
    bucket = 'test-bucket'
    
    # Try to head non-existent object
    with pytest.raises(ClientError) as exc_info:
        client.head_object(Bucket=bucket, Key='missing.pdf')
    
    assert exc_info.value.response['Error']['Code'] == 'NoSuchKey'


def test_delete_object_idempotent():
    """
    Test: DummyS3Client delete_object is idempotent (no error if already deleted).
    
    Coverage: s3_protocol.py delete idempotency
    """
    client = DummyS3Client()
    bucket = 'test-bucket'
    key = 'test.pdf'
    
    # Upload object
    client.put_object(Bucket=bucket, Key=key, Body=b'data')
    
    # Delete once
    response1 = client.delete_object(Bucket=bucket, Key=key)
    assert 'DeleteMarker' in response1
    
    # Delete again (should not raise error)
    response2 = client.delete_object(Bucket=bucket, Key=key)
    assert 'DeleteMarker' in response2  # Still returns valid response


# ============================================================================
# LIFECYCLE POLICY VALIDATOR TESTS
# ============================================================================

def test_lifecycle_policy_valid():
    """
    Test: validate_policy_structure accepts valid policy.
    
    Coverage: s3_lifecycle.py success path
    """
    valid_policy = {
        'Rules': [
            {
                'ID': 'delete-old-certs',
                'Status': 'Enabled',
                'Prefix': 'certs/',
                'Expiration': {'Days': 2555}  # 7 years
            }
        ]
    }
    
    result = validate_policy_structure(valid_policy)
    assert result['valid'] is True
    assert result['errors'] == []


def test_lifecycle_policy_invalid_structure():
    """
    Test: validate_policy_structure rejects invalid structure.
    
    Validates:
    - Missing 'Rules' key
    - Empty rules list
    - Invalid rule structure
    
    Coverage: s3_lifecycle.py error paths
    """
    # Missing Rules
    result1 = validate_policy_structure({'Invalid': 'structure'})
    assert result1['valid'] is False
    assert 'Rules' in str(result1['errors'])
    
    # Empty Rules
    result2 = validate_policy_structure({'Rules': []})
    assert result2['valid'] is False
    assert 'at least one rule' in str(result2['errors']).lower()
    
    # Invalid rule (missing Status)
    result3 = validate_policy_structure({
        'Rules': [
            {'ID': 'test', 'Prefix': 'certs/'}  # Missing Status
        ]
    })
    assert result3['valid'] is False


def test_lifecycle_policy_invalid_expiration():
    """
    Test: validate_policy_structure rejects invalid expiration.
    
    Validates:
    - Days < 1
    - Days > 3650 (10 years max)
    
    Coverage: s3_lifecycle.py expiration validation
    """
    # Too short
    result1 = validate_policy_structure({
        'Rules': [{
            'ID': 'test',
            'Status': 'Enabled',
            'Prefix': 'certs/',
            'Expiration': {'Days': 0}  # Invalid
        }]
    })
    assert result1['valid'] is False
    
    # Too long
    result2 = validate_policy_structure({
        'Rules': [{
            'ID': 'test',
            'Status': 'Enabled',
            'Prefix': 'certs/',
            'Expiration': {'Days': 4000}  # Too long
        }]
    })
    assert result2['valid'] is False


def test_lifecycle_policy_warning_short_retention():
    """
    Test: validate_policy_structure warns on short retention (<365 days).
    
    Coverage: s3_lifecycle.py warning logic
    """
    result = validate_policy_structure({
        'Rules': [{
            'ID': 'test',
            'Status': 'Enabled',
            'Prefix': 'certs/',
            'Expiration': {'Days': 180}  # Valid but short
        }]
    })
    
    assert result['valid'] is True
    assert len(result['warnings']) > 0
    assert 'retention' in str(result['warnings']).lower()
