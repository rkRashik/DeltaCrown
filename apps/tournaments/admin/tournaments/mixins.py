# apps/tournaments/admin/tournaments/mixins.py
from __future__ import annotations

from typing import Optional

from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import path, reverse, NoReverseMatch
from django.utils.safestring import mark_safe

from ...models import Tournament, Match

# Optional scheduling services
try:
    from ...services.scheduling import auto_schedule_matches, clear_schedule
except Exception:
    auto_schedule_matches = None
    clear_schedule = None

# Optional economy
try:
    from apps.economy import services as coin_services
    from apps.economy.models import DeltaCrownTransaction
except Exception:
    coin_services = None
    DeltaCrownTransaction = None


class AdminLinkMixin:
    @staticmethod
    def _admin_change_url(obj) -> Optional[str]:
        try:
            return reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])
        except NoReverseMatch:
            return None

    # ---- helper links used in fieldsets/readonly_fields ----

    @admin.display(description="Bracket")
    def link_bracket(self, obj: Tournament):
        b = getattr(obj, "bracket", None)
        if not b:
            return "—"
        url = self._admin_change_url(b)
        return mark_safe(f'<a href="{url}">Bracket #{b.pk}</a>') if url else f"Bracket #{b.pk}"

    @admin.display(description="Settings")
    def link_settings(self, obj: Tournament):
        s = getattr(obj, "settings", None)
        if not s:
            return "—"
        url = self._admin_change_url(s)
        return mark_safe(f'<a href="{url}">Settings #{s.pk}</a>') if url else f"Settings #{s.pk}"

    @admin.display(description="Valorant Config")
    def link_valorant_config(self, obj: Tournament):
        v = getattr(obj, "valorant_config", None)
        if not v:
            return "—"
        url = self._admin_change_url(v)
        return mark_safe(f'<a href="{url}">ValorantConfig #{v.pk}</a>') if url else f"ValorantConfig #{v.pk}"

    @admin.display(description="eFootball Config")
    def link_efootball_config(self, obj: Tournament):
        e = getattr(obj, "efootball_config", None)
        if not e:
            return "—"
        url = self._admin_change_url(e)
        return mark_safe(f'<a href="{url}">eFootballConfig #{e.pk}</a>') if url else f"eFootballConfig #{e.pk}"

    @admin.display(description="Export Bracket (JSON)")
    def link_export_bracket(self, obj: Tournament):
        try:
            url = reverse("admin:tournaments_export_bracket", kwargs={"pk": obj.pk})
            return mark_safe(f'<a class="button" href="{url}">Download</a>')
        except Exception:
            return "—"

    @admin.display(description="Force Regenerate (confirm)")
    def link_force_regenerate(self, obj: Tournament):
        try:
            url = reverse("admin:tournaments_force_regenerate", kwargs={"pk": obj.pk})
            return mark_safe(
                '<a class="button" style="background:#fee2e2;color:#991b1b" href="{}">Force</a>'.format(url)
            )
        except Exception:
            return "—"

    @admin.display(description="Bracket JSON (preview)")
    def bracket_json_preview(self, obj: Tournament):
        # Small, truncated JSON preview for quick inspection
        matches = (
            Match.objects.filter(tournament=obj)
            .select_related("user_a__user", "user_b__user", "team_a", "team_b", "winner_user__user", "winner_team")
            .order_by("round_no", "position")
        )
        items = []
        for m in matches[:30]:
            a = (m.user_a.user.username if m.user_a_id and getattr(m.user_a, "user", None) else None) or (
                m.team_a.tag if m.team_a_id and getattr(m.team_a, "tag", None) else None
            )
            b = (m.user_b.user.username if m.user_b_id and getattr(m.user_b, "user", None) else None) or (
                m.team_b.tag if m.team_b_id and getattr(m.team_b, "tag", None) else None
            )
            win = (m.winner_user.user.username if m.winner_user_id and getattr(m.winner_user, "user", None) else None) or (
                m.winner_team.tag if m.winner_team_id and getattr(m.winner_team, "tag", None) else None
            )
            items.append({"id": m.pk, "r": m.round_no, "p": m.position, "a": a, "b": b, "w": win})
        import json
        txt = json.dumps({"matches": items, "note": "first 30 only"}, ensure_ascii=False, indent=2)
        return mark_safe(f'<pre style="max-height:240px;overflow:auto">{txt}</pre>')


class ExportBracketMixin:
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/export-bracket/",
                self.admin_site.admin_view(self.view_export_bracket),
                name="tournaments_export_bracket",
            ),
            path(
                "<int:pk>/force-regenerate/",
                self.admin_site.admin_view(self.view_force_regenerate_confirm),
                name="tournaments_force_regenerate",
            ),
        ]
        return custom + urls

    def view_export_bracket(self, request: HttpRequest, pk: int) -> HttpResponse:
        try:
            t = Tournament.objects.get(pk=pk)
        except Tournament.DoesNotExist:
            return JsonResponse({"error": "Tournament not found"}, status=404)

        matches = (
            Match.objects.filter(tournament=t)
            .select_related("user_a__user", "user_b__user", "team_a", "team_b", "winner_user__user", "winner_team")
            .order_by("round_no", "position")
        )

        def _name_user(up):
            if not up:
                return None
            au = getattr(up, "user", None)
            return getattr(au, "username", None) or getattr(up, "display_name", None) or f"user:{up.pk}"

        def _name_team(tp):
            if not tp:
                return None
            return getattr(tp, "tag", None) or getattr(tp, "name", None) or f"team:{tp.pk}"

        payload = {
            "tournament": {"id": t.pk, "name": getattr(t, "name", str(t)), "slug": getattr(t, "slug", None)},
            "matches": [
                {
                    "id": m.pk,
                    "round": m.round_no,
                    "position": m.position,
                    "a": _name_user(m.user_a) if m.user_a_id else _name_team(m.team_a),
                    "b": _name_user(m.user_b) if m.user_b_id else _name_team(m.team_b),
                    "winner": _name_user(m.winner_user) if m.winner_user_id else _name_team(m.winner_team),
                    "start_at": getattr(m, "start_at", None).isoformat() if getattr(m, "start_at", None) else None,
                }
                for m in matches
            ],
        }
        return JsonResponse(payload, json_dumps_params={"ensure_ascii": False, "indent": 2})

    def view_force_regenerate_confirm(self, request: HttpRequest, pk: int) -> HttpResponse:
        """
        Simple confirmation page (no template file required). POST triggers generate.
        """
        from apps.corelib.brackets import generate_bracket

        try:
            t = Tournament.objects.get(pk=pk)
        except Tournament.DoesNotExist:
            return JsonResponse({"error": "Tournament not found"}, status=404)

        if request.method == "POST":
            try:
                generate_bracket(t)
                messages.success(request, f"Force regenerated bracket for '{t.name}'.")
            except Exception as e:
                messages.error(request, f"{t.name}: {e}")
            # Redirect back to tournament change page
            url = reverse(f"admin:{t._meta.app_label}_{t._meta.model_name}_change", args=[t.pk])
            from django.shortcuts import redirect
            return redirect(url)

        # GET → show confirm page
        html = f"""
        <html><body style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,sans-serif;padding:24px">
          <h2>Force regenerate bracket</h2>
          <p><strong>WARNING:</strong> This can overwrite existing matches. Continue?</p>
          <form method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="{getattr(request, 'csrf_token', '')}">
            <button type="submit" style="background:#991b1b;color:#fff;padding:8px 14px;border-radius:8px;border:none;cursor:pointer">Yes, force regenerate</button>
            &nbsp;
            <a href="{reverse(f'admin:{t._meta.app_label}_{t._meta.model_name}_change', args=[t.pk])}">Cancel</a>
          </form>
        </body></html>
        """
        return HttpResponse(html)


class ActionsMixin:
    @admin.action(description="Generate bracket (safe: refuse if results exist)")
    @transaction.atomic
    def action_generate_bracket_safe(self, request, queryset):
        from apps.corelib.brackets import generate_bracket
        ok = fail = skipped = 0
        for t in queryset.select_related("bracket"):
            has_results = Match.objects.filter(tournament=t).filter(
                Q(winner_user__isnull=False) | Q(winner_team__isnull=False)
            ).exists()
            if has_results:
                skipped += 1
                messages.warning(request, f"{t.name}: skipped (results already exist).")
                continue
            try:
                generate_bracket(t)
                ok += 1
            except Exception as e:
                fail += 1
                messages.error(request, f"{t.name}: {e}")
        if ok:
            messages.success(request, f"Generated bracket for {ok} tournament(s).")
        if skipped:
            messages.warning(request, f"Skipped {skipped} tournament(s).")
        if fail:
            messages.error(request, f"{fail} tournament(s) failed.")

    # ✅ restored for backward compatibility + tests
    @admin.action(description="Force regenerate bracket (dangerous)")
    @transaction.atomic
    def action_force_regenerate_bracket(self, request, queryset):
        from apps.corelib.brackets import generate_bracket
        ok = fail = 0
        for t in queryset.select_related("bracket"):
            try:
                generate_bracket(t)
                ok += 1
            except Exception as e:
                fail += 1
                messages.error(request, f"{t.name}: {e}")
        if ok:
            messages.success(request, f"Force regenerated {ok} bracket(s).")
        if fail:
            messages.error(request, f"{fail} bracket(s) failed.")

    @admin.action(description="Lock bracket")
    def action_lock_bracket(self, request, queryset):
        updated = 0
        for t in queryset:
            b = getattr(t, "bracket", None)
            if b and not getattr(b, "is_locked", False):
                b.is_locked = True
                b.save(update_fields=["is_locked"])
                updated += 1
        messages.success(request, f"Locked {updated} bracket(s).")

    @admin.action(description="Unlock bracket")
    def action_unlock_bracket(self, request, queryset):
        updated = 0
        for t in queryset:
            b = getattr(t, "bracket", None)
            if b and getattr(b, "is_locked", False):
                b.is_locked = False
                b.save(update_fields=["is_locked"])
                updated += 1
        messages.success(request, f"Unlocked {updated} bracket(s).")

    @admin.action(description="Auto-schedule matches")
    def action_auto_schedule(self, request, queryset):
        if not auto_schedule_matches:
            messages.warning(request, "Scheduling service not available.")
            return
        total = 0
        for t in queryset:
            try:
                total += auto_schedule_matches(t)
            except Exception as e:
                messages.error(request, f"{t.name}: {e}")
        messages.success(request, f"Scheduled {total} match(es).")

    @admin.action(description="Clear scheduled times")
    def action_clear_schedule(self, request, queryset):
        if not clear_schedule:
            messages.warning(request, "Scheduling service not available.")
            return
        total = 0
        for t in queryset:
            try:
                total += clear_schedule(t)
            except Exception as e:
                messages.error(request, f"{t.name}: {e}")
        messages.warning(request, f"Cleared start times for {total} match(es).")

    @admin.action(description="Award Coins: Participation (verified regs)")
    def action_award_participation(self, request, queryset):
        if not coin_services or not DeltaCrownTransaction:
            messages.warning(request, "Economy app not installed.")
            return
        count = 0
        for t in queryset:
            regs = t.registration_set.all().select_related("payment_verification")
            for r in regs:
                pv = getattr(r, "payment_verification", None)
                if pv and getattr(pv, "status", "") == "verified":
                    tx = coin_services.award_participation_for_registration(r)
                    if tx:
                        count += 1 if isinstance(tx, DeltaCrownTransaction) else len(tx)
        messages.success(request, f"Awarded participation coins to {count} wallet(s).")

    @admin.action(description="Award Coins: Placements (final + semis)")
    def action_award_placements(self, request, queryset):
        if not coin_services:
            messages.warning(request, "Economy app not installed.")
            return
        total = 0
        for t in queryset:
            try:
                awards = coin_services.award_placements(t)
                total += len(awards)
            except Exception as e:
                messages.error(request, f"{t.name}: {e}")
        messages.success(request, f"Created {total} placement transaction(s).")
