from django.db import models
from django.conf import settings

REGION_CHOICES = [
    ("BD", "Bangladesh"),
    ("SA", "South Asia"),
    ("AS", "Asia (Other)"),
    ("EU", "Europe"),
    ("NA", "North America"),
]

def user_avatar_path(instance, filename):
    return f"user_avatars/{instance.user_id}/{filename}"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=80)
    region = models.CharField(max_length=2, choices=REGION_CHOICES, default="BD")
    avatar = models.ImageField(upload_to=user_avatar_path, blank=True, null=True)
    bio = models.TextField(blank=True)

    youtube_link = models.URLField(blank=True)
    twitch_link = models.URLField(blank=True)
    preferred_games = models.JSONField(default=list, blank=True, null=True)
    discord_id = models.CharField(max_length=64, blank=True)
    
    # Game IDs for different platforms
    riot_id = models.CharField(max_length=100, blank=True, help_text="Riot ID (Name#TAG) for Valorant")
    riot_tagline = models.CharField(max_length=50, blank=True, help_text="Riot Tagline (part after #)")
    efootball_id = models.CharField(max_length=100, blank=True, help_text="eFootball User ID")
    steam_id = models.CharField(max_length=100, blank=True, help_text="Steam ID for Dota 2, CS2")
    mlbb_id = models.CharField(max_length=100, blank=True, help_text="Mobile Legends Game ID")
    mlbb_server_id = models.CharField(max_length=50, blank=True, help_text="Mobile Legends Server ID")
    pubg_mobile_id = models.CharField(max_length=100, blank=True, help_text="PUBG Mobile Character/Player ID")
    free_fire_id = models.CharField(max_length=100, blank=True, help_text="Free Fire User/Player ID")
    ea_id = models.CharField(max_length=100, blank=True, help_text="EA ID for FC 24")
    codm_uid = models.CharField(max_length=100, blank=True, help_text="Call of Duty Mobile UID")

    created_at = models.DateTimeField(auto_now_add=True)

    is_private = models.BooleanField(default=False, help_text="Hide entire profile from public.")
    show_email = models.BooleanField(default=False, help_text="Allow showing my email on public profile.")
    show_phone = models.BooleanField(default=False, help_text="Allow showing my phone on public profile.")
    show_socials = models.BooleanField(default=True, help_text="Allow showing my social links/IDs on public profile.")

    class Meta:
        indexes = [models.Index(fields=["region"])]
        verbose_name = "User Profile"

    def __str__(self):
        return self.display_name or getattr(self.user, "username", str(self.user_id))
    
    def get_game_id(self, game_code):
        """Get the appropriate game ID based on game code."""
        game_id_mapping = {
            'valorant': 'riot_id',
            'efootball': 'efootball_id',
            'dota2': 'steam_id',
            'cs2': 'steam_id',
            'mlbb': 'mlbb_id',
            'pubgm': 'pubg_mobile_id',
            'freefire': 'free_fire_id',
            'fc24': 'ea_id',
            'codm': 'codm_uid',
        }
        field_name = game_id_mapping.get(game_code.lower())
        if field_name:
            return getattr(self, field_name, '')
        return ''
    
    def set_game_id(self, game_code, value):
        """Set the appropriate game ID based on game code."""
        game_id_mapping = {
            'valorant': 'riot_id',
            'efootball': 'efootball_id',
            'dota2': 'steam_id',
            'cs2': 'steam_id',
            'mlbb': 'mlbb_id',
            'pubgm': 'pubg_mobile_id',
            'freefire': 'free_fire_id',
            'fc24': 'ea_id',
            'codm': 'codm_uid',
        }
        field_name = game_id_mapping.get(game_code.lower())
        if field_name:
            setattr(self, field_name, value)
            return True
        return False
    
    def get_game_id_label(self, game_code):
        """Get the label for the game ID field."""
        game_id_labels = {
            'valorant': 'Riot ID (Name#TAG)',
            'efootball': 'User ID',
            'dota2': 'Steam ID',
            'cs2': 'Steam ID',
            'mlbb': 'Game ID',
            'pubgm': 'Character ID',
            'freefire': 'Player ID',
            'fc24': 'EA ID',
            'codm': 'UID',
        }
        return game_id_labels.get(game_code.lower(), 'Game ID')

