"""
Group Stage Serializers (Epic 3.2)

Provides UI/API-ready serialization for group stage data.
Supports group editor UI with participant management and standings display.
"""

from typing import List, Dict, Any
from apps.tournaments.models import GroupStage, Group, GroupStanding, Match


class StandingSerializer:
    """Serializer for individual group standing."""
    
    @staticmethod
    def serialize(standing: GroupStanding) -> Dict[str, Any]:
        """
        Serialize a GroupStanding instance.
        
        Args:
            standing: GroupStanding instance
        
        Returns:
            dict with standing data for API/UI consumption
        """
        participant_id = standing.team_id if standing.team_id else standing.user_id
        participant_type = "team" if standing.team_id else "user"
        
        return {
            "id": standing.id,
            "participant_id": participant_id,
            "participant_type": participant_type,
            "rank": standing.rank,
            "points": float(standing.points),
            "matches_played": standing.matches_won + standing.matches_drawn + standing.matches_lost,
            "matches_won": standing.matches_won,
            "matches_drawn": standing.matches_drawn,
            "matches_lost": standing.matches_lost,
            "goals_for": standing.goals_for,
            "goals_against": standing.goals_against,
            "goal_difference": standing.goal_difference,
            "form": [],  # TODO: Last 5 results
        }


class GroupSerializer:
    """Serializer for individual group."""
    
    @staticmethod
    def serialize(group: Group, include_standings: bool = True, include_matches: bool = True) -> Dict[str, Any]:
        """
        Serialize a Group instance.
        
        Args:
            group: Group instance
            include_standings: Whether to include standings list
            include_matches: Whether to include upcoming matches
        
        Returns:
            dict with group data for API/UI consumption
        """
        data = {
            "id": group.id,
            "name": group.name,
            "display_order": group.display_order,
            "max_participants": group.max_participants,
            "current_participants": group.standings.filter(is_deleted=False).count(),
            "is_full": group.is_full,
            "advancement_count": group.advancement_count,
        }
        
        if include_standings:
            standings = group.standings.filter(is_deleted=False).order_by('rank')
            data["standings"] = [StandingSerializer.serialize(s) for s in standings]
        
        if include_matches:
            # Get upcoming matches for this group
            upcoming_matches = Match.objects.filter(
                tournament=group.tournament,
                lobby_info__group_id=group.id,
                state__in=[Match.SCHEDULED, Match.CHECK_IN, Match.READY, Match.LIVE]
            ).order_by('round_number', 'match_number')[:5]
            
            data["upcoming_matches"] = [
                {
                    "id": m.id,
                    "participant1_id": m.participant1_id,
                    "participant2_id": m.participant2_id,
                    "round_number": m.round_number,
                    "match_number": m.match_number,
                    "state": m.state,
                }
                for m in upcoming_matches
            ]
        
        return data


class GroupStageSerializer:
    """Serializer for group stage with all groups and participants."""
    
    @staticmethod
    def serialize(
        stage: GroupStage,
        include_standings: bool = True,
        include_matches: bool = True
    ) -> Dict[str, Any]:
        """
        Serialize a GroupStage instance.
        
        Provides comprehensive group stage data for UI editor:
        - Group list with participants
        - Current standings
        - Upcoming matches
        - Advancement configuration
        
        Args:
            stage: GroupStage instance
            include_standings: Whether to include standings
            include_matches: Whether to include match data
        
        Returns:
            dict with complete group stage data
        
        Example:
            >>> stage = GroupStage.objects.get(id=1)
            >>> data = GroupStageSerializer.serialize(stage)
            >>> data["groups"][0]["standings"]
            [{'participant_id': 5, 'rank': 1, ...}, ...]
        """
        groups = Group.objects.filter(
            tournament=stage.tournament
        ).prefetch_related('standings').order_by('display_order')
        
        return {
            "id": stage.id,
            "name": stage.name,
            "tournament_id": stage.tournament.id,
            "num_groups": stage.num_groups,
            "group_size": stage.group_size,
            "format": stage.format,
            "state": stage.state,
            "advancement_count_per_group": stage.advancement_count_per_group,
            "total_participants": stage.total_participants,
            "total_advancing": stage.total_advancing,
            "config": stage.config,
            "groups": [
                GroupSerializer.serialize(g, include_standings, include_matches)
                for g in groups
            ],
        }
    
    @staticmethod
    def serialize_for_drag_drop(stage: GroupStage) -> Dict[str, Any]:
        """
        Serialize group stage for drag-and-drop participant assignment UI.
        
        Returns simplified structure optimized for drag-drop operations:
        - Participant pools
        - Group capacities
        - Assignment constraints
        
        Args:
            stage: GroupStage instance
        
        Returns:
            dict optimized for drag-drop UI
        """
        from apps.tournaments.models import Registration
        
        # Get all registered participants (confirmed registrations)
        registrations = Registration.objects.filter(
            tournament=stage.tournament,
            status=Registration.CONFIRMED
        )
        
        # Get participants already assigned to groups
        assigned_participants = set()
        groups_data = []
        
        for group in Group.objects.filter(tournament=stage.tournament).order_by('display_order'):
            standings = list(group.standings.filter(is_deleted=False))
            participant_ids = [
                s.team_id if s.team_id else s.user_id
                for s in standings
            ]
            assigned_participants.update(participant_ids)
            
            groups_data.append({
                "id": group.id,
                "name": group.name,
                "participants": participant_ids,
                "max_participants": group.max_participants,
                "current_count": len(participant_ids),
                "slots_remaining": group.max_participants - len(participant_ids),
            })
        
        # Unassigned participants pool
        all_participant_ids = {r.team_id if r.team_id else r.user_id for r in registrations}
        unassigned = list(all_participant_ids - assigned_participants)
        
        return {
            "stage_id": stage.id,
            "groups": groups_data,
            "unassigned_participants": unassigned,
            "total_slots": stage.total_participants,
            "slots_filled": len(assigned_participants),
            "can_auto_balance": len(unassigned) > 0,
        }
