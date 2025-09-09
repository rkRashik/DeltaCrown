from django.core.management.base import BaseCommand, CommandError
from django.test import Client
import re, json

OK = "✅"
BAD = "❌"

class Command(BaseCommand):
    help = "Quick smoke QA for key pages (status/meta/a11y/JSON-LD)."

    def handle(self, *args, **opts):
        c = Client()
        failures = []

        def check(url, fn):
            resp = c.get(url, follow=True)
            if resp.status_code != 200:
                failures.append(f"{BAD} {url} -> {resp.status_code}")
                return
            try:
                fn(resp)
            except Exception as e:
                failures.append(f"{BAD} {url} -> {e}")

        # Home
        def home_checks(resp):
            html = resp.content.decode()
            assert "<html" in html and 'lang="' in html
            assert "Skip to main content" in html
            assert 'property="og:title"' in html
            assert 'name="twitter:card"' in html
            # JSON-LD parse
            scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
            types = set()
            for s in scripts:
                data = json.loads(s.strip())
                if isinstance(data, dict) and "@type" in data:
                    types.add(data["@type"])
            assert "Organization" in types and "WebSite" in types
            # Motion hooks present (at least one)
            assert "data-reveal" in html or "data-count-to" in html
            # Toast container
            assert 'id="dc-toasts"' in html

        def simple_ok(resp):
            pass  # status=200 is enough

        check("/", home_checks)
        check("/accounts/login/", simple_ok)
        check("/accounts/signup/", simple_ok)
        check("/accounts/profile/", lambda r: None)  # anonymous redirects—ignore content
        check("/robots.txt", simple_ok)
        check("/sitemap.xml", simple_ok)

        if failures:
            self.stdout.write(self.style.ERROR("\n".join(failures)))
            raise CommandError(f"{len(failures)} QA checks failed.")
        self.stdout.write(self.style.SUCCESS(f"{OK} QA smoke passed"))
