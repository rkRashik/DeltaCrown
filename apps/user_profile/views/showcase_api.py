"""
Profile Showcase API Endpoints
Phase 14C: Facebook-style About section management

Endpoints:
- GET/POST /api/profile/showcase/ - Get/update showcase config
- POST /api/profile/showcase/toggle/ - Toggle section visibility
- POST /api/profile/showcase/featured-team/ - Set featured team
- POST /api/profile/showcase/featured-passport/ - Set featured passport
- POST /api/profile/showcase/highlights/add/ - Add highlight
- POST /api/profile/showcase/highlights/remove/ - Remove highlight
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction

from apps.user_profile.models import ProfileShowcase, UserProfile, GameProfile
from apps.teams.models import TeamMembership

import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@login_required
def get_showcase(request):
    """
    GET /api/profile/showcase/
    Returns current showcase configuration for authenticated user
    
    Response:
    {
        "success": true,
        "showcase": {
            "enabled_sections": ["identity", "gaming", "social"],
            "section_order": [],
            "featured_team": {"id": 1, "name": "...", "role": "..."},
            "featured_passport": {"id": 1, "game": "...", ...},
            "highlights": [...]
        },
        "available_sections": {...}
    }
    """
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Get or create showcase
        showcase, created = ProfileShowcase.objects.get_or_create(
            user_profile=user_profile,
            defaults={
                'enabled_sections': ProfileShowcase.get_default_sections(),
                'section_order': [],
                'highlights': []
            }
        )
        
        # Build response data
        showcase_data = {
            'enabled_sections': showcase.get_enabled_sections(),
            'section_order': showcase.section_order or [],
            'highlights': showcase.highlights or []
        }
        
        # Add featured team data if exists
        if showcase.featured_team_id:
            try:
                team_membership = TeamMembership.objects.select_related('team').get(
                    profile=user_profile,
                    team_id=showcase.featured_team_id,
                    status=TeamMembership.Status.ACTIVE
                )
                showcase_data['featured_team'] = {
                    'id': team_membership.team.id,
                    'name': team_membership.team.name,
                    'tag': team_membership.team.tag,
                    'game': team_membership.team.game,
                    'role': showcase.featured_team_role or team_membership.role,
                    'logo_url': team_membership.team.logo.url if team_membership.team.logo else None
                }
            except TeamMembership.DoesNotExist:
                # Featured team no longer valid
                showcase_data['featured_team'] = None
        else:
            showcase_data['featured_team'] = None
        
        # Add featured passport data if exists
        if showcase.featured_passport_id:
            try:
                passport = GameProfile.objects.select_related('game').get(
                    id=showcase.featured_passport_id,
                    user=request.user
                )
                showcase_data['featured_passport'] = {
                    'id': passport.id,
                    'game': passport.game.name,
                    'game_slug': passport.game.slug,
                    'game_id': passport.game_id_display,
                    'is_lft': passport.is_lft,
                    'rank': passport.rank
                }
            except GameProfile.DoesNotExist:
                # Featured passport no longer valid
                showcase_data['featured_passport'] = None
        else:
            showcase_data['featured_passport'] = None
        
        return JsonResponse({
            'success': True,
            'showcase': showcase_data,
            'available_sections': ProfileShowcase.get_all_available_sections()
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'User profile not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Failed to get showcase: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Failed to load showcase configuration'
        }, status=500)


@require_http_methods(["POST"])
@login_required
@ensure_csrf_cookie
def update_showcase(request):
    """
    POST /api/profile/showcase/
    Update showcase configuration (enabled sections, order)
    
    Body:
    {
        "enabled_sections": ["identity", "gaming", "social"],
        "section_order": ["identity", "gaming", "social"]  # optional
    }
    """
    try:
        import json
        data = json.loads(request.body)
        
        user_profile = UserProfile.objects.get(user=request.user)
        showcase, created = ProfileShowcase.objects.get_or_create(
            user_profile=user_profile
        )
        
        # Validate sections
        enabled_sections = data.get('enabled_sections', [])
        available = ProfileShowcase.get_all_available_sections().keys()
        invalid_sections = [s for s in enabled_sections if s not in available]
        
        if invalid_sections:
            return JsonResponse({
                'success': False,
                'message': f"Invalid sections: {', '.join(invalid_sections)}"
            }, status=400)
        
        # Update showcase
        showcase.enabled_sections = enabled_sections
        
        if 'section_order' in data:
            showcase.section_order = data['section_order']
        
        showcase.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Showcase updated successfully',
            'showcase': {
                'enabled_sections': showcase.enabled_sections,
                'section_order': showcase.section_order
            }
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'User profile not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Failed to update showcase: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Failed to update showcase'
        }, status=500)


@require_http_methods(["POST"])
@login_required
@ensure_csrf_cookie
def toggle_showcase_section(request):
    """
    POST /api/profile/showcase/toggle/
    Toggle a section on/off
    
    Body:
    {
        "section": "demographics"
    }
    """
    try:
        import json
        data = json.loads(request.body)
        section_slug = data.get('section')
        
        if not section_slug:
            return JsonResponse({
                'success': False,
                'message': 'Section parameter required'
            }, status=400)
        
        # Validate section exists
        if section_slug not in ProfileShowcase.get_all_available_sections():
            return JsonResponse({
                'success': False,
                'message': f"Invalid section: {section_slug}"
            }, status=400)
        
        user_profile = UserProfile.objects.get(user=request.user)
        showcase, created = ProfileShowcase.objects.get_or_create(
            user_profile=user_profile
        )
        
        showcase.toggle_section(section_slug)
        
        return JsonResponse({
            'success': True,
            'message': f"Section '{section_slug}' toggled",
            'enabled': showcase.is_section_enabled(section_slug),
            'enabled_sections': showcase.get_enabled_sections()
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'User profile not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Failed to toggle section: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Failed to toggle section'
        }, status=500)


@require_http_methods(["POST"])
@login_required
@ensure_csrf_cookie
def set_featured_team(request):
    """
    POST /api/profile/showcase/featured-team/
    Set featured team
    
    Body:
    {
        "team_id": 123,
        "role": "Team Captain"  # optional custom role label
    }
    """
    try:
        import json
        data = json.loads(request.body)
        team_id = data.get('team_id')
        role = data.get('role', '')
        
        if not team_id:
            return JsonResponse({
                'success': False,
                'message': 'team_id required'
            }, status=400)
        
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Verify user is member of this team (IDOR protection)
        team_membership = TeamMembership.objects.filter(
            profile=user_profile,
            team_id=team_id,
            status=TeamMembership.Status.ACTIVE
        ).select_related('team').first()
        
        if not team_membership:
            return JsonResponse({
                'success': False,
                'message': 'You are not a member of this team'
            }, status=403)
        
        showcase, created = ProfileShowcase.objects.get_or_create(
            user_profile=user_profile
        )
        
        showcase.set_featured_team(team_id, role)
        
        return JsonResponse({
            'success': True,
            'message': 'Featured team updated',
            'featured_team': {
                'id': team_membership.team.id,
                'name': team_membership.team.name,
                'tag': team_membership.team.tag,
                'role': role or team_membership.role
            }
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'User profile not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Failed to set featured team: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Failed to set featured team'
        }, status=500)


@require_http_methods(["POST"])
@login_required
@ensure_csrf_cookie
def set_featured_passport(request):
    """
    POST /api/profile/showcase/featured-passport/
    Set featured game passport
    
    Body:
    {
        "passport_id": 456
    }
    """
    try:
        import json
        data = json.loads(request.body)
        passport_id = data.get('passport_id')
        
        if not passport_id:
            return JsonResponse({
                'success': False,
                'message': 'passport_id required'
            }, status=400)
        
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Verify passport belongs to user (IDOR protection)
        passport = GameProfile.objects.filter(
            id=passport_id,
            user=request.user
        ).select_related('game').first()
        
        if not passport:
            return JsonResponse({
                'success': False,
                'message': 'Passport not found or does not belong to you'
            }, status=403)
        
        showcase, created = ProfileShowcase.objects.get_or_create(
            user_profile=user_profile
        )
        
        showcase.set_featured_passport(passport_id)
        
        return JsonResponse({
            'success': True,
            'message': 'Featured passport updated',
            'featured_passport': {
                'id': passport.id,
                'game': passport.game.name,
                'game_id': passport.game_id_display
            }
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'User profile not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Failed to set featured passport: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Failed to set featured passport'
        }, status=500)


@require_http_methods(["POST"])
@login_required
@ensure_csrf_cookie
def add_showcase_highlight(request):
    """
    POST /api/profile/showcase/highlights/add/
    Add a highlight to showcase
    
    Body:
    {
        "type": "tournament",  # tournament, achievement, milestone, custom
        "item_id": 789,
        "label": "Champions 2024 Winner",
        "icon": "🏆",
        "metadata": {"placement": 1, "prize": 50000}  # optional
    }
    """
    try:
        import json
        data = json.loads(request.body)
        
        highlight_type = data.get('type')
        item_id = data.get('item_id')
        label = data.get('label')
        icon = data.get('icon', '✨')
        metadata = data.get('metadata', {})
        
        if not all([highlight_type, item_id, label]):
            return JsonResponse({
                'success': False,
                'message': 'type, item_id, and label are required'
            }, status=400)
        
        valid_types = ['tournament', 'achievement', 'milestone', 'custom']
        if highlight_type not in valid_types:
            return JsonResponse({
                'success': False,
                'message': f"Invalid type. Must be one of: {', '.join(valid_types)}"
            }, status=400)
        
        user_profile = UserProfile.objects.get(user=request.user)
        showcase, created = ProfileShowcase.objects.get_or_create(
            user_profile=user_profile
        )
        
        # TODO: Add validation that item_id belongs to user (depends on type)
        
        showcase.add_highlight(highlight_type, item_id, label, icon, metadata)
        
        return JsonResponse({
            'success': True,
            'message': 'Highlight added',
            'highlights': showcase.highlights
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'User profile not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Failed to add highlight: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Failed to add highlight'
        }, status=500)


@require_http_methods(["POST"])
@login_required
@ensure_csrf_cookie
def remove_showcase_highlight(request):
    """
    POST /api/profile/showcase/highlights/remove/
    Remove a highlight from showcase
    
    Body:
    {
        "item_id": 789
    }
    """
    try:
        import json
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        if not item_id:
            return JsonResponse({
                'success': False,
                'message': 'item_id required'
            }, status=400)
        
        user_profile = UserProfile.objects.get(user=request.user)
        showcase = ProfileShowcase.objects.filter(user_profile=user_profile).first()
        
        if not showcase:
            return JsonResponse({
                'success': False,
                'message': 'Showcase not found'
            }, status=404)
        
        showcase.remove_highlight(item_id)
        
        return JsonResponse({
            'success': True,
            'message': 'Highlight removed',
            'highlights': showcase.highlights
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'User profile not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Failed to remove highlight: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Failed to remove highlight'
        }, status=500)
