"""
Organization views for vNext system.

Handles:
- Organization detail and management
- Organization member management
- Organization creation
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from apps.organizations.models import Organization

logger = logging.getLogger(__name__)


def organization_detail(request, org_slug):
    """
    Organization detail page with dynamic tabs and privacy controls.
    
    Displays organization information with tabs for:
    - Headquarters: Overview, manifesto, stats
    - Active Squads: Teams with IGL/Manager (privacy-aware)
    - Operations Log: Recent activity timeline
    - Media/Streams: Featured streamers and content
    - Legacy Wall: Historical achievements
    - Financials: Revenue/expenses (restricted to managers)
    - Settings: Org configuration (restricted to managers)
    
    Args:
        org_slug: Organization URL slug
    
    Returns:
        - 200: Renders org_detail.html with full context
        - 404: Organization not found
    """
    from django.http import Http404
    from django.core.exceptions import FieldError
    from django.db.utils import ProgrammingError
    from apps.organizations.services.org_detail_service import get_org_detail_context
    
    try:
        # Get organization detail context
        context = get_org_detail_context(
            org_slug=org_slug,
            viewer=request.user if request.user.is_authenticated else None
        )
        
        logger.info(
            f"Organization detail accessed: {org_slug}",
            extra={
                'event_type': 'org_detail_accessed',
                'user_id': request.user.id if request.user.is_authenticated else None,
                'org_slug': org_slug,
                'can_manage': context['can_manage_org'],
            }
        )
        
        return render(request, 'organizations/org/org_detail.html', context)
    
    except Http404:
        # Org truly doesn't exist - legitimate 404
        raise
    except (FieldError, ProgrammingError) as e:
        # Schema bugs - log and re-raise, do NOT hide as 404
        logger.error(
            f"Database schema error in organization detail: {org_slug}",
            extra={'error': str(e), 'org_slug': org_slug},
            exc_info=True
        )
        raise
    except Exception as e:
        # Unexpected errors - log and re-raise
        logger.error(
            f"Unexpected error loading organization detail: {org_slug}",
            extra={'error': str(e), 'org_slug': org_slug},
            exc_info=True
        )
        raise


@login_required
def org_create(request):
    """
    Organization creation wizard UI (P3-T7).
    
    Multi-step form for creating new organizations with:
    - Step 1: Identity (name, ticker, slug, manifesto)
    - Step 2: Operations (type, location, socials)
    - Step 3: Treasury (payout method, currency)
    - Step 4: Branding (logo, banner, colors)
    - Step 5: Ratification (terms acceptance)
    
    Returns:
        - 200: Renders org_create.html (Tailwind + custom JS wizard)
        - 302: Redirects to login if not authenticated
    
    Note:
        - Phase A: Demo UI only
        - Phase B: Will wire to /api/vnext/organizations/create/
    """
    logger.info(
        f"Organization create page accessed",
        extra={
            'event_type': 'org_create_accessed',
            'user_id': request.user.id,
            'username': request.user.username,
        }
    )
    
    return render(request, 'organizations/org/org_create.html', {
        'page_title': 'Create Organization',
    })


@login_required
def org_hub(request, org_slug):
    """
    Organization Hub page (P3-T8 - Production).
    
    Centralized dashboard for organization management showing:
    - Quick stats and overview (global rank, CP, earnings, team count)
    - Active teams roster grid with game icons and rosters
    - Recent activity feed
    - Management actions (if authorized)
    - Leadership panel
    
    Args:
        org_slug: Organization URL slug
    
    Returns:
        - 200: Renders org_hub.html with full context
        - 404: Organization not found
    
    Performance:
        - Optimized with select_related and prefetch_related
        - Target: ≤15 queries per request
    """
    from apps.organizations.services.org_hub_service import get_org_hub_context
    from apps.organizations.models import Organization
    from django.shortcuts import get_object_or_404, render
    
    try:
        context = get_org_hub_context(org_slug=org_slug, user=request.user)
        
        logger.info(
            f"Organization hub rendered",
            extra={
                'event_type': 'org_hub_rendered',
                'user_id': request.user.id if request.user.is_authenticated else None,
                'username': request.user.username if request.user.is_authenticated else 'anonymous',
                'org_slug': org_slug,
                'org_id': context['organization'].id,
                'can_manage': context['can_manage'],
                'team_count': context['stats']['team_count'],
            }
        )
        
        # Merge service context with page metadata
        context.update({
            'page_title': f"{context['organization'].name} Hub",
        })
        
        return render(request, 'organizations/org/org_hub.html', context)
        
    except Organization.DoesNotExist:
        logger.warning(
            f"Organization hub 404",
            extra={
                'event_type': 'org_hub_not_found',
                'user_id': request.user.id if request.user.is_authenticated else None,
                'org_slug': org_slug,
            }
        )
        raise


@login_required
def org_control_plane(request, org_slug):
    """
    Organization Control Plane - centralized management interface.
    
    Access Control:
    - Organization CEO (owner)
    - Organization MANAGER/ADMIN (vNext staff)
    - Site staff
    
    Returns:
    - 403 if user lacks permission
    - Control plane interface if authorized
    """
    # Load organization
    organization = get_object_or_404(Organization, slug=org_slug)
    
    # Check permission: CEO OR org MANAGER/ADMIN OR site staff
    can_manage_org = False
    
    if request.user.is_staff:
        can_manage_org = True
    elif organization.ceo_id == request.user.id:
        can_manage_org = True
    else:
        # Check if user is org MANAGER or ADMIN via staff_memberships
        if organization.staff_memberships.filter(
            user=request.user,
            role__in=['MANAGER', 'ADMIN']
        ).exists():
            can_manage_org = True
    
    if not can_manage_org:
        logger.warning(
            f"Unauthorized control plane access attempt",
            extra={
                'event_type': 'control_plane_unauthorized',
                'user_id': request.user.id,
                'org_slug': org_slug,
                'organization_id': organization.id,
            }
        )
        return HttpResponseForbidden(
            "You do not have permission to access the Control Plane for this organization."
        )
    
    # Log authorized access
    logger.info(
        f"Control plane accessed",
        extra={
            'event_type': 'control_plane_access',
            'user_id': request.user.id,
            'org_slug': org_slug,
            'organization_id': organization.id,
        }
    )
    
    context = {
        'organization': organization,
        'can_manage_org': True,
    }
    
    return render(request, 'organizations/org/org_control_plane.html', context)


