from django.core.management.base import BaseCommand
from django.utils import timezone
from django.apps import apps

from apps.notifications.models import Notification
from apps.notifications.services import notify

Match = apps.get_model("tournaments", "Match")

# Optional scheduling helper
try:
    from apps.tournaments.services.scheduling import get_checkin_window
except Exception:
    def get_checkin_window(m):
        # Fallback: open 30m before, close at start
        start = getattr(m, "start_at", None)
        if not start:
            now = timezone.now()
            return now, now
        return start - timezone.timedelta(minutes=30), start


class Command(BaseCommand):
    help = "Send check-in reminder notifications for matches whose check-in window is open now."

    def handle(self, *args, **options):
        now = timezone.now()
        qs = Match.objects.select_related("tournament").filter(start_at__isnull=False)
        sent = 0
        for m in qs:
            open_dt, close_dt = get_checkin_window(m)
            if not (open_dt <= now <= close_dt):
                continue

            recipients = []
            a = getattr(m, "user_a", None) or getattr(getattr(m, "team_a", None), "captain", None)
            b = getattr(m, "user_b", None) or getattr(getattr(m, "team_b", None), "captain", None)
            if a: recipients.append(a)
            if b: recipients.append(b)
            if not recipients:
                continue

            notify(
                recipients,
                Notification.Type.CHECKIN_OPEN,
                title=f"Check-in open: {m.tournament.name}",
                body=f"Round {m.round_no}, match {m.position}. Check-in is now open.",
                url=f"/t/{m.tournament.slug}/",
                tournament=m.tournament,
                match=m,
                dedupe=True,
                email_subject=f"[DeltaCrown] Check-in open – {m.tournament.name}",
                email_template="match_checkin",
                email_ctx={"t": m.tournament, "m": m, "open_dt": open_dt, "close_dt": close_dt},
            )
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} check-in notifications"))
