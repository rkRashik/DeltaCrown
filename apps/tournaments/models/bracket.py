"""
Bracket and BracketNode models for tournament bracket structures (Module 1.5)

Source Documents:
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 5: Bracket Structure Models)
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Section 6: BracketService)
- Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md (Bracket visualization)
- Documents/Planning/PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md (Constraints & indexes)
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md (ADR-001, ADR-003, ADR-004)

Architecture Decisions:
- ADR-001: Service layer pattern - Business logic in BracketService
- ADR-004: PostgreSQL features - JSONB for bracket_structure, GIN indexes

Bracket Formats:
- Single Elimination: Standard knockout tournament
- Double Elimination: Winners + Losers brackets with grand finals
- Round Robin: All participants play each other
- Swiss: Swiss system pairing
- Group Stage: Groups with knockout phase

Seeding Methods:
- slot-order: First-come-first-served (registration order)
- random: Random seeding
- ranked: Based on team rankings from apps.teams
- manual: Organizer manually assigns seeds

BracketNode Navigation:
Double-linked list structure for efficient traversal:
- parent_node: Next match (winner advances here)
- child1_node/child2_node: Previous matches (winners come from here)
- parent_slot: Which slot in parent match (1 or 2)
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.postgres.indexes import GinIndex
from django.db.models import Q, CheckConstraint
from typing import Any, Optional

from apps.common.models import TimestampedModel


# ===========================
# Bracket Model
# ===========================

class Bracket(TimestampedModel):
    """
    Container for tournament bracket structure.
    
    Stores overall bracket configuration and metadata.
    Individual bracket positions/matches are stored in BracketNode model.
    
    Example bracket_structure (Single Elimination, 8 participants):
    {
        "format": "single-elimination",
        "total_participants": 8,
        "rounds": [
            {"round_number": 1, "round_name": "Quarter Finals", "matches": 4},
            {"round_number": 2, "round_name": "Semi Finals", "matches": 2},
            {"round_number": 3, "round_name": "Finals", "matches": 1}
        ],
        "third_place_match": true
    }
    """
    
    # Format choices
    SINGLE_ELIMINATION = 'single-elimination'
    DOUBLE_ELIMINATION = 'double-elimination'
    ROUND_ROBIN = 'round-robin'
    SWISS = 'swiss'
    GROUP_STAGE = 'group-stage'
    
    FORMAT_CHOICES = [
        (SINGLE_ELIMINATION, _('Single Elimination')),
        (DOUBLE_ELIMINATION, _('Double Elimination')),
        (ROUND_ROBIN, _('Round Robin')),
        (SWISS, _('Swiss System')),
        (GROUP_STAGE, _('Group Stage')),
    ]
    
    # Seeding method choices
    SLOT_ORDER = 'slot-order'
    RANDOM = 'random'
    RANKED = 'ranked'
    MANUAL = 'manual'
    
    SEEDING_METHOD_CHOICES = [
        (SLOT_ORDER, _('Slot Order (First-Come-First-Served)')),
        (RANDOM, _('Random Seeding')),
        (RANKED, _('Ranked Seeding')),
        (MANUAL, _('Manual Seeding')),
    ]
    
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='bracket',
        verbose_name=_('Tournament'),
        help_text=_('Tournament this bracket belongs to')
    )
    
    format = models.CharField(
        max_length=50,
        choices=FORMAT_CHOICES,
        default=SINGLE_ELIMINATION,
        verbose_name=_('Bracket Format'),
        help_text=_('Type of bracket structure')
    )
    
    total_rounds = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Rounds'),
        help_text=_('Total number of rounds in bracket')
    )
    
    total_matches = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Matches'),
        help_text=_('Total number of matches in bracket')
    )
    
    bracket_structure = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Bracket Structure'),
        help_text=_('JSONB tree structure metadata for bracket visualization')
    )
    
    seeding_method = models.CharField(
        max_length=30,
        choices=SEEDING_METHOD_CHOICES,
        default=SLOT_ORDER,
        verbose_name=_('Seeding Method'),
        help_text=_('How participants are seeded into bracket')
    )
    
    is_finalized = models.BooleanField(
        default=False,
        verbose_name=_('Is Finalized'),
        help_text=_('Whether bracket is locked and cannot be regenerated')
    )
    
    generated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Generated At'),
        help_text=_('When bracket was initially generated'),
        # Provide default for existing records during migration
        null=True,
        blank=True
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At'),
        help_text=_('Last update timestamp')
    )
    
    class Meta:
        db_table = 'tournament_engine_bracket_bracket'
        verbose_name = _('Bracket')
        verbose_name_plural = _('Brackets')
        indexes = [
            models.Index(fields=['tournament'], name='idx_bracket_tournament'),
            models.Index(fields=['format'], name='idx_bracket_format'),
            GinIndex(fields=['bracket_structure'], name='idx_bracket_structure_gin'),
        ]
    
    def __str__(self) -> str:
        return f"{self.tournament.name} - {self.get_format_display()}"
    
    def get_round_name(self, round_number: int) -> str:
        """
        Get human-readable round name from bracket_structure.
        
        Args:
            round_number: Round number (1-indexed)
        
        Returns:
            Round name (e.g., "Quarter Finals") or default "Round X"
        """
        if not self.bracket_structure or 'rounds' not in self.bracket_structure:
            return f"Round {round_number}"
        
        for round_info in self.bracket_structure.get('rounds', []):
            if round_info.get('round_number') == round_number:
                return round_info.get('round_name', f"Round {round_number}")
        
        return f"Round {round_number}"
    
    @property
    def has_third_place_match(self) -> bool:
        """Check if bracket includes third place playoff"""
        if not self.bracket_structure:
            return False
        return self.bracket_structure.get('third_place_match', False)
    
    @property
    def total_participants(self) -> int:
        """Get total number of participants from bracket_structure"""
        if not self.bracket_structure:
            return 0
        return self.bracket_structure.get('total_participants', 0)


# ===========================
# BracketNode Model
# ===========================

class BracketNode(models.Model):
    """
    Individual bracket position with double-linked list navigation.
    
    Navigation Structure:
    - parent_node: Next match where winner advances
    - child1_node, child2_node: Previous matches where winners come from
    - parent_slot: Which participant slot in parent match (1 or 2)
    
    Example (4-team single elimination):
    ```
    Round 1 (Semi Finals)     Round 2 (Finals)
    ┌─────────┐
    │ Node 1  │───┐
    └─────────┘   │       ┌─────────┐
                  ├──────>│ Node 3  │
    ┌─────────┐   │       └─────────┘
    │ Node 2  │───┘
    └─────────┘
    
    Node 1: parent_node=Node 3, parent_slot=1
    Node 2: parent_node=Node 3, parent_slot=2
    Node 3: child1_node=Node 1, child2_node=Node 2
    ```
    """
    
    # Bracket type choices
    MAIN = 'main'
    LOSERS = 'losers'
    THIRD_PLACE = 'third-place'
    
    BRACKET_TYPE_CHOICES = [
        (MAIN, _('Main Bracket')),
        (LOSERS, _('Losers Bracket')),
        (THIRD_PLACE, _('Third Place Playoff')),
        # group-1, group-2, etc. also valid (validated by CHECK constraint)
    ]
    
    bracket = models.ForeignKey(
        Bracket,
        on_delete=models.CASCADE,
        related_name='nodes',
        verbose_name=_('Bracket'),
        help_text=_('Bracket this node belongs to')
    )
    
    position = models.PositiveIntegerField(
        verbose_name=_('Position'),
        help_text=_('Sequential position in bracket (1-indexed)')
    )
    
    round_number = models.PositiveIntegerField(
        verbose_name=_('Round Number'),
        help_text=_('Round number (1 = first round)')
    )
    
    match_number_in_round = models.PositiveIntegerField(
        verbose_name=_('Match Number in Round'),
        help_text=_('Match number within this round (1-indexed)')
    )
    
    match = models.OneToOneField(
        'tournaments.Match',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bracket_node',
        verbose_name=_('Match'),
        help_text=_('Associated match for this bracket position')
    )
    
    # Participant tracking (denormalized for performance)
    participant1_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Participant 1 ID'),
        help_text=_('Team or User ID for participant 1')
    )
    
    participant1_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Participant 1 Name'),
        help_text=_('Cached name for participant 1')
    )
    
    participant2_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Participant 2 ID'),
        help_text=_('Team or User ID for participant 2')
    )
    
    participant2_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Participant 2 Name'),
        help_text=_('Cached name for participant 2')
    )
    
    winner_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Winner ID'),
        help_text=_('Team or User ID of winner')
    )
    
    # Double-linked list navigation
    parent_node = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Parent Node'),
        help_text=_('Next match where winner advances')
    )
    
    parent_slot = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Parent Slot'),
        help_text=_('Which participant slot in parent match (1 or 2)')
    )
    
    child1_node = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('Child 1 Node'),
        help_text=_('Previous match for participant 1')
    )
    
    child2_node = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('Child 2 Node'),
        help_text=_('Previous match for participant 2')
    )
    
    is_bye = models.BooleanField(
        default=False,
        verbose_name=_('Is Bye'),
        help_text=_('Whether this is a bye match (participant advances without playing)')
    )
    
    bracket_type = models.CharField(
        max_length=50,
        default=MAIN,
        verbose_name=_('Bracket Type'),
        help_text=_('Bracket type (main, losers, third-place, or group-N)')
    )
    
    class Meta:
        db_table = 'tournament_engine_bracket_bracketnode'
        verbose_name = _('Bracket Node')
        verbose_name_plural = _('Bracket Nodes')
        indexes = [
            models.Index(fields=['bracket'], name='idx_bracketnode_bracket'),
            models.Index(fields=['bracket', 'round_number'], name='idx_bracketnode_round'),
            models.Index(fields=['position'], name='idx_bracketnode_position'),
            models.Index(fields=['match'], name='idx_bracketnode_match'),
            models.Index(fields=['parent_node'], name='idx_bracketnode_parent'),
            models.Index(fields=['bracket', 'child1_node', 'child2_node'], name='idx_bracketnode_children'),
            models.Index(fields=['participant1_id', 'participant2_id'], name='idx_bracketnode_participants'),
        ]
        constraints = [
            # Unique position per bracket
            models.UniqueConstraint(
                fields=['bracket', 'position'],
                name='uq_bracketnode_bracket_position'
            ),
            # Round number must be positive
            CheckConstraint(
                check=Q(round_number__gt=0),
                name='chk_bracketnode_round_positive'
            ),
            # Match number in round must be positive
            CheckConstraint(
                check=Q(match_number_in_round__gt=0),
                name='chk_bracketnode_match_number_positive'
            ),
            # Parent slot must be 1 or 2 (if set)
            CheckConstraint(
                check=Q(parent_slot__isnull=True) | Q(parent_slot__in=[1, 2]),
                name='chk_bracketnode_parent_slot'
            ),
        ]
    
    def __str__(self) -> str:
        return (
            f"{self.bracket.tournament.name} - "
            f"R{self.round_number} M{self.match_number_in_round} "
            f"(Pos {self.position})"
        )
    
    @property
    def has_both_participants(self) -> bool:
        """Check if both participants are assigned"""
        return self.participant1_id is not None and self.participant2_id is not None
    
    @property
    def has_winner(self) -> bool:
        """Check if winner is determined"""
        return self.winner_id is not None
    
    @property
    def is_ready_for_match(self) -> bool:
        """Check if node is ready for match to be created/played"""
        if self.is_bye:
            return False  # Bye matches don't need to be played
        return self.has_both_participants and not self.has_winner
    
    def get_winner_name(self) -> Optional[str]:
        """Get winner name based on winner_id"""
        if self.winner_id is None:
            return None
        
        if self.winner_id == self.participant1_id:
            return self.participant1_name
        elif self.winner_id == self.participant2_id:
            return self.participant2_name
        
        return None
    
    def get_loser_id(self) -> Optional[int]:
        """Get loser ID based on winner_id"""
        if self.winner_id is None:
            return None
        
        if self.winner_id == self.participant1_id:
            return self.participant2_id
        elif self.winner_id == self.participant2_id:
            return self.participant1_id
        
        return None
    
    def advance_winner_to_parent(self) -> bool:
        """
        Advance winner to parent node's appropriate slot.
        
        Returns:
            True if winner was advanced, False otherwise
        """
        if not self.has_winner or not self.parent_node or self.parent_slot is None:
            return False
        
        winner_name = self.get_winner_name()
        
        if self.parent_slot == 1:
            self.parent_node.participant1_id = self.winner_id
            self.parent_node.participant1_name = winner_name
        elif self.parent_slot == 2:
            self.parent_node.participant2_id = self.winner_id
            self.parent_node.participant2_name = winner_name
        
        self.parent_node.save()
        return True
