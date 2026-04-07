"""
Bracket and BracketNode models for tournament bracket structures.

Canonical location: apps.brackets.models (Phase 6 extraction).

Bracket Formats:
- Single Elimination: Standard knockout tournament
- Double Elimination: Winners + Losers brackets with grand finals
- Round Robin: All participants play each other
- Swiss: Swiss system pairing
- Group Stage: Groups with knockout phase

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

from apps.common.models import TimestampedModel, SoftDeleteModel
from apps.common.managers import SoftDeleteManager


# ===========================
# Bracket Model
# ===========================

class Bracket(TimestampedModel):
    """
    Container for tournament bracket structure.

    Stores overall bracket configuration and metadata.
    Individual bracket positions/matches are stored in BracketNode model.
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
        null=True,
        blank=True
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At'),
        help_text=_('Last update timestamp')
    )

    class Meta:
        app_label = 'brackets'
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
        """Get human-readable round name from bracket_structure."""
        if not self.bracket_structure or 'rounds' not in self.bracket_structure:
            return self._compute_round_name(round_number, self.total_rounds or 0)

        rounds_data = self.bracket_structure.get('rounds', [])

        if isinstance(rounds_data, list):
            for round_info in rounds_data:
                if isinstance(round_info, dict):
                    rn = round_info.get('round_number') or round_info.get('round')
                    if rn == round_number:
                        return round_info.get('round_name') or round_info.get('name') or f"Round {round_number}"
            # Fallback: compute from total_rounds
            return self._compute_round_name(round_number, self.total_rounds or 0)

        if isinstance(rounds_data, dict):
            upper = rounds_data.get('upper', [])
            lower = rounds_data.get('lower', [])
            grand_final = rounds_data.get('grand_final', [])

            offset = 0
            for rd in upper:
                if isinstance(rd, dict):
                    offset += 1
                    if offset == round_number:
                        return rd.get('name') or rd.get('round_name') or f"Round {round_number}"
            for rd in lower:
                if isinstance(rd, dict):
                    offset += 1
                    if offset == round_number:
                        return rd.get('name') or rd.get('round_name') or f"Round {round_number}"
            for rd in grand_final:
                if isinstance(rd, dict):
                    offset += 1
                    if offset == round_number:
                        return rd.get('name') or rd.get('round_name') or f"Round {round_number}"

        return self._compute_round_name(round_number, self.total_rounds or 0)

    @staticmethod
    def _compute_round_name(round_number: int, total_rounds: int = 0) -> str:
        """Compute round name from position relative to finals."""
        if total_rounds <= 0:
            return f"Round {round_number}"
        rounds_from_end = total_rounds - round_number
        if rounds_from_end == 0:
            return "Finals"
        elif rounds_from_end == 1:
            return "Semi Finals"
        elif rounds_from_end == 2:
            return "Quarter Finals"
        elif rounds_from_end == 3:
            return "Round of 16"
        elif rounds_from_end == 4:
            return "Round of 32"
        else:
            return f"Round {round_number}"

    @property
    def has_third_place_match(self) -> bool:
        if not self.bracket_structure:
            return False
        return self.bracket_structure.get('third_place_match', False)

    @property
    def total_participants(self) -> int:
        if not self.bracket_structure:
            return 0
        return self.bracket_structure.get('total_participants', 0)


# ===========================
# BracketNode Model
# ===========================

class BracketNode(SoftDeleteModel):
    """
    Individual bracket position with double-linked list navigation.
    """

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    MAIN = 'main'
    LOSERS = 'losers'
    THIRD_PLACE = 'third-place'

    BRACKET_TYPE_CHOICES = [
        (MAIN, _('Main Bracket')),
        (LOSERS, _('Losers Bracket')),
        (THIRD_PLACE, _('Third Place Playoff')),
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

    participant1_id = models.IntegerField(null=True, blank=True, verbose_name=_('Participant 1 ID'))
    participant1_name = models.CharField(max_length=100, blank=True, verbose_name=_('Participant 1 Name'))
    participant2_id = models.IntegerField(null=True, blank=True, verbose_name=_('Participant 2 ID'))
    participant2_name = models.CharField(max_length=100, blank=True, verbose_name=_('Participant 2 Name'))
    winner_id = models.IntegerField(null=True, blank=True, verbose_name=_('Winner ID'))

    parent_node = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='children', verbose_name=_('Parent Node')
    )
    parent_slot = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_('Parent Slot'))

    child1_node = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name=_('Child 1 Node')
    )
    child2_node = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name=_('Child 2 Node')
    )

    is_bye = models.BooleanField(default=False, verbose_name=_('Is Bye'))

    bracket_type = models.CharField(
        max_length=50, default=MAIN,
        verbose_name=_('Bracket Type')
    )

    class Meta:
        app_label = 'brackets'
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
            models.UniqueConstraint(fields=['bracket', 'position'], name='uq_bracketnode_bracket_position'),
            CheckConstraint(condition=Q(round_number__gt=0), name='chk_bracketnode_round_positive'),
            CheckConstraint(condition=Q(match_number_in_round__gt=0), name='chk_bracketnode_match_number_positive'),
            CheckConstraint(condition=Q(parent_slot__isnull=True) | Q(parent_slot__in=[1, 2]), name='chk_bracketnode_parent_slot'),
        ]

    def __str__(self) -> str:
        return (
            f"{self.bracket.tournament.name} - "
            f"R{self.round_number} M{self.match_number_in_round} "
            f"(Pos {self.position})"
        )

    @property
    def has_both_participants(self) -> bool:
        return self.participant1_id is not None and self.participant2_id is not None

    @property
    def has_winner(self) -> bool:
        return self.winner_id is not None

    @property
    def is_ready_for_match(self) -> bool:
        if self.is_bye:
            return False
        return self.has_both_participants and not self.has_winner

    def get_winner_name(self) -> Optional[str]:
        if self.winner_id is None:
            return None
        if self.winner_id == self.participant1_id:
            return self.participant1_name
        elif self.winner_id == self.participant2_id:
            return self.participant2_name
        return None

    def get_loser_id(self) -> Optional[int]:
        if self.winner_id is None:
            return None
        if self.winner_id == self.participant1_id:
            return self.participant2_id
        elif self.winner_id == self.participant2_id:
            return self.participant1_id
        return None

    def advance_winner_to_parent(self) -> bool:
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
