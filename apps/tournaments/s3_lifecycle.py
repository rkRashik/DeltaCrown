"""
S3 Lifecycle Policy Configuration - Module 6.5

Defines lifecycle transitions for certificate storage:
- Standard storage: 0-30 days
- Infrequent Access: 30-365 days
- Glacier: 365+ days

Policy Structure:
- Rule ID: CertificateArchival
- Prefix: certificates/
- Transitions: STANDARD → STANDARD_IA @ 30d → GLACIER @ 365d
- Expiration: None (retain indefinitely)
"""


def get_lifecycle_policy():
    """
    Get S3 lifecycle policy for certificate storage.
    
    Returns:
        dict: Lifecycle policy configuration compatible with boto3
    
    Example:
        >>> from apps.tournaments.s3_lifecycle import get_lifecycle_policy
        >>> policy = get_lifecycle_policy()
        >>> s3_client.put_bucket_lifecycle_configuration(
        ...     Bucket='my-bucket',
        ...     LifecycleConfiguration=policy
        ... )
    """
    return {
        "Rules": [
            {
                "Id": "CertificateArchival",
                "Status": "Enabled",
                "Prefix": "certificates/",
                "Transitions": [
                    {
                        "Days": 30,
                        "StorageClass": "STANDARD_IA"
                    },
                    {
                        "Days": 365,
                        "StorageClass": "GLACIER"
                    }
                ],
                "NoncurrentVersionTransitions": [
                    {
                        "NoncurrentDays": 30,
                        "StorageClass": "STANDARD_IA"
                    },
                    {
                        "NoncurrentDays": 365,
                        "StorageClass": "GLACIER"
                    }
                ]
            }
        ]
    }


def get_lifecycle_policy_json():
    """
    Get lifecycle policy as JSON string for manual application.
    
    Returns:
        str: JSON representation of lifecycle policy
    
    Usage:
        Save to file and apply via AWS CLI:
        
        $ python manage.py shell -c "from apps.tournaments.s3_lifecycle import get_lifecycle_policy_json; print(get_lifecycle_policy_json())" > lifecycle.json
        $ aws s3api put-bucket-lifecycle-configuration --bucket deltacrown-certs --lifecycle-configuration file://lifecycle.json
    """
    import json
    return json.dumps(get_lifecycle_policy(), indent=2)


def validate_lifecycle_policy(s3_client, bucket_name):
    """
    Validate that lifecycle policy is applied to bucket.
    
    Args:
        s3_client: boto3 S3 client
        bucket_name: S3 bucket name
    
    Returns:
        tuple: (is_valid, message)
    
    Example:
        >>> from apps.tournaments.s3_protocol import create_real_s3_client
        >>> s3_client = create_real_s3_client()
        >>> is_valid, msg = validate_lifecycle_policy(s3_client, 'deltacrown-certs')
        >>> print(f"Valid: {is_valid}, {msg}")
    """
    try:
        response = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
        rules = response.get('Rules', [])
        
        if not rules:
            return False, "No lifecycle rules found"
        
        # Check for certificate archival rule
        cert_rule = None
        for rule in rules:
            if rule.get('Id') == 'CertificateArchival' or 'certificate' in rule.get('Prefix', '').lower():
                cert_rule = rule
                break
        
        if not cert_rule:
            return False, "CertificateArchival rule not found"
        
        # Validate transitions
        transitions = cert_rule.get('Transitions', [])
        if len(transitions) < 2:
            return False, f"Expected 2 transitions, found {len(transitions)}"
        
        # Check STANDARD_IA transition
        ia_found = any(t['StorageClass'] == 'STANDARD_IA' and t['Days'] == 30 for t in transitions)
        if not ia_found:
            return False, "STANDARD_IA transition @ 30 days not found"
        
        # Check GLACIER transition
        glacier_found = any(t['StorageClass'] == 'GLACIER' and t['Days'] == 365 for t in transitions)
        if not glacier_found:
            return False, "GLACIER transition @ 365 days not found"
        
        return True, "Lifecycle policy valid"
    
    except Exception as e:
        return False, f"Error validating policy: {str(e)}"


def apply_lifecycle_policy(s3_client, bucket_name):
    """
    Apply lifecycle policy to S3 bucket.
    
    Args:
        s3_client: boto3 S3 client
        bucket_name: S3 bucket name
    
    Returns:
        bool: True if successful, False otherwise
    
    Example:
        >>> from apps.tournaments.s3_protocol import create_real_s3_client
        >>> s3_client = create_real_s3_client()
        >>> success = apply_lifecycle_policy(s3_client, 'deltacrown-certs')
        >>> print(f"Applied: {success}")
    """
    try:
        policy = get_lifecycle_policy()
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=policy
        )
        return True
    except Exception as e:
        print(f"Error applying lifecycle policy: {str(e)}")
        return False
