"""
Test Helpers for Certificate Storage Tests

Provides unified metric capture and common test utilities.
"""

from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def capture_cert_metrics():
    """
    Context manager for capturing certificate storage metrics.
    
    Patches the _emit_metric method and tracks metric emission counts.
    
    Usage:
        with capture_cert_metrics() as em:
            storage.save('test.pdf', ContentFile(b'data'))
            assert em.counts.get('cert.s3.write.success', 0) == 1
    
    Returns:
        Mock object with .counts dict tracking metric_name -> count
    """
    with patch('apps.tournaments.storage.CertificateS3Storage._emit_metric') as emit:
        # Initialize counts tracker
        emit.counts = {}
        
        def side_effect(name, value=1, tags=None):
            """Track metric emissions by name."""
            emit.counts[name] = emit.counts.get(name, 0) + value
        
        emit.side_effect = side_effect
        yield emit
