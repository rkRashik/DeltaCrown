"""
Regions and country constants for organization creation.

Used in org_create wizard and other location-based features.
"""

COUNTRIES = [
    ('BD', 'Bangladesh'),
    ('US', 'United States'),
    ('GB', 'United Kingdom'),
    ('SG', 'Singapore'),
    ('IN', 'India'),
    ('PK', 'Pakistan'),
    ('MY', 'Malaysia'),
    ('ID', 'Indonesia'),
    ('PH', 'Philippines'),
    ('TH', 'Thailand'),
    ('VN', 'Vietnam'),
    ('AE', 'United Arab Emirates'),
    ('SA', 'Saudi Arabia'),
    ('TR', 'Turkey'),
    ('EG', 'Egypt'),
    ('ZA', 'South Africa'),
    ('AU', 'Australia'),
    ('NZ', 'New Zealand'),
    ('CA', 'Canada'),
    ('MX', 'Mexico'),
    ('BR', 'Brazil'),
    ('AR', 'Argentina'),
    ('CL', 'Chile'),
    ('DE', 'Germany'),
    ('FR', 'France'),
    ('ES', 'Spain'),
    ('IT', 'Italy'),
    ('NL', 'Netherlands'),
    ('SE', 'Sweden'),
    ('NO', 'Norway'),
    ('DK', 'Denmark'),
    ('FI', 'Finland'),
    ('PL', 'Poland'),
    ('RU', 'Russia'),
    ('JP', 'Japan'),
    ('KR', 'South Korea'),
    ('CN', 'China'),
    ('TW', 'Taiwan'),
    ('HK', 'Hong Kong'),
]

# Default country for IP detection fallback
DEFAULT_COUNTRY = 'BD'

def get_country_name(country_code):
    """Get country name from code."""
    for code, name in COUNTRIES:
        if code == country_code:
            return name
    return 'Unknown'
