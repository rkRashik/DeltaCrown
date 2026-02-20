"""
Live Draw WebSocket Consumer (P4-T07)

Handles real-time bracket seeding draws where seeds are revealed
one at a time with dramatic 2-3 second delays.

Flow:
1. Spectators connect to ws/tournament/<id>/draw/
2. Organizer triggers "start_draw" via the consumer
3. Consumer shuffles confirmed registrations, assigns seeds
4. Each seed is broadcast with a staggered delay
5. Draw result is persisted as permanent bracket seeding

Client messages:
  → {"action": "start_draw"}  (organizer only)

Server broadcasts:
  ← {"type": "draw_reveal", "seed": 1, "name": "...", "total": N}
  ← {"type": "draw_complete", "seeds": [...]}
  ← {"type": "draw_status", "status": "waiting"|"in_progress"|"complete"}
"""
import asyncio
import json
import logging
import random
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


class LiveDrawConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for live bracket seed draws."""

    async def connect(self):
        self.tournament_id = self.scope['url_route']['kwargs']['tournament_id']
        self.room_group = f"live_draw_{self.tournament_id}"
        self.user = self.scope.get('user', None)

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

        # Send current draw status
        status = await self._get_draw_status()
        await self.send_json({'type': 'draw_status', 'status': status})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        action = content.get('action')

        if action == 'start_draw':
            # Only organizers can start the draw
            is_organizer = await self._check_is_organizer()
            if not is_organizer:
                await self.send_json({
                    'type': 'error',
                    'message': 'Only the tournament organizer can start the draw.',
                })
                return

            # Start the draw in a background task
            asyncio.ensure_future(self._run_draw())

    # ------------------------------------------------------------------ #
    # Draw Execution
    # ------------------------------------------------------------------ #

    async def _run_draw(self):
        """Execute the live draw with staggered reveals."""
        participants = await self._get_confirmed_participants()
        if not participants:
            await self.channel_layer.group_send(self.room_group, {
                'type': 'draw_event',
                'payload': {'type': 'error', 'message': 'No confirmed participants to draw.'},
            })
            return

        # Shuffle for random seeding
        random.shuffle(participants)

        # Broadcast draw_start
        await self.channel_layer.group_send(self.room_group, {
            'type': 'draw_event',
            'payload': {
                'type': 'draw_start',
                'total': len(participants),
                'tournament_id': self.tournament_id,
            },
        })

        # Reveal each seed with delay
        seeds = []
        for i, participant in enumerate(participants, 1):
            await asyncio.sleep(2.5)  # 2-3 second dramatic delay

            seed_data = {
                'seed': i,
                'name': participant['name'],
                'registration_id': participant['registration_id'],
                'total': len(participants),
            }
            seeds.append(seed_data)

            await self.channel_layer.group_send(self.room_group, {
                'type': 'draw_event',
                'payload': {'type': 'draw_reveal', **seed_data},
            })

        # Persist seeds to database
        await self._persist_seeds(seeds)

        # Broadcast draw_complete
        await self.channel_layer.group_send(self.room_group, {
            'type': 'draw_event',
            'payload': {
                'type': 'draw_complete',
                'seeds': seeds,
                'total': len(seeds),
            },
        })

    # ------------------------------------------------------------------ #
    # Channel Layer Event Handlers
    # ------------------------------------------------------------------ #

    async def draw_event(self, event):
        """Relay draw events to WebSocket clients."""
        await self.send_json(event['payload'])

    # ------------------------------------------------------------------ #
    # Database Helpers
    # ------------------------------------------------------------------ #

    @database_sync_to_async
    def _check_is_organizer(self):
        """Check if current user is the tournament organizer."""
        if not self.user or not self.user.is_authenticated:
            return False
        try:
            from apps.tournaments.models import Tournament
            tournament = Tournament.objects.get(id=self.tournament_id)
            return (
                tournament.organizer_id == self.user.id
                or self.user.is_staff
            )
        except Exception:
            return False

    @database_sync_to_async
    def _get_confirmed_participants(self):
        """Get all confirmed registrations for this tournament."""
        from apps.tournaments.models import Registration
        registrations = Registration.objects.filter(
            tournament_id=self.tournament_id,
            status=Registration.CONFIRMED,
            is_deleted=False,
        ).select_related('user')

        participants = []
        for reg in registrations:
            name = ''
            if reg.user:
                name = reg.user.username
            elif reg.team_id:
                # Attempt to get team name
                try:
                    from apps.organizations.models import Team
                    team = Team.objects.get(id=reg.team_id)
                    name = team.name
                except Exception:
                    name = f"Team #{reg.team_id}"
            else:
                name = f"Registration #{reg.registration_number}"

            participants.append({
                'registration_id': reg.id,
                'name': name,
            })

        return participants

    @database_sync_to_async
    def _persist_seeds(self, seeds):
        """Save drawn seeds to registrations."""
        from apps.tournaments.models import Registration
        for seed_data in seeds:
            Registration.objects.filter(
                id=seed_data['registration_id']
            ).update(seed=seed_data['seed'])

        logger.info(
            "Live draw persisted %d seeds for tournament %s",
            len(seeds), self.tournament_id,
        )

    @database_sync_to_async
    def _get_draw_status(self):
        """Check if a draw has already been completed."""
        from apps.tournaments.models import Registration
        has_seeds = Registration.objects.filter(
            tournament_id=self.tournament_id,
            status=Registration.CONFIRMED,
            seed__isnull=False,
            is_deleted=False,
        ).exists()
        return 'complete' if has_seeds else 'waiting'
