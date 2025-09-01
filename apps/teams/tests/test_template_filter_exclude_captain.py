from types import SimpleNamespace
from apps.teams.templatetags.teams_extras import exclude_captain


def test_exclude_captain_basic():
    cap_user = SimpleNamespace(id=1, username="cap")
    team = SimpleNamespace(captain=SimpleNamespace(user=cap_user))
    mem_cap = SimpleNamespace(user=cap_user)
    mem_other = SimpleNamespace(user=SimpleNamespace(id=2))

    out = exclude_captain([mem_cap, mem_other], team)
    assert mem_cap not in out
    assert mem_other in out


def test_exclude_captain_tolerates_missing_fields():
    # Captain has no .user; membership exposes .profile.user
    cap_user = SimpleNamespace(id=5)
    team = SimpleNamespace(captain=cap_user)
    mem_weird = SimpleNamespace(profile=SimpleNamespace(user=cap_user))
    mem_ok = SimpleNamespace(profile=SimpleNamespace(user=SimpleNamespace(id=6)))

    out = exclude_captain([mem_weird, mem_ok], team)
    assert mem_weird not in out
    assert mem_ok in out
