from __future__ import annotations

from django.db import connection
from django.db.models.signals import post_delete, post_save, m2m_changed
from django.dispatch import receiver

from django.contrib.auth import get_user_model

from .roles import STAFF_GROUP_NAMES

User = get_user_model()


def _auth_table_exists() -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('auth_user')")
        row = cursor.fetchone()
    return bool(row and row[0])


def _sync_auth_row(user: User) -> None:
    """Ensure a shadow row exists in auth_user for legacy FKs."""
    if not _auth_table_exists():
        return
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


def _sync_staff_flag(user: User) -> None:
    should_be_staff = user.is_superuser or user.groups.filter(name__in=STAFF_GROUP_NAMES).exists()
    if user.is_staff != should_be_staff:
        User.objects.filter(pk=user.pk).update(is_staff=should_be_staff)
        user.is_staff = should_be_staff


@receiver(m2m_changed, sender=User.groups.through)
def ensure_staff_flag(sender, instance: User, action, **_):
    if action not in {"post_add", "post_remove", "post_clear"}:
        return
    _sync_staff_flag(instance)
    _sync_auth_row(instance)


@receiver(post_save, sender=User)
def mirror_auth_user(sender, instance: User, **_):
    _sync_staff_flag(instance)
    _sync_auth_row(instance)


@receiver(post_delete, sender=User)
def delete_auth_shadow(sender, instance: User, **_):
    if not _auth_table_exists():
        return
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM auth_user WHERE id = %s", [instance.id])
