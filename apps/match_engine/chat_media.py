"""Read-time recovery for old lobby chat avatar URLs.

Saved WebSocket chat messages may retain Cloudinary URLs after a private-media
cutover. In hybrid mode, never replay stored external avatar links. Instead
resolve the current governed profile field. No database changes are performed.
"""


def hydrate_history_avatars(messages, profiles_by_user):
    """Overwrite every historical avatar with its present governed local route.

    Missing, deleted or invalid profile media fail closed to an empty URL,
    rather than leaking an obsolete public Cloudinary URL.
    """
    for message in messages:
        profile = profiles_by_user.get(message.get("user_id"))
        url = ""
        if profile is not None:
            try:
                avatar = profile.avatar
                candidate = str(avatar.url) if avatar else ""
                if candidate.startswith("/") and not candidate.startswith("//"):
                    url = candidate
            except (AttributeError, ValueError, TypeError):
                pass
        message["avatar_url"] = url
    return messages
