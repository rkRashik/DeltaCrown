"""
Account Management Event Handlers

Handles user account synchronization with legacy auth_user table
and staff flag management based on group membership.
"""
import logging
from django.db import connection
from django.apps import apps
from django.contrib.auth import get_user_model

from apps.core.events import event_bus

logger = logging.getLogger(__name__)

User = get_user_model()

# Staff group names that automatically grant is_staff flag
STAFF_GROUP_NAMES = ["Admin", "Moderator", "Staff", "Tournament Manager"]


def _auth_table_exists() -> bool:
    """Check if legacy auth_user table exists"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('auth_user')")
            row = cursor.fetchone()
        return bool(row and row[0])
    except Exception:
        return False


def _sync_auth_row(user: User) -> None:
    """Sync user data to legacy auth_user table for backward compatibility"""
    if not _auth_table_exists():
        return
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO auth_user (id, password, last_login, is_superuser, username,
                                       first_name, last_name, email, is_staff, is_active, date_joined)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    password = EXCLUDED.password,
                    last_login = EXCLUDED.last_login,
                    is_superuser = EXCLUDED.is_superuser,
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    email = EXCLUDED.email,
                    is_staff = EXCLUDED.is_staff,
                    is_active = EXCLUDED.is_active,
                    date_joined = EXCLUDED.date_joined
                """,
                [
                    user.id,
                    user.password,
                    getattr(user, "last_login", None),
                    user.is_superuser,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.email,
                    user.is_staff,
                    user.is_active,
                    getattr(user, "date_joined", None),
                ],
            )
    except Exception as e:
        logger.error(f"Failed to sync auth_user table: {e}")


def _sync_staff_flag(user: User) -> None:
    """Update is_staff flag based on group membership"""
    try:
        should_be_staff = user.is_superuser or user.groups.filter(name__in=STAFF_GROUP_NAMES).exists()
        if user.is_staff != should_be_staff:
            User.objects.filter(pk=user.pk).update(is_staff=should_be_staff)
            user.is_staff = should_be_staff
            logger.info(f"Updated staff flag for {user.username}: {should_be_staff}")
    except Exception as e:
        logger.error(f"Failed to sync staff flag: {e}")


def sync_user_on_group_change(event):
    """
    Sync staff flag and auth_user when user groups change.
    
    Replaces: ensure_staff_flag signal
    Triggered by: UserGroupsChangedEvent
    """
    try:
        user_id = event.data.get('user_id')
        user = User.objects.get(id=user_id)
        
        _sync_staff_flag(user)
        _sync_auth_row(user)
        
        logger.info(f"✅ Synced user on group change: {user.username}")
    
    except Exception as e:
        logger.error(f"❌ Failed to sync user on group change: {e}", exc_info=True)


def sync_user_on_save(event):
    """
    Sync staff flag and auth_user when user is created or updated.
    
    Replaces: mirror_auth_user signal
    Triggered by: UserCreatedEvent, UserUpdatedEvent
    """
    try:
        user_id = event.data.get('user_id')
        user = User.objects.get(id=user_id)
        
        _sync_staff_flag(user)
        _sync_auth_row(user)
        
        logger.debug(f"✅ Synced user: {user.username}")
    
    except Exception as e:
        logger.error(f"❌ Failed to sync user on save: {e}", exc_info=True)


def delete_auth_shadow(event):
    """
    Delete legacy auth_user row when user is deleted.
    
    Replaces: delete_auth_shadow signal
    Triggered by: UserDeletedEvent
    """
    try:
        user_id = event.data.get('user_id')
        
        if not _auth_table_exists():
            return
        
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM auth_user WHERE id = %s", [user_id])
        
        logger.info(f"✅ Deleted auth_user shadow for user ID: {user_id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to delete auth_user shadow: {e}", exc_info=True)


def register_accounts_event_handlers():
    """Register account management event handlers"""
    
    # User group changes
    event_bus.subscribe(
        'user.groups_changed',
        sync_user_on_group_change,
        name='sync_user_on_group_change',
        priority=10
    )
    
    # User created/updated
    event_bus.subscribe(
        'user.created',
        sync_user_on_save,
        name='sync_user_on_created',
        priority=10
    )
    
    event_bus.subscribe(
        'user.updated',
        sync_user_on_save,
        name='sync_user_on_updated',
        priority=10
    )
    
    # User deleted
    event_bus.subscribe(
        'user.deleted',
        delete_auth_shadow,
        name='delete_auth_shadow',
        priority=10
    )
    
    logger.info("📢 Registered accounts event handlers")


__all__ = [
    'sync_user_on_group_change',
    'sync_user_on_save',
    'delete_auth_shadow',
    'register_accounts_event_handlers',
]
