"""
Django migrations for apps.organizations.

This directory contains database migrations for the Team & Organization vNext system.

CRITICAL DATABASE NAMING CONVENTION:
- All tables MUST use 'organizations_*' prefix
- NO references to legacy 'teams_*' tables
- Complete separation from apps/teams legacy system

Migration History:
- 0001_initial.py: Initial models (Organization, Team, Membership, Ranking, Migration, Activity)
"""
