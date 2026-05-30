"""
Custom admin form and widget for DailyRewardConfig.
Replaces the raw JSON textarea with a user-friendly 7-day card grid.
"""
from __future__ import annotations

import json
from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe


_DAYS = [
    ("Thu", "Thursday",  "🟣"),
    ("Fri", "Friday",    "🟣"),
    ("Sat", "Saturday",  "🔵"),
    ("Sun", "Sunday",    "🔵"),
    ("Mon", "Monday",    "🟢"),
    ("Tue", "Tuesday",   "🟢"),
    ("Wed", "Wednesday", "⭐"),   # highest reward day
]

_DEFAULTS = {
    "Thu": (25, 0),
    "Fri": (30, 0),
    "Sat": (40, 2),
    "Sun": (50, 0),
    "Mon": (60, 3),
    "Tue": (75, 0),
    "Wed": (100, 10),
}


class WeekScheduleWidget(forms.Widget):
    """
    Renders the 7-day reward schedule as an interactive card grid.
    Each card shows: day label, XP input, DC input.
    Live JavaScript updates the weekly totals as admin types.
    """
    template_name = None   # we override render() directly

    def _parse(self, value) -> list[dict]:
        if not value:
            return []
        if isinstance(value, list):
            return value
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return []

    def render(self, name, value, attrs=None, renderer=None):
        schedule = self._parse(value)
        day_map = {entry.get("day"): entry for entry in schedule}

        cards_html = ""
        for day_short, day_long, emoji in _DAYS:
            entry   = day_map.get(day_short, {})
            xp_val  = entry.get("xp",  _DEFAULTS[day_short][0])
            dc_val  = entry.get("dc",  _DEFAULTS[day_short][1])
            is_wed  = day_short == "Wed"
            card_border = "2px solid #CFA75A" if is_wed else "1px solid #2F3645"
            badge_bg    = "#75591F" if is_wed else "#232936"

            cards_html += f"""
<div class="dc-day-card" style="
  background:#181D27; border-radius:14px; padding:16px 12px;
  border:{card_border}; text-align:center; position:relative;
  transition:box-shadow 140ms;">
  <div style="font-size:18px; margin-bottom:4px;">{emoji}</div>
  <div style="font-family:'Inter',sans-serif; font-weight:700; font-size:13px;
    color:#F4F6FA; margin-bottom:2px;">{day_short}</div>
  <div style="font-size:10px; color:#6B7385; margin-bottom:12px;">{day_long}</div>

  <div style="margin-bottom:8px;">
    <label style="display:block; font-size:10px; font-weight:600;
      letter-spacing:.08em; text-transform:uppercase; color:#8470EE;
      margin-bottom:4px;">XP</label>
    <input
      type="number" min="0" max="9999" step="1"
      name="{name}_{day_short.lower()}_xp"
      value="{xp_val}"
      class="dc-day-input"
      data-field="xp"
      style="width:100%; background:#11151E; border:1px solid #2F3645;
        border-radius:8px; color:#F4F6FA; font-family:'JetBrains Mono',monospace;
        font-size:16px; font-weight:700; text-align:center; padding:8px 4px;
        outline:none; transition:border-color 140ms;"
      onfocus="this.style.borderColor='#8470EE'"
      onblur="this.style.borderColor='#2F3645'"
      oninput="dcUpdateTotals()" />
  </div>

  <div>
    <label style="display:block; font-size:10px; font-weight:600;
      letter-spacing:.08em; text-transform:uppercase; color:#CFA75A;
      margin-bottom:4px;">DC</label>
    <input
      type="number" min="0" max="9999" step="1"
      name="{name}_{day_short.lower()}_dc"
      value="{dc_val}"
      class="dc-day-input"
      data-field="dc"
      style="width:100%; background:#11151E; border:1px solid #2F3645;
        border-radius:8px; color:#CFA75A; font-family:'JetBrains Mono',monospace;
        font-size:16px; font-weight:700; text-align:center; padding:8px 4px;
        outline:none; transition:border-color 140ms;"
      onfocus="this.style.borderColor='#CFA75A'"
      onblur="this.style.borderColor='#2F3645'"
      oninput="dcUpdateTotals()" />
  </div>

  {'<div style="position:absolute;top:8px;right:8px;background:' + badge_bg + ';color:#CFA75A;font-size:9px;font-weight:700;padding:2px 6px;border-radius:4px;letter-spacing:.05em;">BONUS</div>' if is_wed else ''}
</div>"""

        html = f"""
<div id="dc-week-grid" style="
  display:grid; grid-template-columns:repeat(7,1fr); gap:12px;
  margin-bottom:16px;">
  {cards_html}
</div>

<div id="dc-week-total" style="
  display:flex; align-items:center; gap:20px; padding:12px 16px;
  background:#11151E; border-radius:10px; border:1px solid #2F3645;
  font-family:'Inter',sans-serif; font-size:13px; color:#A9B1C2;">
  <span>📅 Weekly total:</span>
  <span style="color:#8470EE; font-weight:700;">
    <span id="dc-total-xp" style="font-family:'JetBrains Mono',monospace;">0</span> XP
  </span>
  <span>+</span>
  <span style="color:#CFA75A; font-weight:700;">
    <span id="dc-total-dc" style="font-family:'JetBrains Mono',monospace;">0</span> DC
  </span>
  <span style="margin-left:auto; font-size:11px; color:#6B7385;">
    Per day: XP = experience &nbsp;·&nbsp; DC = DeltaCoin (platform currency)
  </span>
</div>

<script>
function dcUpdateTotals() {{
  var xpSum = 0, dcSum = 0;
  document.querySelectorAll('.dc-day-input').forEach(function(inp) {{
    var v = parseInt(inp.value, 10) || 0;
    if (inp.dataset.field === 'xp') xpSum += v;
    else dcSum += v;
  }});
  var xEl = document.getElementById('dc-total-xp');
  var dEl = document.getElementById('dc-total-dc');
  if (xEl) xEl.textContent = xpSum.toLocaleString();
  if (dEl) dEl.textContent = dcSum.toLocaleString();
}}
document.addEventListener('DOMContentLoaded', dcUpdateTotals);
</script>
"""
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        """Read individual day inputs and pack back into JSON list."""
        schedule = []
        for day_short, _, _ in _DAYS:
            xp = int(data.get(f"{name}_{day_short.lower()}_xp") or 0)
            dc = int(data.get(f"{name}_{day_short.lower()}_dc") or 0)
            schedule.append({"day": day_short, "xp": xp, "dc": dc})
        return json.dumps(schedule)

    def value_omitted_from_data(self, data, files, name):
        # Any one of the day inputs present → value was submitted
        return f"{name}_thu_xp" not in data


class DailyRewardConfigAdminForm(forms.ModelForm):
    """Admin form for DailyRewardConfig using the card-grid widget."""
    from apps.economy.models.daily_reward import DailyRewardConfig  # lazy import

    class Meta:
        from apps.economy.models.daily_reward import DailyRewardConfig
        model = DailyRewardConfig
        fields = ["name", "is_active", "week_schedule"]
        widgets = {
            "week_schedule": WeekScheduleWidget(),
        }
        labels = {
            "week_schedule": "Week schedule (Thu → Wed)",
        }
        help_texts = {
            "week_schedule": "Set XP and DC rewards for each platform day. Wednesday is the highest-reward day.",
        }
