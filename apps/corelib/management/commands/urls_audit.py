# apps/corelib/management/commands/urls_audit.py
from __future__ import annotations

from typing import Dict, Iterable, Tuple

from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.urls import get_resolver, reverse


class Command(BaseCommand):
    help = "Smoke-audit named URLs for reverse() success and render a few key templates."

    # Provide sample args/kwargs for URLs that need them
    SAMPLE_ARGS: Dict[str, Tuple[Tuple, dict]] = {
        # tournaments
        "tournaments:match_attendance_toggle": ((1, "confirm"), {}),
        "tournaments:match_quick_action": ((1, "remind_team"), {}),
        "tournaments:my_matches_ics": (("SAMPLETOKEN123",), {}),
        "tournaments:my_matches_toggle_pin": ((1,), {}),
        # user_profile
        "user_profile:public_profile": (("sampleuser",), {}),
        # Add more here as your project grows
    }

    # Minimal templates to verify exist & render
    TEMPLATE_SMOKE: Iterable[Tuple[str, dict]] = (
        ("dashboard/my_matches.html", {"page_obj": None, "params": {}, "counters": {"upcoming":0,"live":0,"completed":0}, "pinned": [], "pins_ids": set(), "heat_map": {}, "ics_token": "X", "group_by": ""}),
        ("dashboard/ics_help.html", {"token": "X", "params": {}}),
        ("users/profile_edit.html", {"form": None}),
        ("users/public_profile.html", {"profile": None}),  # if exists in your repo
    )

    def handle(self, *args, **options):
        ok, bad = [], []

        # 1) URL reverses
        resolver = get_resolver()
        # reverse_dict keys can be tuples: (name, namespace) or plain name
        names = set()
        for key in resolver.reverse_dict.keys():
            if isinstance(key, str):
                names.add(key)
            elif isinstance(key, tuple):
                # Last element is the full "ns:name"
                names.add(key[0])

        for name in sorted(n for n in names if ":" in n):  # only named URLs
            args_kwargs = self.SAMPLE_ARGS.get(name, ((), {}))
            try:
                reverse(name, args=args_kwargs[0], kwargs=args_kwargs[1])
                ok.append(name)
            except Exception as e:
                bad.append((name, str(e)))

        # 2) Template smoke renders
        tmpl_ok, tmpl_bad = [], []
        for tmpl, ctx in self.TEMPLATE_SMOKE:
            try:
                render_to_string(tmpl, ctx)
                tmpl_ok.append(tmpl)
            except Exception as e:
                tmpl_bad.append((tmpl, str(e)))

        # Print summary
        self.stdout.write(self.style.MIGRATE_HEADING("URL reverse audit"))
        for n in ok:
            self.stdout.write(self.style.SUCCESS(f"  OK   {n}"))
        for n, err in bad:
            self.stdout.write(self.style.ERROR(f"  FAIL {n} -> {err}"))

        self.stdout.write(self.style.MIGRATE_HEADING("\nTemplate render audit"))
        for t in tmpl_ok:
            self.stdout.write(self.style.SUCCESS(f"  OK   {t}"))
        for t, err in tmpl_bad:
            self.stdout.write(self.style.ERROR(f"  FAIL {t} -> {err}"))

        # Exit codes: 0 if all good, 1 otherwise
        if bad or tmpl_bad:
            self.stdout.write(self.style.WARNING("\nSome audits failed. See details above."))
            return
        self.stdout.write(self.style.SUCCESS("\nAll URL reverses and template renders passed."))
