"""
Registration Service - Business logic for tournament registration and payment operations.

Source Documents:
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Section 5: Service Layer - RegistrationService, PaymentService)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 4: Registration & Payment Models)
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md (UI Flow and Payment Verification)
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md (ADR-001: Service Layer Pattern, ADR-003: Soft Delete)

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
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Q
from apps.tournaments.models import Registration, Payment, Tournament


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
        registration_data: Optional[Dict[str, Any]] = None
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
        # Get tournament
        try:
            tournament = Tournament.objects.select_related('game').get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament with ID {tournament_id} not found")
        
        # Validate eligibility
        RegistrationService.check_eligibility(
            tournament=tournament,
            user=user,
            team_id=team_id
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
        
        # Create registration
        registration = Registration(
            tournament=tournament,
            user=user,
            team_id=team_id,
            registration_data=merged_data,
            status=Registration.PENDING
        )
        
        # Validate
        registration.full_clean()
        registration.save()
        
        # TODO: Future integration points
        # - Send notification to user (apps.notifications)
        # - Create discussion thread if enabled (apps.siteui)
        # - Log event to analytics (apps.tournaments.analytics)
        
        return registration
    
    @staticmethod
    def check_eligibility(
        tournament: Tournament,
        user,
        team_id: Optional[int] = None
    ) -> None:
        """
        Check if a participant is eligible to register for a tournament.
        
        Args:
            tournament: Tournament to check eligibility for
            user: User attempting to register
            team_id: Team ID if registering as a team
        
        Raises:
            ValidationError: If participant is not eligible
        
        Validation Rules:
            1. Tournament must be accepting registrations (status = REGISTRATION_OPEN)
            2. Registration period must be active (within registration_start and registration_end)
            3. Tournament must not be full (check max_participants)
            4. User/team must not already be registered
            5. Participation type must match (team vs solo)
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
        
        # Check capacity
        current_registrations = Registration.objects.filter(
            tournament=tournament,
            status__in=[Registration.PENDING, Registration.PAYMENT_SUBMITTED, Registration.CONFIRMED],
            is_deleted=False
        ).count()
        
        if current_registrations >= tournament.max_participants:
            raise ValidationError(
                f"Tournament is full ({tournament.max_participants} participants)"
            )
        
        # Check participation type match
        if tournament.participation_type == Tournament.TEAM and team_id is None:
            raise ValidationError("This tournament requires team registration")
        if tournament.participation_type == Tournament.SOLO and team_id is not None:
            raise ValidationError("This tournament is for solo participants only")
        
        # Check for duplicate registration
        existing_registration = Registration.objects.filter(
            tournament=tournament,
            user=user,
            is_deleted=False
        ).exclude(
            status__in=[Registration.CANCELLED, Registration.REJECTED]
        ).first()
        
        if existing_registration:
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
        
        # Get game-specific ID field
        game_id_field = tournament.game.profile_id_field
        game_id = getattr(profile, game_id_field, None)
        
        data = {
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
        }
        
        # Add game ID if available
        if game_id:
            data['game_id'] = game_id
        
        # Add optional profile fields if they exist
        if hasattr(profile, 'discord_id') and profile.discord_id:
            data['discord_id'] = profile.discord_id
        if hasattr(profile, 'phone_number') and profile.phone_number:
            data['phone'] = profile.phone_number
        
        return data
    
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
        
        # Update registration status
        registration.status = Registration.PAYMENT_SUBMITTED
        registration.save(update_fields=['status'])
        
        # TODO: Future integration points
        # - Send notification to organizer (apps.notifications)
        # - Log payment submission event
        
        return payment
    
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
        
        # TODO: Module 3.2 - Future integration points
        # - Send notification to organizer (apps.notifications)
        # - Celery task: send_proof_uploaded_email(payment.id)
        # - Log proof submission event in audit log
        
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
                'participant_type': registration.participant_type,
                'participant_id': registration.participant_id,
                'amount': str(payment.amount) if payment.amount else '0',
                'payment_method': payment.payment_method,
                'admin_notes': admin_notes,
            }
        )
        
        # TODO: Future integration points
        # - Send confirmation notification to participant (apps.notifications)
        # - Award DeltaCoin if applicable (apps.economy)
        # - Update tournament analytics
        
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
                'participant_type': registration.participant_type,
                'participant_id': registration.participant_id,
                'reason': reason,
            }
        )
        
        # TODO: Future integration points
        # - Send rejection notification to participant (apps.notifications)
        # - Explain how to resubmit payment
        
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
        
        # TODO: Future integration points
        # - Send cancellation confirmation notification (apps.notifications)
        # - Update tournament capacity analytics
        # - Release slot for waitlist if applicable
        
        return registration
    
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
