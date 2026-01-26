"""
DEPRECATED: This file is deprecated in favor of modular constants/ package.

DO NOT ADD NEW CONSTANTS HERE.

Legacy constants maintained for backward compatibility.
Use `from apps.organizations.constants import TEAM_COUNTRIES` instead
(which now imports from constants/regions.py).

This file will be removed in v2.0.

See: apps/organizations/constants/README.md for migration guide.
"""

import warnings

warnings.warn(
    "Direct import from constants.py is deprecated. "
    "Use 'from apps.organizations.constants import TEAM_COUNTRIES' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Countries for team home region selection
# Represents team's home country/region identity (not game server location)
# DEPRECATED: Import from constants package instead
TEAM_COUNTRIES = [
    {'code': 'US', 'name': 'United States'},
    {'code': 'GB', 'name': 'United Kingdom'},
    {'code': 'IN', 'name': 'India'},
    {'code': 'SG', 'name': 'Singapore'},
    {'code': 'BR', 'name': 'Brazil'},
    {'code': 'BD', 'name': 'Bangladesh'},
    {'code': 'PK', 'name': 'Pakistan'},
    {'code': 'PH', 'name': 'Philippines'},
    {'code': 'ID', 'name': 'Indonesia'},
    {'code': 'MY', 'name': 'Malaysia'},
    {'code': 'TH', 'name': 'Thailand'},
    {'code': 'VN', 'name': 'Vietnam'},
    {'code': 'AU', 'name': 'Australia'},
    {'code': 'NZ', 'name': 'New Zealand'},
    {'code': 'CA', 'name': 'Canada'},
    {'code': 'MX', 'name': 'Mexico'},
    {'code': 'AR', 'name': 'Argentina'},
    {'code': 'CL', 'name': 'Chile'},
    {'code': 'FR', 'name': 'France'},
    {'code': 'DE', 'name': 'Germany'},
    {'code': 'ES', 'name': 'Spain'},
    {'code': 'IT', 'name': 'Italy'},
    {'code': 'SE', 'name': 'Sweden'},
    {'code': 'PL', 'name': 'Poland'},
    {'code': 'TR', 'name': 'Turkey'},
    {'code': 'RU', 'name': 'Russia'},
    {'code': 'JP', 'name': 'Japan'},
    {'code': 'KR', 'name': 'South Korea'},
    {'code': 'CN', 'name': 'China'},
    {'code': 'TW', 'name': 'Taiwan'},
    {'code': 'HK', 'name': 'Hong Kong'},
    {'code': 'SA', 'name': 'Saudi Arabia'},
    {'code': 'AE', 'name': 'United Arab Emirates'},
    {'code': 'ZA', 'name': 'South Africa'},
    {'code': 'EG', 'name': 'Egypt'},
]
