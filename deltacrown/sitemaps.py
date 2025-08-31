from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from apps.tournaments.models import Tournament


class StaticViewSitemap(Sitemap):
    priority = 0.6
    changefreq = "weekly"

    def items(self):
        return ["home"]

    def location(self, item):
        return reverse(item)


class TournamentSitemap(Sitemap):
    priority = 0.8
    changefreq = "daily"

    def items(self):
        # Only published tournaments should appear
        return Tournament.objects.filter(status="PUBLISHED").order_by("-start_at")

    def location(self, obj: Tournament):
        # Explicitly define the URL to avoid relying on get_absolute_url()
        return reverse("tournaments:detail", kwargs={"slug": obj.slug})

    def lastmod(self, obj: Tournament):
        return obj.start_at or timezone.now()


sitemaps = {
    "static": StaticViewSitemap,
    "tournaments": TournamentSitemap,
}
