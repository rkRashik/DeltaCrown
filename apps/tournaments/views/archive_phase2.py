# apps/tournaments/views/archive_phase2.py
"""
Phase 2: Archive Management Views
Provides comprehensive archive browsing, cloning, and restoration functionality

Features:
- Browse archived tournaments with Phase 1 context
- View detailed archive information
- Clone archived tournaments
- Restore tournaments from archive
- Archive history and audit trail
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpRequest, Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django.urls import reverse
from typing import Optional, Dict, Any

from apps.tournaments.models import Tournament
from apps.tournaments.models_phase1 import (
    TournamentSchedule,
    TournamentCapacity,
    TournamentFinance,
    TournamentMedia,
    TournamentRules,
    TournamentArchive,
)

# Permission helpers
def is_staff_or_organizer(user) -> bool:
    """Check if user is staff or tournament organizer"""
    return user.is_staff or user.is_superuser or hasattr(user, 'organizer_profile')


def can_manage_archives(user) -> bool:
    """Check if user can manage archives (staff only for now)"""
    return user.is_staff or user.is_superuser


# ============================================================================
# ARCHIVE BROWSING VIEWS
# ============================================================================

@login_required
@user_passes_test(is_staff_or_organizer, login_url='/login/')
@require_http_methods(["GET"])
def archive_list_view(request: HttpRequest):
    """
    Browse archived tournaments with filtering and search
    
    URL: /tournaments/archives/
    
    Features:
    - List all archived tournaments
    - Filter by archive reason, date, game
    - Search by name
    - Pagination
    - Phase 1 model context
    """
    # Get archived tournaments with Phase 1 models
    archives = TournamentArchive.objects.filter(
        is_archived=True
    ).select_related(
        'tournament',
        'tournament__game',
        'tournament__organizer',
        'archived_by',
    ).prefetch_related(
        Prefetch(
            'tournament__tournamentschedule_set',
            queryset=TournamentSchedule.objects.all(),
            to_attr='schedule_list'
        ),
        Prefetch(
            'tournament__tournamentcapacity_set',
            queryset=TournamentCapacity.objects.all(),
            to_attr='capacity_list'
        ),
        Prefetch(
            'tournament__tournamentfinance_set',
            queryset=TournamentFinance.objects.all(),
            to_attr='finance_list'
        ),
    ).order_by('-archived_at')
    
    # Filtering
    archive_reason = request.GET.get('reason')
    if archive_reason:
        archives = archives.filter(archive_reason__icontains=archive_reason)
    
    game_id = request.GET.get('game')
    if game_id:
        archives = archives.filter(tournament__game_id=game_id)
    
    search_query = request.GET.get('q')
    if search_query:
        archives = archives.filter(
            Q(tournament__name__icontains=search_query) |
            Q(archive_reason__icontains=search_query)
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(archives, 20)  # 20 per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Build context with Phase 1 data
    archive_cards = []
    for archive in page_obj:
        tournament = archive.tournament
        
        # Get Phase 1 models
        schedule = tournament.schedule_list[0] if hasattr(tournament, 'schedule_list') and tournament.schedule_list else None
        capacity = tournament.capacity_list[0] if hasattr(tournament, 'capacity_list') and tournament.capacity_list else None
        finance = tournament.finance_list[0] if hasattr(tournament, 'finance_list') and tournament.finance_list else None
        
        archive_cards.append({
            'archive': archive,
            'tournament': tournament,
            'schedule': {
                'start_at': schedule.start_at if schedule else tournament.start_at,
                'end_at': schedule.end_at if schedule else None,
                'was_completed': schedule.is_completed if schedule else False,
            } if schedule or tournament.start_at else None,
            'capacity': {
                'max_teams': capacity.max_teams if capacity else getattr(tournament, 'slot_size', 0),
                'current_teams': capacity.current_teams if capacity else 0,
            } if capacity else None,
            'finance': {
                'entry_fee_display': finance.entry_fee_display if finance else f"৳{getattr(tournament, 'entry_fee_bdt', 0)}",
                'prize_pool_display': finance.prize_pool_display if finance else f"৳{getattr(tournament, 'prize_pool_bdt', 0)}",
            } if finance else None,
            'can_restore': archive.can_restore and can_manage_archives(request.user),
            'can_clone': True,  # Anyone with access can clone
        })
    
    # Statistics
    stats = {
        'total_archived': TournamentArchive.objects.filter(is_archived=True).count(),
        'archived_this_month': TournamentArchive.objects.filter(
            is_archived=True,
            archived_at__gte=timezone.now().replace(day=1)
        ).count(),
        'restorable': TournamentArchive.objects.filter(
            is_archived=True,
            can_restore=True
        ).count(),
    }
    
    # Available games for filtering
    from apps.tournaments.models import Game
    games = Game.objects.all()
    
    context = {
        'page_obj': page_obj,
        'archive_cards': archive_cards,
        'stats': stats,
        'games': games,
        'current_filters': {
            'reason': archive_reason,
            'game': game_id,
            'search': search_query,
        },
    }
    
    return render(request, 'tournaments/archive_list.html', context)


@login_required
@user_passes_test(is_staff_or_organizer, login_url='/login/')
@require_http_methods(["GET"])
def archive_detail_view(request: HttpRequest, slug: str):
    """
    View detailed archive information for a tournament
    
    URL: /tournaments/<slug>/archive/
    
    Features:
    - Complete archive details
    - All Phase 1 model data
    - Clone history
    - Restoration options
    - Archive metadata
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Get archive record
    try:
        archive = TournamentArchive.objects.select_related(
            'tournament',
            'archived_by',
            'original_tournament',
        ).get(tournament=tournament)
    except TournamentArchive.DoesNotExist:
        # Not archived - show error
        return render(request, 'tournaments/archive_detail.html', {
            'tournament': tournament,
            'not_archived': True,
        })
    
    # Get all Phase 1 models
    try:
        schedule = TournamentSchedule.objects.filter(tournament=tournament).first()
    except:
        schedule = None
    
    try:
        capacity = TournamentCapacity.objects.filter(tournament=tournament).first()
    except:
        capacity = None
    
    try:
        finance = TournamentFinance.objects.filter(tournament=tournament).first()
    except:
        finance = None
    
    try:
        media = TournamentMedia.objects.filter(tournament=tournament).first()
    except:
        media = None
    
    try:
        rules = TournamentRules.objects.filter(tournament=tournament).first()
    except:
        rules = None
    
    # Get clone history (tournaments cloned from this one)
    clones = TournamentArchive.objects.filter(
        original_tournament=tournament,
        is_clone=True
    ).select_related('tournament').order_by('-created_at')[:10]
    
    # Build context
    context = {
        'tournament': tournament,
        'archive': archive,
        
        # Phase 1 data
        'schedule': schedule,
        'capacity': capacity,
        'finance': finance,
        'media': media,
        'rules': rules,
        
        # Archive metadata
        'archive_info': {
            'is_archived': archive.is_archived,
            'archived_at': archive.archived_at,
            'archived_by': archive.archived_by,
            'archive_reason': archive.archive_reason,
            'can_restore': archive.can_restore,
            'is_clone': archive.is_clone,
            'original_tournament': archive.original_tournament,
            'preserve_registrations': archive.preserve_registrations,
            'preserve_matches': archive.preserve_matches,
        },
        
        # Clone history
        'clones': clones,
        'clone_count': clones.count(),
        
        # Permissions
        'can_restore': archive.can_restore and can_manage_archives(request.user),
        'can_clone': True,
        'can_delete': can_manage_archives(request.user),
    }
    
    return render(request, 'tournaments/archive_detail.html', context)


# ============================================================================
# ARCHIVE ACTIONS (API)
# ============================================================================

@login_required
@user_passes_test(can_manage_archives, login_url='/login/')
@require_POST
def archive_tournament_api(request: HttpRequest, slug: str) -> JsonResponse:
    """
    Archive a tournament (API endpoint)
    
    POST /api/tournaments/<slug>/archive/
    
    Request body:
    - reason: Archive reason (required)
    - preserve_registrations: bool (default: True)
    - preserve_matches: bool (default: True)
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    try:
        # Check if already archived
        existing_archive = TournamentArchive.objects.filter(tournament=tournament).first()
        if existing_archive and existing_archive.is_archived:
            return JsonResponse({
                'success': False,
                'errors': {'_archived': ['Tournament is already archived']}
            }, status=400)
        
        # Get parameters
        reason = request.POST.get('reason', '').strip()
        if not reason:
            return JsonResponse({
                'success': False,
                'errors': {'reason': ['Archive reason is required']}
            }, status=400)
        
        preserve_registrations = request.POST.get('preserve_registrations', 'true').lower() == 'true'
        preserve_matches = request.POST.get('preserve_matches', 'true').lower() == 'true'
        
        # Create or update archive
        if existing_archive:
            existing_archive.archive_reason = reason
            existing_archive.preserve_registrations = preserve_registrations
            existing_archive.preserve_matches = preserve_matches
            existing_archive.save()
            archive = existing_archive.archive()
        else:
            archive = TournamentArchive.objects.create(
                tournament=tournament,
                archive_reason=reason,
                preserve_registrations=preserve_registrations,
                preserve_matches=preserve_matches,
            )
            archive = archive.archive()
        
        return JsonResponse({
            'success': True,
            'message': f'Tournament "{tournament.name}" has been archived',
            'archived_at': archive.archived_at.isoformat() if archive.archived_at else None,
        })
        
    except ValidationError as e:
        errors = {}
        if hasattr(e, 'message_dict'):
            errors = e.message_dict
        else:
            errors = {'non_field_errors': [str(e)]}
        
        return JsonResponse({
            'success': False,
            'errors': errors
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'errors': {'non_field_errors': [str(e)]}
        }, status=500)


@login_required
@user_passes_test(can_manage_archives, login_url='/login/')
@require_POST
def restore_tournament_api(request: HttpRequest, slug: str) -> JsonResponse:
    """
    Restore a tournament from archive (API endpoint)
    
    POST /api/tournaments/<slug>/restore/
    
    Request body:
    - restore_reason: Optional restoration reason
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    try:
        # Get archive record
        archive = TournamentArchive.objects.filter(tournament=tournament).first()
        if not archive:
            return JsonResponse({
                'success': False,
                'errors': {'_not_found': ['Tournament is not archived']}
            }, status=404)
        
        if not archive.is_archived:
            return JsonResponse({
                'success': False,
                'errors': {'_not_archived': ['Tournament is not currently archived']}
            }, status=400)
        
        if not archive.can_restore:
            return JsonResponse({
                'success': False,
                'errors': {'_cannot_restore': ['This tournament cannot be restored']}
            }, status=400)
        
        # Restore
        restore_reason = request.POST.get('restore_reason', '').strip()
        restored_archive = archive.restore(restore_reason=restore_reason)
        
        return JsonResponse({
            'success': True,
            'message': f'Tournament "{tournament.name}" has been restored',
            'redirect_url': reverse('tournaments:detail', kwargs={'slug': slug}),
        })
        
    except ValidationError as e:
        errors = {}
        if hasattr(e, 'message_dict'):
            errors = e.message_dict
        else:
            errors = {'non_field_errors': [str(e)]}
        
        return JsonResponse({
            'success': False,
            'errors': errors
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'errors': {'non_field_errors': [str(e)]}
        }, status=500)


# ============================================================================
# CLONE FUNCTIONALITY
# ============================================================================

@login_required
@user_passes_test(is_staff_or_organizer, login_url='/login/')
@require_http_methods(["GET", "POST"])
def clone_tournament_view(request: HttpRequest, slug: str):
    """
    Clone a tournament (with or without archive)
    
    GET: Show clone configuration form
    POST: Create clone
    
    URL: /tournaments/<slug>/clone/
    
    Features:
    - Clone tournament structure
    - Clone all Phase 1 models
    - Optionally clone registrations
    - Optionally clone matches
    - Adjust dates automatically
    """
    original_tournament = get_object_or_404(Tournament, slug=slug)
    
    if request.method == 'GET':
        # Get Phase 1 models for preview
        try:
            schedule = TournamentSchedule.objects.filter(tournament=original_tournament).first()
        except:
            schedule = None
        
        try:
            capacity = TournamentCapacity.objects.filter(tournament=original_tournament).first()
        except:
            capacity = None
        
        try:
            finance = TournamentFinance.objects.filter(tournament=original_tournament).first()
        except:
            finance = None
        
        try:
            rules = TournamentRules.objects.filter(tournament=original_tournament).first()
        except:
            rules = None
        
        context = {
            'original_tournament': original_tournament,
            'schedule': schedule,
            'capacity': capacity,
            'finance': finance,
            'rules': rules,
            'suggested_name': f"{original_tournament.name} (Copy)",
        }
        
        return render(request, 'tournaments/clone_form.html', context)
    
    # POST: Create clone
    try:
        # Get clone parameters
        new_name = request.POST.get('name', '').strip()
        if not new_name:
            raise ValidationError({'name': 'Tournament name is required'})
        
        # Check for duplicate name
        if Tournament.objects.filter(name=new_name).exists():
            raise ValidationError({'name': 'A tournament with this name already exists'})
        
        clone_registrations = request.POST.get('clone_registrations', 'false').lower() == 'true'
        clone_matches = request.POST.get('clone_matches', 'false').lower() == 'true'
        
        # Date adjustments (optional)
        days_offset = request.POST.get('days_offset', '0')
        try:
            days_offset = int(days_offset)
        except ValueError:
            days_offset = 0
        
        # Get or create archive for original
        archive, created = TournamentArchive.objects.get_or_create(
            tournament=original_tournament,
            defaults={
                'archive_reason': 'Created for cloning',
                'preserve_registrations': True,
                'preserve_matches': True,
            }
        )
        
        # Clone the tournament
        cloned_tournament, cloned_archive = archive.clone_tournament(
            new_name=new_name,
            clone_registrations=clone_registrations,
            clone_matches=clone_matches,
        )
        
        # Adjust dates if offset provided
        if days_offset != 0:
            from datetime import timedelta
            try:
                schedule = TournamentSchedule.objects.filter(tournament=cloned_tournament).first()
                if schedule:
                    offset = timedelta(days=days_offset)
                    if schedule.registration_open_at:
                        schedule.registration_open_at += offset
                    if schedule.registration_close_at:
                        schedule.registration_close_at += offset
                    if schedule.start_at:
                        schedule.start_at += offset
                    if schedule.end_at:
                        schedule.end_at += offset
                    schedule.save()
            except Exception:
                pass  # Date adjustment is optional
        
        return redirect('tournaments:detail', slug=cloned_tournament.slug)
        
    except ValidationError as e:
        errors = {}
        if hasattr(e, 'message_dict'):
            errors = e.message_dict
        else:
            errors = {'non_field_errors': [str(e)]}
        
        context = {
            'original_tournament': original_tournament,
            'errors': errors,
            'form_data': request.POST,
        }
        return render(request, 'tournaments/clone_form.html', context)
    
    except Exception as e:
        context = {
            'original_tournament': original_tournament,
            'errors': {'non_field_errors': [str(e)]},
            'form_data': request.POST,
        }
        return render(request, 'tournaments/clone_form.html', context)


@login_required
@user_passes_test(is_staff_or_organizer, login_url='/login/')
@require_POST
def clone_tournament_api(request: HttpRequest, slug: str) -> JsonResponse:
    """
    Clone a tournament (API endpoint)
    
    POST /api/tournaments/<slug>/clone/
    
    Request body:
    - name: New tournament name (required)
    - clone_registrations: bool (default: false)
    - clone_matches: bool (default: false)
    - days_offset: int (default: 0) - Days to adjust dates
    """
    original_tournament = get_object_or_404(Tournament, slug=slug)
    
    try:
        # Get clone parameters
        new_name = request.POST.get('name', '').strip()
        if not new_name:
            return JsonResponse({
                'success': False,
                'errors': {'name': ['Tournament name is required']}
            }, status=400)
        
        # Check for duplicate name
        if Tournament.objects.filter(name=new_name).exists():
            return JsonResponse({
                'success': False,
                'errors': {'name': ['A tournament with this name already exists']}
            }, status=400)
        
        clone_registrations = request.POST.get('clone_registrations', 'false').lower() == 'true'
        clone_matches = request.POST.get('clone_matches', 'false').lower() == 'true'
        
        # Date adjustments
        days_offset = request.POST.get('days_offset', '0')
        try:
            days_offset = int(days_offset)
        except ValueError:
            days_offset = 0
        
        # Get or create archive for original
        archive, created = TournamentArchive.objects.get_or_create(
            tournament=original_tournament,
            defaults={
                'archive_reason': 'Created for cloning',
                'preserve_registrations': True,
                'preserve_matches': True,
            }
        )
        
        # Clone
        cloned_tournament, cloned_archive = archive.clone_tournament(
            new_name=new_name,
            clone_registrations=clone_registrations,
            clone_matches=clone_matches,
        )
        
        # Adjust dates if offset provided
        if days_offset != 0:
            from datetime import timedelta
            try:
                schedule = TournamentSchedule.objects.filter(tournament=cloned_tournament).first()
                if schedule:
                    offset = timedelta(days=days_offset)
                    if schedule.registration_open_at:
                        schedule.registration_open_at += offset
                    if schedule.registration_close_at:
                        schedule.registration_close_at += offset
                    if schedule.start_at:
                        schedule.start_at += offset
                    if schedule.end_at:
                        schedule.end_at += offset
                    schedule.save()
            except Exception:
                pass
        
        return JsonResponse({
            'success': True,
            'message': f'Tournament cloned successfully as "{new_name}"',
            'cloned_tournament': {
                'id': cloned_tournament.id,
                'name': cloned_tournament.name,
                'slug': cloned_tournament.slug,
            },
            'redirect_url': reverse('tournaments:detail', kwargs={'slug': cloned_tournament.slug}),
        })
        
    except ValidationError as e:
        errors = {}
        if hasattr(e, 'message_dict'):
            errors = e.message_dict
        else:
            errors = {'non_field_errors': [str(e)]}
        
        return JsonResponse({
            'success': False,
            'errors': errors
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'errors': {'non_field_errors': [str(e)]}
        }, status=500)


# ============================================================================
# ARCHIVE HISTORY & AUDIT
# ============================================================================

@login_required
@user_passes_test(can_manage_archives, login_url='/login/')
@require_http_methods(["GET"])
def archive_history_view(request: HttpRequest, slug: str):
    """
    View archive history for a tournament
    
    URL: /tournaments/<slug>/archive/history/
    
    Shows:
    - All archive/restore actions
    - Clone history
    - Audit trail
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    try:
        archive = TournamentArchive.objects.get(tournament=tournament)
    except TournamentArchive.DoesNotExist:
        raise Http404("No archive record found for this tournament")
    
    # Get clones
    clones = TournamentArchive.objects.filter(
        original_tournament=tournament,
        is_clone=True
    ).select_related('tournament', 'archived_by').order_by('-created_at')
    
    # Build timeline
    timeline_events = []
    
    # Archive event
    if archive.is_archived and archive.archived_at:
        timeline_events.append({
            'type': 'archived',
            'timestamp': archive.archived_at,
            'user': archive.archived_by,
            'description': archive.archive_reason,
        })
    
    # Clone events
    for clone in clones:
        timeline_events.append({
            'type': 'cloned',
            'timestamp': clone.created_at,
            'user': clone.archived_by,
            'description': f'Cloned as "{clone.tournament.name}"',
            'tournament': clone.tournament,
        })
    
    # Sort by timestamp (most recent first)
    timeline_events.sort(key=lambda x: x['timestamp'], reverse=True)
    
    context = {
        'tournament': tournament,
        'archive': archive,
        'timeline_events': timeline_events,
        'clones': clones,
    }
    
    return render(request, 'tournaments/archive_history.html', context)
