"""
Tournament services package.

Exports all service classes for tournament business logic.
"""

from .tournament_service import TournamentService
from .registration_service import RegistrationService
from .winner_service import WinnerDeterminationService
from .analytics_service import AnalyticsService, analytics_service

# Certificate service requires Cairo / ReportLab native libraries.
# Lazy-import so the app boots on platforms without them (e.g. Windows dev).
try:
    from .certificate_service import CertificateService, certificate_service
except ImportError:
    import logging
    logging.getLogger(__name__).warning(
        'CertificateService unavailable — Cairo / ReportLab not installed. '
        'Certificate generation will be disabled.'
    )
    CertificateService = None       # type: ignore[assignment,misc]
    certificate_service = None      # type: ignore[assignment]

__all__ = [
    'TournamentService',
    'RegistrationService', 
    'WinnerDeterminationService',
    'CertificateService',
    'certificate_service',
    'AnalyticsService',
    'analytics_service',
]
