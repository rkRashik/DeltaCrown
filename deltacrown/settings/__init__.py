"""
DeltaCrown Tournament Engine - Settings Package
===============================================
Loads appropriate settings module based on DJANGO_SETTINGS_MODULE environment variable.

Environment Settings:
- deltacrown.settings.development  (default for local development)
- deltacrown.settings.staging      (pre-production testing)
- deltacrown.settings.production   (production deployment)
- deltacrown.settings.base         (shared settings - not meant to be used directly)

Usage:
    Set DJANGO_SETTINGS_MODULE in your environment:
    
    Development:
        export DJANGO_SETTINGS_MODULE=deltacrown.settings.development
    
    Staging:
        export DJANGO_SETTINGS_MODULE=deltacrown.settings.staging
    
    Production:
        export DJANGO_SETTINGS_MODULE=deltacrown.settings.production
"""
