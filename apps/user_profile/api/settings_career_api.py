"""
Career & Matchmaking Settings API Endpoints (Phase 2A-1)
CSRF-protected JSON endpoints for career and matchmaking preferences.
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
import json
import logging

from apps.user_profile.models import CareerProfile, MatchmakingPreferences, UserProfile

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def career_settings_get(request):
    """GET /me/settings/career/ - Retrieve career settings for logged-in user"""
    try:
        profile = UserProfile.objects.get(user=request.user)
        
        # Get or create CareerProfile
        career, created = CareerProfile.objects.get_or_create(
            user_profile=profile,
            defaults={
                'career_status': 'NOT_LOOKING',
                'lft_enabled': False,
                'primary_roles': [],
                'secondary_roles': [],
                'preferred_region': '',
                'availability': 'PART_TIME',
                'salary_expectation_min': None,
                'contract_type': 'TEAM',
                'recruiter_visibility': 'PUBLIC',
                'allow_direct_contracts': True,
            }
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'career_status': career.career_status,
                'lft_enabled': career.lft_enabled,
                'primary_roles': career.primary_roles,
                'secondary_roles': career.secondary_roles,
                'preferred_region': career.preferred_region,
                'availability': career.availability,
                'salary_expectation_min': career.salary_expectation_min,
                'contract_type': career.contract_type,
                'recruiter_visibility': career.recruiter_visibility,
                'allow_direct_contracts': career.allow_direct_contracts,
            }
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error fetching career settings for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Server error'
        }, status=500)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def career_settings_save(request):
    """POST /me/settings/career/save/ - Save career settings"""
    try:
        data = json.loads(request.body)
        profile = UserProfile.objects.get(user=request.user)
        
        career, created = CareerProfile.objects.get_or_create(
            user_profile=profile
        )
        
        # Update fields
        if 'career_status' in data:
            career.career_status = data['career_status']
        if 'lft_enabled' in data:
            career.lft_enabled = data['lft_enabled']
        if 'primary_roles' in data:
            career.primary_roles = data['primary_roles']
        if 'secondary_roles' in data:
            career.secondary_roles = data['secondary_roles']
        if 'preferred_region' in data:
            career.preferred_region = data['preferred_region']
        if 'availability' in data:
            career.availability = data['availability']
        if 'salary_expectation_min' in data:
            career.salary_expectation_min = data['salary_expectation_min']
        if 'contract_type' in data:
            career.contract_type = data['contract_type']
        if 'recruiter_visibility' in data:
            career.recruiter_visibility = data['recruiter_visibility']
        if 'allow_direct_contracts' in data:
            career.allow_direct_contracts = data['allow_direct_contracts']
        
        # Validate and save
        career.full_clean()  # Raises ValidationError if invalid
        career.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Career settings saved successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON payload'
        }, status=400)
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Error saving career settings for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Server error'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def matchmaking_settings_get(request):
    """GET /me/settings/matchmaking/ - Retrieve matchmaking preferences"""
    try:
        profile = UserProfile.objects.get(user=request.user)
        
        # Get or create MatchmakingPreferences
        prefs, created = MatchmakingPreferences.objects.get_or_create(
            user_profile=profile,
            defaults={
                'enabled': True,
                'games_enabled': [],
                'preferred_modes': [],
                'min_bounty': None,
                'max_bounty': None,
                'auto_accept': False,
                'auto_reject_below_min': False,
                'region_lock': '',
                'skill_range_min': None,
                'skill_range_max': None,
                'allow_team_bounties': True,
            }
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'enabled': prefs.enabled,
                'games_enabled': prefs.games_enabled,
                'preferred_modes': prefs.preferred_modes,
                'min_bounty': prefs.min_bounty,
                'max_bounty': prefs.max_bounty,
                'auto_accept': prefs.auto_accept,
                'auto_reject_below_min': prefs.auto_reject_below_min,
                'region_lock': prefs.region_lock,
                'skill_range_min': prefs.skill_range_min,
                'skill_range_max': prefs.skill_range_max,
                'allow_team_bounties': prefs.allow_team_bounties,
            }
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error fetching matchmaking settings for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Server error'
        }, status=500)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def matchmaking_settings_save(request):
    """POST /me/settings/matchmaking/save/ - Save matchmaking preferences"""
    try:
        data = json.loads(request.body)
        profile = UserProfile.objects.get(user=request.user)
        
        prefs, created = MatchmakingPreferences.objects.get_or_create(
            user_profile=profile
        )
        
        # Update fields
        if 'enabled' in data:
            prefs.enabled = data['enabled']
        if 'games_enabled' in data:
            prefs.games_enabled = data['games_enabled']
        if 'preferred_modes' in data:
            prefs.preferred_modes = data['preferred_modes']
        if 'min_bounty' in data:
            prefs.min_bounty = data['min_bounty']
        if 'max_bounty' in data:
            prefs.max_bounty = data['max_bounty']
        if 'auto_accept' in data:
            prefs.auto_accept = data['auto_accept']
        if 'auto_reject_below_min' in data:
            prefs.auto_reject_below_min = data['auto_reject_below_min']
        if 'region_lock' in data:
            prefs.region_lock = data['region_lock']
        if 'skill_range_min' in data:
            prefs.skill_range_min = data['skill_range_min']
        if 'skill_range_max' in data:
            prefs.skill_range_max = data['skill_range_max']
        if 'allow_team_bounties' in data:
            prefs.allow_team_bounties = data['allow_team_bounties']
        
        # Validate and save
        prefs.full_clean()  # Raises ValidationError if invalid
        prefs.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Matchmaking settings saved successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON payload'
        }, status=400)
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Error saving matchmaking settings for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Server error'
        }, status=500)
