from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from apps.tournaments.models import Tournament
from apps.teams.models import Team
from apps.user_profile.models import UserProfile


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
        # Only published tournaments
        return Tournament.objects.filter(status="PUBLISHED").order_by("-start_at")

    def location(self, obj: Tournament):
        return reverse("tournaments:detail", kwargs={"slug": obj.slug})

    def lastmod(self, obj: Tournament):
        return obj.start_at or timezone.now()


class TeamSitemap(Sitemap):
    priority = 0.5
    changefreq = "weekly"

    def items(self):
        # All teams are indexable (no "is_public" flag in model)
        return Team.objects.all().order_by("-created_at")

    def location(self, obj: Team):
        return reverse("teams:team_detail", kwargs={"team_id": obj.id})

    def lastmod(self, obj: Team):
        return obj.created_at


class ProfileSitemap(Sitemap):
    priority = 0.5
    changefreq = "weekly"

    def items(self):
        # All profiles with a linked User (default behavior)
        return UserProfile.objects.select_related("user").all().order_by("-created_at")

    def location(self, obj: UserProfile):
        return reverse("user_profile:profile", kwargs={"username": obj.user.username})

    def lastmod(self, obj: UserProfile):
        return obj.created_at


sitemaps = {
    "static": StaticViewSitemap,
    "tournaments": TournamentSitemap,
    "teams": TeamSitemap,
    "profiles": ProfileSitemap,
}
