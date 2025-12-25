"""
Game Passport Validators (GP-0)

Per-game identity validation and normalization.

Each validator:
1. Validates in_game_name format
2. Generates normalized identity_key for uniqueness
3. Provides error messages
"""

import re
from typing import Tuple, Optional
from abc import ABC, abstractmethod


class BaseGameValidator(ABC):
    """Base class for game-specific validators"""
    
    game_slug: str = ""
    game_name: str = ""
    format_example: str = ""
    
    @abstractmethod
    def is_valid_ign(self, ign: str) -> bool:
        """Check if IGN format is valid"""
        pass
    
    @abstractmethod
    def generate_identity_key(self, ign: str, metadata: dict = None) -> str:
        """Generate normalized identity_key for uniqueness"""
        pass
    
    def get_error_message(self) -> str:
        """Get validation error message"""
        return f"Invalid {self.game_name} identity. Expected format: {self.format_example}"
    
    def validate_and_normalize(self, ign: str, metadata: dict = None) -> Tuple[bool, str, Optional[str]]:
        """
        Validate IGN and generate identity_key.
        
        Returns:
            Tuple[bool, str, Optional[str]]: (is_valid, identity_key or error_msg, error_msg or None)
        """
        if not self.is_valid_ign(ign):
            return False, self.get_error_message(), self.get_error_message()
        
        identity_key = self.generate_identity_key(ign, metadata)
        return True, identity_key, None


class ValorantValidator(BaseGameValidator):
    """VALORANT Riot ID validator"""
    
    game_slug = "valorant"
    game_name = "VALORANT"
    format_example = "PlayerName#TAG (3-16 chars, #, 3-5 digit/letter tag)"
    
    def is_valid_ign(self, ign: str) -> bool:
        """Riot ID must match: Name#TAG"""
        if not ign or len(ign) > 100:
            return False
        # Name: 3-16 alphanumeric + spaces, Tag: 3-5 alphanumeric
        pattern = r'^[a-zA-Z0-9\s]{3,16}#[a-zA-Z0-9]{3,5}$'
        return bool(re.match(pattern, ign))
    
    def generate_identity_key(self, ign: str, metadata: dict = None) -> str:
        """Lowercase name#tag, preserve casing for display"""
        return ign.lower().strip()


class CS2Validator(BaseGameValidator):
    """Counter-Strike 2 Steam ID validator"""
    
    game_slug = "cs2"
    game_name = "Counter-Strike 2"
    format_example = "76561198012345678 (17-digit Steam ID64)"
    
    def is_valid_ign(self, ign: str) -> bool:
        """Steam ID64: 17 digits starting with 7656"""
        return ign.isdigit() and len(ign) == 17 and ign.startswith('7656')
    
    def generate_identity_key(self, ign: str, metadata: dict = None) -> str:
        """Steam ID is already normalized"""
        return ign.strip()


class Dota2Validator(BaseGameValidator):
    """Dota 2 Steam ID validator"""
    
    game_slug = "dota2"
    game_name = "Dota 2"
    format_example = "76561198012345678 (17-digit Steam ID64)"
    
    def is_valid_ign(self, ign: str) -> bool:
        """Steam ID64: 17 digits starting with 7656"""
        return ign.isdigit() and len(ign) == 17 and ign.startswith('7656')
    
    def generate_identity_key(self, ign: str, metadata: dict = None) -> str:
        """Steam ID is already normalized"""
        return ign.strip()


class MLBBValidator(BaseGameValidator):
    """Mobile Legends: Bang Bang validator"""
    
    game_slug = "mlbb"
    game_name = "Mobile Legends"
    format_example = "123456789 (9-10 digit Game ID) + Zone ID in metadata"
    
    def is_valid_ign(self, ign: str) -> bool:
        """MLBB Game ID: 9-10 digits"""
        return ign.isdigit() and 9 <= len(ign) <= 10
    
    def generate_identity_key(self, ign: str, metadata: dict = None) -> str:
        """Combine game_id + zone_id for uniqueness"""
        zone_id = metadata.get('zone_id', '') if metadata else ''
        if zone_id:
            return f"{ign.strip()}:{zone_id}"
        return ign.strip()


class PUBGMValidator(BaseGameValidator):
    """PUBG Mobile validator"""
    
    game_slug = "pubgm"
    game_name = "PUBG Mobile"
    format_example = "5123456789 (10-digit Character ID)"
    
    def is_valid_ign(self, ign: str) -> bool:
        """PUBGM Character ID: 10 digits starting with 5"""
        return ign.isdigit() and len(ign) == 10 and ign.startswith('5')
    
    def generate_identity_key(self, ign: str, metadata: dict = None) -> str:
        """Character ID is already normalized"""
        return ign.strip()


class FreeFireValidator(BaseGameValidator):
    """Free Fire validator"""
    
    game_slug = "freefire"
    game_name = "Free Fire"
    format_example = "1234567890 (10-digit Player ID)"
    
    def is_valid_ign(self, ign: str) -> bool:
        """Free Fire Player ID: 10 digits"""
        return ign.isdigit() and len(ign) == 10
    
    def generate_identity_key(self, ign: str, metadata: dict = None) -> str:
        """Player ID is already normalized"""
        return ign.strip()


class CODMValidator(BaseGameValidator):
    """Call of Duty Mobile validator"""
    
    game_slug = "codm"
    game_name = "Call of Duty Mobile"
    format_example = "6000000000 (10-digit UID starting with 6)"
    
    def is_valid_ign(self, ign: str) -> bool:
        """CODM UID: 10 digits starting with 6"""
        return ign.isdigit() and len(ign) == 10 and ign.startswith('6')
    
    def generate_identity_key(self, ign: str, metadata: dict = None) -> str:
        """UID is already normalized"""
        return ign.strip()


class EAFCValidator(BaseGameValidator):
    """EA Sports FC validator"""
    
    game_slug = "fc24"
    game_name = "EA Sports FC"
    format_example = "YourEAID (EA Account username)"
    
    def is_valid_ign(self, ign: str) -> bool:
        """EA ID: 3-20 alphanumeric characters"""
        if not ign or not (3 <= len(ign) <= 20):
            return False
        return re.match(r'^[a-zA-Z0-9_-]+$', ign) is not None
    
    def generate_identity_key(self, ign: str, metadata: dict = None) -> str:
        """Lowercase for case-insensitive uniqueness"""
        return ign.lower().strip()


class EFootballValidator(BaseGameValidator):
    """eFootball validator"""
    
    game_slug = "efootball"
    game_name = "eFootball"
    format_example = "PlayerID (alphanumeric, 3-20 chars)"
    
    def is_valid_ign(self, ign: str) -> bool:
        """eFootball ID: 3-20 alphanumeric"""
        if not ign or not (3 <= len(ign) <= 20):
            return False
        return re.match(r'^[a-zA-Z0-9_-]+$', ign) is not None
    
    def generate_identity_key(self, ign: str, metadata: dict = None) -> str:
        """Lowercase for case-insensitive uniqueness"""
        return ign.lower().strip()


class RocketLeagueValidator(BaseGameValidator):
    """Rocket League (Epic Games) validator"""
    
    game_slug = "rocket_league"
    game_name = "Rocket League"
    format_example = "EpicGamesID (alphanumeric, 3-20 chars)"
    
    def is_valid_ign(self, ign: str) -> bool:
        """Epic ID: 3-20 alphanumeric"""
        if not ign or not (3 <= len(ign) <= 20):
            return False
        return re.match(r'^[a-zA-Z0-9_-]+$', ign) is not None
    
    def generate_identity_key(self, ign: str, metadata: dict = None) -> str:
        """Lowercase for case-insensitive uniqueness"""
        return ign.lower().strip()


class R6SiegeValidator(BaseGameValidator):
    """Rainbow Six Siege (Ubisoft) validator"""
    
    game_slug = "r6"
    game_name = "Rainbow Six Siege"
    format_example = "UbisoftUsername (3-20 chars)"
    
    def is_valid_ign(self, ign: str) -> bool:
        """Ubisoft username: 3-20 chars"""
        if not ign or not (3 <= len(ign) <= 20):
            return False
        return re.match(r'^[a-zA-Z0-9_.-]+$', ign) is not None
    
    def generate_identity_key(self, ign: str, metadata: dict = None) -> str:
        """Lowercase for case-insensitive uniqueness"""
        return ign.lower().strip()


class DefaultValidator(BaseGameValidator):
    """Default validator for games without specific rules"""
    
    game_slug = "default"
    game_name = "Game"
    format_example = "In-game name (3-100 chars)"
    
    def is_valid_ign(self, ign: str) -> bool:
        """Generic validation: 3-100 chars"""
        return ign and 3 <= len(ign) <= 100
    
    def generate_identity_key(self, ign: str, metadata: dict = None) -> str:
        """Lowercase and trim"""
        return ign.lower().strip()


class GameValidators:
    """Factory for game-specific validators"""
    
    _validators = {
        'valorant': ValorantValidator(),
        'cs2': CS2Validator(),
        'dota2': Dota2Validator(),
        'mlbb': MLBBValidator(),
        'pubgm': PUBGMValidator(),
        'freefire': FreeFireValidator(),
        'codm': CODMValidator(),
        'fc24': EAFCValidator(),
        'efootball': EFootballValidator(),
        'rocket_league': RocketLeagueValidator(),
        'r6': R6SiegeValidator(),
    }
    
    @classmethod
    def get_validator(cls, game_slug: str) -> BaseGameValidator:
        """Get validator for a specific game"""
        return cls._validators.get(game_slug, DefaultValidator())
    
    @classmethod
    def validate_and_normalize(cls, game_slug: str, ign: str, metadata: dict = None) -> Tuple[bool, str, Optional[str]]:
        """
        Validate IGN and generate identity_key.
        
        Returns:
            Tuple[bool, str, Optional[str]]: (is_valid, identity_key or error_msg, error_msg or None)
        """
        validator = cls.get_validator(game_slug)
        return validator.validate_and_normalize(ign, metadata)
