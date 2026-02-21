"""
Smart Registration View — One-Click, Auto-Fill Registration

Replaces the multi-step wizard with a single intelligent page:
- All fields auto-filled from Profile, GamePassport, and Team data
- Missing fields highlighted for quick manual entry
- Payment handled inline (DeltaCoin auto-debit, or mobile payment proof)
- One-click submission when ready
"""

import logging
import math
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models as db_models
from django.http import JsonResponse

from apps.tournaments.models import Tournament, Registration, Payment
from apps.tournaments.models.smart_registration import (
    RegistrationQuestion, RegistrationAnswer, RegistrationDraft,
)
from apps.tournaments.models.form_configuration import TournamentFormConfiguration
from apps.tournaments.services.registration_service import RegistrationService
from apps.tournaments.services.payment_service import PaymentService
from apps.tournaments.services.registration_autofill import RegistrationAutoFillService
from apps.tournaments.services.eligibility_service import RegistrationEligibilityService
from apps.games.services import game_service
from apps.organizations.models import Team, TeamMembership

logger = logging.getLogger(__name__)


class SmartRegistrationView(LoginRequiredMixin, View):
    """
    Smart one-page registration with auto-fill.

    GET: Auto-fill all data → render single smart page
    POST: Validate → create Registration + Payment → redirect to success
    """
    template_name = 'tournaments/registration/smart_register.html'

    def get(self, request, slug=None, tournament_slug=None):
        actual_slug = slug or tournament_slug
        tournament = get_object_or_404(
            Tournament.objects.select_related('game'),
            slug=actual_slug
        )

        # Eligibility check
        eligibility = RegistrationEligibilityService.check_eligibility(tournament, request.user)
        if not eligibility['can_register']:
            return self._render_ineligible(request, tournament, eligibility)

        context = self._build_context(request, tournament, eligibility)
        return render(request, self.template_name, context)

    def post(self, request, slug=None, tournament_slug=None):
        actual_slug = slug or tournament_slug
        tournament = get_object_or_404(
            Tournament.objects.select_related('game'),
            slug=actual_slug
        )

        # Re-check eligibility
        eligibility = RegistrationEligibilityService.check_eligibility(tournament, request.user)
        if not eligibility['can_register']:
            messages.error(request, eligibility['reason'])
            return redirect('tournaments:detail', slug=actual_slug)

        try:
            registration = self._process_registration(request, tournament, eligibility)
            return redirect('tournaments:dynamic_registration_success', tournament_slug=actual_slug, registration_id=registration.id)
        except ValidationError as e:
            error_msg = e.message if hasattr(e, 'message') else str(e)
            messages.error(request, error_msg)
            context = self._build_context(request, tournament, eligibility)
            return render(request, self.template_name, context)
        except Exception as e:
            logger.exception(f"Registration failed for {request.user.username} in {actual_slug}: {e}")
            messages.error(request, "Something went wrong. Please try again.")
            context = self._build_context(request, tournament, eligibility)
            return render(request, self.template_name, context)

    # ──────────────────────────────────────────────
    # Context Builder
    # ──────────────────────────────────────────────

    def _build_context(self, request, tournament, eligibility=None):
        user = request.user
        is_team = tournament.participation_type == Tournament.TEAM

        # Guest team detection
        is_guest_mode = (
            request.GET.get('guest') == '1'
            or request.POST.get('registration_type') == 'guest_team'
        )
        allows_guest = getattr(tournament, 'max_guest_teams', 0) and tournament.max_guest_teams > 0
        is_guest_team = is_team and allows_guest and is_guest_mode
        
        # Guest team slot info
        guest_slots_remaining = 0
        if allows_guest:
            current_guest_count = Registration.objects.filter(
                tournament=tournament,
                is_guest_team=True,
                is_deleted=False,
            ).exclude(
                status__in=[Registration.CANCELLED, Registration.REJECTED]
            ).count()
            guest_slots_remaining = max(0, tournament.max_guest_teams - current_guest_count)
        
        # Waitlist info
        is_waitlist = eligibility and eligibility.get('status') == 'full_waitlist'
        waitlist_count = Registration.objects.filter(
            tournament=tournament,
            status=Registration.WAITLISTED,
            is_deleted=False,
        ).count() if is_waitlist else 0

        # Game theme
        canonical_slug = game_service.normalize_slug(tournament.game.slug)
        game_spec = game_service.get_game(canonical_slug)
        game_color = getattr(game_spec, 'primary_color', '#06b6d4') if game_spec else '#06b6d4'
        game_color_rgb = getattr(game_spec, 'primary_color_rgb', '6, 182, 212') if game_spec else '6, 182, 212'

        # Determine team (for team tournaments)
        team = None
        roster_members = []
        user_teams = []

        if is_team:
            team, user_teams = self._resolve_team(request, tournament)
            if team:
                roster_members = list(
                    TeamMembership.objects.filter(
                        team=team,
                        status=TeamMembership.Status.ACTIVE
                    ).select_related('user__profile').order_by('role', '-joined_at')[:20]
                )

                # ── Attach game passport data per member ──
                if roster_members:
                    from apps.user_profile.models_main import GameProfile, SocialLink
                    member_user_ids = [m.user_id for m in roster_members]
                    passports = {
                        gp.user_id: gp
                        for gp in GameProfile.objects.filter(
                            user_id__in=member_user_ids,
                            game=tournament.game,
                            status=GameProfile.STATUS_ACTIVE,
                        )
                    }

                    # Prefetch discord social links for Player Info tab
                    discord_links = {}
                    try:
                        for sl in SocialLink.objects.filter(
                            user_id__in=member_user_ids,
                            platform='discord',
                        ):
                            discord_links[sl.user_id] = sl.handle or sl.url or ''
                    except Exception:
                        pass  # SocialLink may not exist yet

                    for member in roster_members:
                        gp = passports.get(member.user_id)
                        member._game_passport = gp  # attach for template access
                        member.gp_ign = gp.ign if gp else ''
                        member.gp_discriminator = gp.discriminator if gp else ''
                        member.gp_in_game_name = gp.in_game_name if gp else ''
                        member.gp_rank_name = gp.rank_name if gp else ''
                        member.gp_rank_image_url = gp.rank_image.url if gp and gp.rank_image else ''
                        member.gp_platform = gp.platform if gp else ''
                        member.gp_region = gp.region if gp else ''
                        member.gp_main_role = gp.main_role if gp else ''
                        member.gp_matches_played = gp.matches_played if gp else 0
                        member.gp_win_rate = gp.win_rate if gp else 0
                        member.gp_kd_ratio = gp.kd_ratio if gp else None
                        member.gp_hours_played = gp.hours_played if gp else None
                        member.gp_has_passport = bool(gp)

                        # ── Attach user profile data for Player Info tab ──
                        profile = getattr(member.user, 'profile', None)
                        member.profile_full_name = getattr(profile, 'real_full_name', '') or ''
                        member.profile_email = getattr(member.user, 'email', '') or ''
                        member.profile_discord = discord_links.get(member.user_id, '')
                        member.profile_pronouns = getattr(profile, 'pronouns', '') or ''
                        member.profile_phone = getattr(profile, 'phone', '') or ''
                        member.profile_country = str(getattr(profile, 'country', '') or '')
                        member.profile_gender = getattr(profile, 'gender', '') or ''
                        dob = getattr(profile, 'date_of_birth', None)
                        member.profile_dob = dob.isoformat() if dob else ''

        # ── Form Configuration (organizer-defined) ──
        form_config = TournamentFormConfiguration.get_or_create_for_tournament(tournament)
        form_config_ctx = form_config.to_template_context()

        # ── Game Roster Config (game-specific limits) ──
        roster_config = {}
        try:
            rl = game_service.get_roster_limits(tournament.game)
            roster_config = {
                'min_team_size': rl.get('min_team_size', 1),
                'max_team_size': rl.get('max_team_size', 5),
                'min_substitutes': rl.get('min_substitutes', 0),
                'max_substitutes': rl.get('max_substitutes', 2),
                'min_roster_size': rl.get('min_roster_size', 1),
                'max_roster_size': rl.get('max_roster_size', 10),
                'allow_coaches': rl.get('allow_coaches', True),
                'max_coaches': rl.get('max_coaches', 1),
                'allow_analysts': rl.get('allow_analysts', False),
                'max_analysts': rl.get('max_analysts', 0),
                'team_size_display': f"{rl.get('max_team_size', 5)}v{rl.get('max_team_size', 5)}" if rl.get('min_team_size') == rl.get('max_team_size') else f"{rl.get('min_team_size', 1)}-{rl.get('max_team_size', 5)}",
            }
        except Exception:
            roster_config = {
                'min_team_size': 5, 'max_team_size': 5,
                'min_substitutes': 0, 'max_substitutes': 2,
                'min_roster_size': 5, 'max_roster_size': 10,
                'allow_coaches': True, 'max_coaches': 1,
                'allow_analysts': False, 'max_analysts': 0,
                'team_size_display': '5v5',
            }

        # ── Roster role positions (game-specific from GameRole) ──
        roster_roles = []
        try:
            from apps.games.models import GameRole
            roster_roles = list(
                GameRole.objects.filter(
                    game=tournament.game,
                    is_active=True,
                ).order_by('order', 'role_name').values('role_name', 'role_code', 'icon', 'color', 'description')
            )
        except Exception:
            pass

        # Auto-fill via service
        autofill_data = RegistrationAutoFillService.get_autofill_data(user, tournament, team)
        completion = RegistrationAutoFillService.get_completion_percentage(autofill_data)
        missing_fields = RegistrationAutoFillService.get_missing_fields(autofill_data)

        # Build flat field dict for template
        fields = self._build_fields(user, tournament, autofill_data, game_spec)

        # Count filled vs missing for the fields we actually display
        display_keys = [
            'full_name', 'display_name', 'email', 'phone', 'discord', 'country',
            'game_id', 'platform_server', 'rank'
        ]
        filled_count = sum(1 for k in display_keys if fields.get(k, {}).get('value'))
        missing_count = sum(1 for k in display_keys if not fields.get(k, {}).get('value'))
        total_fields = len(display_keys)
        readiness = int((filled_count / total_fields) * 100) if total_fields else 100

        # Readiness ring calculations (SVG circumference for r=34)
        circumference = round(2 * math.pi * 34, 2)
        dash_offset = round(circumference * (1 - readiness / 100), 2)

        # Section completeness
        identity_complete = all(
            fields.get(k, {}).get('value')
            for k in ['full_name', 'display_name', 'email']
        )
        game_complete = bool(fields.get('game_id', {}).get('value'))

        # DeltaCoin check
        deltacoin_can_afford = False
        deltacoin_balance = 0
        if tournament.has_entry_fee:
            try:
                dc_check = PaymentService.can_use_deltacoin(user, int(tournament.entry_fee_amount))
                deltacoin_can_afford = dc_check['can_afford']
                deltacoin_balance = dc_check['balance']
            except Exception:
                pass

        # Game ID label (game-specific)
        game_id_label = 'Riot ID' if 'valorant' in (canonical_slug or '') else \
                        'Steam ID' if 'cs' in (canonical_slug or '') else \
                        'Game ID'
        game_id_placeholder = 'Name#TAG' if 'valorant' in (canonical_slug or '') else \
                              'Steam profile URL' if 'cs' in (canonical_slug or '') else \
                              'Your in-game name/ID'

        # Section completeness for progressive disclosure summary bar
        section_flags = [
            ('identity', identity_complete),
            ('game', game_complete),
        ]
        if is_team:
            section_flags.append(('team', team is not None))
        section_flags.append(('contact', True))   # always has a default
        section_flags.append(('details', True))    # read-only info
        if tournament.has_entry_fee:
            section_flags.append(('payment', False))  # needs user action
        section_flags.append(('terms', False))  # needs checkboxes

        sections_total = len(section_flags)
        sections_complete = sum(1 for _, done in section_flags if done)
        sections_needing_input = sections_total - sections_complete

        # ── Custom Questions ──
        custom_questions = list(
            RegistrationQuestion.objects.filter(
                db_models.Q(tournament=tournament) | db_models.Q(game=tournament.game, tournament__isnull=True),
                is_active=True,
            ).order_by('order', 'id')
        )
        # Filter by scope: for solo tournaments, exclude team-level questions
        if not is_team:
            custom_questions = [q for q in custom_questions if q.scope != RegistrationQuestion.TEAM_LEVEL]

        return {
            'tournament': tournament,
            'game_spec': game_spec,
            'game_color': game_color,
            'game_color_rgb': game_color_rgb,
            'registration_type': 'team' if is_team else 'solo',
            'fields': fields,
            'readiness': readiness,
            'filled_count': filled_count,
            'missing_count': missing_count,
            'total_fields': total_fields,
            'circumference': circumference,
            'dash_offset': dash_offset,
            'identity_complete': identity_complete,
            'game_complete': game_complete,
            'team': team,
            'roster_members': roster_members,
            'user_teams': user_teams,
            'deltacoin_can_afford': deltacoin_can_afford,
            'deltacoin_balance': deltacoin_balance,
            'game_id_label': game_id_label,
            'game_id_placeholder': game_id_placeholder,
            'sections_complete': sections_complete,
            'sections_total': sections_total,
            'sections_needing_input': sections_needing_input,
            'custom_questions': custom_questions,
            'refund_policy': tournament.refund_policy,
            'refund_policy_display': tournament.get_refund_policy_display(),
            'refund_policy_text': tournament.refund_policy_text,
            # Guest team context
            'is_guest_team': is_guest_team,
            'allows_guest_teams': allows_guest,
            'guest_slots_remaining': guest_slots_remaining,
            'max_guest_teams': getattr(tournament, 'max_guest_teams', 0),
            # Waitlist context
            'is_waitlist': is_waitlist,
            'waitlist_count': waitlist_count,
            # Display name override
            'allow_display_name_override': getattr(tournament, 'allow_display_name_override', False),
            # ── NEW: Form configuration (organizer-defined) ──
            'form_config': form_config_ctx,
            # ── NEW: Game roster config ──
            'roster_config': roster_config,
            'roster_roles': roster_roles,
            # ── NEW: Payment methods from tournament ──
            'payment_methods': getattr(tournament, 'payment_methods', None) or ['bkash', 'nagad', 'rocket'],
        }

    def _build_fields(self, user, tournament, autofill_data, game_spec):
        """
        Build a flat field dictionary for the template.

        Each field: { value, locked, source }
        """
        profile = getattr(user, 'profile', None)

        # Player identity
        full_name = user.get_full_name() or ''
        if not full_name and profile:
            full_name = getattr(profile, 'real_full_name', '') or ''

        # Game ID from autofill (passport)
        game_id_val = ''
        game_id_locked = False
        if 'player_id' in autofill_data and autofill_data['player_id'].value:
            game_id_val = autofill_data['player_id'].value
            game_id_locked = True  # From passport = verified
        elif 'ign' in autofill_data and autofill_data['ign'].value:
            game_id_val = autofill_data['ign'].value
            game_id_locked = True

        # Platform/server
        platform_val = ''
        if 'platform' in autofill_data and autofill_data['platform'].value:
            platform_val = autofill_data['platform'].value
        elif 'server' in autofill_data and autofill_data['server'].value:
            platform_val = autofill_data['server'].value

        # Rank
        rank_val = ''
        rank_locked = False
        if 'rank' in autofill_data and autofill_data['rank'].value:
            rank_val = autofill_data['rank'].value
            rank_locked = True

        # Discord — try autofill, then profile
        discord_val = ''
        if 'discord' in autofill_data and autofill_data['discord'].value:
            discord_val = autofill_data['discord'].value
        elif profile:
            discord_val = getattr(profile, 'discord_id', '') or getattr(profile, 'discord', '') or ''

        # Phone
        phone_val = ''
        if 'phone' in autofill_data and autofill_data['phone'].value:
            phone_val = autofill_data['phone'].value
        elif profile:
            phone_val = getattr(profile, 'phone', '') or ''

        # Country
        country_val = ''
        if 'country' in autofill_data and autofill_data['country'].value:
            country_val = autofill_data['country'].value
        elif profile:
            country_val = str(getattr(profile, 'country', '') or '')

        fields = {
            'full_name': {
                'value': full_name,
                'locked': bool(full_name),
                'source': 'profile',
            },
            'display_name': {
                'value': user.username,
                'locked': not getattr(tournament, 'allow_display_name_override', False),
                'source': 'username' if not getattr(tournament, 'allow_display_name_override', False) else 'editable',
            },
            'email': {
                'value': user.email,
                'locked': True,
                'source': 'account',
            },
            'phone': {
                'value': phone_val,
                'locked': False,
                'source': 'profile',
            },
            'discord': {
                'value': discord_val,
                'locked': False,
                'source': 'profile',
            },
            'country': {
                'value': country_val,
                'locked': False,
                'source': 'profile',
            },
            'game_id': {
                'value': game_id_val,
                'locked': game_id_locked,
                'source': 'game_passport',
            },
            'platform_server': {
                'value': platform_val,
                'locked': False,
                'source': 'game_passport',
            },
            'rank': {
                'value': rank_val,
                'locked': rank_locked,
                'source': 'game_passport',
            },
            'preferred_contact': {
                'value': 'discord' if discord_val else 'email',
                'locked': False,
                'source': 'default',
            },
        }
        return fields

    def _resolve_team(self, request, tournament):
        """
        Resolve team for team tournaments.

        Permission logic mirrors ``_check_team_eligibility`` in the
        eligibility service.  A user can register a team if ANY of:
          1. Role is OWNER or MANAGER on the membership
          2. ``is_tournament_captain`` flag is set
          3. Granular ``register_tournaments`` permission in JSON overrides
          4. User created the team (``team.created_by == user``)
          5. User is CEO of the team's owning Organization
          6. User is CEO/MANAGER in the owning Organization's membership

        Returns (selected_team_or_None, list_of_user_teams).
        """
        user = request.user
        from django.db.models import Q
        from apps.organizations.models import Organization, OrganizationMembership

        # ── 1. Teams via direct membership ──────────────────────────────
        memberships = list(
            TeamMembership.objects.filter(
                user=user,
                status=TeamMembership.Status.ACTIVE,
                team__game_id=tournament.game_id,
                team__status='ACTIVE',
            ).select_related('team')
        )

        # Filter in Python: role/captain/granular permission
        direct_teams = {}          # team_id → Team
        for m in memberships:
            if (
                m.role in ['OWNER', 'MANAGER']
                or m.is_tournament_captain
                or m.has_permission('register_tournaments')
            ):
                direct_teams[m.team_id] = m.team

        # ── 2. Teams via org-level authority (CEO / org MANAGER) ────────
        ceo_org_ids = set(
            Organization.objects.filter(ceo=user).values_list('id', flat=True)
        )
        staff_org_ids = set(
            OrganizationMembership.objects.filter(
                user=user, role__in=['CEO', 'MANAGER']
            ).values_list('organization_id', flat=True)
        )
        all_org_ids = ceo_org_ids | staff_org_ids

        if all_org_ids:
            org_teams = Team.objects.filter(
                game_id=tournament.game_id,
                organization_id__in=all_org_ids,
                status='ACTIVE',
            )
            for t in org_teams:
                direct_teams.setdefault(t.id, t)

        # ── 3. Teams the user personally created ────────────────────────
        created_teams = Team.objects.filter(
            created_by=user,
            game_id=tournament.game_id,
            status='ACTIVE',
        )
        for t in created_teams:
            direct_teams.setdefault(t.id, t)

        user_teams = list(direct_teams.values())

        if not user_teams:
            return None, []

        # If only one team, auto-select
        if len(user_teams) == 1:
            return user_teams[0], user_teams

        # If team_id passed in request, use that
        team_id = request.GET.get('team_id') or request.POST.get('team_id')
        if team_id:
            try:
                tid = int(team_id)
                selected = direct_teams.get(tid)
                if selected:
                    return selected, user_teams
            except (ValueError, TypeError):
                pass

        return None, user_teams

    # ──────────────────────────────────────────────
    # Registration Processing
    # ──────────────────────────────────────────────

    def _process_registration(self, request, tournament, eligibility=None):
        """Process form submission: create Registration + Payment."""
        user = request.user
        is_team = tournament.participation_type == Tournament.TEAM
        
        # Detect guest team submission
        is_guest_team = request.POST.get('registration_type') == 'guest_team'

        # Collect form data
        form_data = request.POST

        # ── Load form configuration for toggle-aware processing ──
        form_config = TournamentFormConfiguration.get_or_create_for_tournament(tournament)

        # Build registration_data JSON — core fields always captured
        registration_data = {
            'full_name': form_data.get('full_name', '').strip(),
            'display_name': form_data.get('display_name', user.username),
            'email': form_data.get('email', user.email),
            'phone': form_data.get('phone', '').strip(),
            'discord': form_data.get('discord', '').strip(),
            'country': form_data.get('country', '').strip(),
            'game_id': form_data.get('game_id', '').strip(),
            'platform_server': form_data.get('platform_server', '').strip(),
            'rank': form_data.get('rank', '').strip(),
            'preferred_contact': form_data.get('preferred_contact', 'discord'),
        }

        # ── Coordinator delegation (v3 flow) ──
        coordinator_is_self = form_data.get('coordinator_is_self', 'true')
        registration_data['coordinator_is_self'] = coordinator_is_self == 'true'
        if coordinator_is_self != 'true':
            coordinator_member_id = form_data.get('coordinator_member_id', '').strip()
            if coordinator_member_id:
                registration_data['coordinator_member_id'] = int(coordinator_member_id)

        # ── Coordinator role ──
        if form_config.enable_coordinator_role:
            registration_data['coordinator_role'] = form_data.get('coordinator_role', '').strip()

        # ── Organizer-enabled solo fields ──
        if form_config.enable_age_field:
            age_raw = form_data.get('age', '').strip()
            if age_raw:
                try:
                    age_val = int(age_raw)
                    if age_val < 13 or age_val > 99:
                        raise ValidationError("Age must be between 13 and 99.")
                    registration_data['age'] = age_val
                except (ValueError, TypeError):
                    raise ValidationError("Please enter a valid age.")

        # ── Captain contact fields ──
        if form_config.enable_captain_display_name_field:
            registration_data['captain_display_name'] = form_data.get('captain_display_name', '').strip()
        if form_config.enable_captain_whatsapp_field:
            registration_data['captain_whatsapp'] = form_data.get('captain_whatsapp', '').strip()
        if form_config.enable_captain_phone_field:
            registration_data['captain_phone'] = form_data.get('captain_phone', '').strip()
        if form_config.enable_captain_discord_field:
            registration_data['captain_discord'] = form_data.get('captain_discord', '').strip()

        # ── Dynamic communication channels ──
        channels = form_config.get_communication_channels()
        if channels:
            comms_data = {}
            for channel in channels:
                key = channel.get('key', '')
                if key:
                    # Check both comm_<key> (dynamic field) and <key> (static field)
                    val = (
                        form_data.get(f'comm_{key}', '').strip()
                        or form_data.get(key, '').strip()
                    )
                    # Also check captain_<key> variant (e.g. captain_whatsapp)
                    if not val:
                        val = form_data.get(f'captain_{key}', '').strip()
                    if val:
                        comms_data[key] = val
                    # Validate required channels
                    if channel.get('required') and not val:
                        label = channel.get('label', key)
                        raise ValidationError(f"{label} is required.")
            if comms_data:
                registration_data['communication_channels'] = comms_data

        # ── Team-specific fields ──
        if is_team:
            if form_config.enable_team_region_field:
                registration_data['team_region'] = form_data.get('team_region', '').strip()
            if form_config.enable_team_bio:
                registration_data['team_bio'] = form_data.get('team_bio', '').strip()
            # File uploads — store filenames; actual files stored via MEDIA_ROOT
            if form_config.enable_team_logo_upload and 'team_logo' in request.FILES:
                logo_file = request.FILES['team_logo']
                if logo_file.size > 5 * 1024 * 1024:
                    raise ValidationError("Team logo file must be under 5MB.")
                registration_data['team_logo_filename'] = logo_file.name
            if form_config.enable_team_banner_upload and 'team_banner' in request.FILES:
                banner_file = request.FILES['team_banner']
                if banner_file.size > 10 * 1024 * 1024:
                    raise ValidationError("Team banner file must be under 10MB.")
                registration_data['team_banner_filename'] = banner_file.name

        # ── Payment extra fields (stored in registration_data, not Payment) ──
        if tournament.has_entry_fee:
            if form_config.enable_payment_mobile_number_field:
                registration_data['payment_mobile_number'] = form_data.get('payment_mobile_number', '').strip()
            if form_config.enable_payment_notes_field:
                registration_data['payment_notes'] = form_data.get('payment_notes', '').strip()

        # Validate required fields
        if not registration_data['game_id']:
            raise ValidationError("Game ID is required for registration.")

        # Team ID / Guest team data
        team_id = None
        guest_team_data = None
        
        if is_guest_team:
            # Collect guest team fields
            guest_team_data = {
                'team_name': form_data.get('guest_team_name', '').strip(),
                'team_tag': form_data.get('guest_team_tag', '').strip(),
                'justification': form_data.get('guest_team_justification', '').strip(),
                'members': [],
            }
            
            # Collect member fields (dynamic rows, indexed 0..N)
            idx = 0
            while True:
                member_gid = form_data.get(f'member_game_id_{idx}', '').strip()
                member_name = form_data.get(f'member_display_name_{idx}', '').strip()
                if not member_gid and not member_name:
                    break
                if member_gid:
                    guest_team_data['members'].append({
                        'game_id': member_gid,
                        'display_name': member_name or member_gid,
                    })
                idx += 1
                if idx > 20:  # safety cap
                    break
        elif is_team:
            team_id_str = form_data.get('team_id', '')
            if not team_id_str:
                raise ValidationError("Please select a team for registration.")
            try:
                team_id = int(team_id_str)
            except (ValueError, TypeError):
                raise ValidationError("Invalid team selection.")

            # Re-verify team ownership — prevent team_id tampering
            resolved_team, user_teams = self._resolve_team(request, tournament)
            valid_team_ids = {t.id for t in user_teams}
            if team_id not in valid_team_ids:
                raise ValidationError("You don't have permission to register this team.")

        # Create registration via service
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user,
            team_id=team_id,
            registration_data=registration_data,
            is_guest_team=is_guest_team,
            guest_team_data=guest_team_data,
        )

        # ── Capture Lineup Snapshot (team tournaments) ──
        if is_team and team_id:
            try:
                roster_qs = TeamMembership.objects.filter(
                    team_id=team_id,
                    status=TeamMembership.Status.ACTIVE,
                ).select_related('user__profile')

                # Get roster limits for validation
                try:
                    rl = game_service.get_roster_limits(tournament.game)
                    min_roster = rl.get('min_team_size', 1)
                    max_roster = rl.get('max_roster_size', 20)
                except Exception:
                    min_roster = 1
                    max_roster = 20

                active_count = roster_qs.count()
                if active_count < min_roster:
                    raise ValidationError(
                        f"Your team needs at least {min_roster} active members "
                        f"but only has {active_count}."
                    )
                if active_count > max_roster:
                    raise ValidationError(
                        f"Your team roster ({active_count}) exceeds the maximum "
                        f"of {max_roster} members."
                    )

                # Collect per-member form overrides (roster_slot, player_role)
                submitted_member_ids = form_data.getlist('roster_member_ids')

                snapshot = []
                for member in roster_qs:
                    member_entry = {
                        'user_id': member.user_id,
                        'username': member.user.username,
                        'role': member.role,
                        'display_name': member.display_name or member.user.username,
                    }
                    # Capture per-member form data if submitted
                    mid = str(member.id)
                    roster_slot = form_data.get(f'member_{mid}_roster_slot', '').strip()
                    player_role = form_data.get(f'member_{mid}_player_role', '').strip()
                    if roster_slot:
                        member_entry['roster_slot'] = roster_slot
                    if player_role:
                        member_entry['player_role'] = player_role
                    # Capture per-member game_id override from form
                    member_game_id = form_data.get(f'member_{mid}_game_id', '').strip()
                    if member_game_id:
                        member_entry['game_id'] = member_game_id
                    # Capture game_id if available from profile
                    if hasattr(member.user, 'profile') and member.user.profile:
                        profile = member.user.profile
                        member_entry['avatar'] = (profile.avatar.url if getattr(profile, 'avatar', None) else '')

                    snapshot.append(member_entry)

                registration.lineup_snapshot = snapshot
                registration.save(update_fields=['lineup_snapshot'])
            except ValidationError:
                # Re-raise validation errors (roster size issues)
                raise
            except Exception as e:
                logger.warning(f"Failed to capture lineup snapshot: {e}")

        # Handle payment
        if tournament.has_entry_fee:
            self._process_payment(request, registration, tournament)

        # ── Save Custom Question Answers ──
        custom_questions = RegistrationQuestion.objects.filter(
            db_models.Q(tournament=tournament) | db_models.Q(game=tournament.game, tournament__isnull=True),
            is_active=True,
        )
        if not is_team:
            custom_questions = custom_questions.exclude(scope=RegistrationQuestion.TEAM_LEVEL)

        answers_to_create = []
        for question in custom_questions:
            field_name = f'custom_q_{question.id}'
            if question.type == RegistrationQuestion.MULTI_SELECT:
                raw_value = form_data.getlist(field_name)
                value = raw_value if raw_value else []
            elif question.type == RegistrationQuestion.BOOLEAN:
                value = field_name in form_data
            elif question.type == RegistrationQuestion.FILE:
                if field_name in request.FILES:
                    # Store filename reference — file handling can be extended later
                    value = request.FILES[field_name].name
                else:
                    value = ''
            else:
                value = form_data.get(field_name, '').strip()

            # Validate required
            if question.is_required and not value:
                raise ValidationError(f'"{question.text}" is required.')

            if value or value == 0 or value is False:
                answers_to_create.append(RegistrationAnswer(
                    registration=registration,
                    question=question,
                    value=value if isinstance(value, (list, bool)) else str(value),
                    normalized_value=str(value).lower() if isinstance(value, str) else str(value),
                ))

        if answers_to_create:
            RegistrationAnswer.objects.bulk_create(answers_to_create)

        # P2-T07: Delete draft on successful registration
        RegistrationDraft.objects.filter(
            user=user,
            tournament=tournament,
            submitted=False,
        ).update(submitted=True)

        return registration

    def _process_payment(self, request, registration, tournament):
        """Process payment for paid tournaments."""
        payment_method = request.POST.get('payment_method', '')

        if not payment_method:
            raise ValidationError("Please select a payment method.")

        amount = tournament.entry_fee_amount

        if payment_method == 'deltacoin':
            # Auto-debit DeltaCoin via PaymentService
            dc_check = PaymentService.can_use_deltacoin(request.user, int(amount))
            if not dc_check['can_afford']:
                raise ValidationError(
                    f"Insufficient DeltaCoin balance. "
                    f"You have {dc_check['balance']} DC but need {int(amount)} DC."
                )

            try:
                PaymentService.process_deltacoin_payment(
                    registration_id=registration.id,
                    user=request.user,
                    idempotency_key=f"reg-{registration.id}-deltacoin"
                )
            except Exception as e:
                logger.warning(f"DeltaCoin auto-processing failed: {e}")
                raise ValidationError(f"DeltaCoin payment failed: {e}")

        else:
            # Cash methods (bKash, Nagad, Rocket)
            transaction_id = request.POST.get('transaction_id', '').strip()
            if not transaction_id:
                raise ValidationError("Transaction ID is required for mobile payment.")

            # Handle payment proof upload
            payment_proof = ''
            if 'payment_proof' in request.FILES:
                proof_file = request.FILES['payment_proof']
                # Validate file size (5MB max)
                if proof_file.size > 5 * 1024 * 1024:
                    raise ValidationError("Payment proof file must be under 5MB.")
                payment_proof = proof_file

            payment = RegistrationService.submit_payment(
                registration_id=registration.id,
                payment_method=payment_method,
                amount=Decimal(str(amount)),
                transaction_id=transaction_id,
                payment_proof=payment_proof,
            )

    # ──────────────────────────────────────────────
    # Ineligible rendering
    # ──────────────────────────────────────────────

    def _render_ineligible(self, request, tournament, eligibility):
        """Render the ineligible page with reasons."""
        canonical_slug = game_service.normalize_slug(tournament.game.slug)
        game_spec = game_service.get_game(canonical_slug)
        game_color = getattr(game_spec, 'primary_color', '#06b6d4') if game_spec else '#06b6d4'
        game_color_rgb = getattr(game_spec, 'primary_color_rgb', '6, 182, 212') if game_spec else '6, 182, 212'

        reasons = [eligibility['reason']] if eligibility.get('reason') else []

        suggestions = []
        status = eligibility.get('status', '')
        if status == 'not_authenticated':
            suggestions.append('Log in or create an account to register.')
        elif status == 'already_registered':
            suggestions.append('You are already registered. Visit the tournament lobby.')
        elif status == 'team_already_registered':
            suggestions.append('Your team is already registered. Check with your team captain.')
        elif status == 'full':
            suggestions.append('This tournament is currently full. Check back for cancellations or join the waitlist.')
        elif status == 'registration_closed':
            suggestions.append('Registration is no longer open for this tournament.')
        elif status in ('no_team', 'no_eligible_team'):
            suggestions.append('Create or join a team for this game to register.')
            suggestions.append('Ask your team captain to register the team.')
        elif status == 'no_captain_permission':
            suggestions.append('Only team owners and managers can register a team.')
            suggestions.append('Ask your team captain to register, or request registration permission.')

        return render(request, 'tournaments/registration/smart_ineligible.html', {
            'tournament': tournament,
            'game_color': game_color,
            'game_color_rgb': game_color_rgb,
            'reasons': reasons,
            'suggestions': suggestions,
        })


class SmartRegistrationSuccessView(LoginRequiredMixin, View):
    """Registration success page with confetti."""

    def get(self, request, slug=None, tournament_slug=None, registration_id=None):
        actual_slug = slug or tournament_slug
        tournament = get_object_or_404(Tournament.objects.select_related('game'), slug=actual_slug)
        registration = get_object_or_404(
            Registration,
            id=registration_id,
            tournament=tournament,
        )

        # Security: only the registrant can see their success page
        if registration.user and registration.user != request.user:
            # Check team membership
            if registration.team:
                is_member = TeamMembership.objects.filter(
                    team=registration.team,
                    user=request.user,
                    status=TeamMembership.Status.ACTIVE
                ).exists()
                if not is_member:
                    messages.error(request, "You don't have access to this registration.")
                    return redirect('tournaments:detail', slug=actual_slug)
            else:
                messages.error(request, "You don't have access to this registration.")
                return redirect('tournaments:detail', slug=actual_slug)

        # Game colors
        canonical_slug = game_service.normalize_slug(tournament.game.slug)
        game_spec = game_service.get_game(canonical_slug)
        game_color = getattr(game_spec, 'primary_color', '#06b6d4') if game_spec else '#06b6d4'
        game_color_rgb = getattr(game_spec, 'primary_color_rgb', '6, 182, 212') if game_spec else '6, 182, 212'

        return render(request, 'tournaments/registration/smart_success.html', {
            'tournament': tournament,
            'registration': registration,
            'team': registration.team,
            'game_color': game_color,
            'game_color_rgb': game_color_rgb,
        })


class SmartDraftSaveAPIView(LoginRequiredMixin, View):
    """P2-T07: Auto-save draft for smart registration (JSON API)."""

    def post(self, request, slug=None, tournament_slug=None):
        import json as _json
        actual_slug = slug or tournament_slug
        tournament = get_object_or_404(Tournament, slug=actual_slug)

        try:
            body = _json.loads(request.body)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

        form_data = body.get('form_data', {})
        if not isinstance(form_data, dict):
            return JsonResponse({'success': False, 'error': 'form_data must be a dict'}, status=400)

        draft, created = RegistrationDraft.objects.get_or_create(
            user=request.user,
            tournament=tournament,
            defaults={
                'registration_number': f"DRF-{tournament.id}-{request.user.id}",
                'form_data': form_data,
                'expires_at': timezone.now() + timezone.timedelta(days=7),
            }
        )

        if not created:
            draft.form_data = form_data
            draft.expires_at = timezone.now() + timezone.timedelta(days=7)
            draft.save(update_fields=['form_data', 'expires_at', 'updated_at'])

        return JsonResponse({
            'success': True,
            'draft_uuid': str(draft.uuid),
            'saved_at': draft.last_saved_at.isoformat() if draft.last_saved_at else None,
        })


class SmartDraftGetAPIView(LoginRequiredMixin, View):
    """P2-T07: Retrieve saved draft for smart registration (JSON API)."""

    def get(self, request, slug=None, tournament_slug=None):
        actual_slug = slug or tournament_slug
        tournament = get_object_or_404(Tournament, slug=actual_slug)

        try:
            draft = RegistrationDraft.objects.get(
                user=request.user,
                tournament=tournament,
                submitted=False,
            )
        except RegistrationDraft.DoesNotExist:
            return JsonResponse({'success': True, 'draft': None})

        if draft.is_expired():
            draft.delete()
            return JsonResponse({'success': True, 'draft': None})

        return JsonResponse({
            'success': True,
            'draft': {
                'uuid': str(draft.uuid),
                'form_data': draft.form_data,
                'saved_at': draft.last_saved_at.isoformat() if draft.last_saved_at else None,
            },
        })

