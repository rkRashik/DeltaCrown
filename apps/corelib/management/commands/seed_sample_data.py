from __future__ import annotations

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from django.apps import apps
from django.db.models.signals import post_save

try:
    from apps.user_profile.signals import ensure_profile
except Exception:  # pragma: no cover
    ensure_profile = None


class Command(BaseCommand):
    help = "Reset key tables and seed demo data for local development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip safety prompt and run immediately.",
        )

    def handle(self, *args, **options):
        if not options["force"]:
            self.stdout.write(self.style.WARNING("Add --force to run the seeder (avoids accidental wipes)."))
            return

        with transaction.atomic():
            self._reset_database()
            summary = self._seed()

        self.stdout.write(self.style.SUCCESS("Seed completed."))
        for line in summary:
            self.stdout.write(f"  - {line}")

    # ------------------------------------------------------------------
    def _reset_database(self) -> None:
        self.stdout.write("Clearing existing data (using TRUNCATE CASCADE) ...")
        tables = [
            "notifications_notification",
            "economy_deltacrowntransaction",
            "economy_deltacrownwallet",
            "teams_teammembership",
            "teams_teaminvite",
            "teams_teamachievement",
            "teams_efootballteampreset",
            "teams_valorantteampreset",
            "teams_valorantplayerpreset",
            "teams_team",
            "tournaments_registration",
            "tournaments_paymentverification",
            "tournaments_calendarfeedtoken",
            "tournaments_savedmatchfilter",
            "tournaments_pinnedtournament",
            "tournaments_tournament",
            "accounts_emailotp",
            "accounts_pendingsignup",
            "user_profile_userprofile",
            "accounts_user",
            "auth_user",
        ]
        existing_tables = set(connection.introspection.table_names())
        with connection.cursor() as cursor:
            cursor.execute("SET session_replication_role = 'replica'")
            try:
                for table in tables:
                    if table not in existing_tables:
                        continue
                    try:
                        cursor.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE')
                    except Exception:
                        pass
            finally:
                cursor.execute("SET session_replication_role = 'origin'")

    # ------------------------------------------------------------------
    def _ensure_roles(self):
        Group = apps.get_model('auth', 'Group')
        role_names = [
            'Platform Admin',
            'Tournament Staff',
            'Valorant Organizer',
            'eFootball Organizer',
            'Team Moderator',
            'Support Staff',
        ]
        roles = {}
        for name in role_names:
            roles[name], _ = Group.objects.get_or_create(name=name)
        return roles

    def _ensure_admin_user(self, roles, UserProfile):
        User = get_user_model()
        admin_defaults = {
            'email': 'admin@example.com',
            'is_staff': True,
            'is_superuser': True,
        }
        admin_user, _ = User.objects.update_or_create(
            username='admin', defaults=admin_defaults
        )
        admin_user.is_verified = True if hasattr(admin_user, 'is_verified') else admin_user.is_active
        admin_user.set_password('AdminPass123!')
        admin_user.save()
        self._sync_auth_user(admin_user)
        admin_profile = None
        if UserProfile is not None:
            admin_profile, _ = UserProfile.objects.get_or_create(
                user=admin_user, defaults={'display_name': 'Admin'}
            )
        if roles.get('Platform Admin'):
            admin_user.groups.set([roles['Platform Admin']])
        return admin_user, admin_profile

    def _seed(self) -> list[str]:
        self.stdout.write("Creating demo users, teams, and tournaments ...")
        User = get_user_model()
        UserProfile = apps.get_model("user_profile", "UserProfile")

        roles = self._ensure_roles()
        self._ensure_admin_user(roles, UserProfile)
        Team = apps.get_model("organizations", "Team")
        TeamMembership = apps.get_model("organizations", "TeamMembership")
        Tournament = apps.get_model("tournaments", "Tournament")
        Registration = apps.get_model("tournaments", "Registration")

        now = timezone.now()

        disconnect_signal = ensure_profile and User
        if disconnect_signal:
            post_save.disconnect(ensure_profile, sender=User)

        users = []
        profiles = []
        try:
            for i in range(1, 31):
                username = f"player{i:02d}"
                user = User.objects.create_user(
                    username=username,
                    email=f"{username}@example.com",
                    password="DemoPass123!",
                )
                if hasattr(user, "mark_email_verified"):
                    user.mark_email_verified()

                self._sync_auth_user(user)

                if UserProfile is not None:
                    profile = UserProfile.objects.create(
                        user=user,
                        display_name=user.username or user.email or f"Player {i}",
                    )
                else:
                    profile = getattr(user, "profile", None)

                users.append(user)
                profiles.append(profile)
        finally:
            if disconnect_signal:
                post_save.connect(ensure_profile, sender=User)

        resolved_profiles = []
        for user_obj, profile in zip(users, profiles):
            if profile:
                resolved_profiles.append(profile)
                continue
            fallback = None
            if UserProfile is not None:
                fallback = UserProfile.objects.filter(user=user_obj).first()
            if not fallback:
                try:
                    fallback = user_obj.profile
                except Exception:
                    fallback = None
            if fallback:
                resolved_profiles.append(fallback)
        if len(resolved_profiles) < len(users):
            raise CommandError("Failed to build profiles for all demo users.")
        profiles = resolved_profiles

        status_choices = getattr(Tournament, "Status", None)
        status_published = getattr(status_choices, "PUBLISHED", "PUBLISHED")

        valorant_tournament = Tournament.objects.create(
            name="Valorant Delta Masters",
            slug="valorant-delta-masters",
            game="valorant",
            status=status_published,
            short_description="Premier Valorant showdown for seeded teams.",
            slot_size=32,
            reg_open_at=now - timedelta(days=2),
            reg_close_at=now + timedelta(days=5),
            start_at=now + timedelta(days=7),
        )

        efootball_tournament = Tournament.objects.create(
            name="eFootball Champions Cup",
            slug="efootball-champions",
            game="efootball",
            status=status_published,
            short_description="1v1 eFootball ladder with verified payouts.",
            slot_size=10,
            reg_open_at=now - timedelta(days=1),
            reg_close_at=now + timedelta(days=2),
            start_at=now + timedelta(days=4),
            entry_fee_bdt=200,
            prize_pool_bdt=5000,
        )

        roster_pointer = 0
        valorant_team_sizes = [6, 7, 6, 7]
        valorant_teams = []
        for idx, size in enumerate(valorant_team_sizes, start=1):
            members = profiles[roster_pointer:roster_pointer + size]
            roster_pointer += size
            team = Team.objects.create(
                name=f"Valorant Squad {idx}",
                slug=f"valorant-squad-{idx}",
                game="valorant",
            )
            for m_idx, profile in enumerate(members):
                role = TeamMembership.Role.CAPTAIN if m_idx == 0 else TeamMembership.Role.PLAYER
                TeamMembership.objects.create(
                    team=team,
                    profile=profile,
                    role=role,
                    status=TeamMembership.Status.ACTIVE,
                )
                if role == TeamMembership.Role.CAPTAIN:
                    team.captain = profile
            team.save(update_fields=["captain"])
            valorant_teams.append(team)

        efootball_teams = []
        members_per_team = 2
        for idx in range(10):
            members = profiles[roster_pointer:roster_pointer + members_per_team]
            roster_pointer += members_per_team
            team = Team.objects.create(
                name=f"eFootball Duo {idx + 1}",
                slug=f"efootball-duo-{idx + 1}",
                game="efootball",
            )
            for m_idx, profile in enumerate(members):
                role = TeamMembership.Role.CAPTAIN if m_idx == 0 else TeamMembership.Role.PLAYER
                TeamMembership.objects.create(
                    team=team,
                    profile=profile,
                    role=role,
                    status=TeamMembership.Status.ACTIVE,
                )
                if role == TeamMembership.Role.CAPTAIN:
                    team.captain = profile
            team.save(update_fields=["captain"])
            efootball_teams.append(team)

        for profile in profiles[:10]:
            Registration.objects.create(
                tournament=efootball_tournament,
                user=profile,
                payment_method="bkash",
                payment_reference=f"TXN-{random.randint(10000, 99999)}",
                payment_sender="01700000000",
                status="PENDING",
            )

        return [
            "30 demo users created (password: DemoPass123!)",
            f"{len(valorant_teams)} Valorant teams seeded",
            f"{len(efootball_teams)} eFootball duos seeded",
            "10 eFootball registrations created",
            f"Tournaments: {valorant_tournament.name}, {efootball_tournament.name}",
        ]

    def _sync_auth_user(self, user) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('auth_user')")
            if cursor.fetchone()[0] is None:
                return
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
                    None,
                    user.is_superuser,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.email,
                    user.is_staff,
                    user.is_active,
                    timezone.now(),
                ],
            )

