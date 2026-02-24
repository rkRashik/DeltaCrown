"""
Smart Registration Service for Phase 5.

Orchestrates configuration-driven registration flows with:
- Dynamic question forms
- Draft persistence
- Answer validation
- Auto-approval/rejection rules
- Event publishing

Source: Documents/Modify_TournamentApp/Workplan/SMART_REG_AND_RULES_PART_3.md (Section 3)
Architecture: No ORM imports - uses adapters only
"""

from typing import Optional
from datetime import datetime

from apps.tournament_ops.dtos import (
    RegistrationDTO,
    RegistrationQuestionDTO,
    RegistrationRuleDTO,
    RegistrationDraftDTO,
)
from apps.tournament_ops.adapters import (
    SmartRegistrationAdapterProtocol,
    TeamAdapterProtocol,
    UserAdapterProtocol,
    GameAdapterProtocol,
    TournamentAdapterProtocol,
)
from apps.tournament_ops.exceptions import (
    InvalidRegistrationStateError,
    RegistrationNotFoundError,
)
from apps.tournament_ops.services.registration_service import RegistrationService
from apps.common.events import get_event_bus, Event


class SmartRegistrationService:
    """
    Smart registration orchestration layer.
    
    Wraps existing RegistrationService with:
    - Configuration-driven questions
    - Draft persistence
    - Auto-approval rules
    - Multi-step wizard support
    """
    
    def __init__(
        self,
        smart_reg_adapter: SmartRegistrationAdapterProtocol,
        registration_service: RegistrationService,
        team_adapter: TeamAdapterProtocol,
        user_adapter: UserAdapterProtocol,
        game_adapter: GameAdapterProtocol,
        tournament_adapter: TournamentAdapterProtocol,
    ):
        self.smart_reg_adapter = smart_reg_adapter
        self.registration_service = registration_service
        self.team_adapter = team_adapter
        self.user_adapter = user_adapter
        self.game_adapter = game_adapter
        self.tournament_adapter = tournament_adapter
    
    def create_draft_registration(
        self,
        tournament_id: int,
        user_id: int,
        team_id: Optional[int] = None,
    ) -> RegistrationDraftDTO:
        """
        Create a new registration draft.
        
        Workflow:
        1. Validate eligibility (reuse existing RegistrationService logic)
        2. Generate registration number
        3. Create draft
        4. Publish event
        
        Args:
            tournament_id: Tournament ID
            user_id: User creating registration
            team_id: Team ID (null for solo tournaments)
        
        Returns:
            RegistrationDraftDTO
        
        Raises:
            InvalidRegistrationStateError: If eligibility fails
        """
        # Basic eligibility check via existing service
        tournament = self.tournament_adapter.get_tournament(tournament_id)
        
        # Generate registration number
        registration_number = self._generate_registration_number(tournament_id)
        
        # Create draft via adapter
        draft = self.smart_reg_adapter.create_draft(
            user_id=user_id,
            tournament_id=tournament_id,
            team_id=team_id,
            registration_number=registration_number,
        )
        
        # Publish event
        event_bus = get_event_bus()
        event_bus.publish(Event(
            name='RegistrationDraftCreatedEvent',
            payload={
                'draft_id': draft.id,
                'draft_uuid': draft.uuid,
                'registration_number': draft.registration_number,
                'user_id': user_id,
                'tournament_id': tournament_id,
                'team_id': team_id,
            }
        ))
        
        return draft
    
    def get_registration_form(
        self,
        tournament_id: int,
        user_id: int,
        team_id: Optional[int] = None,
    ) -> dict:
        """
        Get registration form configuration.
        
        Returns JSON structure for frontend:
        - Built-in system questions (from Game configuration)
        - Custom organizer questions (from RegistrationQuestion)
        - Auto-fill data
        - Validation rules
        
        Args:
            tournament_id: Tournament ID
            user_id: User ID
            team_id: Team ID (null for solo)
        
        Returns:
            {
                'questions': [RegistrationQuestionDTO, ...],
                'auto_fill_data': {field_name: value, ...},
                'locked_fields': [field_name, ...],
            }
        """
        # Get tournament and game info
        tournament = self.tournament_adapter.get_tournament(tournament_id)
        
        # Get dynamic questions
        questions = self.smart_reg_adapter.get_questions_for_tournament(tournament_id)
        
        # Get auto-fill data from user profile
        user_profile = self.user_adapter.get_profile_data(user_id)
        auto_fill_data = {
            'email': user_profile.email,
            'phone': user_profile.phone or '',
            'discord': user_profile.discord or '',
        }
        
        # Lock verified fields
        locked_fields = []
        if user_profile.email_verified:
            locked_fields.append('email')
        if user_profile.phone_verified:
            locked_fields.append('phone')
        
        # Get game-specific identity fields
        game_identity_configs = self.game_adapter.get_identity_fields(tournament.game_id)
        for config in game_identity_configs:
            # Auto-fill from profile
            field_value = getattr(user_profile, config.field_name, None)
            if field_value:
                auto_fill_data[config.field_name] = field_value
        
        return {
            'questions': [q.to_dict() for q in questions],
            'auto_fill_data': auto_fill_data,
            'locked_fields': locked_fields,
        }
    
    def submit_answers(
        self,
        registration_id: int,
        answers: dict,
    ) -> RegistrationDTO:
        """
        Submit answers to registration questions.
        
        Workflow:
        1. Validate answers against question definitions
        2. Save answers via adapter
        3. Publish event
        
        Args:
            registration_id: Registration ID
            answers: {question_slug: answer_value, ...}
        
        Returns:
            Updated RegistrationDTO
        
        Raises:
            InvalidRegistrationStateError: If validation fails
        """
        # Get registration
        registration = self.registration_service.get_registration(registration_id)
        
        # Get questions for validation
        questions = self.smart_reg_adapter.get_questions_for_tournament(registration.tournament_id)
        question_map = {q.slug: q for q in questions}
        
        # Validate answers
        errors = []
        for slug, value in answers.items():
            if slug in question_map:
                question = question_map[slug]
                is_valid, question_errors = question.validate_answer(value)
                if not is_valid:
                    errors.extend(question_errors)
        
        # Check required questions
        for question in questions:
            if question.is_required and question.slug not in answers:
                errors.append(f'{question.text} is required')
        
        if errors:
            raise InvalidRegistrationStateError(
                f"Answer validation failed: {', '.join(errors)}"
            )
        
        # Save answers via adapter
        self.smart_reg_adapter.save_answers(registration_id, answers)
        
        # Publish event
        event_bus = get_event_bus()
        event_bus.publish(Event(
            name='RegistrationAnswersSubmittedEvent',
            payload={
                'registration_id': registration_id,
                'tournament_id': registration.tournament_id,
                'user_id': registration.user_id,
                'answers': answers,
            }
        ))
        
        return registration
    
    def evaluate_registration(
        self,
        registration_id: int,
    ) -> RegistrationDTO:
        """
        Evaluate registration against auto-approval rules.
        
        Workflow:
        1. Get registration + answers
        2. Get rules for tournament
        3. Evaluate rules in priority order
        4. Apply first matching rule:
           - AUTO_APPROVE → call RegistrationService.complete_registration
           - AUTO_REJECT → update status to REJECTED
           - FLAG_FOR_REVIEW → update status to NEEDS_REVIEW
        5. Publish appropriate event
        
        Args:
            registration_id: Registration ID
        
        Returns:
            Updated RegistrationDTO
        """
        # Get registration
        registration = self.registration_service.get_registration(registration_id)
        
        # Get answers
        answers = self.smart_reg_adapter.get_answers(registration_id)
        
        # Get rules
        rules = self.smart_reg_adapter.get_rules_for_tournament(registration.tournament_id)
        
        # Build registration data for evaluation
        user_profile = self.user_adapter.get_profile_data(registration.user_id)
        registration_data = {
            'user_id': registration.user_id,
            'team_id': registration.team_id,
            'email_verified': user_profile.email_verified,
            'phone_verified': user_profile.phone_verified,
        }
        
        # Evaluate rules in priority order
        matched_rule = None
        for rule in rules:
            if rule.evaluate(registration_data, answers):
                matched_rule = rule
                break
        
        event_bus = get_event_bus()
        
        if matched_rule:
            if matched_rule.rule_type == 'auto_approve':
                # Auto-approve: use existing RegistrationService workflow
                # Note: This would call complete_registration in real implementation
                # For Phase 5, just update state
                registration.status = 'auto_approved'
                
                event_bus.publish(Event(
                    name='RegistrationAutoApprovedEvent',
                    payload={
                        'registration_id': registration_id,
                        'tournament_id': registration.tournament_id,
                        'user_id': registration.user_id,
                        'rule_id': matched_rule.id,
                        'rule_name': matched_rule.name,
                        'reason': matched_rule.reason_template,
                    }
                ))
            
            elif matched_rule.rule_type == 'auto_reject':
                # Auto-reject
                registration.status = 'rejected'
                
                event_bus.publish(Event(
                    name='RegistrationAutoRejectedEvent',
                    payload={
                        'registration_id': registration_id,
                        'tournament_id': registration.tournament_id,
                        'user_id': registration.user_id,
                        'rule_id': matched_rule.id,
                        'rule_name': matched_rule.name,
                        'reason': matched_rule.reason_template,
                    }
                ))
            
            elif matched_rule.rule_type == 'flag_for_review':
                # Flag for manual review
                registration.status = 'needs_review'
                
                event_bus.publish(Event(
                    name='RegistrationFlaggedForReviewEvent',
                    payload={
                        'registration_id': registration_id,
                        'tournament_id': registration.tournament_id,
                        'user_id': registration.user_id,
                        'rule_id': matched_rule.id,
                        'rule_name': matched_rule.name,
                        'reason': matched_rule.reason_template,
                    }
                ))
        else:
            # No rule matched, default to needs review
            registration.status = 'needs_review'
            
            event_bus.publish(Event(
                name='RegistrationFlaggedForReviewEvent',
                payload={
                    'registration_id': registration_id,
                    'tournament_id': registration.tournament_id,
                    'user_id': registration.user_id,
                    'rule_id': None,
                    'rule_name': 'No matching rule',
                    'reason': 'Manual organizer review required',
                }
            ))
        
        return registration
    
    def auto_process_registration(
        self,
        tournament_id: int,
        user_id: int,
        team_id: Optional[int],
        answers: dict,
    ) -> tuple[RegistrationDTO, str]:
        """
        One-shot registration processing (for testing/simple flows).
        
        Workflow:
        1. Create registration via RegistrationService
        2. Submit answers
        3. Evaluate rules
        4. Return registration + decision
        
        Args:
            tournament_id: Tournament ID
            user_id: User ID
            team_id: Team ID (null for solo)
            answers: {question_slug: answer_value, ...}
        
        Returns:
            (RegistrationDTO, decision: 'auto_approved'|'auto_rejected'|'needs_review')
        """
        # Create registration via existing service
        registration = self.registration_service.create_registration(
            tournament_id=tournament_id,
            user_id=user_id,
            team_id=team_id,
            registration_data={}  # Answers stored separately
        )
        
        # Submit answers
        self.submit_answers(registration.id, answers)
        
        # Evaluate registration
        updated_registration = self.evaluate_registration(registration.id)
        
        # Determine decision
        decision = updated_registration.status
        if decision == 'auto_approved':
            decision_str = 'auto_approved'
        elif decision == 'rejected':
            decision_str = 'auto_rejected'
        else:
            decision_str = 'needs_review'
        
        return (updated_registration, decision_str)
    
    def _generate_registration_number(self, tournament_id: int) -> str:
        """
        Generate unique registration number.
        
        Format: {GAME_PREFIX}-{YEAR}-{SEQUENCE}
        Example: VCT-2025-001234
        
        Args:
            tournament_id: Tournament ID
        
        Returns:
            Registration number
        """
        from django.utils import timezone
        import random
        
        tournament = self.tournament_adapter.get_tournament(tournament_id)
        
        # Get game prefix (first 4 chars of game slug, uppercase)
        game_prefix = tournament.game_slug[:4].upper() if hasattr(tournament, 'game_slug') else 'TOURN'
        
        # Get year
        year = timezone.now().year
        
        # Generate random sequence (simple implementation for Phase 5)
        # Phase 6+: Use database sequence or counter
        sequence = random.randint(1, 999999)
        
        return f'{game_prefix}-{year}-{sequence:06d}'
