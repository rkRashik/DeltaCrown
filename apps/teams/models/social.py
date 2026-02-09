"""
Frozen stub — kept ONLY so migration 0001_initial can resolve the
``upload_to=apps.teams.models.social.team_media_upload_path`` reference.
Do NOT add any model classes here.
"""


def team_media_upload_path(instance, filename):
    """Upload path callback referenced by historical migration."""
    return f"teams/media/{filename}"
