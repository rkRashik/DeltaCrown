from __future__ import annotations

import random
import string
from datetime import timedelta
from decimal import Decimal

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.utils import timezone


def _rand_tag(n=3):
    return "".join(random.choice(string.ascii_uppercase) for _ in range(n))


def _now():
    return timezone.now()


def _fields(model):
    return {f.name for f in model._meta.get_fields() if hasattr(f, "attname")}


def _safe_create(model, **kwargs):
    """Create instance with only valid field names."""
    valid = _fields(model)
    data = {k: v for k, v in kwargs.items() if k in valid}
    return model.objects.create(**data)


def _ensure_profile(user):
    # Works if profile OneToOne is named "profile" or "userprofile"
    p = getattr(user, "profile", None) or getattr(user, "userprofile", None)
    if p:
        return p
    UserProfile = apps.get_model("user_profile", "UserProfile")
    p, _ = UserProfile.objects.get_or_create(
        user=user, defaults={"display_name": getattr(user, "username", "Player")}
    )
    return p


def _table_exists(model) -> bool:
    """Check if the DB table for a model exists (prevents aborted transactions)."""
    db_table = model._meta.db_table
    try:
        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))
    except Exception:
        tables = set(connection.introspection.table_names())
    return db_table in tables


class Command(BaseCommand):
    help = "Seed demo data: users, teams, tournaments, registrations, matches, notifications."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing demo items for known slugs/tags before seeding again.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        # Models
        User = get_user_model()
        Tournament = apps.get_model("tournaments", "Tournament")
        Registration = apps.get_model("tournaments", "Registration")
        Match = apps.get_model("tournaments", "Match")
        Bracket = apps.get_model("tournaments", "Bracket")
        Team = apps.get_model("teams", "Team")
        TeamMembership = apps.get_model("teams", "TeamMembership")
        Notification = apps.get_model("notifications", "Notification")

        # Ensure core tables exist (fail early with a clear message)
        required_models = [User, Tournament, Team, TeamMembership, Registration, Match]
        missing = [m.__name__ for m in required_models if not _table_exists(m)]
        if missing:
            raise SystemExit(
                "Required tables are missing: "
                + ", ".join(missing)
                + ". Run:  python manage.py migrate"
            )

        # Known demo identifiers
        SOLO_SLUG = "efootball-weekend-cup"
        TEAM_SLUG = "valorant-5v5-clash"
        TEAM1_TAG = "WLV"
        TEAM2_TAG = "RVN"

        # Fresh cleanup (only if the tables exist; DO NOT swallow DB errors)
        if opts["fresh"]:
            if _table_exists(Registration):
                Registration.objects.all().delete()
            if _table_exists(Match):
                Match.objects.all().delete()
            if _table_exists(Bracket):
                Bracket.objects.all().delete()
            if _table_exists(Tournament):
                Tournament.objects.filter(slug__in=[SOLO_SLUG, TEAM_SLUG]).delete()
            if _table_exists(TeamMembership):
                TeamMembership.objects.all().delete()
            if _table_exists(Team):
                Team.objects.filter(tag__in=[TEAM1_TAG, TEAM2_TAG]).delete()
            if _table_exists(Notification):
                Notification.objects.all().delete()

        # --- Users & profiles ---
        # admin (for login)
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="admin123",
            )

        # regular users
        def mkuser(u):
            obj, _ = User.objects.get_or_create(username=u, defaults={"email": f"{u}@example.com"})
            if not obj.has_usable_password():
                obj.set_password("pass1234")
                obj.save(update_fields=["password"])
            return obj

        u_alice = mkuser("alice")
        u_bob = mkuser("bob")
        u_carol = mkuser("carol")
        u_dave = mkuser("dave")

        p_alice = _ensure_profile(u_alice)
        p_bob = _ensure_profile(u_bob)
        p_carol = _ensure_profile(u_carol)
        p_dave = _ensure_profile(u_dave)

        # --- Teams & memberships (for Valorant) ---
        t_wolves = Team.objects.filter(tag=TEAM1_TAG).first()
        if not t_wolves:
            t_wolves = _safe_create(
                Team,
                name="Wolves",
                tag=TEAM1_TAG,
                captain=p_alice,
            )
        TeamMembership.objects.get_or_create(team=t_wolves, user=p_alice, defaults={"role": "captain"})
        TeamMembership.objects.get_or_create(team=t_wolves, user=p_bob, defaults={"role": "player"})

        t_ravens = Team.objects.filter(tag=TEAM2_TAG).first()
        if not t_ravens:
            t_ravens = _safe_create(
                Team,
                name="Ravens",
                tag=TEAM2_TAG,
                captain=p_carol,
            )
        TeamMembership.objects.get_or_create(team=t_ravens, user=p_carol, defaults={"role": "captain"})
        TeamMembership.objects.get_or_create(team=t_ravens, user=p_dave, defaults={"role": "player"})

        # --- Tournaments ---
        now = _now()
        def dt(days): return now + timedelta(days=days)

        # Solo (eFootball)
        solo_attrs = dict(
            name="Efootball Weekend Cup",
            slug=SOLO_SLUG,
            game="efootball",
            short_description="1v1 friendly eFootball cup.",
            reg_open_at=dt(-1),
            reg_close_at=dt(3),
            start_at=dt(4),
            end_at=dt(4) + timedelta(hours=4),
            slot_size=8,
            entry_fee=Decimal("0.00") if "entry_fee" in _fields(Tournament) else None,
            entry_fee_bdt=Decimal("0.00") if "entry_fee_bdt" in _fields(Tournament) else None,
        )
        t_solo = Tournament.objects.filter(slug=SOLO_SLUG).first()
        if not t_solo:
            t_solo = _safe_create(Tournament, **solo_attrs)

        # Team (Valorant)
        team_attrs = dict(
            name="Valorant 5v5 Clash",
            slug=TEAM_SLUG,
            game="valorant",
            short_description="Competitive 5v5 Valorant bracket.",
            reg_open_at=dt(-1),
            reg_close_at=dt(5),
            start_at=dt(6),
            end_at=dt(6) + timedelta(hours=6),
            slot_size=8,
            entry_fee=Decimal("0.00") if "entry_fee" in _fields(Tournament) else None,
            entry_fee_bdt=Decimal("0.00") if "entry_fee_bdt" in _fields(Tournament) else None,
        )
        t_team = Tournament.objects.filter(slug=TEAM_SLUG).first()
        if not t_team:
            t_team = _safe_create(Tournament, **team_attrs)

        # --- Registrations ---
        reg_status_field = "status" if "status" in _fields(Registration) else None
        CONF = "CONFIRMED"
        defaults = {reg_status_field: CONF} if reg_status_field else {}

        # solo registrations (users)
        Registration.objects.get_or_create(tournament=t_solo, user=p_alice, defaults=defaults)
        Registration.objects.get_or_create(tournament=t_solo, user=p_bob, defaults=defaults)

        # team registrations (teams)
        Registration.objects.get_or_create(tournament=t_team, team=t_wolves, defaults=defaults)
        Registration.objects.get_or_create(tournament=t_team, team=t_ravens, defaults=defaults)

        # --- Brackets (best-effort) ---
        if _table_exists(Bracket):
            Bracket.objects.get_or_create(tournament=t_solo)
            Bracket.objects.get_or_create(tournament=t_team)

        # --- Matches ---
        # Solo match
        m1 = Match.objects.filter(tournament=t_solo, round_no=1, position=1).first()
        if not m1:
            m1 = _safe_create(
                Match,
                tournament=t_solo,
                round_no=1,
                position=1,
                best_of=1 if "best_of" in _fields(Match) else None,
                user_a=p_alice if "user_a" in _fields(Match) else None,
                user_b=p_bob if "user_b" in _fields(Match) else None,
            )

        # Team match
        m2 = Match.objects.filter(tournament=t_team, round_no=1, position=1).first()
        if not m2:
            m2 = _safe_create(
                Match,
                tournament=t_team,
                round_no=1,
                position=1,
                best_of=1 if "best_of" in _fields(Match) else None,
                team_a=t_wolves if "team_a" in _fields(Match) else None,
                team_b=t_ravens if "team_b" in _fields(Match) else None,
            )

        # --- Notifications (optional) ---
        if _table_exists(Notification):
            try:
                Notification.notify_once(
                    recipient=p_alice,
                    type="match_scheduled",
                    title=f"Match scheduled — Round 1",
                    url=f"/tournaments/match/{getattr(m1, 'id', 0)}/report/",
                    tournament=t_solo,
                    match=m1,
                )
                Notification.notify_once(
                    recipient=p_carol,
                    type="match_scheduled",
                    title=f"Match scheduled — Round 1",
                    url=f"/tournaments/match/{getattr(m2, 'id', 0)}/report/",
                    tournament=t_team,
                    match=m2,
                )
            except Exception:
                # ignore if model differs
                pass

        self.stdout.write(self.style.SUCCESS("✅ Seed data created:"))
        self.stdout.write("  Users: admin/admin123 (superuser), alice, bob, carol, dave (all 'pass1234')")
        self.stdout.write(f"  Teams: {TEAM1_TAG} (Wolves), {TEAM2_TAG} (Ravens)")
        self.stdout.write(f"  Tournaments: {SOLO_SLUG}, {TEAM_SLUG}")
        self.stdout.write(f"  Matches: solo #{getattr(m1, 'id', None)}, team #{getattr(m2, 'id', None)}")
