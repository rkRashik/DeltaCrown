from __future__ import annotations
from typing import Any, Dict, Optional

from django import forms
from django.apps import apps

# Models (tolerant lookups)
Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")

def _get_model(app_label: str, name: str):
    try:
        return apps.get_model(app_label, name)
    except Exception:
        return None

Team = _get_model("tournaments", "Team") or _get_model("teams", "Team")
TeamMembership = _get_model("tournaments", "TeamMembership") or _get_model("teams", "TeamMembership")


# -------------------------- Helpers --------------------------

def _settings(tournament: Any):
    return getattr(tournament, "settings", None)

def _cfg_efootball(tournament: Any):
    for attr in ("efootball_config", "efb_config", "game_config"):
        obj = getattr(tournament, attr, None) or getattr(_settings(tournament), attr, None)
        if obj:
            return obj
    return None

def _cfg_valorant(tournament: Any):
    for attr in ("valorant_config", "valo_config", "game_config"):
        obj = getattr(tournament, attr, None) or getattr(_settings(tournament), attr, None)
        if obj:
            return obj
    return None

def _bool(obj, name: str, default: bool = False) -> bool:
    try:
        v = getattr(obj, name, default)
        if isinstance(v, str):
            return v.lower() in ("1", "true", "yes", "on")
        return bool(v)
    except Exception:
        return default


# -------------------------- Base Dynamic Form --------------------------

class _BaseRegForm(forms.Form):
    """
    Base for tournament registration forms.
    Accepts `tournament` and `request` in kwargs; adds dynamic fields from organizer config.
    Includes shared payment fields (optional; validated by the view when fee > 0).
    """

    # Shared payment fields — only added if tournament has entry fee
    # payment_method = forms.ChoiceField(...)  # Added dynamically
    # payer_account_number = forms.CharField(...)  # Added dynamically
    # payment_reference = forms.CharField(...)  # Added dynamically

    def __init__(self, *args, **kwargs):
        self.tournament = kwargs.pop("tournament", None)
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Add payment fields only if tournament has entry fee
        self._add_payment_fields()
        
        # Add organizer-defined fields dynamically
        self._add_dynamic_fields()

    def _add_payment_fields(self):
        """Add payment fields only if tournament has entry fee."""
        if not self.tournament:
            return
        
        # Check if tournament has entry fee
        entry_fee = getattr(self.tournament, 'entry_fee', None) or getattr(self.tournament, 'entry_fee_bdt', None)
        
        if not entry_fee or entry_fee <= 0:
            return  # No fee, don't add payment fields
        
        # Add payment fields
        self.fields['payment_method'] = forms.ChoiceField(
            choices=(("bkash", "bKash"), ("nagad", "Nagad"), ("rocket", "Rocket"), ("bank", "Bank")),
            required=True,
            label="Payment Method"
        )
        self.fields['payer_account_number'] = forms.CharField(
            required=True, 
            label="Payer mobile/account",
            help_text="Your mobile number or account used for payment"
        )
        self.fields['payment_reference'] = forms.CharField(
            required=True, 
            label="Transaction ID / Reference",
            help_text="Transaction ID from payment confirmation"
        )

    def _validate_tournament_slots(self):
        """
        Check if tournament has available slots for new registrations.
        """
        if not self.tournament:
            return
            
        slot_size = getattr(self.tournament, "slot_size", None)
        if slot_size is None or slot_size <= 0:
            return  # No slot limit set
        
        # Get current registration count
        try:
            current_count = Registration.objects.filter(
                tournament=self.tournament
            ).count()
            
            # Try to get confirmed registrations if status field exists
            try:
                confirmed_count = Registration.objects.filter(
                    tournament=self.tournament, 
                    status="CONFIRMED"
                ).count()
                current_count = confirmed_count
            except:
                pass  # Fallback to total count
                
        except Exception:
            return  # Skip validation if can't query
        
        if current_count >= slot_size:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f"This tournament is full! ({current_count}/{slot_size} slots taken)"
            )

    def _add_dynamic_fields(self):
        """
        Dynamically attach fields according to toggles on tournament.settings
        and per-game configs for eFootball/Valorant.
        """
        t = self.tournament
        sett = _settings(t)
        efb = _cfg_efootball(t)
        valo = _cfg_valorant(t)

        # Generic toggles commonly used by organizers
        wants_ingame_id    = _bool(sett, "ask_ingame_id") or _bool(sett, "require_ingame_id")
        wants_username     = _bool(sett, "ask_username") or _bool(sett, "require_username")
        wants_team_name    = _bool(sett, "ask_team_name")
        wants_screenshot   = _bool(sett, "ask_team_screenshot") or _bool(sett, "ask_roster_screenshot")
        wants_discord      = _bool(sett, "ask_discord") or _bool(sett, "require_discord")
        wants_whatsapp     = _bool(sett, "ask_whatsapp")
        wants_region       = _bool(sett, "ask_region")
        wants_logo         = _bool(sett, "ask_team_logo")
        wants_agree_rules  = _bool(sett, "require_rules_agree") or _bool(sett, "agree_rules")

        # Game-specific
        wants_efb_username = _bool(efb, "ask_username")
        wants_efb_id       = _bool(efb, "ask_ingame_id") or _bool(efb, "require_ingame_id")
        wants_valo_tag     = _bool(valo, "ask_riot_id") or _bool(valo, "require_riot_id")

        # Build fields (Form API ignores duplicates)
        if wants_username or wants_efb_username:
            self.fields.setdefault("in_game_username", forms.CharField(
                label="In-game Username", required=True
            ))
        if wants_ingame_id or wants_efb_id or wants_valo_tag:
            self.fields.setdefault("in_game_id", forms.CharField(
                label="In-game ID / Tag", required=True
            ))
        if wants_team_name:
            self.fields.setdefault("team_name", forms.CharField(
                label="Team Name", required=False
            ))
        if wants_logo:
            self.fields.setdefault("team_logo", forms.ImageField(
                label="Team Logo", required=False
            ))
        if wants_region:
            self.fields.setdefault("region", forms.CharField(
                label="Region", required=False
            ))
        if wants_discord:
            self.fields.setdefault("discord_id", forms.CharField(
                label="Discord ID", required=False
            ))
        if wants_whatsapp:
            self.fields.setdefault("whatsapp_number", forms.CharField(
                label="WhatsApp Number", required=False
            ))
        if wants_screenshot:
            self.fields.setdefault("team_screenshot", forms.ImageField(
                label="Team / Roster Screenshot", required=False
            ))
        if wants_agree_rules:
            self.fields.setdefault("agree_rules", forms.BooleanField(
                label="I agree to the tournament rules", required=True
            ))

    # Default tolerant save: create a Registration if schema matches; always return payload.
    def save(self) -> Dict[str, Any]:
        data = dict(self.cleaned_data)
        try:
            reg = Registration.objects.create(
                tournament=self.tournament,
                user=getattr(self.request, "user", None),
                status="submitted",
                # Best-effort copies; only if your Registration has these fields
                display_name=data.get("in_game_username") or data.get("team_name") or None,
                phone=data.get("payer_account_number") or None,
                email=getattr(getattr(self.request, "user", None), "email", None),
                team_name=data.get("team_name") or None,
            )
            data["registration_id"] = getattr(reg, "id", None)
        except Exception:
            # If schema doesn’t match, we still return cleaned data (service can persist)
            pass
        return data


# -------------------------- SOLO (1v1) --------------------------

class SoloRegistrationForm(_BaseRegForm):
    """
    For 1v1 solo tournaments (eFootball solo, etc.).
    """
    display_name = forms.CharField(required=False, label="Display name")
    email = forms.EmailField(required=False, label="Email")
    phone = forms.CharField(required=False, label="Phone")

    def clean(self):
        cd = super().clean()
        
        # Check tournament slot availability
        self._validate_tournament_slots()
        
        # If organizer requires rules agree (added dynamically), ensure it's True
        if "agree_rules" in self.fields and not cd.get("agree_rules"):
            self.add_error("agree_rules", "You must agree to the rules to continue.")
        # Phone format (basic BD mobile if provided)
        phone = cd.get("phone") or cd.get("payer_account_number")
        if phone:
            import re
            if not re.match(r"^(?:\+?880|0)1[0-9]{9}$", str(phone).replace(" ", "")):
                self.add_error("phone", "Enter a valid Bangladeshi mobile number.")
        return cd


# -------------------------- TEAM (captain-led) --------------------------

class TeamRegistrationForm(_BaseRegForm):
    """
    For team tournaments (Valorant, etc.). The view handles:
      - already-in-a-team path (captain registers),
      - create-team path when the user has no team.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if Team:
            try:
                self.fields.setdefault("team", forms.ModelChoiceField(
                    queryset=Team.objects.all(),
                    required=False,
                    label="Team (auto-selected if you’re in one)"
                ))
            except Exception:
                pass

    def clean(self):
        cd = super().clean()
        
        # Check tournament slot availability
        self._validate_tournament_slots()
        
        if "agree_rules" in self.fields and not cd.get("agree_rules"):
            self.add_error("agree_rules", "Team must accept the rules to continue.")
        return cd
