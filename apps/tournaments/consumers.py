"""
Real-time Match Updates via WebSocket

Provides live match score updates and state changes using Django Channels.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from apps.tournaments.models import Match, Tournament


class MatchConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time match updates"""
    
    async def connect(self):
        self.match_id = self.scope['url_route']['kwargs']['match_id']
        self.match_group_name = f'match_{self.match_id}'
        
        # Join match group
        await self.channel_layer.group_add(
            self.match_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current match state
        match_data = await self.get_match_data()
        await self.send(text_data=json.dumps({
            'type': 'match_state',
            'match': match_data
        }))
    
    async def disconnect(self, close_code):
        # Leave match group
        await self.channel_layer.group_discard(
            self.match_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming messages (heartbeat, etc.)"""
        data = json.loads(text_data)
        
        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
    
    async def match_update(self, event):
        """Handler for match update events from group"""
        await self.send(text_data=json.dumps({
            'type': 'match_update',
            'match': event['match_data']
        }))
    
    async def score_update(self, event):
        """Handler for score update events"""
        await self.send(text_data=json.dumps({
            'type': 'score_update',
            'score': event['score_data']
        }))
    
    @database_sync_to_async
    def get_match_data(self):
        """Fetch match data from database"""
        try:
            match = Match.objects.select_related(
                'tournament', 'bracket'
            ).get(id=self.match_id)
            
            return {
                'id': match.id,
                'state': match.state,
                'participant1_name': match.participant1_name,
                'participant2_name': match.participant2_name,
                'participant1_score': match.participant1_score,
                'participant2_score': match.participant2_score,
                'winner_id': match.winner_id,
                'scheduled_time': match.scheduled_time.isoformat() if match.scheduled_time else None,
                'started_at': match.started_at.isoformat() if match.started_at else None,
                'completed_at': match.completed_at.isoformat() if match.completed_at else None,
            }
        except Match.DoesNotExist:
            return None


class TournamentBracketConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time bracket updates"""
    
    async def connect(self):
        self.tournament_slug = self.scope['url_route']['kwargs']['tournament_slug']
        self.bracket_group_name = f'tournament_bracket_{self.tournament_slug}'
        
        # Join bracket group
        await self.channel_layer.group_add(
            self.bracket_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current bracket state
        bracket_data = await self.get_bracket_data()
        await self.send(text_data=json.dumps({
            'type': 'bracket_state',
            'bracket': bracket_data
        }))
    
    async def disconnect(self, close_code):
        # Leave bracket group
        await self.channel_layer.group_discard(
            self.bracket_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming messages"""
        data = json.loads(text_data)
        
        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
    
    async def bracket_update(self, event):
        """Handler for bracket update events"""
        await self.send(text_data=json.dumps({
            'type': 'bracket_update',
            'matches': event['matches_data']
        }))
    
    async def match_completed(self, event):
        """Handler for match completion events"""
        await self.send(text_data=json.dumps({
            'type': 'match_completed',
            'match_id': event['match_id'],
            'winner_id': event['winner_id']
        }))
    
    @database_sync_to_async
    def get_bracket_data(self):
        """Fetch bracket data from database"""
        try:
            tournament = Tournament.objects.get(slug=self.tournament_slug)
            
            if not hasattr(tournament, 'bracket'):
                return None
            
            matches = Match.objects.filter(
                tournament=tournament
            ).order_by('round_number', 'match_number')
            
            return {
                'tournament_id': tournament.id,
                'format': tournament.bracket.format,
                'total_rounds': tournament.bracket.total_rounds,
                'matches': [
                    {
                        'id': m.id,
                        'round': m.round_number,
                        'match_number': m.match_number,
                        'p1_name': m.participant1_name,
                        'p2_name': m.participant2_name,
                        'p1_score': m.participant1_score,
                        'p2_score': m.participant2_score,
                        'state': m.state,
                        'winner_id': m.winner_id,
                    }
                    for m in matches
                ]
            }
        except Tournament.DoesNotExist:
            return None


# Signal handlers to broadcast updates
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@receiver(post_save, sender=Match)
def broadcast_match_update(sender, instance, created, **kwargs):
    """Broadcast match updates to WebSocket clients"""
    channel_layer = get_channel_layer()
    
    # Broadcast to match-specific group
    match_group = f'match_{instance.id}'
    async_to_sync(channel_layer.group_send)(
        match_group,
        {
            'type': 'match_update',
            'match_data': {
                'id': instance.id,
                'state': instance.state,
                'participant1_score': instance.participant1_score,
                'participant2_score': instance.participant2_score,
                'winner_id': instance.winner_id,
            }
        }
    )
    
    # Broadcast to tournament bracket group
    bracket_group = f'tournament_bracket_{instance.tournament.slug}'
    async_to_sync(channel_layer.group_send)(
        bracket_group,
        {
            'type': 'bracket_update',
            'matches_data': [{
                'id': instance.id,
                'state': instance.state,
                'p1_score': instance.participant1_score,
                'p2_score': instance.participant2_score,
                'winner_id': instance.winner_id,
            }]
        }
    )
    
    # If match completed, send special event
    if instance.state == Match.COMPLETED:
        async_to_sync(channel_layer.group_send)(
            bracket_group,
            {
                'type': 'match_completed',
                'match_id': instance.id,
                'winner_id': instance.winner_id,
            }
        )
