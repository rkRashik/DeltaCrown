# Phase 9A-30: Custom Game Passport Admin Interface

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator

from apps.user_profile.models import GameProfile
from apps.user_profile.models.cooldown import GamePassportCooldown
from apps.games.models import Game


@staff_member_required
def game_passport_admin_dashboard(request):
    """
    Custom admin dashboard for Game Passport management.
    Clean, modern interface for verification workflow.
    """
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    game_filter = request.GET.get('game', 'all')
    search_query = request.GET.get('q', '')
    page_number = request.GET.get('page', 1)
    
    # Base queryset
    passports = GameProfile.objects.select_related('user', 'game').all()
    
    # Apply filters
    if status_filter != 'all':
        passports = passports.filter(verification_status=status_filter)
    
    if game_filter != 'all':
        passports = passports.filter(game__slug=game_filter)
    
    if search_query:
        passports = passports.filter(
            Q(user__username__icontains=search_query) |
            Q(in_game_name__icontains=search_query) |
            Q(identity_key__icontains=search_query)
        )
    
    # Order by verification status priority (PENDING first, then FLAGGED, then VERIFIED)
    passports = passports.order_by(
        '-verification_status',  # PENDING > FLAGGED > VERIFIED alphabetically reversed
        '-created_at'
    )
    
    # Pagination
    paginator = Paginator(passports, 25)  # 25 per page
    page_obj = paginator.get_page(page_number)
    
    # Get statistics
    stats = {
        'total': GameProfile.objects.count(),
        'pending': GameProfile.objects.filter(verification_status='PENDING').count(),
        'verified': GameProfile.objects.filter(verification_status='VERIFIED').count(),
        'flagged': GameProfile.objects.filter(verification_status='FLAGGED').count(),
        'locked': GameProfile.objects.filter(locked_until__gt=timezone.now()).count(),
        'cooldown': GamePassportCooldown.objects.filter(expires_at__gt=timezone.now()).count(),
    }
    
    # Get all games for filter dropdown
    games = Game.objects.all().order_by('name')
    
    # Check cooldowns for displayed passports
    passports_with_cooldown = []
    for passport in page_obj:
        has_cooldown, cooldown_obj = GamePassportCooldown.check_cooldown(
            passport.user, passport.game, 'POST_DELETE'
        )
        passport.has_active_cooldown = has_cooldown
        passport.cooldown_days = cooldown_obj.days_remaining() if has_cooldown and cooldown_obj else 0
        
        # Add days_locked for UI display
        if passport.is_identity_locked and passport.locked_until is not None:
            passport.days_locked = (passport.locked_until - timezone.now()).days
        else:
            passport.days_locked = 0
        
        passports_with_cooldown.append(passport)
    
    context = {
        'page_obj': page_obj,
        'passports': passports_with_cooldown,
        'stats': stats,
        'games': games,
        'current_status': status_filter,
        'current_game': game_filter,
        'search_query': search_query,
    }
    
    return render(request, 'user_profile/admin/game_passport_dashboard.html', context)


@staff_member_required
def game_passport_verify(request, passport_id):
    """Mark a passport as VERIFIED"""
    passport = get_object_or_404(GameProfile, id=passport_id)
    
    if request.method == 'POST':
        passport.verification_status = 'VERIFIED'
        passport.verified_by = request.user
        passport.verified_at = timezone.now()
        passport.save()
        
        messages.success(request, f'âœ“ {passport.game.name} passport for {passport.user.username} marked as VERIFIED')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'status': 'VERIFIED'})
        
        return redirect('user_profile:game_passport_admin')
    
    return JsonResponse({'error': 'POST required'}, status=400)


@staff_member_required
def game_passport_flag(request, passport_id):
    """Mark a passport as FLAGGED"""
    passport = get_object_or_404(GameProfile, id=passport_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'Suspicious activity detected')
        
        passport.verification_status = 'FLAGGED'
        passport.flag_reason = reason
        passport.flagged_by = request.user
        passport.flagged_at = timezone.now()
        passport.save()
        
        messages.warning(request, f'âš  {passport.game.name} passport for {passport.user.username} marked as FLAGGED')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'status': 'FLAGGED'})
        
        return redirect('user_profile:game_passport_admin')
    
    return JsonResponse({'error': 'POST required'}, status=400)


@staff_member_required
def game_passport_reset(request, passport_id):
    """Reset passport to PENDING status"""
    passport = get_object_or_404(GameProfile, id=passport_id)
    
    if request.method == 'POST':
        passport.verification_status = 'PENDING'
        passport.verified_by = None
        passport.verified_at = None
        passport.flagged_by = None
        passport.flagged_at = None
        passport.flag_reason = ''
        passport.save()
        
        messages.info(request, f'â†º {passport.game.name} passport for {passport.user.username} reset to PENDING')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'status': 'PENDING'})
        
        return redirect('user_profile:game_passport_admin')
    
    return JsonResponse({'error': 'POST required'}, status=400)


@staff_member_required
def game_passport_unlock(request, passport_id):
    """Remove identity lock from passport"""
    passport = get_object_or_404(GameProfile, id=passport_id)
    
    if request.method == 'POST':
        passport.locked_until = None
        passport.save()
        
        messages.success(request, f'ðŸ”“ Identity lock removed from {passport.game.name} passport for {passport.user.username}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        return redirect('user_profile:game_passport_admin')
    
    return JsonResponse({'error': 'POST required'}, status=400)


@staff_member_required
def game_passport_override_cooldown(request, passport_id):
    """Override active cooldown"""
    passport = get_object_or_404(GameProfile, id=passport_id)
    
    if request.method == 'POST':
        has_cooldown, cooldown_obj = GamePassportCooldown.check_cooldown(
            passport.user, passport.game, 'POST_DELETE'
        )
        
        if has_cooldown and cooldown_obj:
            cooldown_obj.override(
                admin_user=request.user,
                reason=f"Admin override by {request.user.username}"
            )
            messages.success(request, f'âœ“ Cooldown removed for {passport.game.name} passport')
        else:
            messages.info(request, 'No active cooldown found')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        return redirect('user_profile:game_passport_admin')
    
    return JsonResponse({'error': 'POST required'}, status=400)


@staff_member_required
def game_passport_detail(request, passport_id):
    """View detailed information about a passport"""
    passport = get_object_or_404(GameProfile, id=passport_id)
    
    # Get cooldown info
    has_cooldown, cooldown_obj = GamePassportCooldown.check_cooldown(
        passport.user, passport.game, 'POST_DELETE'
    )
    
    # Add days_locked for UI display
    if passport.is_identity_locked:
        passport.days_locked = (passport.locked_until - timezone.now()).days
    else:
        passport.days_locked = 0
    
    # Get team memberships
    from apps.organizations.models import TeamMembership
    team_memberships = TeamMembership.objects.filter(
        user=passport.user,
        team__game_id=passport.game_id,
        status='ACTIVE'
    ).select_related('team')
    
    # Get tournament registrations
    from apps.tournaments.models import Registration
    tournament_registrations = Registration.objects.filter(
        user=passport.user,
        tournament__game__slug=passport.game.slug,
        status__in=['pending', 'confirmed', 'payment_submitted', 'submitted', 'auto_approved', 'needs_review']
    ).select_related('tournament')[:10]
    
    context = {
        'passport': passport,
        'has_cooldown': has_cooldown,
        'cooldown': cooldown_obj,
        'team_memberships': team_memberships,
        'tournament_registrations': tournament_registrations,
    }
    
    return render(request, 'user_profile/admin/game_passport_detail.html', context)

