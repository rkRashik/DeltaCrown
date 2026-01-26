"""
Constants for organizations app.

Exports canonical region/country constants for team and org creation.

IMPORT GUIDELINES:
- Prefer importing from submodules for clarity: `from apps.organizations.constants.regions import COUNTRIES`
- Root-level imports supported for backward compatibility: `from apps.organizations.constants import COUNTRIES`
- TEAM_COUNTRIES is legacy alias for COUNTRIES (will be deprecated in v2)
"""

from .regions import COUNTRIES, DEFAULT_COUNTRY, get_country_name

# Legacy alias for backward compatibility (DEPRECATED - use COUNTRIES)
TEAM_COUNTRIES = [{'code': code, 'name': name} for code, name in COUNTRIES]

__all__ = [
    'COUNTRIES',
    'TEAM_COUNTRIES',  # Legacy alias
    'DEFAULT_COUNTRY',
    'get_country_name',
]
