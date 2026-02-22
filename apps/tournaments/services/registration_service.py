"""
Registration Service - Business logic for tournament registration and payment operations.

Source Documents:
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Section 5: Service Layer - RegistrationService, PaymentService)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 4: Registration & Payment Models)
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md (UI Flow and Payment Verification)
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md (ADR-001: Service Layer Pattern, ADR-003: Soft Delete)

Architecture Decisions:
- ADR-001: Service Layer Pattern - All business logic in services, not views or models
- ADR-003: Soft Delete Strategy - Cancellation uses soft delete with refund tracking
- ADR-004: PostgreSQL Features - JSONB for registration_data

Responsibilities:
- Registration creation with eligibility validation
- Payment submission and verification
- Registration cancellation with refund processing
- Auto-fill registration data from user profile
- Slot and seed assignment coordination

Integration Points:
- TournamentService: Capacity and slot management
- apps.user_profile: Auto-fill registration data
- apps.economy: DeltaCoin payment processing (future)
- apps.notifications: Registration status notifications (future)

Usage:
    from apps.tournaments.services import RegistrationService
    
    # Register participant
    registration = RegistrationService.register_participant(
        tournament_id=tournament.id,
        user=request.user,
        registration_data={
            'game_id': 'Player#TAG',
            'phone': '+8801712345678',
            'notes': 'Ready to compete!'
        }
    )
    
    # Submit payment
    payment = RegistrationService.submit_payment(
        registration_id=registration.id,
        payment_method='bkash',
        amount=Decimal('500.00'),
        transaction_id='TXN123456',
        payment_proof='path/to/proof.jpg'
    )
    
    # Verify payment (admin action)
    RegistrationService.verify_payment(
        payment_id=payment.id,
        verified_by=request.user,
        admin_notes='Payment verified successfully'
    )
"""

from typing import Dict, Optional, Any
import logging
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction, models
from django.utils import timezone
from django.db.models import Count, Q
from apps.tournaments.models import Registration, Payment, Tournament
from apps.user_profile.integrations.tournaments import (
    on_registration_status_change,
    on_payment_status_change,
)

logger = logging.getLogger(__name__)


def _publish_registration_event(event_name: str, **kwargs):
    """Publish registration lifecycle events via the core EventBus (fire-and-forget)."""
    try:
        from apps.tournament_ops.events.publishers import (
            publish_registration_created,
            publish_registration_confirmed,
        )
        if event_name == "registration.created":
            publish_registration_created(**kwargs)
        elif event_name == "registration.confirmed":
            publish_registration_confirmed(**kwargs)
        else:
            # Generic fallback for events without a dedicated publisher
            from apps.core.events import event_bus
            from apps.core.events.bus import Event
            event_bus.publish(Event(event_type=event_name, data=kwargs, source="registration_service"))
    except Exception as exc:
        logger.warning("Failed to publish %s event: %s", event_name, exc)


class RegistrationService:
    """
    Service class for tournament registration business logic.
    
    Handles:
    - Participant registration with eligibility checks
    - Payment submission and verification
    - Registration cancellation with refunds
    - Slot and seed assignment
    """
    
    @staticmethod
    @transaction.atomic
    def register_participant(
        tournament_id: int,
        user,
        team_id: Optional[int] = None,
        registration_data: Optional[Dict[str, Any]] = None,
        is_guest_team: bool = False,
        guest_team_data: Optional[Dict[str, Any]] = None,
    ) -> Registration:
        """
        Register a participant (user or team) for a tournament.
        
        Args:
            tournament_id: ID of tournament to register for
            user: User registering (either solo participant or team captain)
            team_id: Team ID if registering as a team (optional)
            registration_data: Additional registration data (JSONB)
                - game_id (str): In-game ID/username
                - phone (str): Contact phone number
                - notes (str): Additional notes
                - custom_fields (dict): Tournament-specific custom fields
                - team_roster (list): For team registrations
            is_guest_team: Whether this is a guest (ad-hoc) team registration
            guest_team_data: Guest team details when is_guest_team=True
                - team_name (str): Name of the guest team
                - team_tag (str): Short tag/abbreviation (max 6 chars)
                - captain (dict): { 'game_id': ..., 'display_name': ... }
                - members (list[dict]): [{ 'game_id': ..., 'display_name': ... }, ...]
                - justification (str): Optional reason for guest team
        
        Returns:
            Registration: Created registration instance
        
        Raises:
            Tournament.DoesNotExist: If tournament not found
            ValidationError: If registration fails validation
        
        Example:
            >>> registration = RegistrationService.register_participant(
            ...     tournament_id=42,
            ...     user=request.user,
            ...     registration_data={
            ...         'game_id': 'Player#TAG',
            ...         'phone': '+8801712345678',
            ...         'notes': 'Looking forward to competing!'
            ...     }
            ... )
        """
        # Get tournament with lock for capacity checks
        try:
            tournament = Tournament.objects.select_related('game').select_for_update().get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament with ID {tournament_id} not found")
        
        # Validate eligibility (skips team requirement for guest teams)
        RegistrationService.check_eligibility(
            tournament=tournament,
            user=user,
            team_id=team_id,
            is_guest_team=is_guest_team,
        )
        
        # Guest team validations
        if is_guest_team:
            RegistrationService._validate_guest_team(
                tournament=tournament,
                user=user,
                guest_team_data=guest_team_data,
            )
        
        # Auto-fill registration data from user profile if not provided
        if registration_data is None:
            registration_data = {}
        
        auto_filled_data = RegistrationService._auto_fill_registration_data(
            user=user,
            tournament=tournament
        )
        # Merge auto-filled with provided data (provided data takes precedence)
        merged_data = {**auto_filled_data, **registration_data}
        
        # Store guest team data in registration_data JSON
        if is_guest_team and guest_team_data:
            merged_data['guest_team'] = guest_team_data
        
        # Duplicate game ID detection
        game_id = merged_data.get('game_id', '')
        if game_id:
            RegistrationService._check_duplicate_game_id(
                tournament=tournament,
                game_id=game_id,
                exclude_user=user,
            )
        
        # Determine registration status based on capacity
        current_registrations = Registration.objects.filter(
            tournament=tournament,
            status__in=[Registration.PENDING, Registration.PAYMENT_SUBMITTED, Registration.CONFIRMED],
            is_deleted=False,
        ).count()
        
        at_capacity = current_registrations >= tournament.max_participants
        
        if is_guest_team:
            initial_status = Registration.PENDING  # Guest teams always start as PENDING for review
        elif at_capacity:
            initial_status = Registration.WAITLISTED
        else:
            initial_status = Registration.PENDING
        
        # Create registration
        # Note: For team registrations, user must be None (XOR constraint)
        # For guest teams: user is set, team_id is None, is_guest_team=True
        registration = Registration(
            tournament=tournament,
            user=user if (is_guest_team or not team_id) else None,
            team_id=team_id if not is_guest_team else None,
            registration_data=merged_data,
            status=initial_status,
            is_guest_team=is_guest_team,
        )
        
        # Assign waitlist position if waitlisted
        if initial_status == Registration.WAITLISTED:
            last_position = Registration.objects.filter(
                tournament=tournament,
                status=Registration.WAITLISTED,
                is_deleted=False,
            ).aggregate(max_pos=models.Max('waitlist_position'))['max_pos'] or 0
            registration.waitlist_position = last_position + 1
        
        # Validate
        registration.full_clean()
        registration.save()
        
        # Publish registration.created event + UserProfile activity tracking
        def _emit_created():
            try:
                on_registration_status_change(
                    user_id=user.id if user else None,
                    tournament_id=tournament.id,
                    registration_id=registration.id,
                    status='created',
                )
            except Exception:
                pass  # Non-blocking
            _publish_registration_event(
                "registration.created",
                registration_id=registration.id,
                tournament_id=tournament.id,
                team_id=team_id,
                user_id=user.id if user else None,
                is_guest_team=is_guest_team,
                is_waitlisted=initial_status == Registration.WAITLISTED,
                source="registration_service",
            )
        transaction.on_commit(_emit_created)
        
        return registration
    
    @staticmethod
    def check_eligibility(
        tournament: Tournament,
        user,
        team_id: Optional[int] = None,
        is_guest_team: bool = False,
    ) -> None:
        """
        Check if a participant is eligible to register for a tournament.
        
        Args:
            tournament: Tournament to check eligibility for
            user: User attempting to register
            team_id: Team ID if registering as a team
            is_guest_team: Whether this is a guest team registration
        
        Raises:
            ValidationError: If participant is not eligible
        
        Validation Rules:
            1. Tournament must be accepting registrations (status = REGISTRATION_OPEN)
            2. Registration period must be active (within registration_start and registration_end)
            3. Tournament capacity check (auto-waitlist when full, no hard reject)
            4. User/team must not already be registered
            5. Participation type must match (team vs solo; guest teams bypass team requirement)
        """
        # Check tournament status
        if tournament.status != Tournament.REGISTRATION_OPEN:
            raise ValidationError(
                f"Tournament is not accepting registrations (status: {tournament.get_status_display()})"
            )
        
        # Check registration period
        now = timezone.now()
        if now < tournament.registration_start:
            raise ValidationError(
                f"Registration opens on {tournament.registration_start.strftime('%Y-%m-%d %H:%M')}"
            )
        if now > tournament.registration_end:
            raise ValidationError(
                f"Registration closed on {tournament.registration_end.strftime('%Y-%m-%d %H:%M')}"
            )
        
        # Capacity check — no longer hard-rejects; register_participant() auto-waitlists
        # We still hard-reject if waitlist is also disabled in future, but for now allow through
        
        # Check participation type match
        # Guest teams bypass the "must have a team_id" requirement for TEAM tournaments
        if not is_guest_team:
            if tournament.participation_type == Tournament.TEAM and team_id is None:
                raise ValidationError("This tournament requires team registration")
            if tournament.participation_type == Tournament.SOLO and team_id is not None:
                raise ValidationError("This tournament is for solo participants only")
        else:
            # Guest teams only valid for TEAM tournaments
            if tournament.participation_type != Tournament.TEAM:
                raise ValidationError("Guest teams are only allowed for team tournaments")
        
        # For team registrations, validate user has permission to register the team
        if team_id is not None and not is_guest_team:
            RegistrationService._validate_team_registration_permission(team_id, user)
        
        # Check for duplicate registration
        existing_registration = Registration.objects.filter(
            tournament=tournament,
            user=user,
            is_deleted=False
        ).exclude(
            status__in=[Registration.CANCELLED, Registration.REJECTED]
        ).first()
        
        if existing_registration:
            if is_guest_team:
                raise ValidationError(
                    "You have already submitted a guest team for this tournament."
                )
            raise ValidationError("You are already registered for this tournament")
        
        # For team registrations, check if team is already registered
        if team_id is not None:
            team_registered = Registration.objects.filter(
                tournament=tournament,
                team_id=team_id,
                is_deleted=False
            ).exclude(
                status__in=[Registration.CANCELLED, Registration.REJECTED]
            ).exists()
            
            if team_registered:
                raise ValidationError("This team is already registered for this tournament")
    
    @staticmethod
    def _validate_team_registration_permission(team_id: int, user) -> None:
        """
        Validate that the user has permission to register the team for tournaments.
        
        Args:
            team_id: ID of the team to validate
            user: User attempting to register the team
        
        Raises:
            ValidationError: If user lacks permission to register this team
        
        Permission Rules (any ONE is sufficient):
            1. Team role is OWNER or MANAGER
            2. ``is_tournament_captain`` flag is set on membership
            3. Granular ``register_tournaments`` permission in JSON overrides
            4. User is the team's creator (``team.created_by == user``)
            5. User is CEO of the team's owning Organization
            6. User is CEO/MANAGER in owning Organization's staff membership
        """
        from apps.organizations.models import TeamMembership, Team
        from apps.organizations.models import Organization, OrganizationMembership
        
        # Get team
        try:
            team = Team.objects.select_related('organization').get(id=team_id)
        except Team.DoesNotExist:
            raise ValidationError(f"Team with ID {team_id} not found")
        
        # ── Check 4: Team creator ───────────────────────────────────
        if team.created_by_id == user.id:
            return  # Allowed
        
        # ── Check 5 & 6: Org-level authority (CEO / org MANAGER) ───
        if team.organization_id:
            # Direct CEO field on Organization
            is_org_ceo = (
                team.organization and team.organization.ceo_id == user.id
            )
            if is_org_ceo:
                return  # Allowed
            
            # OrganizationMembership with CEO or MANAGER role
            is_org_staff = OrganizationMembership.objects.filter(
                organization_id=team.organization_id,
                user=user,
                role__in=['CEO', 'MANAGER'],
            ).exists()
            if is_org_staff:
                return  # Allowed
        
        # ── Check 1, 2, 3: Team membership checks ──────────────────
        try:
            membership = TeamMembership.objects.get(
                team=team,
                user=user,
                status=TeamMembership.Status.ACTIVE
            )
        except TeamMembership.DoesNotExist:
            raise ValidationError(
                f"You are not an active member of {team.name}. "
                "Only team members can register their team."
            )
        
        # Role-based: OWNER or MANAGER
        if membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER,
        ]:
            return  # Allowed
        
        # Tournament captain flag
        if membership.is_tournament_captain:
            return  # Allowed
        
        # Granular permission override
        if membership.has_permission('register_tournaments'):
            return  # Allowed
        
        raise ValidationError(
            f"You do not have permission to register {team.name} for tournaments. "
            "Only team owners, managers, or members with explicit registration "
            "permission can register teams."
        )
    
    @staticmethod
    def _auto_fill_registration_data(user, tournament: Tournament) -> Dict[str, Any]:
        """
        Auto-fill registration data from user profile.
        
        Args:
            user: User to pull data from
            tournament: Tournament to register for (for game-specific fields)
        
        Returns:
            Dict containing auto-filled registration data
        
        Note:
            This is an internal helper method. Returns empty dict if profile doesn't exist.
        """
        try:
            profile = user.profile
        except Exception:
            # Profile doesn't exist or error accessing it
            return {}
        
        # Get game-specific ID field from GameService
        from apps.games.services import game_service
        canonical_slug = game_service.normalize_slug(tournament.game.slug)
        game_spec = game_service.get_game(canonical_slug)
        game_id_field = game_spec.profile_id_field if game_spec and hasattr(game_spec, 'profile_id_field') else 'game_id'
        game_id = getattr(profile, game_id_field, None) if game_id_field else None
        
        data = {
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
        }
        
        # Add game ID if available
        if game_id:
            data['game_id'] = game_id
        
        # Add optional profile fields if they exist
        # Discord is stored in SocialLink model, not on UserProfile
        try:
            from apps.user_profile.models_main import SocialLink
            discord_link = SocialLink.objects.filter(
                user=user, platform='discord'
            ).first()
            if discord_link and discord_link.handle:
                data['discord'] = discord_link.handle
        except Exception:
            pass
        if hasattr(profile, 'phone') and profile.phone:
            data['phone'] = profile.phone
        
        return data
    
    @staticmethod
    def _validate_guest_team(
        tournament: Tournament,
        user,
        guest_team_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Validate guest team registration constraints.
        
        Checks:
        1. Tournament allows guest teams (max_guest_teams > 0)
        2. Guest team cap not reached (atomic check)
        3. User hasn't already registered a guest team for this tournament
        4. Required guest_team_data fields are present
        
        Raises:
            ValidationError: If guest team registration is not allowed
        """
        # Check if tournament allows guest teams
        if not getattr(tournament, 'max_guest_teams', 0) or tournament.max_guest_teams <= 0:
            raise ValidationError(
                "This tournament does not allow guest team registrations."
            )
        
        # Check guest team cap (atomic, tournament already locked with select_for_update)
        current_guest_count = Registration.objects.filter(
            tournament=tournament,
            is_guest_team=True,
            is_deleted=False,
        ).exclude(
            status__in=[Registration.CANCELLED, Registration.REJECTED]
        ).count()
        
        if current_guest_count >= tournament.max_guest_teams:
            raise ValidationError(
                f"Guest team slots are full ({tournament.max_guest_teams} max). "
                "Consider joining an existing team instead."
            )
        
        # Rate limit: 1 guest team per user per tournament
        existing_guest = Registration.objects.filter(
            tournament=tournament,
            user=user,
            is_guest_team=True,
            is_deleted=False,
        ).exclude(
            status__in=[Registration.CANCELLED, Registration.REJECTED]
        ).exists()
        
        if existing_guest:
            raise ValidationError(
                "You have already submitted a guest team for this tournament."
            )
        
        # Validate required guest_team_data fields
        if not guest_team_data:
            raise ValidationError("Guest team details are required.")
        
        if not guest_team_data.get('team_name', '').strip():
            raise ValidationError("Guest team name is required.")
        
        if not guest_team_data.get('team_tag', '').strip():
            raise ValidationError("Guest team tag is required.")
        
        tag = guest_team_data['team_tag'].strip()
        if len(tag) > 6:
            raise ValidationError("Guest team tag must be 6 characters or fewer.")
        
        members = guest_team_data.get('members', [])
        if not members or len(members) < 1:
            raise ValidationError(
                "At least one team member is required for guest team registration."
            )
    
    @staticmethod
    def _check_duplicate_game_id(
        tournament: Tournament,
        game_id: str,
        exclude_user=None,
    ) -> None:
        """
        Check if a game ID is already used in another active registration.
        
        Prevents the same in-game account from appearing in multiple
        registrations for the same tournament (cross-team duplicate detection).
        
        Args:
            tournament: Tournament to check within
            game_id: The in-game ID to check
            exclude_user: User to exclude from the check (for re-registration)
        
        Raises:
            ValidationError: If the game ID is already registered
        """
        if not game_id:
            return
        
        normalized_id = game_id.strip().lower()
        
        # Check registration_data JSONB for matching game_id (case-insensitive)
        duplicates = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False,
        ).exclude(
            status__in=[Registration.CANCELLED, Registration.REJECTED]
        )
        
        if exclude_user:
            duplicates = duplicates.exclude(user=exclude_user)
        
        # Use PostgreSQL JSONB lookup for game_id field
        for reg in duplicates.only('registration_data', 'user', 'team_id'):
            existing_game_id = (reg.registration_data or {}).get('game_id', '')
            if existing_game_id and existing_game_id.strip().lower() == normalized_id:
                participant = f"team #{reg.team_id}" if reg.team_id else "another participant"
                raise ValidationError(
                    f"Game ID '{game_id}' is already registered by {participant} in this tournament. "
                    "Each player may only be registered once."
                )
            
            # Also check member game IDs in guest team data
            guest_team = (reg.registration_data or {}).get('guest_team', {})
            for member in guest_team.get('members', []):
                member_gid = (member.get('game_id', '') or '').strip().lower()
                if member_gid and member_gid == normalized_id:
                    team_name = guest_team.get('team_name', 'a guest team')
                    raise ValidationError(
                        f"Game ID '{game_id}' is already registered as a member of guest team "
                        f"'{team_name}' in this tournament."
                    )
    
    @staticmethod
    @transaction.atomic
    def promote_from_waitlist(
        tournament_id: int,
        registration_id: Optional[int] = None,
        promoted_by=None,
    ) -> Optional[Registration]:
        """
        Promote a registration from the waitlist.
        
        If registration_id is given, promotes that specific registration.
        Otherwise, promotes the next in FIFO order (lowest waitlist_position).
        
        Args:
            tournament_id: Tournament ID
            registration_id: Specific registration to promote (optional)
            promoted_by: Staff user performing the promotion
        
        Returns:
            Registration that was promoted, or None if waitlist is empty
        
        Raises:
            ValidationError: If registration cannot be promoted
        """
        tournament = Tournament.objects.select_for_update().get(id=tournament_id)
        
        # Check if there's room
        active_count = Registration.objects.filter(
            tournament=tournament,
            status__in=[Registration.PENDING, Registration.PAYMENT_SUBMITTED, Registration.CONFIRMED],
            is_deleted=False,
        ).count()
        
        if active_count >= tournament.max_participants:
            raise ValidationError(
                "Cannot promote from waitlist: tournament is still at capacity."
            )
        
        if registration_id:
            reg = Registration.objects.select_for_update().get(
                id=registration_id,
                tournament=tournament,
                status=Registration.WAITLISTED,
                is_deleted=False,
            )
        else:
            # FIFO: get the earliest waitlisted registration
            reg = Registration.objects.select_for_update().filter(
                tournament=tournament,
                status=Registration.WAITLISTED,
                is_deleted=False,
            ).order_by('waitlist_position', 'created_at').first()
        
        if not reg:
            return None
        
        # Promote
        old_position = reg.waitlist_position
        reg.status = Registration.PENDING
        reg.waitlist_position = None
        reg.save(update_fields=['status', 'waitlist_position'])
        
        # Reorder remaining waitlist positions
        remaining = Registration.objects.filter(
            tournament=tournament,
            status=Registration.WAITLISTED,
            is_deleted=False,
        ).order_by('waitlist_position', 'created_at')
        
        for idx, waitlisted_reg in enumerate(remaining, start=1):
            if waitlisted_reg.waitlist_position != idx:
                waitlisted_reg.waitlist_position = idx
                waitlisted_reg.save(update_fields=['waitlist_position'])
        
        logger.info(
            "Promoted registration %d from waitlist position %s (by %s)",
            reg.id, old_position, promoted_by,
        )
        
        return reg
    
    @staticmethod
    @transaction.atomic
    def auto_promote_waitlist(tournament_id: int) -> Optional[Registration]:
        """
        Automatically promote the next waitlisted registration when a slot opens.
        
        Called after cancellation, rejection, or disqualification creates a vacancy.
        
        Returns:
            The promoted Registration, or None if waitlist is empty or tournament full.
        """
        try:
            return RegistrationService.promote_from_waitlist(
                tournament_id=tournament_id,
            )
        except (Tournament.DoesNotExist, ValidationError):
            return None
    
    @staticmethod
    @transaction.atomic
    def submit_payment(
        registration_id: int,
        payment_method: str,
        amount: Decimal,
        transaction_id: str = '',
        payment_proof: str = ''
    ) -> Payment:
        """
        Submit payment proof for a registration.
        
        Args:
            registration_id: ID of registration to pay for
            payment_method: Payment method ('bkash', 'nagad', 'rocket', 'bank', 'deltacoin')
            amount: Payment amount
            transaction_id: Transaction reference ID (optional)
            payment_proof: Path to payment proof image (optional)
        
        Returns:
            Payment: Created payment instance
        
        Raises:
            Registration.DoesNotExist: If registration not found
            ValidationError: If payment submission fails validation
        
        Example:
            >>> payment = RegistrationService.submit_payment(
            ...     registration_id=123,
            ...     payment_method='bkash',
            ...     amount=Decimal('500.00'),
            ...     transaction_id='TXN123456',
            ...     payment_proof='payments/proof_123.jpg'
            ... )
        """
        # Get registration
        try:
            registration = Registration.objects.select_related('tournament').get(id=registration_id)
        except Registration.DoesNotExist:
            raise ValidationError(f"Registration with ID {registration_id} not found")
        
        # Validate registration status
        if registration.status not in [Registration.PENDING, Registration.PAYMENT_SUBMITTED]:
            raise ValidationError(
                f"Cannot submit payment for registration with status '{registration.get_status_display()}'"
            )
        
        # Check if payment already exists
        if hasattr(registration, 'payment'):
            raise ValidationError("Payment has already been submitted for this registration")
        
        # Validate tournament has entry fee
        if not registration.tournament.has_entry_fee:
            raise ValidationError("This tournament does not require an entry fee")
        
        # Validate amount matches tournament entry fee
        expected_amount = registration.tournament.entry_fee_amount
        if amount != expected_amount:
            raise ValidationError(
                f"Payment amount {amount} does not match entry fee {expected_amount}"
            )
        
        # Validate payment method is accepted
        if payment_method not in registration.tournament.payment_methods:
            raise ValidationError(
                f"Payment method '{payment_method}' is not accepted for this tournament. "
                f"Accepted methods: {', '.join(registration.tournament.payment_methods)}"
            )
        
        # Create payment
        payment = Payment(
            registration=registration,
            payment_method=payment_method,
            amount=amount,
            transaction_id=transaction_id,
            payment_proof=payment_proof,
            status=Payment.SUBMITTED
        )
        
        # Validate
        payment.full_clean()
        payment.save()
        
        # P4-T03: Dual-write to PaymentVerification
        from apps.tournaments.services.payment_service import _sync_to_payment_verification
        _sync_to_payment_verification(payment)
        
        # Update registration status
        registration.status = Registration.PAYMENT_SUBMITTED
        registration.save(update_fields=['status'])
        
        # TODO: Future integration points
        # - Send notification to organizer (apps.notifications)
        # - Log payment submission event
        
        return payment
    
    @staticmethod
    @transaction.atomic
    def pay_with_deltacoin(
        registration_id: int,
        user
    ) -> tuple[Payment, 'DeltaCrownTransaction']:
        """
        Pay tournament entry fee using DeltaCoin wallet balance.
        
        This method handles instant payment verification for DeltaCoin transactions:
        1. Validates user has sufficient balance
        2. Debits wallet with tournament entry fee
        3. Creates verified payment record
        4. Auto-confirms registration
        
        Args:
            registration_id: ID of registration to pay for
            user: User making the payment (must own the registration)
        
        Returns:
            tuple: (Payment instance, DeltaCrownTransaction instance)
        
        Raises:
            Registration.DoesNotExist: If registration not found
            ValidationError: If payment validation fails
            InsufficientFunds: If user doesn't have enough DeltaCoin
        
        Example:
            >>> from apps.tournaments.services import RegistrationService
            >>> payment, transaction = RegistrationService.pay_with_deltacoin(
            ...     registration_id=123,
            ...     user=request.user
            ... )
            >>> # Registration is now CONFIRMED, no manual verification needed
        """
        from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
        from apps.economy.exceptions import InsufficientFunds
        
        # Get registration
        try:
            registration = Registration.objects.select_related('tournament').get(id=registration_id)
        except Registration.DoesNotExist:
            raise ValidationError(f"Registration with ID {registration_id} not found")
        
        # Validate registration belongs to user (solo) or user is team captain (team)
        if registration.user_id is not None:
            # Solo registration - user must own it
            if registration.user_id != user.id:
                raise ValidationError("You can only pay for your own registrations")
        else:
            # Team registration - user must be team captain
            from apps.organizations.models import Team
            try:
                team = Team.objects.get(id=registration.team_id)
                if team.captain.user_id != user.id:
                    raise ValidationError("Only the team captain can pay for team registrations")
            except Team.DoesNotExist:
                raise ValidationError("Team not found for this registration")
        
        # Validate registration status
        if registration.status not in [Registration.PENDING, Registration.PAYMENT_SUBMITTED]:
            raise ValidationError(
                f"Cannot pay for registration with status '{registration.get_status_display()}'"
            )
        
        # Check if payment already exists and is verified
        if hasattr(registration, 'payment') and registration.payment.status == Payment.VERIFIED:
            raise ValidationError("Payment has already been verified for this registration")
        
        # Validate tournament requires entry fee
        if not registration.tournament.has_entry_fee:
            raise ValidationError("This tournament does not require an entry fee")
        
        # Validate DeltaCoin is accepted payment method
        if 'deltacoin' not in registration.tournament.payment_methods:
            raise ValidationError(
                "DeltaCoin payments are not accepted for this tournament"
            )
        
        # Get entry fee amount
        entry_fee = registration.tournament.entry_fee_amount
        if entry_fee <= 0:
            raise ValidationError("Invalid entry fee amount")
        
        # Convert to integer (DeltaCoin uses integer amounts)
        entry_fee_dc = int(entry_fee)
        
        # Get or create user's wallet
        try:
            wallet = DeltaCrownWallet.objects.select_for_update().get(profile=user.profile)
        except DeltaCrownWallet.DoesNotExist:
            # Auto-create wallet if doesn't exist
            wallet = DeltaCrownWallet.objects.create(profile=user.profile, cached_balance=0)
        
        # Check sufficient balance
        if wallet.cached_balance < entry_fee_dc:
            raise InsufficientFunds(
                f"Insufficient DeltaCoin balance. Required: {entry_fee_dc} DC, "
                f"Available: {wallet.cached_balance} DC"
            )
        
        # Create debit transaction
        idempotency_key = f"tournament_entry_{registration.tournament_id}_reg_{registration_id}"
        
        try:
            dc_transaction = DeltaCrownTransaction.objects.create(
                wallet=wallet,
                amount=-entry_fee_dc,  # Negative for debit
                reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT,
                tournament_id=registration.tournament_id,
                registration_id=registration_id,
                note=f"Tournament entry fee: {registration.tournament.name}",
                created_by=user,
                idempotency_key=idempotency_key
            )
        except Exception as e:
            # Handle duplicate transaction (idempotency)
            if 'unique constraint' in str(e).lower() or 'duplicate key' in str(e).lower():
                # Transaction already exists - fetch and return existing payment
                existing_tx = DeltaCrownTransaction.objects.get(idempotency_key=idempotency_key)
                existing_payment = registration.payment
                return existing_payment, existing_tx
            raise
        
        # Update wallet balance
        wallet.cached_balance -= entry_fee_dc
        wallet.save(update_fields=['cached_balance', 'updated_at'])
        
        # Create or update payment record (auto-verified for DeltaCoin)
        if hasattr(registration, 'payment'):
            payment = registration.payment
            payment.payment_method = 'deltacoin'
            payment.amount = entry_fee
            payment.transaction_id = f"DC-{dc_transaction.id}"
            payment.status = Payment.VERIFIED
            payment.verified_by = user
            payment.verified_at = timezone.now()
            payment.admin_notes = "Auto-verified DeltaCoin payment"
            payment.save()
        else:
            payment = Payment.objects.create(
                registration=registration,
                payment_method='deltacoin',
                amount=entry_fee,
                transaction_id=f"DC-{dc_transaction.id}",
                status=Payment.VERIFIED,
                verified_by=user,
                verified_at=timezone.now(),
                admin_notes="Auto-verified DeltaCoin payment"
            )
        
        # Auto-confirm registration
        registration.status = Registration.CONFIRMED
        registration.save(update_fields=['status', 'updated_at'])
        
        # Send confirmation notification
        from apps.tournaments.services.notification_service import TournamentNotificationService
        try:
            TournamentNotificationService.notify_registration_confirmed(registration)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send registration confirmation: {e}")
        
        return payment, dc_transaction
    
    @staticmethod
    @transaction.atomic
    def submit_payment_proof(
        registration_id: int,
        payment_proof_file,
        reference_number: str = '',
        notes: str = ''
    ) -> Payment:
        """
        Submit payment proof file for a registration (Module 3.2: Payment Processing).
        
        This method handles file upload for manual payment verification (bKash, Nagad, etc.).
        Replaces any existing pending proof submission.
        
        Args:
            registration_id: ID of registration to submit proof for
            payment_proof_file: Uploaded file (Django UploadedFile object)
            reference_number: Payment reference number from receipt (optional)
            notes: Additional notes about the payment (optional)
        
        Returns:
            Payment: Updated payment instance with proof file
        
        Raises:
            Registration.DoesNotExist: If registration not found
            ValidationError: If proof submission fails validation
        
        File Validation:
            - Size: Maximum 5MB
            - Types: JPG, PNG, PDF only
            - Automatically determines file_type based on extension
        
        Example:
            >>> from django.core.files.uploadedfile import SimpleUploadedFile
            >>> proof_file = request.FILES['payment_proof']
            >>> payment = RegistrationService.submit_payment_proof(
            ...     registration_id=123,
            ...     payment_proof_file=proof_file,
            ...     reference_number='BKH123456789',
            ...     notes='Paid via bKash on 2025-11-08'
            ... )
        """
        # Get registration with payment
        try:
            registration = Registration.objects.select_related(
                'tournament', 'payment'
            ).get(id=registration_id)
        except Registration.DoesNotExist:
            raise ValidationError(f"Registration with ID {registration_id} not found")
        
        # Check if payment exists
        if not hasattr(registration, 'payment'):
            raise ValidationError(
                "No payment record found for this registration. "
                "Please submit payment details first using submit_payment()."
            )
        
        payment = registration.payment
        
        # Validate payment status - can only submit proof for pending/submitted payments
        if payment.status not in [Payment.PENDING, Payment.SUBMITTED, Payment.REJECTED]:
            raise ValidationError(
                f"Cannot submit proof for payment with status '{payment.get_status_display()}'. "
                f"Payment proof can only be submitted for pending, submitted, or rejected payments."
            )
        
        # Delete existing proof file if replacing (for resubmission after rejection)
        if payment.payment_proof:
            try:
                payment.payment_proof.delete(save=False)
            except Exception:
                pass  # Ignore errors if file doesn't exist
        
        # Assign new file
        payment.payment_proof = payment_proof_file
        payment.reference_number = reference_number
        payment.admin_notes = notes if notes else payment.admin_notes
        payment.status = Payment.SUBMITTED
        
        # Validate (this will trigger file size/type validation in model's clean())
        payment.full_clean()
        payment.save()
        
        # Update registration status
        if registration.status != Registration.PAYMENT_SUBMITTED:
            registration.status = Registration.PAYMENT_SUBMITTED
            registration.save(update_fields=['status'])
        
        # Send payment pending notification
        from apps.tournaments.services.notification_service import TournamentNotificationService
        try:
            TournamentNotificationService.notify_payment_pending(registration)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send payment pending notification: {e}")
        
        # Emit payment.submitted event (P4-T06)
        _reg_id = registration.id
        _tourney_id = registration.tournament_id
        _pay_id = payment.id
        def _emit_payment_submitted():
            _publish_registration_event(
                "payment.submitted",
                registration_id=_reg_id,
                tournament_id=_tourney_id,
                payment_id=_pay_id,
                source="registration_service",
            )
        transaction.on_commit(_emit_payment_submitted)
        
        return payment
    
    @staticmethod
    @transaction.atomic
    def verify_payment(
        payment_id: int,
        verified_by,
        admin_notes: str = ''
    ) -> Payment:
        """
        Verify a payment (admin/organizer action).
        
        Module 2.4: Security Hardening - Audit logging added
        
        Args:
            payment_id: ID of payment to verify
            verified_by: User verifying the payment (admin/organizer)
            admin_notes: Optional notes about verification
        
        Returns:
            Payment: Verified payment instance
        
        Raises:
            Payment.DoesNotExist: If payment not found
            ValidationError: If payment cannot be verified
        
        Example:
            >>> payment = RegistrationService.verify_payment(
            ...     payment_id=456,
            ...     verified_by=request.user,
            ...     admin_notes='Payment verified - bKash transaction confirmed'
            ... )
        """
        # Get payment
        try:
            payment = Payment.objects.select_related('registration').get(id=payment_id)
        except Payment.DoesNotExist:
            raise ValidationError(f"Payment with ID {payment_id} not found")
        
        # Use model method to verify
        payment.verify(verified_by=verified_by, admin_notes=admin_notes)
        
        # Update registration status to CONFIRMED
        registration = payment.registration
        registration.status = Registration.CONFIRMED
        registration.save(update_fields=['status'])
        
        # User Profile Integration Hook - Payment Verified
        def _notify_profile():
            try:
                on_payment_status_change(
                    user_id=registration.user_id,
                    tournament_id=registration.tournament_id,
                    transaction_id=payment.transaction_id or str(payment.id),
                    registration_id=registration.id,
                    status='verified',
                    actor_user_id=verified_by.id,
                    amount=payment.amount,
                    reason=admin_notes,
                )
            except Exception:
                pass  # Non-blocking
        transaction.on_commit(_notify_profile)
        
        # =====================================================================
        # MODULE 2.4: Audit Logging
        # =====================================================================
        from apps.tournaments.security.audit import audit_event, AuditAction
        
        audit_event(
            user=verified_by,
            action=AuditAction.PAYMENT_VERIFY,
            meta={
                'payment_id': payment_id,
                'tournament_id': registration.tournament_id,
                'registration_id': registration.id,
                'user_id': registration.user_id if registration.user_id else None,
                'team_id': registration.team_id if registration.team_id else None,
                'amount': str(payment.amount) if payment.amount else '0',
                'payment_method': payment.payment_method,
                'admin_notes': admin_notes,
            }
        )
        
        # Send confirmation notification
        from apps.tournaments.services.notification_service import TournamentNotificationService
        try:
            TournamentNotificationService.notify_registration_confirmed(registration)
        except Exception as e:
            logger.error(f"Failed to send registration confirmation: {e}")
        
        # Publish events: registration.confirmed + payment.verified
        def _emit_confirmed():
            _publish_registration_event(
                "registration.confirmed",
                registration_id=registration.id,
                tournament_id=registration.tournament_id,
                team_id=registration.team_id,
                user_id=registration.user_id,
                source="registration_service",
            )
            _publish_registration_event(
                "payment.verified",
                payment_id=payment.id,
                registration_id=registration.id,
                amount=float(payment.amount) if payment.amount else 0.0,
                source="registration_service",
            )
        transaction.on_commit(_emit_confirmed)
        
        return payment
    
    @staticmethod
    @transaction.atomic
    def reject_payment(
        payment_id: int,
        rejected_by,
        reason: str
    ) -> Payment:
        """
        Reject a payment (admin/organizer action).
        
        Module 2.4: Security Hardening - Audit logging added
        
        Args:
            payment_id: ID of payment to reject
            rejected_by: User rejecting the payment (admin/organizer)
            reason: Reason for rejection
        
        Returns:
            Payment: Rejected payment instance
        
        Raises:
            Payment.DoesNotExist: If payment not found
            ValidationError: If payment cannot be rejected
        
        Example:
            >>> payment = RegistrationService.reject_payment(
            ...     payment_id=456,
            ...     rejected_by=request.user,
            ...     reason='Invalid transaction ID - please resubmit with correct details'
            ... )
        """
        # Get payment
        try:
            payment = Payment.objects.select_related('registration').get(id=payment_id)
        except Payment.DoesNotExist:
            raise ValidationError(f"Payment with ID {payment_id} not found")
        
        # Use model method to reject
        payment.reject(rejected_by=rejected_by, reason=reason)
        
        # Update registration status back to PENDING
        registration = payment.registration
        registration.status = Registration.PENDING
        registration.save(update_fields=['status'])
        
        # UP-INTEGRATION-01: Notify user profile of payment rejection
        def _notify_profile():
            try:
                on_payment_status_change(
                    user_id=registration.user_id if registration.user_id else None,
                    team_id=registration.team_id if registration.team_id else None,
                    tournament_id=registration.tournament_id,
                    payment_id=payment_id,
                    new_status='rejected',
                    amount=payment.amount if hasattr(payment, 'amount') else None
                )
            except Exception:
                pass  # Non-blocking
        transaction.on_commit(_notify_profile)
        
        # =====================================================================
        # MODULE 2.4: Audit Logging
        # =====================================================================
        from apps.tournaments.security.audit import audit_event, AuditAction
        
        audit_event(
            user=rejected_by,
            action=AuditAction.PAYMENT_REJECT,
            meta={
                'payment_id': payment_id,
                'tournament_id': registration.tournament_id,
                'registration_id': registration.id,
                'user_id': registration.user_id if registration.user_id else None,
                'team_id': registration.team_id if registration.team_id else None,
                'reason': reason,
            }
        )
        
        # TODO: Future integration points
        # - Send rejection notification to participant (apps.notifications)
        # - Explain how to resubmit payment
        
        # Emit payment.rejected event (P4-T06)
        _reg_id = registration.id
        _tourney_id = registration.tournament_id
        _pay_id = payment_id
        _reason = reason
        def _emit_payment_rejected():
            _publish_registration_event(
                "payment.rejected",
                registration_id=_reg_id,
                tournament_id=_tourney_id,
                payment_id=_pay_id,
                reason=_reason,
                source="registration_service",
            )
        transaction.on_commit(_emit_payment_rejected)
        
        return payment
    
    @staticmethod
    @transaction.atomic
    def cancel_registration(
        registration_id: int,
        user,
        reason: str = ''
    ) -> Registration:
        """
        Cancel a registration with soft delete and optional refund.
        
        Args:
            registration_id: ID of registration to cancel
            user: User canceling the registration
            reason: Reason for cancellation (optional)
        
        Returns:
            Registration: Cancelled registration instance
        
        Raises:
            Registration.DoesNotExist: If registration not found
            ValidationError: If registration cannot be cancelled
        
        Example:
            >>> registration = RegistrationService.cancel_registration(
            ...     registration_id=123,
            ...     user=request.user,
            ...     reason='Schedule conflict - unable to participate'
            ... )
        """
        # Get registration
        try:
            registration = Registration.objects.select_related('tournament').get(id=registration_id)
        except Registration.DoesNotExist:
            raise ValidationError(f"Registration with ID {registration_id} not found")
        
        # Validate can be cancelled
        if registration.status in [Registration.CANCELLED, Registration.NO_SHOW]:
            raise ValidationError(
                f"Registration is already cancelled or marked as no-show"
            )
        
        # Check if tournament has started
        if registration.tournament.status in [Tournament.LIVE, Tournament.COMPLETED]:
            raise ValidationError(
                "Cannot cancel registration after tournament has started"
            )
        
        # Update status to cancelled
        registration.status = Registration.CANCELLED
        registration.save(update_fields=['status'])
        
        # Soft delete
        registration.soft_delete(user=user)
        
        # Process refund if payment was verified
        if hasattr(registration, 'payment') and registration.payment.is_verified:
            RegistrationService.refund_payment(
                payment_id=registration.payment.id,
                refunded_by=user,
                reason=reason or 'Registration cancelled'
            )
        
        # Publish registration.cancelled event + UserProfile tracking
        def _emit_cancelled():
            try:
                on_registration_status_change(
                    user_id=registration.user_id,
                    tournament_id=registration.tournament_id,
                    registration_id=registration.id,
                    status='cancelled',
                    actor_user_id=user.id if user else None,
                )
            except Exception:
                pass  # Non-blocking
            _publish_registration_event(
                "registration.cancelled",
                registration_id=registration.id,
                tournament_id=registration.tournament_id,
                team_id=registration.team_id,
                user_id=registration.user_id,
                source="registration_service",
            )
        transaction.on_commit(_emit_cancelled)
        
        return registration
    
    @staticmethod
    @transaction.atomic
    def approve_registration(registration: Registration, approved_by) -> Registration:
        """
        Approve a pending registration (organizer action).
        
        Args:
            registration: Registration instance to approve
            approved_by: User performing the approval (organizer/admin)
        
        Returns:
            Registration: Approved registration instance
        
        Raises:
            ValidationError: If registration cannot be approved
        
        Example:
            >>> registration = get_object_or_404(Registration, id=reg_id)
            >>> RegistrationService.approve_registration(registration, request.user)
        """
        # Move exact logic from organizer.py::approve_registration view
        registration.status = 'confirmed'
        registration.save()
        
        # User Profile Integration Hook
        def _notify_profile():
            try:
                on_registration_status_change(
                    user_id=registration.user_id,
                    tournament_id=registration.tournament_id,
                    registration_id=registration.id,
                    status='approved',
                    actor_user_id=approved_by.id if approved_by else None,
                )
            except Exception:
                pass  # Non-blocking
            # Publish registration.confirmed event
            _publish_registration_event(
                "registration.confirmed",
                registration_id=registration.id,
                tournament_id=registration.tournament_id,
                team_id=registration.team_id,
                user_id=registration.user_id,
                source="registration_service",
            )
        transaction.on_commit(_notify_profile)
        
        return registration
    
    @staticmethod
    @transaction.atomic
    def reject_registration(registration: Registration, rejected_by) -> Registration:
        """
        Reject a pending registration (organizer action).
        
        Args:
            registration: Registration instance to reject
            rejected_by: User performing the rejection (organizer/admin)
        
        Returns:
            Registration: Rejected registration instance
        
        Raises:
            ValidationError: If registration cannot be rejected
        
        Example:
            >>> registration = get_object_or_404(Registration, id=reg_id)
            >>> RegistrationService.reject_registration(registration, request.user)
        """
        # Move exact logic from organizer.py::reject_registration view
        registration.status = 'rejected'
        registration.save()
        
        # User Profile Integration Hook + event emission (P4-T06)
        def _notify_profile_reject():
            try:
                on_registration_status_change(
                    user_id=registration.user_id,
                    tournament_id=registration.tournament_id,
                    registration_id=registration.id,
                    status='rejected',
                    actor_user_id=rejected_by.id if rejected_by else None,
                )
            except Exception:
                pass  # Non-blocking
            _publish_registration_event(
                "registration.rejected",
                registration_id=registration.id,
                tournament_id=registration.tournament_id,
                team_id=registration.team_id,
                user_id=registration.user_id,
                source="registration_service",
            )
        transaction.on_commit(_notify_profile_reject)
        
        return registration
    
    @staticmethod
    @transaction.atomic
    def bulk_approve_registrations(
        registration_ids: list,
        tournament: Tournament,
        approved_by
    ) -> dict:
        """
        Bulk approve multiple pending registrations (organizer action).
        
        Args:
            registration_ids: List of registration IDs to approve
            tournament: Tournament instance (for permission check)
            approved_by: User performing the approval (organizer/admin)
        
        Returns:
            dict: {'success': True, 'count': number_updated}
        
        Raises:
            ValidationError: If no registrations selected or validation fails
        
        Example:
            >>> result = RegistrationService.bulk_approve_registrations(
            ...     registration_ids=[1, 2, 3],
            ...     tournament=tournament,
            ...     approved_by=request.user
            ... )
            >>> print(result['count'])  # Number of registrations approved
        """
        # Move exact logic from organizer.py::bulk_approve_registrations view
        if not registration_ids:
            raise ValidationError('No registrations selected')
        
        updated = Registration.objects.filter(
            id__in=registration_ids,
            tournament=tournament,
            status=Registration.PENDING
        ).update(status=Registration.CONFIRMED)
        
        return {'success': True, 'count': updated}
    
    @staticmethod
    @transaction.atomic
    def bulk_reject_registrations(
        registration_ids: list,
        tournament: Tournament,
        rejected_by,
        reason: str = ''
    ) -> dict:
        """
        Bulk reject multiple pending registrations (organizer action).
        
        Args:
            registration_ids: List of registration IDs to reject
            tournament: Tournament instance (for permission check)
            rejected_by: User performing the rejection (organizer/admin)
            reason: Optional rejection reason to store in registration_data
        
        Returns:
            dict: {'success': True, 'count': number_updated}
        
        Raises:
            ValidationError: If no registrations selected or validation fails
        
        Example:
            >>> result = RegistrationService.bulk_reject_registrations(
            ...     registration_ids=[1, 2, 3],
            ...     tournament=tournament,
            ...     rejected_by=request.user,
            ...     reason='Invalid game IDs'
            ... )
            >>> print(result['count'])  # Number of registrations rejected
        """
        # Move exact logic from organizer.py::bulk_reject_registrations view
        if not registration_ids:
            raise ValidationError('No registrations selected')
        
        registrations = Registration.objects.filter(
            id__in=registration_ids,
            tournament=tournament,
            status=Registration.PENDING
        )
        
        updated = 0
        for reg in registrations:
            reg.status = Registration.REJECTED
            if reason:
                # Store rejection reason in registration_data JSONB
                reg.registration_data = reg.registration_data or {}
                reg.registration_data['rejection_reason'] = reason
            reg.save()
            updated += 1
        
        return {'success': True, 'count': updated}
    
    @staticmethod
    @transaction.atomic
    def refund_payment(
        payment_id: int,
        refunded_by,
        reason: str = ''
    ) -> Payment:
        """
        Process a refund for a payment.
        
        Module 2.4: Security Hardening - Audit logging added
        
        Args:
            payment_id: ID of payment to refund
            refunded_by: User processing the refund (admin/organizer)
            reason: Reason for refund
        
        Returns:
            Payment: Refunded payment instance
        
        Raises:
            Payment.DoesNotExist: If payment not found
            ValidationError: If payment cannot be refunded
        
        Example:
            >>> payment = RegistrationService.refund_payment(
            ...     payment_id=456,
            ...     refunded_by=request.user,
            ...     reason='Tournament cancelled'
            ... )
        """
        # Get payment
        try:
            payment = Payment.objects.select_related('registration').get(id=payment_id)
        except Payment.DoesNotExist:
            raise ValidationError(f"Payment with ID {payment_id} not found")
        
        # Use model method to refund
        payment.refund(refunded_by=refunded_by, reason=reason)
        
        # =====================================================================
        # MODULE 2.4: Audit Logging
        # =====================================================================
        from apps.tournaments.security.audit import audit_event, AuditAction
        
        audit_event(
            user=refunded_by,
            action=AuditAction.PAYMENT_REFUND,
            meta={
                'payment_id': payment_id,
                'tournament_id': payment.registration.tournament_id,
                'registration_id': payment.registration_id,
                'amount': str(payment.amount) if payment.amount else '0',
                'reason': reason,
            }
        )
        
        # TODO: Future integration points
        # - Process actual refund through payment gateway
        # - Refund DeltaCoin if applicable (apps.economy)
        # - Send refund notification (apps.notifications)
        
        return payment
    
    @staticmethod
    @transaction.atomic
    def waive_fee(
        registration_id: int,
        waived_by,
        reason: str
    ) -> Payment:
        """
        Waive tournament entry fee for a registration.
        
        Creates a payment record with WAIVED status. Used for:
        - Top-ranked teams/players
        - Sponsored participants
        - Special invitations
        - Organizer discretion
        
        Module 2.4: Security Hardening - Audit logging included
        
        Args:
            registration_id: ID of registration to waive fee for
            waived_by: User granting the waiver (organizer/admin)
            reason: Reason for waiving fee (required for audit trail)
        
        Returns:
            Payment: Payment instance with WAIVED status
        
        Raises:
            Registration.DoesNotExist: If registration not found
            ValidationError: If registration already has payment or invalid state
        
        Example:
            >>> payment = RegistrationService.waive_fee(
            ...     registration_id=123,
            ...     waived_by=request.user,
            ...     reason='Top-ranked team in previous season'
            ... )
        """
        # Validate inputs
        if not reason or not reason.strip():
            raise ValidationError("Fee waiver reason is required")
        
        # Get registration
        try:
            registration = Registration.objects.select_related('tournament').get(id=registration_id)
        except Registration.DoesNotExist:
            raise ValidationError(f"Registration with ID {registration_id} not found")
        
        # Check if payment already exists
        if hasattr(registration, 'payment'):
            existing_payment = registration.payment
            if existing_payment.status == Payment.WAIVED:
                raise ValidationError("Fee already waived for this registration")
            elif existing_payment.status == Payment.VERIFIED:
                raise ValidationError(
                    "Cannot waive fee - payment already verified. "
                    "Consider issuing a refund instead."
                )
            else:
                # Update existing payment to waived
                existing_payment.status = Payment.WAIVED
                existing_payment.waived = True
                existing_payment.waive_reason = reason.strip()
                existing_payment.verified_by = waived_by
                existing_payment.verified_at = timezone.now()
                existing_payment.save(update_fields=[
                    'status', 'waived', 'waive_reason', 
                    'verified_by', 'verified_at', 'updated_at'
                ])
                payment = existing_payment
        else:
            # Create new payment with waived status
            payment = Payment.objects.create(
                registration=registration,
                payment_method=Payment.DELTACOIN,  # Use generic method for waived fees
                amount=registration.tournament.entry_fee or Decimal('0.00'),
                status=Payment.WAIVED,
                waived=True,
                waive_reason=reason.strip(),
                verified_by=waived_by,
                verified_at=timezone.now()
            )
        
        # Auto-confirm registration
        registration.status = Registration.CONFIRMED
        registration.save(update_fields=['status', 'updated_at'])
        
        # =====================================================================
        # MODULE 2.4: Audit Logging
        # =====================================================================
        from apps.tournaments.security.audit import audit_event, AuditAction
        
        audit_event(
            user=waived_by,
            action=AuditAction.FEE_WAIVED,
            meta={
                'registration_id': registration_id,
                'tournament_id': registration.tournament_id,
                'tournament_name': registration.tournament.name,
                'participant': registration.participant_identifier,
                'amount': str(payment.amount),
                'reason': reason.strip(),
            }
        )
        
        # Send fee waiver confirmation notification
        from apps.tournaments.services.notification_service import TournamentNotificationService
        try:
            TournamentNotificationService.notify_registration_confirmed(registration)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send fee waiver confirmation: {e}")
        
        # TODO: Future integration points
        # - Update tournament revenue analytics
        
        return payment
    
    @staticmethod
    def check_auto_waive_eligibility(registration_id: int) -> tuple[bool, str]:
        """
        Check if a registration is eligible for automatic fee waiver.
        
        Checks for:
        - Sponsored teams (from apps.teams if team_id present)
        - Top-ranked participants (from apps.leaderboards)
        - Special tournament settings (free_entry, sponsor_waives_fee)
        
        Args:
            registration_id: Registration to check
        
        Returns:
            tuple: (is_eligible, reason) where reason explains eligibility
        
        Example:
            >>> eligible, reason = RegistrationService.check_auto_waive_eligibility(123)
            >>> if eligible:
            ...     RegistrationService.waive_fee(123, system_user, reason)
        """
        try:
            registration = Registration.objects.select_related('tournament').get(id=registration_id)
        except Registration.DoesNotExist:
            return (False, "Registration not found")
        
        tournament = registration.tournament
        
        # Check tournament-level settings
        if getattr(tournament, 'free_entry', False):
            return (True, "Tournament has free entry enabled")
        
        # Check if team is sponsored (requires apps.teams integration)
        if registration.team_id:
            # TODO: Check team sponsorship status
            # from apps.organizations.models import Team
            # team = Team.objects.get(id=registration.team_id)
            # if team.is_sponsored or team.sponsor_covers_fees:
            #     return (True, f"Team sponsored by {team.sponsor_name}")
            pass
        
        # Check top-ranked status (requires apps.leaderboards integration)
        if registration.user:
            # TODO: Check user ranking
            # from apps.leaderboards.services import LeaderboardService
            # rank = LeaderboardService.get_user_rank(registration.user, tournament.game)
            # if rank and rank <= 10:  # Top 10 players get free entry
            #     return (True, f"Top-ranked player (Rank #{rank})")
            pass
        
        return (False, "No auto-waive criteria met")
    
    @staticmethod
    @transaction.atomic
    def add_to_waitlist(
        registration_id: int
    ) -> Registration:
        """
        Add a registration to the waitlist when tournament is at capacity.
        
        This method is called during registration when:
        - Tournament has reached max_participants capacity
        - All confirmed slots are filled
        
        Args:
            registration_id: ID of registration to add to waitlist
        
        Returns:
            Registration: Waitlisted registration with assigned position
        
        Example:
            >>> registration = RegistrationService.add_to_waitlist(registration_id=123)
            >>> print(f"Added to waitlist at position {registration.waitlist_position}")
        """
        # Get registration
        try:
            registration = Registration.objects.select_related('tournament').get(id=registration_id)
        except Registration.DoesNotExist:
            raise ValidationError(f"Registration with ID {registration_id} not found")
        
        # Get next waitlist position
        max_position = Registration.objects.filter(
            tournament=registration.tournament,
            status=Registration.WAITLISTED,
            is_deleted=False
        ).aggregate(max_pos=models.Max('waitlist_position'))['max_pos']
        
        next_position = (max_position or 0) + 1
        
        # Update registration
        registration.status = Registration.WAITLISTED
        registration.waitlist_position = next_position
        registration.save(update_fields=['status', 'waitlist_position', 'updated_at'])
        
        # Send waitlist notification
        try:
            from apps.tournaments.services.notification_service import TournamentNotificationService
            TournamentNotificationService.notify_added_to_waitlist(registration)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to send waitlist notification: {e}")
        
        return registration
    
    @staticmethod
    def check_and_promote_waitlist(tournament_id: int):
        """
        Check if waitlist promotion is needed and trigger it.
        
        This is a helper method that should be called after:
        - Registration cancellation
        - Payment rejection resulting in cancelled registration
        - Tournament capacity increase
        
        Args:
            tournament_id: ID of tournament to check
        
        Returns:
            int: Number of participants promoted from waitlist
        """
        promoted = RegistrationService.promote_from_waitlist(tournament_id=tournament_id)
        return len(promoted)
    
    @staticmethod
    @transaction.atomic
    def assign_slot(
        registration_id: int,
        slot_number: int,
        assigned_by
    ) -> Registration:
        """
        Assign a bracket slot to a registration.
        
        Args:
            registration_id: ID of registration to assign slot to
            slot_number: Slot number in the bracket
            assigned_by: User assigning the slot (admin/organizer)
        
        Returns:
            Registration: Registration with assigned slot
        
        Raises:
            Registration.DoesNotExist: If registration not found
            ValidationError: If slot assignment fails
        
        Example:
            >>> registration = RegistrationService.assign_slot(
            ...     registration_id=123,
            ...     slot_number=1,
            ...     assigned_by=request.user
            ... )
        """
        # Get registration
        try:
            registration = Registration.objects.select_related('tournament').get(id=registration_id)
        except Registration.DoesNotExist:
            raise ValidationError(f"Registration with ID {registration_id} not found")
        
        # Validate registration is confirmed
        if registration.status != Registration.CONFIRMED:
            raise ValidationError(
                "Only confirmed registrations can be assigned slots"
            )
        
        # Check if slot is already taken
        slot_taken = Registration.objects.filter(
            tournament=registration.tournament,
            slot_number=slot_number,
            is_deleted=False
        ).exclude(id=registration.id).exists()
        
        if slot_taken:
            raise ValidationError(f"Slot {slot_number} is already assigned")
        
        # Assign slot using model method
        registration.assign_slot(slot_number)
        
        # TODO: Future integration points
        # - Update bracket generation if applicable
        # - Send slot assignment notification
        
        return registration
    
    @staticmethod
    @transaction.atomic
    def assign_seed(
        registration_id: int,
        seed: int,
        assigned_by
    ) -> Registration:
        """
        Assign a seeding number to a registration.
        
        Args:
            registration_id: ID of registration to assign seed to
            seed: Seeding number (1 = highest seed)
            assigned_by: User assigning the seed (admin/organizer)
        
        Returns:
            Registration: Registration with assigned seed
        
        Raises:
            Registration.DoesNotExist: If registration not found
            ValidationError: If seed assignment fails
        
        Example:
            >>> registration = RegistrationService.assign_seed(
            ...     registration_id=123,
            ...     seed=1,
            ...     assigned_by=request.user
            ... )
        """
        # Get registration
        try:
            registration = Registration.objects.get(id=registration_id)
        except Registration.DoesNotExist:
            raise ValidationError(f"Registration with ID {registration_id} not found")
        
        # Validate registration is confirmed
        if registration.status != Registration.CONFIRMED:
            raise ValidationError(
                "Only confirmed registrations can be assigned seeds"
            )
        
        # Assign seed using model method
        registration.assign_seed(seed)
        
        # TODO: Future integration points
        # - Apply dynamic seeding based on team rankings (apps.teams)
        # - Update bracket seeding
        
        return registration
    
    @staticmethod
    def get_registration_stats(tournament_id: int) -> Dict[str, Any]:
        """
        Get registration statistics for a tournament.
        
        Args:
            tournament_id: ID of tournament
        
        Returns:
            Dict containing registration statistics:
                - total_registrations: Total number of active registrations
                - pending: Registrations pending payment
                - payment_submitted: Registrations with payment submitted
                - confirmed: Confirmed registrations
                - cancelled: Cancelled registrations
                - capacity_percentage: Percentage of capacity filled
        
        Example:
            >>> stats = RegistrationService.get_registration_stats(tournament_id=42)
            >>> print(f"Capacity: {stats['capacity_percentage']}%")
        """
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament with ID {tournament_id} not found")
        
        # Get registration counts by status
        registrations = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False
        )
        
        stats = {
            'total_registrations': registrations.count(),
            'pending': registrations.filter(status=Registration.PENDING).count(),
            'payment_submitted': registrations.filter(status=Registration.PAYMENT_SUBMITTED).count(),
            'confirmed': registrations.filter(status=Registration.CONFIRMED).count(),
            'cancelled': registrations.filter(status=Registration.CANCELLED).count(),
            'rejected': registrations.filter(status=Registration.REJECTED).count(),
            'no_show': registrations.filter(status=Registration.NO_SHOW).count(),
        }
        
        # Calculate capacity percentage
        active_registrations = stats['pending'] + stats['payment_submitted'] + stats['confirmed']
        stats['capacity_percentage'] = round(
            (active_registrations / tournament.max_participants) * 100, 2
        )
        
        return stats
    
    @staticmethod
    def can_withdraw(registration: Registration) -> tuple[bool, str]:
        """
        Check if a registration can be withdrawn.
        
        Returns:
            (can_withdraw, reason)
        """
        tournament = registration.tournament
        
        # Check if tournament has started
        if tournament.tournament_start and timezone.now() >= tournament.tournament_start:
            return False, "Cannot withdraw after tournament has started"
        
        # Check withdrawal deadline (24 hours before tournament start)
        if tournament.tournament_start:
            withdrawal_deadline = tournament.tournament_start - timezone.timedelta(hours=24)
            if timezone.now() >= withdrawal_deadline:
                return False, "Withdrawal deadline has passed (24 hours before tournament)"
        
        # Check if already cancelled
        if registration.status in [Registration.CANCELLED, Registration.REJECTED]:
            return False, "Registration is already cancelled or rejected"
        
        # Check if checked in
        if hasattr(registration, 'checkin') and registration.checkin and registration.checkin.checked_in_at:
            return False, "Cannot withdraw after checking in"
        
        return True, "Withdrawal allowed"
    
    @staticmethod
    @transaction.atomic
    def withdraw_registration(registration: Registration, reason: str = "") -> dict:
        """
        Withdraw a registration and handle cleanup.
        
        Returns:
            {
                'success': bool,
                'message': str,
                'refund_eligible': bool,
                'refund_amount': Decimal,
                'roster_unlocked': bool
            }
        """
        can_withdraw, withdrawal_reason = RegistrationService.can_withdraw(registration)
        
        if not can_withdraw:
            raise ValidationError(withdrawal_reason)
        
        tournament = registration.tournament
        refund_info = {
            'refund_eligible': False,
            'refund_amount': Decimal('0.00'),
            'refund_percentage': 0
        }
        
        # Calculate refund eligibility
        if tournament.has_entry_fee and registration.status == Registration.CONFIRMED:
            time_until_start = tournament.tournament_start - timezone.now()
            hours_until = time_until_start.total_seconds() / 3600
            
            # Refund policy: 
            # - 100% if >7 days before
            # - 50% if 3-7 days before
            # - 25% if 1-3 days before
            # - 0% if <24 hours
            if hours_until > 168:  # 7 days
                refund_info['refund_eligible'] = True
                refund_info['refund_amount'] = tournament.entry_fee_amount
                refund_info['refund_percentage'] = 100
            elif hours_until > 72:  # 3 days
                refund_info['refund_eligible'] = True
                refund_info['refund_amount'] = tournament.entry_fee_amount * Decimal('0.50')
                refund_info['refund_percentage'] = 50
            elif hours_until > 24:  # 1 day
                refund_info['refund_eligible'] = True
                refund_info['refund_amount'] = tournament.entry_fee_amount * Decimal('0.25')
                refund_info['refund_percentage'] = 25
        
        # Update registration status
        old_status = registration.status
        registration.status = Registration.CANCELLED
        
        # Add cancellation tracking fields if they don't exist
        if not hasattr(registration, 'cancelled_at'):
            registration.registration_data['cancelled_at'] = timezone.now().isoformat()
            registration.registration_data['cancellation_reason'] = reason or "User withdrawal"
            registration.registration_data['refund_info'] = refund_info
        
        registration.save()
        
        # Unlock roster members if team tournament
        roster_unlocked = False
        if registration.team_id and registration.registration_data.get('roster'):
            from apps.organizations.models import TeamMembership
            roster = registration.registration_data.get('roster', [])
            for player in roster:
                try:
                    membership = TeamMembership.objects.get(id=player.get('member_id'))
                    if membership.locked_for_tournament_id == tournament.id:
                        membership.unlock_from_tournament()
                        roster_unlocked = True
                except TeamMembership.DoesNotExist:
                    pass
        
        # Promote from waitlist if space available
        RegistrationService._promote_from_waitlist(tournament)
        
        # Publish registration.withdrawn event
        _reg_id = registration.id
        _tourney_id = tournament.id
        _team_id = registration.team_id
        _user_id = registration.user_id
        def _emit_withdrawn():
            _publish_registration_event(
                "registration.withdrawn",
                registration_id=_reg_id,
                tournament_id=_tourney_id,
                team_id=_team_id,
                user_id=_user_id,
                source="registration_service",
            )
        transaction.on_commit(_emit_withdrawn)
        
        return {
            'success': True,
            'message': 'Registration withdrawn successfully',
            'refund_eligible': refund_info['refund_eligible'],
            'refund_amount': refund_info['refund_amount'],
            'refund_percentage': refund_info.get('refund_percentage', 0),
            'roster_unlocked': roster_unlocked,
            'previous_status': old_status
        }
    
    @staticmethod
    def _promote_from_waitlist(tournament: Tournament):
        """Promote next waitlisted registration if space available"""
        # Count active registrations
        active_count = Registration.objects.filter(
            tournament=tournament,
            status__in=[Registration.PENDING, Registration.PAYMENT_SUBMITTED, Registration.CONFIRMED],
            is_deleted=False
        ).count()
        
        # Check if space available
        if active_count < tournament.max_participants:
            # Get next waitlisted registration
            next_waitlist = Registration.objects.filter(
                tournament=tournament,
                status=Registration.WAITLISTED,
                is_deleted=False
            ).order_by('registered_at').first()
            
            if next_waitlist:
                next_waitlist.status = Registration.PENDING
                if not hasattr(next_waitlist, 'promoted_from_waitlist_at'):
                    next_waitlist.registration_data['promoted_from_waitlist_at'] = timezone.now().isoformat()
                next_waitlist.save()
                
                # TODO: Send email notification about promotion
                # from apps.notifications.services import send_waitlist_promotion_email
                # send_waitlist_promotion_email(next_waitlist)
    
    @staticmethod
    @transaction.atomic
    def disqualify_registration(registration: Registration, reason: str, disqualified_by) -> dict:
        """
        Disqualify a registration (organizer action).
        
        This is different from withdrawal - no refund, locks remain until tournament ends.
        """
        if registration.status == Registration.CANCELLED:
            raise ValidationError("Registration is already cancelled")
        
        # Update status
        old_status = registration.status
        registration.status = Registration.REJECTED
        
        # Add disqualification tracking
        registration.registration_data['disqualified_at'] = timezone.now().isoformat()
        registration.registration_data['disqualified_by'] = disqualified_by.username if hasattr(disqualified_by, 'username') else str(disqualified_by)
        registration.registration_data['disqualification_reason'] = reason
        registration.save()
        
        # Keep roster locked (they're still disqualified from this tournament)
        # Unlock will happen after tournament ends
        
        # TODO: Send disqualification email
        # from apps.notifications.services import send_disqualification_email
        # send_disqualification_email(registration, reason)
        
        return {
            'success': True,
            'message': 'Registration disqualified',
            'reason': reason,
            'previous_status': old_status
        }
    
    @staticmethod
    @transaction.atomic
    def auto_unlock_tournament_rosters(tournament: Tournament):
        """
        Unlock all roster members after tournament ends.
        Called by post-tournament cleanup task.
        """
        from apps.organizations.models import TeamMembership
        
        # Find all locked memberships for this tournament
        locked_members = TeamMembership.objects.filter(
            locked_for_tournament_id=tournament.id
        )
        
        unlocked_count = 0
        for membership in locked_members:
            membership.unlock_from_tournament()
            unlocked_count += 1
        
        return {
            'success': True,
            'unlocked_count': unlocked_count,
            'message': f'Unlocked {unlocked_count} roster members'
        }

