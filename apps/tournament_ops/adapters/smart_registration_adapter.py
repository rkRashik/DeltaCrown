"""
Smart Registration Adapter for Phase 5.

Provides access to registration configuration (questions, rules, drafts)
without coupling tournament_ops service layer to ORM models.

Source: Documents/Modify_TournamentApp/Workplan/SMART_REG_AND_RULES_PART_3.md
Architecture: No ORM imports in tournament_ops - all model access via adapters
"""

from typing import Protocol, Optional, Any
from apps.tournament_ops.dtos import (
    RegistrationQuestionDTO,
    RegistrationRuleDTO,
    RegistrationDraftDTO,
)
from apps.tournament_ops.exceptions import RegistrationNotFoundError


class SmartRegistrationAdapterProtocol(Protocol):
    """
    Protocol for smart registration adapter.
    
    Defines interface for accessing registration configuration without ORM coupling.
    """
    
    def get_questions_for_tournament(self, tournament_id: int) -> list[RegistrationQuestionDTO]:
        """
        Get all registration questions for tournament.
        
        Includes:
        - Tournament-specific questions
        - Game-specific questions
        - Global questions
        
        Args:
            tournament_id: Tournament ID
        
        Returns:
            List of RegistrationQuestionDTO ordered by display order
        """
        ...
    
    def get_rules_for_tournament(self, tournament_id: int) -> list[RegistrationRuleDTO]:
        """
        Get all active registration rules for tournament.
        
        Args:
            tournament_id: Tournament ID
        
        Returns:
            List of RegistrationRuleDTO ordered by priority (lowest first)
        """
        ...
    
    def create_draft(
        self,
        user_id: int,
        tournament_id: int,
        team_id: Optional[int],
        registration_number: str,
    ) -> RegistrationDraftDTO:
        """
        Create a new registration draft.
        
        Args:
            user_id: User creating the draft
            tournament_id: Tournament ID
            team_id: Team ID (null for solo tournaments)
            registration_number: Unique registration number (e.g., VCT-2025-001234)
        
        Returns:
            RegistrationDraftDTO
        """
        ...
    
    def get_draft(self, draft_uuid: str) -> RegistrationDraftDTO:
        """
        Get draft by UUID.
        
        Args:
            draft_uuid: Draft UUID
        
        Returns:
            RegistrationDraftDTO
        
        Raises:
            RegistrationNotFoundError: If draft doesn't exist
        """
        ...
    
    def update_draft(
        self,
        draft_uuid: str,
        form_data: dict,
        current_step: str,
        completion_percentage: int,
    ) -> RegistrationDraftDTO:
        """
        Update draft data (auto-save).
        
        Args:
            draft_uuid: Draft UUID
            form_data: Updated form data
            current_step: Current wizard step
            completion_percentage: 0-100
        
        Returns:
            Updated RegistrationDraftDTO
        """
        ...
    
    def save_answers(
        self,
        registration_id: int,
        answers: dict[str, Any],
    ) -> None:
        """
        Save answers to registration questions.
        
        Args:
            registration_id: Registration ID
            answers: {question_slug: answer_value, ...}
        """
        ...
    
    def get_answers(self, registration_id: int) -> dict[str, Any]:
        """
        Get all answers for registration.
        
        Args:
            registration_id: Registration ID
        
        Returns:
            {question_slug: answer_value, ...}
        """
        ...


class SmartRegistrationAdapter:
    """
    Concrete implementation of SmartRegistrationAdapter.
    
    Uses method-level imports to avoid ORM coupling.
    """
    
    def get_questions_for_tournament(self, tournament_id: int) -> list[RegistrationQuestionDTO]:
        """Get all registration questions for tournament."""
        from apps.tournaments.models import RegistrationQuestion, Tournament
        from django.db import models as django_models
        
        # Get tournament and its game
        tournament = Tournament.objects.select_related('game').get(id=tournament_id)
        
        # Fetch questions: tournament-specific + game-specific + global
        questions = RegistrationQuestion.objects.filter(
            django_models.Q(tournament_id=tournament_id) |
            django_models.Q(game_id=tournament.game_id, tournament_id__isnull=True) |
            django_models.Q(tournament_id__isnull=True, game_id__isnull=True),
            is_active=True
        ).order_by('order', 'id')
        
        return [RegistrationQuestionDTO.from_model(q) for q in questions]
    
    def get_rules_for_tournament(self, tournament_id: int) -> list[RegistrationRuleDTO]:
        """Get all active registration rules for tournament."""
        from apps.tournaments.models import RegistrationRule
        
        rules = RegistrationRule.objects.filter(
            tournament_id=tournament_id,
            is_active=True
        ).order_by('priority', 'id')
        
        return [RegistrationRuleDTO.from_model(r) for r in rules]
    
    def create_draft(
        self,
        user_id: int,
        tournament_id: int,
        team_id: Optional[int],
        registration_number: str,
    ) -> RegistrationDraftDTO:
        """Create a new registration draft."""
        from apps.tournaments.models import RegistrationDraft
        from django.utils import timezone
        
        # Create draft
        draft = RegistrationDraft.objects.create(
            user_id=user_id,
            tournament_id=tournament_id,
            team_id=team_id,
            registration_number=registration_number,
            form_data={},
            auto_filled_fields=[],
            locked_fields=[],
            current_step='player_info',
            completion_percentage=0,
            submitted=False,
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )
        
        return RegistrationDraftDTO.from_model(draft)
    
    def get_draft(self, draft_uuid: str) -> RegistrationDraftDTO:
        """Get draft by UUID."""
        from apps.tournaments.models import RegistrationDraft
        
        try:
            draft = RegistrationDraft.objects.get(uuid=draft_uuid)
            return RegistrationDraftDTO.from_model(draft)
        except RegistrationDraft.DoesNotExist:
            raise RegistrationNotFoundError(f"Draft with UUID {draft_uuid} not found")
    
    def update_draft(
        self,
        draft_uuid: str,
        form_data: dict,
        current_step: str,
        completion_percentage: int,
    ) -> RegistrationDraftDTO:
        """Update draft data (auto-save)."""
        from apps.tournaments.models import RegistrationDraft
        
        try:
            draft = RegistrationDraft.objects.get(uuid=draft_uuid)
            draft.form_data = form_data
            draft.current_step = current_step
            draft.completion_percentage = completion_percentage
            draft.save()
            
            return RegistrationDraftDTO.from_model(draft)
        except RegistrationDraft.DoesNotExist:
            raise RegistrationNotFoundError(f"Draft with UUID {draft_uuid} not found")
    
    def save_answers(
        self,
        registration_id: int,
        answers: dict[str, Any],
    ) -> None:
        """Save answers to registration questions."""
        from apps.tournaments.models import RegistrationAnswer, RegistrationQuestion
        
        # Get all questions by slug
        question_slugs = list(answers.keys())
        questions = RegistrationQuestion.objects.filter(slug__in=question_slugs)
        question_map = {q.slug: q for q in questions}
        
        # Create or update answers
        for slug, value in answers.items():
            if slug not in question_map:
                # Unknown question slug, skip
                continue
            
            question = question_map[slug]
            
            # Normalize value for search
            if isinstance(value, (list, dict)):
                normalized = str(value)
            else:
                normalized = str(value) if value is not None else ''
            
            # Create or update answer
            RegistrationAnswer.objects.update_or_create(
                registration_id=registration_id,
                question=question,
                defaults={
                    'value': value,
                    'normalized_value': normalized,
                }
            )
    
    def get_answers(self, registration_id: int) -> dict[str, Any]:
        """Get all answers for registration."""
        from apps.tournaments.models import RegistrationAnswer
        
        answers = RegistrationAnswer.objects.filter(
            registration_id=registration_id
        ).select_related('question')
        
        return {
            answer.question.slug: answer.value
            for answer in answers
        }
