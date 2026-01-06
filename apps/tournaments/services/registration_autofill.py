"""
Registration Auto-Fill Service

Aggressively auto-fills registration forms from user profile and team data.
Provides visual badges and "Update Profile" prompts for missing data.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from django.contrib.auth import get_user_model

User = get_user_model()


@dataclass
class AutoFillField:
    """Represents an auto-filled field with metadata"""
    field_name: str
    value: Any
    source: str  # 'profile', 'team', 'game_account', 'manual'
    confidence: str  # 'high', 'medium', 'low'
    needs_verification: bool = False
    missing: bool = False
    update_url: Optional[str] = None


class RegistrationAutoFillService:
    """
    Service for auto-filling registration forms from user data.
    
    Pulls data from:
    - User profile (name, email, phone, country, etc.)
    - Team data (name, logo, roster, region, etc.)
    - Game accounts (IGN, rank, platform, etc.)
    - Previous registrations
    """
    
    @staticmethod
    def get_autofill_data(user, tournament, team=None) -> Dict[str, AutoFillField]:
        """
        Get all auto-fillable data for a user/team registration.
        
        Args:
            user: User instance
            tournament: Tournament instance
            team: Optional Team instance for team tournaments
            
        Returns:
            Dict mapping field names to AutoFillField objects
        """
        autofill_data = {}
        
        # Solo player fields
        if not team or tournament.participation_type in ['solo', 'both']:
            autofill_data.update(
                RegistrationAutoFillService._get_player_autofill(user, tournament)
            )
        
        # Team fields
        if team:
            autofill_data.update(
                RegistrationAutoFillService._get_team_autofill(user, team, tournament)
            )
        
        # Payment fields
        autofill_data.update(
            RegistrationAutoFillService._get_payment_autofill(user)
        )
        
        return autofill_data
    
    @staticmethod
    def _get_player_autofill(user, tournament) -> Dict[str, AutoFillField]:
        """Get auto-fill data for solo player fields"""
        data = {}
        
        try:
            profile = user.profile
        except:
            profile = None
        
        # Full Name
        if user.first_name and user.last_name:
            data['player_name'] = AutoFillField(
                field_name='player_name',
                value=f"{user.first_name} {user.last_name}",
                source='profile',
                confidence='high'
            )
        elif user.get_full_name():
            data['player_name'] = AutoFillField(
                field_name='player_name',
                value=user.get_full_name(),
                source='profile',
                confidence='medium'
            )
        else:
            data['player_name'] = AutoFillField(
                field_name='player_name',
                value='',
                source='profile',
                confidence='low',
                missing=True,
                update_url='/profile/edit/'
            )
        
        # Email
        data['email'] = AutoFillField(
            field_name='email',
            value=user.email,
            source='profile',
            confidence='high'
        )
        
        # Phone Number
        if profile and profile.phone:
            data['phone'] = AutoFillField(
                field_name='phone',
                value=profile.phone,
                source='profile',
                confidence='high'
            )
        else:
            data['phone'] = AutoFillField(
                field_name='phone',
                value='',
                source='profile',
                confidence='low',
                missing=True,
                update_url='/profile/edit/'
            )
        
        # Age
        if profile and profile.date_of_birth:
            from datetime import date
            age = (date.today() - profile.date_of_birth).days // 365
            data['age'] = AutoFillField(
                field_name='age',
                value=age,
                source='profile',
                confidence='high'
            )
        else:
            data['age'] = AutoFillField(
                field_name='age',
                value='',
                source='profile',
                confidence='low',
                missing=True,
                update_url='/profile/edit/'
            )
        
        # Country
        if profile and profile.country:
            data['country'] = AutoFillField(
                field_name='country',
                value=profile.country,
                source='profile',
                confidence='high'
            )
        else:
            data['country'] = AutoFillField(
                field_name='country',
                value='',
                source='profile',
                confidence='low',
                missing=True,
                update_url='/profile/edit/'
            )
        
        # Game-specific data (IGN, Rank, Platform)
        game_data = RegistrationAutoFillService._get_game_account_data(
            user, tournament.game
        )
        data.update(game_data)
        
        return data
    
    @staticmethod
    def _get_game_account_data(user, game) -> Dict[str, AutoFillField]:
        """
        Get auto-fill data from Game Passports.
        
        PHASE 9A-12: Single source of truth - uses Game Passports instead of PlayerGameAccount.
        """
        data = {}
        
        try:
            from apps.user_profile.services.game_passport_service import GamePassportService
            
            # Get passport for this game
            passport = GamePassportService.get_passport(user, game.slug)
            
            if passport:
                # In-Game Name
                if passport.ign:
                    data['ign'] = AutoFillField(
                        field_name='ign',
                        value=passport.ign,
                        source='game_passport',
                        confidence='high'
                    )
                
                # Player ID (game-specific identity fields)
                # Map identity fields based on game
                identity_field_map = {
                    'valorant': ('riot_id', 'Riot ID'),
                    'counter-strike-2': ('steam_id', 'Steam ID'),
                    'dota-2': ('steam_id', 'Steam ID'),
                    'mobile-legends': ('moonton_id', 'Moonton ID'),
                    'pubg-mobile': ('pubg_id', 'PUBG ID'),
                    'free-fire': ('garena_id', 'Garena ID'),
                    'call-of-duty-mobile': ('activision_id', 'Activision ID'),
                    'efootball': ('konami_id', 'Konami ID'),
                    'ea-sports-fc-26': ('ea_id', 'EA ID'),
                    'rainbow-six-siege': ('ubisoft_username', 'Ubisoft Username'),
                    'rocket-league': ('epic_games_id', 'Epic Games ID'),
                }
                
                if game.slug in identity_field_map:
                    field_name, display_name = identity_field_map[game.slug]
                    field_value = getattr(passport, field_name, None)
                    if field_value:
                        data['player_id'] = AutoFillField(
                            field_name='player_id',
                            value=field_value,
                            source='game_passport',
                            confidence='high'
                        )
                
                # Rank
                if passport.rank:
                    data['rank'] = AutoFillField(
                        field_name='rank',
                        value=passport.rank,
                        source='game_passport',
                        confidence='high'
                    )
                
                # Platform
                if passport.platform:
                    data['platform'] = AutoFillField(
                        field_name='platform',
                        value=passport.platform,
                        source='game_passport',
                        confidence='high'
                    )
                
                # Region
                if passport.region:
                    data['region'] = AutoFillField(
                        field_name='region',
                        value=passport.region,
                        source='game_passport',
                        confidence='high'
                    )
                
                # Server
                if passport.server:
                    data['server'] = AutoFillField(
                        field_name='server',
                        value=passport.server,
                        source='game_passport',
                        confidence='high'
                    )
                
                return data
            
            # No passport found - suggest creating one
            data['ign'] = AutoFillField(
                field_name='ign',
                value='',
                source='game_passport',
                confidence='low',
                missing=True,
                update_url='/settings/#game-passports'
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to get game account data for {user.username}/{game.slug}: {e}")
            pass
        
        return data
    
    @staticmethod
    def _get_team_autofill(user, team, tournament) -> Dict[str, AutoFillField]:
        """Get auto-fill data for team fields"""
        data = {}
        
        # Team Name
        data['team_name'] = AutoFillField(
            field_name='team_name',
            value=team.name,
            source='team',
            confidence='high'
        )
        
        # Team Logo
        if team.logo:
            data['team_logo'] = AutoFillField(
                field_name='team_logo',
                value=team.logo.url,
                source='team',
                confidence='high'
            )
        else:
            data['team_logo'] = AutoFillField(
                field_name='team_logo',
                value='',
                source='team',
                confidence='low',
                missing=True,
                update_url=f'/teams/{team.slug}/edit/'
            )
        
        # Team Region
        if team.region:
            data['team_region'] = AutoFillField(
                field_name='team_region',
                value=team.region,
                source='team',
                confidence='high'
            )
        
        # Captain Info
        try:
            from apps.teams.models import TeamMember
            captain = TeamMember.objects.filter(
                team=team,
                role='captain',
                is_active=True
            ).first()
            
            if captain:
                data['captain_name'] = AutoFillField(
                    field_name='captain_name',
                    value=captain.user.get_full_name() or captain.user.username,
                    source='team',
                    confidence='high'
                )
                
                data['captain_email'] = AutoFillField(
                    field_name='captain_email',
                    value=captain.user.email,
                    source='team',
                    confidence='high'
                )
                
                if hasattr(captain.user, 'profile') and captain.user.profile.phone_number:
                    data['captain_phone'] = AutoFillField(
                        field_name='captain_phone',
                        value=captain.user.profile.phone_number,
                        source='team',
                        confidence='high'
                    )
        except:
            pass
        
        # Roster (team members)
        try:
            from apps.teams.models import TeamMembership
            members = TeamMembership.objects.filter(
                team=team,
                is_active=True
            ).select_related('user').order_by('role', '-joined_at')
            
            roster_data = []
            for member in members:
                roster_data.append({
                    'username': member.user.username,
                    'name': member.user.get_full_name() or member.user.username,
                    'role': member.role,
                    'ign': RegistrationAutoFillService._get_member_ign(
                        member.user, tournament.game
                    )
                })
            
            data['roster'] = AutoFillField(
                field_name='roster',
                value=roster_data,
                source='team',
                confidence='high'
            )
        except:
            pass
        
        return data
    
    @staticmethod
    def _get_member_ign(user, game) -> Optional[str]:
        """
        Get member's IGN for a specific game from Game Passport.
        
        PHASE 9A-12: Single source of truth - uses Game Passports instead of legacy fields.
        """
        try:
            from apps.user_profile.services.game_passport_service import GamePassportService
            
            passport = GamePassportService.get_passport(user, game.slug)
            if passport and passport.ign:
                return passport.ign
            
            # Phase 9A-14: No passport found, return None
            return None
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to get IGN for {user.username}/{game.slug}: {e}")
            return None
    
    @staticmethod
    def _get_payment_autofill(user) -> Dict[str, AutoFillField]:
        """Get auto-fill data for payment fields"""
        data = {}
        
        try:
            profile = user.profile
            
            # Payment Mobile Number (often same as phone)
            if profile.phone_number:
                data['payment_mobile'] = AutoFillField(
                    field_name='payment_mobile',
                    value=profile.phone_number,
                    source='profile',
                    confidence='high',
                    needs_verification=True
                )
        except:
            pass
        
        # Check previous payments for mobile number
        try:
            from apps.tournaments.models import Payment
            recent_payment = Payment.objects.filter(
                registration__user=user,
                mobile_number__isnull=False
            ).order_by('-created_at').first()
            
            if recent_payment and recent_payment.mobile_number:
                data['payment_mobile'] = AutoFillField(
                    field_name='payment_mobile',
                    value=recent_payment.mobile_number,
                    source='previous_payment',
                    confidence='medium',
                    needs_verification=True
                )
        except:
            pass
        
        return data
    
    @staticmethod
    def get_missing_fields(autofill_data: Dict[str, AutoFillField]) -> List[str]:
        """
        Get list of missing field names that need user input.
        
        Args:
            autofill_data: Dict of auto-fill data
            
        Returns:
            List of field names that are missing data
        """
        return [
            field_name
            for field_name, field_data in autofill_data.items()
            if field_data.missing
        ]
    
    @staticmethod
    def get_completion_percentage(autofill_data: Dict[str, AutoFillField]) -> int:
        """
        Calculate what percentage of fields have data.
        
        Args:
            autofill_data: Dict of auto-fill data
            
        Returns:
            Percentage (0-100) of fields with data
        """
        if not autofill_data:
            return 0
        
        total_fields = len(autofill_data)
        filled_fields = sum(
            1 for field in autofill_data.values()
            if not field.missing and field.value
        )
        
        return int((filled_fields / total_fields) * 100)
    
    @staticmethod
    def get_update_prompts(autofill_data: Dict[str, AutoFillField]) -> List[Dict[str, str]]:
        """
        Get list of prompts for missing data with update URLs.
        
        Args:
            autofill_data: Dict of auto-fill data
            
        Returns:
            List of dicts with 'field', 'message', 'url'
        """
        prompts = []
        
        for field_name, field_data in autofill_data.items():
            if field_data.missing and field_data.update_url:
                prompts.append({
                    'field': field_name,
                    'message': f"Add your {field_name.replace('_', ' ')} to auto-fill this field",
                    'url': field_data.update_url
                })
        
        return prompts
