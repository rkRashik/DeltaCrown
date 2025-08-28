from django.core.management.base import BaseCommand, CommandError
from apps.tournaments.models import Tournament
from apps.corelib.brackets import generate_bracket

class Command(BaseCommand):
    help = "Idempotently generate single-elimination bracket for a tournament."

    def add_arguments(self, parser):
        parser.add_argument("tournament", help="Tournament ID or slug")

    def handle(self, *args, **opts):
        key = opts["tournament"]
        try:
            t = Tournament.objects.get(id=int(key)) if key.isdigit() else Tournament.objects.get(slug=key)
        except Tournament.DoesNotExist:
            raise CommandError("Tournament not found.")
        generate_bracket(t)
        self.stdout.write(self.style.SUCCESS(f"Bracket generated for {t.name}"))
