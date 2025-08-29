from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.tournaments.models import Match
from apps.tournaments.services.scheduling import get_checkin_window

class Command(BaseCommand):
    help = "Send check-in reminder emails/notifications for matches whose check-in window is open now."

    def handle(self, *args, **options):
        now = timezone.now()
        qs = Match.objects.select_related("tournament").filter(start_at__isnull=False)
        sent = 0
        for m in qs:
            open_dt, close_dt = get_checkin_window(m)
            if not open_dt or not close_dt:
                continue
            if not (open_dt <= now < close_dt):
                continue

            recipients = []
            if m.user_a_id: recipients.append(m.user_a)
            if m.user_b_id: recipients.append(m.user_b)
            if m.team_a_id and getattr(m.team_a, "captain_id", None): recipients.append(m.team_a.captain)
            if m.team_b_id and getattr(m.team_b, "captain_id", None): recipients.append(m.team_b.captain)

            for p in recipients:
                if Notification.objects.filter(recipient=p, type=Notification.Type.CHECKIN_OPEN, match=m).exists():
                    continue
                notify(
                    p, Notification.Type.CHECKIN_OPEN,
                    title=f"Check-in open: {m.tournament.name}",
                    body=f"Round {m.round_no}, match {m.position}. Check-in is now open.",
                    url=f"/t/{m.tournament.slug}/",
                    tournament=m.tournament, match=m,
                    email_subject=f"[DeltaCrown] Check-in open – {m.tournament.name}",
                    email_template="match_checkin",
                    email_ctx={"t": m.tournament, "m": m, "open_dt": open_dt, "close_dt": close_dt},
                )
                sent += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} check-in notifications"))
