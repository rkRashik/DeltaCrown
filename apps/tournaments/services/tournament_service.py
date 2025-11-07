"""
Tournament Service - Business logic for tournament operations.

Source Documents:
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Section 2: Service Layer Architecture)
- Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md (Section 3.1: Core App)
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md (ADR-001: Service Layer Pattern)

Architecture Decisions:
- ADR-001: Service Layer Pattern - All business logic in services, not views or models
- ADR-003: Soft Delete Strategy - Cancel uses soft delete

Responsibilities:
- Tournament creation with validation
- Tournament publishing (draft → published)
- Tournament cancellation with soft delete
- Version management and audit trail

Usage:
    from apps.tournaments.services import TournamentService
    
    # Create tournament
    tournament = TournamentService.create_tournament(
        organizer=request.user,
        data={
            'name': 'DeltaCrown Valorant Cup',
            'game_id': game.id,
            'format': 'single_elimination',
            ...
        }
    )
    
    # Publish tournament
    TournamentService.publish_tournament(
        tournament_id=tournament.id,
        user=request.user
    )
    
    # Cancel tournament
    TournamentService.cancel_tournament(
        tournament_id=tournament.id,
        user=request.user,
        reason='Insufficient registrations'
    )
"""

from typing import Dict, Optional, Any
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from apps.tournaments.models.tournament import Tournament, Game, TournamentVersion


class TournamentService:
    """
    Service class for tournament business logic.
    
    All tournament operations should go through this service layer to ensure:
    - Consistent validation
    - Audit trail via version management
    - Transaction safety
    - Business rule enforcement
    """
    
    @staticmethod
    @transaction.atomic
    def create_tournament(organizer, data: Dict[str, Any]) -> Tournament:
        """
        Create a new tournament with validation.
        
        Args:
            organizer: User creating the tournament
            data: Dictionary containing tournament configuration
                Required fields:
                    - name (str): Tournament name
                    - game_id (int): ID of the game
                    - format (str): Tournament format
                    - max_participants (int): Maximum participants
                    - registration_start (datetime): When registration opens
                    - registration_end (datetime): When registration closes
                    - tournament_start (datetime): When tournament begins
                Optional fields:
                    - description (str)
                    - participation_type (str): 'team' or 'solo'
                    - min_participants (int)
                    - prize_pool (Decimal)
                    - entry_fee_amount (Decimal)
                    - payment_methods (list)
                    - (and all other Tournament model fields)
        
        Returns:
            Tournament: Created tournament instance in DRAFT status
        
        Raises:
            ValidationError: If validation fails
            Game.DoesNotExist: If game_id is invalid
        
        Example:
            >>> tournament = TournamentService.create_tournament(
            ...     organizer=request.user,
            ...     data={
            ...         'name': 'DeltaCrown Valorant Cup',
            ...         'game_id': 1,
            ...         'format': 'single_elimination',
            ...         'max_participants': 16,
            ...         'registration_start': datetime(2025, 11, 10),
            ...         'registration_end': datetime(2025, 11, 15),
            ...         'tournament_start': datetime(2025, 11, 16),
            ...     }
            ... )
        """
        # Validate required fields
        required_fields = [
            'name', 'game_id', 'format', 'max_participants',
            'registration_start', 'registration_end', 'tournament_start'
        ]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Get game
        try:
            game = Game.objects.get(id=data['game_id'], is_active=True)
        except Game.DoesNotExist:
            raise ValidationError(f"Game with ID {data['game_id']} not found or is inactive")
        
        # Validate dates
        reg_start = data['registration_start']
        reg_end = data['registration_end']
        tour_start = data['tournament_start']
        
        if reg_start >= reg_end:
            raise ValidationError("Registration start must be before registration end")
        if reg_end >= tour_start:
            raise ValidationError("Registration must end before tournament starts")
        
        # Validate participants
        max_participants = data['max_participants']
        min_participants = data.get('min_participants', 2)
        if min_participants > max_participants:
            raise ValidationError("Minimum participants cannot exceed maximum participants")
        if min_participants < 2:
            raise ValidationError("Minimum participants must be at least 2")
        
        # Create tournament
        tournament = Tournament(
            name=data['name'],
            description=data.get('description', ''),
            organizer=organizer,
            game=game,
            format=data['format'],
            participation_type=data.get('participation_type', Tournament.TEAM),
            max_participants=max_participants,
            min_participants=min_participants,
            registration_start=reg_start,
            registration_end=reg_end,
            tournament_start=tour_start,
            tournament_end=data.get('tournament_end'),
            status=Tournament.DRAFT,
            
            # Prize pool
            prize_pool=data.get('prize_pool', Decimal('0.00')),
            prize_currency=data.get('prize_currency', 'BDT'),
            prize_deltacoin=data.get('prize_deltacoin', 0),
            prize_distribution=data.get('prize_distribution', {}),
            
            # Entry fee
            has_entry_fee=data.get('has_entry_fee', False),
            entry_fee_amount=data.get('entry_fee_amount', Decimal('0.00')),
            entry_fee_currency=data.get('entry_fee_currency', 'BDT'),
            entry_fee_deltacoin=data.get('entry_fee_deltacoin', 0),
            payment_methods=data.get('payment_methods', []),
            
            # Fee waiver
            enable_fee_waiver=data.get('enable_fee_waiver', False),
            fee_waiver_top_n_teams=data.get('fee_waiver_top_n_teams', 0),
            
            # Media
            banner_image=data.get('banner_image'),
            thumbnail_image=data.get('thumbnail_image'),
            rules_pdf=data.get('rules_pdf'),
            promo_video_url=data.get('promo_video_url', ''),
            stream_youtube_url=data.get('stream_youtube_url', ''),
            stream_twitch_url=data.get('stream_twitch_url', ''),
            
            # Features
            enable_check_in=data.get('enable_check_in', True),
            check_in_minutes_before=data.get('check_in_minutes_before', 15),
            enable_dynamic_seeding=data.get('enable_dynamic_seeding', False),
            enable_live_updates=data.get('enable_live_updates', True),
            enable_certificates=data.get('enable_certificates', True),
            enable_challenges=data.get('enable_challenges', False),
            enable_fan_voting=data.get('enable_fan_voting', False),
            
            # Rules
            rules_text=data.get('rules_text', ''),
            
            # SEO
            meta_description=data.get('meta_description', ''),
            meta_keywords=data.get('meta_keywords', []),
            
            # Official status
            is_official=data.get('is_official', False),
        )
        
        # Full model validation
        tournament.full_clean()
        tournament.save()
        
        # Create initial version
        TournamentService._create_version(
            tournament=tournament,
            changed_by=organizer,
            change_summary="Tournament created"
        )
        
        return tournament
    
    @staticmethod
    @transaction.atomic
    def publish_tournament(tournament_id: int, user) -> Tournament:
        """
        Publish a tournament (DRAFT → PUBLISHED → REGISTRATION_OPEN).
        
        Args:
            tournament_id: ID of tournament to publish
            user: User performing the publish action
        
        Returns:
            Tournament: Published tournament instance
        
        Raises:
            Tournament.DoesNotExist: If tournament not found
            ValidationError: If tournament cannot be published
        
        Example:
            >>> tournament = TournamentService.publish_tournament(
            ...     tournament_id=42,
            ...     user=request.user
            ... )
        """
        tournament = Tournament.objects.get(id=tournament_id)
        
        # Validate current status
        if tournament.status != Tournament.DRAFT:
            raise ValidationError(f"Cannot publish tournament with status '{tournament.status}'")
        
        # Validate tournament configuration
        tournament.full_clean()
        
        # Set status based on registration timing
        now = timezone.now()
        if now >= tournament.registration_start:
            tournament.status = Tournament.REGISTRATION_OPEN
        else:
            tournament.status = Tournament.PUBLISHED
        
        tournament.published_at = now
        tournament.save(update_fields=['status', 'published_at'])
        
        # Create version
        TournamentService._create_version(
            tournament=tournament,
            changed_by=user,
            change_summary=f"Tournament published (status: {tournament.status})"
        )
        
        return tournament
    
    @staticmethod
    @transaction.atomic
    def cancel_tournament(tournament_id: int, user, reason: str = '') -> Tournament:
        """
        Cancel a tournament with soft delete.
        
        Args:
            tournament_id: ID of tournament to cancel
            user: User performing the cancellation
            reason: Reason for cancellation (stored in version)
        
        Returns:
            Tournament: Cancelled tournament instance
        
        Raises:
            Tournament.DoesNotExist: If tournament not found
            ValidationError: If tournament cannot be cancelled
        
        Example:
            >>> tournament = TournamentService.cancel_tournament(
            ...     tournament_id=42,
            ...     user=request.user,
            ...     reason='Insufficient registrations'
            ... )
        """
        tournament = Tournament.objects.get(id=tournament_id)
        
        # Validate can be cancelled
        if tournament.status in [Tournament.COMPLETED, Tournament.ARCHIVED]:
            raise ValidationError(f"Cannot cancel tournament with status '{tournament.status}'")
        
        # Set status to cancelled
        tournament.status = Tournament.CANCELLED
        tournament.save(update_fields=['status'])
        
        # Soft delete
        tournament.soft_delete(user=user)
        
        # Create version
        change_summary = f"Tournament cancelled: {reason}" if reason else "Tournament cancelled"
        TournamentService._create_version(
            tournament=tournament,
            changed_by=user,
            change_summary=change_summary
        )
        
        # TODO: Integration points (future modules)
        # - Notify all registered participants
        # - Process refunds if applicable
        # - Cancel scheduled matches
        
        return tournament
    
    @staticmethod
    def _create_version(tournament: Tournament, changed_by, change_summary: str) -> TournamentVersion:
        """
        Create a version snapshot of tournament configuration.
        
        Args:
            tournament: Tournament to snapshot
            changed_by: User making the change
            change_summary: Description of what changed
        
        Returns:
            TournamentVersion: Created version instance
        
        Note:
            This is an internal method called by public service methods.
            Not meant to be called directly from views.
        """
        # Get latest version number
        latest_version = tournament.versions.order_by('-version_number').first()
        new_version_number = (latest_version.version_number + 1) if latest_version else 1
        
        # Serialize tournament configuration
        version_data = {
            'name': tournament.name,
            'description': tournament.description,
            'game_id': tournament.game_id,
            'format': tournament.format,
            'participation_type': tournament.participation_type,
            'max_participants': tournament.max_participants,
            'min_participants': tournament.min_participants,
            'registration_start': tournament.registration_start.isoformat(),
            'registration_end': tournament.registration_end.isoformat(),
            'tournament_start': tournament.tournament_start.isoformat(),
            'prize_pool': str(tournament.prize_pool),
            'prize_currency': tournament.prize_currency,
            'prize_distribution': tournament.prize_distribution,
            'entry_fee_amount': str(tournament.entry_fee_amount),
            'payment_methods': tournament.payment_methods,
            'status': tournament.status,
        }
        
        # Create version record
        version = TournamentVersion.objects.create(
            tournament=tournament,
            version_number=new_version_number,
            version_data=version_data,
            change_summary=change_summary,
            changed_by=changed_by
        )
        
        return version
    
    @staticmethod
    @transaction.atomic
    def rollback_to_version(tournament_id: int, version_number: int, user) -> Tournament:
        """
        Rollback tournament configuration to a previous version.
        
        Args:
            tournament_id: ID of tournament to rollback
            version_number: Version number to rollback to
            user: User performing the rollback
        
        Returns:
            Tournament: Tournament with configuration restored
        
        Raises:
            Tournament.DoesNotExist: If tournament not found
            TournamentVersion.DoesNotExist: If version not found
            ValidationError: If rollback is not allowed
        
        Example:
            >>> tournament = TournamentService.rollback_to_version(
            ...     tournament_id=42,
            ...     version_number=5,
            ...     user=request.user
            ... )
        """
        tournament = Tournament.objects.get(id=tournament_id)
        version = TournamentVersion.objects.get(
            tournament=tournament,
            version_number=version_number
        )
        
        # Validate can rollback
        if tournament.status in [Tournament.LIVE, Tournament.COMPLETED]:
            raise ValidationError("Cannot rollback tournament that is live or completed")
        
        # Restore configuration from version_data
        version_data = version.version_data
        tournament.name = version_data.get('name', tournament.name)
        tournament.description = version_data.get('description', tournament.description)
        tournament.format = version_data.get('format', tournament.format)
        tournament.max_participants = version_data.get('max_participants', tournament.max_participants)
        tournament.prize_pool = Decimal(version_data.get('prize_pool', '0.00'))
        tournament.entry_fee_amount = Decimal(version_data.get('entry_fee_amount', '0.00'))
        # ... restore other fields as needed
        
        tournament.save()
        
        # Mark rollback in version history
        version.rolled_back_at = timezone.now()
        version.rolled_back_by = user
        version.save(update_fields=['rolled_back_at', 'rolled_back_by'])
        
        # Create new version after rollback
        TournamentService._create_version(
            tournament=tournament,
            changed_by=user,
            change_summary=f"Rolled back to version {version_number}"
        )
        
        return tournament
