from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apps.tournaments.api.toc.service import TOCService
from apps.tournaments.templatetags.tournament_filters import render_rulebook


@pytest.mark.parametrize(
    'progress,stage,expected',
    [
        (None, 'knockout_stage', 'pending'),
        ({'state': 'completed', 'total_matches': 0}, 'group_stage', 'pending'),
        ({'total_matches': 201, 'completed_matches': 200, 'completion_pct': 100},
         'group_stage', 'pending'),
        ({'total_matches': 6, 'completed_matches': 6}, 'group_stage', 'done'),
    ],
)
def test_group_completion_requires_finished_fixtures(progress, stage, expected):
    tournament = SimpleNamespace(
        status='registration_open', format='group_playoff',
        get_current_stage=lambda: stage,
    )
    with (
        patch('apps.tournaments.api.toc.service.Match.objects') as matches,
        patch('apps.brackets.models.Bracket.objects') as brackets,
        patch('apps.tournaments.services.completion_truth.is_tournament_effectively_completed',
              return_value=False),
    ):
        matches.filter.return_value.count.return_value = 0
        brackets.filter.return_value.exists.return_value = False
        result = TOCService._build_lifecycle_stepper(
            tournament=tournament, reg_stats={}, match_stats={}, group_progress=progress,
        )
    steps = {step['key']: step['status'] for step in result['steps']}
    assert steps['registration'] == 'active'
    assert steps['group_stage_live'] == expected


def test_about_rich_text_preserves_formatting_and_removes_unsafe_attributes():
    result = str(render_rulebook(
        '&lt;p&gt;Welcome &lt;strong&gt;players&lt;/strong&gt;&lt;/p&gt;'
        '<a href="javascript:alert(1)" onclick="alert(1)">Join</a>'
    ))
    assert '<p>Welcome <strong>players</strong></p>' in result
    assert 'javascript:' not in result
    assert 'onclick' not in result
