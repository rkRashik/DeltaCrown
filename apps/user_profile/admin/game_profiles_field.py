"""
Game Profiles JSON Field and Widget for Django Admin

Provides user-friendly game_profiles editing in admin with:
- Pretty JSON formatting
- Schema validation
- Visual feedback
"""

from django import forms
from django.core.exceptions import ValidationError
import json
from datetime import datetime


VALID_GAME_KEYS = [
    'valorant', 'lol', 'mlbb', 'pubg_mobile', 'free_fire', 
    'codm', 'efootball', 'cs2', 'dota2', 'fifa', 'apex',
]


class GameProfilesWidget(forms.Textarea):
    """Custom widget for pretty JSON display"""
    
    template_name = 'admin/widgets/game_profiles_widget.html'
    
    def __init__(self, attrs=None):
        default_attrs = {
            'rows': 20,
            'cols': 80,
            'style': 'font-family: monospace; background: #f8f9fa;',
            'placeholder': '[\n  {\n    "game": "valorant",\n    "ign": "Player#TAG",\n    "rank": "Immortal",\n    "verified": false\n  }\n]'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
    
    def format_value(self, value):
        """Pretty-print JSON for display"""
        if value is None or value == '':
            return '[]'
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        if isinstance(value, (list, dict)):
            return json.dumps(value, indent=2, ensure_ascii=False)
        return value


class GameProfilesField(forms.JSONField):
    """Custom field with validation for game profiles schema"""
    
    widget = GameProfilesWidget
    
    def __init__(self, **kwargs):
        kwargs.setdefault('help_text', '''
            <strong>Game Profiles Schema:</strong><br>
            Each entry must have:<br>
            - <code>game</code>: Game identifier (valorant, lol, mlbb, etc.)<br>
            - <code>ign</code>: In-game name<br>
            - <code>rank</code> (optional): Player rank/tier<br>
            - <code>region</code> (optional): Server region<br>
            - <code>verified</code>: Boolean (default: false)<br>
            - <code>updated_at</code>: ISO timestamp (auto-set if missing)
        ''')
        super().__init__(**kwargs)
    
    def to_python(self, value):
        """Parse and validate JSON"""
        if value in self.empty_values:
            return []
        
        # Handle already-parsed value
        if isinstance(value, (list, dict)):
            data = value
        else:
            # Parse string
            try:
                data = json.loads(value)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON: {e}")
        
        # Ensure list
        if not isinstance(data, list):
            raise ValidationError("Game profiles must be a JSON array/list")
        
        # Validate each profile
        validated = []
        for idx, profile in enumerate(data):
            if not isinstance(profile, dict):
                raise ValidationError(f"Profile #{idx + 1} must be a JSON object")
            
            # Required fields
            if 'game' not in profile:
                raise ValidationError(f"Profile #{idx + 1} missing required 'game' field")
            if 'ign' not in profile:
                raise ValidationError(f"Profile #{idx + 1} missing required 'ign' field")
            
            # Normalize
            normalized = {
                'game': profile['game'].lower() if isinstance(profile['game'], str) else profile['game'],
                'ign': profile['ign'],
                'rank': profile.get('rank', ''),
                'region': profile.get('region', ''),
                'verified': bool(profile.get('verified', False)),
                'updated_at': profile.get('updated_at', datetime.utcnow().isoformat() + 'Z'),
            }
            
            # Copy any extra metadata
            for key in profile:
                if key not in normalized:
                    normalized[key] = profile[key]
            
            validated.append(normalized)
        
        return validated
    
    def prepare_value(self, value):
        """Prepare for display in widget"""
        if value is None or value == '':
            return []
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return []
        return value
