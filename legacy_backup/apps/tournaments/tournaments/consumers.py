"""
WebSocket Consumers for Real-time Tournament Features
Handles chat, live updates, and notifications
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class TournamentChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for tournament chat room
    Allows real-time messaging between tournament participants
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.tournament_slug = self.scope['url_route']['kwargs']['slug']
        self.room_group_name = f'tournament_chat_{self.tournament_slug}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'system',
            'message': 'Connected to tournament chat',
            'online_count': await self.get_online_count()
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'ping':
                # Keep-alive ping
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid message format'
            }))
    
    async def handle_chat_message(self, data):
        """Process and broadcast chat message"""
        user = self.scope.get('user')
        
        if isinstance(user, AnonymousUser):
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'You must be logged in to send messages'
            }))
            return
        
        message = data.get('message', '').strip()
        
        if not message:
            return
        
        # Get user info
        user_info = await self.get_user_info(user)
        
        # Broadcast to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'username': user.username,
                'user_id': user.id,
                'team': user_info.get('team'),
                'avatar': user_info.get('avatar'),
                'message': message,
                'timestamp': data.get('timestamp')
            }
        )
    
    async def chat_message(self, event):
        """Send chat message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'username': event['username'],
            'user_id': event['user_id'],
            'team': event['team'],
            'avatar': event['avatar'],
            'message': event['message'],
            'timestamp': event['timestamp']
        }))
    
    @database_sync_to_async
    def get_user_info(self, user):
        """Get user team and avatar information"""
        from apps.teams.models import Team
        
        info = {
            'team': None,
            'avatar': None
        }
        
        # Check if user has a team in this tournament
        try:
            team = Team.objects.filter(
                captain=user
            ).first() or Team.objects.filter(
                players=user
            ).first()
            
            if team:
                info['team'] = team.name
        except Exception:
            pass
        
        # Get avatar if available
        if hasattr(user, 'profile') and hasattr(user.profile, 'avatar'):
            if user.profile.avatar:
                info['avatar'] = user.profile.avatar.url
        
        return info
    
    @database_sync_to_async
    def get_online_count(self):
        """Get count of online users (placeholder)"""
        # In production, track this with Redis or database
        return 1


class TournamentLiveUpdatesConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for live tournament updates
    Broadcasts match results, bracket updates, etc.
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.tournament_slug = self.scope['url_route']['kwargs']['slug']
        self.room_group_name = f'tournament_updates_{self.tournament_slug}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming messages"""
        # This consumer is mainly for broadcasting, not receiving
        pass
    
    async def tournament_update(self, event):
        """Send tournament update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': event['update_type'],
            'data': event['data'],
            'timestamp': event.get('timestamp')
        }))
