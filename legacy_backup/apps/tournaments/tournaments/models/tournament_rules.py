"""
TournamentRules Model
Handles all rules, regulations, eligibility requirements, and scoring systems
for tournaments.

Part of Phase 1 - Core Tournament Models
"""

from django.db import models
from django.core.exceptions import ValidationError
from django_ckeditor_5.fields import CKEditor5Field
from typing import Optional, Dict, List


class TournamentRules(models.Model):
    """
    Rules, regulations, and requirements for tournaments.
    
    This model handles all rule-related fields that were previously part of
    the Tournament model. It provides centralized management of tournament
    rules and requirements.
    
    Fields:
    - general_rules: General competition rules (rich text)
    - eligibility_requirements: Who can participate (rich text)
    - match_rules: Match-specific rules (rich text)
    - scoring_system: How scoring works (rich text)
    - penalty_rules: Penalty and disqualification rules (rich text)
    - prize_distribution_rules: How prizes are distributed (rich text)
    - additional_notes: Any additional information (rich text)
    - checkin_instructions: Check-in process instructions (rich text)
    - require_discord: Discord account required for participation
    - require_game_id: Game account ID required
    - require_team_logo: Team logo required for team tournaments
    - min_age: Minimum age requirement
    - max_age: Maximum age requirement
    - region_restriction: Geographic region restrictions
    - rank_restriction: Game rank restrictions
    - created_at: Timestamp of creation
    - updated_at: Timestamp of last update
    """
    
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='rules',
        help_text="Associated tournament"
    )
    
    # Rule sections (rich text)
    general_rules = CKEditor5Field(
        'General Rules',
        config_name='default',
        blank=True,
        null=True,
        help_text="General competition rules and guidelines"
    )
    
    eligibility_requirements = CKEditor5Field(
        'Eligibility Requirements',
        config_name='default',
        blank=True,
        null=True,
        help_text="Who can participate in this tournament"
    )
    
    match_rules = CKEditor5Field(
        'Match Rules',
        config_name='default',
        blank=True,
        null=True,
        help_text="Specific rules for matches"
    )
    
    scoring_system = CKEditor5Field(
        'Scoring System',
        config_name='default',
        blank=True,
        null=True,
        help_text="How scoring and points work"
    )
    
    penalty_rules = CKEditor5Field(
        'Penalty Rules',
        config_name='default',
        blank=True,
        null=True,
        help_text="Penalties and disqualification rules"
    )
    
    prize_distribution_rules = CKEditor5Field(
        'Prize Distribution Rules',
        config_name='default',
        blank=True,
        null=True,
        help_text="How prizes are distributed to winners"
    )
    
    additional_notes = CKEditor5Field(
        'Additional Notes',
        config_name='default',
        blank=True,
        null=True,
        help_text="Any additional information or notes"
    )
    
    checkin_instructions = CKEditor5Field(
        'Check-in Instructions',
        config_name='default',
        blank=True,
        null=True,
        help_text="Instructions for tournament check-in process"
    )
    
    # Requirement flags
    require_discord = models.BooleanField(
        default=False,
        help_text="Require Discord account for participation"
    )
    
    require_game_id = models.BooleanField(
        default=True,
        help_text="Require game account ID/username"
    )
    
    require_team_logo = models.BooleanField(
        default=False,
        help_text="Require team logo for team tournaments"
    )
    
    # Age restrictions
    min_age = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Minimum age requirement (years)"
    )
    
    max_age = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Maximum age requirement (years)"
    )
    
    # Geographic and rank restrictions
    region_restriction = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Geographic region restrictions (e.g., 'Bangladesh only', 'Asia')"
    )
    
    rank_restriction = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Game rank restrictions (e.g., 'Gold and above', 'Diamond+')"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this rules record was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this rules record was last updated"
    )
    
    class Meta:
        db_table = 'tournament_rules'
        verbose_name = 'Tournament Rules'
        verbose_name_plural = 'Tournament Rules'
        ordering = ['-updated_at']
    
    def __str__(self) -> str:
        return f"Rules for {self.tournament.name}"
    
    def clean(self) -> None:
        """
        Validate rules fields.
        - Check age restrictions are logical
        - Validate that min_age <= max_age
        """
        super().clean()
        
        # Validate age restrictions
        if self.min_age is not None and self.min_age < 0:
            raise ValidationError({
                'min_age': 'Minimum age cannot be negative'
            })
        
        if self.max_age is not None and self.max_age < 0:
            raise ValidationError({
                'max_age': 'Maximum age cannot be negative'
            })
        
        if self.min_age is not None and self.max_age is not None:
            if self.min_age > self.max_age:
                raise ValidationError({
                    'max_age': 'Maximum age must be greater than or equal to minimum age'
                })
        
        # Validate reasonable age ranges
        if self.min_age is not None and self.min_age > 100:
            raise ValidationError({
                'min_age': 'Minimum age seems unreasonably high'
            })
        
        if self.max_age is not None and self.max_age > 150:
            raise ValidationError({
                'max_age': 'Maximum age seems unreasonably high'
            })
    
    # Property methods for checking rule sections
    @property
    def has_general_rules(self) -> bool:
        """Check if tournament has general rules"""
        return bool(self.general_rules)
    
    @property
    def has_eligibility_requirements(self) -> bool:
        """Check if tournament has eligibility requirements"""
        return bool(self.eligibility_requirements)
    
    @property
    def has_match_rules(self) -> bool:
        """Check if tournament has match rules"""
        return bool(self.match_rules)
    
    @property
    def has_scoring_system(self) -> bool:
        """Check if tournament has scoring system"""
        return bool(self.scoring_system)
    
    @property
    def has_penalty_rules(self) -> bool:
        """Check if tournament has penalty rules"""
        return bool(self.penalty_rules)
    
    @property
    def has_prize_distribution_rules(self) -> bool:
        """Check if tournament has prize distribution rules"""
        return bool(self.prize_distribution_rules)
    
    @property
    def has_additional_notes(self) -> bool:
        """Check if tournament has additional notes"""
        return bool(self.additional_notes)
    
    @property
    def has_checkin_instructions(self) -> bool:
        """Check if tournament has check-in instructions"""
        return bool(self.checkin_instructions)
    
    @property
    def has_age_restrictions(self) -> bool:
        """Check if tournament has any age restrictions"""
        return self.min_age is not None or self.max_age is not None
    
    @property
    def has_region_restriction(self) -> bool:
        """Check if tournament has region restrictions"""
        return bool(self.region_restriction)
    
    @property
    def has_rank_restriction(self) -> bool:
        """Check if tournament has rank restrictions"""
        return bool(self.rank_restriction)
    
    @property
    def has_any_restrictions(self) -> bool:
        """Check if tournament has any restrictions"""
        return (
            self.has_age_restrictions or
            self.has_region_restriction or
            self.has_rank_restriction
        )
    
    @property
    def has_complete_rules(self) -> bool:
        """Check if tournament has all essential rule sections"""
        return (
            self.has_general_rules and
            self.has_eligibility_requirements and
            self.has_match_rules
        )
    
    @property
    def age_range_text(self) -> Optional[str]:
        """Get formatted age range text"""
        if not self.has_age_restrictions:
            return None
        
        if self.min_age is not None and self.max_age is not None:
            return f"{self.min_age}-{self.max_age} years"
        elif self.min_age is not None:
            return f"{self.min_age}+ years"
        elif self.max_age is not None:
            return f"Under {self.max_age} years"
        
        return None
    
    def get_rule_sections(self) -> Dict[str, Optional[str]]:
        """Get all rule sections in a dictionary"""
        return {
            'general_rules': self.general_rules,
            'eligibility_requirements': self.eligibility_requirements,
            'match_rules': self.match_rules,
            'scoring_system': self.scoring_system,
            'penalty_rules': self.penalty_rules,
            'prize_distribution_rules': self.prize_distribution_rules,
            'additional_notes': self.additional_notes,
            'checkin_instructions': self.checkin_instructions,
        }
    
    def get_requirements(self) -> Dict[str, bool]:
        """Get all requirement flags in a dictionary"""
        return {
            'require_discord': self.require_discord,
            'require_game_id': self.require_game_id,
            'require_team_logo': self.require_team_logo,
        }
    
    def get_restrictions(self) -> Dict[str, Optional[str]]:
        """Get all restrictions in a dictionary"""
        return {
            'age_range': self.age_range_text,
            'min_age': self.min_age,
            'max_age': self.max_age,
            'region': self.region_restriction,
            'rank': self.rank_restriction,
        }
    
    def get_populated_sections(self) -> List[str]:
        """Get list of section names that have content"""
        sections = []
        if self.has_general_rules:
            sections.append('general_rules')
        if self.has_eligibility_requirements:
            sections.append('eligibility_requirements')
        if self.has_match_rules:
            sections.append('match_rules')
        if self.has_scoring_system:
            sections.append('scoring_system')
        if self.has_penalty_rules:
            sections.append('penalty_rules')
        if self.has_prize_distribution_rules:
            sections.append('prize_distribution_rules')
        if self.has_additional_notes:
            sections.append('additional_notes')
        if self.has_checkin_instructions:
            sections.append('checkin_instructions')
        return sections
    
    @property
    def populated_sections_count(self) -> int:
        """Count how many rule sections have content"""
        return len(self.get_populated_sections())
