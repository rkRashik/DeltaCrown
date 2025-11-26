# apps/user_profile/services/__init__.py
from .xp_service import XPService, award_xp, award_badge, check_level_up

__all__ = ['XPService', 'award_xp', 'award_badge', 'check_level_up']
