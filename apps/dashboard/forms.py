from __future__ import annotations
from django import forms
from django.utils import timezone

GAME_CHOICES = (
    ("", "All games"),
    ("valorant", "Valorant"),
    ("efootball", "eFootball"),
)

STATUS_CHOICES = (
    ("", "Any status"),
    ("upcoming", "Upcoming"),
    ("live", "Live"),
    ("completed", "Completed"),
)

class MyMatchesFilterForm(forms.Form):
    game = forms.ChoiceField(
        choices=GAME_CHOICES, required=False,
        label="Game", help_text="Filter by game."
    )
    tournament = forms.ChoiceField(
        choices=(), required=False,
        label="Tournament", help_text="Only tournaments you have matches in."
    )
    date_from = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"}),
        label="From date"
    )
    date_to = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"}),
        label="To date"
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES, required=False,
        label="Status"
    )
    q = forms.CharField(
        required=False, label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Search team name…”"})
    )

    def set_tournament_choices(self, choices: list[tuple[str, str]]):
        self.fields["tournament"].choices = [("", "All tournaments")] + choices
