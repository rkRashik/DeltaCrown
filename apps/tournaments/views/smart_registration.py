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

from apps.tournaments.models import Tournament, Registration, Payment
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

        context = self._build_context(request, tournament)
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
            registration = self._process_registration(request, tournament)
            return redirect('tournaments:dynamic_registration_success', tournament_slug=actual_slug, registration_id=registration.id)
        except ValidationError as e:
            error_msg = e.message if hasattr(e, 'message') else str(e)
            messages.error(request, error_msg)
            context = self._build_context(request, tournament)
            return render(request, self.template_name, context)
        except Exception as e:
            logger.exception(f"Registration failed for {request.user.username} in {actual_slug}: {e}")
            messages.error(request, "Something went wrong. Please try again.")
            context = self._build_context(request, tournament)
            return render(request, self.template_name, context)

    # ──────────────────────────────────────────────
    # Context Builder
    # ──────────────────────────────────────────────

    def _build_context(self, request, tournament):
        user = request.user
        is_team = tournament.participation_type == Tournament.TEAM

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
                roster_members = TeamMembership.objects.filter(
                    team=team,
                    status=TeamMembership.Status.ACTIVE
                ).select_related('user').order_by('role', '-joined_at')[:12]

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
                'locked': True,
                'source': 'username',
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
        Returns (selected_team_or_None, list_of_user_teams).
        """
        user = request.user

        # Get user's active team memberships where they can register
        # (OWNER, MANAGER, or is_tournament_captain)
        from django.db.models import Q
        eligible_memberships = TeamMembership.objects.filter(
            user=user,
            status=TeamMembership.Status.ACTIVE,
            team__game_id=tournament.game_id,
        ).filter(
            Q(role__in=['OWNER', 'MANAGER']) | Q(is_tournament_captain=True)
        ).select_related('team')

        user_teams = [m.team for m in eligible_memberships]

        if not user_teams:
            return None, []

        # If only one team, auto-select
        if len(user_teams) == 1:
            return user_teams[0], user_teams

        # If team_id passed in request, use that
        team_id = request.GET.get('team_id') or request.POST.get('team_id')
        if team_id:
            try:
                selected = Team.objects.get(id=int(team_id))
                if selected in user_teams:
                    return selected, user_teams
            except (Team.DoesNotExist, ValueError):
                pass

        return None, user_teams

    # ──────────────────────────────────────────────
    # Registration Processing
    # ──────────────────────────────────────────────

    def _process_registration(self, request, tournament):
        """Process form submission: create Registration + Payment."""
        user = request.user
        is_team = tournament.participation_type == Tournament.TEAM

        # Collect form data
        form_data = request.POST

        # Build registration_data JSON
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

        # Validate required fields
        if not registration_data['game_id']:
            raise ValidationError("Game ID is required for registration.")

        # Team ID
        team_id = None
        if is_team:
            team_id_str = form_data.get('team_id', '')
            if not team_id_str:
                raise ValidationError("Please select a team for registration.")
            team_id = int(team_id_str)

        # Create registration via service
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user,
            team_id=team_id,
            registration_data=registration_data,
        )

        # Handle payment
        if tournament.has_entry_fee:
            self._process_payment(request, registration, tournament)

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

