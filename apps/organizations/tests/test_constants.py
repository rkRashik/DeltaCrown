"""
Tests for organizations constants.

Ensures constants are correctly defined, importable, and not duplicated.
"""

import pytest


class TestConstantsImports:
    """Test that all constants are properly importable."""
    
    def test_import_from_package_root(self):
        """All __all__ exports should be importable from package root."""
        from apps.organizations.constants import (
            COUNTRIES,
            TEAM_COUNTRIES,
            DEFAULT_COUNTRY,
            get_country_name,
        )
        
        # Verify types
        assert isinstance(COUNTRIES, list)
        assert isinstance(TEAM_COUNTRIES, list)
        assert isinstance(DEFAULT_COUNTRY, str)
        assert callable(get_country_name)
    
    def test_import_from_submodule(self):
        """Constants should be importable from their submodules."""
        from apps.organizations.constants.regions import (
            COUNTRIES,
            DEFAULT_COUNTRY,
            get_country_name,
        )
        
        assert isinstance(COUNTRIES, list)
        assert isinstance(DEFAULT_COUNTRY, str)
        assert callable(get_country_name)
    
    def test_no_missing_exports(self):
        """__all__ should not reference missing names."""
        import apps.organizations.constants as constants_module
        
        for name in constants_module.__all__:
            assert hasattr(constants_module, name), (
                f"'{name}' is in __all__ but not defined in module"
            )


class TestCountriesConstants:
    """Test country/region constants."""
    
    def test_countries_format(self):
        """COUNTRIES should be list of (code, name) tuples."""
        from apps.organizations.constants.regions import COUNTRIES
        
        assert len(COUNTRIES) > 0
        
        for item in COUNTRIES:
            assert isinstance(item, tuple)
            assert len(item) == 2
            code, name = item
            assert isinstance(code, str)
            assert isinstance(name, str)
            assert len(code) == 2  # ISO 3166-1 alpha-2
            assert code.isupper()
    
    def test_team_countries_format(self):
        """TEAM_COUNTRIES should be list of dicts (legacy format)."""
        from apps.organizations.constants import TEAM_COUNTRIES
        
        assert len(TEAM_COUNTRIES) > 0
        
        for item in TEAM_COUNTRIES:
            assert isinstance(item, dict)
            assert 'code' in item
            assert 'name' in item
            assert isinstance(item['code'], str)
            assert isinstance(item['name'], str)
            assert len(item['code']) == 2
            assert item['code'].isupper()
    
    def test_default_country_valid(self):
        """DEFAULT_COUNTRY should exist in COUNTRIES list."""
        from apps.organizations.constants.regions import COUNTRIES, DEFAULT_COUNTRY
        
        country_codes = [code for code, name in COUNTRIES]
        assert DEFAULT_COUNTRY in country_codes
    
    def test_no_duplicate_country_codes(self):
        """COUNTRIES should not have duplicate country codes."""
        from apps.organizations.constants.regions import COUNTRIES
        
        codes = [code for code, name in COUNTRIES]
        assert len(codes) == len(set(codes)), "Duplicate country codes found"
    
    def test_get_country_name_function(self):
        """get_country_name() should return correct names."""
        from apps.organizations.constants.regions import get_country_name
        
        # Test known country
        assert get_country_name('BD') == 'Bangladesh'
        assert get_country_name('US') == 'United States'
        
        # Test unknown country
        assert get_country_name('XX') == 'Unknown'
        assert get_country_name('') == 'Unknown'


class TestConstantsConsistency:
    """Test that constants are consistent across modules."""
    
    def test_countries_same_data(self):
        """COUNTRIES and TEAM_COUNTRIES should represent same data."""
        from apps.organizations.constants.regions import COUNTRIES
        from apps.organizations.constants import TEAM_COUNTRIES
        
        # Same length
        assert len(COUNTRIES) == len(TEAM_COUNTRIES)
        
        # Same country codes
        countries_codes = set(code for code, name in COUNTRIES)
        team_countries_codes = set(item['code'] for item in TEAM_COUNTRIES)
        assert countries_codes == team_countries_codes
    
    def test_no_duplicate_definitions(self):
        """Constants should not be redefined in multiple places."""
        import apps.organizations.constants.regions as regions
        import apps.organizations.constants as constants_pkg
        
        # TEAM_COUNTRIES should be generated from COUNTRIES, not independently defined
        # This is enforced by code structure, but we verify the relationship
        from apps.organizations.constants import TEAM_COUNTRIES
        from apps.organizations.constants.regions import COUNTRIES
        
        # If someone adds duplicate definitions, lengths would diverge
        assert len(TEAM_COUNTRIES) == len(COUNTRIES)


class TestConstantsContract:
    """Test that constants follow documented contracts."""
    
    def test_all_exports_documented(self):
        """All __all__ exports should be documented in README."""
        import apps.organizations.constants as constants_module
        
        # This is a reminder test - if it fails, update README.md
        documented_exports = {
            'COUNTRIES',
            'TEAM_COUNTRIES',
            'DEFAULT_COUNTRY',
            'get_country_name',
        }
        
        actual_exports = set(constants_module.__all__)
        
        missing_docs = actual_exports - documented_exports
        if missing_docs:
            pytest.fail(
                f"New exports not documented in README: {missing_docs}. "
                "Please update apps/organizations/constants/README.md"
            )
