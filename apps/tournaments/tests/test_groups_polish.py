# apps/tournaments/tests/test_groups_polish.py
import pytest
from django.apps import apps
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.django_db

def test_validator_accepts_stats():
    from apps.tournaments.admin.brackets import _validate_groups_payload
    _validate_groups_payload({
        'groups': [{
            'name': 'Group A',
            'teams': [1,2],
            'stats': {'1': {'w': 2, 'l': 0}, '2': {'w': 1, 'l': 1}}
        }]
    })

def test_validator_rejects_bad_stats():
    from apps.tournaments.admin.brackets import _validate_groups_payload
    with pytest.raises(ValidationError):
        _validate_groups_payload({'groups': [{'name': 'A', 'teams': [1], 'stats': []}]})
    with pytest.raises(ValidationError):
        _validate_groups_payload({'groups': [{'name': 'A', 'teams': [1], 'stats': {'x': {}}}]})
    with pytest.raises(ValidationError):
        _validate_groups_payload({'groups': [{'name': 'A', 'teams': [1], 'stats': {'1': {'w': 'two'}}}]})
